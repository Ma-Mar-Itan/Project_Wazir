# Wazir

A task-ranking engine that actually knows what I care about. No SaaS, no notifications, just a direct line to my priorities.

"Wazir" is Arabic for vizier — the advisor who handles the day-to-day so the principal can focus elsewhere. That's roughly what I want this to grow into.

This is **v0.1**. Today it does one thing — re-rank my open tasks on demand against my current life context. Other modules are planned (calendar, daily briefing, email triage), but I'm not shipping them until I've actually used the foundation for a while.

---

## Why this exists

I got tired of to-do lists that just grow until I stop looking at them.

What I wanted instead: a thing I can dump every passing thought into, and that will, when I ask, tell me the *one* thing I should be doing right now — given that I want to start a robotics company in 10 years, that I have a project due Monday, that the exam I was dreading just got cancelled, that I'm tired today, and that I keep saying I'll learn time series analysis but somehow never do.

Standard apps treat priorities as static. Mine aren't. So Wazir treats `what's next` as a recomputation against current state, not a lookup against a fixed list. Every ask hits the LLM with my full context and produces a ranked Top 10 with reasoning, plus arrows showing what shifted since last time.

---

## What it looks like

Normal day:

```
me   > Read the new robotics book
bot  > 📥 Logged. (8 active)

me   > /context exam on Monday cancelled #transient
bot  > 📌 Added [transient]: exam on Monday cancelled (expires 2026-05-02)

me   > what's next

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
       Reply `/keep <keyword>` or `/kill <keyword>`.
```

Tired day:

```
me   > /energy low
bot  > 🔋 Energy set to *low* (decays in 12h)

me   > what's next

bot  > _Low energy — surfacing quick-wins that don't need a full brain._
       
       *Top 3*
       1. ↑5 *Reply to the center email*
          _15 min, low-friction; clears one open loop._
       2. ↑2 *File expense receipts*
          _Mechanical; doesn't compete for focus._
       3. ↓1 *Learn time series analysis*
          _Demoted: needs deep work, not today's job._
```

Arrows (`↑3`, `↓2`, `NEW`, `=`) show movement since the previous run. The italic line at the top is the LLM's one-sentence summary of what's actually driving today's order. The "stale" callout flags items I've been carrying for weeks that never make Top 10 — usually things I'm avoiding for a reason.

---

## What it actually does

- **Capture by text or voice.** Send anything to the bot. Voice notes go through Whisper if you've configured it. Lands in the Inbox tab.
- **Type `what's next`.** Re-rank on demand. No slash, no menu, no clicks.
- **Tag context with type and expiry.** `#identity`, `#goal`, `#constraint`, or `#transient`. `#expires:2026-05-15` or `#expires:friday`. Transient items auto-clear.
- **Mark things done from chat.** `/done 1` for the Top 10 index, `/done python` for substring match. No opening Sheets to flip a checkbox.
- **Snooze.** `/snooze 3 1w` parks task #3 for a week.
- **Energy-aware.** `/energy low|medium|high` shifts the ranking toward quick-wins or deep work for the next 12 hours.
- **Stale-item flagging.** Things older than 14 days that have appeared in past Top 10s but never been done get surfaced. Reply `/keep` or `/kill` to resolve.
- **Memory across runs.** The LLM sees the last 5 runs' Top 3 plus what got closed since, so it can notice patterns ("this keeps ranking high but you keep skipping it").
- **Quiet by default.** Only sends messages when you message it first. Two exceptions: a daily 02:00 sweep that pings you *only* if it cleared expired context, and a Friday 17:00 stale-items review.

---

## Modules (planned)

The codebase is set up so each capability is a separate module that registers handlers on startup. Adding the next one means dropping a new file in `bot/` and wiring it in `main.py`.

| Module           | Job                                                                                | Status     |
| ---------------- | ---------------------------------------------------------------------------------- | ---------- |
| **Oracle**       | Re-ranks open tasks against context, energy, decision history                      | Live       |
| **Almanac**      | Pulls in Google Calendar so ranking respects what's actually scheduled             | Next       |
| **Herald**       | Morning briefing — what shifted overnight, what's due, anything I'm tracking       | Soon       |
| **Scribe**       | Drafts and triages email; never sends without explicit approval                    | Soon       |
| **Cartographer** | Long-term memory; surfaces "you mentioned X two weeks ago, follow up?"             | Planned    |
| **Steward**      | File management — "organize my Downloads," "find the contract from March"          | Planned    |
| **Watchman**     | Sleep / focus signals; intervenes when context says rest                           | Planned    |

