# Dani Cohen Financial Bot 📈

A comprehensive financial analysis bot that provides automated market insights through Telegram channels. The bot analyzes major market indices, generates technical analysis charts, and delivers AI-powered commentary using multiple LLM providers.

## 🚀 Features

- **Automated Market Analysis**: Daily technical analysis of S&P 500 and NASDAQ-100
- **Multi-Channel Distribution**: Sends analysis to both public and private Telegram channels
- **AI-Powered Insights**: Uses Claude (Anthropic), GPT-4 (OpenAI), and Perplexity AI for market commentary
- **Technical Indicators**: Dynamic channel analysis with support/resistance levels
- **Scheduled Operations**: Automated weekly technical analysis and monthly macro reports
- **Instagram Integration**: Automated social media posting capabilities
- **Hebrew Language Support**: Specialized prompts and character personas in Hebrew

## 📁 Project Structure

```
├── financial_bot/              # Main implementation (current version)
│   ├── main.py                # Entry point and orchestration
│   ├── config.py              # Configuration and environment variables
│   ├── telegram_bot.py        # Telegram integration
│   ├── chart_analyzer.py      # Technical analysis and chart generation
│   ├── macro_analyzer.py      # Macro economic analysis
│   ├── market_analysis.py     # Market data processing
│   ├── instagram_service.py   # Instagram automation
│   ├── characters_and_prompts.py # AI personas and prompts
│   └── requirements.txt       # Python dependencies
├── financial_bot - Copy/       # Legacy version (for reference)
├── 3_telegram.py              # Standalone OpenAI version
├── 4_telegram_claude.py       # Standalone Claude version
├── 5_telegram_claude_perplexity.py # Multi-LLM version
└── characters_and_prompts.py  # Shared AI prompts
```

## 🛠️ Setup

### Prerequisites

- Python 3.8+
- Telegram Bot Token
- API Keys for:
  - Anthropic Claude
  - OpenAI GPT-4
  - Perplexity AI
  - Replicate (for image generation)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/eyalRR/Dani-Cohen-FInancial-Bot.git
cd Dani-Cohen-FInancial-Bot
```

2. Install dependencies:

```bash
cd financial_bot
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory:

```env
# Telegram Bot API
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
CHANNEL_ID_PUBLIC=@YourPublicChannel
CHANNEL_ID_PRIVATE=-1001234567890

# AI API Keys
OPENAI_API_KEY=sk-your_openai_key
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key
PERPLEXITY_API_KEY=pplx-your_perplexity_key
REPLICATE_API_TOKEN=your_replicate_token

# Instagram (Optional)
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```

## 🚀 Usage

### Main Bot (Recommended)

```bash
cd financial_bot
python main.py
```

### Standalone Scripts

```bash
# OpenAI version
python 3_telegram.py

# Claude version
python 4_telegram_claude.py

# Multi-LLM version
python 5_telegram_claude_perplexity.py
```

## 📅 Automation Schedule

- **Weekly Technical Analysis**: Every Sunday - S&P 500 and NASDAQ-100 charts with AI commentary
- **Monthly Macro Report**: 18th of each month - Comprehensive market outlook using Perplexity AI
- **Motivation Posts**: 3 times daily (9:00, 15:00, 19:00) - Inspirational financial content

## 🤖 AI Personas

The bot uses specialized Hebrew-speaking financial advisor personas:

- **Dani Cohen**: Experienced Israeli investment advisor character
- **Technical Analysis Expert**: Focuses on chart patterns and market trends
- **Macro Economist**: Provides broader economic context and insights

## 🔧 Configuration

Key settings in `financial_bot/config.py`:

- Market indices to analyze
- Posting schedules
- AI model preferences
- Channel configurations

## 📊 Technical Analysis Features

- **Dynamic Channel Detection**: Identifies support and resistance levels
- **Multi-Timeframe Analysis**: Long-term and short-term trend analysis
- **Peak/Trough Identification**: Algorithmic detection of significant price points
- **Visual Chart Generation**: Professional candlestick charts with overlays

## 🔐 Security

- All API keys stored in environment variables
- Comprehensive `.gitignore` prevents credential exposure
- No hardcoded sensitive information in source code

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is private and proprietary. All rights reserved.

## 📞 Support

For questions or support, please contact the repository owner.

---

**Note**: This bot is designed for educational and informational purposes. Always consult with qualified financial advisors before making investment decisions.
