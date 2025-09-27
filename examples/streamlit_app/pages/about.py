import sys
from pathlib import Path
import streamlit as st

_PAGES_DIR = Path(__file__).resolve().parent
_APP_DIR = _PAGES_DIR.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
from ui_shared import inject_css  # noqa: E402

# Set page config with logo
try:
    logo_path = Path(__file__).parent.parent.parent / "logo.png"
    if logo_path.exists():
        st.set_page_config(page_title="About", page_icon=str(logo_path), layout="wide")
    else:
        st.set_page_config(page_title="About", page_icon="ℹ️", layout="wide")
except Exception:
    st.set_page_config(page_title="About", page_icon="ℹ️", layout="wide")

inject_css()

# Display Horizon logo
try:
    logo_path = Path(__file__).parent.parent.parent / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=100)
        st.title("About Horizon AI")
    else:
        st.title("ℹ️ About Horizon AI")  # Fallback to emoji
except Exception:
    st.title("ℹ️ About Horizon AI")  # Fallback to emoji

st.caption("The AI Tactician for Onchain Trading")

# Main description
st.markdown("""
## 🌅 What is Horizon AI?

**Horizon** is an AI-powered trading agent that transforms how you interact with the Solana blockchain. Instead of manually monitoring markets and executing trades, Horizon understands natural language commands and autonomously manages your onchain operations.

### 🎯 Key Features

- **🤖 AI-Powered Trading**: Natural language command processing and intelligent trade execution
- **🔧 15+ Tools**: Comprehensive blockchain operation toolkit
- **🔐 Secure Storage**: Encrypted private key management with user isolation
- **📊 Real-Time Intelligence**: Live market data integration and analysis
- **🎨 Modern Interface**: Beautiful Streamlit interface with real-time updates

### 🚀 How It Works

Simply chat with Horizon using natural language:
- "Check my wallet balance"
- "Buy 0.1 SOL worth of BONK"
- "What's trending on Solana right now?"
- "Research the latest news about Jupiter token"

Horizon understands your intent and executes the appropriate blockchain operations automatically.
""")

# Commands section
st.markdown("""
## 💬 Available Commands

### Slash Commands
Type these commands in the chat to navigate quickly:

| Command | Description | Example |
|---------|-------------|---------|
| `/settings` or `/config` | Open settings page | `/settings` |
| `/wallet` | Manage wallet and private keys | `/wallet` |
| `/tools` | View available trading tools | `/tools` |
| `/sessions` or `/session` | Manage conversation sessions | `/sessions` |
| `/clear`, `/new`, or `/reset` | Clear current conversation | `/clear` |

### Natural Language Commands

#### 💰 Wallet Operations
- **Balance Check**: "Check my wallet balance", "Show my SOL balance"
- **Transfer**: "Send 0.5 SOL to [address]", "Transfer 1 SOL to..."
- **Address**: "What's my wallet address?", "Show my address"

#### 🚀 Trading Operations
- **Buy Tokens**: "Buy 0.1 SOL worth of [token]", "Purchase [token]"
- **Sell Tokens**: "Sell 50% of [token]", "Sell all [token]"
- **Swap**: "Swap 1 SOL to USDC", "Exchange SOL for USDC"
- **Smart Trading**: "Buy [token]" (automatically uses optimal route)

#### 📊 Market Analysis
- **Price Check**: "What's the price of SOL?", "Price of [token]"
- **Trending**: "What's trending on Solana?", "Show trending tokens"
- **Research**: "Research [token] news", "Find information about [token]"
- **Market Data**: "Show market data for [token]"

#### 🔍 Advanced Queries
- **Portfolio**: "Show my portfolio", "What tokens do I own?"
- **Trading History**: "Show my recent trades", "Trading history"
- **Market Sentiment**: "What do markets think about [event]?"
- **Price Alerts**: "Alert me when [token] reaches $X"

### 🛠️ Available Tools

Horizon has access to 15+ specialized tools:

#### Core Trading Tools
- `smart_buy()` - Intelligent token purchasing (Pump.fun → Jupiter fallback)
- `pump_fun_buy()` - Direct Pump.fun purchases
- `pump_fun_sell()` - Sell Pump.fun tokens
- `jupiter_swap()` - DEX token swaps
- `transfer_sol()` - Send SOL to addresses

#### Market Analysis Tools
- `get_token_price()` - Real-time price data
- `get_trending_pairs()` - Trending tokens
- `search_pairs()` - Find trading pairs
- `get_token_pairs()` - Token pair information
- `get_sol_price()` - SOL price in USD

#### Research Tools
- `search_web()` - Web research capabilities
- `polymarket_search()` - Prediction market data

#### Wallet Tools
- `get_balance()` - Complete wallet overview
- `get_token_data()` - Token metadata
- `get_token_trades()` - Trading history

### 🎯 Smart Features

#### Intelligent Routing
- **Smart Buy**: Automatically tries Pump.fun first, falls back to Jupiter
- **Optimal Slippage**: Uses appropriate slippage based on token volatility
- **Route Optimization**: Finds the best execution path

#### Safety Features
- **Transaction Limits**: Configurable safety limits
- **Input Validation**: Comprehensive parameter validation
- **Error Handling**: Graceful error recovery
- **User Isolation**: Each browser session gets unique, isolated data

### 🔒 Security & Privacy

- **Encrypted Storage**: Private keys encrypted with Fernet encryption
- **User Isolation**: Each browser session has completely separate data
- **Secure Validation**: All inputs validated and sanitized
- **No Data Sharing**: Your data is never shared with other users

### 📱 Getting Started

1. **Set Up Wallet**: Go to `/wallet` to add your private key
2. **Start Trading**: Use natural language commands in the chat
3. **Explore Tools**: Check `/tools` to see all available capabilities
4. **Manage Sessions**: Use `/sessions` to organize conversations

### 🆘 Need Help?

- **Commands**: Type any of the slash commands above
- **Examples**: Try the natural language examples
- **Tools**: Visit `/tools` to see all available functions
- **Settings**: Use `/settings` to configure your preferences

---

**Horizon AI** - Where AI meets DeFi. Start trading with natural language today! 🚀
""")

# Footer
st.divider()
st.caption("🔒 Your data is secure and isolated. Each browser session gets unique, private data.")