# 🧠 Horizon LLM Integration

## Overview

Horizon's LLM integration provides a unified interface for multiple Large Language Model providers, enabling the AI agent to understand natural language commands and execute blockchain operations autonomously.

## Supported LLM Providers

### 1. OpenAI
- **Models**: GPT-4, GPT-4o, GPT-3.5-turbo
- **Features**: Function calling, streaming, token tracking
- **Base URL**: `https://api.openai.com/v1` (configurable)

### 2. Anthropic (Claude)
- **Models**: Claude-3.5-Sonnet, Claude-3-Haiku
- **Features**: Advanced reasoning, function calling
- **Base URL**: `https://api.anthropic.com` (configurable)

### 3. xAI (Grok)
- **Models**: Grok-2-latest
- **Features**: Real-time information, function calling
- **Base URL**: `https://api.x.ai/v1` (configurable)

### 4. Local/OpenRouter
- **Models**: Any OpenAI-compatible model
- **Features**: Local deployment, custom models
- **Base URL**: Configurable (e.g., `http://localhost:11434/v1`)

## LLM Provider Architecture

### Base Provider Interface

```python
class LLMProvider:
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> ChatResponse:
        raise NotImplementedError
```

### ChatResponse Structure

```python
@dataclass
class ChatResponse:
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
```

## Provider Implementations

### OpenAI-Compatible Provider

```python
class OpenAICompatibleProvider(LLMProvider):
    async def chat_completion(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> ChatResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages
        }
        
        # Add tools if provided
        if tools:
            formatted_tools = []
            for tool in tools:
                function_def = {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
                formatted_tools.append({
                    "type": "function",
                    "function": function_def
                })
            
            payload["tools"] = formatted_tools
            payload["tool_choice"] = "auto"
        
        # Execute request with retry logic
        return await self._make_request(payload)
```

### xAI Provider

```python
class XAIProvider(OpenAICompatibleProvider):
    async def chat_completion(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> ChatResponse:
        payload = {
            "model": self.model,
            "messages": messages
        }
        
        # Format tools for xAI compatibility
        if tools:
            formatted_tools = []
            for tool in tools:
                cleaned_params = self._clean_parameters(tool["input_schema"])
                function_def = {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": cleaned_params
                }
                formatted_tools.append({
                    "type": "function",
                    "function": function_def
                })
            
            if formatted_tools:
                payload["tools"] = formatted_tools
                payload["tool_choice"] = "auto"
        
        return await self._make_request(payload)
    
    def _clean_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Clean parameters for xAI compatibility."""
        # Remove complex schemas that might cause issues
        cleaned = {}
        for key, value in parameters.items():
            if isinstance(value, dict) and "type" in value:
                cleaned[key] = value
        return cleaned
```

## Tool Calling Integration

### Tool Format Conversion

The LLM integration automatically converts Horizon's tool specifications to the appropriate format for each provider:

```python
def format_tools_for_provider(tools: List[Dict[str, Any]], provider: str) -> List[Dict[str, Any]]:
    formatted_tools = []
    
    for tool in tools:
        if provider == "openai":
            function_def = {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"]
            }
            formatted_tools.append({
                "type": "function",
                "function": function_def
            })
        
        elif provider == "anthropic":
            # Anthropic-specific formatting
            formatted_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            })
    
    return formatted_tools
```

### Tool Call Processing

```python
async def process_tool_calls(tool_calls: List[Dict[str, Any]], tools: ToolRegistry) -> List[Dict[str, Any]]:
    results = []
    
    for tool_call in tool_calls:
        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(tool_call["function"]["arguments"])
        
        # Execute tool
        result = await tools.call(tool_name, tool_args)
        
        results.append({
            "tool_call_id": tool_call["id"],
            "name": tool_name,
            "content": json.dumps(result)
        })
    
    return results
```

## Configuration Management

### Environment Variables

```bash
# LLM Provider Selection
LLM_PROVIDER=openai  # openai, anthropic, xai, local

# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Anthropic Configuration
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-3-5-sonnet-latest

# xAI Configuration
XAI_API_KEY=xai-...
XAI_BASE_URL=https://api.x.ai/v1
XAI_MODEL=grok-2-latest

# Local/OpenRouter Configuration
LOCAL_LLM_BASE_URL=https://openrouter.ai/api/v1
LOCAL_LLM_API_KEY=sk-or-...
LOCAL_LLM_MODEL=openai/gpt-4o
```

