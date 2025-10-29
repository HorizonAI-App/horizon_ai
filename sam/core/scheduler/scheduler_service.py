"""Core scheduler service for managing scheduled transactions."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from ..memory import MemoryManager
from ..events import EventBus
from ...utils.connection_pool import get_db_connection
from .models import (
    ScheduledTransaction,
    ScheduleTransactionInput,
    TransactionStatus,
    ScheduleType,
    OnceScheduleConfig,
    RecurringScheduleConfig,
    ConditionalScheduleConfig,
)
from ..tools import ToolRegistry
from .executor import ScheduledTransactionExecutor

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled transaction execution."""

    def __init__(self, memory_manager: MemoryManager, event_bus: EventBus):
        self.memory = memory_manager
        self.event_bus = event_bus
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._tool_registry: Optional[ToolRegistry] = None
        self._executor: Optional[ScheduledTransactionExecutor] = None
        self._execution_lock = asyncio.Lock()

    def set_tool_registry(self, tool_registry: ToolRegistry) -> None:
        """Set the tool registry for executing transactions."""
        self._tool_registry = tool_registry
        self._executor = ScheduledTransactionExecutor(tool_registry, self.event_bus)

    async def start(self) -> None:
        """Start the scheduler background task."""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._execution_loop())
        logger.info("Scheduler service started")

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler service stopped")

    async def schedule_transaction(
        self, 
        user_id: str, 
        input_data: ScheduleTransactionInput
    ) -> str:
        """Schedule a new transaction."""
        try:
            # Create schedule config based on type
            schedule_config = self._create_schedule_config(
                input_data.schedule_type, 
                input_data.schedule_config
            )

            # Calculate next execution time
            next_execution = self._calculate_next_execution(schedule_config)

            # Create scheduled transaction
            transaction = ScheduledTransaction(
                user_id=user_id,
                transaction_type=self._get_transaction_type(input_data.tool_name),
                tool_name=input_data.tool_name,
                parameters=input_data.parameters,
                schedule_config=schedule_config,
                next_execution=next_execution,
                max_executions=input_data.max_executions,
                metadata={"notes": input_data.notes} if input_data.notes else None,
            )

            # Store in database
            transaction_id = await self._store_transaction(transaction)

            # Emit event
            await self.event_bus.publish("scheduler.transaction_scheduled", {
                "transaction_id": transaction_id,
                "user_id": user_id,
                "tool_name": input_data.tool_name,
                "next_execution": next_execution.isoformat() if next_execution else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            logger.info(f"Scheduled transaction {transaction_id} for user {user_id}")
            return str(transaction_id)

        except Exception as e:
            logger.error(f"Failed to schedule transaction: {e}")
            raise

    async def cancel_transaction(self, transaction_id: int, user_id: str) -> bool:
        """Cancel a scheduled transaction."""
        try:
            async with get_db_connection(self.memory.db_path) as conn:
                # Check if transaction exists and belongs to user
                cursor = await conn.execute(
                    "SELECT id FROM scheduled_transactions WHERE id = ? AND user_id = ? AND status = 'pending'",
                    (transaction_id, user_id)
                )
                result = await cursor.fetchone()
                
                if not result:
                    return False

                # Update status to cancelled
                await conn.execute(
                    "UPDATE scheduled_transactions SET status = 'cancelled' WHERE id = ?",
                    (transaction_id,)
                )
                await conn.commit()

            # Emit event
            await self.event_bus.publish("scheduler.transaction_cancelled", {
                "transaction_id": transaction_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            logger.info(f"Cancelled transaction {transaction_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel transaction {transaction_id}: {e}")
            return False

    async def list_user_transactions(
        self, 
        user_id: str, 
        status: Optional[TransactionStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScheduledTransaction]:
        """List scheduled transactions for a user."""
        try:
            async with get_db_connection(self.memory.db_path) as conn:
                query = "SELECT * FROM scheduled_transactions WHERE user_id = ?"
                params = [user_id]

                if status:
                    query += " AND status = ?"
                    params.append(status.value)

                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor = await conn.execute(query, params)
                rows = await cursor.fetchall()

                transactions = []
                for row in rows:
                    # Convert row to dict
                    row_dict = dict(zip([col[0] for col in cursor.description], row))
                    transaction = ScheduledTransaction.from_dict(row_dict)
                    transactions.append(transaction)

                return transactions

        except Exception as e:
            logger.error(f"Failed to list transactions for user {user_id}: {e}")
            return []

    async def _execution_loop(self) -> None:
        """Main execution loop - runs every minute."""
        logger.info("Starting scheduler execution loop")
        
        while self.running:
            try:
                await self._process_due_transactions()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler execution loop: {e}")
                await asyncio.sleep(60)  # Continue after error

        logger.info("Scheduler execution loop stopped")

    async def _process_due_transactions(self) -> None:
        """Process transactions that are due for execution."""
        if not self._executor:
            logger.warning("No executor available, skipping transaction processing")
            return

        async with self._execution_lock:
            try:
                # Get due transactions
                due_transactions = await self._get_due_transactions()
                
                for transaction in due_transactions:
                    try:
                        # Pre-flight check
                        if not await self._executor.can_execute_transaction(transaction):
                            logger.warning(f"Skipping transaction {transaction.id} - pre-flight check failed")
                            await self._mark_transaction_failed(transaction.id, "Pre-flight check failed")
                            continue

                        # Execute the transaction
                        result = await self._executor.execute_transaction(transaction)
                        
                        # Check if execution was successful
                        if isinstance(result, dict) and result.get("error"):
                            await self._mark_transaction_failed(transaction.id, result["error"])
                        else:
                            await self._mark_transaction_executed(transaction, result)

                    except Exception as e:
                        logger.error(f"Failed to execute transaction {transaction.id}: {e}")
                        await self._mark_transaction_failed(transaction.id, str(e))

            except Exception as e:
                logger.error(f"Error processing due transactions: {e}")

    async def _get_due_transactions(self) -> List[ScheduledTransaction]:
        """Get transactions that are due for execution."""
        now = datetime.now(timezone.utc)
        
        try:
            async with get_db_connection(self.memory.db_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT * FROM scheduled_transactions 
                    WHERE status = 'pending' 
                    AND next_execution IS NOT NULL 
                    AND next_execution <= ?
                    ORDER BY next_execution ASC
                    """,
                    (now.isoformat(),)
                )
                rows = await cursor.fetchall()

                transactions = []
                for row in rows:
                    row_dict = dict(zip([col[0] for col in cursor.description], row))
                    transaction = ScheduledTransaction.from_dict(row_dict)
                    transactions.append(transaction)

                return transactions

        except Exception as e:
            logger.error(f"Failed to get due transactions: {e}")
            return []


    async def _mark_transaction_executed(
        self, 
        transaction: ScheduledTransaction, 
        result: Dict[str, Any]
    ) -> None:
        """Mark transaction as executed and schedule next execution if needed."""
        now = datetime.now(timezone.utc)
        
        # Calculate next execution for recurring transactions
        next_execution = None
        if transaction.schedule_config.schedule_type == ScheduleType.RECURRING:
            next_execution = self._calculate_next_recurring_execution(
                transaction.schedule_config, 
                now
            )

        # Check if we've reached max executions
        new_execution_count = transaction.execution_count + 1
        status = TransactionStatus.PENDING if next_execution else TransactionStatus.EXECUTED
        
        if (transaction.max_executions and 
            new_execution_count >= transaction.max_executions):
            status = TransactionStatus.EXECUTED

        try:
            async with get_db_connection(self.memory.db_path) as conn:
                await conn.execute(
                    """
                    UPDATE scheduled_transactions 
                    SET status = ?, 
                        last_execution = ?, 
                        next_execution = ?, 
                        execution_count = ?,
                        error_message = NULL
                    WHERE id = ?
                    """,
                    (
                        status.value,
                        now.isoformat(),
                        next_execution.isoformat() if next_execution else None,
                        new_execution_count,
                        transaction.id,
                    )
                )
                await conn.commit()

        except Exception as e:
            logger.error(f"Failed to update transaction {transaction.id}: {e}")

    async def _mark_transaction_failed(self, transaction_id: int, error_message: str) -> None:
        """Mark transaction as failed."""
        try:
            async with get_db_connection(self.memory.db_path) as conn:
                await conn.execute(
                    """
                    UPDATE scheduled_transactions 
                    SET status = 'failed', 
                        error_message = ?
                    WHERE id = ?
                    """,
                    (error_message, transaction_id)
                )
                await conn.commit()

        except Exception as e:
            logger.error(f"Failed to mark transaction {transaction_id} as failed: {e}")

    async def _store_transaction(self, transaction: ScheduledTransaction) -> int:
        """Store transaction in database and return ID."""
        try:
            async with get_db_connection(self.memory.db_path) as conn:
                data = transaction.to_dict()
                
                cursor = await conn.execute(
                    """
                    INSERT INTO scheduled_transactions 
                    (user_id, transaction_type, tool_name, parameters, schedule_type, 
                     schedule_config, status, created_at, next_execution, execution_count, 
                     max_executions, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["user_id"],
                        data["transaction_type"],
                        data["tool_name"],
                        data["parameters"],
                        data["schedule_type"],
                        data["schedule_config"],
                        data["status"],
                        data["created_at"],
                        data["next_execution"],
                        data["execution_count"],
                        data["max_executions"],
                        data["metadata"],
                    )
                )
                await conn.commit()
                return cursor.lastrowid

        except Exception as e:
            logger.error(f"Failed to store transaction: {e}")
            raise

    def _create_schedule_config(
        self, 
        schedule_type: ScheduleType, 
        config_data: Dict[str, Any]
    ) -> Any:
        """Create schedule config object from data."""
        if schedule_type == ScheduleType.ONCE:
            return OnceScheduleConfig(**config_data)
        elif schedule_type == ScheduleType.RECURRING:
            return RecurringScheduleConfig(**config_data)
        elif schedule_type == ScheduleType.CONDITIONAL:
            return ConditionalScheduleConfig(**config_data)
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

    def _calculate_next_execution(self, schedule_config: Any) -> Optional[datetime]:
        """Calculate next execution time based on schedule config."""
        if isinstance(schedule_config, OnceScheduleConfig):
            return schedule_config.execute_at
        elif isinstance(schedule_config, RecurringScheduleConfig):
            return self._calculate_next_recurring_execution(
                schedule_config, 
                datetime.now(timezone.utc)
            )
        elif isinstance(schedule_config, ConditionalScheduleConfig):
            # For conditional, we'll check periodically
            return datetime.now(timezone.utc) + timedelta(seconds=schedule_config.check_interval)
        else:
            return None

    def _calculate_next_recurring_execution(
        self, 
        config: RecurringScheduleConfig, 
        from_time: datetime
    ) -> Optional[datetime]:
        """Calculate next execution time for recurring schedule."""
        if config.frequency == "hourly":
            return from_time + timedelta(hours=1)
        elif config.frequency == "daily":
            next_day = from_time + timedelta(days=1)
            if config.time:
                hour, minute = map(int, config.time.split(":"))
                return next_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return next_day
        elif config.frequency == "weekly":
            if config.days_of_week:
                # Find next occurrence of specified days
                for day_offset in range(1, 8):
                    next_date = from_time + timedelta(days=day_offset)
                    if next_date.weekday() + 1 in config.days_of_week:  # Convert to 1-7
                        if config.time:
                            hour, minute = map(int, config.time.split(":"))
                            return next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        return next_date
            return from_time + timedelta(weeks=1)
        elif config.frequency == "monthly":
            if config.day_of_month:
                # Find next occurrence of specified day of month
                next_month = from_time.replace(day=1) + timedelta(days=32)
                next_month = next_month.replace(day=1)  # First day of next month
                try:
                    next_date = next_month.replace(day=config.day_of_month)
                    if config.time:
                        hour, minute = map(int, config.time.split(":"))
                        return next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    return next_date
                except ValueError:
                    # Day doesn't exist in that month, use last day
                    last_day = (next_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                    if config.time:
                        hour, minute = map(int, config.time.split(":"))
                        return last_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    return last_day
            return from_time + timedelta(days=30)  # Approximate month
        
        return None

    def _get_transaction_type(self, tool_name: str) -> str:
        """Get transaction type from tool name."""
        type_mapping = {
            "smart_buy": "buy",
            "smart_sell": "sell", 
            "jupiter_swap": "swap",
            "transfer_sol": "transfer",
            "pump_fun_buy": "buy",
            "pump_fun_sell": "sell",
            "aster_open_long": "futures_long",
            "aster_close_position": "futures_close",
        }
        return type_mapping.get(tool_name, "unknown")
