# Wazir

**A personal AI butler. Quiet, competent, always thinking ahead.**

*Wazir* (وزير) is the Arabic word for a high counsel — a vizier, an advisor, the strategist who serves the sultan and runs the day-to-day so the principal can focus on what only they can do. That's the role this project aims at: a JARVIS-class personal assistant, built piece by piece.

The current organ — what's running today — is **Project Oracle**, the prioritization brain. You feed it your tasks and your life context, and an LLM re-ranks your world on demand. More organs are coming.

This is **v0.1**. The foundation.

---

## The long-term vision

What JARVIS does for Tony Stark: scheduling, triage, research, comms, monitoring, gentle nudges, ambient awareness. Wazir aims at the same role — minus the holograms — for a single human, running locally.

The build plan, organ by organ:

| Organ            | What it does                                                                       | Status     |
| ---------------- | ---------------------------------------------------------------------------------- | ---------- |
| **Oracle**       | Re-ranks your active tasks against context, energy, and decision history           | **Live**   |
| **Almanac**      | Pulls in calendar + deadlines so ranking respects what's actually scheduled        | Next       |
| **Herald**       | Morning briefing — what shifted overnight, what's due today, weather/markets       | Soon       |
| **Scribe**       | Drafts and triages email + messages; never sends without explicit approval         | Soon       |
| **Cartographer** | Long-term memory and journal; surfaces "you mentioned X two weeks ago, follow up?" | Planned    |
| **Steward**      | File management — "organize my Downloads," "find the contract from March"          | Planned    |
| **Watchman**     | Health, sleep, focus signals — intervenes when context demands rest                | Planned    |

Each organ slots into the same architecture: Telegram-fronted, Sheets/JSON-persisted, OpenRouter-backed, local-first, modular.

---

## What's running today: Project Oracle

Open Telegram, talk to your Wazir:

```
you  > Read the new robotics book
bot  > 📥 Logged. (8 active)

you  > /context exam on Monday cancelled #transient
bot  > 📌 Added [transient]: exam on Monday cancelled (expires 2026-05-02)

you  > what's next

bot  > _Today's primary driver: exam pressure removed → deep-work tasks rise._
       
       *Top 5*
       1. ↑3 *Learn time series analysis*
          _Prerequisite for ML contests; freed bandwidth from cancelled exam._
       2. ↑1 *Read robotics book*
          _Aligns directly with 10-year robotics goal._
       3. ↓2 *Project for the center due Monday*
          _Still on deadline but no longer the only thing competing for today._
       4. NEW *Quran*
          _Identity-aligned daily practice; promote on freed days._
       5. = *Speech*
          _Steady-state; remains relevant but not blocked or urgent._
       
       🧹 *Possibly stale*:
       • Hard to kill
       Reply `/keep <keyword>` to keep, `/kill <keyword>` to abandon.
```

The arrows (`↑3`, `↓2`, `NEW`, `=`) show movement since the last run. The italicized line is the LLM's one-sentence summary of what's driving today's ranking. The "stale" callout flags items that have lingered for weeks without ever making the Top 10 — likely things you're avoiding for a reason.

### What Oracle does

- **Frictionless capture.** Send any text or voice note to the bot — it lands in your Inbox. Voice goes through Whisper.
- **Natural-language trigger.** Type `what's next`. No slash needed.
- **Typed context with TTL.** Tag items `#identity`, `#goal`, `#constraint`, or `#transient`. Add `#expires:2026-05-15` or `#expires:friday` and the constraint auto-clears.
- **Movement diff.** `↑3`, `↓2`, `NEW`, `=` next to each entry — see exactly what shifted.
- **Energy-aware ranking.** `/energy low|medium|high`. Low → quick-wins (≤30 min). High → deep work and prerequisites that unblock big projects.
- **Staleness detection.** Items aged past a threshold that never make Top 10 get flagged. Reply `/keep` or `/kill` to resolve in one tap.
- **Memory across runs.** The LLM sees the last N runs' Top 3 plus what got closed, so a chronically-deferred task gets surfaced rather than buried.
- **One-shot completion.** `/done 1` or `/done python` from Telegram — no opening Sheets to mark things off.
- **Snooze.** `/snooze 3 1w` parks an item for a week. `/snooze python friday` until next Friday.
- **Local, single-binary, single-user.** No webhook, no public URL, no cloud bill.
- **Daily auto-sweep + Friday weekly review.** Expired transient context gets cleared at 02:00 daily; Friday at 17:00 you get a stale-items review pinged to you.

