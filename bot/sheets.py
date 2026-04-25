"""Project Oracle — Google Sheets access via gspread.

Schema:
  Inbox:        Timestamp | Content | Type | EstimatedMinutes | Status | SnoozedUntil | TimesRanked
  Context:      Context Item | Type | ExpiresAt
  Master Path:  Priority | Task | Reasoning | Movement
  DecisionLog:  Run Timestamp | Top 10 Tasks | Energy | Done Since Last Run
"""

import json
from datetime import datetime
from typing import Any, Optional

import gspread
from google.oauth2.service_account import Credentials

from config import CONFIG, Sheets, Status, CtxType

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None
_spreadsheet = None


def _ss():
    """Lazy spreadsheet handle. One Google Sheets connection per process."""
    global _client, _spreadsheet
    if _spreadsheet is None:
        creds = Credentials.from_service_account_file(
            CONFIG.GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
        )
        _client = gspread.authorize(creds)
        _spreadsheet = _client.open_by_key(CONFIG.GOOGLE_SHEETS_ID)
    return _spreadsheet


def _tab(name: str):
    return _ss().worksheet(name)


def _tab_or_create(name: str, headers: list):
    try:
        return _ss().worksheet(name)
    except gspread.WorksheetNotFound:
        ws = _ss().add_worksheet(title=name, rows=1000, cols=max(10, len(headers)))
        ws.update("A1", [headers])
        ws.freeze(rows=1)
        return ws


def _safe_parse(s: Any, fallback: Any) -> Any:
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return fallback


def _parse_dt(s: Any) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


# ============ Inbox ==================================================

def inbox_append(content: str) -> None:
    _tab(Sheets.INBOX).append_row(
        [datetime.now().isoformat(timespec="seconds"), content, "", "", Status.PENDING, "", 0],
        value_input_option="USER_ENTERED",
    )


def inbox_all() -> list:
    rows = _tab(Sheets.INBOX).get_all_values()
    if len(rows) < 2:
        return []
    items = []
    for i, r in enumerate(rows[1:], start=2):
        r = (r + [""] * 7)[:7]
        if not r[1]:
            continue
        try:
            est = int(r[3]) if str(r[3]).strip().isdigit() else None
        except ValueError:
            est = None
        try:
            tr = int(r[6]) if str(r[6]).strip().isdigit() else 0
        except ValueError:
            tr = 0
        items.append({
            "row": i,
            "timestamp": _parse_dt(r[0]) or datetime.now(),
            "content": r[1],
            "type": (r[2] or "task").lower(),
            "est_minutes": est,
            "status": (r[4] or Status.PENDING).lower(),
            "snoozed_until": _parse_dt(r[5]),
            "times_ranked": tr,
        })
    return items


def inbox_active() -> list:
    now = datetime.now()
    out = []
    for it in inbox_all():
        if it["status"] == Status.DONE:    continue
        if it["status"] == Status.KILLED:  continue
        if (it["status"] == Status.SNOOZED and it["snoozed_until"]
                and it["snoozed_until"] > now):
            continue
        out.append(it)
    return out


def inbox_set_status(row: int, status: str) -> None:
    _tab(Sheets.INBOX).update_cell(row, 5, status)


def inbox_set_snooze(row: int, until_dt: datetime) -> None:
    sh = _tab(Sheets.INBOX)
    sh.update_cell(row, 5, Status.SNOOZED)
    sh.update_cell(row, 6, until_dt.isoformat(timespec="seconds"))


def inbox_increment_ranked(rows: list) -> None:
    if not rows:
        return
    sh = _tab(Sheets.INBOX)
    for r in rows:
        cur = sh.cell(r, 7).value
        cur_n = int(cur) if cur and str(cur).strip().isdigit() else 0
        sh.update_cell(r, 7, cur_n + 1)


def inbox_mark_pending_processed() -> None:
    sh = _tab(Sheets.INBOX)
    rows = sh.get_all_values()
    if len(rows) < 2:
        return
    updates = []
    for i, r in enumerate(rows[1:], start=2):
        if len(r) >= 5 and (r[4] or "").strip().lower() == Status.PENDING:
            updates.append({"range": f"E{i}", "values": [[Status.PROCESSED]]})
    if updates:
        sh.batch_update(updates)


def inbox_delete_row(row: int) -> None:
    _tab(Sheets.INBOX).delete_rows(row)


# ============ Context ================================================

def context_all() -> list:
    rows = _tab(Sheets.CONTEXT).get_all_values()
    if len(rows) < 2:
        return []
    items = []
    for i, r in enumerate(rows[1:], start=2):
        r = (r + [""] * 3)[:3]
        if not r[0]:
            continue
        items.append({
            "row": i,
            "item": r[0],
            "type": (r[1] or CtxType.CONSTRAINT).lower(),
            "expires_at": _parse_dt(r[2]),
        })
    return items


