@echo off
echo Killing processes on ports 5173 and 8001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8001" ^| findstr "LISTENING"') do taskkill /F /PID %%a 2>nul
echo Done. Ports should be free now.
pause

