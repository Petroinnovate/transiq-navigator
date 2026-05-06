@echo off
REM ============================================================================
REM TransIQ QUICK START GUIDE
REM Complete instructions for running the full stack
REM ============================================================================

setlocal enabledelayedexpansion

:menu
cls
echo.
echo ============================================================================
echo  TransIQ QUICK START MENU
echo ============================================================================
echo.
echo Choose an option:
echo.
echo  1. Check Environment Setup
echo  2. Start Complete Stack (Backend + Frontend)
echo  3. Start Backend Only (Port 8001)
echo  4. Start Frontend Only (Port 5173)
echo  5. View Configuration
echo  6. Exit
echo.
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto check_setup
if "%choice%"=="2" goto start_full
if "%choice%"=="3" goto start_backend
if "%choice%"=="4" goto start_frontend
if "%choice%"=="5" goto view_config
if "%choice%"=="6" goto end
goto menu

:check_setup
cls
call CHECK_SETUP.bat
goto menu

:start_full
cls
echo.
echo Starting complete stack...
call START_FULL_STACK.bat
goto menu

:start_backend
cls
set BACKEND_PATH=C:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master
echo.
echo Starting Backend (FastAPI)...
echo Path: %BACKEND_PATH%
echo Port: 8001
echo.
if exist "%BACKEND_PATH%" (
    start "TransIQ Backend" cmd /k "cd /d "%BACKEND_PATH%" && python -m uvicorn main:app --host localhost --port 8001 --reload"
    echo ✅ Backend is starting on http://localhost:8001
    echo    Check the backend terminal for startup messages
    echo.
) else (
    echo ❌ Backend folder not found!
    echo    Expected path: %BACKEND_PATH%
    echo.
)
timeout /t 3 /nobreak
goto menu

:start_frontend
cls
set FRONTEND_PATH=C:\github-copiolot\1 A TransIQ\TransIQ-frontend-main\TransIQ-frontend-main
echo.
echo Starting Frontend (React + Vite)...
echo Path: %FRONTEND_PATH%
echo Port: 5173
echo.
if exist "%FRONTEND_PATH%" (
    start "TransIQ Frontend" cmd /k "cd /d "%FRONTEND_PATH%" && bun run dev"
    echo ✅ Frontend is starting on http://localhost:5173
    echo    Check the frontend terminal for startup messages
    echo.
) else (
    echo ❌ Frontend folder not found!
    echo    Expected path: %FRONTEND_PATH%
    echo.
)
timeout /t 3 /nobreak
goto menu

:view_config
cls
echo.
echo ============================================================================
echo  CURRENT CONFIGURATION
echo ============================================================================
echo.
echo Backend Configuration:
echo  ✓ Path: C:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master
echo  ✓ URL: http://localhost:8001
echo  ✓ Framework: FastAPI (Python)
echo  ✓ Services: Gemini API, Vector DB, Document Chunking
echo.
echo Frontend Configuration:
echo  ✓ Path: C:\github-copiolot\1 A TransIQ\TransIQ-frontend-main\TransIQ-frontend-main
echo  ✓ URL: http://localhost:5173
echo  ✓ Framework: React with Vite
echo  ✓ Package Manager: Bun (or npm)
echo.
echo Environment Variables (.env):
type .env
echo.
echo API Endpoints:
echo  ✓ POST /api/v2/generate - Upload and process file
echo  ✓ GET /api/v2/dashboard/latest - Get latest dashboard
echo  ✓ GET /api/v2/dashboard/{reportId} - Get specific dashboard
echo  ✓ GET /api/v2/search - Search documents
echo  ✓ WS /api/v2/ws/{task_id} - Real-time progress updates
echo.
echo ============================================================================
echo.
pause
goto menu

:end
cls
echo.
echo Goodbye!
echo.
exit /b 0
