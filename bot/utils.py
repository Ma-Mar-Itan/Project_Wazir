"""Project Oracle — date parsing + Markdown helpers."""

import re
from datetime import datetime, timedelta
from typing import Optional, Union

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def parse_duration(s: str) -> Optional[datetime]:
    """Accepts: YYYY-MM-DD, weekday name, or <n><unit> where unit ∈ h,d,w,mo."""
    if not s:
        return None
    s = str(s).strip().lower()

    # Absolute ISO date
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        try:
            return datetime.fromisoformat(s + "T23:59:59")
        except ValueError:
            return None

    # Weekday → next occurrence (always at least 1 day in the future)
    if s in WEEKDAYS:
        target = WEEKDAYS.index(s)
        now = datetime.now()
        diff = (target - now.weekday()) % 7 or 7
        return (now + timedelta(days=diff)).replace(hour=23, minute=59, second=59, microsecond=0)

    # Relative: <n><unit>
    m = re.match(r"^(\d+)(h|d|w|mo)$", s)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        now = datetime.now()
        if unit == "h":  return now + timedelta(hours=n)
        if unit == "d":  return now + timedelta(days=n)
        if unit == "w":  return now + timedelta(weeks=n)
        if unit == "mo": return now + timedelta(days=30 * n)
    return None


def format_date(d: Union[datetime, str, None]) -> str:
    if not d:
        return ""
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d)
        except ValueError:
            return d
    return d.strftime("%Y-%m-%d")


def escape_markdown(s: Union[str, None]) -> str:
    """Escape Telegram (legacy) Markdown special chars."""
    if not s:
        return ""
    return re.sub(r"([_*`\[\]])", r"\\\1", str(s))
