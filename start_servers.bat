@echo off
echo ===============================================
echo CHORDIS AI - Starting Services
echo ===============================================
echo.

REM Check if ChordMiniApp exists
if not exist "%~dp0chordmini\python_backend\app.py" (
    echo [ERROR] ChordMiniApp not found!
    echo.
    echo Please clone ChordMiniApp first:
    echo   cd %~dp0
    echo   git clone https://github.com/ptnghia-j/ChordMiniApp.git chordmini
    echo.
    echo Then install dependencies:
    echo   cd chordmini\python_backend
    echo   pip install --no-cache-dir Cython numpy==1.22.4
    echo   pip install --no-cache-dir madmom
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo [1/2] Starting ChordMiniApp backend (port 5001)...
echo       ML-based chord detection with 301 chord types
start "ChordMiniApp - Port 5001" cmd /k "cd /d %~dp0chordmini\python_backend && python app.py"

echo Waiting for ChordMiniApp to initialize...
timeout /t 5 /nobreak > nul

echo [2/2] Starting Chordis API (port 5000)...
start "Chordis API - Port 5000" cmd /k "cd /d %~dp0 && python api.py"

echo.
echo ===============================================
echo Both servers are starting in separate windows!
echo ===============================================
echo.
echo Services:
echo   - ChordMiniApp: http://localhost:5001 (chord detection)
echo   - Chordis API:  http://localhost:5000 (main app)
echo   - Chordis Web:  http://localhost:5000 (open in browser)
echo.
echo To stop all servers, run: stop_servers.bat
echo ===============================================
pause

