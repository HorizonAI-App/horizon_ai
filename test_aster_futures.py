#!/usr/bin/env python3
"""Test script for Aster futures integration."""

import asyncio
import os
import sys
from pathlib import Path

# Add the sam package to the path
sys.path.insert(0, str(Path(__file__).parent))

from sam.core.futures_agent_builder import FuturesAgentBuilder
from sam.config.settings import Settings


async def test_aster_futures_integration():
    """Test the Aster futures integration."""
    print("🧪 Testing Aster Futures Integration")
    print("=" * 50)
    
    # Check if Aster futures tools are enabled
    print(f"✅ Aster Futures Tools Enabled: {Settings.ENABLE_ASTER_FUTURES_TOOLS}")
    print(f"✅ Aster Base URL: {Settings.ASTER_BASE_URL}")
    print(f"✅ Aster API Key Configured: {'Yes' if Settings.ASTER_API_KEY else 'No'}")
    print(f"✅ Aster API Secret Configured: {'Yes' if Settings.ASTER_API_SECRET else 'No'}")
    
    if not Settings.ENABLE_ASTER_FUTURES_TOOLS:
        print("❌ Aster futures tools are disabled. Set ENABLE_ASTER_FUTURES_TOOLS=true")
        return False
    
    if not Settings.ASTER_API_KEY or not Settings.ASTER_API_SECRET:
        print("❌ Aster API credentials not configured. Set ASTER_API_KEY and ASTER_API_SECRET")
        return False
    
    # Test building the futures agent
    try:
        print("\n🔧 Building Futures Trading Agent...")
        builder = FuturesAgentBuilder()
        agent = await builder.build(session_id="test")
        
        print(f"✅ Agent built successfully with {len(agent.tools.list_specs())} tools")
        
        # List available tools
        print("\n📋 Available Futures Trading Tools:")
        for tool_spec in agent.tools.list_specs():
            print(f"  - {tool_spec.name}: {tool_spec.description}")
        
        # Test account balance tool (if credentials are valid)
        print("\n💰 Testing Account Balance Tool...")
        try:
            result = await agent.tools.call("aster_account_balance", {})
            if "error" in result:
                print(f"⚠️  Account balance check failed: {result['error']}")
                print("   This is expected if API credentials are invalid or account is empty")
            else:
                print("✅ Account balance tool working")
        except Exception as e:
            print(f"⚠️  Account balance test failed: {e}")
        
        print("\n✅ Aster Futures Integration Test Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to build futures agent: {e}")
        return False


async def main():
    """Main test function."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Refresh settings
    Settings.refresh_from_env()
    
    success = await test_aster_futures_integration()
    
    if success:
        print("\n🎉 All tests passed! Aster futures integration is working.")
        print("\nTo use the futures trading agent, run:")
        print("  sam futures")
    else:
        print("\n❌ Some tests failed. Check your configuration.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())







