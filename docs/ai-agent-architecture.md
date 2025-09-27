# 🌅 Horizon AI Agent Architecture

## Overview

Horizon's AI Agent is a sophisticated system that combines Large Language Models (LLMs) with blockchain tools to create an autonomous trading agent. The architecture is designed for modularity, extensibility, and production-grade reliability.

## Core Architecture Components

### 1. Agent Core (`SAMAgent`)

The `SAMAgent` is the central orchestrator that coordinates all system components:

```python
class SAMAgent:
    def __init__(
        self,
        llm: LLMProvider,           # Language model for understanding
        tools: ToolRegistry,        # Available blockchain tools
        memory: MemoryManager,      # Session and context storage
        system_prompt: str,         # Agent behavior instructions
        event_bus: Optional[EventBus] = None,  # Event system
    ):
```

**Key Responsibilities:**
- **Message Processing**: Handles user input and maintains conversation context
- **Tool Orchestration**: Decides which tools to call based on user intent
- **Memory Management**: Stores and retrieves conversation history
- **Event Publishing**: Emits events for UI updates and monitoring
- **Session Statistics**: Tracks token usage and performance metrics

### 2. LLM Provider System

Horizon supports multiple LLM providers through a unified interface:

#### Supported Providers:
- **OpenAI**: GPT-4, GPT-4o, GPT-3.5-turbo
- **Anthropic**: Claude-3.5-Sonnet, Claude-3-Haiku
- **xAI**: Grok-2-latest
- **Local/OpenRouter**: Any OpenAI-compatible API

#### Provider Architecture:

```python
class LLMProvider:
    async def chat_completion(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> ChatResponse:
        raise NotImplementedError
```

**Key Features:**
- **Tool Calling**: Native support for function calling
- **Retry Logic**: Exponential backoff for reliability
- **Token Tracking**: Usage monitoring and cost optimization
- **Error Handling**: Graceful degradation on API failures

### 3. Tool Registry System

The tool registry manages all available blockchain operations:

#### Tool Structure:

```python
class Tool:
    def __init__(
        self,
        spec: ToolSpec,                    # Tool metadata and schema
        handler: Handler,                  # Async function implementation
        input_model: Optional[Type[BaseModel]] = None,  # Pydantic validation
    ):
```

#### Tool Categories:

**Wallet Operations:**
- `get_balance()` - Retrieve SOL and token balances
- `transfer_sol()` - Send SOL to addresses
- `get_token_data()` - Fetch token metadata

**Trading Operations:**
- `smart_buy()` - Intelligent token purchasing (Pump.fun → Jupiter fallback)
- `pump_fun_buy()` - Direct Pump.fun purchases
- `pump_fun_sell()` - Sell Pump.fun tokens
- `jupiter_swap()` - DEX token swaps

**Market Analysis:**
- `get_token_price()` - Real-time price data
- `get_trending_pairs()` - Trending tokens
- `search_pairs()` - Find trading pairs
- `get_token_pairs()` - Token pair information

**Research Tools:**
- `search_web()` - Web research capabilities
- `polymarket_search()` - Prediction market data

#### Tool Execution Flow:

1. **Validation**: Input validation using Pydantic models
2. **Middleware Chain**: Security, logging, and monitoring middleware
3. **Execution**: Async tool handler execution
4. **Result Normalization**: Consistent response format
5. **Error Handling**: Graceful error reporting

### 4. Memory Management System

The memory system provides persistent storage for conversation context:

#### Memory Architecture:

```python
class MemoryManager:
    async def load_session(self, session_id: str, user_id: str) -> List[Dict[str, Any]]
    async def save_session(self, session_id: str, user_id: str, messages: List[Dict[str, Any]])
    async def clear_session(self, session_id: str, user_id: str)
```

#### Storage Features:
- **Session Persistence**: Maintains conversation history across restarts
- **User Isolation**: Separate memory spaces per user
- **Context Compression**: Automatic context management for long conversations
- **Performance Optimization**: Efficient database operations with connection pooling

### 5. Event System

The event system enables real-time communication between components:

#### Event Types:
- `agent.status` - Agent state updates
- `agent.delta` - Streaming response content
- `agent.message` - Complete response messages
- `tool.called` - Tool execution start
- `tool.succeeded` - Tool execution success
- `tool.failed` - Tool execution failure
- `llm.usage` - Token usage statistics

#### Event Flow:
```
User Input → Agent → LLM → Tool Execution → Event Publishing → UI Updates
```

### 6. Agent Builder System

The `AgentBuilder` provides a factory pattern for creating configured agents:

#### Builder Process:

1. **LLM Initialization**: Create configured LLM provider
2. **Memory Setup**: Initialize memory manager with database
3. **Tool Registration**: Register all available tools
4. **Middleware Configuration**: Apply security and monitoring middleware
5. **Integration Loading**: Load blockchain integrations
6. **Plugin System**: Load external plugins
7. **Agent Assembly**: Create fully configured SAMAgent

#### Configuration-Driven:
- Environment variable configuration
- Feature flags for tool enablement
- Middleware configuration via JSON
- Plugin loading with allowlists

## Execution Flow

### 1. User Input Processing

```
User Input → Session Loading → Context Building → Message Chain Creation
```

**Details:**
- Load conversation history from memory
- Build message chain with system prompt
- Add conversation context and user input
- Apply anti-repetition logic

### 2. LLM Interaction

```
Message Chain → LLM Provider → Tool Selection → Response Generation
```

