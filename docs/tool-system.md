# 🔧 Horizon Tool System

## Overview

Horizon's tool system is the core mechanism that enables the AI agent to interact with the Solana blockchain and external services. Each tool represents a specific capability that the agent can use to execute user requests.

## Tool Architecture

### Tool Definition

Every tool in Horizon follows a standardized structure:

```python
class Tool:
    def __init__(
        self,
        spec: ToolSpec,                    # Tool metadata and schema
        handler: Handler,                  # Async function implementation
        input_model: Optional[Type[BaseModel]] = None,  # Pydantic validation
    ):
```

### Tool Specification

```python
class ToolSpec(BaseModel):
    name: str                             # Unique tool identifier
    description: str                      # Human-readable description
    input_schema: Dict[str, Any]         # JSON schema for validation
    namespace: Optional[str] = None      # Logical grouping
    version: Optional[str] = None        # Tool version
```

## Tool Categories

### 1. Wallet Operations

#### `get_balance()`
**Purpose**: Retrieve complete wallet information including SOL and token balances.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```

**Response Format**:
```json
{
  "success": true,
  "wallet_address": "string",
  "sol_balance": "number",
  "sol_usd_value": "number",
  "tokens": [
    {
      "mint": "string",
      "symbol": "string",
      "name": "string",
      "balance": "number",
      "decimals": "number",
      "usd_value": "number"
    }
  ]
}
```

**Usage Example**:
```
User: "Check my wallet balance"
Agent: Calls get_balance() → Returns complete wallet overview
```

#### `transfer_sol()`
**Purpose**: Send SOL to a specified address.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "to_address": {"type": "string"},
    "amount": {"type": "number"}
  },
  "required": ["to_address", "amount"]
}
```

**Response Format**:
```json
{
  "success": true,
  "transaction_signature": "string",
  "amount_sent": "number",
  "recipient": "string"
}
```

### 2. Trading Operations

#### `smart_buy()`
**Purpose**: Intelligent token purchasing with automatic route optimization.

**Strategy**:
1. First attempts Pump.fun (for meme tokens)
2. Falls back to Jupiter DEX if Pump.fun fails
3. Provides optimal execution path

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "mint": {"type": "string"},
    "amount_sol": {"type": "number"},
    "slippage_percent": {"type": "number", "default": 5}
  },
  "required": ["mint", "amount_sol"]
}
```

**Response Format**:
```json
{
  "success": true,
  "route": "pump_fun|jupiter",
  "tokens_received": "number",
  "transaction_signature": "string",
  "execution_details": "object"
}
```

#### `pump_fun_buy()`
**Purpose**: Direct purchase on Pump.fun platform.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "mint": {"type": "string"},
    "amount_sol": {"type": "number"},
    "slippage_percent": {"type": "number", "default": 5}
  },
  "required": ["mint", "amount_sol"]
}
```

#### `pump_fun_sell()`
**Purpose**: Sell tokens on Pump.fun platform.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "mint": {"type": "string"},
    "percentage": {"type": "number"},
    "slippage_percent": {"type": "number", "default": 5}
  },
  "required": ["mint", "percentage"]
}
```

#### `jupiter_swap()`
**Purpose**: Execute token swaps via Jupiter DEX.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "input_mint": {"type": "string"},
    "output_mint": {"type": "string"},
    "amount": {"type": "number"},
    "slippage": {"type": "number", "default": 1}
  },
  "required": ["input_mint", "output_mint", "amount"]
}
```

### 3. Market Analysis Tools

#### `get_token_price()`
**Purpose**: Get real-time USD price for any Solana token.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "token_mint": {"type": "string"}
  },
  "required": ["token_mint"]
}
```

**Response Format**:
```json
{
  "success": true,
  "price_usd": "number",
  "price_change_24h": "number",
  "market_cap": "number",
  "volume_24h": "number"
}
```

#### `get_trending_pairs()`
**Purpose**: Get trending tokens on specified blockchain.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "chain": {"type": "string", "default": "solana"}
  },
  "required": []
}
```

**Response Format**:
```json
{
  "success": true,
  "trending_tokens": [
    {
      "pair_address": "string",
      "base_token": {
        "address": "string",
        "symbol": "string",
        "name": "string"
      },
      "price_usd": "number",
      "price_change_24h": "number",
      "volume_24h": "number"
    }
  ]
}
```

#### `search_pairs()`
**Purpose**: Search for trading pairs by query.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string"}
  },
  "required": ["query"]
}
```

### 4. Research Tools

#### `search_web()`
**Purpose**: Perform web research for market intelligence.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string"},
    "max_results": {"type": "number", "default": 5}
  },
  "required": ["query"]
}
```

**Response Format**:
```json
{
  "success": true,
  "results": [
    {
      "title": "string",
      "url": "string",
      "snippet": "string",
      "published_date": "string"
    }
  ]
}
```

