@echo off
REM ============================================================================
REM TransIQ ENVIRONMENT SETUP VERIFICATION
REM Checks if Python, Node/Bun, and required dependencies are available
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo  TransIQ ENVIRONMENT SETUP VERIFICATION
echo ============================================================================
echo.

REM Check Python
echo [1/4] Checking Python Installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is NOT installed or not in PATH
    echo    Please install Python 3.8+ from https://www.python.org/
    echo.
) else (
    for /f "tokens=*" %%i in ('python --version') do echo ✅ %%i
)

REM Check Bun
echo.
echo [2/4] Checking Bun/Node Installation...
bun --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Bun is NOT installed. Checking for npm instead...
    npm --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Neither Bun nor npm is installed
        echo    Install Node.js from https://nodejs.org/ (includes npm)
        echo    Or install Bun from https://bun.sh/
        echo.
    ) else (
        for /f "tokens=*" %%i in ('npm --version') do echo ✅ npm %%i
    )
) else (
    for /f "tokens=*" %%i in ('bun --version') do echo ✅ bun %%i
)

REM Check if Backend folder exists
echo.
echo [3/4] Checking Backend Folder...
set BACKEND_PATH=C:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master
if exist "%BACKEND_PATH%" (
    echo ✅ Backend found at:
    echo    %BACKEND_PATH%
) else (
    echo ❌ Backend folder NOT found at:
    echo    %BACKEND_PATH%
)

REM Check if Frontend folder exists
echo.
echo [4/4] Checking Frontend Folder...
set FRONTEND_PATH=C:\github-copiolot\1 A TransIQ\TransIQ-frontend-main\TransIQ-frontend-main
if exist "%FRONTEND_PATH%" (
    echo ✅ Frontend found at:
    echo    %FRONTEND_PATH%
) else (
    echo ❌ Frontend folder NOT found at:
    echo    %FRONTEND_PATH%
)

echo.
echo ============================================================================
echo  RECOMMENDED NEXT STEPS
echo ============================================================================
echo.
echo 1. Install Backend Dependencies:
echo    cd "C:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master"
echo    pip install -r requirements.txt
echo.
echo 2. Set up Gemini API Key (if not already set):
echo    set GEMINI_API_KEY=your_api_key_here
echo.
echo 3. Install Frontend Dependencies:
echo    cd "C:\github-copiolot\1 A TransIQ\TransIQ-frontend-main\TransIQ-frontend-main"
echo    bun install  (or npm install)
echo.
echo 4. Run the complete stack:
echo    Double-click: START_FULL_STACK.bat
echo.
echo ============================================================================
echo.

pause
