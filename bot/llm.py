"""Project Oracle — LLM call + the optimization engine."""

import json
import time
from datetime import datetime
from typing import Awaitable, Callable, Optional

import requests

from config import CONFIG
from sheets import (
    inbox_active, inbox_increment_ranked, inbox_mark_pending_processed,
    context_active, context_remove_expired,
    master_path_read, master_path_write,
    decision_log_append, decision_log_recent,
)
from state import get_property, set_property, get_current_energy
from utils import format_date, escape_markdown


SendFn = Callable[[str], Awaitable[None]]


# ============ LLM call ===============================================

def call_llm(system_prompt: str, user_prompt: str) -> str:
    res = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {CONFIG.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://project-oracle.local",
            "X-Title": "Project Oracle",
            "Content-Type": "application/json",
        },
        json={
            "model": CONFIG.OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
            # No response_format: many free / preview OpenRouter models reject it.
            # The prompt already mandates JSON-only output.
        },
        timeout=60,
    )
    if res.status_code >= 400:
        raise RuntimeError(
            f"OpenRouter HTTP {res.status_code} for model={CONFIG.OPENROUTER_MODEL}: "
            f"{res.text[:500]}"
        )
    j = res.json()
    if not j.get("choices"):
        raise RuntimeError(f"LLM bad response: {str(j)[:400]}")
    return _strip_code_fence(j["choices"][0]["message"]["content"])


def _strip_code_fence(s: str) -> str:
    """Some models wrap JSON in ```json ... ``` fences. Strip if present."""
    if not s:
        return s
    s = s.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1:]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
    return s


# ============ Prompt building ========================================

def build_system_prompt() -> str:
    return f"""You are Project Oracle, a personal logic engine for an INTP user. Your job: re-rank the user's active tasks into a Top {CONFIG.TOP_N} every time they ask "what's next".

Apply this reasoning, in order:
1. Identify prerequisite chains. If task X depends on Y, Y comes first.
2. Weight context by type: identity = core values (always relevant), goal = long-term direction (boost aligned tasks), constraint = current realities, transient = time-bound situations.
3. Match energy to task type. Low → quick-wins (≤30 min). High → deep work and prerequisites that unblock big projects.
4. For Type=project items, rank the next concrete physical action — not the project label.
5. Items aged >{CONFIG.STALE_DAYS} days that have appeared in past Top 10s many times but never been done are likely being avoided. Surface them in stale_flags.
6. Decision history shows what the user actually does vs. what gets ranked. If a task keeps ranking high but never gets done, deprioritize and flag.

Return ONLY a JSON object, no prose, no markdown fences:
{{
  "top": [
    {{"priority": 1, "task_id": <number>, "task": "<exact task content>", "reasoning": "<one short sentence>"}}
  ],
  "primary_driver": "<one-line summary of what is driving today's ranking>",
  "stale_flags": [<task_id>, ...]
}}

Use task_id values exactly as given. Limit top to {CONFIG.TOP_N}. Keep reasoning under 20 words per item."""


def build_user_prompt(ctx: list, items: list, history: list, energy: Optional[str]) -> str:
    if not ctx:
        ctx_str = "(none)"
    else:
        lines = []
        for c in ctx:
            exp = f" [until {format_date(c['expires_at'])}]" if c["expires_at"] else ""
            lines.append(f"- [{c['type']}] {c['item']}{exp}")
        ctx_str = "\n".join(lines)

    items_lines = []
    now = datetime.now()
    for it in items:
        age_days = max((now - it["timestamp"]).days, 0)
        meta_parts = [
            f"id={it['row']}",
            f"type={it['type']}",
        ]
        if it["est_minutes"]:
            meta_parts.append(f"est={it['est_minutes']}m")
        meta_parts.append(f"age={age_days}d")
        meta_parts.append(f"ranked={it['times_ranked']}x")
        meta = " ".join(meta_parts)
        items_lines.append(f"- ({meta}) {it['content']}")
    items_str = "\n".join(items_lines)

    if not history:
        hist_str = "(no prior runs)"
    else:
        hist_lines = []
        for h in history:
            top3 = " | ".join((x.get("task") or "") for x in (h.get("top10_tasks") or [])[:3])
            done = " | ".join(h.get("done_since_last") or [])
            ts_str = format_date(h["timestamp"]) if h.get("timestamp") else "?"
            hist_lines.append(
                f"- {ts_str} (energy={h.get('energy') or '?'}): top3 = {top3}; closed since = {done or 'none'}"
            )
        hist_str = "\n".join(hist_lines)

    return f"""CONTEXT (active worldview):
{ctx_str}

INBOX (active items — id, type, estimated minutes, age, times appeared in past Top 10):
{items_str}

CURRENT ENERGY: {energy or 'unknown'}

DECISION HISTORY (last {CONFIG.DECISION_LOG_DEPTH} runs):
{hist_str}

Return your JSON now."""


