# BTS - Bitcoin Auto Trading System

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> Professional-grade Bitcoin automated trading system with Clean Architecture design

[한국어 문서](README_KR.md) | [Strategy Guide](docs/strategy_guide.md) | [API Reference](docs/api_reference.md)

## 🎯 Overview

BTS is a professional Bitcoin automated trading system designed with Clean Architecture principles, featuring:

- **Virtual Wallet System**: Safe paper trading for strategy testing
- **4-Tier Strategy Framework**: Screening → Entry → Portfolio → Exit
- **AI-Powered Evaluation**: Claude & OpenAI integration for signal validation
- **Comprehensive Backtesting**: Historical performance analysis with slippage & Sharpe ratio
- **Multi-Exchange Support**: Upbit priority (extensible architecture)

## ✨ Key Features

### 📊 Trading Strategies

#### 1. Screening Strategies
Automatically select high-potential coins from KRW/BTC markets:
- **Momentum-based**: Price change, volume increase, RSI momentum
- **Volume-based**: Trading volume surge detection
- **Technical Indicators**: RSI + MACD + MA combination
- **Hybrid**: Weighted combination of multiple strategies

#### 2. Entry Strategies
Optimal entry timing detection:
- **RSI**: Oversold bounce detection
- **MA Cross**: Golden cross signals
- **Bollinger Bands**: Lower band touch/breakout
- **MACD**: Golden cross & histogram reversal
- **Stochastic**: Oversold %K/%D crossover
- **Multi-Indicator**: AND/OR combination modes

#### 3. Portfolio Strategies
Efficient capital allocation:
- **Equal Weight**: Identical allocation to all assets
- **Proportional Weight**: Rank-based or custom weights
- **Kelly Criterion**: Mathematically optimal position sizing
- **Risk Parity**: Inverse volatility weighting
- **Dynamic Allocation**: Market condition-based adjustment

#### 4. Exit Strategies
Profit-taking & loss-cutting:
- **Fixed Target**: Profit target & stop loss
- **Ladder Exit**: Stepped profit-taking
- **Trailing Stop**: Dynamic stop following highest price
- **ATR-based Stop**: Volatility-adjusted stop loss
- **Multi-Condition**: OR combination of exit signals

### 🤖 AI Evaluation System

**Multi-Provider Support**: Claude (Anthropic) & OpenAI (GPT)

- **Token Optimization**: Only recent 20 candles + summarized indicators
- **Fallback System**: Automatic model switching on failure
  - Claude: `claude-3-5-sonnet-20241022` → `claude-3-5-haiku-20241022`
  - OpenAI: `gpt-4o` → `gpt-4o-mini`
- **Result Caching**: 15-minute TTL for cost reduction
- **Signal Combination**: Weighted average (Strategy 60% + AI 40%)

### 📈 Backtesting Engine

Comprehensive performance analysis:
- **Realistic Simulation**: Slippage (0.1%) & commission (0.05%)
- **Performance Metrics**: Sharpe ratio, MDD, win rate, P&L ratio
- **Visual Analysis**: Equity curve, drawdown chart, trade distribution
- **Strategy Comparison**: Side-by-side comparison of multiple strategies

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Upbit API key (for live trading)
- Claude API key or OpenAI API key (for AI evaluation)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/BTS.git
cd BTS

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -m infrastructure.database.init_db
```

### Configuration

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Upbit API (optional for paper trading)
UPBIT_ACCESS_KEY=your_access_key
UPBIT_SECRET_KEY=your_secret_key

# AI Provider Selection
AI_PROVIDER=claude  # or openai

# Claude API
CLAUDE_API_KEY=your_claude_api_key
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_FALLBACK_MODEL=claude-3-5-haiku-20241022

# OpenAI API
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
OPENAI_FALLBACK_MODEL=gpt-4o-mini

# Trading Mode
TRADING_MODE=paper  # paper or live
INITIAL_BALANCE=10000000
```

### Running the Application

