"""Specialized agent builder for Aster futures trading."""

import asyncio
import logging
from typing import Optional

from .agent import SAMAgent
from .llm_provider import create_llm_provider
from .memory_provider import create_memory_manager
from .tools import ToolRegistry
from .middleware import LoggingMiddleware, RateLimitMiddleware, RetryMiddleware
from .context import RequestContext
from ..config.prompts import ASTER_FUTURES_TRADING_PROMPT
from ..config.settings import Settings
from ..config.config_loader import load_middleware_config
from ..utils.secure_storage import get_secure_storage
from ..utils.http_client import cleanup_http_client
from ..utils.connection_pool import cleanup_database_pool
from ..utils.rate_limiter import cleanup_rate_limiter
from ..utils.price_service import cleanup_price_service

# Import only Aster futures tools
from ..integrations.aster_futures import AsterFuturesClient, create_aster_futures_tools

logger = logging.getLogger(__name__)


class FuturesAgentBuilder:
    """Specialized agent builder for Aster futures trading."""

    def __init__(self, system_prompt: str = ASTER_FUTURES_TRADING_PROMPT):
        self.system_prompt = system_prompt

    async def build(
        self, 
        context: Optional[RequestContext] = None, 
        session_id: Optional[str] = None
    ) -> SAMAgent:
        """Build a specialized futures trading agent."""
        
        # Create LLM provider
        llm = create_llm_provider()
        
        # Create memory manager
        memory = create_memory_manager(session_id=session_id)
        
        # Create tool registry with middleware
        middleware_config = load_middleware_config()
        middlewares = [
            LoggingMiddleware(),
            RateLimitMiddleware(middleware_config.rate_limit),
            RetryMiddleware(middleware_config.retry),
        ]
        tools = ToolRegistry(middlewares=middlewares)
        
        # Create agent
        agent = SAMAgent(
            llm=llm, 
            tools=tools, 
            memory=memory, 
            system_prompt=self.system_prompt
        )
        
        # Store context on agent for tools to access
        if context:
            setattr(agent, "_context", context)

        # Initialize Aster futures client
        aster_client = await self._setup_aster_client()
        if aster_client:
            # Register Aster futures tools
            for tool in create_aster_futures_tools(aster_client):
                tools.register(tool)
            
            # Store client reference
            setattr(agent, "_aster_client", aster_client)
            logger.info("Aster futures tools registered successfully")
        else:
            logger.warning("Aster futures client not available - tools not registered")

        # Store references
        setattr(agent, "_llm", llm)
        setattr(agent, "_tools", tools)
        setattr(agent, "_memory", memory)

        logger.info(f"Futures trading agent built with {len(tools.list_specs())} tools")
        return agent

    async def _setup_aster_client(self) -> Optional[AsterFuturesClient]:
        """Setup Aster futures client with credentials."""
        try:
            secure_storage = get_secure_storage()
            
            # Get API credentials from secure storage or environment
            aster_api_key = secure_storage.get_api_key("aster_api")
            if not aster_api_key and Settings.ASTER_API_KEY:
                if secure_storage.store_api_key("aster_api", Settings.ASTER_API_KEY):
                    aster_api_key = Settings.ASTER_API_KEY
                else:
                    aster_api_key = Settings.ASTER_API_KEY

            aster_api_secret = secure_storage.get_private_key("aster_api_secret")
            if not aster_api_secret and Settings.ASTER_API_SECRET:
                if secure_storage.store_private_key("aster_api_secret", Settings.ASTER_API_SECRET):
                    aster_api_secret = Settings.ASTER_API_SECRET
                else:
                    aster_api_secret = Settings.ASTER_API_SECRET

            if aster_api_key and aster_api_secret:
                client = AsterFuturesClient(
                    base_url=Settings.ASTER_BASE_URL,
                    api_key=aster_api_key,
                    api_secret=aster_api_secret,
                    default_recv_window=Settings.ASTER_DEFAULT_RECV_WINDOW,
                )
                logger.info("Aster futures client initialized successfully")
                return client
            else:
                logger.warning(
                    "Aster API credentials not found. Set ASTER_API_KEY and ASTER_API_SECRET "
                    "or store them via secure storage."
                )
                return None
                
        except Exception as e:
            logger.error(f"Failed to setup Aster futures client: {e}")
            return None


async def cleanup_futures_agent() -> None:
    """Cleanup resources for futures trading agent."""
    await asyncio.gather(
        cleanup_http_client(),
        cleanup_database_pool(),
        cleanup_rate_limiter(),
        cleanup_price_service(),
        return_exceptions=True,
    )
