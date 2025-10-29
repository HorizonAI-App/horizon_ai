"""Transaction executor for scheduled transactions."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..tools import ToolRegistry
from ..events import EventBus
from .models import ScheduledTransaction

logger = logging.getLogger(__name__)


class ScheduledTransactionExecutor:
    """Executes scheduled transactions using existing tools."""

    def __init__(self, tool_registry: ToolRegistry, event_bus: EventBus):
        self.tool_registry = tool_registry
        self.event_bus = event_bus

    async def execute_transaction(self, transaction: ScheduledTransaction) -> Dict[str, Any]:
        """Execute a scheduled transaction using the appropriate tool."""
        logger.info(f"Executing scheduled transaction {transaction.id}: {transaction.tool_name}")

        try:
            # Get the tool handler
            tool = self.tool_registry._tools.get(transaction.tool_name)
            if not tool:
                error_msg = f"Tool {transaction.tool_name} not found"
                logger.error(error_msg)
                return {"error": error_msg}

            # Validate parameters
            validation_result = self._validate_parameters(transaction)
            if validation_result:
                return validation_result

            # Execute the tool
            logger.info(f"Executing tool {transaction.tool_name} with parameters: {transaction.parameters}")
            result = await tool.handler(transaction.parameters)

            # Check if execution was successful
            if isinstance(result, dict) and result.get("error"):
                error_msg = f"Tool execution failed: {result['error']}"
                logger.error(error_msg)
                return {"error": error_msg}

            # Emit success event
            await self.event_bus.publish("scheduler.transaction_executed", {
                "transaction_id": transaction.id,
                "user_id": transaction.user_id,
                "tool_name": transaction.tool_name,
                "parameters": transaction.parameters,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            logger.info(f"Successfully executed transaction {transaction.id}")
            return result

        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            logger.error(f"Failed to execute transaction {transaction.id}: {e}")

            # Emit error event
            await self.event_bus.publish("scheduler.transaction_failed", {
                "transaction_id": transaction.id,
                "user_id": transaction.user_id,
                "tool_name": transaction.tool_name,
                "parameters": transaction.parameters,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            return {"error": error_msg}

    def _validate_parameters(self, transaction: ScheduledTransaction) -> Optional[Dict[str, Any]]:
        """Validate transaction parameters before execution."""
        try:
            # Basic parameter validation
            if not transaction.parameters:
                return {"error": "No parameters provided"}

            # Tool-specific validation
            if transaction.tool_name in ["smart_buy", "pump_fun_buy"]:
                return self._validate_buy_parameters(transaction.parameters)
            elif transaction.tool_name in ["smart_sell", "pump_fun_sell"]:
                return self._validate_sell_parameters(transaction.parameters)
            elif transaction.tool_name == "jupiter_swap":
                return self._validate_swap_parameters(transaction.parameters)
            elif transaction.tool_name == "transfer_sol":
                return self._validate_transfer_parameters(transaction.parameters)
            elif transaction.tool_name in ["aster_open_long", "aster_close_position"]:
                return self._validate_aster_parameters(transaction.parameters)

            return None

        except Exception as e:
            logger.error(f"Parameter validation failed: {e}")
            return {"error": f"Parameter validation failed: {str(e)}"}

    def _validate_buy_parameters(self, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate buy transaction parameters."""
        required_fields = ["mint", "amount_sol"]
        for field in required_fields:
            if field not in parameters:
                return {"error": f"Missing required parameter: {field}"}

        # Validate amount
        amount_sol = parameters.get("amount_sol")
        if not isinstance(amount_sol, (int, float)) or amount_sol <= 0:
            return {"error": "amount_sol must be a positive number"}

        if amount_sol > 1000:  # Safety limit
            return {"error": "amount_sol exceeds maximum limit of 1000 SOL"}

        # Validate mint address
        mint = parameters.get("mint")
        if not isinstance(mint, str) or len(mint) != 44:
            return {"error": "Invalid mint address format"}

        return None

    def _validate_sell_parameters(self, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate sell transaction parameters."""
        required_fields = ["mint", "percentage"]
        for field in required_fields:
            if field not in parameters:
                return {"error": f"Missing required parameter: {field}"}

        # Validate percentage
        percentage = parameters.get("percentage")
        if not isinstance(percentage, (int, float)) or not (0 < percentage <= 100):
            return {"error": "percentage must be between 0 and 100"}

        # Validate mint address
        mint = parameters.get("mint")
        if not isinstance(mint, str) or len(mint) != 44:
            return {"error": "Invalid mint address format"}

        return None

    def _validate_swap_parameters(self, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate swap transaction parameters."""
        required_fields = ["input_mint", "output_mint", "amount"]
        for field in required_fields:
            if field not in parameters:
                return {"error": f"Missing required parameter: {field}"}

        # Validate amount
        amount = parameters.get("amount")
        if not isinstance(amount, (int, float)) or amount <= 0:
            return {"error": "amount must be a positive number"}

        # Validate mint addresses
        for field in ["input_mint", "output_mint"]:
            mint = parameters.get(field)
            if not isinstance(mint, str) or len(mint) != 44:
                return {"error": f"Invalid {field} format"}

        return None

    def _validate_transfer_parameters(self, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate transfer transaction parameters."""
        required_fields = ["to_address", "amount"]
        for field in required_fields:
            if field not in parameters:
                return {"error": f"Missing required parameter: {field}"}

        # Validate amount
        amount = parameters.get("amount")
        if not isinstance(amount, (int, float)) or amount <= 0:
            return {"error": "amount must be a positive number"}

        if amount > 1000:  # Safety limit
            return {"error": "amount exceeds maximum limit of 1000 SOL"}

        # Validate address
        to_address = parameters.get("to_address")
        if not isinstance(to_address, str) or len(to_address) != 44:
            return {"error": "Invalid to_address format"}

        return None

    def _validate_aster_parameters(self, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate Aster futures transaction parameters."""
        if "symbol" not in parameters:
            return {"error": "Missing required parameter: symbol"}

        symbol = parameters.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            return {"error": "symbol must be a non-empty string"}

        # For open_long, validate usd_notional and leverage
        if "usd_notional" in parameters:
            usd_notional = parameters.get("usd_notional")
            if not isinstance(usd_notional, (int, float)) or usd_notional <= 0:
                return {"error": "usd_notional must be a positive number"}

        if "leverage" in parameters:
            leverage = parameters.get("leverage")
            if not isinstance(leverage, (int, float)) or not (1 <= leverage <= 20):
                return {"error": "leverage must be between 1 and 20"}

        return None

    async def can_execute_transaction(self, transaction: ScheduledTransaction) -> bool:
        """Check if a transaction can be executed (pre-flight checks)."""
        try:
            # Check if tool exists
            tool = self.tool_registry._tools.get(transaction.tool_name)
            if not tool:
                logger.warning(f"Tool {transaction.tool_name} not available")
                return False

            # Validate parameters
            validation_result = self._validate_parameters(transaction)
            if validation_result:
                logger.warning(f"Parameter validation failed: {validation_result}")
                return False

            # Additional checks could be added here:
            # - Check wallet balance
            # - Check network connectivity
            # - Check market conditions

            return True

        except Exception as e:
            logger.error(f"Pre-flight check failed: {e}")
            return False