### Provider Factory

```python
def create_llm_provider() -> LLMProvider:
    """Factory to create the configured LLM provider."""
    provider = Settings.LLM_PROVIDER
    
    # Check for external provider plugins first
    try:
        eps = entry_points(group="sam.llm_providers")
        for ep in eps:
            if ep.name == provider:
                factory = ep.load()
                instance = factory(Settings)
                if isinstance(instance, LLMProvider):
                    return instance
    except Exception:
        pass
    
    # Built-in providers
    if provider == "openai":
        return OpenAICompatibleProvider(
            api_key=Settings.OPENAI_API_KEY,
            model=Settings.OPENAI_MODEL,
            base_url=Settings.OPENAI_BASE_URL
        )
    
    elif provider == "anthropic":
        return AnthropicProvider(
            api_key=Settings.ANTHROPIC_API_KEY,
            model=Settings.ANTHROPIC_MODEL,
            base_url=Settings.ANTHROPIC_BASE_URL
        )
    
    elif provider == "xai":
        return XAIProvider(
            api_key=Settings.XAI_API_KEY,
            model=Settings.XAI_MODEL,
            base_url=Settings.XAI_BASE_URL
        )
    
    elif provider in ("openai_compat", "local"):
        base_url = (
            Settings.OPENAI_BASE_URL if provider == "openai_compat" 
            else Settings.LOCAL_LLM_BASE_URL
        )
        api_key = (
            Settings.OPENAI_API_KEY if provider == "openai_compat"
            else Settings.LOCAL_LLM_API_KEY
        )
        model = (
            Settings.OPENAI_MODEL if provider == "openai_compat"
            else Settings.LOCAL_LLM_MODEL
        )
        
        return OpenAICompatibleProvider(
            api_key=api_key,
            model=model,
            base_url=base_url
        )
    
    # Fallback to OpenAI
    return OpenAICompatibleProvider(
        api_key=Settings.OPENAI_API_KEY,
        model=Settings.OPENAI_MODEL,
        base_url=Settings.OPENAI_BASE_URL
    )
```

## Error Handling and Retry Logic

### Retry Strategy

```python
async def _make_request(self, payload: Dict[str, Any]) -> ChatResponse:
    max_retries = 3
    base_delay = 1.0
    
    for attempt in range(max_retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_response(data)
                    else:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
        
        except Exception as e:
            if attempt == max_retries:
                raise
            
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
            await asyncio.sleep(delay)
    
    raise Exception("Maximum retries exceeded")
```

### Error Types

1. **Network Errors**: Connection timeouts, DNS failures
2. **API Errors**: Rate limits, authentication failures
3. **Model Errors**: Invalid requests, model overload
4. **Parsing Errors**: Malformed responses

### Error Recovery

```python
async def handle_llm_error(error: Exception, attempt: int) -> bool:
    """Determine if error is retryable."""
    if isinstance(error, aiohttp.ClientTimeout):
        return True  # Network timeout - retry
    
    if isinstance(error, aiohttp.ClientResponseError):
        if error.status in [429, 500, 502, 503, 504]:
            return True  # Rate limit or server error - retry
        if error.status == 401:
            return False  # Authentication error - don't retry
    
    return attempt < 2  # Retry other errors up to 2 times
```

## Token Usage Tracking

### Usage Statistics

```python
class TokenUsage:
    def __init__(self):
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.requests = 0
    
    def update(self, usage: Dict[str, int]):
        self.total_tokens += usage.get("total_tokens", 0)
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)
        self.requests += 1
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "requests": self.requests,
            "average_tokens_per_request": (
                self.total_tokens / self.requests if self.requests > 0 else 0
            )
        }
```

### Cost Estimation

```python
def estimate_cost(usage: Dict[str, int], provider: str, model: str) -> float:
    """Estimate cost based on token usage and provider pricing."""
    pricing = {
        "openai": {
            "gpt-4o": {"prompt": 0.005, "completion": 0.015},
            "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
            "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002}
        },
        "anthropic": {
            "claude-3-5-sonnet": {"prompt": 0.003, "completion": 0.015},
            "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125}
        }
    }
    
    if provider not in pricing or model not in pricing[provider]:
        return 0.0
    
    prompt_cost = (usage.get("prompt_tokens", 0) / 1000) * pricing[provider][model]["prompt"]
    completion_cost = (usage.get("completion_tokens", 0) / 1000) * pricing[provider][model]["completion"]
    
    return prompt_cost + completion_cost
```

