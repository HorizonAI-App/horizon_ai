#!/usr/bin/env python3
"""Simple script to clear the Horizon database."""

import sqlite3
import os
import sys


def clear_database():
    """Clear all data from the database."""
    # Default database path (same as in settings.py)
    db_path = ".sam/sam_memory.db"
    
    print("🗄️ Horizon Database Clearer")
    print("=" * 40)
    print(f"Database path: {db_path}")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("❌ Database file not found. Nothing to clear.")
        print(f"Looking for: {os.path.abspath(db_path)}")
        return False
    
    # Get database size before clearing
    db_size = os.path.getsize(db_path)
    print(f"Database size: {db_size:,} bytes ({db_size / 1024 / 1024:.2f} MB)")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of all tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in database.")
            conn.close()
            return True
        
        print(f"\nFound {len(tables)} tables:")
        total_records = 0
        
        # Count records in each table
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()
            record_count = count[0] if count else 0
            total_records += record_count
            print(f"  - {table_name}: {record_count:,} records")
        
        print(f"\nTotal records: {total_records:,}")
        
        if total_records == 0:
            print("Database is already empty.")
            conn.close()
            return True
        
        print("\n⚠️  WARNING: This will delete ALL user data!")
        print("This includes:")
        print("  - All user sessions and conversation history")
        print("  - All user preferences and settings")
        print("  - All wallet information and private keys")
        print("  - All trading history and data")
        
        # Confirm deletion
        try:
            response = input("\nAre you sure you want to clear the database? Type 'yes' to confirm: ")
            if response.lower().strip() != 'yes':
                print("Operation cancelled.")
                conn.close()
                return False
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            conn.close()
            return False
        
        # Clear each table
        print("\nClearing database...")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"DELETE FROM {table_name}")
            print(f"  ✅ Cleared table: {table_name}")
        
        # Reset auto-increment counters
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
            except Exception:
                # Table might not have auto-increment, ignore error
                pass
        
        conn.commit()
        conn.close()
        print("\n✅ Database cleared successfully!")
        
        # Show updated size
        new_size = os.path.getsize(db_path)
        print(f"Database size after clearing: {new_size:,} bytes ({new_size / 1024 / 1024:.2f} MB)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        return False


def main():
    """Main function."""
    success = clear_database()
    
    if success:
        print("\n🎉 Database clearing completed!")
        print("\nNext steps:")
        print("1. Deploy your updated Streamlit app")
        print("2. Test with multiple browser windows to verify user isolation")
        print("3. Users will need to re-enter their wallet information")
        print("4. Each browser session will now have unique, isolated data")
    else:
        print("\n❌ Database clearing failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()