I'll only build these as I actually need them. Speculative features rot.

---

## Design choices

A few that hold across every module I add:

1. **Local.** Runs on my PC. No cloud bill, no public URL, no login wall to my own life. Bot polls Telegram; reads/writes my own Google Sheet via a service account.
2. **Telegram as the universal interface.** Typing > clicking, voice > typing, and Telegram works on every device. One chat fronts everything.
3. **Sheets as the persistent body.** Auditable, hand-editable, no dashboard to build. Anything Wazir thinks is in a tab I can open and fix manually.
4. **Provider-agnostic LLM.** Via OpenRouter, so I can swap models without code changes. Free models work; paid ones cost cents per call.
5. **Persistent by default.** Tasks and context stay until I explicitly close them. Combined with staleness detection, the system can't quietly forget things I've half-committed to.

---

## Architecture

```
┌─────────────────┐   text/voice     ┌──────────────────┐
│  Telegram bot   │ ───────────────► │  Local Python    │
│   (Senses)      │                  │   (Modules)      │
└─────────────────┘ ◄─── reply ───── └────────┬─────────┘
                                              │
                              gspread ────────┼──── requests
                                              ▼
                              ┌─────────────────┐  ┌─────────────┐
                              │  Google Sheets  │  │ OpenRouter  │
                              │     (Body)      │  │   (Brain)   │
                              └─────────────────┘  └─────────────┘
```

Oracle owns four sheet tabs: `Inbox`, `Context`, `Master Path`, `DecisionLog`. Future modules will add their own.

---

## Reality check on setup

This isn't a one-click install. You need:

- A Telegram bot token (from @BotFather)
- Your Telegram chat ID (one URL fetch, takes 30 seconds)
- An OpenRouter API key (free tier is fine)
- A Google Cloud service account with Sheets + Drive APIs enabled, and you need to share your sheet with the service account's email
- Python 3.10+ on PATH
- Optionally an OpenAI key if you want voice transcription

When it breaks during setup, it's almost always one of:

- The `.env` file isn't actually named `.env` (Windows likes to add `.txt`)
- The Sheets/Drive APIs aren't enabled in your Google Cloud project
- You forgot to share the sheet with the service account email
- Your OpenRouter balance is $0 and the model you picked isn't free
- The model slug you picked is deprecated — preview-tier OpenRouter models rotate

Fix any of those and it runs indefinitely. The polling bot will sit in the background using essentially no resources.

---

## Setup

### 1. Credentials

