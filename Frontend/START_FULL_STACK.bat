@echo off
REM ============================================================================
REM TransIQ COMPLETE STACK LAUNCHER
REM Starts: Backend (FastAPI) + Vector DB + Frontend (Vite)
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo  TransIQ COMPLETE STACK LAUNCHER
echo ============================================================================
echo.

REM Define paths
for %%I in ("%~dp0.") do set "FRONTEND_PATH=%%~fI"
for %%I in ("%~dp0..") do set "ROOT_PATH=%%~fI"
set "BACKEND_PATH=%ROOT_PATH%\Backend"

REM Check if backend folder exists
if not exist "%BACKEND_PATH%" (
    echo ERROR: Backend folder not found at:
    echo %BACKEND_PATH%
    echo.
    pause
    exit /b 1
)

REM Check if frontend folder exists
if not exist "%FRONTEND_PATH%" (
    echo ERROR: Frontend folder not found at:
    echo %FRONTEND_PATH%
    echo.
    pause
    exit /b 1
)

echo [1/3] Starting Backend (FastAPI + Gemini + Vector DB)...
echo        Path: %BACKEND_PATH%
echo        Command: python -m uvicorn main:app --host localhost --port 8001 --reload
echo.
start "TransIQ Backend (Port 8001)" cmd /k "cd /d "%BACKEND_PATH%" && python -m uvicorn main:app --host localhost --port 8001 --reload"

timeout /t 3 /nobreak

echo [2/3] Starting Frontend (React + Vite)...
echo        Path: %FRONTEND_PATH%
echo        Command: bun run dev (or npm run dev)
echo.
start "TransIQ Frontend (Port 5173)" cmd /k "cd /d "%FRONTEND_PATH%" && bun run dev"

timeout /t 3 /nobreak

echo.
echo ============================================================================
echo  ✅ STACK LAUNCHING
echo ============================================================================
echo.
echo Backend:  http://localhost:8001
echo Frontend: http://localhost:5173
echo.
echo SERVICES STARTING:
echo  ✓ FastAPI Backend with Gemini integration
echo  ✓ Vector Database (Chroma/Pinecone)
echo  ✓ Document Chunking Service
echo  ✓ React Frontend with Vite
echo.
echo Please wait 15-30 seconds for services to fully initialize...
echo Once ready, open your browser to: http://localhost:5173
echo.
echo To stop all services: Close both command windows
echo.
echo ============================================================================
echo.

pause
