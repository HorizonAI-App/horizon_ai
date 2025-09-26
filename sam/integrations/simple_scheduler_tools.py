#!/usr/bin/env python3
"""Simple scheduler tools that actually work."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from pydantic import BaseModel, Field
from ..core.tools import Tool, ToolSpec
from ..core.simple_scheduler import get_simple_scheduler
from ..utils.error_handling import handle_errors

logger = logging.getLogger(__name__)

class SimpleScheduleInput(BaseModel):
    """Input for simple scheduling."""
    task_type: str = Field(..., description="Type of task")
    execute_in_minutes: int = Field(..., description="Execute in X minutes")
    task_data: Dict[str, Any] = Field(..., description="Task data")

@handle_errors("simple_scheduler")
async def simple_schedule_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Schedule a task simply."""
    try:
        scheduler = get_simple_scheduler()
        
        # Calculate execute time
        execute_at = datetime.now() + timedelta(minutes=args["execute_in_minutes"])
        
        # Generate task ID
        tasks = scheduler.get_tasks()
        task_id = max([t["id"] for t in tasks], default=0) + 1
        
        # Schedule the task
        success = scheduler.schedule_task(
            task_id=task_id,
            execute_at=execute_at,
            task_data=args["task_data"]
        )
        
        if success:
            return {
                "success": True,
                "task_id": task_id,
                "execute_at": execute_at.isoformat(),
                "message": f"Task scheduled for {execute_at}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to schedule task"
            }
            
    except Exception as e:
        logger.error(f"Error in simple schedule: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@handle_errors("simple_scheduler")
async def simple_get_tasks_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all scheduled tasks."""
    try:
        scheduler = get_simple_scheduler()
        tasks = scheduler.get_tasks()
        
        return {
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def register(registry, agent=None):
    """Register simple scheduler tools."""
    if agent is None:
        logger.warning("No agent provided to simple scheduler tools")
        return
    
    # Simple schedule tool
    registry.register(Tool(
        spec=ToolSpec(
            name="simple_schedule",
            description="Schedule a task to execute in X minutes (simple and reliable)",
            input_schema={
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "Type of task"
                    },
                    "execute_in_minutes": {
                        "type": "integer",
                        "description": "Execute in X minutes"
                    },
                    "task_data": {
                        "type": "object",
                        "description": "Task data"
                    }
                },
                "required": ["task_type", "execute_in_minutes", "task_data"]
            },
            namespace="simple_scheduler",
            version="1.0.0"
        ),
        handler=simple_schedule_handler,
        input_model=SimpleScheduleInput
    ))
    
    # Get tasks tool
    registry.register(Tool(
        spec=ToolSpec(
            name="simple_get_tasks",
            description="Get all scheduled tasks",
            input_schema={
                "type": "object",
                "properties": {}
            },
            namespace="simple_scheduler",
            version="1.0.0"
        ),
        handler=simple_get_tasks_handler
    ))
    
    logger.info("Simple scheduler tools registered")
