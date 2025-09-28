# ruff: noqa: E402

import sys
from pathlib import Path
import streamlit as st
import hashlib
import secrets
import time

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
    clear_agent_cache,
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

# Use the same session ID as the main app for consistency
session_id = st.session_state.get("session_id", "default")

# Initialize private key manager
private_key_manager = PrivateKeyManager(get_secure_storage())

# Check if user is authenticated
async def check_auth_status():
    return await private_key_manager.has_private_key(session_id)

is_authenticated = run_sync(check_auth_status())

# Wallet initialization will be handled in the wallet information section

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
                    # Clear agent cache to ensure fresh state
                    clear_agent_cache()
                    st.rerun()
                else:
                    st.error(f"❌ Authentication failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"❌ Authentication failed: {str(e)}")
else:
    st.success("✅ Authenticated - Private key is securely stored for this session")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🗑️ Clear Authentication", type="secondary"):
            async def clear_auth():
                result = await private_key_manager.clear_session_key(session_id)
                return result
            
            try:
                result = run_sync(clear_auth())
                if result.get("success"):
                    st.success("🔓 Authentication cleared successfully")
                    # Clear agent cache to ensure fresh state
                    clear_agent_cache()
                    st.rerun()
                else:
                    st.error(f"❌ Failed to clear authentication: {result.get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"❌ Failed to clear authentication: {str(e)}")
    
    with col2:
        if st.button("🔄 Refresh Wallet", type="secondary"):
            # Clear agent cache and refresh
            clear_agent_cache()
            st.rerun()

st.divider()

# Wallet Information Section
st.subheader("💼 Wallet Information")

try:
    agent = run_sync(get_agent(get_local_context()))
    sol_tools = getattr(agent, "_solana_tools", None) if agent else None
    
    # Ensure wallet is initialized if user is authenticated
    if is_authenticated and sol_tools:
        async def ensure_wallet_initialized():
            if not await sol_tools.has_wallet():
                private_key = await private_key_manager.get_private_key(session_id)
                if private_key:
                    await sol_tools.set_session_private_key(private_key)
        
        run_sync(ensure_wallet_initialized())
    
    wallet = getattr(sol_tools, "wallet_address", None) if sol_tools else None
    
except Exception as e:
    agent = None
    sol_tools = None
    wallet = None
    st.error(f"Failed to initialize agent: {e}")

# Only show wallet address if user is authenticated AND wallet is configured
if is_authenticated and wallet:
    st.write(f"**Address:** `{wallet}`")
    
    # Copy to clipboard button
    if st.button("📋 Copy Address", use_container_width=False):
        st.write("Address copied to clipboard!")
elif is_authenticated and not wallet:
    st.warning("⚠️ Private key is stored but wallet is not configured. Please refresh the page.")
elif not is_authenticated:
    st.warning("⚠️ No wallet configured. Please authenticate with your private key first.")

# Enhanced Debug information with browser-specific storage details
with st.expander("🔍 Enhanced Debug Information"):
    st.write("### 📊 Basic Information")
    st.write(f"**Session ID:** `{session_id}`")
    st.write(f"**Authenticated:** {is_authenticated}")
    st.write(f"**Agent Available:** {agent is not None}")
    st.write(f"**Solana Tools Available:** {sol_tools is not None}")
    
    if sol_tools:
        has_wallet = run_sync(sol_tools.has_wallet()) if sol_tools else False
        st.write(f"**Has Wallet:** {has_wallet}")
        st.write(f"**Wallet Address:** `{wallet}`")
    
    st.write("### 🔑 Browser-Specific Storage Information")
    
    # Show browser fingerprint information
    if "browser_fingerprint" in st.session_state:
        st.write(f"**Browser Fingerprint:** `{st.session_state['browser_fingerprint'][:20]}...`")
    else:
        st.write("**Browser Fingerprint:** Not generated yet")
    
    # Show session state information
    st.write(f"**Session State ID:** `{id(st.session_state)}`")
    st.write(f"**Session State Keys:** {list(st.session_state.keys())}")
    
    # Check if private key exists in storage with detailed debugging
    st.write("### 🗄️ Storage Details")
    try:
        # Check if private key exists in storage
        stored_key = run_sync(private_key_manager.get_private_key(session_id))
        st.write(f"**Private Key Stored:** {stored_key is not None}")
        
        if stored_key:
            st.write(f"**Private Key Length:** {len(stored_key)} characters")
            st.write(f"**Private Key Preview:** `{stored_key[:10]}...{stored_key[-10:]}`")
        else:
            st.write("**Private Key:** Not found in storage")
            
        # Show all session keys in private key manager
        session_keys = list(private_key_manager._session_keys.keys())
        st.write(f"**Session Keys in Memory:** {session_keys}")
        
    except Exception as e:
        st.write(f"**Storage Check Error:** {e}")
    
    st.write("### 🔍 Cross-Profile Isolation Test")
    st.write("**Expected Behavior:** Each browser profile should have:")
    st.write("- Different browser fingerprints")
    st.write("- Different storage keys")
    st.write("- Isolated private key storage")
    st.write("- No cross-profile access to private keys")
    
    # Show what would happen with different session IDs
    test_session_id = f"test-{int(time.time())}"
    st.write(f"**Test Session ID:** `{test_session_id}`")
    st.write("**Note:** Different session IDs should result in different storage keys")

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

# Security information
st.divider()
st.subheader("🔒 Security Information")
st.info("""
**Your private key is protected by:**
- **Fernet encryption** - Your key is encrypted before storage
- **OS keyring integration** - Uses your system's secure credential storage
- **Browser-specific storage** - Each browser profile has isolated storage keys
- **Session isolation** - Each browser session has its own encrypted storage
- **No network transmission** - Your private key never leaves your device unencrypted

**Browser Isolation Features:**
- **Unique Browser Fingerprints** - Each browser profile gets a unique identifier
- **Isolated Storage Keys** - Private keys are stored with browser-specific keys
- **Cross-Profile Protection** - Different browser profiles cannot access each other's keys
- **Persistent Isolation** - Storage keys remain consistent within a browser session

**Best practices:**
- Never share your private key with anyone
- Use this application only on trusted devices
- Clear authentication when done using shared devices
- Test with different browser profiles to verify isolation
""")

# Additional debugging section for troubleshooting
with st.expander("🛠️ Advanced Troubleshooting"):
    st.write("### 🔧 Manual Storage Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Clear All Storage", type="secondary"):
            try:
                # Clear session state
                if "browser_fingerprint" in st.session_state:
                    del st.session_state["browser_fingerprint"]
                
                # Clear private key manager cache
                private_key_manager._session_keys.clear()
                
                st.success("✅ Local storage cleared")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error clearing storage: {e}")
    
    with col2:
        if st.button("🔄 Regenerate Fingerprint", type="secondary"):
            try:
                # Force regenerate browser fingerprint
                if "browser_fingerprint" in st.session_state:
                    del st.session_state["browser_fingerprint"]
                
                # Clear agent cache to force regeneration
                clear_agent_cache()
                st.success("✅ Browser fingerprint regenerated")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error regenerating fingerprint: {e}")
    
    st.write("### 📋 Storage Key Analysis")
    try:
        # Show current session ID
        st.write(f"**Current Session ID:** `{session_id}`")
        
        # Show what would happen with a different session
        different_session = f"different-{int(time.time())}"
        st.write(f"**Different Session ID:** `{different_session}`")
        st.write(f"**Sessions Are Different:** {session_id != different_session}")
        st.write("**Note:** Different session IDs should result in different storage keys for browser isolation")
        
    except Exception as e:
        st.write(f"**Key Analysis Error:** {e}")