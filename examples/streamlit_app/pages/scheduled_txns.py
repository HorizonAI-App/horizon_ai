#!/usr/bin/env python3
"""Scheduled Transactions page for Streamlit app."""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Any, List

# Import shared utilities
import sys
from pathlib import Path

# Add the parent directory to the path for imports
_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from ui_shared import run_sync, get_local_context

st.set_page_config(
    page_title="Scheduled Transactions",
    page_icon="⏰",
    layout="wide"
)

st.title("⏰ Scheduled Transactions")
st.markdown("Manage your scheduled transactions - view, monitor, and cancel as needed.")

# Auto-refresh every 30 seconds
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

if (datetime.now() - st.session_state.last_refresh).seconds >= 30:
    st.rerun()

async def get_scheduled_tasks() -> List[Dict[str, Any]]:
    """Get scheduled tasks from the scheduler."""
    try:
        from sam.core.scheduler import get_scheduler_manager
        scheduler = await get_scheduler_manager()
        context = get_local_context()
        return await scheduler.get_scheduled_transactions(context.user_id)
    except Exception as e:
        st.error(f"Error getting scheduled tasks: {e}")
        return []

async def cancel_task(task_id: str) -> Dict[str, Any]:
    """Cancel a scheduled task."""
    try:
        from sam.core.scheduler import get_scheduler_manager
        scheduler = await get_scheduler_manager()
        context = get_local_context()
        result = await scheduler.cancel_transaction(int(task_id), context.user_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

def render_transaction_summary(tasks: List[Dict[str, Any]]) -> None:
    """Render transaction summary cards."""
    total = len(tasks)
    pending = len([t for t in tasks if t["status"] == "pending"])
    completed = len([t for t in tasks if t["status"] == "completed"])
    failed = len([t for t in tasks if t["status"] == "failed"])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total", total)
    
    with col2:
        st.metric("Pending", pending)
    
    with col3:
        st.metric("Completed", completed)
    
    with col4:
        st.metric("Failed", failed)

def render_transaction_card(task: Dict[str, Any]) -> None:
    """Render a transaction card with details and actions."""
    task_id = task["id"]
    task_type = task["transaction_type"]
    status = task["status"]
    execute_at = task["schedule_time"]
    task_data = task["transaction_data"]
    created_at = task["created_at"]
    executed_at = task.get("executed_at")
    error_message = task.get("error_message")
    retry_count = task.get("retry_count", 0)
    max_retries = task.get("max_retries", 3)
    
    # Parse datetime strings - handle different formats
    if isinstance(execute_at, str):
        if execute_at.endswith('Z'):
            execute_dt = datetime.fromisoformat(execute_at.replace('Z', '+00:00'))
        else:
            execute_dt = datetime.fromisoformat(execute_at)
    else:
        execute_dt = execute_at
    
    if isinstance(created_at, str):
        if created_at.endswith('Z'):
            created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        else:
            created_dt = datetime.fromisoformat(created_at)
    else:
        created_dt = created_at
    
    # Status color and icon
    status_config = {
        "pending": ("🟡", "Pending"),
        "executing": ("🔵", "Executing"),
        "completed": ("🟢", "Completed"),
        "failed": ("🔴", "Failed"),
        "cancelled": ("⚫", "Cancelled")
    }
    
    status_icon, status_text = status_config.get(status, ("❓", status.title()))
    
    # Check if overdue
    now = datetime.now()
    is_overdue = status == "pending" and execute_dt < now
    overdue_text = " ⚠️ OVERDUE" if is_overdue else ""
    
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"**{status_icon} {status_text}{overdue_text}**")
            st.markdown(f"**Type:** {task_type.replace('_', ' ').title()}")
            st.markdown(f"**Scheduled:** {execute_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            st.markdown(f"**Created:** {created_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if executed_at:
                if isinstance(executed_at, str):
                    if executed_at.endswith('Z'):
                        executed_dt = datetime.fromisoformat(executed_at.replace('Z', '+00:00'))
                    else:
                        executed_dt = datetime.fromisoformat(executed_at)
                else:
                    executed_dt = executed_at
                st.markdown(f"**Executed:** {executed_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if retry_count > 0:
                st.markdown(f"**Retries:** {retry_count}/{max_retries}")
            
            # Show task data
            if task_data:
                st.markdown("**Task Data:**")
                st.json(task_data)
            
            # Show error message if failed
            if error_message:
                st.error(f"**Error:** {error_message}")
        
        with col2:
            if status == "pending":
                if st.button("❌ Cancel", key=f"cancel_{task_id}", type="secondary"):
                    with st.spinner("Cancelling task..."):
                        result = run_sync(cancel_task(task_id))
                        if result.get("success"):
                            st.success("Task cancelled!")
                            st.rerun()
                        else:
                            st.error(f"Failed to cancel: {result.get('error')}")
        
        with col3:
            if status == "completed":
                st.success("✅ Done")
            elif status == "failed":
                st.error("❌ Failed")
            elif status == "executing":
                st.info("🔄 Running")
            elif is_overdue:
                st.warning("⏰ Overdue")
            else:
                st.info("⏳ Waiting")
        
        st.divider()

def render_scheduled_tasks_page():
    """Render the main scheduled tasks page."""
    
    # Quick Schedule New Transaction
    with st.expander("⚡ Quick Schedule New Transaction"):
        st.markdown("**Schedule a new transaction:**")
        
        task_type = st.selectbox(
            "Task Type",
            ["transfer_sol", "swap", "buy_token", "sell_token"],
            key="quick_task_type"
        )
        
        execute_at = st.text_input(
            "Execute At",
            placeholder="e.g., 'in 5 minutes', 'in 1 hour', '2024-01-01 12:00:00'",
            key="quick_execute_at"
        )
        
        task_data_json = st.text_area(
            "Task Data (JSON)",
            placeholder='{"to_address": "address", "amount": 0.001}',
            key="quick_task_data"
        )
        
        if st.button("Schedule Task", type="primary"):
            if execute_at and task_data_json:
                try:
                    task_data = json.loads(task_data_json)
                    
                    # Schedule the task
                    async def _schedule_task():
                        from sam.core.scheduler import get_scheduler_manager
                        scheduler = await get_scheduler_manager()
                        context = get_local_context()
                        
                        return await scheduler.schedule_transaction(
                            user_id=context.user_id,
                            session_id=context.session_id,
                            transaction_type=task_type,
                            schedule_time=execute_at,
                            transaction_data=task_data
                        )
                    
                    result = run_sync(_schedule_task())
                    
                    if result.get("success"):
                        st.success(f"Task scheduled! ID: {result.get('transaction_id')}")
                        st.rerun()
                    else:
                        st.error(f"Failed to schedule: {result.get('error')}")
                        
                except json.JSONDecodeError:
                    st.error("Invalid JSON in task data")
                except Exception as e:
                    st.error(f"Error scheduling task: {e}")
            else:
                st.error("Please fill in all fields")
    
    # Refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh", type="primary"):
            st.rerun()
    
    with col2:
        st.markdown("**Auto-refreshes every 30 seconds**")
    
    st.divider()
    
    # Get scheduled tasks
    tasks = run_sync(get_scheduled_tasks())
    
    if not tasks:
        st.info("No scheduled tasks found.")
        return
    
    # Render transaction summary
    render_transaction_summary(tasks)
    
    st.divider()
    
    # Filter and sort options
    col1, col2 = st.columns(2)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "pending", "executing", "completed", "failed", "cancelled"],
            key="status_filter"
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Schedule Time", "Created Time", "Status", "Type"],
            key="sort_by"
        )
    
    # Filter tasks
    if status_filter != "All":
        tasks = [task for task in tasks if task["status"] == status_filter]
    
    # Sort tasks
    if sort_by == "Schedule Time":
        tasks.sort(key=lambda x: x["schedule_time"], reverse=True)
    elif sort_by == "Created Time":
        tasks.sort(key=lambda x: x["created_at"], reverse=True)
    elif sort_by == "Status":
        tasks.sort(key=lambda x: x["status"])
    elif sort_by == "Type":
        tasks.sort(key=lambda x: x["transaction_type"])
    
    # Display tasks
    for task in tasks:
        render_transaction_card(task)

# Render the page
render_scheduled_tasks_page()