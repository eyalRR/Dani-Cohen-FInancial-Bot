# main.py
import asyncio
import logging
from datetime import datetime
import os
import sys
import subprocess
import random
from config import Settings
from market_analysis import MarketAnalysis
from chart_analyzer import ChartAnalyzer
from macro_analyzer import MacroAnalyzer
from telegram_bot import TelegramBot
from instagram_service import InstagramService
from characters_and_prompts import *
from history import History

# Set up logging
logging.basicConfig(
    filename='run_history.log',  # Name of the log file
    filemode='a',   #File mode: 'a' for append (default), 'w' for overwrite
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_requirements():
    """Update all packages from requirements.txt on the 1st of each month."""
    if datetime.now().day == 1:
        print("Updating libraries from requirements.txt...")
        try:
            req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
            subprocess.run(["pip", "install", "--upgrade", "-r", req_path], check=True)
            print("Libraries updated successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to update libraries: {e}")

async def run_macro_analysis(macro_analyzer, telegram):
    """Run monthly macro-economic analysis."""
    logger.info("Running monthly macro-economic analysis...")
    macro_response = await macro_analyzer.get_macro_analysis(
        dani_financial_description,
        dani_perplexity_prompt
    )
    if macro_response:
        formatted_report = macro_analyzer.fix_hebrew_text(
            macro_response,
            dani_financial_description
        )
        if formatted_report:
            await telegram.send_text(formatted_report)
            logger.info("Monthly macro analysis completed and sent")

async def run_technical_analysis(market, chart_analyzer, telegram):
    """Run technical analysis for all indices."""
    logger.info("Running technical analysis...")
    for symbol, name in Settings.INDICES.items():
        # Fetch and analyze data
        data = market.fetch_data(symbol)
        if data is None:
            logger.error(f"Failed to fetch data for {name}")
            continue

        # Identify channels
        long_term_channel, intermediate_channels = market.identify_channels(data)
        
        # Report channel detection status
        if long_term_channel is None and not intermediate_channels:
            print("No significant trends detected")
        else:
            if long_term_channel:
                print("Long-term channel detected")
            print(f"Number of intermediate channels detected: {len(intermediate_channels)}")

        # Create chart
        if not market.plot_with_channels(data, name, long_term_channel, intermediate_channels):
            logger.error(f"Failed to create chart for {name}")
            continue

        # Send chart and analysis
        image_path = f"{name}_analysis.png"
        await telegram.send_image(image_path)
        
        last_price = data['Close'].iloc[-1]
        
        analysis_text = chart_analyzer.analyze_chart(
            image_path,
            dani_financial_description,
            dani_financial_ultimate_prompt + f"\nAdded Knowledge:\nLast Price: {last_price:.2f}"
        )
        if analysis_text:
            await telegram.send_text(analysis_text)
            logger.info(f"Analysis for {name} completed and sent")

async def run_motivation_post(instagram):
    """Generate and post motivational content."""
    logger.info("Generating motivation post...")
    theme = random.choice(instagram_themes)
    success = await instagram.generate_and_post_motivation(theme)
    if success:
        logger.info("Successfully posted motivation content")
    else:
        logger.error("Failed to post motivation content")

async def main():
    print("Starting main script...")
    
    curr_dir = os.path.dirname(os.path.abspath(__file__))
        
    # Initialize services
    history = History(curr_dir + "\\run_history.json")
    market = MarketAnalysis()
    chart_analyzer = ChartAnalyzer()
    macro_analyzer = MacroAnalyzer()
    telegram = TelegramBot()
    # instagram = InstagramService()
    current_time = datetime.now()
    
    # Monthly Macro Analysis (once every 18th of month or first run after)
    days_since_macro = history.get_timestamp_delta('macro_analysis').days
    if (days_since_macro > 1 and current_time.day == Settings.MACRO_ANALYSIS_DAY) or \
       (days_since_macro > 30):
        await run_macro_analysis(macro_analyzer, telegram)
        history.update_timestamp('macro_analysis')
    
    # Weekly Technical Analysis (Sundays or if more than 7 days have passed)
    days_since_technical = history.get_timestamp_delta('technical_analysis').days
    if (days_since_technical > 1 and current_time.weekday() == Settings.TECHNICAL_ANALYSIS_DAY) or \
       (days_since_technical > 7):
        await run_technical_analysis(market, chart_analyzer, telegram)
        history.update_timestamp('technical_analysis')
        
    # # Special occasion
    # await run_technical_analysis(market, chart_analyzer, telegram)

    # # Daily Motivation Posts
    # current_time_str = current_time.strftime("%H:%M")
    # if current_time_str in Settings.MOTIVATION_POST_TIMES:
    #     await run_motivation_post(instagram)

if __name__ == "__main__":
    # Run updates every 1st of month
    update_requirements()
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        raise