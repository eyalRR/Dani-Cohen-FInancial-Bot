#!/usr/bin/env python3
"""
Test script to verify that all dependencies are properly installed
"""

import sys
import importlib

def test_import(module_name, package_name=None):
    """Test if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"OK: {package_name or module_name}")
        return True
    except ImportError as e:
        print(f"FAILED: {package_name or module_name} - {e}")
        return False

def main():
    print("Testing Financial Bot Environment Dependencies...")
    print("=" * 50)
    
    # List of required modules
    dependencies = [
        ("anthropic", "Anthropic AI"),
        ("openai", "OpenAI"),
        ("yfinance", "Yahoo Finance"),
        ("telegram", "Python Telegram Bot"),
        ("numpy", "NumPy"),
        ("pandas", "Pandas"),
        ("matplotlib", "Matplotlib"),
        ("scipy", "SciPy"),
        ("mplfinance", "MPL Finance"),
        ("PIL", "Pillow (PIL)"),
        ("requests", "Requests"),
        ("dotenv", "Python Dotenv"),
        ("replicate", "Replicate"),
        ("instabot", "InstagramBot")
    ]
    
    success_count = 0
    total_count = len(dependencies)
    
    for module, name in dependencies:
        if test_import(module, name):
            success_count += 1
    
    print("=" * 50)
    print(f"Results: {success_count}/{total_count} dependencies successfully imported")
    
    if success_count == total_count:
        print("SUCCESS: Environment setup is COMPLETE! You can now run the financial bot.")
        print("\nTo run the main bot:")
        print("  cd financial_bot")
        print("  python main.py")
        print("\nTo run standalone scripts:")
        print("  python 3_telegram.py")
        print("  python 4_telegram_claude.py") 
        print("  python 5_telegram_claude_perplexity.py")
    else:
        print("WARNING: Some dependencies are missing. Please check the installation.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())