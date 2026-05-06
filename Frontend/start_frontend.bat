@echo off
echo Starting Frontend Server...
cd /d "%~dp0"
echo Current directory: %CD%
echo Checking Node.js...
node --version
echo Checking npm...
npm --version
echo.
echo Starting Vite dev server...
echo This will open in a new window. Wait for "Local: http://localhost:5173"
echo.
call npm run dev
pause

