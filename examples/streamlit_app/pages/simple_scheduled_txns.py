#!/usr/bin/env python3
"""Simple Scheduled Transactions page that actually works."""

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
    page_title="Simple Scheduled Transactions",
    page_icon="⏰",
    layout="wide"
)

st.title("⏰ Simple Scheduled Transactions")
st.markdown("**This actually works!** Schedule tasks and watch them execute automatically.")

# Auto-refresh every 10 seconds
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

if (datetime.now() - st.session_state.last_refresh).seconds >= 10:
    st.rerun()

def get_tasks() -> List[Dict[str, Any]]:
    """Get tasks from simple scheduler."""
    try:
        from sam.core.simple_scheduler import get_simple_scheduler
        scheduler = get_simple_scheduler()
        return scheduler.get_tasks()
    except Exception as e:
        st.error(f"Error getting tasks: {e}")
        return []

def schedule_task(task_type: str, minutes: int, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Schedule a task."""
    try:
        from sam.core.simple_scheduler import get_simple_scheduler
        scheduler = get_simple_scheduler()
        
        # Calculate execute time
        execute_at = datetime.now() + timedelta(minutes=minutes)
        
        # Generate task ID
        tasks = scheduler.get_tasks()
        task_id = max([t["id"] for t in tasks], default=0) + 1
        
        # Schedule the task
        success = scheduler.schedule_task(
            task_id=task_id,
            execute_at=execute_at,
            task_data=task_data
        )
        
        if success:
            return {
                "success": True,
                "task_id": task_id,
                "execute_at": execute_at.isoformat()
            }
        else:
            return {"success": False, "error": "Failed to schedule"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def render_task_card(task: Dict[str, Any]) -> None:
    """Render a task card."""
    task_id = task["id"]
    status = task["status"]
    execute_at = task["execute_at"]
    task_data = task["task_data"]
    created_at = task["created_at"]
    executed_at = task.get("executed_at")
    error_message = task.get("error_message")
    
    # Parse datetime
    if isinstance(execute_at, str):
        execute_dt = datetime.fromisoformat(execute_at)
    else:
        execute_dt = execute_at
    
    if isinstance(created_at, str):
        created_dt = datetime.fromisoformat(created_at)
    else:
        created_dt = created_at
    
    # Status styling
    status_config = {
        "pending": ("🟡", "Pending", "info"),
        "executing": ("🔵", "Executing", "info"),
        "completed": ("🟢", "Completed", "success"),
        "failed": ("🔴", "Failed", "error")
    }
    
    status_icon, status_text, status_type = status_config.get(status, ("❓", status.title(), "info"))
    
    # Check if overdue
    now = datetime.now()
    is_overdue = status == "pending" and execute_dt < now
    if is_overdue:
        overdue_seconds = int((now - execute_dt).total_seconds())
        status_text += f" ⚠️ OVERDUE ({overdue_seconds}s)"
    
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            if status_type == "success":
                st.success(f"**{status_icon} {status_text}**")
            elif status_type == "error":
                st.error(f"**{status_icon} {status_text}**")
            else:
                st.info(f"**{status_icon} {status_text}**")
            
            st.markdown(f"**Task ID:** {task_id}")
            st.markdown(f"**Scheduled:** {execute_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            st.markdown(f"**Created:** {created_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if executed_at:
                if isinstance(executed_at, str):
                    executed_dt = datetime.fromisoformat(executed_at)
                else:
                    executed_dt = executed_at
                st.markdown(f"**Executed:** {executed_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if task_data:
                st.markdown("**Task Data:**")
                st.json(task_data)
            
            if error_message:
                st.error(f"**Error:** {error_message}")
        
        with col2:
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
        
        with col3:
            # Show countdown for pending tasks
            if status == "pending":
                if execute_dt > now:
                    remaining = execute_dt - now
                    minutes = int(remaining.total_seconds() / 60)
                    seconds = int(remaining.total_seconds() % 60)
                    st.metric("Time Left", f"{minutes}m {seconds}s")
                else:
                    st.metric("Overdue", f"{overdue_seconds}s")
        
        st.divider()

def render_simple_scheduled_tasks_page():
    """Render the simple scheduled tasks page."""
    
    # Quick Schedule
    st.subheader("🚀 Quick Schedule New Task")
    
    col1, col2 = st.columns(2)
    
    with col1:
        task_type = st.selectbox(
            "Task Type",
            ["transfer_sol", "swap", "buy_token", "sell_token", "custom"],
            key="simple_task_type"
        )
        
        minutes = st.number_input(
            "Execute in (minutes)",
            min_value=1,
            max_value=60,
            value=2,
            key="simple_minutes"
        )
    
    with col2:
        task_data_json = st.text_area(
            "Task Data (JSON)",
            value='{"to_address": "376fAJt8fW8gfbosr7Kzc3RuSKGHVcYGGK1p9mGm468v", "amount": 0.001}',
            key="simple_task_data"
        )
    
    if st.button("📅 Schedule Task", type="primary", use_container_width=True):
        try:
            task_data = json.loads(task_data_json)
            result = schedule_task(task_type, minutes, task_data)
            
            if result.get("success"):
                st.success(f"✅ Task scheduled! ID: {result.get('task_id')}")
                st.rerun()
            else:
                st.error(f"❌ Failed: {result.get('error')}")
                
        except json.JSONDecodeError:
            st.error("❌ Invalid JSON in task data")
        except Exception as e:
            st.error(f"❌ Error: {e}")
    
    st.divider()
    
    # Refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh", type="secondary"):
            st.rerun()
    
    with col2:
        st.markdown("**Auto-refreshes every 10 seconds**")
    
    st.divider()
    
    # Get and display tasks
    tasks = get_tasks()
    
    if not tasks:
        st.info("No scheduled tasks found. Schedule one above!")
        return
    
    # Summary
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
    
    st.divider()
    
    # Display tasks
    for task in sorted(tasks, key=lambda x: x["execute_at"], reverse=True):
        render_task_card(task)

# Render the page
render_simple_scheduled_tasks_page()
