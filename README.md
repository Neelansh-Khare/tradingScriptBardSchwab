# Schwab-AI Portfolio Manager

A Python application that automatically connects to your Charles Schwab account via the schwab-py library and uses AI/LLM APIs (OpenAI, Claude, Gemini) to analyze and manage your portfolio with a risk-averse approach. It also integrates real-time market data from various providers.

## Overview

This application helps you manage your investment portfolio by:

1. Connecting to your Schwab account using the unofficial schwab-py API wrapper
2. Retrieving your current portfolio holdings and account information
3. Analyzing market data, news, and your portfolio using AI/LLM (Claude, GPT, etc.)
4. Executing trades based on risk-averse algorithms and AI recommendations
5. Providing detailed logs and reports of all analyses and transactions

## Features

- **Secure Authentication**: Manages OAuth authentication with Schwab API securely
- **Portfolio Analysis**: Retrieves and analyzes your current holdings
- **Real-time Market Data**: Integrates with multiple data providers (Alpha Vantage, Finnhub, Polygon.io, Yahoo Finance)
- **AI-Powered Insights**: Leverages LLMs (OpenAI, Claude, Gemini) to analyze market trends, news, and portfolio performance
- **Risk-Averse Algorithm**: Implements trading strategies focused on preserving capital
- **Automatic Trading**: Executes buy/sell orders based on AI recommendations
- **Customizable Risk Profile**: Adjust risk tolerance and investment preferences
- **Detailed Logging**: Comprehensive tracking of all analyses and transactions
- **Regular Reports**: Generate performance reports and insights with visualizations

## Prerequisites

- Charles Schwab brokerage account
- Charles Schwab Developer Account with API access
- Python 3.8+
- An API key for OpenAI, Anthropic, or other LLM provider

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/schwab-ai-portfolio-manager.git
cd schwab-ai-portfolio-manager
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Set up your configuration:
```bash
cp .env.example .env
```
Then edit the `.env` file with your API keys and account information.

## Configuration

Edit the `.env` file with the following information:

```
# Schwab API credentials
SCHWAB_API_KEY=your_api_key
SCHWAB_APP_SECRET=your_app_secret
SCHWAB_CALLBACK_URL=your_callback_url
SCHWAB_TOKEN_PATH=path/to/token.json
SCHWAB_ACCOUNT_ID=your_account_id

# LLM API credentials (choose one or more)
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4

ANTHROPIC_API_KEY=your_anthropic_key
ANTHROPIC_MODEL=claude-3-opus-20240229

GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-pro

# Market data API credentials (optional, will use yfinance as fallback)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
FINNHUB_API_KEY=your_finnhub_key
POLYGON_API_KEY=your_polygon_key

# Risk profile settings (1-10, where 1 is most conservative)
RISK_TOLERANCE=3
MAX_POSITION_SIZE_PERCENT=5
MAX_SECTOR_EXPOSURE_PERCENT=20

# Trading parameters
ENABLE_AUTO_TRADING=false  # Set to true to enable automatic trading
DRY_RUN=true  # Set to false to execute real trades
MAX_TRADES_PER_SESSION=5
MIN_CASH_RESERVE_PERCENT=5
```

## Usage

### Basic Usage

Run the main application:

```bash
python src/main.py
```

This will:
1. Connect to your Schwab account
2. Retrieve your portfolio
3. Analyze your holdings with AI
4. Generate recommendations
5. Execute trades if auto-trading is enabled

### Command-line Options

```bash
# Just analyze portfolio without making trades
python src/main.py --analyze-only

# Generate a detailed report
python src/main.py --generate-report

# Run with a custom configuration file
python src/main.py --config custom_config.yaml

# Perform a dry run (no actual trades)
python src/main.py --dry-run
```

## Project Structure

```
schwab-ai-portfolio-manager/
├── .env.example                 # Example environment configuration
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup file
├── src/
│   ├── main.py                  # Main application entry point
│   ├── schwab/
│   │   ├── __init__.py          
│   │   ├── auth.py              # Schwab authentication helper
│   │   ├── client.py            # Schwab API client wrapper
│   │   └── portfolio.py         # Portfolio data structures
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py            # LLM client interface
│   │   ├── claude.py            # Anthropic Claude implementation
│   │   ├── openai.py            # OpenAI GPT implementation
│   │   ├── gemini.py            # Google Gemini implementation
│   │   └── prompts.py           # LLM prompt templates
│   ├── data/
│   │   ├── __init__.py
│   │   └── market_data.py       # Real-time market data client
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── portfolio.py         # Portfolio analysis utilities
│   │   ├── risk.py              # Risk assessment algorithms
│   │   └── recommendation.py    # Trade recommendation engine
│   ├── trading/
│   │   ├── __init__.py
│   │   ├── executor.py          # Trade execution logic
│   │   ├── validation.py        # Order validation
│   │   └── strategy.py          # Trading strategies
│   └── utils/
│       ├── __init__.py
│       ├── config.py            # Configuration management
│       ├── logging.py           # Logging utilities
│       └── reporting.py         # Report generation
└── tests/
    ├── README.md                # Testing guide
    ├── __init__.py
    ├── test_auth.py             # Authentication tests
    ├── test_analysis.py         # Analysis tests
    └── test_trading.py          # Trading tests
```

## Risk-Averse Algorithm

The application uses a multi-factor risk assessment approach:

1. **Diversification Analysis**: Ensures portfolio is properly diversified across sectors and asset classes
2. **Volatility Management**: Favors lower-volatility investments
3. **Fundamental Analysis**: LLM evaluates company fundamentals (earnings, debt, etc.)
4. **News Sentiment**: Analyzes recent news for sentiment impact
5. **Market Trend Analysis**: Considers broader market trends
6. **Risk-Adjusted Return**: Optimizes for the best return given risk constraints

The trading algorithm prioritizes capital preservation over aggressive growth and implements stop-loss mechanisms to protect against significant downturns.

## Security Notes

- This application requires API access to your Schwab account and can make trades on your behalf
- API keys and credentials are stored locally in your `.env` file
- Always use the dry run mode first to verify behavior
- Enable auto-trading only after thorough testing
- Review all generated trade recommendations before execution

## Disclaimer

This is an unofficial tool using the schwab-py library, which is not affiliated with or endorsed by Charles Schwab. Use at your own risk. This tool does not constitute financial advice. Always consult with a financial advisor before making investment decisions.

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.