"""
Scheduled Transactions System
Handles scheduling and execution of future transactions.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field

from ..utils.connection_pool import get_db_connection
from ..utils.error_handling import handle_errors

logger = logging.getLogger(__name__)


class TransactionType(str, Enum):
    """Types of transactions that can be scheduled."""
    SWAP = "swap"
    TRANSFER_SOL = "transfer_sol"
    BUY_TOKEN = "buy_token"
    SELL_TOKEN = "sell_token"
    CUSTOM = "custom"


class ScheduleStatus(str, Enum):
    """Status of scheduled transactions."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecurrenceType(str, Enum):
    """Types of recurring schedules."""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ScheduledTransaction:
    """Represents a scheduled transaction."""
    id: Optional[int] = None
    user_id: str = ""
    session_id: str = ""
    transaction_type: TransactionType = TransactionType.SWAP
    schedule_time: datetime = datetime.now()
    recurrence: RecurrenceType = RecurrenceType.ONCE
    status: ScheduleStatus = ScheduleStatus.PENDING
    transaction_data: Dict[str, Any] = None
    conditions: Optional[Dict[str, Any]] = None
    created_at: datetime = datetime.now()
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if self.transaction_data is None:
            self.transaction_data = {}
        if self.conditions is None:
            self.conditions = {}


class SchedulerInput(BaseModel):
    """Input model for scheduling transactions."""
    transaction_type: TransactionType = Field(..., description="Type of transaction to schedule")
    schedule_time: str = Field(..., description="When to execute (ISO format or relative like 'in 5 minutes')")
    transaction_data: Dict[str, Any] = Field(..., description="Transaction parameters")
    recurrence: RecurrenceType = Field(RecurrenceType.ONCE, description="How often to repeat")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Conditions for execution (e.g., price targets)")


