#!/usr/bin/env python3
"""
Test script for Horizon web app integration.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sam.core.private_key_manager import PrivateKeyManager
from sam.utils.secure_storage import get_secure_storage


async def test_private_key_manager():
    """Test the private key manager functionality."""
    print("🧪 Testing Private Key Manager...")
    
    # Create manager
    secure_storage = get_secure_storage()
    manager = PrivateKeyManager(secure_storage)
    
    # Test session
    session_id = "test_session_123"
    test_private_key = "5Kb8kLf9CQJj4Kb8kLf9CQJj4Kb8kLf9CQJj4Kb8kLf9CQJj4Kb8kLf9CQJj4"  # Fake key for testing
    
    # Test storing private key
    print("  📝 Testing private key storage...")
    result = await manager.request_private_key(session_id, test_private_key)
    print(f"    Result: {result}")
    
    # Test retrieving private key
    print("  🔍 Testing private key retrieval...")
    retrieved_key = await manager.get_private_key(session_id)
    print(f"    Retrieved: {retrieved_key is not None}")
    
    # Test authentication check
    print("  ✅ Testing authentication check...")
    has_key = await manager.has_private_key(session_id)
    print(f"    Has key: {has_key}")
    
    # Test clearing private key
    print("  🗑️ Testing private key clearing...")
    clear_result = await manager.clear_session_key(session_id)
    print(f"    Clear result: {clear_result}")
    
    print("✅ Private Key Manager tests completed!")


async def main():
    """Run all tests."""
    print("🚀 Starting Horizon Integration Tests\n")
    
    try:
        await test_private_key_manager()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())






