"""Data models for scheduled transactions."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ScheduleType(str, Enum):
    """Types of scheduling supported."""
    ONCE = "once"
    RECURRING = "recurring"
    CONDITIONAL = "conditional"


class TransactionStatus(str, Enum):
    """Status of scheduled transactions."""
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class RecurrenceFrequency(str, Enum):
    """Recurrence frequency options."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ConditionalOperator(str, Enum):
    """Operators for conditional execution."""
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"


class ScheduleConfig(BaseModel):
    """Base class for schedule configurations."""
    schedule_type: ScheduleType


class OnceScheduleConfig(ScheduleConfig):
    """Configuration for one-time execution."""
    schedule_type: ScheduleType = ScheduleType.ONCE
    execute_at: datetime = Field(..., description="When to execute the transaction")

    @field_validator("execute_at", mode="before")
    @classmethod
    def parse_execute_at(cls, v) -> datetime:
        """Parse execute_at from string or datetime."""
        if isinstance(v, str):
            try:
                # Handle ISO format strings
                if v.endswith('Z'):
                    v = v[:-1] + '+00:00'
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError(f"Invalid datetime format: {v}")
        elif isinstance(v, datetime):
            return v
        else:
            raise ValueError(f"execute_at must be a datetime or ISO string, got {type(v)}")

    @field_validator("execute_at")
    @classmethod
    def validate_execute_at(cls, v: datetime) -> datetime:
        """Ensure execute_at is in the future (only for new schedules)."""
        # Note: We don't validate past times here because transactions loaded from DB
        # might be past due and need to be executed. The validation happens during
        # the scheduling process, not during deserialization.
        return v


