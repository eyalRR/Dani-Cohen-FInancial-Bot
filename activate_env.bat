@echo off
echo Activating Financial Bot Environment...
call financial_bot_env\Scripts\activate
echo.
echo Environment activated! You can now run:
echo   cd financial_bot
echo   python main.py
echo.
echo Or run standalone scripts:
echo   python 3_telegram.py
echo   python 4_telegram_claude.py
echo   python 5_telegram_claude_perplexity.py
echo.
cmd /k