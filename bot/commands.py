"""Project Oracle — Telegram command handlers + default text/voice handlers."""

import os
import re
import tempfile
import time
from datetime import datetime
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from config import CONFIG, Status, CtxType, Sheets as SheetNames
from sheets import (
    inbox_all, inbox_active, inbox_append, inbox_set_status, inbox_set_snooze,
    inbox_increment_ranked, inbox_delete_row,
    context_all, context_active, context_append, context_delete,
    context_clear_all, context_remove_expired,
    master_path_read, setup_schema,
)
from utils import parse_duration, format_date, escape_markdown
from state import set_property
from llm import run_optimize


# ============ Reply helper ===========================================

async def reply(update: Update, text: str) -> None:
    await update.message.reply_text(
        text, parse_mode="Markdown", disable_web_page_preview=True
    )


# ============ Lookup helper ==========================================

def find_inbox_item(arg: str, items: list) -> Optional[dict]:
    """Resolve a /done-style argument to an inbox item.
    1) Numeric 1..TOP_N → Master Path row.
    2) Otherwise fuzzy keyword match against active inbox content.
    """
    if not arg:
        return None
    arg = arg.strip()
    try:
        idx = int(arg)
        if 1 <= idx <= CONFIG.TOP_N:
            path = master_path_read()
            if idx - 1 < len(path):
                target = path[idx - 1]
                for it in items:
                    if str(it["content"]).strip() == str(target["task"]).strip():
                        return it
    except ValueError:
        pass
    lc = arg.lower()
    for it in items:
        if lc in str(it["content"]).lower():
            return it
    return None


# ============ Task lifecycle =========================================

async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args)
    target = find_inbox_item(args, inbox_active())
    if not target:
        await reply(update, "Couldn't find that item. Use `/done <#>` (Top 10 index) or `/done <keyword>`.")
        return
    inbox_set_status(target["row"], Status.DONE)
    await reply(update, f"✓ Done: *{escape_markdown(target['content'])}*")


async def cmd_snooze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await reply(update,
            "Usage: `/snooze <#|keyword> <duration>`\n"
            "Duration: `1d`, `3d`, `1w`, `2w`, `1mo`, weekday name, or `YYYY-MM-DD`")
        return
    dur = args[-1]
    target = find_inbox_item(" ".join(args[:-1]), inbox_active())
    if not target:
        await reply(update, "Couldn't find that item.")
        return
    until = parse_duration(dur)
    if not until:
        await reply(update, f"Could not parse duration: `{dur}`")
        return
    inbox_set_snooze(target["row"], until)
    await reply(update, f"💤 Snoozed *{escape_markdown(target['content'])}* until {format_date(until)}")


async def cmd_keep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args)
    target = find_inbox_item(args, inbox_active())
    if not target:
        await reply(update, "Couldn't find that item.")
        return
    inbox_increment_ranked([target["row"]])
    await reply(update, f"🌱 Keeping *{escape_markdown(target['content'])}* alive.")


async def cmd_kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args)
    target = find_inbox_item(args, inbox_active())
    if not target:
        await reply(update, "Couldn't find that item.")
        return
    inbox_set_status(target["row"], Status.KILLED)
    await reply(update, f"☠️ Killed: *{escape_markdown(target['content'])}*")


async def cmd_clearinbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arg = " ".join(context.args).strip().lower() or "done"
    if arg not in ("done", "killed", "all"):
        await reply(update, "Usage: `/clearinbox [done|killed|all]` (default: done)")
        return
    all_items = inbox_all()
    if arg == "done":
        to_delete = [i for i in all_items if i["status"] == Status.DONE]
    elif arg == "killed":
        to_delete = [i for i in all_items if i["status"] == Status.KILLED]
    else:
        to_delete = list(all_items)
    to_delete.sort(key=lambda i: -i["row"])
    for it in to_delete:
        inbox_delete_row(it["row"])
    await reply(update, f"🧹 Cleared {len(to_delete)} item(s) from inbox ({arg}).")


# ============ Context ================================================

_TAG_RE = re.compile(r"^#(\w+)(?::(.+))?$", re.IGNORECASE)


async def cmd_context(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args)
    if not args:
        await reply(update,
            "Usage: `/context <text> [#identity|#goal|#constraint|#transient] [#expires:<date>]`\n"
            "Date: `YYYY-MM-DD`, `7d`, `2w`, `1mo`, or weekday name (e.g. `friday`).")
        return

    opts = {}
    text_tokens = []
    for tok in args.split():
        m = _TAG_RE.match(tok)
        if m:
            opts[m.group(1).lower()] = m.group(2) if m.group(2) else True
        else:
            text_tokens.append(tok)
    text = " ".join(text_tokens).strip()
    if not text:
        await reply(update, "Need some text for the context item.")
        return

    ctx_type = CtxType.CONSTRAINT
    for t in CtxType.ALL:
        if opts.get(t):
            ctx_type = t

    expires = None
    if isinstance(opts.get("expires"), str):
        expires = parse_duration(opts["expires"])
    if not expires and ctx_type == CtxType.TRANSIENT:
        expires = parse_duration(f"{CONFIG.TRANSIENT_DEFAULT_DAYS}d")

    context_append(text, ctx_type, expires)
    exp_str = f" (expires {format_date(expires)})" if expires else ""
    await reply(update, f"📌 Added [{ctx_type}]: {escape_markdown(text)}{exp_str}")


