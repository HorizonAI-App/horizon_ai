"""Current time utilities for accurate time calculations."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta


def get_current_utc_time() -> str:
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def get_current_utc_plus_minutes(minutes: int) -> str:
    """Get current UTC time plus specified minutes in ISO format."""
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def get_current_utc_plus_hours(hours: int) -> str:
    """Get current UTC time plus specified hours in ISO format."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def get_current_utc_plus_days(days: int) -> str:
    """Get current UTC time plus specified days in ISO format."""
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def get_current_utc_plus_weeks(weeks: int) -> str:
    """Get current UTC time plus specified weeks in ISO format."""
    return (datetime.now(timezone.utc) + timedelta(weeks=weeks)).isoformat()


def get_time_at_hour_minute(hour: int, minute: int = 0) -> str:
    """Get time today at specified hour:minute, or tomorrow if time has passed."""
    now = datetime.now(timezone.utc)
    target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If time has passed today, schedule for tomorrow
    if target_time <= now:
        target_time += timedelta(days=1)
    
    return target_time.isoformat()


def get_time_tomorrow_at_hour_minute(hour: int, minute: int = 0) -> str:
    """Get time tomorrow at specified hour:minute."""
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