**Details:**
- Send messages and available tools to LLM
- LLM decides on tool calls or direct response
- Handle tool calling format conversion
- Track token usage and costs

### 3. Tool Execution

```
Tool Call → Validation → Middleware Chain → Handler Execution → Result Processing
```

**Details:**
- Validate tool arguments using Pydantic models
- Apply middleware (security, logging, monitoring)
- Execute tool handler asynchronously
- Normalize and return results

### 4. Response Generation

```
Tool Results → LLM Processing → Response Formatting → Memory Storage
```

**Details:**
- Send tool results back to LLM
- Generate final response to user
- Store conversation in memory
- Publish completion events

## Security Architecture

### 1. Private Key Management

- **Fernet Encryption**: AES encryption for private key storage
- **OS Keyring Integration**: Secure credential storage
- **Memory Protection**: Keys never logged or exposed
- **Access Control**: User-specific key isolation

### 2. Input Validation

- **Pydantic Models**: Type-safe input validation
- **Schema Validation**: JSON schema enforcement
- **Sanitization**: Input cleaning and normalization
- **Rate Limiting**: API call throttling

### 3. Transaction Safety

- **Amount Limits**: Configurable transaction limits
- **Slippage Protection**: Default slippage settings
- **Address Validation**: Solana address format checking
- **Error Handling**: Comprehensive error management

## Performance Optimizations

### 1. Async Architecture

- **Non-blocking Operations**: All I/O operations are async
- **Concurrent Execution**: Parallel tool execution where possible
- **Connection Pooling**: Efficient database and API connections
- **Resource Management**: Proper cleanup and resource disposal

### 2. Caching Strategy

- **Session Caching**: In-memory session data caching
- **Token Metadata**: Cached token information
- **Balance Data**: Cached wallet balance information
- **Price Data**: Cached market price information

### 3. Memory Management

- **Context Compression**: Automatic context size management
- **Session Cleanup**: Regular session cleanup and optimization
- **Resource Monitoring**: Memory usage tracking
- **Garbage Collection**: Efficient memory cleanup

## Integration Architecture

### 1. Blockchain Integrations

**Solana Core:**
- RPC connection management
- Transaction building and signing
- Account and balance queries
- Token metadata retrieval

**Jupiter DEX:**
- Swap quote generation
- Route optimization
- Transaction execution
- Slippage management

**Pump.fun:**
- Meme token trading
- Bonding curve interactions
- Token information retrieval
- Trading history access

### 2. External APIs

**DexScreener:**
- Market data aggregation
- Price tracking
- Volume analysis
- Trending token identification

**Polymarket:**
- Prediction market data
- Market sentiment analysis
- Event probability tracking

**Web Search:**
- Market research capabilities
- News aggregation
- Information synthesis

## Plugin System

### 1. Plugin Architecture

```python
def register(registry: ToolRegistry, agent: Optional[SAMAgent] = None):
    registry.register(Tool(
        spec=ToolSpec(
            name="custom_tool",
            description="Custom tool description",
            input_schema={"type": "object", "properties": {...}},
            namespace="custom",
            version="1.0.0"
        ),
        handler=custom_tool_handler
    ))
```

### 2. Plugin Features

- **Entry Point Discovery**: Automatic plugin loading
- **Namespace Organization**: Logical tool grouping
- **Version Management**: Plugin versioning support
- **Security Policies**: Plugin allowlists and restrictions

## Monitoring and Observability

### 1. Event Tracking

- **Tool Usage**: Track which tools are used most frequently
- **Performance Metrics**: Response times and success rates
- **Error Monitoring**: Comprehensive error tracking
- **User Analytics**: Usage patterns and behavior analysis

### 2. Logging System

- **Structured Logging**: JSON-formatted logs
- **Log Levels**: Configurable logging verbosity
- **Context Preservation**: Request context in logs
- **Performance Logging**: Detailed performance metrics

### 3. Health Monitoring

- **System Health**: Component health checks
- **Resource Usage**: Memory and CPU monitoring
- **API Status**: External API health monitoring
- **Database Health**: Database connection monitoring

## Scalability Considerations

### 1. Horizontal Scaling

- **Stateless Design**: Agent instances can be scaled horizontally
- **Session Management**: Distributed session storage
- **Load Balancing**: Multiple agent instances
- **Database Scaling**: Database connection pooling

### 2. Performance Optimization

- **Connection Pooling**: Efficient resource utilization
- **Caching Layers**: Multiple caching strategies
- **Async Processing**: Non-blocking operations
- **Resource Limits**: Configurable resource constraints

### 3. Fault Tolerance

- **Error Recovery**: Graceful error handling
- **Retry Logic**: Automatic retry mechanisms
- **Circuit Breakers**: API failure protection
- **Fallback Strategies**: Alternative execution paths

## Development and Testing

### 1. Testing Strategy

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end testing
- **Mock Services**: External service mocking
- **Performance Tests**: Load and stress testing

### 2. Development Tools

- **Type Safety**: Full type hinting with mypy
- **Code Quality**: Ruff linting and formatting
- **Documentation**: Comprehensive docstrings
- **Debugging**: Detailed logging and error reporting

### 3. Deployment

- **Containerization**: Docker support
- **Environment Management**: Configuration management
- **CI/CD**: Automated testing and deployment
- **Monitoring**: Production monitoring setup

This architecture provides a robust, scalable, and maintainable foundation for AI-powered blockchain trading, enabling autonomous execution of complex trading strategies while maintaining security and reliability.