---

## Design principles

These hold across every future organ:

1. **Local-first.** Your data stays on your machine and your Sheet. No SaaS in the loop. No login wall to your own life.
2. **Telegram as the universal interface.** Typing beats clicking, voice beats typing, and Telegram works on every device with a network. One chat — eventually one bot — fronting every organ.
3. **Sheets as the persistent body.** Auditable, hand-editable, easy to inspect. Anything Wazir thinks lives in a tab you can open. No black box.
4. **Provider-agnostic LLM.** OpenRouter, so you can swap models without code changes. Free models work; paid ones cost cents.
5. **Modular by organ.** Each capability is independently installable. Today's Oracle stays running while tomorrow's Almanac slots in beside it.
6. **Persistent by default.** Wazir doesn't quietly forget. Tasks, context, history — they stay until you explicitly close them.

---

## Architecture

```
┌─────────────────┐   text/voice     ┌──────────────────┐
│  Telegram bot   │ ───────────────► │  Local Python    │
│   (Senses)      │                  │  (Organs)        │
└─────────────────┘ ◄─── reply ───── └────────┬─────────┘
                                              │
                              gspread ────────┼──── requests
                                              ▼
                              ┌─────────────────┐  ┌─────────────┐
                              │  Google Sheets  │  │ OpenRouter  │
                              │     (Body)      │  │   (Brain)   │
                              └─────────────────┘  └─────────────┘
```

- **Senses (Telegram):** async capture via long-polling. No public URL.
- **Body (Google Sheets):** Oracle owns four tabs — `Inbox`, `Context`, `Master Path`, `DecisionLog`. Future organs add their own tabs.
- **Brain (OpenRouter):** any LLM you point it at. Currently `openai/gpt-oss-120b:free`.

The Python process is the home for all organs. Each one registers handlers (slash commands, scheduled jobs) on startup. Adding a new organ means dropping a new module in `bot/` and wiring it in `main.py`.

---

## Quick start

You'll need a Telegram account, a Google account, an OpenRouter account, and Python 3.10+.

### 1. Gather credentials