class SchedulerManager:
    """Manages scheduled transactions."""
    
    def __init__(self, db_path: str = ".sam/sam_memory.db"):
        self.db_path = db_path
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the scheduler database tables."""
        await self._init_database()
        
    async def _init_database(self) -> None:
        """Create scheduler tables in the database."""
        async with get_db_connection(self.db_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    schedule_time TEXT NOT NULL,
                    recurrence TEXT NOT NULL DEFAULT 'once',
                    status TEXT NOT NULL DEFAULT 'pending',
                    transaction_data TEXT NOT NULL,
                    conditions TEXT,
                    created_at TEXT NOT NULL,
                    executed_at TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3
                )
            """)
            
            # Create indexes for performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_time ON scheduled_transactions(schedule_time)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON scheduled_transactions(status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON scheduled_transactions(user_id)")
            
            await conn.commit()
            
    @handle_errors("scheduler")
    async def schedule_transaction(
        self,
        user_id: str,
        session_id: str,
        transaction_type: TransactionType,
        schedule_time: Union[str, datetime],
        transaction_data: Dict[str, Any],
        recurrence: RecurrenceType = RecurrenceType.ONCE,
        conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Schedule a new transaction."""
        try:
            # Parse schedule time
            if isinstance(schedule_time, str):
                schedule_dt = self._parse_schedule_time(schedule_time)
            else:
                schedule_dt = schedule_time
                
            # Create scheduled transaction
            scheduled_tx = ScheduledTransaction(
                user_id=user_id,
                session_id=session_id,
                transaction_type=transaction_type,
                schedule_time=schedule_dt,
                recurrence=recurrence,
                transaction_data=transaction_data,
                conditions=conditions or {}
            )
            
            # Store in database
            async with get_db_connection(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO scheduled_transactions (
                        user_id, session_id, transaction_type, schedule_time,
                        recurrence, status, transaction_data, conditions,
                        created_at, retry_count, max_retries
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    scheduled_tx.user_id,
                    scheduled_tx.session_id,
                    scheduled_tx.transaction_type.value,
                    scheduled_tx.schedule_time.isoformat(),
                    scheduled_tx.recurrence.value,
                    scheduled_tx.status.value,
                    json.dumps(scheduled_tx.transaction_data),
                    json.dumps(scheduled_tx.conditions) if scheduled_tx.conditions else None,
                    scheduled_tx.created_at.isoformat(),
                    scheduled_tx.retry_count,
                    scheduled_tx.max_retries
                ))
                
                # Get the inserted ID
                cursor = await conn.execute("SELECT last_insert_rowid()")
                result = await cursor.fetchone()
                scheduled_tx.id = result[0] if result else None
                
                await conn.commit()
                
            logger.info(f"Scheduled transaction {scheduled_tx.id} for {schedule_dt}")
            
            return {
                "success": True,
                "transaction_id": scheduled_tx.id,
                "schedule_time": schedule_dt.isoformat(),
                "status": scheduled_tx.status.value,
                "message": f"Transaction scheduled for {schedule_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
        except Exception as e:
            logger.error(f"Failed to schedule transaction: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to schedule transaction"
            }
    
    def _parse_schedule_time(self, time_str: str) -> datetime:
        """Parse schedule time from string."""
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
                    
        raise ValueError(f"Unable to parse schedule time: {time_str}")
    
    @handle_errors("scheduler")
    async def get_scheduled_transactions(
        self,
        user_id: str,
        status: Optional[ScheduleStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get scheduled transactions for a user."""
        try:
            async with get_db_connection(self.db_path) as conn:
                query = "SELECT * FROM scheduled_transactions WHERE user_id = ?"
                params = [user_id]
                
                if status:
                    query += " AND status = ?"
                    params.append(status.value)
                    
                query += " ORDER BY schedule_time ASC"
                
                cursor = await conn.execute(query, params)
                rows = await cursor.fetchall()
                
                transactions = []
                for row in rows:
                    tx_data = {
                        "id": row[0],
                        "user_id": row[1],
                        "session_id": row[2],
                        "transaction_type": row[3],
                        "schedule_time": row[4],
                        "recurrence": row[5],
                        "status": row[6],
                        "transaction_data": json.loads(row[7]),
                        "conditions": json.loads(row[8]) if row[8] else {},
                        "created_at": row[9],
                        "executed_at": row[10],
                        "error_message": row[11],
                        "retry_count": row[12],
                        "max_retries": row[13]
                    }
                    transactions.append(tx_data)
                    
                return transactions
                
        except Exception as e:
            logger.error(f"Failed to get scheduled transactions: {e}")
            return []
    
    @handle_errors("scheduler")
    async def cancel_transaction(self, transaction_id: int, user_id: str) -> Dict[str, Any]:
        """Cancel a scheduled transaction."""
        try:
            async with get_db_connection(self.db_path) as conn:
                await conn.execute("""
                    UPDATE scheduled_transactions 
                    SET status = ? 
                    WHERE id = ? AND user_id = ? AND status = ?
                """, (ScheduleStatus.CANCELLED.value, transaction_id, user_id, ScheduleStatus.PENDING.value))
                
                if conn.total_changes > 0:
                    await conn.commit()
                    return {
                        "success": True,
                        "message": f"Transaction {transaction_id} cancelled"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Transaction not found or already executed"
                    }
                    
        except Exception as e:
            logger.error(f"Failed to cancel transaction: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def start_worker(self) -> None:
        """Start the background worker to execute scheduled transactions."""
        if self._running:
            return
            
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Scheduler worker started")
    
    async def stop_worker(self) -> None:
        """Stop the background worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler worker stopped")
    
    async def _worker_loop(self) -> None:
        """Main worker loop to check and execute scheduled transactions."""
        while self._running:
            try:
                await self._check_and_execute_transactions()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler worker: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _check_and_execute_transactions(self) -> None:
        """Check for transactions that are ready to execute."""
        try:
            now = datetime.now()
            
            async with get_db_connection(self.db_path) as conn:
                # Get pending transactions that are due
                cursor = await conn.execute("""
                    SELECT * FROM scheduled_transactions 
                    WHERE status = ? AND schedule_time <= ?
                    ORDER BY schedule_time ASC
                """, (ScheduleStatus.PENDING.value, now.isoformat()))
                
                rows = await cursor.fetchall()
                
                for row in rows:
                    await self._execute_transaction(row, conn)
                    
        except Exception as e:
            logger.error(f"Error checking scheduled transactions: {e}")
    
    async def _execute_transaction(self, row: tuple, conn) -> None:
        """Execute a scheduled transaction."""
        transaction_id = row[0]
        user_id = row[1]
        session_id = row[2]
        transaction_type = row[3]
        # Parse transaction_data - handle both string and dict cases
        try:
            if isinstance(row[7], str):
                transaction_data = json.loads(row[7])
            else:
                transaction_data = row[7]
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse transaction_data for transaction {transaction_id}: {e}")
            transaction_data = {}
        
        # Parse conditions
        try:
            if row[8] and isinstance(row[8], str):
                conditions = json.loads(row[8])
            elif row[8]:
                conditions = row[8]
            else:
                conditions = {}
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse conditions for transaction {transaction_id}: {e}")
            conditions = {}
        retry_count = row[12]
        max_retries = row[13]
        
        try:
            # Update status to executing
            await conn.execute("""
                UPDATE scheduled_transactions 
                SET status = ? 
                WHERE id = ?
            """, (ScheduleStatus.EXECUTING.value, transaction_id))
            await conn.commit()
            
            # Check conditions if any
            if conditions and not await self._check_conditions(conditions):
                # Reschedule for later if conditions not met
                await conn.execute("""
                    UPDATE scheduled_transactions 
                    SET status = ?, schedule_time = ?
                    WHERE id = ?
                """, (ScheduleStatus.PENDING.value, (datetime.now() + timedelta(minutes=5)).isoformat(), transaction_id))
                await conn.commit()
                return
            
            # Execute the transaction
            result = await self._execute_transaction_by_type(
                transaction_type, transaction_data, user_id, session_id
            )
            
            if result.get("success", False):
                # Mark as completed
                await conn.execute("""
                    UPDATE scheduled_transactions 
                    SET status = ?, executed_at = ?
                    WHERE id = ?
                """, (ScheduleStatus.COMPLETED.value, datetime.now().isoformat(), transaction_id))
                
                # Handle recurrence
                if row[5] != RecurrenceType.ONCE.value:
                    await self._schedule_next_recurrence(row, conn)
                    
            else:
                # Handle failure
                if retry_count < max_retries:
                    # Retry later
                    await conn.execute("""
                        UPDATE scheduled_transactions 
                        SET status = ?, retry_count = ?, schedule_time = ?
                        WHERE id = ?
                    """, (
                        ScheduleStatus.PENDING.value,
                        retry_count + 1,
                        (datetime.now() + timedelta(minutes=5)).isoformat(),
                        transaction_id
                    ))
                else:
                    # Mark as failed
                    await conn.execute("""
                        UPDATE scheduled_transactions 
                        SET status = ?, error_message = ?
                        WHERE id = ?
                    """, (ScheduleStatus.FAILED.value, result.get("error", "Unknown error"), transaction_id))
                
            await conn.commit()
            
        except Exception as e:
            logger.error(f"Error executing transaction {transaction_id}: {e}")
            await conn.execute("""
                UPDATE scheduled_transactions 
                SET status = ?, error_message = ?
                WHERE id = ?
            """, (ScheduleStatus.FAILED.value, str(e), transaction_id))
            await conn.commit()
    
    async def _check_conditions(self, conditions: Dict[str, Any]) -> bool:
        """Check if execution conditions are met."""
        # This is a placeholder - implement specific condition checking
        # For example: price targets, market conditions, etc.
        return True
    
    async def _execute_transaction_by_type(
        self,
        transaction_type: str,
        transaction_data: Dict[str, Any],
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Execute a transaction based on its type."""
        logger.info(f"Executing {transaction_type} transaction: {transaction_data}")
        
        try:
            # Import here to avoid circular imports
            from ..integrations.solana.solana_tools import SolanaTools
            from ..integrations.jupiter import JupiterTools
            from ..integrations.pump_fun import PumpFunTools
            from ..config.settings import Settings
            from ..core.private_key_manager import PrivateKeyManager
            
            # Get the private key for this session
            from ..utils.secure_storage import get_secure_storage
            secure_storage = get_secure_storage()
            private_key_manager = PrivateKeyManager(secure_storage)
            private_key = await private_key_manager.get_private_key(session_id)
            
            if not private_key:
                return {
                    "success": False,
                    "error": "No private key available for this session",
                    "message": "Please authenticate first"
                }
            
            # Initialize tools
            solana_tools = SolanaTools(Settings.SAM_SOLANA_RPC_URL, private_key, session_id)
            jupiter_tools = JupiterTools()
            pump_tools = PumpFunTools(solana_tools)
            
            # Execute based on transaction type
            if transaction_type == "swap":
                return await self._execute_swap(jupiter_tools, transaction_data)
            elif transaction_type == "transfer_sol":
                return await self._execute_transfer_sol(solana_tools, transaction_data)
            elif transaction_type == "buy_token":
                return await self._execute_buy_token(pump_tools, transaction_data)
            elif transaction_type == "sell_token":
                return await self._execute_sell_token(pump_tools, transaction_data)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported transaction type: {transaction_type}",
                    "message": "Transaction type not implemented"
                }
                
        except Exception as e:
            logger.error(f"Error executing {transaction_type} transaction: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Transaction execution failed"
            }
    
    async def _execute_swap(self, jupiter_tools, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Jupiter swap."""
        try:
            input_mint = data.get("input_mint")
            output_mint = data.get("output_mint")
            amount = data.get("amount", 0.01)
            slippage = data.get("slippage", 5)
            
            if not input_mint or not output_mint:
                return {
                    "success": False,
                    "error": "Missing input_mint or output_mint",
                    "message": "Swap requires input and output token addresses"
                }
            
            # Execute the swap
            result = await jupiter_tools.jupiter_swap(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                slippage=slippage
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Swap execution failed"
            }
    
    async def _execute_transfer_sol(self, solana_tools, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a SOL transfer."""
        try:
            to_address = data.get("to_address")
            amount = data.get("amount", 0.01)
            
            if not to_address:
                return {
                    "success": False,
                    "error": "Missing to_address",
                    "message": "Transfer requires destination address"
                }
            
            # Execute the transfer
            result = await solana_tools.transfer_sol(to_address, amount)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Transfer execution failed"
            }
    
    async def _execute_buy_token(self, pump_tools, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a token buy on pump.fun."""
        try:
            mint_address = data.get("mint_address")
            sol_amount = data.get("sol_amount", 0.01)
            slippage = data.get("slippage", 5)
            
            if not mint_address:
                return {
                    "success": False,
                    "error": "Missing mint_address",
                    "message": "Token buy requires mint address"
                }
            
            # Execute the buy
            result = await pump_tools.pump_fun_buy(mint_address, sol_amount, slippage)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Token buy execution failed"
            }
    
    async def _execute_sell_token(self, pump_tools, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a token sell on pump.fun."""
        try:
            mint_address = data.get("mint_address")
            percentage = data.get("percentage", 100)
            slippage = data.get("slippage", 5)
            
            if not mint_address:
                return {
                    "success": False,
                    "error": "Missing mint_address",
                    "message": "Token sell requires mint address"
                }
            
            # Execute the sell
            result = await pump_tools.pump_fun_sell(mint_address, percentage, slippage)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Token sell execution failed"
            }
    
    async def _schedule_next_recurrence(self, row: tuple, conn) -> None:
        """Schedule the next occurrence of a recurring transaction."""
        recurrence = row[5]
        schedule_time = datetime.fromisoformat(row[4])
        
        if recurrence == RecurrenceType.DAILY.value:
            next_time = schedule_time + timedelta(days=1)
        elif recurrence == RecurrenceType.WEEKLY.value:
            next_time = schedule_time + timedelta(weeks=1)
        elif recurrence == RecurrenceType.MONTHLY.value:
            next_time = schedule_time + timedelta(days=30)  # Approximate
        else:
            return
            
        # Create new scheduled transaction
        await conn.execute("""
            INSERT INTO scheduled_transactions (
                user_id, session_id, transaction_type, schedule_time,
                recurrence, status, transaction_data, conditions,
                created_at, retry_count, max_retries
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row[1], row[2], row[3], next_time.isoformat(),
            row[5], ScheduleStatus.PENDING.value, row[7], row[8],
            datetime.now().isoformat(), 0, row[13]
        ))


# Global scheduler instance
_scheduler_manager: Optional[SchedulerManager] = None


async def get_scheduler_manager() -> SchedulerManager:
    """Get the global scheduler manager instance."""
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
        await _scheduler_manager.initialize()
    return _scheduler_manager