#### `polymarket_search()`
**Purpose**: Search prediction markets for sentiment analysis.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string"}
  },
  "required": ["query"]
}
```

## Tool Execution Flow

### 1. Tool Discovery
```
User Request → Intent Analysis → Tool Selection → Schema Validation
```

### 2. Input Validation
```python
# Pydantic model validation
if tool.input_model is not None:
    model = tool.input_model(**(args or {}))
    validated_args = model.model_dump()
```

### 3. Middleware Chain
```python
# Security, logging, and monitoring middleware
call_chain: ToolCall = base_call
for mw in reversed(self._middlewares):
    call_chain = mw.wrap(name, call_chain)
```

### 4. Handler Execution
```python
# Async tool execution
result = await call_chain(validated_args, context)
```

### 5. Result Normalization
```python
# Consistent response format
{
    "success": bool,
    "data": Any,
    "error": Optional[str],
    "error_detail": Optional[Dict]
}
```

## Tool Registry Management

### Registration Process

```python
def register(registry: ToolRegistry, agent: Optional[SAMAgent] = None):
    registry.register(Tool(
        spec=ToolSpec(
            name="tool_name",
            description="Tool description",
            input_schema={"type": "object", "properties": {...}},
            namespace="integration_name",
            version="1.0.0"
        ),
        handler=tool_handler,
        input_model=ToolInputModel
    ))
```

### Tool Discovery

```python
# List all available tools
tools = registry.list_specs()

# Get specific tool
tool = registry.get_tool("tool_name")

# Check tool availability
available = registry.has_tool("tool_name")
```

## Error Handling

### Error Types

1. **Validation Errors**: Invalid input parameters
2. **Execution Errors**: Tool handler failures
3. **Network Errors**: API or blockchain connection issues
4. **Business Logic Errors**: Domain-specific failures

### Error Response Format

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_detail": {
    "code": "error_code",
    "message": "Detailed error message",
    "context": "Additional context"
  }
}
```

## Security Considerations

### 1. Input Validation
- **Type Safety**: Pydantic model validation
- **Schema Enforcement**: JSON schema validation
- **Sanitization**: Input cleaning and normalization
- **Range Checking**: Parameter bounds validation

### 2. Transaction Safety
- **Amount Limits**: Configurable transaction limits
- **Address Validation**: Solana address format checking
- **Slippage Protection**: Default slippage settings
- **Rate Limiting**: API call throttling

### 3. Access Control
- **User Isolation**: User-specific tool access
- **Permission Checks**: Tool execution permissions
- **Audit Logging**: Tool usage tracking
- **Error Masking**: Sensitive information protection

## Performance Optimization

### 1. Caching Strategy
- **Result Caching**: Cache tool results for repeated calls
- **Metadata Caching**: Cache token metadata and prices
- **Session Caching**: In-memory session data
- **TTL Management**: Cache expiration policies

### 2. Async Execution
- **Non-blocking Operations**: All tools are async
- **Concurrent Execution**: Parallel tool execution
- **Connection Pooling**: Efficient resource utilization
- **Timeout Management**: Request timeout handling

### 3. Resource Management
- **Memory Optimization**: Efficient memory usage
- **Connection Limits**: Resource constraint management
- **Cleanup Procedures**: Proper resource disposal
- **Monitoring**: Resource usage tracking

## Tool Development Guidelines

### 1. Tool Design Principles
- **Single Responsibility**: Each tool has one clear purpose
- **Idempotency**: Tools should be safe to retry
- **Error Handling**: Comprehensive error management
- **Documentation**: Clear tool descriptions and examples

### 2. Input Validation
```python
class ToolInput(BaseModel):
    parameter: str = Field(..., description="Parameter description")
    
    @validator('parameter')
    def validate_parameter(cls, v):
        if not v:
            raise ValueError("Parameter cannot be empty")
        return v
```

### 3. Error Handling
```python
async def tool_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Tool implementation
        result = await perform_operation(args)
        return {"success": True, "data": result}
    except ValidationError as e:
        return {"success": False, "error": f"Validation failed: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Operation failed: {e}"}
```

### 4. Testing
```python
@pytest.mark.asyncio
async def test_tool_execution():
    # Test successful execution
    result = await tool_handler({"parameter": "value"})
    assert result["success"] is True
    
    # Test error handling
    result = await tool_handler({"parameter": ""})
    assert result["success"] is False
```

## Integration Patterns

### 1. Blockchain Integration
- **RPC Management**: Efficient Solana RPC usage
- **Transaction Building**: Proper transaction construction
- **Error Handling**: Blockchain-specific error management
- **Retry Logic**: Network failure recovery

### 2. External API Integration
- **Rate Limiting**: API quota management
- **Authentication**: Secure API key handling
- **Error Handling**: API failure management
- **Caching**: Response caching strategies

### 3. Data Processing
- **Data Transformation**: Input/output data processing
- **Validation**: Data integrity checking
- **Normalization**: Consistent data formats
- **Aggregation**: Data combination and analysis

This tool system provides a robust, extensible foundation for AI-powered blockchain operations, enabling the agent to execute complex trading strategies while maintaining security, reliability, and performance.
