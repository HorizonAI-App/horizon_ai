#!/usr/bin/env python3
"""Test wallet configuration in the agent."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

async def test_wallet_config():
    """Test if wallet is configured in the agent."""
    try:
        from sam.core.agent_factory import get_default_factory
        
        print("🔍 Testing wallet configuration...")
        
        # Create agent
        factory = get_default_factory()
        agent = await factory.get_agent()
        
        # Get solana tools
        solana_tools = getattr(agent, "_solana_tools", None)
        if not solana_tools:
            print("❌ No solana_tools found on agent")
            return
        
        print(f"✅ Solana tools found: {solana_tools}")
        print(f"✅ Has keypair: {solana_tools.keypair is not None}")
        print(f"✅ Has wallet address: {solana_tools.wallet_address is not None}")
        print(f"✅ Session ID: {solana_tools.session_id}")
        
        if solana_tools.keypair:
            print(f"✅ Wallet address: {solana_tools.wallet_address}")
        else:
            print("❌ No wallet configured - this is why transfers fail")
            
        # Test the transfer_sol tool directly
        print("\n🧪 Testing transfer_sol tool directly...")
        tool_registry = agent.tools
        transfer_tool = tool_registry._tools.get("transfer_sol")
        
        if transfer_tool:
            print("✅ transfer_sol tool found")
            # Try to call the handler directly
            result = await transfer_tool.handler({
                "to_address": "11111111111111111111111111111112",  # System program
                "amount": 0.001
            })
            print(f"📋 Transfer result: {result}")
        else:
            print("❌ transfer_sol tool not found")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_wallet_config())


