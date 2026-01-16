"""
Test script for macro analyzer date filtering feature.
This script runs only the macro analysis and prints results to console.
"""
import asyncio
import logging
import sys
import os

# Add src directory to path (parent directory of tests)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from macro_analyzer import MacroAnalyzer
from characters_and_prompts import dani_financial_description, dani_perplexity_prompt

# Set up logging to see filtering statistics - use DEBUG to see all details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Also set the macro_analyzer logger to INFO to see the report
logging.getLogger('macro_analyzer').setLevel(logging.INFO)

async def test_macro_analysis():
    """Test macro analysis with date filtering."""
    logger.info("Starting macro analysis test...")
    
    # Initialize analyzer
    macro_analyzer = MacroAnalyzer()
    
    # Run analysis
    logger.info("Fetching macro analysis from Claude with web search...")
    macro_response = await macro_analyzer.get_macro_analysis(
        dani_financial_description,
        dani_perplexity_prompt
    )
    
    if macro_response:
        logger.info("=" * 80)
        logger.info("RAW MACRO ANALYSIS RESULT (before Hebrew formatting):")
        logger.info("=" * 80)
        print(macro_response)
        logger.info("=" * 80)
        
        # Format Hebrew text
        logger.info("Formatting Hebrew text...")
        formatted_report = macro_analyzer.fix_hebrew_text(
            macro_response,
            dani_financial_description
        )
        
        if formatted_report:
            logger.info("=" * 80)
            logger.info("FORMATTED MACRO ANALYSIS RESULT:")
            logger.info("=" * 80)
            print(formatted_report)
            logger.info("=" * 80)
            logger.info("Test completed successfully!")
        else:
            logger.error("Failed to format Hebrew text")
    else:
        logger.error("Failed to get macro analysis")

if __name__ == "__main__":
    try:
        asyncio.run(test_macro_analysis())
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