## Streaming Support

### Streaming Response Handling

```python
async def stream_chat_completion(
    self, 
    messages: List[Dict[str, Any]], 
    tools: Optional[List[Dict[str, Any]]] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream chat completion responses."""
    payload = self._build_payload(messages, tools)
    payload["stream"] = True
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{self.base_url}/chat/completions",
            headers=self._get_headers(),
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            async for line in response.content:
                if line.startswith(b"data: "):
                    data = line[6:].decode("utf-8").strip()
                    if data == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data)
                        yield chunk
                    except json.JSONDecodeError:
                        continue
```

### Event Publishing

```python
async def publish_streaming_events(
    self, 
    stream: AsyncGenerator[Dict[str, Any], None],
    event_bus: EventBus
):
    """Publish streaming events to event bus."""
    async for chunk in stream:
        if "choices" in chunk:
            choice = chunk["choices"][0]
            if "delta" in choice:
                delta = choice["delta"]
                if "content" in delta:
                    await event_bus.publish("agent.delta", {
                        "content": delta["content"]
                    })
                elif "tool_calls" in delta:
                    await event_bus.publish("tool.called", {
                        "name": delta["tool_calls"][0]["function"]["name"],
                        "args": delta["tool_calls"][0]["function"]["arguments"]
                    })
```

## Performance Optimization

### Connection Pooling

```python
class LLMProvider:
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with connection pooling."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
```

### Request Batching

```python
async def batch_requests(
    self, 
    requests: List[Dict[str, Any]]
) -> List[ChatResponse]:
    """Batch multiple requests for efficiency."""
    tasks = []
    for request in requests:
        task = self.chat_completion(
            request["messages"],
            request.get("tools")
        )
        tasks.append(task)
    
    return await asyncio.gather(*tasks, return_exceptions=True)
```

## Security Considerations

### API Key Management

```python
class SecureLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        # Store encrypted API key
        self._encrypted_key = self._encrypt_key(api_key)
        self.model = model
        self.base_url = base_url
    
    def _encrypt_key(self, key: str) -> bytes:
        """Encrypt API key for storage."""
        from cryptography.fernet import Fernet
        fernet = Fernet(Settings.SAM_FERNET_KEY.encode())
        return fernet.encrypt(key.encode())
    
    def _get_api_key(self) -> str:
        """Decrypt API key for use."""
        from cryptography.fernet import Fernet
        fernet = Fernet(Settings.SAM_FERNET_KEY.encode())
        return fernet.decrypt(self._encrypted_key).decode()
```

### Request Validation

```python
def validate_request(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> bool:
    """Validate request before sending to LLM."""
    # Check message format
    for message in messages:
        if "role" not in message or "content" not in message:
            return False
        if message["role"] not in ["system", "user", "assistant"]:
            return False
    
    # Check tool format
    if tools:
        for tool in tools:
            if "name" not in tool or "description" not in tool:
                return False
    
    return True
```

## Monitoring and Observability

### Metrics Collection

```python
class LLMMetrics:
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_tokens = 0
        self.response_times = []
    
    def record_request(self, tokens: int, response_time: float, success: bool):
        self.request_count += 1
        if not success:
            self.error_count += 1
        self.total_tokens += tokens
        self.response_times.append(response_time)
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "total_tokens": self.total_tokens,
            "average_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0
        }
```

### Health Checks

```python
async def health_check(provider: LLMProvider) -> Dict[str, Any]:
    """Check LLM provider health."""
    try:
        start_time = time.time()
        response = await provider.chat_completion([
            {"role": "user", "content": "Hello"}
        ])
        response_time = time.time() - start_time
        
        return {
            "status": "healthy",
            "response_time": response_time,
            "model": provider.model,
            "provider": provider.__class__.__name__
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "model": provider.model,
            "provider": provider.__class__.__name__
        }
```

This LLM integration provides a robust, scalable foundation for AI-powered blockchain operations, supporting multiple providers with comprehensive error handling, performance optimization, and security features.
