"""Project Oracle — entry point. Run this file to start the bot."""

import logging
from datetime import time as dt_time

from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters,
)

from config import CONFIG
from sheets import context_remove_expired
from commands import (
    cmd_done, cmd_snooze, cmd_keep, cmd_kill, cmd_clearinbox,
    cmd_context, cmd_listcontext, cmd_clearcontext,
    cmd_energy, cmd_review, cmd_help, cmd_setup,
    handle_text, handle_voice, do_review,
)


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("oracle")


# ============ Telegram command menu ==================================
# This populates the blue "Menu" button next to the input box in Telegram.
# Runs once on startup; stays in sync with the code automatically.

BOT_COMMANDS = [
    BotCommand("done",         "Mark a task complete"),
    BotCommand("snooze",       "Pause a task until a date"),
    BotCommand("keep",         "Keep a stale-flagged item alive"),
    BotCommand("kill",         "Abandon a task"),
    BotCommand("clearinbox",   "Bulk delete inbox items"),
    BotCommand("context",      "Add a context item"),
    BotCommand("listcontext",  "Show active context"),
    BotCommand("clearcontext", "Remove context items"),
    BotCommand("energy",       "Set energy level"),
    BotCommand("review",       "Stale items + cleanup"),
    BotCommand("setup",        "Initialize sheet schema"),
    BotCommand("help",         "Show command list"),
]


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(BOT_COMMANDS)
    log.info("Telegram command menu registered (%d commands).", len(BOT_COMMANDS))


# ============ Scheduled jobs =========================================

async def daily_sweep_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    removed = context_remove_expired()
    if removed > 0 and CONFIG.TELEGRAM_CHAT_ID:
        await context.bot.send_message(
            chat_id=CONFIG.TELEGRAM_CHAT_ID,
            text=f"🧹 Daily sweep: removed {removed} expired context item(s).",
        )


async def weekly_review_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not CONFIG.TELEGRAM_CHAT_ID:
        return

    async def send(text: str) -> None:
        await context.bot.send_message(
            chat_id=CONFIG.TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

    await do_review(send)


# ============ Bootstrap ==============================================

def main() -> None:
    app = (
        Application.builder()
        .token(CONFIG.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Slash commands
    app.add_handler(CommandHandler("done",         cmd_done))
    app.add_handler(CommandHandler("snooze",       cmd_snooze))
    app.add_handler(CommandHandler("keep",         cmd_keep))
    app.add_handler(CommandHandler("kill",         cmd_kill))
    app.add_handler(CommandHandler("clearinbox",   cmd_clearinbox))
    app.add_handler(CommandHandler("context",      cmd_context))
    app.add_handler(CommandHandler("listcontext",  cmd_listcontext))
    app.add_handler(CommandHandler("clearcontext", cmd_clearcontext))
    app.add_handler(CommandHandler("energy",       cmd_energy))
    app.add_handler(CommandHandler("review",       cmd_review))
    app.add_handler(CommandHandler("help",         cmd_help))
    app.add_handler(CommandHandler("setup",        cmd_setup))

    # Voice notes (Whisper) + plain text fallback
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Scheduled jobs (in-process JobQueue, runs while bot is running)
    jq = app.job_queue
    if jq is not None:
        jq.run_daily(daily_sweep_job, time=dt_time(hour=2, minute=0))
        jq.run_daily(weekly_review_job, time=dt_time(hour=17, minute=0), days=(4,))
    else:
        log.warning("JobQueue unavailable. Install `python-telegram-bot[job-queue]` for scheduled tasks.")

    log.info("Project Oracle is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
