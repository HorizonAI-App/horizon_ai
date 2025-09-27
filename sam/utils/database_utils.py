"""Database utility functions for managing the Horizon database."""

import asyncio
import os
import logging
from typing import Optional, List, Dict, Any

import aiosqlite
from sam.config.settings import Settings

logger = logging.getLogger(__name__)


async def clear_all_user_data(db_path: Optional[str] = None) -> bool:
    """Clear all user data from the database.
    
    Args:
        db_path: Optional path to database file. If not provided, uses Settings.SAM_DB_PATH
        
    Returns:
        True if successful, False otherwise
    """
    if db_path is None:
        db_path = Settings.SAM_DB_PATH
    
    # Check if database exists
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found: {db_path}")
        return False
    
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Get list of all tables
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = await cursor.fetchall()
            
            if not tables:
                logger.info("No tables found in database.")
                return True
            
            logger.info(f"Clearing {len(tables)} tables from database")
            
            # Clear each table
            for table in tables:
                table_name = table[0]
                await conn.execute(f"DELETE FROM {table_name}")
                logger.info(f"Cleared table: {table_name}")
            
            # Reset auto-increment counters
            for table in tables:
                table_name = table[0]
                try:
                    await conn.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
                except Exception:
                    # Table might not have auto-increment, ignore error
                    pass
            
            await conn.commit()
            logger.info("Database cleared successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        return False


async def get_database_info(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Get information about the database.
    
    Args:
        db_path: Optional path to database file. If not provided, uses Settings.SAM_DB_PATH
        
    Returns:
        Dictionary with database information
    """
    if db_path is None:
        db_path = Settings.SAM_DB_PATH
    
    info = {
        "db_path": db_path,
        "exists": os.path.exists(db_path),
        "size_bytes": 0,
        "tables": [],
        "total_records": 0
    }
    
    if not info["exists"]:
        return info
    
    try:
        info["size_bytes"] = os.path.getsize(db_path)
        
        async with aiosqlite.connect(db_path) as conn:
            # Get list of all tables
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = await cursor.fetchall()
            
            total_records = 0
            for table in tables:
                table_name = table[0]
                
                # Get record count for each table
                count_cursor = await conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = await count_cursor.fetchone()
                record_count = count[0] if count else 0
                total_records += record_count
                
                info["tables"].append({
                    "name": table_name,
                    "records": record_count
                })
            
            info["total_records"] = total_records
            
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        info["error"] = str(e)
    
    return info


async def clear_user_sessions(user_id: str, db_path: Optional[str] = None) -> bool:
    """Clear sessions for a specific user.
    
    Args:
        user_id: User ID to clear sessions for
        db_path: Optional path to database file. If not provided, uses Settings.SAM_DB_PATH
        
    Returns:
        True if successful, False otherwise
    """
    if db_path is None:
        db_path = Settings.SAM_DB_PATH
    
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found: {db_path}")
        return False
    
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Clear sessions for specific user
            cursor = await conn.execute(
                "DELETE FROM sessions WHERE user_id = ?", (user_id,)
            )
            deleted_sessions = cursor.rowcount
            
            # Clear preferences for specific user
            cursor = await conn.execute(
                "DELETE FROM preferences WHERE user_id = ?", (user_id,)
            )
            deleted_preferences = cursor.rowcount
            
            await conn.commit()
            
            logger.info(f"Cleared {deleted_sessions} sessions and {deleted_preferences} preferences for user {user_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error clearing user sessions: {e}")
        return False


async def backup_database(db_path: Optional[str] = None, backup_path: Optional[str] = None) -> bool:
    """Create a backup of the database.
    
    Args:
        db_path: Optional path to database file. If not provided, uses Settings.SAM_DB_PATH
        backup_path: Optional path for backup file. If not provided, creates timestamped backup
        
    Returns:
        True if successful, False otherwise
    """
    if db_path is None:
        db_path = Settings.SAM_DB_PATH
    
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found: {db_path}")
        return False
    
    if backup_path is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error backing up database: {e}")
        return False
