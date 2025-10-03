#!/usr/bin/env python3
"""
Clear All Database Data Script
Uses the database_utils.py to completely clear all user data from the database.
This ensures a clean slate for testing browser-specific storage.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sam.utils.database_utils import clear_all_user_data, get_database_info

async def main():
    """Main function to clear all database data."""
    print("🧹 Horizon Database Data Cleaner")
    print("=" * 50)
    
    # Get database info before clearing
    print("📊 Getting database information...")
    db_info = await get_database_info()
    
    print(f"Database path: {db_info['db_path']}")
    print(f"Database exists: {db_info['exists']}")
    
    if not db_info['exists']:
        print("❌ Database file not found. Nothing to clear.")
        return
    
    print(f"Database size: {db_info['size_bytes']:,} bytes ({db_info['size_bytes'] / 1024 / 1024:.2f} MB)")
    print(f"Total records: {db_info['total_records']}")
    
    if db_info['tables']:
        print("\n📋 Tables found:")
        for table in db_info['tables']:
            print(f"  - {table['name']}: {table['records']} records")
    
    print("\n⚠️  WARNING: This will delete ALL user data!")
    print("This includes:")
    print("- All user sessions and conversation history")
    print("- All user preferences and settings")
    print("- All wallet information and private keys")
    print("- All trading history and data")
    print("- All secure data entries")
    
    # Confirm before proceeding
    response = input("\nAre you sure you want to clear ALL database data? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("❌ Operation cancelled.")
        return
    
    print("\n🚀 Starting database cleanup...")
    
    # Clear all user data
    success = await clear_all_user_data()
    
    if success:
        print("✅ Database cleared successfully!")
        
        # Get database info after clearing
        print("\n📊 Database info after clearing:")
        db_info_after = await get_database_info()
        print(f"Database size: {db_info_after['size_bytes']:,} bytes ({db_info_after['size_bytes'] / 1024 / 1024:.2f} MB)")
        print(f"Total records: {db_info_after['total_records']}")
        
        print("\n🎉 Database cleanup completed!")
        print("\nNext steps:")
        print("1. Deploy your updated Streamlit app")
        print("2. Test with different browser profiles")
        print("3. Each browser profile should now have isolated data")
        print("4. No more cross-profile private key sharing!")
    else:
        print("❌ Failed to clear database. Check the logs for details.")

if __name__ == "__main__":
    asyncio.run(main())



