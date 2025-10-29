"""Tools for scheduling transactions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import re

from ..tools import Tool, ToolSpec
from ...utils.time_helpers import calculate_execution_time, format_execution_time, get_time_until_execution
from .models import (
    ScheduleTransactionInput,
    ListScheduledTransactionsInput,
    CancelScheduledTransactionInput,
    TransactionStatus,
    ScheduleType,
    OnceScheduleConfig,
    RecurringScheduleConfig,
)
from .scheduler_service import SchedulerService

logger = logging.getLogger(__name__)


def parse_relative_time(time_str: str) -> Optional[datetime]:
    """Parse relative time expressions like 'in 3 minutes', 'in 1 hour', etc."""
    if not time_str:
        return None
    
    time_str = time_str.lower().strip()
    
    # Pattern for "in X minutes/hours/days"
    relative_pattern = r'in\s+(\d+)\s+(minute|hour|day|week)s?'
    match = re.search(relative_pattern, time_str)
    
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        
        now = datetime.now(timezone.utc)
        
        if unit == 'minute':
            return now + timedelta(minutes=amount)
        elif unit == 'hour':
            return now + timedelta(hours=amount)
        elif unit == 'day':
            return now + timedelta(days=amount)
        elif unit == 'week':
            return now + timedelta(weeks=amount)
    
    return None


def parse_absolute_time(time_str: str) -> Optional[datetime]:
    """Parse absolute time expressions like 'at 9:00 AM', 'tomorrow at 10:00', etc."""
    if not time_str:
        return None
    
    time_str = time_str.lower().strip()
    now = datetime.now(timezone.utc)
    
    # Pattern for "at HH:MM AM/PM"
    time_pattern = r'at\s+(\d{1,2}):(\d{2})\s*(am|pm)?'
    match = re.search(time_pattern, time_str)
    
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = match.group(3)
        
        # Convert to 24-hour format
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        
        # Check if it's for today or tomorrow
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if target_time <= now:
            # If time has passed today, schedule for tomorrow
            target_time += timedelta(days=1)
        
        return target_time
    
    return None


def validate_and_fix_schedule_config(schedule_type: str, schedule_config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and fix schedule configuration, especially for time calculations."""
    if schedule_type == "once":
        execute_at = schedule_config.get("execute_at")
        
        if execute_at:
            try:
                if isinstance(execute_at, str):
                    # Use the new time helper to calculate execution time
                    calculated_time = calculate_execution_time(execute_at)
                    if calculated_time:
                        schedule_config["execute_at"] = calculated_time
                        return schedule_config
                    
                    # Fallback to old parsing methods
                    relative_time = parse_relative_time(execute_at)
                    if relative_time:
                        schedule_config["execute_at"] = relative_time.isoformat()
                        return schedule_config
                    
                    absolute_time = parse_absolute_time(execute_at)
                    if absolute_time:
                        schedule_config["execute_at"] = absolute_time.isoformat()
                        return schedule_config
                    
                    # Try to parse as ISO format
                    parsed_time = datetime.fromisoformat(execute_at.replace('Z', '+00:00'))
                    
                    # If the time is in the past, add a small buffer
                    now = datetime.now(timezone.utc)
                    if parsed_time <= now:
                        # Add 1 minute to ensure it's in the future
                        parsed_time = now + timedelta(minutes=1)
                        schedule_config["execute_at"] = parsed_time.isoformat()
                        logger.warning(f"Adjusted past execution time to {parsed_time.isoformat()}")
                    
                elif isinstance(execute_at, datetime):
                    # If it's already a datetime object, ensure it's in the future
                    now = datetime.now(timezone.utc)
                    if execute_at <= now:
                        execute_at = now + timedelta(minutes=1)
                        schedule_config["execute_at"] = execute_at.isoformat()
                        logger.warning(f"Adjusted past execution time to {execute_at.isoformat()}")
                
            except Exception as e:
                logger.error(f"Failed to parse execution time: {e}")
                # Default to 1 minute from now
                default_time = datetime.now(timezone.utc) + timedelta(minutes=1)
                schedule_config["execute_at"] = default_time.isoformat()
                logger.warning(f"Using default execution time: {default_time.isoformat()}")
    
    return schedule_config


