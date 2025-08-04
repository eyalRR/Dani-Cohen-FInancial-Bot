@echo off
echo Starting Financial Bot...
echo.

REM Activate the virtual environment
call financial_bot_env\Scripts\activate

REM Check if .env file exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please create a .env file with your API keys before running the bot.
    echo See README.md for the required format.
    pause
    exit /b 1
)

REM Change to financial_bot directory and run the main script
cd financial_bot
echo Running main.py...
python main.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Bot stopped with an error. Check the output above.
    pause
)