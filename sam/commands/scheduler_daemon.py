#!/usr/bin/env python3
"""Scheduler daemon for running scheduled transactions in the background."""

import asyncio
import logging
import signal
import sys
from typing import Optional

from ..core.memory_provider import create_memory_manager
from ..core.events import get_event_bus
from ..core.scheduler import SchedulerService
from ..core.tools import ToolRegistry
from ..config.settings import Settings, setup_logging
from ..utils.env_files import find_env_path

logger = logging.getLogger(__name__)


class SchedulerDaemon:
    """Background daemon for executing scheduled transactions."""
    
    def __init__(self):
        self.scheduler_service: Optional[SchedulerService] = None
        self.tool_registry: Optional[ToolRegistry] = None
        self.running = False
        self._shutdown_event = asyncio.Event()
    
    async def start(self) -> None:
        """Start the scheduler daemon."""
        try:
            # Setup logging
            setup_logging()
            logger.info("Starting SAM Scheduler Daemon")
            
            # Load environment
            from dotenv import load_dotenv
            env_path = find_env_path()
            load_dotenv(env_path, override=True)
            Settings.refresh_from_env()
            
            # Create memory manager
            memory = await create_memory_manager()
            
            # Create event bus
            event_bus = get_event_bus()
            
            # Create scheduler service
            self.scheduler_service = SchedulerService(memory, event_bus)
            
            # Create minimal tool registry with only the tools needed for scheduled transactions
            self.tool_registry = await self._create_minimal_tool_registry()
            
            # Set tool registry for scheduler
            self.scheduler_service.set_tool_registry(self.tool_registry)
            
            # Start scheduler
            await self.scheduler_service.start()
            self.running = True
            
            logger.info("Scheduler daemon started successfully")
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Failed to start scheduler daemon: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop the scheduler daemon."""
        if not self.running:
            return
        
        logger.info("Stopping scheduler daemon...")
        self.running = False
        
        if self.scheduler_service:
            await self.scheduler_service.stop()
        
        logger.info("Scheduler daemon stopped")
    
    async def _create_minimal_tool_registry(self) -> ToolRegistry:
        """Create a minimal tool registry with only the tools needed for scheduled transactions."""
        from ..core.tools import ToolRegistry
        
        registry = ToolRegistry()
        
        # Import and register only the tools that can be scheduled
        try:
            # Solana tools (for transfers)
            from ..integrations.solana.solana_tools import create_solana_tools
            solana_tools = create_solana_tools()
            for tool in solana_tools:
                registry.register(tool)
            
            # Pump.fun tools
            from ..integrations.pump_fun import create_pump_fun_tools
            pump_tools = create_pump_fun_tools()
            for tool in pump_tools:
                registry.register(tool)
            
            # Jupiter tools
            from ..integrations.jupiter import create_jupiter_tools
            jupiter_tools = create_jupiter_tools()
            for tool in jupiter_tools:
                registry.register(tool)
            
            # Aster futures tools (if enabled)
            if Settings.ENABLE_ASTER_FUTURES_TOOLS:
                try:
                    from ..integrations.aster_futures import create_aster_futures_tools
                    aster_tools = create_aster_futures_tools()
                    for tool in aster_tools:
                        registry.register(tool)
                except Exception as e:
                    logger.warning(f"Failed to load Aster futures tools: {e}")
            
            # Smart trader tools
            try:
                from ..integrations.smart_trader import SmartTrader, create_smart_trader_tools
                trader = SmartTrader(pump_tools, jupiter_tools, solana_tools)
                for tool in create_smart_trader_tools(trader):
                    registry.register(tool)
            except Exception as e:
                logger.warning(f"Failed to load smart trader tools: {e}")
            
            logger.info(f"Created tool registry with {len(registry.list_specs())} tools")
            
        except Exception as e:
            logger.error(f"Failed to create tool registry: {e}")
            raise
        
        return registry
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def run_scheduler_daemon() -> int:
    """Run the scheduler daemon."""
    daemon = SchedulerDaemon()
    
    try:
        await daemon.start()
        return 0
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        return 0
    except Exception as e:
        logger.error(f"Scheduler daemon failed: {e}")
        return 1


def main() -> None:
    """Main entry point for the scheduler daemon."""
    try:
        exit_code = asyncio.run(run_scheduler_daemon())
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


