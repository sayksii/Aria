"""Application-wide timezone helpers based on IANA timezone names."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

APP_TIMEZONE_SYSTEM = "system"
_app_timezone_name = APP_TIMEZONE_SYSTEM


def available_timezone_names() -> list[str]:
    """Return a compact IANA timezone list for UI selection."""
    common = [
        "UTC",
        "America/Los_Angeles",
        "America/Denver",
        "America/Chicago",
        "America/New_York",
        "America/Phoenix",
        "America/Anchorage",
        "Pacific/Honolulu",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Asia/Shanghai",
        "Asia/Tokyo",
        "Asia/Seoul",
        "Asia/Singapore",
        "Asia/Hong_Kong",
        "Asia/Taipei",
    ]
    return common


def validate_timezone_name(name: str) -> bool:
    """Validate IANA timezone name or system mode."""
    if not name or name == APP_TIMEZONE_SYSTEM:
        return True
    try:
        ZoneInfo(name)
        return True
    except Exception:
        return False


def set_app_timezone_name(name: str | None) -> str:
    """Set app timezone by IANA name; invalid values fall back to system."""
    global _app_timezone_name
    candidate = (name or APP_TIMEZONE_SYSTEM).strip()
    if not validate_timezone_name(candidate):
        candidate = APP_TIMEZONE_SYSTEM
    _app_timezone_name = candidate
    return _app_timezone_name


def get_app_timezone_name() -> str:
    """Get current app timezone name."""
    return _app_timezone_name


def now_in_app_timezone() -> datetime:
    """Get current datetime using selected app timezone."""
    if _app_timezone_name == APP_TIMEZONE_SYSTEM:
        return datetime.now().astimezone()
    return datetime.now(ZoneInfo(_app_timezone_name))


def datetime_from_timestamp(timestamp: float) -> datetime:
    """Convert UNIX timestamp to selected app timezone datetime."""
    if _app_timezone_name == APP_TIMEZONE_SYSTEM:
        return datetime.fromtimestamp(timestamp).astimezone()
    return datetime.fromtimestamp(timestamp, ZoneInfo(_app_timezone_name))
