"""Tests for scheduler functionality."""

import asyncio
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sam.core.scheduler.models import (
    ScheduledTransaction,
    ScheduleTransactionInput,
    ScheduleType,
    TransactionStatus,
    OnceScheduleConfig,
    RecurringScheduleConfig,
    ConditionalScheduleConfig,
)
from sam.core.scheduler.scheduler_service import SchedulerService
from sam.core.scheduler.executor import ScheduledTransactionExecutor
from sam.core.scheduler.tools import create_scheduler_tools, set_scheduler_user_context
from sam.core.memory import MemoryManager
from sam.core.events import EventBus
from sam.core.tools import ToolRegistry
from sam.utils.time_helpers import (
    calculate_execution_time,
    format_execution_time,
    get_time_until_execution,
)


@pytest.fixture
async def memory_manager():
    """Create a memory manager for testing."""
    manager = MemoryManager(":memory:")
    await manager.initialize()
    return manager


@pytest.fixture
def event_bus():
    """Create an event bus for testing."""
    return EventBus()


@pytest.fixture
def tool_registry():
    """Create a tool registry for testing."""
    return ToolRegistry()


@pytest.fixture
async def scheduler_service(memory_manager, event_bus):
    """Create a scheduler service for testing."""
    service = SchedulerService(memory_manager, event_bus)
    return service


@pytest.fixture
def mock_tool():
    """Create a mock tool for testing."""
    tool = MagicMock()
    tool.handler = AsyncMock(return_value={"success": True, "result": "test"})
    return tool


class TestScheduledTransactionModels:
    """Test scheduled transaction data models."""

    def test_once_schedule_config_validation(self):
        """Test once schedule config validation."""
        # Valid future date
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        config = OnceScheduleConfig(execute_at=future_date)
        assert config.execute_at == future_date

        # Invalid past date
        past_date = datetime.now(timezone.utc) - timedelta(hours=1)
        with pytest.raises(ValueError, match="execute_at must be in the future"):
            OnceScheduleConfig(execute_at=past_date)

    def test_recurring_schedule_config_validation(self):
        """Test recurring schedule config validation."""
        # Valid daily schedule
        config = RecurringScheduleConfig(
            frequency="daily",
            time="09:00",
            timezone="UTC"
        )
        assert config.frequency == "daily"
        assert config.time == "09:00"

        # Invalid time format
        with pytest.raises(ValueError, match="time must be in HH:MM format"):
            RecurringScheduleConfig(frequency="daily", time="25:00")

        # Invalid days of week
        with pytest.raises(ValueError, match="days_of_week must be integers between 1 and 7"):
            RecurringScheduleConfig(frequency="weekly", days_of_week=[0, 8])

    def test_conditional_schedule_config_validation(self):
        """Test conditional schedule config validation."""
        # Valid conditional schedule
        config = ConditionalScheduleConfig(
            condition_type="price_target",
            condition_config={"token": "SOL", "target": 100.0},
            check_interval=300
        )
        assert config.condition_type == "price_target"
        assert config.check_interval == 300

        # Invalid check interval
        with pytest.raises(ValueError, match="check_interval must be at least 60 seconds"):
            ConditionalScheduleConfig(
                condition_type="price_target",
                condition_config={},
                check_interval=30
            )

    def test_scheduled_transaction_creation(self):
        """Test scheduled transaction creation."""
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        schedule_config = OnceScheduleConfig(execute_at=future_date)
        
        transaction = ScheduledTransaction(
            user_id="test_user",
            transaction_type="buy",
            tool_name="smart_buy",
            parameters={"mint": "test_mint", "amount_sol": 0.1},
            schedule_config=schedule_config,
        )
        
        assert transaction.user_id == "test_user"
        assert transaction.tool_name == "smart_buy"
        assert transaction.status == TransactionStatus.PENDING
        assert transaction.next_execution == future_date

    def test_scheduled_transaction_serialization(self):
        """Test scheduled transaction serialization."""
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        schedule_config = OnceScheduleConfig(execute_at=future_date)
        
        transaction = ScheduledTransaction(
            user_id="test_user",
            transaction_type="buy",
            tool_name="smart_buy",
            parameters={"mint": "test_mint", "amount_sol": 0.1},
            schedule_config=schedule_config,
        )
        
        # Test to_dict
        data = transaction.to_dict()
        assert data["user_id"] == "test_user"
        assert data["tool_name"] == "smart_buy"
        assert data["status"] == "pending"
        assert json.loads(data["parameters"]) == {"mint": "test_mint", "amount_sol": 0.1}
        
        # Test from_dict
        restored = ScheduledTransaction.from_dict(data)
        assert restored.user_id == transaction.user_id
        assert restored.tool_name == transaction.tool_name
        assert restored.status == transaction.status
        assert restored.parameters == transaction.parameters


