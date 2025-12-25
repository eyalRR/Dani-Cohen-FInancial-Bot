# Dani Cohen Financial Bot 📈

A comprehensive financial analysis bot that provides automated market insights through Telegram and Instagram. The bot analyzes major market indices, generates technical analysis charts, and delivers AI-powered commentary using multiple LLM providers.

## 🚀 Features

- **Automated Market Analysis**: Daily technical analysis of S&P 500 and NASDAQ-100.
- **Multi-Channel Distribution**: Sends analysis to both public and private Telegram channels.
- **AI-Powered Insights**: Uses Claude (Anthropic), GPT-4 (OpenAI), and Perplexity AI for market commentary.
- **Technical Indicators**: Dynamic channel analysis with support/resistance levels.
- **Scheduled Operations**: Automated weekly technical analysis and monthly macro reports.
- **Instagram Integration**: Automated social media posting capabilities.
- **Hebrew Language Support**: Specialized prompts and character personas in Hebrew.

## 📁 Project Structure

The project is organized with all source code located within the `financial_bot` directory.

```
/
├── financial_bot/              # Main application source code
│   ├── main.py                # Entry point and orchestration
│   ├── config.py              # Configuration and environment variables
│   ├── telegram_bot.py        # Telegram integration
│   ├── chart_analyzer.py      # Technical analysis and chart generation
│   ├── macro_analyzer.py      # Macro economic analysis
│   ├── market_analysis.py     # Market data processing
│   ├── instagram_service.py   # Instagram automation
│   ├── characters_and_prompts.py # AI personas and prompts
│   └── requirements.txt       # Python dependencies
│
├── .gitignore                  # Files and directories to ignore
├── README.md                   # This file
├── activate_env.bat            # Helper script to activate the environment
└── run_bot.bat                 # Helper script to run the bot on Windows
```

## 🛠️ Setup

### Prerequisites

- Python 3.8+
- Git
- Telegram Bot Token
- API Keys for:
  - Anthropic Claude
  - OpenAI GPT-4
  - Perplexity AI
  - Replicate (for image generation)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/eyalRR/Dani-Cohen-FInancial-Bot.git
    cd Dani-Cohen-FInancial-Bot
    ```

2.  **Create and activate the virtual environment:**
    - Create the environment:
      ```bash
      python -m venv financial_bot/.venv
      ```
    - Activate it. On Windows, you can use the helper script:
      ```bash
      activate_env.bat
      ```
      (On macOS/Linux: `source financial_bot/.venv/bin/activate`)

3.  **Install dependencies:**
    ```bash
    pip install -r financial_bot/requirements.txt
    ```

4.  **Create the environment file:**
    - In the project's **root directory**, create a file named `.env`.
    - Copy the contents of the example below and replace the placeholder values with your actual credentials.

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

### With the Helper Script (Windows)

The easiest way to run the bot is using the provided helper script. Simply double-click it or run it from your terminal:

```bash
run_bot.bat
```

### Manually (All Platforms)

1.  Make sure your virtual environment is activated.
2.  Run the main script from the project root directory:

    ```bash
    python financial_bot/main.py
    ```

## 📅 Automation Schedule

-   **Weekly Technical Analysis**: Every Sunday - S&P 500 and NASDAQ-100 charts with AI commentary.
-   **Monthly Macro Report**: 18th of each month - Comprehensive market outlook using Perplexity AI.
-   **Motivation Posts**: 3 times daily (9:00, 15:00, 19:00) - Inspirational financial content.

## 🤖 AI Personas

The bot uses specialized Hebrew-speaking financial advisor personas:

-   **Dani Cohen**: Experienced Israeli investment advisor character.
-   **Technical Analysis Expert**: Focuses on chart patterns and market trends.
-   **Macro Economist**: Provides broader economic context and insights.

## 🔧 Configuration

Key settings can be adjusted in `financial_bot/config.py`:

-   Market indices to analyze
-   Posting schedules
-   AI model preferences
-   Channel configurations

## 🔐 Security

-   All API keys and secrets are loaded from a `.env` file.
-   A comprehensive `.gitignore` file prevents credentials and temporary files from being committed.
-   No hardcoded sensitive information in the source code.

## 🤝 Contributing

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes (`git commit -m 'Add amazing feature'`).
4.  Push to the branch (`git push origin feature/amazing-feature`).
5.  Open a Pull Request.

## 📝 License

This project is private and proprietary. All rights reserved.

---

**Note**: This bot is designed for educational and informational purposes only. Always consult with a qualified financial advisor before making investment decisions.
