#!/usr/bin/env python3
"""Agent scheduler tools for automatic transaction execution."""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field

from ..core.tools import Tool, ToolSpec
from ..core.scheduler import get_scheduler_manager
from ..utils.error_handling import handle_errors

logger = logging.getLogger(__name__)

class ScheduleTaskInput(BaseModel):
    """Input model for scheduling a task."""
    task_type: str = Field(..., description="Type of task: 'swap', 'transfer_sol', 'buy_token', 'sell_token'")
    execute_at: str = Field(..., description="When to execute the task (ISO format or relative time like 'in 5 minutes')")
    task_data: Dict[str, Any] = Field(..., description="Task-specific data (addresses, amounts, etc.)")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Optional execution conditions")

class GetScheduledTasksInput(BaseModel):
    """Input model for getting scheduled tasks."""
    status: Optional[str] = Field(None, description="Filter by status: 'pending', 'executing', 'completed', 'failed', 'cancelled'")

class CancelTaskInput(BaseModel):
    """Input model for cancelling a task."""
    task_id: str = Field(..., description="ID of the task to cancel")

@handle_errors("agent_scheduler")
async def schedule_task_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Schedule a task for automatic execution."""
    try:
        # Get user context from agent
        user_id = "default"
        session_id = "default"
        
        # Try to get from agent context if available
        if hasattr(schedule_task_handler, '_agent') and schedule_task_handler._agent:
            context = getattr(schedule_task_handler._agent, '_context', None)
            if context:
                user_id = getattr(context, 'user_id', user_id)
                session_id = getattr(context, 'session_id', session_id)
        
        # Parse execute_at time
        execute_at_str = args["execute_at"]
        execute_at = _parse_execute_time(execute_at_str)
        
        # Get scheduler and schedule the task
        from ..core.scheduler import TransactionType
        scheduler = await get_scheduler_manager()
        result = await scheduler.schedule_transaction(
            user_id=user_id,
            session_id=session_id,
            transaction_type=TransactionType(args["task_type"]),
            schedule_time=execute_at.isoformat(),
            transaction_data=args["task_data"],
            conditions=args.get("conditions")
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error scheduling task: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@handle_errors("agent_scheduler")
async def get_scheduled_tasks_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get scheduled tasks for the current user."""
    try:
        # Get user context from agent
        user_id = "default"
        
        # Try to get from agent context if available
        if hasattr(get_scheduled_tasks_handler, '_agent') and get_scheduled_tasks_handler._agent:
            context = getattr(get_scheduled_tasks_handler._agent, '_context', None)
            if context:
                user_id = getattr(context, 'user_id', user_id)
        
        # Get scheduler and fetch tasks
        scheduler = await get_scheduler_manager()
        tasks = await scheduler.get_scheduled_transactions(
            user_id=user_id,
            status=args.get("status")
        )
        
        return {
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }
        
    except Exception as e:
        logger.error(f"Error getting scheduled tasks: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@handle_errors("agent_scheduler")
async def cancel_task_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Cancel a scheduled task."""
    try:
        # Get user context from agent
        user_id = "default"
        
        # Try to get from agent context if available
        if hasattr(cancel_task_handler, '_agent') and cancel_task_handler._agent:
            context = getattr(cancel_task_handler._agent, '_context', None)
            if context:
                user_id = getattr(context, 'user_id', user_id)
        
        # Get scheduler and cancel the task
        scheduler = await get_scheduler_manager()
        result = await scheduler.cancel_transaction(
            transaction_id=int(args["task_id"]),
            user_id=user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def _parse_execute_time(time_str: str) -> datetime:
    """Parse execute time from string."""
    time_str = time_str.strip().lower()
    now = datetime.now()
    
    # Handle relative times
    if time_str.startswith("in "):
        # Parse "in X minutes/hours/days"
        parts = time_str[3:].split()
        if len(parts) >= 2:
            amount = int(parts[0])
            unit = parts[1]
            
            if unit.startswith("minute"):
                return now + timedelta(minutes=amount)
            elif unit.startswith("hour"):
                return now + timedelta(hours=amount)
            elif unit.startswith("day"):
                return now + timedelta(days=amount)
            elif unit.startswith("week"):
                return now + timedelta(weeks=amount)
    
    # Handle absolute times
    try:
        # Try ISO format first
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except ValueError:
        # Try common formats
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M"]:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
                
    raise ValueError(f"Unable to parse execute time: {time_str}")

# Wrapper functions to capture agent instance
def schedule_task_wrapper(agent):
    def wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
        schedule_task_handler._agent = agent
        return schedule_task_handler(args)
    return wrapper

def get_scheduled_tasks_wrapper(agent):
    def wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
        get_scheduled_tasks_handler._agent = agent
        return get_scheduled_tasks_handler(args)
    return wrapper

def cancel_task_wrapper(agent):
    def wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
        cancel_task_handler._agent = agent
        return cancel_task_handler(args)
    return wrapper

def register(registry, agent=None):
    """Register agent scheduler tools."""
    if agent is None:
        logger.warning("No agent provided to agent scheduler tools")
        return
    
    # Schedule task tool
    registry.register(Tool(
        spec=ToolSpec(
            name="schedule_task",
            description="Schedule a task for automatic execution at a specific time",
            input_schema={
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "enum": ["swap", "transfer_sol", "buy_token", "sell_token"],
                        "description": "Type of task to execute"
                    },
                    "execute_at": {
                        "type": "string",
                        "description": "When to execute (ISO format or 'in X minutes/hours/days')"
                    },
                    "task_data": {
                        "type": "object",
                        "description": "Task-specific data (addresses, amounts, etc.)"
                    },
                    "conditions": {
                        "type": "object",
                        "description": "Optional execution conditions"
                    }
                },
                "required": ["task_type", "execute_at", "task_data"]
            },
            namespace="agent_scheduler",
            version="1.0.0"
        ),
        handler=schedule_task_wrapper(agent),
        input_model=ScheduleTaskInput
    ))
    
    # Get scheduled tasks tool
    registry.register(Tool(
        spec=ToolSpec(
            name="get_scheduled_tasks",
            description="Get all scheduled tasks for the current user",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "executing", "completed", "failed", "cancelled"],
                        "description": "Filter by status"
                    }
                }
            },
            namespace="agent_scheduler",
            version="1.0.0"
        ),
        handler=get_scheduled_tasks_wrapper(agent),
        input_model=GetScheduledTasksInput
    ))
    
    # Cancel task tool
    registry.register(Tool(
        spec=ToolSpec(
            name="cancel_task",
            description="Cancel a scheduled task",
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to cancel"
                    }
                },
                "required": ["task_id"]
            },
            namespace="agent_scheduler",
            version="1.0.0"
        ),
        handler=cancel_task_wrapper(agent),
        input_model=CancelTaskInput
    ))
    
    logger.info("Agent scheduler tools registered")
