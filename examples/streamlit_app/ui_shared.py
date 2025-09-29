import asyncio
from pathlib import Path
import streamlit as st

from sam.web.session import get_agent
from sam.core.context import RequestContext
from sam.config.settings import Settings


def inject_css():
    css_path = Path(__file__).parent / "styles.css"
    try:
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception:
        pass


def ensure_env_loaded():
    from sam.utils.env_files import find_env_path
    from dotenv import load_dotenv

    env_path = find_env_path()
    load_dotenv(env_path, override=True)
    Settings.refresh_from_env()


def ensure_session_init():
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    # Attach to latest session by default (or create a dated one)
    if "session_id" not in st.session_state or not st.session_state["session_id"]:
        try:
            from sam.web.session import get_default_session_id

            st.session_state["session_id"] = run_sync(
                get_default_session_id(get_local_context())
            )
        except Exception:
            # Fallback to a generated id if web adapter fails
            from uuid import uuid4

            st.session_state["session_id"] = str(uuid4())
    if "agent_ready" not in st.session_state:
        st.session_state["agent_ready"] = False
    if "last_input" not in st.session_state:
        st.session_state["last_input"] = None
    if "history_loaded" not in st.session_state:
        st.session_state["history_loaded"] = False


def run_sync(coro):
    """Run an async coroutine in both fresh and existing event loop contexts."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # If there's already an event loop running, create a new task
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a new task and wait for it
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)


def get_local_context() -> RequestContext:
    """Return a request context suitable for local Streamlit usage with proper user isolation."""
    session_id = st.session_state.get("session_id", "default")
    
    # Generate unique user ID that's truly isolated per browser session
    # This ensures complete user isolation by not caching user_id in session state
    import hashlib
    import secrets
    import time
    
    # Create a unique identifier that changes for each new browser session
    # Use timestamp + random data + session state ID for maximum uniqueness
    browser_fingerprint = f"{time.time()}-{secrets.token_hex(8)}-{id(st.session_state)}"
    user_id = hashlib.sha256(f"horizon-{browser_fingerprint}".encode()).hexdigest()[:16]
    
    return RequestContext(user_id=user_id, session_id=session_id)


@st.cache_resource(show_spinner=False)
def agent_ready_marker() -> bool:
    async def _build():
        await get_agent(get_local_context())

    run_sync(_build())
    return True


def clear_agent_cache():
    """Clear the cached agent to force reload with updated price service."""
    agent_ready_marker.clear()
    # Also clear the global price service cache
    async def _clear():
        from sam.utils.price_service import cleanup_price_service
        await cleanup_price_service()
    
    run_sync(_clear())


# Agent starts automatically when first accessed - no marker needed