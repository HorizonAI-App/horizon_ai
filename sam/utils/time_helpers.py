"""Time helper utilities for scheduling and time calculations."""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any


def calculate_execution_time(time_expression: str) -> Optional[str]:
    """
    Calculate execution time from natural language expressions.
    
    Args:
        time_expression: Natural language time expression like "in 3 minutes", "at 9:00 AM", etc.
        
    Returns:
        ISO format timestamp string or None if parsing fails
    """
    if not time_expression:
        return None
    
    time_expression = time_expression.lower().strip()
    now = datetime.now(timezone.utc)
    
    # Handle relative time expressions
    relative_time = _parse_relative_time(time_expression, now)
    if relative_time:
        return relative_time.isoformat()
    
    # Handle absolute time expressions
    absolute_time = _parse_absolute_time(time_expression, now)
    if absolute_time:
        return absolute_time.isoformat()
    
    # Handle specific date/time expressions
    specific_time = _parse_specific_time(time_expression, now)
    if specific_time:
        return specific_time.isoformat()
    
    return None


def _parse_relative_time(time_str: str, base_time: datetime) -> Optional[datetime]:
    """Parse relative time expressions like 'in 3 minutes', 'in 1 hour', etc."""
    
    # Pattern for "in X minutes/hours/days/weeks"
    relative_pattern = r'in\s+(\d+)\s+(minute|hour|day|week)s?'
    match = re.search(relative_pattern, time_str)
    
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        
        if unit == 'minute':
            return base_time + timedelta(minutes=amount)
        elif unit == 'hour':
            return base_time + timedelta(hours=amount)
        elif unit == 'day':
            return base_time + timedelta(days=amount)
        elif unit == 'week':
            return base_time + timedelta(weeks=amount)
    
    return None


def _parse_absolute_time(time_str: str, base_time: datetime) -> Optional[datetime]:
    """Parse absolute time expressions like 'at 9:00 AM', 'at 15:30', etc."""
    
    # Pattern for "at HH:MM AM/PM" or "at HH:MM"
    time_patterns = [
        r'at\s+(\d{1,2}):(\d{2})\s*(am|pm)',
        r'at\s+(\d{1,2}):(\d{2})',
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            ampm = match.group(3) if len(match.groups()) > 2 else None
            
            # Convert to 24-hour format
            if ampm:
                if ampm == 'pm' and hour != 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
            
            # Create target time for today
            target_time = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time has passed today, schedule for tomorrow
            if target_time <= base_time:
                target_time += timedelta(days=1)
            
            return target_time
    
    return None


def _parse_specific_time(time_str: str, base_time: datetime) -> Optional[datetime]:
    """Parse specific date/time expressions like 'tomorrow at 10:00', 'next Monday', etc."""
    
    # Handle "tomorrow at X:XX"
    tomorrow_pattern = r'tomorrow\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)?'
    match = re.search(tomorrow_pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = match.group(3)
        
        # Convert to 24-hour format
        if ampm:
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
        
        tomorrow = base_time + timedelta(days=1)
        return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Handle "next [day] at X:XX"
    next_day_pattern = r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)?'
    match = re.search(next_day_pattern, time_str)
    if match:
        day_name = match.group(1).lower()
        hour = int(match.group(2))
        minute = int(match.group(3))
        ampm = match.group(4)
        
        # Convert to 24-hour format
        if ampm:
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
        
        # Map day names to numbers (Monday = 0, Sunday = 6)
        day_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        target_day = day_map[day_name]
        
        # Calculate days until next occurrence
        current_day = base_time.weekday()
        days_ahead = target_day - current_day
        if days_ahead <= 0:  # Target day already passed this week
            days_ahead += 7
        
        target_date = base_time + timedelta(days=days_ahead)
        return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    return None


def format_execution_time(iso_timestamp: str) -> str:
    """Format ISO timestamp for user-friendly display."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return iso_timestamp


def get_time_until_execution(iso_timestamp: str) -> Optional[str]:
    """Get human-readable time until execution."""
    try:
        execution_time = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if execution_time <= now:
            return "Past due"
        
        delta = execution_time - now
        
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} and {delta.seconds // 3600} hour{'s' if delta.seconds // 3600 > 1 else ''}"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            return f"{hours} hour{'s' if hours > 1 else ''} and {minutes} minute{'s' if minutes > 1 else ''}"
        else:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''}"
    except:
        return None


