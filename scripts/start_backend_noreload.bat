@echo off
echo Starting TransIQ Backend Server (No Reload)...
cd /d "%~dp0"
echo Server will run on http://localhost:8001
echo Press CTRL+C to stop
if exist "..\.venv\Scripts\python.exe" (
	"..\.venv\Scripts\python.exe" -c "import uvicorn; from app.main import app; uvicorn.run(app, host='0.0.0.0', port=8001, reload=False)"
) else (
	python -c "import uvicorn; from app.main import app; uvicorn.run(app, host='0.0.0.0', port=8001, reload=False)"
)
pause