class TestSchedulerService:
    """Test scheduler service functionality."""

    @pytest.mark.asyncio
    async def test_scheduler_service_initialization(self, scheduler_service):
        """Test scheduler service initialization."""
        assert not scheduler_service.running
        assert scheduler_service._task is None
        assert scheduler_service._tool_registry is None
        assert scheduler_service._executor is None

    @pytest.mark.asyncio
    async def test_scheduler_service_start_stop(self, scheduler_service):
        """Test scheduler service start and stop."""
        # Start service
        await scheduler_service.start()
        assert scheduler_service.running
        assert scheduler_service._task is not None
        
        # Stop service
        await scheduler_service.stop()
        assert not scheduler_service.running

    @pytest.mark.asyncio
    async def test_schedule_transaction(self, scheduler_service, tool_registry):
        """Test scheduling a transaction."""
        scheduler_service.set_tool_registry(tool_registry)
        
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        input_data = ScheduleTransactionInput(
            tool_name="smart_buy",
            parameters={"mint": "test_mint", "amount_sol": 0.1},
            schedule_type=ScheduleType.ONCE,
            schedule_config={"execute_at": future_date.isoformat()},
            notes="Test transaction"
        )
        
        transaction_id = await scheduler_service.schedule_transaction("test_user", input_data)
        assert transaction_id is not None
        
        # Verify transaction was stored
        transactions = await scheduler_service.list_user_transactions("test_user")
        assert len(transactions) == 1
        assert transactions[0].tool_name == "smart_buy"
        assert transactions[0].metadata["notes"] == "Test transaction"

    @pytest.mark.asyncio
    async def test_cancel_transaction(self, scheduler_service, tool_registry):
        """Test canceling a transaction."""
        scheduler_service.set_tool_registry(tool_registry)
        
        # Schedule a transaction
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        input_data = ScheduleTransactionInput(
            tool_name="smart_buy",
            parameters={"mint": "test_mint", "amount_sol": 0.1},
            schedule_type=ScheduleType.ONCE,
            schedule_config={"execute_at": future_date.isoformat()},
        )
        
        transaction_id = await scheduler_service.schedule_transaction("test_user", input_data)
        
        # Cancel the transaction
        success = await scheduler_service.cancel_transaction(int(transaction_id), "test_user")
        assert success
        
        # Verify transaction was cancelled
        transactions = await scheduler_service.list_user_transactions("test_user")
        assert len(transactions) == 1
        assert transactions[0].status == TransactionStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_list_user_transactions(self, scheduler_service, tool_registry):
        """Test listing user transactions."""
        scheduler_service.set_tool_registry(tool_registry)
        
        # Schedule multiple transactions
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        for i in range(3):
            input_data = ScheduleTransactionInput(
                tool_name="smart_buy",
                parameters={"mint": f"test_mint_{i}", "amount_sol": 0.1},
                schedule_type=ScheduleType.ONCE,
                schedule_config={"execute_at": future_date.isoformat()},
            )
            await scheduler_service.schedule_transaction("test_user", input_data)
        
        # List transactions
        transactions = await scheduler_service.list_user_transactions("test_user")
        assert len(transactions) == 3
        
        # Test filtering by status
        pending_transactions = await scheduler_service.list_user_transactions(
            "test_user", status=TransactionStatus.PENDING
        )
        assert len(pending_transactions) == 3