async def cmd_listcontext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = context_active()
    if not items:
        await reply(update, "No active context.")
        return
    lines = []
    for i, c in enumerate(items, 1):
        exp = f" _(until {format_date(c['expires_at'])})_" if c["expires_at"] else ""
        lines.append(f"{i}. *[{c['type']}]* {escape_markdown(c['item'])}{exp}")
    await reply(update, "*Current Context:*\n" + "\n".join(lines))


async def cmd_clearcontext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arg = " ".join(context.args).strip().lower()
    if not arg:
        await reply(update, "Usage: `/clearcontext <#|all>`")
        return
    if arg == "all":
        context_clear_all()
        await reply(update, "🧹 Cleared all context.")
        return
    try:
        idx = int(arg)
    except ValueError:
        await reply(update, "Use an index from `/listcontext` or `all`.")
        return
    items = context_active()
    if idx < 1 or idx > len(items):
        await reply(update, "Index out of range.")
        return
    target = items[idx - 1]
    context_delete(target["row"])
    await reply(update, f"🗑 Removed: {escape_markdown(target['item'])}")


# ============ Energy =================================================

async def cmd_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    level = " ".join(context.args).strip().lower()
    if level not in ("low", "medium", "high"):
        await reply(update, "Usage: `/energy <low|medium|high>`")
        return
    set_property("CURRENT_ENERGY", level)
    set_property("CURRENT_ENERGY_SET_AT", str(time.time()))
    await reply(update, f"🔋 Energy set to *{level}* (decays in {CONFIG.ENERGY_TTL_HOURS}h)")


# ============ Review =================================================

async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def send(text: str) -> None:
        await update.message.reply_text(
            text, parse_mode="Markdown", disable_web_page_preview=True
        )
    await do_review(send)


async def do_review(send) -> None:
    """send: async callable taking a single text argument."""
    all_items = inbox_all()
    now = datetime.now()
    stale = [
        i for i in all_items
        if i["status"] in (Status.PROCESSED, Status.PENDING)
        and (now - i["timestamp"]).days >= CONFIG.STALE_DAYS
        and i["times_ranked"] <= CONFIG.STALE_MAX_RANKS
    ]
    expired = [c for c in context_all() if c["expires_at"] and c["expires_at"] <= now]
    removed = context_remove_expired()

    msg = "*Weekly Review*\n\n"
    if stale:
        msg += "*Stale items* (old, never prioritized):\n"
        for i, s in enumerate(stale, 1):
            msg += f"{i}. {escape_markdown(s['content'])}\n"
        msg += "\nUse `/keep <keyword>` or `/kill <keyword>`.\n\n"
    if expired:
        msg += f"*Auto-cleared {removed} expired context item(s).*\n\n"
    if not stale and not expired:
        msg += "Nothing stale or expired. Inbox looks healthy.\n"
    await send(msg)


# ============ Help / setup ===========================================

_HELP = """*Project Oracle — Commands*

*Capture*
• Send any text → logged to Inbox
• Send a voice note → transcribed via Whisper + logged

*Tasks*
• `/done <#|keyword>` — mark complete
• `/snooze <#|keyword> <dur>` — pause (3d, 1w, friday, 2026-05-01)
• `/keep <#|keyword>` — keep stale item alive
• `/kill <#|keyword>` — abandon item
• `/clearinbox [done|killed|all]` — bulk delete (default: done)

*Context*
• `/context <text> [#type] [#expires:<date>]`
   types: `#identity` `#goal` `#constraint` `#transient`
• `/listcontext` — show active context
• `/clearcontext <#|all>` — remove

*State*
• `/energy <low|medium|high>` — set energy (decays in 12h)
• `/review` — surface stale items + clear expired context

*Optimization*
• Type `what's next` (no slash) — re-rank everything

*Setup*
• `/setup` — initialize sheet schema
• `/help` — this message"""


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, _HELP)


async def cmd_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    setup_schema()
    await reply(update,
        "✓ Setup complete.\n"
        "• Sheet schema validated\n"
        "• Missing columns added\n"
        "• Daily/weekly jobs running in-process")


# ============ Default text + voice ===================================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return

    lower = text.lower().rstrip("?!.").strip()
    if lower in ("what's next", "whats next", "what next"):
        async def send(t: str) -> None:
            await update.message.reply_text(
                t, parse_mode="Markdown", disable_web_page_preview=True
            )
        await run_optimize(send)
        return

    inbox_append(text)
    count = len(inbox_active())
    await reply(update, f"📥 Logged. ({count} active)")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from voice import transcribe_voice_file  # late import for optional dep

    voice = update.message.voice
    if not voice:
        return

    tmp_path = None
    try:
        tg_file = await context.bot.get_file(voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tf:
            tmp_path = tf.name
        await tg_file.download_to_drive(tmp_path)
        text = transcribe_voice_file(tmp_path)
    except Exception as e:
        await reply(update, f"🎙 Transcription failed: {e}")
        return
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    if not text:
        await reply(update, "🎙 Voice transcription unavailable. Set `OPENAI_API_KEY` in `.env`.")
        return

    inbox_append(text)
    await reply(update, f"🎙 Logged: {escape_markdown(text)}")
