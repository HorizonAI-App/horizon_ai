"""
Scheduler Tools for the SAM Agent
Allows the agent to schedule transactions for future execution.
"""

import logging
from typing import Any, Dict, List, Optional

from ..core.tools import Tool, ToolSpec
from ..core.scheduler import (
    SchedulerManager, TransactionType, ScheduleStatus, RecurrenceType,
    get_scheduler_manager
)
from ..utils.error_handling import handle_errors

logger = logging.getLogger(__name__)


@handle_errors("scheduler_tools")
async def schedule_transaction_handler(args: Dict[str, Any], agent=None) -> Dict[str, Any]:
    """Schedule a transaction for future execution."""
    try:
        # Extract parameters
        transaction_type = args.get("transaction_type", "swap")
        schedule_time = args.get("schedule_time", "in 5 minutes")
        transaction_data = args.get("transaction_data", {})
        recurrence = args.get("recurrence", "once")
        conditions = args.get("conditions")
        
        # Get user_id and session_id from agent context
        user_id = "default"
        session_id = "default"
        if agent and hasattr(agent, '_context'):
            user_id = getattr(agent._context, 'user_id', 'default')
            session_id = getattr(agent._context, 'session_id', 'default')
        
        # Validate transaction type
        try:
            tx_type = TransactionType(transaction_type)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid transaction type: {transaction_type}",
                "message": f"Valid types are: {', '.join([t.value for t in TransactionType])}"
            }
        
        # Validate recurrence
        try:
            recur_type = RecurrenceType(recurrence)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid recurrence type: {recurrence}",
                "message": f"Valid types are: {', '.join([r.value for r in RecurrenceType])}"
            }
        
        # Get scheduler manager
        scheduler = await get_scheduler_manager()
        
        # Schedule the transaction
        result = await scheduler.schedule_transaction(
            user_id=user_id,
            session_id=session_id,
            transaction_type=tx_type,
            schedule_time=schedule_time,
            transaction_data=transaction_data,
            recurrence=recur_type,
            conditions=conditions
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in schedule_transaction_handler: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to schedule transaction"
        }


@handle_errors("scheduler_tools")
async def get_scheduled_transactions_handler(args: Dict[str, Any], agent=None) -> Dict[str, Any]:
    """Get all scheduled transactions for a user."""
    try:
        # Get user_id from agent context
        user_id = "default"
        if agent and hasattr(agent, '_context'):
            user_id = getattr(agent._context, 'user_id', 'default')
        
        status = args.get("status")
        
        # Get scheduler manager
        scheduler = await get_scheduler_manager()
        
        # Get transactions
        transactions = await scheduler.get_scheduled_transactions(
            user_id=user_id,
            status=ScheduleStatus(status) if status else None
        )
        
        return {
            "success": True,
            "transactions": transactions,
            "count": len(transactions),
            "message": f"Found {len(transactions)} scheduled transactions"
        }
        
    except Exception as e:
        logger.error(f"Error in get_scheduled_transactions_handler: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get scheduled transactions"
        }


@handle_errors("scheduler_tools")
async def cancel_scheduled_transaction_handler(args: Dict[str, Any], agent=None) -> Dict[str, Any]:
    """Cancel a scheduled transaction."""
    try:
        transaction_id = args.get("transaction_id")
        
        # Get user_id from agent context
        user_id = "default"
        if agent and hasattr(agent, '_context'):
            user_id = getattr(agent._context, 'user_id', 'default')
        
        if not transaction_id:
            return {
                "success": False,
                "error": "transaction_id is required",
                "message": "Please provide a transaction ID to cancel"
            }
        
        # Get scheduler manager
        scheduler = await get_scheduler_manager()
        
        # Cancel the transaction
        result = await scheduler.cancel_transaction(
            transaction_id=int(transaction_id),
            user_id=user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in cancel_scheduled_transaction_handler: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to cancel scheduled transaction"
        }


def register(registry, agent=None):
    """Register scheduler tools with the agent."""
    
    # Create wrapper functions that have access to the agent
    async def schedule_transaction_wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
        return await schedule_transaction_handler(args, agent)
    
    async def get_scheduled_transactions_wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
        return await get_scheduled_transactions_handler(args, agent)
    
    async def cancel_scheduled_transaction_wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
        return await cancel_scheduled_transaction_handler(args, agent)
    
    # Schedule Transaction Tool
    registry.register(Tool(
        spec=ToolSpec(
            name="schedule_transaction",
            description="Schedule a transaction to be executed at a specific time",
            input_schema={
                "type": "object",
                "properties": {
                    "transaction_type": {
                        "type": "string",
                        "enum": ["swap", "transfer_sol", "buy_token", "sell_token", "custom"],
                        "description": "Type of transaction to schedule"
                    },
                    "schedule_time": {
                        "type": "string",
                        "description": "When to execute (e.g., 'in 5 minutes', 'in 1 hour', '2024-01-01 12:00:00')"
                    },
                    "transaction_data": {
                        "type": "object",
                        "description": "Transaction parameters (amount, addresses, etc.)"
                    },
                    "recurrence": {
                        "type": "string",
                        "enum": ["once", "daily", "weekly", "monthly"],
                        "default": "once",
                        "description": "How often to repeat the transaction"
                    },
                    "conditions": {
                        "type": "object",
                        "description": "Optional conditions for execution (e.g., price targets)"
                    }
                },
                "required": ["transaction_type", "schedule_time", "transaction_data"]
            },
            namespace="scheduler",
            version="1.0.0"
        ),
        handler=schedule_transaction_wrapper
    ))
    
    # Get Scheduled Transactions Tool
    registry.register(Tool(
        spec=ToolSpec(
            name="get_scheduled_transactions",
            description="Get all scheduled transactions for the current user",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "executing", "completed", "failed", "cancelled"],
                        "description": "Filter by transaction status (optional)"
                    }
                }
            },
            namespace="scheduler",
            version="1.0.0"
        ),
        handler=get_scheduled_transactions_wrapper
    ))
    
    # Cancel Scheduled Transaction Tool
    registry.register(Tool(
        spec=ToolSpec(
            name="cancel_scheduled_transaction",
            description="Cancel a scheduled transaction before it executes",
            input_schema={
                "type": "object",
                "properties": {
                    "transaction_id": {
                        "type": "integer",
                        "description": "ID of the transaction to cancel"
                    }
                },
                "required": ["transaction_id"]
            },
            namespace="scheduler",
            version="1.0.0"
        ),
        handler=cancel_scheduled_transaction_wrapper
    ))
    
    logger.info("Scheduler tools registered successfully")
