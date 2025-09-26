#!/usr/bin/env python3
"""
Test script for Horizon Streamlit integration.
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


async def test_solana_tools_session_support():
    """Test SolanaTools session support."""
    print("\n🧪 Testing SolanaTools Session Support...")
    
    from sam.integrations.solana.solana_tools import SolanaTools
    
    # Test without private key
    print("  📝 Testing SolanaTools without private key...")
    sol_tools = SolanaTools("https://api.mainnet-beta.solana.com", session_id="test_session")
    
    has_wallet = await sol_tools.has_wallet()
    print(f"    Has wallet: {has_wallet}")
    
    # Test setting session private key
    print("  🔑 Testing setting session private key...")
    test_key = "5Kb8kLf9CQJj4Kb8kLf9CQJj4Kb8kLf9CQJj4Kb8kLf9CQJj4Kb8kLf9CQJj4"
    success = await sol_tools.set_session_private_key(test_key)
    print(f"    Set key success: {success}")
    
    has_wallet_after = await sol_tools.has_wallet()
    print(f"    Has wallet after: {has_wallet_after}")
    
    print("✅ SolanaTools session support tests completed!")


async def main():
    """Run all tests."""
    print("🚀 Starting Horizon Streamlit Integration Tests\n")
    
    try:
        await test_private_key_manager()
        await test_solana_tools_session_support()
        print("\n🎉 All tests passed!")
        print("\n📋 Next steps:")
        print("1. Run: streamlit run examples/streamlit_app/app.py")
        print("2. Navigate to the Wallet page")
        print("3. Enter your private key to authenticate")
        print("4. Go back to chat and ask: 'Check my balance'")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
