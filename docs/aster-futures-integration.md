# 🚀 Aster Futures Trading Integration

SAM Framework now includes professional futures trading capabilities through Aster DEX integration.

## Overview

The Aster futures trading agent provides:
- **Leveraged Trading**: Open long/short positions with up to 125x leverage
- **Risk Management**: Built-in position sizing and margin monitoring
- **Professional Tools**: Account management, trade history, and performance tracking
- **AI-Powered**: Natural language trading commands with intelligent risk assessment

## Quick Start

### 1. Set Up Aster API Credentials

```bash
# Set your Aster API credentials
export ASTER_API_KEY=your_aster_api_key
export ASTER_API_SECRET=your_aster_api_secret

# Enable Aster futures tools (enabled by default)
export ENABLE_ASTER_FUTURES_TOOLS=true
```

### 2. Start the Futures Trading Agent

```bash
# Start the specialized futures trading agent
sam futures

# Or with custom session
sam futures --session my_trading_session
```

### 3. Start Trading

The agent will greet you with available commands:

```
🚀 Aster Futures Trading Agent
Professional leveraged trading on Aster DEX

Available Commands:
  Check account balance     - aster_account_balance()
  Open long position       - aster_open_long(symbol, usd_notional, leverage)
  Close position          - aster_close_position(symbol)
  Check positions         - aster_position_check(symbol)
  View trade history      - aster_trade_history(symbol)

Example: 'Open a $100 long position on SOL with 5x leverage'
```

## Available Tools

### Account Management
- `aster_account_balance()` - Get detailed account balance and margin status
- `aster_account_info()` - Get comprehensive account information

### Position Management
- `aster_open_long(symbol, usd_notional, leverage)` - Open leveraged long positions
- `aster_close_position(symbol, quantity, position_side)` - Close or reduce positions
- `aster_position_check(symbol)` - Monitor current positions and risk

### Trade History
- `aster_trade_history(symbol, limit)` - Review trading history and performance

## Trading Examples

### Natural Language Commands

```
# Check account balance
"Show my account balance"

# Open a long position
"Open a $100 long position on SOL with 5x leverage"

# Check current positions
"Show my current positions"

# Close a position
"Close my SOL position"

# View trade history
"Show my recent trades for SOL"
```

### Direct Tool Usage

```python
# Open long position
await agent.tools.call("aster_open_long", {
    "symbol": "SOLUSDT",
    "usd_notional": 100,
    "leverage": 5
})

# Check positions
await agent.tools.call("aster_position_check", {
    "symbol": "SOLUSDT"
})

# Close position
await agent.tools.call("aster_close_position", {
    "symbol": "SOLUSDT"
})
```

## Risk Management Features

The futures trading agent includes built-in risk management:

### Position Sizing
- Maximum 2% of account per trade
- Automatic position size calculation based on risk tolerance
- Support for both quantity and USD notional sizing

### Leverage Management
- Appropriate leverage based on volatility (2x-10x)
- Automatic leverage adjustment before opening positions
- Maximum leverage limits enforcement

### Margin Monitoring
- Continuous margin requirement monitoring
- Automatic position closure if margin ratio becomes dangerous
- Real-time account equity tracking

## Configuration

### Environment Variables

```bash
# Required
ASTER_API_KEY=your_api_key
ASTER_API_SECRET=your_api_secret

# Optional
ASTER_BASE_URL=https://fapi.asterdex.com
ASTER_DEFAULT_RECV_WINDOW=5000
ENABLE_ASTER_FUTURES_TOOLS=true
```

### Settings

The integration respects SAM Framework's security settings:
- Encrypted credential storage
- Rate limiting for API calls
- Input validation and sanitization
- Secure key management

## Security Features

- **Encrypted Storage**: API credentials stored with Fernet encryption
- **Secure Validation**: All inputs validated and sanitized
- **Rate Limiting**: API calls rate-limited to prevent abuse
- **Error Handling**: Graceful error handling with detailed logging

## Testing

Run the integration test:

```bash
python test_aster_futures.py
```

This will verify:
- Configuration is correct
- Agent builds successfully
- Tools are properly registered
- Basic functionality works

## Troubleshooting

### Common Issues

1. **"Aster futures tools are disabled"**
   - Set `ENABLE_ASTER_FUTURES_TOOLS=true`

2. **"Aster API credentials not found"**
   - Set `ASTER_API_KEY` and `ASTER_API_SECRET`

3. **"Failed to initialize futures trading agent"**
   - Check API credentials are valid
   - Verify network connectivity to Aster API

4. **"Account balance check failed"**
   - API credentials may be invalid
   - Account may be empty or not set up

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
sam futures
```

## Advanced Usage

### Custom System Prompt

You can customize the trading agent's behavior by modifying the system prompt in `sam/config/prompts.py`:

```python
ASTER_FUTURES_TRADING_PROMPT = """
Your custom trading instructions here...
"""
```

### Integration with Other Tools

The futures trading agent can be combined with other SAM tools:

```python
# Use with market analysis tools
from sam.core.builder import AgentBuilder

# Build agent with both futures and market tools
agent = await AgentBuilder().build()
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the logs with `LOG_LEVEL=DEBUG`
3. Test with the provided test script
4. Check Aster DEX documentation for API details

## License

This integration follows the same license as SAM Framework.