| What                   | Where                                                                   |
| ---------------------- | ----------------------------------------------------------------------- |
| Telegram bot token     | DM [@BotFather](https://t.me/BotFather) → `/newbot`                     |
| Telegram chat ID       | Send your bot any message, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat.id` |
| OpenRouter API key     | [openrouter.ai/keys](https://openrouter.ai/keys)                        |
| Google service account | [console.cloud.google.com](https://console.cloud.google.com) → enable Sheets + Drive APIs → IAM → Service accounts → Create → Keys → JSON → save as `credentials.json` |

Then share your Google Sheet with the service account email (Editor access).

### 2. Configure

```bash
git clone https://github.com/<you>/wazir.git
cd wazir/bot
cp .env.example .env
# edit .env with your values
# put credentials.json in this folder
```

`.env`:

```ini
TELEGRAM_BOT_TOKEN=123456:ABC-...
TELEGRAM_CHAT_ID=123456789
OPENROUTER_API_KEY=sk-or-v1-...
GOOGLE_SHEETS_ID=1aBc...    # the long string in your sheet's URL between /d/ and /edit
GOOGLE_CREDENTIALS_PATH=credentials.json
OPENROUTER_MODEL=openai/gpt-oss-120b:free
OPENAI_API_KEY=             # optional, only for voice
```

### 3. Run

**Windows:** double-click `bot/run.bat`. First run builds the venv (~1 min); subsequent runs start instantly.

**macOS / Linux:**
```bash
cd bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 4. Initialize the sheet

Send `/setup` to the bot. Adds missing columns and creates the `DecisionLog` tab.

To run on Windows boot: `Win+R` → `shell:startup` → drop a shortcut to `run.bat` in there.

---

## Commands

### Capture
| Action              | How                                            |
| ------------------- | ---------------------------------------------- |
| Log a thought       | Send any text                                  |
| Log a voice thought | Send a voice note (needs `OPENAI_API_KEY`)     |
| Re-rank now         | Type `what's next`                             |

### Tasks
| Command                            | Effect                                                       |
| ---------------------------------- | ------------------------------------------------------------ |
| `/done <#\|keyword>`               | Mark complete                                                |
| `/snooze <#\|keyword> <duration>`  | Pause until later (`3d`, `1w`, `friday`, `2026-05-15`)       |
| `/keep <#\|keyword>`               | Keep stale-flagged item alive                                |
| `/kill <#\|keyword>`               | Abandon (different from done)                                |
| `/clearinbox [done\|killed\|all]`  | Bulk delete; default `done`                                  |

### Context
| Command                                       | Effect                                                       |
| --------------------------------------------- | ------------------------------------------------------------ |
| `/context <text> [#type] [#expires:<date>]`   | Add. Types: `#identity` `#goal` `#constraint` `#transient`   |
| `/listcontext`                                | Show active context                                          |
| `/clearcontext <#\|all>`                      | Remove single item or wipe                                   |

### State
| Command                       | Effect                                                  |
| ----------------------------- | ------------------------------------------------------- |
| `/energy <low\|medium\|high>` | Set energy; weights ranking; decays in 12h              |
| `/review`                     | Stale items + clear expired context                     |

### Setup
| Command  | Effect                                              |
| -------- | --------------------------------------------------- |
| `/setup` | Initialize sheet schema + register scheduled jobs   |
| `/help`  | Print the command list inside Telegram              |

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

`Inbox.Type`: `task` (default) or `project`. For `project`, the LLM ranks the next concrete physical action, not the project label itself.
`Inbox.Status`: `pending` | `processed` | `done` | `snoozed` | `killed`.
`Context.Type`: `identity` | `goal` | `constraint` | `transient`.

You can edit anything in Sheets directly. Bot picks it up on the next run.

---

## Repo layout

```
wazir/
├── README.md
├── improvements_checklist.md   ← design notes from the audit pass
├── pyproject.toml
└── bot/
    ├── README.md               ← detailed setup walkthrough
    ├── main.py                 ← entry point (polling + scheduled jobs)
    ├── commands.py             ← Oracle slash commands + text/voice handlers
    ├── llm.py                  ← OpenRouter call + the "what's next" engine
    ├── sheets.py               ← Google Sheets via gspread
    ├── voice.py                ← Whisper transcription
    ├── config.py               ← .env loader, tunables
    ├── utils.py                ← date parsing + Markdown helpers
    ├── state.py                ← local JSON state
    ├── requirements.txt
    ├── run.bat                 ← Windows launcher
    └── .env.example
```

---

## Tech stack

- Python 3.10+
- [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot) (`[job-queue]` extra)
- [`gspread`](https://github.com/burnash/gspread)
- [`requests`](https://requests.readthedocs.io/)
- [`python-dotenv`](https://github.com/theskumar/python-dotenv)

LLM is provider-agnostic via OpenRouter:

| Model                                    | Notes                                |
| ---------------------------------------- | ------------------------------------ |
| `openai/gpt-oss-120b:free`               | Free; current default                |
| `meta-llama/llama-3.3-70b-instruct:free` | Free; capable; well-supported        |
| `google/gemini-2.0-flash-001`            | Paid; ~$0.10/M tokens; very fast     |
| `anthropic/claude-3.5-haiku`             | Paid; strong at structured output    |

---

## Status

v0.1, single-user, runs while my PC is on. Built for myself. Open-sourced because the shape is generally useful and because building in public makes the next module easier to pull off.
