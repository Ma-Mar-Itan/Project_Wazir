# Project Oracle — Local Python Bot

Runs entirely on your PC. Polls Telegram (no public URL/webhook needed). Reads and writes the same Google Sheet via the Sheets API. Talks to OpenRouter for ranking and (optionally) OpenAI Whisper for voice notes. Scheduled daily/weekly jobs run in the same process while the bot is up.

## Files

| File              | Purpose                                                      |
| ----------------- | ------------------------------------------------------------ |
| `config.py`       | Loads `.env`, defines tunables, sheet/status enums           |
| `utils.py`        | Date parsing, Markdown escaping                              |
| `state.py`        | Local JSON persistence (energy, last-run timestamp)          |
| `sheets.py`       | All Google Sheets access (gspread)                           |
| `voice.py`        | Whisper transcription (optional)                             |
| `llm.py`          | OpenRouter call + the `what's next` engine                   |
| `commands.py`     | All slash commands + default text/voice handlers             |
| `main.py`         | Entry point — handlers, scheduled jobs, polling loop         |
| `run.bat`         | Windows launcher (creates venv, installs deps, runs bot)     |
| `requirements.txt`| Python dependencies                                          |
| `.env.example`    | Copy to `.env` and fill in                                   |

## One-time setup

### 1. Install Python

Need Python 3.10+. Get it from [python.org](https://www.python.org/downloads/) — during install, **check "Add Python to PATH"**. To verify: open Command Prompt and run `python --version`.

### 2. Get a Telegram bot token

Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → follow prompts. Save the token.

### 3. Find your personal chat ID

Send any message to your bot, then visit:
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```
Look for `"chat":{"id":<NUMBER>` — that number is your chat ID.

### 4. Get an OpenRouter API key

Sign up at [openrouter.ai](https://openrouter.ai) → Keys → Create. Add some credit ($5 will last weeks of personal use on Sonnet).

### 5. Set up Google Sheets API access (service account)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create a new project (or pick one).
2. Enable the **Google Sheets API** and **Google Drive API** for that project.
3. Go to *APIs & Services → Credentials → Create credentials → Service account*. Give it a name. Skip the optional steps.
4. Click your new service account → *Keys → Add key → Create new key → JSON*. A JSON file downloads — rename it `credentials.json` and put it in this `bot/` folder.
5. Open the JSON file, find `"client_email": "...@...iam.gserviceaccount.com"`. Copy that email.
6. Open your Project Oracle Google Sheet → Share → paste the service account email → give Editor access → Send.

### 6. Find your Google Sheets ID

It's the long string in the URL between `/d/` and `/edit`:
`https://docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`

### 7. Configure `.env`

Copy `.env.example` to `.env` (literally rename — the dot in front matters), then fill in values:

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
OPENROUTER_API_KEY=sk-or-v1-...
GOOGLE_SHEETS_ID=1aBcDeFgHiJkLmNoPqRsTuVwXyZ...
GOOGLE_CREDENTIALS_PATH=credentials.json
OPENROUTER_MODEL=anthropic/claude-sonnet-4.5

# Optional — only if you want voice notes transcribed
OPENAI_API_KEY=sk-...
```

### 8. Run it

Double-click `run.bat`. First run will create a virtual environment and install dependencies (takes ~1–2 minutes). Subsequent runs start instantly.

You should see:
```
[run] Starting Project Oracle...
... | INFO | oracle | Project Oracle is running. Press Ctrl+C to stop.
```

### 9. Initialize the schema

In Telegram, send `/setup` to your bot. This adds the missing columns (`SnoozedUntil`, `TimesRanked`, `Movement`) and creates the `DecisionLog` tab.

### 10. You're done

Try `/help` to see all commands. Send any text — it logs to Inbox. Type `what's next` — it ranks.

## Keep it running

The bot only works while `run.bat` is open. Close that window, the bot stops.

To start it automatically when your PC boots:
1. Press `Win + R` → type `shell:startup` → Enter.
2. Drag `run.bat` into that folder (or right-click → Create shortcut → put the shortcut there).

To run minimized: edit the shortcut's *Run* property to *Minimized*.

To run truly in the background (no window at all), use Windows Task Scheduler with "Run whether user is logged on or not."

## Notes on existing data

- Existing inbox items keep their `processed` status — they're treated as active.
- Existing context items default to `type=constraint`. To upgrade them:
  - Edit the Type column directly in the Context tab, or
  - Delete + re-add via `/context <text> #identity` (or `#goal`).

## Tunables

Edit `config.py`:

```
RATE_LIMIT_SECONDS:     300   # cooldown on what's next
STALE_DAYS:             14    # age threshold for staleness
STALE_MAX_RANKS:        1     # ...AND ranked at most this many times
TOP_N:                  10
DECISION_LOG_DEPTH:     5     # last N runs fed back as memory
TRANSIENT_DEFAULT_DAYS: 7     # default expiry for #transient context
ENERGY_TTL_HOURS:       12
```

## Schema

| Sheet         | Columns                                                                  |
| ------------- | ------------------------------------------------------------------------ |
| `Inbox`       | Timestamp, Content, Type, EstimatedMinutes, Status, SnoozedUntil, TimesRanked |
| `Context`     | Context Item, Type, ExpiresAt                                            |
| `Master Path` | Priority, Task, Reasoning, Movement                                      |
| `DecisionLog` | Run Timestamp, Top 10 Tasks, Energy, Done Since Last Run                 |

Status values: `pending`, `processed`, `done`, `snoozed`, `killed`.
Context Type: `identity`, `goal`, `constraint`, `transient`.
Inbox Type: `task` (default), `project`. For `project` items, the LLM is instructed to rank the next concrete physical action, not the project label.

## Troubleshooting

**"Missing required env var"** — `.env` isn't being picked up. Confirm the file is named exactly `.env` (no `.txt` suffix) and is in the same folder as `main.py`.

**"WorksheetNotFound"** — service account email isn't shared on the sheet, or the `GOOGLE_SHEETS_ID` is wrong.

**"403 / 401 from Google"** — the Sheets and Drive APIs aren't enabled in your Google Cloud project.

**"Conflict: terminated by other getUpdates request"** — your bot is already running somewhere else (or a webhook is set). Run this once:
```
https://api.telegram.org/bot<YOUR_TOKEN>/deleteWebhook
```

**Voice notes do nothing** — `OPENAI_API_KEY` not set in `.env`, or you have no credit on it.

**`python` not recognized** — Python isn't on PATH. Reinstall and check the box during install.