class RecurringScheduleConfig(ScheduleConfig):
    """Configuration for recurring execution."""
    schedule_type: ScheduleType = ScheduleType.RECURRING
    frequency: RecurrenceFrequency = Field(..., description="How often to execute")
    time: Optional[str] = Field(None, description="Time of day (HH:MM format)")
    days_of_week: Optional[List[int]] = Field(None, description="Days of week (1=Monday, 7=Sunday)")
    day_of_month: Optional[int] = Field(None, description="Day of month (1-31)")
    timezone: str = Field("UTC", description="Timezone for execution")
    start_date: Optional[datetime] = Field(None, description="When to start recurring")
    end_date: Optional[datetime] = Field(None, description="When to stop recurring")

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_datetime_fields(cls, v) -> Optional[datetime]:
        """Parse datetime fields from string or datetime."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                # Handle ISO format strings
                if v.endswith('Z'):
                    v = v[:-1] + '+00:00'
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError(f"Invalid datetime format: {v}")
        elif isinstance(v, datetime):
            return v
        else:
            raise ValueError(f"Date must be a datetime or ISO string, got {type(v)}")

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: Optional[str]) -> Optional[str]:
        """Validate time format."""
        if v is None:
            return v
        try:
            datetime.strptime(v, "%H:%M")
            return v
        except ValueError:
            raise ValueError("time must be in HH:MM format")

    @field_validator("days_of_week")
    @classmethod
    def validate_days_of_week(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        """Validate days of week."""
        if v is None:
            return v
        if not all(1 <= day <= 7 for day in v):
            raise ValueError("days_of_week must be integers between 1 and 7")
        return v

    @field_validator("day_of_month")
    @classmethod
    def validate_day_of_month(cls, v: Optional[int]) -> Optional[int]:
        """Validate day of month."""
        if v is None:
            return v
        if not 1 <= v <= 31:
            raise ValueError("day_of_month must be between 1 and 31")
        return v


class ConditionalScheduleConfig(ScheduleConfig):
    """Configuration for conditional execution."""
    schedule_type: ScheduleType = ScheduleType.CONDITIONAL
    condition_type: str = Field(..., description="Type of condition (e.g., 'price_target')")
    condition_config: Dict[str, Any] = Field(..., description="Condition-specific configuration")
    check_interval: int = Field(300, description="How often to check condition (seconds)")
    max_checks: Optional[int] = Field(None, description="Maximum number of checks before expiring")

    @field_validator("check_interval")
    @classmethod
    def validate_check_interval(cls, v: int) -> int:
        """Validate check interval."""
        if v < 60:  # Minimum 1 minute
            raise ValueError("check_interval must be at least 60 seconds")
        return v


class ScheduledTransaction(BaseModel):
    """Model for a scheduled transaction."""
    id: Optional[int] = Field(None, description="Database ID")
    user_id: str = Field(..., description="User who scheduled the transaction")
    transaction_type: str = Field(..., description="Type of transaction (e.g., 'buy', 'sell', 'transfer')")
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(..., description="Parameters for the tool")
    schedule_config: Union[OnceScheduleConfig, RecurringScheduleConfig, ConditionalScheduleConfig] = Field(
        ..., description="Schedule configuration"
    )
    status: TransactionStatus = Field(TransactionStatus.PENDING, description="Current status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_execution: Optional[datetime] = Field(None, description="When to execute next")
    last_execution: Optional[datetime] = Field(None, description="When last executed")
    execution_count: int = Field(0, description="Number of times executed")
    max_executions: Optional[int] = Field(None, description="Maximum executions allowed")
    error_message: Optional[str] = Field(None, description="Last error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name."""
        # List of known tools that can be scheduled
        allowed_tools = {
            "smart_buy", "smart_sell", "jupiter_swap", "transfer_sol",
            "pump_fun_buy", "pump_fun_sell", "aster_open_long", "aster_close_position"
        }
        if v not in allowed_tools:
            logger.warning(f"Unknown tool name: {v}")
        return v

    @field_validator("max_executions")
    @classmethod
    def validate_max_executions(cls, v: Optional[int]) -> Optional[int]:
        """Validate max executions."""
        if v is not None and v <= 0:
            raise ValueError("max_executions must be positive")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        # Convert schedule config to dict and ensure all datetime objects are strings
        schedule_config_dict = self.schedule_config.model_dump()
        schedule_config_dict = self._convert_datetime_to_string(schedule_config_dict)
        
        return {
            "user_id": self.user_id,
            "transaction_type": self.transaction_type,
            "tool_name": self.tool_name,
            "parameters": json.dumps(self.parameters),
            "schedule_type": self.schedule_config.schedule_type.value,
            "schedule_config": json.dumps(schedule_config_dict),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "next_execution": self.next_execution.isoformat() if self.next_execution else None,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "execution_count": self.execution_count,
            "max_executions": self.max_executions,
            "error_message": self.error_message,
            "metadata": json.dumps(self.metadata) if self.metadata else None,
        }
    
    def _convert_datetime_to_string(self, obj: Any) -> Any:
        """Recursively convert datetime objects to ISO strings."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._convert_datetime_to_string(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_datetime_to_string(item) for item in obj]
        else:
            return obj

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScheduledTransaction:
        """Create from dictionary loaded from database."""
        # Parse schedule config based on type
        schedule_type = ScheduleType(data["schedule_type"])
        schedule_config_data = json.loads(data["schedule_config"])
        
        if schedule_type == ScheduleType.ONCE:
            schedule_config = OnceScheduleConfig(**schedule_config_data)
        elif schedule_type == ScheduleType.RECURRING:
            schedule_config = RecurringScheduleConfig(**schedule_config_data)
        elif schedule_type == ScheduleType.CONDITIONAL:
            schedule_config = ConditionalScheduleConfig(**schedule_config_data)
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            transaction_type=data["transaction_type"],
            tool_name=data["tool_name"],
            parameters=json.loads(data["parameters"]),
            schedule_config=schedule_config,
            status=TransactionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            next_execution=datetime.fromisoformat(data["next_execution"]) if data["next_execution"] else None,
            last_execution=datetime.fromisoformat(data["last_execution"]) if data["last_execution"] else None,
            execution_count=data["execution_count"],
            max_executions=data["max_executions"],
            error_message=data["error_message"],
            metadata=json.loads(data["metadata"]) if data["metadata"] else None,
        )


class ScheduleTransactionInput(BaseModel):
    """Input model for scheduling a transaction."""
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(..., description="Parameters for the tool")
    schedule_type: ScheduleType = Field(..., description="Type of schedule")
    schedule_config: Dict[str, Any] = Field(..., description="Schedule configuration")
    max_executions: Optional[int] = Field(None, description="Maximum executions allowed")
    notes: Optional[str] = Field(None, description="User notes about the transaction")

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name."""
        allowed_tools = {
            "smart_buy", "smart_sell", "jupiter_swap", "transfer_sol",
            "pump_fun_buy", "pump_fun_sell", "aster_open_long", "aster_close_position"
        }
        if v not in allowed_tools:
            raise ValueError(f"Tool '{v}' is not schedulable. Allowed tools: {', '.join(allowed_tools)}")
        return v


class ListScheduledTransactionsInput(BaseModel):
    """Input model for listing scheduled transactions."""
    status: Optional[TransactionStatus] = Field(None, description="Filter by status")
    limit: int = Field(50, ge=1, le=200, description="Maximum number of transactions to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class CancelScheduledTransactionInput(BaseModel):
    """Input model for canceling a scheduled transaction."""
    transaction_id: int = Field(..., description="ID of the transaction to cancel")