| What                   | Where                                                                   |
| ---------------------- | ----------------------------------------------------------------------- |
| Telegram bot token     | DM [@BotFather](https://t.me/BotFather) → `/newbot`                     |
| Telegram chat ID       | Send your bot any message, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat.id` |
| OpenRouter API key     | [openrouter.ai/keys](https://openrouter.ai/keys)                        |
| Google service account | [console.cloud.google.com](https://console.cloud.google.com) → enable Sheets + Drive APIs → IAM → Service accounts → Create → Keys → JSON → save as `credentials.json` |

Then **share your Google Sheet with the service account email** (looks like `something@project-name.iam.gserviceaccount.com`) — Editor access.

### 2. Configure

```bash
git clone https://github.com/<you>/wazir.git
cd wazir/bot
cp .env.example .env
# edit .env with your values
# place credentials.json in this folder
```

Minimum `.env`:

```ini
TELEGRAM_BOT_TOKEN=123456:ABC-...
TELEGRAM_CHAT_ID=123456789
OPENROUTER_API_KEY=sk-or-v1-...
GOOGLE_SHEETS_ID=1aBc...    # the long string in your sheet's URL between /d/ and /edit
GOOGLE_CREDENTIALS_PATH=credentials.json
OPENROUTER_MODEL=openai/gpt-oss-120b:free
OPENAI_API_KEY=             # optional, for Whisper voice transcription
```

### 3. Run

**Windows:** double-click `bot/run.bat`. First run creates a venv and installs dependencies (~1 min); subsequent runs start instantly.

**macOS / Linux:**
```bash
cd bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 4. Initialize the sheet

In Telegram, send `/setup`. The bot adds any missing columns (`SnoozedUntil`, `TimesRanked`, `Movement`) and creates the `DecisionLog` tab.

### 5. Use it

- Send any text → logged to Inbox
- Send a voice note → transcribed (if `OPENAI_API_KEY` is set) and logged
- Type `what's next` → ranked Top 10 with reasoning + diff arrows
- Send `/help` for the full command list

To keep Wazir running automatically on Windows: `Win+R` → `shell:startup` → drop a shortcut to `run.bat` in there.

---

## Commands (Oracle organ)

### Capture
| Action              | How                                            |
| ------------------- | ---------------------------------------------- |
| Log a thought       | Send any text                                  |
| Log a voice thought | Send a voice note (requires `OPENAI_API_KEY`)  |
| Re-rank now         | Type `what's next`                             |

### Tasks
| Command                            | Effect                                                       |
| ---------------------------------- | ------------------------------------------------------------ |
| `/done <#\|keyword>`               | Mark complete (Top 10 index or substring match)              |
| `/snooze <#\|keyword> <duration>`  | Pause until later (`3d`, `1w`, `friday`, `2026-05-15`)       |
| `/keep <#\|keyword>`               | Keep stale-flagged item alive                                |
| `/kill <#\|keyword>`               | Abandon item (different from done)                           |
| `/clearinbox [done\|killed\|all]`  | Bulk delete; default is `done`                               |

### Context
| Command                                       | Effect                                                       |
| --------------------------------------------- | ------------------------------------------------------------ |
| `/context <text> [#type] [#expires:<date>]`   | Add context. Types: `#identity` `#goal` `#constraint` `#transient` |
| `/listcontext`                                | Show active context, numbered                                |
| `/clearcontext <#\|all>`                      | Remove a single item by index, or wipe everything            |

Examples:
```
/context I value depth over breadth #identity
/context Conference deadline May 15 #constraint #expires:2026-05-15
/context Job interview Tuesday #transient
```

### State
| Command                       | Effect                                                       |
| ----------------------------- | ------------------------------------------------------------ |
| `/energy <low\|medium\|high>` | Set energy; weights quick-wins vs. deep work; decays in 12h  |
| `/review`                     | Stale items + clear expired context                          |

### Setup
| Command  | Effect                                              |
| -------- | --------------------------------------------------- |
| `/setup` | Initialize sheet schema + register scheduled jobs   |
| `/help`  | Print the full command list inside Telegram         |

---

## Configuration

Tunables in `bot/config.py`:

| Constant                 | Default | Meaning                                                  |
| ------------------------ | ------- | -------------------------------------------------------- |
| `RATE_LIMIT_SECONDS`     | 0       | Cooldown between `what's next` runs                      |
| `STALE_DAYS`             | 14      | Items older than this AND ranked few times = stale       |
| `STALE_MAX_RANKS`        | 1       | Threshold for "few times"                                |
| `TOP_N`                  | 10      | How many items in the ranked output                      |
| `DECISION_LOG_DEPTH`     | 5       | Last N runs fed back to LLM as memory                    |
| `TRANSIENT_DEFAULT_DAYS` | 7       | Default expiry for `#transient` context with no date     |
| `ENERGY_TTL_HOURS`       | 12      | How long a `/energy` setting stays in effect             |

---

## Schema

| Sheet         | Columns                                                                  |
| ------------- | ------------------------------------------------------------------------ |
| `Inbox`       | Timestamp, Content, Type, EstimatedMinutes, Status, SnoozedUntil, TimesRanked |
| `Context`     | Context Item, Type, ExpiresAt                                            |
| `Master Path` | Priority, Task, Reasoning, Movement                                      |
| `DecisionLog` | Run Timestamp, Top 10 Tasks, Energy, Done Since Last Run                 |

- `Inbox.Type` ∈ `task` (default) | `project`. For `project` items, the LLM ranks the **next concrete physical action**, not the project label.
- `Inbox.Status` ∈ `pending` | `processed` | `done` | `snoozed` | `killed`
- `Context.Type` ∈ `identity` | `goal` | `constraint` | `transient`

Edit anything directly in Sheets — Wazir reads it on the next run.

---

## Repo layout

```
wazir/
├── README.md                   ← you are here
├── improvements_checklist.md   ← design notes from the audit pass
├── pyproject.toml
└── bot/                        ← Python process — home for all organs
    ├── README.md               ← detailed setup walkthrough
    ├── main.py                 ← entry point (polling loop + JobQueue)
    ├── commands.py             ← Oracle slash commands + text/voice handlers
    ├── llm.py                  ← OpenRouter call + the "what's next" engine
    ├── sheets.py               ← Google Sheets via gspread
    ├── voice.py                ← Whisper transcription
    ├── config.py               ← loads .env, defines tunables
    ├── utils.py                ← date parsing + Markdown helpers
    ├── state.py                ← local JSON state (energy, last-run timestamp)
    ├── requirements.txt
    ├── run.bat                 ← Windows launcher
    └── .env.example
```

Future organs will land as new modules in `bot/` and register their handlers in `main.py`.

---

## Tech stack

- Python 3.10+
- [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot) (`[job-queue]` extra) — polling + scheduled jobs
- [`gspread`](https://github.com/burnash/gspread) — Google Sheets via service account
- [`requests`](https://requests.readthedocs.io/) — OpenRouter and Whisper HTTP
- [`python-dotenv`](https://github.com/theskumar/python-dotenv) — `.env` loading

LLM is provider-agnostic via OpenRouter:

| Model                                    | Notes                                |
| ---------------------------------------- | ------------------------------------ |
| `openai/gpt-oss-120b:free`               | Free, current default                |
| `meta-llama/llama-3.3-70b-instruct:free` | Free, capable, well-supported        |
| `google/gemini-2.0-flash-001`            | Paid, ~$0.10/M tokens, very fast     |
| `anthropic/claude-3.5-haiku`             | Paid, strong at structured output    |

---

## Troubleshooting

| Symptom                                    | Likely cause                                                  |
| ------------------------------------------ | ------------------------------------------------------------- |
| `Missing required env var`                 | `.env` not picked up — confirm filename is exactly `.env`     |
| `WorksheetNotFound` on launch              | Sheet not shared with service account email, or wrong sheet ID |
| `403 / 401` from Google                    | Sheets and Drive APIs not enabled in your Google Cloud project |
| `Conflict: terminated by other getUpdates` | Bot already running elsewhere, or webhook is set: visit `https://api.telegram.org/bot<TOKEN>/deleteWebhook` |
| `OpenRouter HTTP 400`                      | Model slug invalid, deprecated, or doesn't support requested features. The error body now surfaces the exact reason |
| Voice notes do nothing                     | `OPENAI_API_KEY` not set, or no credit                        |

---

## Status

**v0.1** — Oracle organ live and stable. Foundation laid; subsequent organs slot in without rearchitecture.

Single-user by design. Local-first. The "Persistent Iteration" mode (tasks stay until you explicitly close them) is intentional — combined with staleness detection, it gives you a system that won't quietly forget things you've half-committed to.

> The cost of remembering is offloaded to the system; the cost of *deciding* is offloaded to the LLM; what's left for you is just doing.

Built for myself. Open-sourced because the shape of this tool seems generally useful, and because building Wazir in public makes the next organ easier to pull off.
