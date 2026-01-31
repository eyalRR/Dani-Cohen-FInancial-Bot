# main.py

import asyncio
import logging
from datetime import datetime, timedelta
import os

curr_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(curr_dir + "\\run_history1.json"):
    os.remove(curr_dir + "\\run_history1.json")
if os.path.exists(curr_dir + "\\run_history1.log"):
    os.remove(curr_dir + "\\run_history1.log")
    
    
import sys
import subprocess
import random
from config import Settings
from history import History


# Set up logging
logging.basicConfig(
    filename='run_history1.log',  # Name of the log file
    filemode='a',   #File mode: 'a' for append (default), 'w' for overwrite
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
        
        
async def main():
    print("Starting main script...")
    
    curr_dir = os.path.dirname(os.path.abspath(__file__))
        
    # Initialize services
    history = History(curr_dir + "\\run_history1.json")
    start_time = datetime.now()
    
    #=================
    offset_back = 110
    skip_days=27    # Change for DEBUG - see run_history1.log for results
    #=================
    for i in range(offset_back, 0, -1):
        # return the date i days ago
        current_time = start_time - timedelta(days=i)
        
        if i < 109 and skip_days > 0:
            print(f"<~~~~~ skip {skip_days} days~~~~~>")
            logger.info(f"<~~~~~ skip {skip_days} days~~~~~>")
            skip_days -=1
            continue
            
        
        print(current_time)
        #logger.info(f"current_time: {current_time.strftime('%Y-%m-%d')} - weekday {current_time.weekday()}")

        # Monthly Macro Analysis (once every 18th of month or first run after until end of month)
        days_since_macro = history.get_timestamp_delta('macro_analysis', current_time).days
        already_run_this_month = history.is_timestamp_in_current_month('macro_analysis', current_time)
        #logger.info(f"already_run_this_month: {already_run_this_month}")
        
        #logger.info(f"days_since_macro: {days_since_macro}")
        if ((not already_run_this_month) and current_time.day >= Settings.MACRO_ANALYSIS_DAY):
            print("===> macro")
            logger.info(f"current_time: {current_time.strftime('%Y-%m-%d')} - {current_time.weekday()}")
            logger.info(f"         ===> macro @ 18.xx <<<<<<<<<")
            #await run_macro_analysis(macro_analyzer, telegram)
            history.update_timestamp('macro_analysis', current_time)
        
        # Weekly Technical Analysis (Sundays or if more than 7 days have passed)
        days_since_technical = history.get_timestamp_delta('technical_analysis', current_time).days
        #logger.info(f"days_since_technical: {days_since_technical}")
        if (days_since_technical > 1 and current_time.weekday() == Settings.TECHNICAL_ANALYSIS_DAY) or \
        (days_since_technical > 7):
            #await run_technical_analysis(market, chart_analyzer, telegram)
            print("===> technical")
            logger.info(f"current_time: {current_time.strftime('%Y-%m-%d')} - {current_time.weekday()}")
            logger.info(f"        ===> technical @ - 6 <<<<<<<<<")
            history.update_timestamp('technical_analysis', current_time)
        

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        raise