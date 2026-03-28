"""Timezone utilities — all timestamps in Swedish local time."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

SE_TZ = ZoneInfo("Europe/Stockholm")


def now() -> datetime:
    """Current time in Swedish timezone."""
    return datetime.now(SE_TZ)


def today() -> date:
    """Current date in Swedish timezone."""
    return datetime.now(SE_TZ).date()
