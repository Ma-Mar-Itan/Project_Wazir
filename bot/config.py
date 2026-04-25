"""Project Oracle — configuration. All secrets live in .env."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _required(key: str) -> str:
    v = os.environ.get(key, "").strip()
    if not v:
        raise RuntimeError(f"Missing required env var: {key} (set it in .env)")
    return v


@dataclass(frozen=True)
class _Config:
    # --- Required ---
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: int
    OPENROUTER_API_KEY: str
    GOOGLE_SHEETS_ID: str
    GOOGLE_CREDENTIALS_PATH: str

    # --- Optional ---
    OPENAI_API_KEY: str
    OPENROUTER_MODEL: str

    # --- Tunables ---
    RATE_LIMIT_SECONDS: int = 0
    STALE_DAYS: int = 14
    STALE_MAX_RANKS: int = 1
    TOP_N: int = 10
    DECISION_LOG_DEPTH: int = 5
    TRANSIENT_DEFAULT_DAYS: int = 7
    ENERGY_TTL_HOURS: int = 12


def _load_config() -> _Config:
    return _Config(
        TELEGRAM_BOT_TOKEN=_required("TELEGRAM_BOT_TOKEN"),
        TELEGRAM_CHAT_ID=int(_required("TELEGRAM_CHAT_ID")),
        OPENROUTER_API_KEY=_required("OPENROUTER_API_KEY"),
        GOOGLE_SHEETS_ID=_required("GOOGLE_SHEETS_ID"),
        GOOGLE_CREDENTIALS_PATH=os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json"),
        OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY", "").strip(),
        OPENROUTER_MODEL=os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.5").strip(),
    )


CONFIG = _load_config()


# --- Sheet names ---
class Sheets:
    INBOX = "Inbox"
    CONTEXT = "Context"
    MASTER_PATH = "Master Path"
    DECISION_LOG = "DecisionLog"


# --- Status values for Inbox.Status ---
class Status:
    PENDING = "pending"
    PROCESSED = "processed"
    DONE = "done"
    SNOOZED = "snoozed"
    KILLED = "killed"


# --- Type values for Context.Type ---
class CtxType:
    IDENTITY = "identity"
    GOAL = "goal"
    CONSTRAINT = "constraint"
    TRANSIENT = "transient"
    ALL = (IDENTITY, GOAL, CONSTRAINT, TRANSIENT)