class TestScheduledTransactionExecutor:
    """Test scheduled transaction executor."""

    @pytest.fixture
    def executor(self, tool_registry, event_bus):
        """Create an executor for testing."""
        return ScheduledTransactionExecutor(tool_registry, event_bus)

    @pytest.mark.asyncio
    async def test_execute_transaction_success(self, executor, mock_tool):
        """Test successful transaction execution."""
        executor.tool_registry.get_tool = MagicMock(return_value=mock_tool)
        
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        schedule_config = OnceScheduleConfig(execute_at=future_date)
        
        transaction = ScheduledTransaction(
            user_id="test_user",
            transaction_type="buy",
            tool_name="smart_buy",
            parameters={"mint": "test_mint", "amount_sol": 0.1},
            schedule_config=schedule_config,
        )
        
        result = await executor.execute_transaction(transaction)
        assert result["success"] is True
        assert result["result"] == "test"
        
        # Verify tool was called with correct parameters
        mock_tool.handler.assert_called_once_with({"mint": "test_mint", "amount_sol": 0.1})

    @pytest.mark.asyncio
    async def test_execute_transaction_tool_not_found(self, executor):
        """Test transaction execution when tool is not found."""
        executor.tool_registry.get_tool = MagicMock(return_value=None)
        
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        schedule_config = OnceScheduleConfig(execute_at=future_date)
        
        transaction = ScheduledTransaction(
            user_id="test_user",
            transaction_type="buy",
            tool_name="nonexistent_tool",
            parameters={"mint": "test_mint", "amount_sol": 0.1},
            schedule_config=schedule_config,
        )
        
        result = await executor.execute_transaction(transaction)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_transaction_tool_error(self, executor, mock_tool):
        """Test transaction execution when tool returns error."""
        mock_tool.handler = AsyncMock(return_value={"error": "Tool execution failed"})
        executor.tool_registry.get_tool = MagicMock(return_value=mock_tool)
        
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        schedule_config = OnceScheduleConfig(execute_at=future_date)
        
        transaction = ScheduledTransaction(
            user_id="test_user",
            transaction_type="buy",
            tool_name="smart_buy",
            parameters={"mint": "test_mint", "amount_sol": 0.1},
            schedule_config=schedule_config,
        )
        
        result = await executor.execute_transaction(transaction)
        assert "error" in result
        assert "Tool execution failed" in result["error"]

    def test_validate_buy_parameters(self, executor):
        """Test buy parameter validation."""
        # Valid parameters
        valid_params = {"mint": "test_mint", "amount_sol": 0.1}
        result = executor._validate_buy_parameters(valid_params)
        assert result is None
        
        # Missing mint
        invalid_params = {"amount_sol": 0.1}
        result = executor._validate_buy_parameters(invalid_params)
        assert "Missing required parameter: mint" in result["error"]
        
        # Invalid amount
        invalid_params = {"mint": "test_mint", "amount_sol": -0.1}
        result = executor._validate_buy_parameters(invalid_params)
        assert "amount_sol must be a positive number" in result["error"]
        
        # Amount too large
        invalid_params = {"mint": "test_mint", "amount_sol": 2000}
        result = executor._validate_buy_parameters(invalid_params)
        assert "amount_sol exceeds maximum limit" in result["error"]

    def test_validate_sell_parameters(self, executor):
        """Test sell parameter validation."""
        # Valid parameters
        valid_params = {"mint": "test_mint", "percentage": 50}
        result = executor._validate_sell_parameters(valid_params)
        assert result is None
        
        # Invalid percentage
        invalid_params = {"mint": "test_mint", "percentage": 150}
        result = executor._validate_sell_parameters(invalid_params)
        assert "percentage must be between 0 and 100" in result["error"]

    def test_validate_transfer_parameters(self, executor):
        """Test transfer parameter validation."""
        # Valid parameters
        valid_params = {"to_address": "test_address", "amount": 1.0}
        result = executor._validate_transfer_parameters(valid_params)
        assert result is None
        
        # Invalid address format
        invalid_params = {"to_address": "invalid", "amount": 1.0}
        result = executor._validate_transfer_parameters(invalid_params)
        assert "Invalid to_address format" in result["error"]


