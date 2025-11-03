@echo off
echo ========================================
echo   Starting Python Music Analyzer Server
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check if Flask is installed
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Error: Flask is not installed!
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Starting Flask server...
echo Server will be available at: http://localhost:5000
echo Press Ctrl+C to stop
echo.

python api.py

pause

