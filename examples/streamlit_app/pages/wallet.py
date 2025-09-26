# ruff: noqa: E402

import sys
from pathlib import Path
import streamlit as st

# Ensure parent directory import for shared UI helpers
_PAGES_DIR = Path(__file__).resolve().parent
_APP_DIR = _PAGES_DIR.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
from ui_shared import (
    inject_css,
    ensure_env_loaded,
    agent_ready_marker,
    run_sync,
    get_local_context,
)  # noqa: E402
from sam.web.session import get_agent  # noqa: E402
from sam.core.private_key_manager import PrivateKeyManager  # noqa: E402
from sam.utils.secure_storage import get_secure_storage  # noqa: E402


st.set_page_config(page_title="Wallet", page_icon="👛", layout="wide")
inject_css()
ensure_env_loaded()
agent_ready_marker()

st.title("👛 Wallet")
st.caption("Manage your wallet and private key for trading")

# Initialize private key manager
private_key_manager = PrivateKeyManager(get_secure_storage())

# Get session ID
session_id = st.session_state.get("session_id", "default")

# Check if user is authenticated
async def check_auth_status():
    return await private_key_manager.has_private_key(session_id)

is_authenticated = run_sync(check_auth_status())

# Update SolanaTools with session private key if authenticated
async def update_solana_tools_with_session_key():
    if is_authenticated:
        try:
            agent = await get_agent(get_local_context())
            sol_tools = getattr(agent, "_solana_tools", None)
            if sol_tools and not await sol_tools.has_wallet():
                private_key = await private_key_manager.get_private_key(session_id)
                if private_key:
                    await sol_tools.set_session_private_key(private_key)
        except Exception as e:
            st.error(f"Failed to update Solana tools: {e}")

if is_authenticated:
    run_sync(update_solana_tools_with_session_key())

# Authentication Section
st.subheader("🔐 Authentication")

if not is_authenticated:
    st.info("🔑 Please provide your private key to enable trading functionality.")
    
    with st.form("private_key_form"):
        private_key = st.text_input(
            "Private Key", 
            type="password",
            placeholder="Enter your Solana private key (Base58 format)",
            help="Your private key will be encrypted and stored securely for this session only."
        )
        
        submitted = st.form_submit_button("🔐 Authenticate", use_container_width=True)
        
        if submitted and private_key:
            async def authenticate():
                result = await private_key_manager.request_private_key(session_id, private_key)
                return result
            
            try:
                result = run_sync(authenticate())
                if result.get("success"):
                    st.success("✅ Private key stored securely! You can now perform transactions.")
                    st.rerun()
                else:
                    st.error(f"❌ Authentication failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"❌ Authentication failed: {str(e)}")
else:
    st.success("✅ Authenticated - Private key is securely stored for this session")
    
    if st.button("🗑️ Clear Authentication", type="secondary"):
        async def clear_auth():
            result = await private_key_manager.clear_session_key(session_id)
            return result
        
        try:
            result = run_sync(clear_auth())
            if result.get("success"):
                st.success("🔓 Authentication cleared successfully")
                st.rerun()
            else:
                st.error(f"❌ Failed to clear authentication: {result.get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"❌ Failed to clear authentication: {str(e)}")

st.divider()

# Wallet Information Section
st.subheader("💼 Wallet Information")

try:
    agent = run_sync(get_agent(get_local_context()))
except Exception as e:
    agent = None
    st.error(f"Failed to initialize agent: {e}")

sol_tools = getattr(agent, "_solana_tools", None) if agent else None
wallet = getattr(sol_tools, "wallet_address", None)

if wallet:
    st.write(f"**Address:** `{wallet}`")
    
    # Copy to clipboard button
    if st.button("📋 Copy Address", use_container_width=False):
        st.write("Address copied to clipboard!")
else:
    st.warning("⚠️ No wallet configured. Please authenticate with your private key first.")

st.divider()

# Balance Section
st.subheader("💰 Balance")

if st.button("🔄 Check Balance", use_container_width=True, disabled=not is_authenticated):
    if not is_authenticated:
        st.warning("Please authenticate with your private key first.")
    elif not sol_tools:
        st.warning("Solana tools are disabled or unavailable.")
    else:
        try:
            result = run_sync(sol_tools.get_balance())
            if isinstance(result, dict):
                if "error" in result:
                    if result.get("requires_private_key"):
                        st.warning("🔑 Please authenticate with your private key to check balance.")
                    else:
                        st.warning(result.get("error") or "Unknown error")
                else:
                    # Display balance in a nice format
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric(
                            "SOL Balance", 
                            f"{result.get('sol_balance', 0):.4f} SOL",
                            f"${result.get('sol_usd', 0):.2f} USD"
                        )
                    
                    with col2:
                        st.metric(
                            "Total Portfolio", 
                            f"${result.get('total_portfolio_usd', 0):.2f} USD",
                            f"{result.get('token_count', 0)} tokens"
                        )
                    
                    # Show token details if available
                    tokens = result.get('tokens', [])
                    if tokens:
                        st.subheader("🪙 Token Holdings")
                        for token in tokens[:10]:  # Show first 10 tokens
                            st.write(f"• {token.get('mint', 'Unknown')}: {token.get('uiAmount', 0):.4f}")
                        
                        if len(tokens) > 10:
                            st.caption(f"... and {len(tokens) - 10} more tokens")
            else:
                st.info("No balance data returned.")
        except Exception as e:
            st.error(f"Error checking balance: {str(e)}")

# Trading Instructions
st.divider()
st.subheader("📖 How to Trade")

if is_authenticated:
    st.success("🎉 You're all set! You can now:")
    st.write("• Go to the main chat and ask me to check your balance")
    st.write("• Request to buy tokens: 'Buy 1000 BONK tokens'")
    st.write("• Transfer SOL: 'Send 0.1 SOL to [address]'")
    st.write("• Get token information: 'Tell me about BONK token'")
else:
    st.info("🔐 Please authenticate with your private key above to start trading.")
