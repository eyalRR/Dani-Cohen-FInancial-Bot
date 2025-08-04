# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    CHANNEL_ID_PUBLIC = os.getenv('CHANNEL_ID_PUBLIC')
    CHANNEL_ID_PRIVATE = os.getenv('CHANNEL_ID_PRIVATE')
    
    # API Keys
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
    REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')

    # Instagram Configuration
    INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
    INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
    
    # Market Data Configuration
    INDICES = {
        '^GSPC': 'S&P 500',
        '^NDX': 'NASDAQ-100'
    }
    
    # Schedule Configuration
    MACRO_ANALYSIS_DAY = 18  # Day of month for macro analysis
    TECHNICAL_ANALYSIS_DAY = 6  # Sunday (0 = Monday, 6 = Sunday)
    MOTIVATION_POST_TIMES = ["09:00", "15:00", "19:00"]  # Times for motivation posts