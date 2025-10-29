"""Time calculation tools for the AI agent."""

from __future__ import annotations

import logging
from typing import Any, Dict

from .tools import Tool, ToolSpec
from ..utils.current_time import (
    get_current_utc_time,
    get_current_utc_plus_minutes,
    get_current_utc_plus_hours,
    get_current_utc_plus_days,
    get_current_utc_plus_weeks,
    get_time_at_hour_minute,
    get_time_tomorrow_at_hour_minute,
)

logger = logging.getLogger(__name__)


def create_time_tools() -> list[Tool]:
    """Create time calculation tools for the agent."""
    
    async def handle_get_current_utc_time(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current UTC time in ISO format."""
        try:
            current_time = get_current_utc_time()
            return {
                "success": True,
                "current_utc_time": current_time,
                "message": f"Current UTC time: {current_time}",
            }
        except Exception as e:
            logger.error(f"Failed to get current UTC time: {e}")
            return {
                "success": False,
                "error": f"Failed to get current UTC time: {str(e)}",
            }

    async def handle_get_current_utc_plus_minutes(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current UTC time plus specified minutes."""
        try:
            minutes = args.get("minutes", 0)
            if not isinstance(minutes, int) or minutes < 0:
                return {
                    "success": False,
                    "error": "Minutes must be a non-negative integer",
                }
            
            future_time = get_current_utc_plus_minutes(minutes)
            return {
                "success": True,
                "future_time": future_time,
                "message": f"UTC time + {minutes} minutes: {future_time}",
            }
        except Exception as e:
            logger.error(f"Failed to calculate future time: {e}")
            return {
                "success": False,
                "error": f"Failed to calculate future time: {str(e)}",
            }

    async def handle_get_current_utc_plus_hours(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current UTC time plus specified hours."""
        try:
            hours = args.get("hours", 0)
            if not isinstance(hours, int) or hours < 0:
                return {
                    "success": False,
                    "error": "Hours must be a non-negative integer",
                }
            
            future_time = get_current_utc_plus_hours(hours)
            return {
                "success": True,
                "future_time": future_time,
                "message": f"UTC time + {hours} hours: {future_time}",
            }
        except Exception as e:
            logger.error(f"Failed to calculate future time: {e}")
            return {
                "success": False,
                "error": f"Failed to calculate future time: {str(e)}",
            }

    async def handle_get_current_utc_plus_days(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current UTC time plus specified days."""
        try:
            days = args.get("days", 0)
            if not isinstance(days, int) or days < 0:
                return {
                    "success": False,
                    "error": "Days must be a non-negative integer",
                }
            
            future_time = get_current_utc_plus_days(days)
            return {
                "success": True,
                "future_time": future_time,
                "message": f"UTC time + {days} days: {future_time}",
            }
        except Exception as e:
            logger.error(f"Failed to calculate future time: {e}")
            return {
                "success": False,
                "error": f"Failed to calculate future time: {str(e)}",
            }

    async def handle_get_time_at_hour_minute(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get time today at specified hour:minute, or tomorrow if time has passed."""
        try:
            hour = args.get("hour", 0)
            minute = args.get("minute", 0)
            
            if not isinstance(hour, int) or not 0 <= hour <= 23:
                return {
                    "success": False,
                    "error": "Hour must be an integer between 0 and 23",
                }
            
            if not isinstance(minute, int) or not 0 <= minute <= 59:
                return {
                    "success": False,
                    "error": "Minute must be an integer between 0 and 59",
                }
            
            target_time = get_time_at_hour_minute(hour, minute)
            return {
                "success": True,
                "target_time": target_time,
                "message": f"Time at {hour:02d}:{minute:02d}: {target_time}",
            }
        except Exception as e:
            logger.error(f"Failed to calculate target time: {e}")
            return {
                "success": False,
                "error": f"Failed to calculate target time: {str(e)}",
            }

    async def handle_get_time_tomorrow_at_hour_minute(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get time tomorrow at specified hour:minute."""
        try:
            hour = args.get("hour", 0)
            minute = args.get("minute", 0)
            
            if not isinstance(hour, int) or not 0 <= hour <= 23:
                return {
                    "success": False,
                    "error": "Hour must be an integer between 0 and 23",
                }
            
            if not isinstance(minute, int) or not 0 <= minute <= 59:
                return {
                    "success": False,
                    "error": "Minute must be an integer between 0 and 59",
                }
            
            target_time = get_time_tomorrow_at_hour_minute(hour, minute)
            return {
                "success": True,
                "target_time": target_time,
                "message": f"Tomorrow at {hour:02d}:{minute:02d}: {target_time}",
            }
        except Exception as e:
            logger.error(f"Failed to calculate tomorrow time: {e}")
            return {
                "success": False,
                "error": f"Failed to calculate tomorrow time: {str(e)}",
            }

    return [
        Tool(
            spec=ToolSpec(
                name="get_current_utc_time",
                description="Get current UTC time in ISO format",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
                namespace="time",
                version="1.0.0",
            ),
            handler=handle_get_current_utc_time,
        ),
        Tool(
            spec=ToolSpec(
                name="get_current_utc_plus_minutes",
                description="Get current UTC time plus specified minutes",
                input_schema={
                    "type": "object",
                    "properties": {
                        "minutes": {
                            "type": "integer",
                            "description": "Number of minutes to add",
                            "minimum": 0,
                        },
                    },
                    "required": ["minutes"],
                },
                namespace="time",
                version="1.0.0",
            ),
            handler=handle_get_current_utc_plus_minutes,
        ),
        Tool(
            spec=ToolSpec(
                name="get_current_utc_plus_hours",
                description="Get current UTC time plus specified hours",
                input_schema={
                    "type": "object",
                    "properties": {
                        "hours": {
                            "type": "integer",
                            "description": "Number of hours to add",
                            "minimum": 0,
                        },
                    },
                    "required": ["hours"],
                },
                namespace="time",
                version="1.0.0",
            ),
            handler=handle_get_current_utc_plus_hours,
        ),
        Tool(
            spec=ToolSpec(
                name="get_current_utc_plus_days",
                description="Get current UTC time plus specified days",
                input_schema={
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to add",
                            "minimum": 0,
                        },
                    },
                    "required": ["days"],
                },
                namespace="time",
                version="1.0.0",
            ),
            handler=handle_get_current_utc_plus_days,
        ),
        Tool(
            spec=ToolSpec(
                name="get_time_at_hour_minute",
                description="Get time today at specified hour:minute, or tomorrow if time has passed",
                input_schema={
                    "type": "object",
                    "properties": {
                        "hour": {
                            "type": "integer",
                            "description": "Hour (0-23)",
                            "minimum": 0,
                            "maximum": 23,
                        },
                        "minute": {
                            "type": "integer",
                            "description": "Minute (0-59)",
                            "minimum": 0,
                            "maximum": 59,
                        },
                    },
                    "required": ["hour"],
                },
                namespace="time",
                version="1.0.0",
            ),
            handler=handle_get_time_at_hour_minute,
        ),
        Tool(
            spec=ToolSpec(
                name="get_time_tomorrow_at_hour_minute",
                description="Get time tomorrow at specified hour:minute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "hour": {
                            "type": "integer",
                            "description": "Hour (0-23)",
                            "minimum": 0,
                            "maximum": 23,
                        },
                        "minute": {
                            "type": "integer",
                            "description": "Minute (0-59)",
                            "minimum": 0,
                            "maximum": 59,
                        },
                    },
                    "required": ["hour"],
                },
                namespace="time",
                version="1.0.0",
            ),
            handler=handle_get_time_tomorrow_at_hour_minute,
        ),
    ]


