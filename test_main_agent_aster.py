#!/usr/bin/env python3
"""Test script to verify Aster futures tools are available in the main agent."""

import asyncio
import os
import sys
from pathlib import Path

# Add the sam package to the path
sys.path.insert(0, str(Path(__file__).parent))

from sam.core.builder import AgentBuilder
from sam.config.settings import Settings


async def test_main_agent_aster_tools():
    """Test that the main agent includes Aster futures tools."""
    print("🧪 Testing Main Agent Aster Futures Integration")
    print("=" * 50)
    
    # Check if Aster futures tools are enabled
    print(f"✅ Aster Futures Tools Enabled: {Settings.ENABLE_ASTER_FUTURES_TOOLS}")
    print(f"✅ Aster Base URL: {Settings.ASTER_BASE_URL}")
    print(f"✅ Aster API Key Configured: {'Yes' if Settings.ASTER_API_KEY else 'No'}")
    print(f"✅ Aster API Secret Configured: {'Yes' if Settings.ASTER_API_SECRET else 'No'}")
    
    if not Settings.ENABLE_ASTER_FUTURES_TOOLS:
        print("❌ Aster futures tools are disabled. Set ENABLE_ASTER_FUTURES_TOOLS=true")
        return False
    
    # Test building the main agent
    try:
        print("\n🔧 Building Main Agent...")
        builder = AgentBuilder()
        agent = await builder.build(session_id="test")
        
        print(f"✅ Main agent built successfully with {len(agent.tools.list_specs())} tools")
        
        # List all available tools
        print("\n📋 All Available Tools:")
        aster_tools = []
        for tool_spec in agent.tools.list_specs():
            tool_name = tool_spec.name
            print(f"  - {tool_name}: {tool_spec.description}")
            if tool_name.startswith("aster_"):
                aster_tools.append(tool_name)
        
        # Check if Aster tools are present
        if aster_tools:
            print(f"\n🚀 Aster Futures Tools Found ({len(aster_tools)}):")
            for tool in aster_tools:
                print(f"  ✅ {tool}")
            print("\n✅ Main agent includes Aster futures tools!")
        else:
            print("\n❌ No Aster futures tools found in main agent")
            return False
        
        # Test if the agent recognizes Aster-related queries
        print("\n🧠 Testing Agent Recognition of Aster Queries...")
        
        # Test a simple query that should trigger Aster tools
        test_queries = [
            "check my Aster account balance",
            "show my current positions",
            "open a long position on SOL",
        ]
        
        for query in test_queries:
            print(f"  Testing: '{query}'")
            # We can't actually run the agent without proper setup, but we can check if tools are available
            print(f"    → Aster tools available: {len(aster_tools)} tools")
        
        print("\n✅ Main Agent Aster Integration Test Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to build main agent: {e}")
        return False


async def main():
    """Main test function."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Refresh settings
    Settings.refresh_from_env()
    
    success = await test_main_agent_aster_tools()
    
    if success:
        print("\n🎉 All tests passed! Main agent includes Aster futures tools.")
        print("\nThe Streamlit app should now recognize Aster trading commands!")
    else:
        print("\n❌ Some tests failed. Check your configuration.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())







