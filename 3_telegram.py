import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from scipy.signal import find_peaks
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import TelegramError
import logging
from dotenv import load_dotenv
import os
import asyncio
from openai import OpenAI
import base64
from characters_and_prompts import *
import requests


# Set up logging with a higher level to reduce output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from the .env file
load_dotenv()

# Access the environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
CHANNEL_ID_PUBLIC = os.getenv('CHANNEL_ID_PUBLIC')
CHANNEL_ID_PRIVATE = os.getenv('CHANNEL_ID_PRIVATE')
API_KEY = os.getenv('OPENAI_API_KEY')


def fetch_data(ticker, period="1y"):
    """Fetch data for the given ticker."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    return yf.Ticker(ticker).history(start=start_date, end=end_date)

def find_significant_points(data, window=20, distance=10):
    """Find significant peaks and troughs in the data."""
    highs = data['High'].values
    lows = data['Low'].values
    
    peaks, _ = find_peaks(highs, distance=distance)
    troughs, _ = find_peaks(-lows, distance=distance)
    
    return peaks, troughs

def construct_channel(data, peaks, troughs):
    """Construct a channel from significant points."""
    x = np.arange(len(data))
    
    # Upper trendline
    upper_slope, upper_intercept = np.polyfit(peaks, data['High'].iloc[peaks], 1)
    
    # Lower trendline (parallel to upper)
    lower_intercept = np.min(data['Low'].iloc[troughs] - upper_slope * troughs)
    
    return (upper_slope, upper_intercept), (upper_slope, lower_intercept)

def identify_channels(data):
    """Identify long-term and short-term channels."""
    long_peaks, long_troughs = find_significant_points(data, window=30, distance=20)
    short_term_data = data.tail(66)
    short_peaks, short_troughs = find_significant_points(short_term_data, window=10, distance=5)
    
    long_term_channel = construct_channel(data, long_peaks, long_troughs)
    short_term_channel = construct_channel(short_term_data, short_peaks, short_troughs)
    
    return long_term_channel, short_term_channel

def plot_with_channels(data, ticker, long_term_channel, short_term_channel):
    """Create a candlestick chart with dynamic channels."""
    # Prepare channel plots
    x_long = np.arange(len(data))
    long_upper = long_term_channel[0][0] * x_long + long_term_channel[0][1]
    long_lower = long_term_channel[1][0] * x_long + long_term_channel[1][1]
    
    short_term_length = 66
    x_short = np.arange(short_term_length)
    short_upper = np.full(len(data), np.nan)
    short_lower = np.full(len(data), np.nan)
    short_upper[-short_term_length:] = short_term_channel[0][0] * x_short + short_term_channel[0][1]
    short_lower[-short_term_length:] = short_term_channel[1][0] * x_short + short_term_channel[1][1]
    
    # Create additional plots for channels
    apds = [
        mpf.make_addplot(long_upper, color='blue', linestyle='--', width=1),
        mpf.make_addplot(long_lower, color='blue', linestyle='--', width=1),
        mpf.make_addplot(short_upper, color='red', linestyle=':', width=1),
        mpf.make_addplot(short_lower, color='red', linestyle=':', width=1)
    ]
    
    # Plot candlestick chart with channels
    mpf.plot(data, type='candle', style='charles',
             title=f'{ticker} - Last Year Performance',
             ylabel='Price',
             addplot=apds,
             figsize=(12, 6),
             savefig=f'{ticker.replace("^", "")}_analysis.png')

async def send_image_to_telegram(image_path):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        logger.info(f"Attempting to send image: {image_path}")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        with open(image_path, 'rb') as image_file:
            message = await bot.send_photo(chat_id=CHANNEL_ID_PRIVATE, photo=image_file)
        
        logger.info(f"Image sent successfully! Message ID: {message.message_id}")
    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
    except TelegramError as e:
        logger.error(f"Telegram error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        
async def send_text_message(text):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        logger.info(f"Attempting to send text message: {text}")

        # שליחת הודעת טקסט לערוץ או למשתמש
        message = await bot.send_message(chat_id=CHANNEL_ID_PRIVATE, text=text)
        
        logger.info(f"Message sent successfully! Message ID: {message.message_id}")
    except TelegramError as e:
        logger.error(f"Telegram error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        
# OpenAI Functions
# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def chatGPT_vision(image_path, character_description, prompt, api_key):
    base64_image = encode_image(image_path)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": character_description
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1000
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def process_result(result):
    if result:
        text = result['choices'][0]['message']['content']
        print(text)
    else:
        text = "Failed to get a response"
        print(text)
    return text
        
async def analyze_with_chatgpt(image_path, api_key):
    result = chatGPT_vision(image_path, dani_financial_description, dani_financial_prompt, api_key)
    return process_result(result)
        
async def main():
    # Check if today is Sunday (where Monday is 0 and Sunday is 6)
    # if datetime.now().weekday() != 6:
    #     print("Today is not Sunday. Script will not run.")
    #     return
    
    indices = {
        '^GSPC': 'S&P 500',
        '^NDX': 'NASDAQ-100'
    }
    
    for symbol, name in indices.items():
        data = fetch_data(symbol)
        long_term_channel, short_term_channel = identify_channels(data)
        plot_with_channels(data, name, long_term_channel, short_term_channel)
        print(f"Chart for {name} has been saved.")
        
    image_path = r"S&P 500_analysis.png"
    await send_image_to_telegram(image_path)
    
    # OpenAI analyze
    print(f"Analyzing {name} chart with ChatGPT...")
    text_post = await analyze_with_chatgpt(image_path, API_KEY)
    await send_text_message(text_post)
    
    image_path = r"NASDAQ-100_analysis.png"
    await send_image_to_telegram(image_path)
    
    # OpenAI analyze
    print(f"Analyzing {name} chart with ChatGPT...")
    text_post = await analyze_with_chatgpt(image_path, API_KEY)
    await send_text_message(text_post)

if __name__ == "__main__":
    asyncio.run(main())
