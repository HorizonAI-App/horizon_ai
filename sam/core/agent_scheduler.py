#!/usr/bin/env python3
"""Agent-integrated scheduler for automatic transaction execution."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import threading
import time

from ..utils.error_handling import handle_errors
from ..utils.secure_storage import get_secure_storage
from ..core.private_key_manager import PrivateKeyManager

logger = logging.getLogger(__name__)

@dataclass
class ScheduledTask:
    """Represents a scheduled task with execution details."""
    task_id: str
    user_id: str
    session_id: str
    task_type: str  # 'swap', 'transfer_sol', 'buy_token', 'sell_token'
    execute_at: datetime
    task_data: Dict[str, Any]
    conditions: Optional[Dict[str, Any]] = None
    status: str = 'pending'  # 'pending', 'executing', 'completed', 'failed', 'cancelled'
    created_at: datetime = None
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class AgentScheduler:
    """Agent-integrated scheduler that handles automatic transaction execution."""
    
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._next_task_id = 1
        
    async def start(self) -> None:
        """Start the scheduler worker."""
        if self._running:
            return
            
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Agent scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Agent scheduler stopped")
    
    async def schedule_task(
        self,
        user_id: str,
        session_id: str,
        task_type: str,
        execute_at: datetime,
        task_data: Dict[str, Any],
        conditions: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Schedule a new task for execution."""
        async with self._lock:
            task_id = f"task_{self._next_task_id}"
            self._next_task_id += 1
            
            task = ScheduledTask(
                task_id=task_id,
                user_id=user_id,
                session_id=session_id,
                task_type=task_type,
                execute_at=execute_at,
                task_data=task_data,
                conditions=conditions,
                max_retries=max_retries
            )
            
            self._tasks[task_id] = task
            
            logger.info(f"Scheduled task {task_id} for {execute_at}")
            
            return {
                "success": True,
                "task_id": task_id,
                "execute_at": execute_at.isoformat(),
                "status": "pending",
                "message": f"Task scheduled for {execute_at}"
            }
    
    async def get_tasks(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get tasks for a user, optionally filtered by status."""
        async with self._lock:
            tasks = []
            for task in self._tasks.values():
                if task.user_id == user_id:
                    if status is None or task.status == status:
                        tasks.append(asdict(task))
            return tasks
    
    async def cancel_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """Cancel a scheduled task."""
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.user_id == user_id and task.status == 'pending':
                    task.status = 'cancelled'
                    logger.info(f"Cancelled task {task_id}")
                    return {
                        "success": True,
                        "message": f"Task {task_id} cancelled"
                    }
            
            return {
                "success": False,
                "error": "Task not found or cannot be cancelled"
            }
    
    async def _worker_loop(self) -> None:
        """Main worker loop to check and execute scheduled tasks."""
        while self._running:
            try:
                await self._check_and_execute_tasks()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in agent scheduler worker: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _check_and_execute_tasks(self) -> None:
        """Check for tasks that are ready to execute."""
        now = datetime.now()
        tasks_to_execute = []
        
        async with self._lock:
            for task in self._tasks.values():
                if (task.status == 'pending' and 
                    task.execute_at <= now and
                    (task.conditions is None or await self._check_conditions(task.conditions))):
                    tasks_to_execute.append(task)
        
        # Execute tasks outside the lock to avoid blocking
        for task in tasks_to_execute:
            await self._execute_task(task)
    
    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task."""
        logger.info(f"Executing task {task.task_id}: {task.task_type}")
        
        async with self._lock:
            task.status = 'executing'
        
        try:
            result = await self._execute_task_by_type(
                task.task_type,
                task.task_data,
                task.user_id,
                task.session_id
            )
            
            async with self._lock:
                if result.get("success"):
                    task.status = 'completed'
                    task.executed_at = datetime.now()
                    logger.info(f"Task {task.task_id} completed successfully")
                else:
                    task.retry_count += 1
                    if task.retry_count >= task.max_retries:
                        task.status = 'failed'
                        task.error_message = result.get("error", "Unknown error")
                        logger.error(f"Task {task.task_id} failed after {task.max_retries} retries")
                    else:
                        task.status = 'pending'
                        # Retry in 1 minute
                        task.execute_at = datetime.now() + timedelta(minutes=1)
                        logger.info(f"Task {task.task_id} will retry in 1 minute (attempt {task.retry_count + 1})")
                        
        except Exception as e:
            async with self._lock:
                task.retry_count += 1
                if task.retry_count >= task.max_retries:
                    task.status = 'failed'
                    task.error_message = str(e)
                    logger.error(f"Task {task.task_id} failed with exception: {e}")
                else:
                    task.status = 'pending'
                    task.execute_at = datetime.now() + timedelta(minutes=1)
                    logger.info(f"Task {task.task_id} will retry in 1 minute (attempt {task.retry_count + 1})")
    
    async def _check_conditions(self, conditions: Dict[str, Any]) -> bool:
        """Check if execution conditions are met."""
        # This is a placeholder - implement specific condition checking
        # For example: price targets, market conditions, etc.
        return True
    
    async def _execute_task_by_type(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Execute a task based on its type."""
        logger.info(f"Executing {task_type} task: {task_data}")
        
        try:
            # Import here to avoid circular imports
            from ..integrations.solana.solana_tools import SolanaTools
            from ..integrations.jupiter import JupiterTools
            from ..integrations.pump_fun import PumpFunTools
            from ..config.settings import Settings
            
            # Get the private key for this session
            secure_storage = get_secure_storage()
            private_key_manager = PrivateKeyManager(secure_storage)
            private_key = await private_key_manager.get_private_key(session_id)
            
            if not private_key:
                return {
                    "success": False,
                    "error": "No private key available for this session",
                    "message": "Please authenticate first"
                }
            
            # Execute based on task type
            if task_type == "transfer_sol":
                solana_tools = SolanaTools()
                return await solana_tools.transfer_sol_handler({
                    "to_address": task_data["to_address"],
                    "amount": task_data["amount"],
                    "private_key": private_key
                })
            
            elif task_type == "swap":
                jupiter_tools = JupiterTools()
                return await jupiter_tools.swap_handler({
                    "input_mint": task_data["input_mint"],
                    "output_mint": task_data["output_mint"],
                    "amount": task_data["amount"],
                    "slippage": task_data.get("slippage", 2),
                    "private_key": private_key
                })
            
            elif task_type == "buy_token":
                pump_tools = PumpFunTools()
                return await pump_tools.buy_token_handler({
                    "token_address": task_data["token_address"],
                    "amount_sol": task_data["amount_sol"],
                    "slippage": task_data.get("slippage", 2),
                    "private_key": private_key
                })
            
            elif task_type == "sell_token":
                pump_tools = PumpFunTools()
                return await pump_tools.sell_token_handler({
                    "token_address": task_data["token_address"],
                    "amount_tokens": task_data["amount_tokens"],
                    "slippage": task_data.get("slippage", 2),
                    "private_key": private_key
                })
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown task type: {task_type}"
                }
                
        except Exception as e:
            logger.error(f"Error executing {task_type} task: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Global scheduler instance
_agent_scheduler: Optional[AgentScheduler] = None

async def get_agent_scheduler() -> AgentScheduler:
    """Get the global agent scheduler instance."""
    global _agent_scheduler
    if _agent_scheduler is None:
        _agent_scheduler = AgentScheduler()
        await _agent_scheduler.start()
    return _agent_scheduler
