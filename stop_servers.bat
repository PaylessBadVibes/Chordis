@echo off
echo ===============================================
echo CHORDIS AI - Stopping Services
echo ===============================================
echo.

echo Stopping ChordMiniApp...
taskkill /FI "WINDOWTITLE eq ChordMiniApp*" /F 2>nul
if %errorlevel%==0 (
    echo   [OK] ChordMiniApp stopped
) else (
    echo   [--] ChordMiniApp was not running
)

echo Stopping Chordis API...
taskkill /FI "WINDOWTITLE eq Chordis API*" /F 2>nul
if %errorlevel%==0 (
    echo   [OK] Chordis API stopped
) else (
    echo   [--] Chordis API was not running
)

echo.
echo ===============================================
echo All services stopped.
echo ===============================================
pause

