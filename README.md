# 🌅 Horizon - AI-Powered Solana Agent Framework

**Horizon** is a production-ready AI agent framework for Solana blockchain operations, built on the SAM (Solana Agent Middleware) framework. It provides intelligent automation for trading, portfolio management, market analysis, and scheduled transactions.

## 🎯 Problem Statement

Traditional DeFi interactions require constant monitoring, manual execution, and complex timing decisions. Users need to:
- Monitor market conditions 24/7
- Execute trades at optimal times
- Manage complex portfolio strategies
- Handle time-sensitive transactions

**Horizon solves this** by providing an AI agent that can understand natural language commands and execute blockchain operations autonomously.

## 🏗️ Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Horizon Frontend                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Chat Interface│  │  Wallet Manager │  │  Scheduled   │ │
│  │   (Streamlit)   │  │                 │  │  Transactions│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SAM Framework                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   AI Agent      │  │   Tool Registry │  │  Memory      │ │
│  │   (LLM)         │  │   (15+ Tools)   │  │  Management  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Blockchain Integrations                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Solana        │  │   Jupiter       │  │  Pump.fun    │ │
│  │   (Core)        │  │   (DEX)         │  │  (Meme)      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   DexScreener   │  │   Polymarket    │  │  Web Search  │ │
│  │   (Analytics)   │  │   (Prediction)  │  │  (Research)  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

- **🤖 AI Agent**: Natural language understanding and execution
- **🔧 15+ Tools**: Comprehensive blockchain operation toolkit
- **⏰ Scheduled Transactions**: Time-based automation
- **🔐 Secure Storage**: Encrypted private key management
- **📊 Real-time Data**: Live market prices and analytics
- **🎨 Modern UI**: Beautiful Streamlit interface

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Solana wallet with private key
- API keys for LLM provider (OpenAI, Anthropic, or XAI)

### Installation

```bash
# Clone the repository
git clone https://github.com/MakindeAhmed2110/horizon.git
cd horizon

# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Configuration

Create a `.env` file with:

```bash
# Required
SAM_FERNET_KEY=your_encryption_key_here
LLM_PROVIDER=openai  # or anthropic, xai

# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
XAI_API_KEY=xai-...

# Optional
SAM_SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
DEFAULT_SLIPPAGE=2
MAX_TRANSACTION_SOL=1000
```

### Running Horizon

```bash
# Start the Streamlit web interface
uv run streamlit run examples/streamlit_app/app.py

# Or use the CLI
uv run sam
```

## 💡 Usage Examples

### Chat Interface

```
User: "Check my wallet balance"
Agent: "Your wallet contains 2.5 SOL ($500) and 3 tokens..."

User: "Buy 0.1 SOL worth of BONK"
Agent: "Executing buy order for 0.1 SOL worth of BONK..."

User: "Schedule a transfer of 1 SOL to [address] in 1 hour"
Agent: "Transaction scheduled for execution in 1 hour..."
```

### Scheduled Transactions

Horizon includes a powerful scheduling system:

- **Time-based execution**: "in 5 minutes", "tomorrow at 2 PM"
- **Condition-based execution**: Price targets, market conditions
- **Recurring transactions**: Daily, weekly, monthly
- **Real-time monitoring**: Live status updates

### Available Tools

| Tool | Description | Example |
|------|-------------|---------|
| `get_balance` | Check wallet balance | "Show my SOL balance" |
| `transfer_sol` | Send SOL | "Send 0.5 SOL to [address]" |
| `swap` | Token swaps via Jupiter | "Swap 1 SOL to USDC" |
| `pump_fun_buy` | Buy meme tokens | "Buy 0.1 SOL of [token]" |
| `get_token_price` | Get token prices | "What's the price of BONK?" |
| `simple_schedule` | Schedule transactions | "Schedule a buy in 10 minutes" |
| `search_web` | Web research | "Research [token] news" |

## 🔧 Development

### Project Structure

```
horizon/
├── sam/                    # Core SAM framework
│   ├── core/              # Agent, LLM, memory, tools
│   ├── integrations/      # Blockchain integrations
│   ├── config/            # Settings and prompts
│   └── utils/             # Utilities and security
├── examples/
│   ├── streamlit_app/     # Web interface
│   ├── plugins/           # Custom plugins
│   └── sdk/               # SDK examples
└── tests/                 # Test suite
```

### Adding New Tools

```python
from sam.core.tools import Tool, ToolSpec

async def my_tool_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    # Your tool logic here
    return {"success": True, "result": "..."}

def register(registry, agent=None):
    registry.register(Tool(
        spec=ToolSpec(
            name="my_tool",
            description="What this tool does",
            input_schema={"type": "object", "properties": {...}},
            namespace="my_integration",
            version="1.0.0"
        ),
        handler=my_tool_handler
    ))
```

### Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=sam

# Run specific test
uv run pytest tests/test_tools.py::test_balance_check
```

## 🔐 Security

- **Private Key Encryption**: Fernet encryption with OS keyring integration
- **Input Validation**: Pydantic models for all inputs
- **Rate Limiting**: Built-in API rate limiting
- **Transaction Limits**: Configurable safety limits
- **Error Handling**: Comprehensive error management

## 📊 Performance

- **Async Architecture**: Non-blocking operations
- **Connection Pooling**: Efficient RPC connections
- **Caching**: Smart caching for frequently accessed data
- **Memory Management**: Context compression for long sessions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style

- Python 3.11+ with type hints
- 100-character line length
- Async-first architecture
- Comprehensive error handling

## 📄 License

MIT License - see LICENSE file for details.

## 🏆 Hackathon Submission

**Horizon** was built for the Solana hackathon with the following goals:

- ✅ **Innovation**: First AI agent framework for Solana
- ✅ **Usability**: Natural language interface
- ✅ **Functionality**: 15+ blockchain tools
- ✅ **Security**: Production-ready security measures
- ✅ **Scalability**: Extensible plugin architecture

### Demo Video

[Link to demo video showcasing Horizon's capabilities]

### Live Demo

[Link to live demo instance]

## 📞 Support

- **Documentation**: [Link to docs]
- **Discord**: [Link to Discord]
- **Twitter**: [@HorizonSolana]
- **Email**: support@horizon-solana.com

---

**Built with ❤️ for the Solana ecosystem**