def context_active() -> list:
    now = datetime.now()
    return [c for c in context_all() if not c["expires_at"] or c["expires_at"] > now]


def context_append(item: str, ctx_type: str, expires_at: Optional[datetime]) -> None:
    exp_str = expires_at.isoformat(timespec="seconds") if expires_at else ""
    _tab(Sheets.CONTEXT).append_row(
        [item, ctx_type or CtxType.CONSTRAINT, exp_str],
        value_input_option="USER_ENTERED",
    )


def context_delete(row: int) -> None:
    _tab(Sheets.CONTEXT).delete_rows(row)


def context_clear_all() -> None:
    sh = _tab(Sheets.CONTEXT)
    rows = sh.get_all_values()
    if len(rows) > 1:
        sh.delete_rows(2, len(rows))


def context_remove_expired() -> int:
    items = context_all()
    now = datetime.now()
    expired = [c for c in items if c["expires_at"] and c["expires_at"] <= now]
    expired.sort(key=lambda c: -c["row"])
    for c in expired:
        _tab(Sheets.CONTEXT).delete_rows(c["row"])
    return len(expired)


# ============ Master Path ============================================

def master_path_read() -> list:
    rows = _tab(Sheets.MASTER_PATH).get_all_values()
    if len(rows) < 2:
        return []
    out = []
    for r in rows[1:]:
        r = (r + [""] * 4)[:4]
        if not r[1]:
            continue
        out.append({
            "priority": r[0],
            "task": r[1],
            "reasoning": r[2],
            "movement": r[3],
        })
    return out


def master_path_write(top: list) -> None:
    sh = _tab(Sheets.MASTER_PATH)
    n = len(sh.get_all_values())
    if n > 1:
        sh.batch_clear([f"A2:D{n}"])
    if not top:
        return
    rows = [[t["priority"], t["task"], t.get("reasoning", ""), t.get("movement", "")] for t in top]
    sh.update(f"A2:D{1 + len(rows)}", rows, value_input_option="USER_ENTERED")


# ============ Decision Log ===========================================

def decision_log_append(entry: dict) -> None:
    sh = _tab_or_create(
        Sheets.DECISION_LOG,
        ["Run Timestamp", "Top 10 Tasks", "Energy", "Done Since Last Run"],
    )
    sh.append_row(
        [
            entry["timestamp"].isoformat(timespec="seconds"),
            json.dumps(entry.get("top10_tasks", [])),
            entry.get("energy", "") or "",
            json.dumps(entry.get("done_since_last", [])),
        ],
        value_input_option="USER_ENTERED",
    )


def decision_log_recent(n: int) -> list:
    try:
        sh = _tab(Sheets.DECISION_LOG)
    except gspread.WorksheetNotFound:
        return []
    rows = sh.get_all_values()
    if len(rows) < 2:
        return []
    out = []
    for r in rows[-n:]:
        r = (r + [""] * 4)[:4]
        out.append({
            "timestamp": _parse_dt(r[0]),
            "top10_tasks": _safe_parse(r[1], []),
            "energy": r[2],
            "done_since_last": _safe_parse(r[3], []),
        })
    return out


# ============ Setup / schema =========================================

def _ensure_headers(sheet, expected: list) -> None:
    rows = sheet.get_all_values()
    current = rows[0] if rows else []
    current = (current + [""] * len(expected))[:max(len(current), len(expected))]
    updates = []
    for i, h in enumerate(expected):
        if i >= len(current) or current[i] != h:
            col_letter = chr(ord("A") + i)
            updates.append({"range": f"{col_letter}1", "values": [[h]]})
    if updates:
        sheet.batch_update(updates)
    sheet.freeze(rows=1)


def setup_schema() -> None:
    inbox = _tab(Sheets.INBOX)
    _ensure_headers(inbox, [
        "Timestamp", "Content", "Type", "EstimatedMinutes",
        "Status", "SnoozedUntil", "TimesRanked",
    ])
    rows = inbox.get_all_values()
    if len(rows) >= 2:
        updates = []
        for i, r in enumerate(rows[1:], start=2):
            if len(r) < 7 or not str(r[6]).strip():
                updates.append({"range": f"G{i}", "values": [[0]]})
        if updates:
            inbox.batch_update(updates)

    _ensure_headers(_tab(Sheets.CONTEXT), ["Context Item", "Type", "ExpiresAt"])
    _ensure_headers(_tab(Sheets.MASTER_PATH), ["Priority", "Task", "Reasoning", "Movement"])
    _tab_or_create(Sheets.DECISION_LOG, ["Run Timestamp", "Top 10 Tasks", "Energy", "Done Since Last Run"])