```bash
# Start Streamlit web interface
streamlit run presentation/streamlit_app.py

# Or run specific services
python application/services/strategy_service.py
python application/services/screening_service.py
```

Access the web interface at: `http://localhost:8501`

## 📖 Usage Guide

### 1. Create Virtual Wallet

1. Navigate to **Virtual Wallet** page
2. Click "Create Wallet"
3. Set initial balance (default: 10,000,000 KRW)

### 2. Screen Promising Coins

1. Go to **Screening** page
2. Select market (KRW or BTC)
3. Choose screening strategy
4. Adjust parameters
5. Click "Run Screening"
6. Review top-ranked coins

### 3. Configure Trading Strategy

1. Open **Strategy Settings** page
2. Select entry strategy (RSI, MACD, etc.)
3. Configure parameters
4. Activate strategy
5. Monitor signals in Dashboard

### 4. Allocate Portfolio

1. Visit **Portfolio** page
2. Select wallet
3. Choose allocation strategy
4. Input symbols (or use screening results)
5. Click "Execute Allocation"
6. Review distribution chart

### 5. Backtest Performance

1. Go to **Backtest** page
2. Select strategy
3. Set date range
4. Run backtest
5. Analyze metrics & charts

## 🏗️ Architecture

### Clean Architecture Layers

```
┌─────────────────────────────────────┐
│   Presentation Layer (Streamlit)    │  ← User Interface
├─────────────────────────────────────┤
│   Application Layer (Services)      │  ← Use Cases
├─────────────────────────────────────┤
│   Domain Layer (Models/Strategies)  │  ← Business Logic
├─────────────────────────────────────┤
│   Infrastructure Layer              │  ← External Services
│   (Database, Exchange, AI APIs)     │
└─────────────────────────────────────┘
```

### Directory Structure

```
BTS/
├── core/                   # Domain models & enums
│   ├── models.py
│   └── enums.py
├── domain/                 # Business logic
│   ├── entities/
│   └── strategies/
│       ├── screening/      # Screening strategies
│       ├── entry/          # Entry strategies
│       ├── exit/           # Exit strategies
│       └── portfolio/      # Portfolio strategies
├── application/            # Use cases
│   └── services/
├── infrastructure/         # External interfaces
│   ├── database/
│   ├── exchanges/
│   └── ai/                 # AI clients
│       ├── claude_client.py
│       ├── openai_client.py
│       └── data_summarizer.py
├── presentation/           # UI layer
│   ├── streamlit_app.py
│   ├── pages/
│   └── components/
└── utils/                  # Utilities
```

## 🔧 Advanced Configuration

### Custom Strategy Development

Create your own strategy by inheriting base classes:

```python
from domain.strategies.entry.base_entry import BaseEntryStrategy

class MyCustomEntry(BaseEntryStrategy):
    def check_entry_condition(self, ohlcv_data, indicators):
        # Your logic here
        return should_enter, confidence
```

### AI Provider Switching

Runtime switching via UI or programmatic:

```python
from application.services.ai_evaluation_service import AIEvaluationService

# Use Claude
service = AIEvaluationService(provider="claude")

# Or OpenAI
service = AIEvaluationService(provider="openai")
```

## 📊 Performance Metrics

The backtesting engine calculates:

- **Total Return**: Overall profit/loss percentage
- **Sharpe Ratio**: Risk-adjusted return
- **Max Drawdown (MDD)**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Profit/Loss Ratio**: Average win vs average loss
- **Total Trades**: Number of executed trades

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**This software is for educational and research purposes only.**

- Cryptocurrency trading involves substantial risk
- Past performance does not guarantee future results
- Always conduct thorough testing before live trading
- The authors are not responsible for any financial losses

## 🙏 Acknowledgments

- [Upbit](https://upbit.com/) - Korean cryptocurrency exchange
- [Anthropic Claude](https://www.anthropic.com/) - AI evaluation
- [OpenAI](https://openai.com/) - AI evaluation
- [Streamlit](https://streamlit.io/) - Web framework

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ using Clean Architecture principles**