# ============ Optimize engine ========================================

async def run_optimize(send: SendFn) -> None:
    """Re-rank everything. send(text) is an async function that posts to Telegram."""

    last = get_property("LAST_OPTIMIZE_AT")
    if last:
        try:
            since = time.time() - float(last)
            if since < CONFIG.RATE_LIMIT_SECONDS:
                wait = int(CONFIG.RATE_LIMIT_SECONDS - since)
                await send(f"⏳ Just ran. Try again in {wait}s — ranking won't meaningfully change inside that window.")
                return
        except (ValueError, TypeError):
            pass

    context_remove_expired()

    ctx = context_active()
    items = inbox_active()
    if not items:
        await send("Inbox is empty. Add tasks first.")
        return

    energy = get_current_energy()
    history = decision_log_recent(CONFIG.DECISION_LOG_DEPTH)
    previous = master_path_read()

    try:
        raw = call_llm(build_system_prompt(), build_user_prompt(ctx, items, history, energy))
        result = json.loads(raw)
    except Exception as e:
        await send(f"⚠️ LLM error: {e}")
        return

    if not isinstance(result, dict) or not result.get("top"):
        await send("⚠️ LLM returned malformed output.")
        return

    valid_ids = {it["row"] for it in items}
    enriched = []
    for t in result["top"][:CONFIG.TOP_N]:
        if not t.get("task"):
            continue
        try:
            priority = int(t.get("priority"))
        except (ValueError, TypeError):
            priority = 0
        try:
            task_id = int(t.get("task_id"))
        except (ValueError, TypeError):
            task_id = 0
        enriched.append({
            "priority": priority,
            "task_id": task_id,
            "task": t["task"],
            "reasoning": t.get("reasoning", ""),
            "movement": _compute_movement(t["task"], priority, previous),
        })

    master_path_write(enriched)

    top_rows = [t["task_id"] for t in enriched if t["task_id"] in valid_ids]
    inbox_increment_ranked(top_rows)
    inbox_mark_pending_processed()

    last_entry = history[-1] if history else None
    done_since = _compute_done_since_last(last_entry, items)
    decision_log_append({
        "timestamp": datetime.now(),
        "top10_tasks": [{"p": t["priority"], "task": t["task"]} for t in enriched],
        "energy": energy or "",
        "done_since_last": done_since,
    })

    set_property("LAST_OPTIMIZE_AT", str(time.time()))

    await send(_format_top_n(enriched, result.get("primary_driver")))

    flagged_ids = []
    for x in (result.get("stale_flags") or []):
        try:
            xi = int(x)
            if xi in valid_ids:
                flagged_ids.append(xi)
        except (ValueError, TypeError):
            continue
    if flagged_ids:
        flagged = [it for it in items if it["row"] in flagged_ids]
        if flagged:
            lines = "\n".join(f"• {escape_markdown(f['content'])}" for f in flagged)
            await send(
                f"🧹 *Possibly stale*:\n{lines}\n\n"
                "Reply `/keep <keyword>` to keep, `/kill <keyword>` to abandon."
            )


def _compute_movement(task: str, new_priority, previous: list) -> str:
    prev = next((p for p in previous if str(p["task"]).strip() == str(task).strip()), None)
    if not prev:
        return "NEW"
    try:
        old_p = int(prev["priority"])
        new_p = int(new_priority)
    except (ValueError, TypeError):
        return ""
    if old_p == new_p:
        return "="
    if new_p < old_p:
        return f"↑{old_p - new_p}"
    return f"↓{new_p - old_p}"


def _compute_done_since_last(last_entry: Optional[dict], current_items: list) -> list:
    if not last_entry or not last_entry.get("top10_tasks"):
        return []
    active_set = {str(it["content"]).strip() for it in current_items}
    out = []
    for t in last_entry["top10_tasks"]:
        task_text = t.get("task")
        if task_text and str(task_text).strip() not in active_set:
            out.append(task_text)
    return out


def _format_top_n(top: list, primary_driver: Optional[str]) -> str:
    s = ""
    if primary_driver:
        s += f"_{escape_markdown(primary_driver)}_\n\n"
    s += f"*Top {len(top)}*\n"
    for t in top:
        arrow = f" `{t['movement']}`" if t.get("movement") else ""
        s += f"{t['priority']}.{arrow} *{escape_markdown(t['task'])}*\n   _{escape_markdown(t['reasoning'])}_\n"
    return s
