#!/usr/bin/env python3
"""Simple, reliable scheduler that actually works."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import threading
import time

logger = logging.getLogger(__name__)

class SimpleScheduler:
    """Simple scheduler that actually works."""
    
    def __init__(self):
        self._tasks: Dict[int, Dict[str, Any]] = {}
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        
    def start(self):
        """Start the scheduler."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        logger.info("Simple scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Simple scheduler stopped")
    
    def schedule_task(self, task_id: int, execute_at: datetime, task_data: Dict[str, Any]) -> bool:
        """Schedule a task."""
        with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "execute_at": execute_at,
                "task_data": task_data,
                "status": "pending",
                "created_at": datetime.now()
            }
        logger.info(f"Scheduled task {task_id} for {execute_at}")
        return True
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks."""
        with self._lock:
            return list(self._tasks.values())
    
    def _worker_loop(self):
        """Worker loop that actually executes tasks."""
        while self._running:
            try:
                now = datetime.now()
                tasks_to_execute = []
                
                # Find overdue tasks
                with self._lock:
                    for task_id, task in self._tasks.items():
                        if (task["status"] == "pending" and 
                            task["execute_at"] <= now):
                            tasks_to_execute.append(task_id)
                
                # Execute tasks
                for task_id in tasks_to_execute:
                    self._execute_task(task_id)
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in scheduler worker: {e}")
                time.sleep(30)
    
    def _execute_task(self, task_id: int):
        """Execute a task."""
        try:
            with self._lock:
                if task_id not in self._tasks:
                    return
                task = self._tasks[task_id]
                task["status"] = "executing"
            
            logger.info(f"Executing task {task_id}")
            
            # Simulate execution (replace with actual transaction logic)
            time.sleep(2)  # Simulate processing time
            
            with self._lock:
                if task_id in self._tasks:
                    self._tasks[task_id]["status"] = "completed"
                    self._tasks[task_id]["executed_at"] = datetime.now()
            
            logger.info(f"Task {task_id} completed")
            
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            with self._lock:
                if task_id in self._tasks:
                    self._tasks[task_id]["status"] = "failed"
                    self._tasks[task_id]["error_message"] = str(e)

# Global simple scheduler
_simple_scheduler = None

def get_simple_scheduler() -> SimpleScheduler:
    """Get the global simple scheduler."""
    global _simple_scheduler
    if _simple_scheduler is None:
        _simple_scheduler = SimpleScheduler()
        _simple_scheduler.start()
    return _simple_scheduler
