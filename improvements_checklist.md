# Project Oracle — Improvements Checklist

Each item is tagged with what's **manual** (sheet edits, API keys, decisions only you can make) and what **I can do** (code, prompts, schemas, logic).

---

## 1. Capture-to-completion loop (highest daily impact)

- [ ] **`/done [index|keyword]` Telegram command**
  - Manual: nothing
  - I can do: write the Apps Script + bot handler that flips status to `done`

- [ ] **`/snooze [index] [duration]` Telegram command**
  - Manual: add `SnoozedUntil` column to the Inbox tab
  - I can do: write the command handler + update `optimize_path` to skip snoozed items until their date

---

## 2. Persistent Iteration / staleness

- [ ] **Soft staleness detection** (surface items old + never-ranked)
  - Manual: nothing
  - I can do: write detection logic + prompt template that asks "still relevant? `/keep` or `/kill`"

- [ ] **Freshness/decay weighting in the LLM prompt**
  - Manual: nothing
  - I can do: add age scoring to each item before injection, update prompt to consider it

- [ ] **`/keep` and `/kill` quick-action commands**
  - Manual: nothing
  - I can do: write handlers

---

## 3. Context tab structure

- [ ] **Add `Type` column to Context tab** (`identity` / `goal` / `constraint` / `transient`)
  - Manual: add column header in Google Sheets, classify existing items once
  - I can do: update `/context` command to prompt for type, update LLM prompt to weight by type

- [ ] **Add `ExpiresAt` column to Context tab**
  - Manual: add column header
  - I can do: write auto-cleanup trigger + update `/context` to capture expiration ("/context exam Friday — expires 2026-05-01")

- [ ] **Auto-clear expired transient context** (daily sweep)
  - Manual: nothing
  - I can do: write a scheduled Apps Script trigger

---

## 4. Output transparency

- [ ] **Show diff between `what's next` runs** (arrows for movement + one-line "what changed")
  - Manual: nothing
  - I can do: write diff logic against the previous Master Path snapshot, format in Markdown

- [ ] **Add a global "weighting summary" line** at the top of each output
  - Manual: nothing
  - I can do: extend the LLM prompt to return aggregate reasoning ("today's top driver: deadline pressure")

---

## 5. Time & energy awareness

- [ ] **Add `EstimatedMinutes` column to Inbox tab**
  - Manual: add column header (optionally backfill existing items)
  - I can do: update prompt to use it; LLM can infer when blank

- [ ] **`/energy [low|medium|high]` command** (sets a transient context flag)
  - Manual: nothing
  - I can do: write handler + update prompt to weight quick-wins vs deep-work accordingly

---

## 6. Project vs task distinction

- [ ] **Add `ItemType` column to Inbox** (`task` / `project`)
  - Manual: add column header, classify big items as projects (one-time pass)
  - I can do: update prompt to rank concrete next-actions, not project labels

- [ ] **`NextAction` subfield (or sub-tab) for projects**
  - Manual: pick a schema (extra column vs. separate tab) — design preference call
  - I can do: write the data model + bot capture flow once you choose

---

## 7. Smaller but real wins

- [ ] **Voice-note ingestion via Whisper**
  - Manual: API key for Whisper (OpenAI or OpenRouter), add env var to your bot host
  - I can do: write the audio handler + transcription → Inbox pipeline

- [ ] **Weekly review nudge** (Friday afternoon ping)
  - Manual: nothing
  - I can do: scheduled Apps Script trigger + review prompt that surfaces stale items

- [ ] **Rate-limit `what's next`** (5-minute cooldown)
  - Manual: nothing
  - I can do: simple timestamp check in the bot

---

## 8. Memory across runs (highest ceiling, biggest lift)

- [ ] **Decision log** — record each `what's next` Top 10 + what got marked done within 24h
  - Manual: add a `DecisionLog` tab to the sheet
  - I can do: write the logging logic + feed a summarized log back as additional context to future runs ("user has consistently chosen X over Y when both ranked highly")

---

## Suggested order

1. `/done` command — kills the worst friction point in one move
2. Context `Type` + `ExpiresAt` columns — biggest ranking-quality win
3. Output diff — makes the system feel alive
4. `/snooze` + soft staleness — keeps the inbox honest
5. Everything else, in any order

---

## What's purely on you (no code I can write)

- Editing the Google Sheet schema (adding columns, headers)
- Classifying your existing context items into types (one-time cleanup)
- API keys / env vars (Whisper, OpenRouter, etc.)
- Architectural decisions where there's a real trade-off (e.g., NextAction as column vs. tab)
- Actually marking items done in the existing sheet (until `/done` ships)
