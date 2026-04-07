@echo off
REM ============================================
REM TransIQ Multi-Tenant Migration Setup Script
REM ============================================

echo.
echo ============================================
echo TransIQ Multi-Tenant Migration Setup
echo ============================================
echo.

REM Check if virtual environment exists
if not exist ".venv\" (
    echo ❌ Virtual environment not found!
    echo Please create it first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    exit /b 1
)

echo Step 1: Activating virtual environment...
call .venv\Scripts\activate

echo.
echo Step 2: Installing new dependencies...
pip install sqlalchemy==2.0.25 alembic==1.13.1 python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4

if %errorlevel% neq 0 (
    echo ❌ Failed to install dependencies
    exit /b 1
)

echo.
echo ✅ Dependencies installed successfully!
echo.

echo Step 3: Setting up .env file...
if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo ⚠️  IMPORTANT: Edit .env and set:
    echo    - API_KEY ^(generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"^)
    echo    - GEMINI_API_KEY ^(your Gemini API key^)
    echo    - DATABASE_URL ^(optional - defaults to SQLite^)
    echo.
    echo Press any key to continue after editing .env...
    pause >nul
)

echo.
echo Step 4: Testing imports...
python -c "from app.db import init_db; from app.auth import get_current_user; from app.db.models import User; print('✅ All imports successful')"

if %errorlevel% neq 0 (
    echo ❌ Import test failed!
    echo Check the error above and fix any issues.
    exit /b 1
)

echo.
echo Step 5: Initializing database...
python -c "from app.db import init_db; init_db(); print('✅ Database initialized')"

if %errorlevel% neq 0 (
    echo ❌ Database initialization failed!
    exit /b 1
)

echo.
echo ============================================
echo ✅ Setup Complete!
echo ============================================
echo.
echo Next steps:
echo.
echo 1. Start the backend:
echo    python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
echo.
echo 2. Register a user:
echo    curl -X POST http://localhost:8001/auth/register \
echo      -H "Content-Type: application/json" \
echo      -d "{\"email\": \"admin@test.com\", \"password\": \"testpass123\"}"
echo.
echo 3. Test authentication:
echo    ^(Use the access_token from step 2^)
echo    curl http://localhost:8001/auth/me \
echo      -H "Authorization: Bearer YOUR_TOKEN"
echo.
echo 4. Upload a document:
echo    curl -X POST http://localhost:8001/api/v2/generate \
echo      -H "X-API-Key: your-api-key" \
echo      -H "Authorization: Bearer YOUR_TOKEN" \
echo      -F "file=@test.txt"
echo.
echo See DATABASE_MIGRATION.md for complete guide.
echo.
pause
