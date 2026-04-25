"""Project Oracle — local state (energy, last-run timestamp). JSON file."""

import json
import os
import time
from typing import Any, Optional

from config import CONFIG

STATE_FILE = "state.json"


def _load() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def get_property(key: str, default: Any = None) -> Any:
    return _load().get(key, default)


def set_property(key: str, value: Any) -> None:
    data = _load()
    data[key] = value
    _save(data)


def get_current_energy() -> Optional[str]:
    set_at = get_property("CURRENT_ENERGY_SET_AT")
    if not set_at:
        return None
    try:
        set_at = float(set_at)
    except (ValueError, TypeError):
        return None
    age_hrs = (time.time() - set_at) / 3600
    if age_hrs > CONFIG.ENERGY_TTL_HOURS:
        return None
    return get_property("CURRENT_ENERGY")