def create_scheduler_tools(scheduler_service: SchedulerService) -> List[Tool]:
    """Create scheduling tools for the agent."""

    async def handle_schedule_transaction(args: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a transaction for future execution."""
        try:
            # Get user_id from context (this will be set by the agent)
            user_id = getattr(scheduler_service, "_current_user_id", "default")
            
            # Validate and fix schedule configuration
            schedule_type = args.get("schedule_type", "once")
            schedule_config = args.get("schedule_config", {})
            
            # Apply time validation and fixes
            fixed_schedule_config = validate_and_fix_schedule_config(schedule_type, schedule_config)
            args["schedule_config"] = fixed_schedule_config
            
            # Parse input
            input_data = ScheduleTransactionInput(**args)
            
            # Schedule the transaction
            transaction_id = await scheduler_service.schedule_transaction(user_id, input_data)
            
            # Get execution time for user feedback
            execution_time = None
            time_until_execution = None
            if schedule_type == "once" and "execute_at" in fixed_schedule_config:
                try:
                    execution_time_str = fixed_schedule_config["execute_at"]
                    execution_time = datetime.fromisoformat(execution_time_str.replace('Z', '+00:00'))
                    time_until_execution = get_time_until_execution(execution_time_str)
                except:
                    pass
            
            # Format response message
            message = f"✅ Transaction scheduled successfully with ID: {transaction_id}"
            if execution_time:
                formatted_time = format_execution_time(execution_time.isoformat())
                message += f"\n⏰ Execution time: {formatted_time}"
                if time_until_execution:
                    message += f"\n⏳ Time until execution: {time_until_execution}"
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "message": message,
                "tool_name": input_data.tool_name,
                "schedule_type": input_data.schedule_type.value,
                "execution_time": execution_time.isoformat() if execution_time else None,
                "notes": input_data.notes,
            }

        except Exception as e:
            logger.error(f"Failed to schedule transaction: {e}")
            
            # Provide more helpful error messages
            error_msg = str(e)
            if "execute_at must be in the future" in error_msg:
                error_msg = "The specified execution time is in the past. Please provide a future time."
            elif "Invalid schedule configuration" in error_msg:
                error_msg = "Invalid schedule configuration. Please check your time format."
            
            return {
                "success": False,
                "error": f"Failed to schedule transaction: {error_msg}",
                "suggestion": "Try using formats like 'in 5 minutes', 'at 9:00 AM', or a specific future date/time.",
            }

    async def handle_list_scheduled_transactions(args: Dict[str, Any]) -> Dict[str, Any]:
        """List scheduled transactions for the user."""
        try:
            # Get user_id from context
            user_id = getattr(scheduler_service, "_current_user_id", "default")
            
            # Parse input
            input_data = ListScheduledTransactionsInput(**args)
            
            # Get transactions
            transactions = await scheduler_service.list_user_transactions(
                user_id=user_id,
                status=input_data.status,
                limit=input_data.limit,
                offset=input_data.offset,
            )
            
            # Format results
            formatted_transactions = []
            for tx in transactions:
                # Format execution times
                next_execution_formatted = None
                time_until_execution = None
                if tx.next_execution:
                    next_execution_formatted = format_execution_time(tx.next_execution.isoformat())
                    time_until_execution = get_time_until_execution(tx.next_execution.isoformat())
                
                last_execution_formatted = None
                if tx.last_execution:
                    last_execution_formatted = format_execution_time(tx.last_execution.isoformat())
                
                formatted_transactions.append({
                    "id": tx.id,
                    "tool_name": tx.tool_name,
                    "transaction_type": tx.transaction_type,
                    "status": tx.status.value,
                    "created_at": tx.created_at.isoformat(),
                    "next_execution": tx.next_execution.isoformat() if tx.next_execution else None,
                    "next_execution_formatted": next_execution_formatted,
                    "time_until_execution": time_until_execution,
                    "last_execution": tx.last_execution.isoformat() if tx.last_execution else None,
                    "last_execution_formatted": last_execution_formatted,
                    "execution_count": tx.execution_count,
                    "max_executions": tx.max_executions,
                    "error_message": tx.error_message,
                    "notes": tx.metadata.get("notes") if tx.metadata else None,
                })
            
            return {
                "success": True,
                "count": len(formatted_transactions),
                "transactions": formatted_transactions,
                "message": f"Found {len(formatted_transactions)} scheduled transactions",
            }

        except Exception as e:
            logger.error(f"Failed to list scheduled transactions: {e}")
            return {
                "success": False,
                "error": f"Failed to list transactions: {str(e)}",
            }

    async def handle_cancel_scheduled_transaction(args: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel a scheduled transaction."""
        try:
            # Get user_id from context
            user_id = getattr(scheduler_service, "_current_user_id", "default")
            
            # Parse input
            input_data = CancelScheduledTransactionInput(**args)
            
            # Cancel the transaction
            success = await scheduler_service.cancel_transaction(
                input_data.transaction_id, 
                user_id
            )
            
            if success:
                return {
                    "success": True,
                    "message": f"Transaction {input_data.transaction_id} cancelled successfully",
                    "transaction_id": input_data.transaction_id,
                }
            else:
                return {
                    "success": False,
                    "error": f"Transaction {input_data.transaction_id} not found or already processed",
                    "transaction_id": input_data.transaction_id,
                }

        except Exception as e:
            logger.error(f"Failed to cancel transaction: {e}")
            return {
                "success": False,
                "error": f"Failed to cancel transaction: {str(e)}",
            }

    return [
        Tool(
            spec=ToolSpec(
                name="schedule_transaction",
                description="Schedule a transaction for future execution (once, recurring, or conditional)",
                namespace="scheduler",
                input_schema={
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Name of the tool to execute",
                            "enum": [
                                "smart_buy", "smart_sell", "jupiter_swap", "transfer_sol",
                                "pump_fun_buy", "pump_fun_sell", "aster_open_long", "aster_close_position"
                            ]
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Parameters for the tool execution"
                        },
                        "schedule_type": {
                            "type": "string",
                            "description": "Type of schedule",
                            "enum": ["once", "recurring", "conditional"]
                        },
                        "schedule_config": {
                            "type": "object",
                            "description": "Schedule configuration (varies by schedule_type)"
                        },
                        "max_executions": {
                            "type": "integer",
                            "description": "Maximum number of executions (optional)",
                            "minimum": 1
                        },
                        "notes": {
                            "type": "string",
                            "description": "User notes about the transaction (optional)"
                        }
                    },
                    "required": ["tool_name", "parameters", "schedule_type", "schedule_config"]
                }
            ),
            handler=handle_schedule_transaction,
            input_model=ScheduleTransactionInput,
        ),
        Tool(
            spec=ToolSpec(
                name="list_scheduled_transactions",
                description="List all scheduled transactions for the user",
                namespace="scheduler",
                input_schema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by status",
                            "enum": ["pending", "executed", "failed", "cancelled", "expired"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of transactions to return",
                            "minimum": 1,
                            "maximum": 200,
                            "default": 50
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Offset for pagination",
                            "minimum": 0,
                            "default": 0
                        }
                    }
                }
            ),
            handler=handle_list_scheduled_transactions,
            input_model=ListScheduledTransactionsInput,
        ),
        Tool(
            spec=ToolSpec(
                name="cancel_scheduled_transaction",
                description="Cancel a scheduled transaction",
                namespace="scheduler",
                input_schema={
                    "type": "object",
                    "properties": {
                        "transaction_id": {
                            "type": "integer",
                            "description": "ID of the transaction to cancel"
                        }
                    },
                    "required": ["transaction_id"]
                }
            ),
            handler=handle_cancel_scheduled_transaction,
            input_model=CancelScheduledTransactionInput,
        ),
    ]


def set_scheduler_user_context(scheduler_service: SchedulerService, user_id: str) -> None:
    """Set the current user context for the scheduler service."""
    setattr(scheduler_service, "_current_user_id", user_id)