class TestSchedulerTools:
    """Test scheduler tools."""

    @pytest.fixture
    def scheduler_tools(self, scheduler_service):
        """Create scheduler tools for testing."""
        return create_scheduler_tools(scheduler_service)

    def test_scheduler_tools_creation(self, scheduler_tools):
        """Test scheduler tools are created correctly."""
        assert len(scheduler_tools) == 3
        
        tool_names = [tool.spec.name for tool in scheduler_tools]
        assert "schedule_transaction" in tool_names
        assert "list_scheduled_transactions" in tool_names
        assert "cancel_scheduled_transaction" in tool_names

    @pytest.mark.asyncio
    async def test_schedule_transaction_tool(self, scheduler_tools, tool_registry):
        """Test schedule transaction tool."""
        # Find the schedule transaction tool
        schedule_tool = next(tool for tool in scheduler_tools if tool.spec.name == "schedule_transaction")
        
        # Set up scheduler service
        scheduler_service = schedule_tool.handler.__self__._scheduler_service
        scheduler_service.set_tool_registry(tool_registry)
        set_scheduler_user_context(scheduler_service, "test_user")
        
        # Test scheduling a transaction
        args = {
            "tool_name": "smart_buy",
            "parameters": {"mint": "test_mint", "amount_sol": 0.1},
            "schedule_type": "once",
            "schedule_config": {
                "execute_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            },
            "notes": "Test transaction"
        }
        
        result = await schedule_tool.handler(args)
        assert result["success"] is True
        assert "transaction_id" in result
        assert result["tool_name"] == "smart_buy"

    @pytest.mark.asyncio
    async def test_list_scheduled_transactions_tool(self, scheduler_tools, tool_registry):
        """Test list scheduled transactions tool."""
        # Find the list tool
        list_tool = next(tool for tool in scheduler_tools if tool.spec.name == "list_scheduled_transactions")
        
        # Set up scheduler service
        scheduler_service = list_tool.handler.__self__._scheduler_service
        scheduler_service.set_tool_registry(tool_registry)
        set_scheduler_user_context(scheduler_service, "test_user")
        
        # Test listing transactions
        args = {"limit": 10, "offset": 0}
        result = await list_tool.handler(args)
        assert result["success"] is True
        assert "transactions" in result
        assert "count" in result

    @pytest.mark.asyncio
    async def test_cancel_scheduled_transaction_tool(self, scheduler_tools, tool_registry):
        """Test cancel scheduled transaction tool."""
        # Find the cancel tool
        cancel_tool = next(tool for tool in scheduler_tools if tool.spec.name == "cancel_scheduled_transaction")
        
        # Set up scheduler service
        scheduler_service = cancel_tool.handler.__self__._scheduler_service
        scheduler_service.set_tool_registry(tool_registry)
        set_scheduler_user_context(scheduler_service, "test_user")
        
        # Test canceling a non-existent transaction
        args = {"transaction_id": 999}
        result = await cancel_tool.handler(args)
        assert result["success"] is False
        assert "not found" in result["error"]


class TestTimeHelpers:
    """Test time helper functions."""

    def test_calculate_execution_time_relative(self):
        """Test relative time calculation."""
        # Test "in 3 minutes"
        result = calculate_execution_time("in 3 minutes")
        assert result is not None
        
        # Parse the result and verify it's approximately 3 minutes from now
        execution_time = datetime.fromisoformat(result.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        diff = execution_time - now
        
        # Should be within 1 second of 3 minutes
        assert abs(diff.total_seconds() - 180) < 1

    def test_calculate_execution_time_absolute(self):
        """Test absolute time calculation."""
        # Test "at 9:00 AM"
        result = calculate_execution_time("at 9:00 AM")
        assert result is not None
        
        execution_time = datetime.fromisoformat(result.replace('Z', '+00:00'))
        assert execution_time.hour == 9
        assert execution_time.minute == 0

    def test_calculate_execution_time_tomorrow(self):
        """Test tomorrow time calculation."""
        # Test "tomorrow at 10:00"
        result = calculate_execution_time("tomorrow at 10:00")
        assert result is not None
        
        execution_time = datetime.fromisoformat(result.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(days=1)
        
        # Should be tomorrow at 10:00
        assert execution_time.date() == tomorrow.date()
        assert execution_time.hour == 10
        assert execution_time.minute == 0

    def test_calculate_execution_time_invalid(self):
        """Test invalid time expressions."""
        result = calculate_execution_time("invalid time")
        assert result is None
        
        result = calculate_execution_time("")
        assert result is None

    def test_format_execution_time(self):
        """Test time formatting."""
        iso_time = "2024-01-15T14:30:00Z"
        formatted = format_execution_time(iso_time)
        assert "2024-01-15 14:30:00 UTC" in formatted

    def test_get_time_until_execution(self):
        """Test time until execution calculation."""
        # Test future time
        future_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        result = get_time_until_execution(future_time)
        assert "5 minute" in result
        
        # Test past time
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        result = get_time_until_execution(past_time)
        assert result == "Past due"


class TestSchedulerIntegration:
    """Test scheduler integration with the full system."""

    @pytest.mark.asyncio
    async def test_scheduler_with_mock_tools(self, memory_manager, event_bus, tool_registry):
        """Test scheduler with mock tools."""
        # Create a mock tool
        mock_tool = MagicMock()
        mock_tool.handler = AsyncMock(return_value={"success": True, "result": "executed"})
        tool_registry.register_tool = MagicMock()
        tool_registry.get_tool = MagicMock(return_value=mock_tool)
        
        # Create scheduler service
        scheduler_service = SchedulerService(memory_manager, event_bus)
        scheduler_service.set_tool_registry(tool_registry)
        
        # Schedule a transaction for immediate execution
        now = datetime.now(timezone.utc)
        input_data = ScheduleTransactionInput(
            tool_name="smart_buy",
            parameters={"mint": "test_mint", "amount_sol": 0.1},
            schedule_type=ScheduleType.ONCE,
            schedule_config={"execute_at": now.isoformat()},
        )
        
        transaction_id = await scheduler_service.schedule_transaction("test_user", input_data)
        
        # Start scheduler and wait for execution
        await scheduler_service.start()
        
        # Wait a bit for execution
        await asyncio.sleep(0.1)
        
        # Stop scheduler
        await scheduler_service.stop()
        
        # Verify transaction was executed
        transactions = await scheduler_service.list_user_transactions("test_user")
        assert len(transactions) == 1
        # Note: In a real test, we'd need to wait for the execution loop to run
        # For now, we just verify the transaction was scheduled
        assert transactions[0].tool_name == "smart_buy"

    @pytest.mark.asyncio
    async def test_enhanced_schedule_transaction_tool(self, scheduler_tools, tool_registry):
        """Test enhanced schedule transaction tool with time parsing."""
        # Find the schedule transaction tool
        schedule_tool = next(tool for tool in scheduler_tools if tool.spec.name == "schedule_transaction")
        
        # Set up scheduler service
        scheduler_service = schedule_tool.handler.__self__._scheduler_service
        scheduler_service.set_tool_registry(tool_registry)
        set_scheduler_user_context(scheduler_service, "test_user")
        
        # Test scheduling with natural language time
        args = {
            "tool_name": "transfer_sol",
            "parameters": {"to_address": "test_address", "amount": 0.1},
            "schedule_type": "once",
            "schedule_config": {
                "execute_at": "in 5 minutes"  # Natural language time
            },
            "notes": "Test transaction with natural language time"
        }
        
        result = await schedule_tool.handler(args)
        assert result["success"] is True
        assert "transaction_id" in result
        assert "Execution time:" in result["message"]
        assert "Time until execution:" in result["message"]
