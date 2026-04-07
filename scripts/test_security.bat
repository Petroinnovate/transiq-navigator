@echo off
REM ===========================================
REM TransIQ Security Test Script
REM ===========================================
REM Tests API key authentication and rate limiting

echo.
echo ============================================
echo TransIQ Security Test
echo ============================================
echo.

REM Set your API key here (copy from .env)
set API_KEY=%1

if "%API_KEY%"=="" (
    echo ERROR: No API key provided
    echo Usage: test_security.bat YOUR_API_KEY
    echo Example: test_security.bat ZSOLc_hD6aI6yK2BhP7SAItq9_ihNY9pUEhMAiEZLgs
    exit /b 1
)

echo Testing security at: http://localhost:8001
echo Using API Key: %API_KEY:~0,10%... ^(truncated^)
echo.

echo ============================================
echo Test 1: Access WITHOUT API Key ^(Should FAIL^)
echo ============================================
curl -s http://localhost:8001/api/v2/health 2>nul
if %errorlevel% equ 0 (
    echo ✅ Request completed ^(check response for 401^)
) else (
    echo ⚠️  Curl failed - is backend running?
)
echo.
timeout /t 2 /nobreak >nul

echo ============================================
echo Test 2: Access WITH Valid API Key ^(Should SUCCEED^)
echo ============================================
curl -s -H "X-API-Key: %API_KEY%" http://localhost:8001/api/v2/health 2>nul
if %errorlevel% equ 0 (
    echo ✅ Request succeeded
) else (
    echo ❌ Request failed - check API key
)
echo.
timeout /t 2 /nobreak >nul

echo ============================================
echo Test 3: Access WITH Wrong API Key ^(Should FAIL^)
echo ============================================
curl -s -H "X-API-Key: wrong-key-12345" http://localhost:8001/api/v2/health 2>nul
if %errorlevel% equ 0 (
    echo ✅ Request completed ^(check response for 401^)
) else (
    echo ⚠️  Curl failed
)
echo.
timeout /t 2 /nobreak >nul

echo ============================================
echo Test 4: Rate Limiting ^(Send 65 requests^)
echo ============================================
echo This will take ~3 seconds...
echo Expected: First 60 succeed, then 429 Rate Limit errors
echo.

set /a count=0
set /a success=0
set /a failed=0

:loop
if %count% geq 65 goto :end_loop

set /a count=%count%+1

REM Send request silently
curl -s -H "X-API-Key: %API_KEY%" http://localhost:8001/api/v2/health -o nul 2>nul
if %errorlevel% equ 0 (
    set /a success=%success%+1
    echo Request %count%: ✅ Success
) else (
    set /a failed=%failed%+1
    echo Request %count%: ❌ Rate Limited ^(429^)
)

goto :loop

:end_loop

echo.
echo ============================================
echo Rate Limit Test Results
echo ============================================
echo Total Requests: %count%
echo Successful: %success%
echo Rate Limited: %failed%
echo.

if %failed% gtr 0 (
    echo ✅ Rate limiting is working correctly!
    echo    ^(~60 requests succeeded, rest were blocked^)
) else (
    echo ⚠️  All requests succeeded - rate limiting may not be working
    echo    ^(Check RATE_LIMIT_PER_MINUTE in .env^)
)

echo.
echo ============================================
echo Security Test Complete
echo ============================================
echo.
echo Next Steps:
echo 1. If Test 1 returned 401 Unauthorized → CORRECT ✅
echo 2. If Test 2 returned 200 OK → CORRECT ✅
echo 3. If Test 3 returned 401 Unauthorized → CORRECT ✅
echo 4. If Test 4 showed rate limiting → CORRECT ✅
echo.
echo If all tests pass, your API is secured! 🔒
echo.

pause
