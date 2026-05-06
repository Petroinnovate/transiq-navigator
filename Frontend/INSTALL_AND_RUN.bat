@echo off
REM ============================================================================
REM TransIQ COMPLETE SETUP & RUN SCRIPT
REM Installs dependencies and runs the complete stack
REM ============================================================================

setlocal enabledelayedexpansion

cls
echo.
echo ============================================================================
echo  TransIQ COMPLETE SETUP & LAUNCHER
echo ============================================================================
echo.

REM Define paths
for %%I in ("%~dp0.") do set "FRONTEND_PATH=%%~fI"
for %%I in ("%~dp0..") do set "ROOT_PATH=%%~fI"
set "BACKEND_PATH=%ROOT_PATH%\Backend"

REM Check paths exist
if not exist "%BACKEND_PATH%" (
    echo ERROR: Backend folder not found!
    echo Expected: %BACKEND_PATH%
    pause
    exit /b 1
)

if not exist "%FRONTEND_PATH%" (
    echo ERROR: Frontend folder not found!
    echo Expected: %FRONTEND_PATH%
    pause
    exit /b 1
)

echo ✓ Project folders found
echo.

REM ============================================================================
REM STEP 1: Check and install Python dependencies
REM ============================================================================
echo ============================================================================
echo STEP 1: Backend Dependencies
echo ============================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python is not installed or not in PATH
    echo    Please install Python 3.8+ from https://www.python.org/
    echo.
    pause
    exit /b 1
)

echo ✅ Python is installed
echo.
echo Checking if requirements.txt exists in backend...

if exist "%BACKEND_PATH%\requirements.txt" (
    echo ✓ Found requirements.txt
    echo.
    echo Installing Python dependencies...
    echo Command: pip install -r requirements.txt
    echo.
    cd /d "%BACKEND_PATH%"
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ⚠️  Warning: Some dependencies may have failed to install
        echo    This might be ok if core packages installed successfully
    ) else (
        echo ✅ Backend dependencies installed successfully
    )
) else (
    echo ⚠️  requirements.txt not found in backend folder
    echo    Skipping dependency installation
    echo    The backend may fail if dependencies are missing
)

echo.
echo.

REM ============================================================================
REM STEP 2: Check and install Node/Bun dependencies
REM ============================================================================
echo ============================================================================
echo STEP 2: Frontend Dependencies
echo ============================================================================
echo.

bun --version >nul 2>&1
set HAS_BUN=0
if errorlevel 0 set HAS_BUN=1

npm --version >nul 2>&1
set HAS_NPM=0
if errorlevel 0 set HAS_NPM=1

if %HAS_BUN%==1 (
    echo ✅ Bun is installed
    echo.
    echo Installing frontend dependencies with Bun...
    echo Command: bun install
    echo.
    cd /d "%FRONTEND_PATH%"
    bun install
    if errorlevel 1 (
        echo ❌ Bun install failed
        echo    Trying with npm...
        npm install
    ) else (
        echo ✅ Frontend dependencies installed with Bun
    )
) else if %HAS_NPM%==1 (
    echo ✅ npm is installed
    echo.
    echo Installing frontend dependencies with npm...
    echo Command: npm install
    echo.
    cd /d "%FRONTEND_PATH%"
    npm install
    if errorlevel 1 (
        echo ❌ npm install failed
        pause
        exit /b 1
    ) else (
        echo ✅ Frontend dependencies installed successfully
    )
) else (
    echo ❌ ERROR: Neither Bun nor npm is installed!
    echo    Install one of:
    echo    - Node.js (includes npm): https://nodejs.org/
    echo    - Bun: https://bun.sh/
    echo.
    pause
    exit /b 1
)

echo.
echo.

REM ============================================================================
REM STEP 3: Launch services
REM ============================================================================
echo ============================================================================
echo STEP 3: Starting Services
echo ============================================================================
echo.

echo [1/2] Starting Backend (FastAPI)...
echo        Path: %BACKEND_PATH%
echo        Port: 8001
echo        Command: python -m uvicorn main:app --host localhost --port 8001 --reload
echo.
cd /d "%BACKEND_PATH%"
start "TransIQ Backend (Port 8001)" cmd /k "python -m uvicorn main:app --host localhost --port 8001 --reload"

timeout /t 5 /nobreak

echo [2/2] Starting Frontend (React + Vite)...
echo        Path: %FRONTEND_PATH%
echo        Port: 5173
if %HAS_BUN%==1 (
    echo        Command: bun run dev
    cd /d "%FRONTEND_PATH%"
    start "TransIQ Frontend (Port 5173)" cmd /k "bun run dev"
) else (
    echo        Command: npm run dev
    cd /d "%FRONTEND_PATH%"
    start "TransIQ Frontend (Port 5173)" cmd /k "npm run dev"
)

echo.
echo.

REM ============================================================================
REM FINAL STATUS
REM ============================================================================
echo ============================================================================
echo  ✅ SETUP COMPLETE - STACK LAUNCHING
echo ============================================================================
echo.
echo 🌐 ACCESS POINTS:
echo    Frontend:    http://localhost:5173
echo    Backend API: http://localhost:8001
echo    API Docs:    http://localhost:8001/docs
echo.
echo 📊 SERVICES STARTING:
echo    ✓ FastAPI Backend with Gemini integration
echo    ✓ Vector Database (Chroma/Pinecone)
echo    ✓ Document Chunking Service
echo    ✓ React Frontend with Vite
echo.
echo ⏳ INITIALIZATION TIME:
echo    Please wait 15-30 seconds for all services to fully initialize
echo.
echo 🎯 NEXT STEPS:
echo    1. Wait for "Uvicorn running on..." in backend terminal
echo    2. Wait for "VITE v..." message in frontend terminal
echo    3. Open browser to: http://localhost:5173
echo    4. Click "Upload" to start using TransIQ
echo.
echo 🛑 TO STOP:
echo    Close both command windows (Backend and Frontend terminals)
echo.
echo 📚 DOCUMENTATION:
echo    - QUICK_REFERENCE.md - Quick start guide
echo    - TESTING_GUIDE.md - Testing instructions
echo    - FRONTEND_V2_UPGRADE_GUIDE.md - Technical details
echo.
echo ============================================================================
echo.

pause
