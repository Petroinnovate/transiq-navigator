"""
Auth Integration Test Suite — Production Readiness Check
Tests the dual auth layer (API Key + JWT Bearer) end-to-end.
"""
import sys
import time
import requests
import subprocess
import signal
import os

# ── Configuration ──────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:8001"
API_KEY = None  # Will be loaded from settings

results = []

def record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((name, passed, detail))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


# ── Pre-flight (no server needed) ─────────────────────────────────────────────

def run_preflight():
    print("=" * 60)
    print("SECTION 0: Pre-flight Checks (no server)")
    print("=" * 60)

    # 1. Settings
    from core.config.settings import settings
    api_key = settings.API_KEY
    record("API_KEY loaded from .env", bool(api_key), f"len={len(api_key) if api_key else 0}")
    global API_KEY
    API_KEY = api_key

    # 2. JWT secret not hardcoded
    from core.security.jwt import SECRET_KEY
    not_hardcoded = SECRET_KEY != "your-secret-key-change-in-production"
    record("JWT SECRET_KEY not hardcoded", not_hardcoded, SECRET_KEY[:20] + "...")

    # 3. JWT round-trip
    from core.security.jwt import create_access_token, decode_access_token
    token = create_access_token(data={"sub": "test-user-42"})
    decoded = decode_access_token(token)
    record("JWT create+decode round-trip", decoded == "test-user-42", f"decoded={decoded}")

    # 4. JWT expired token
    from datetime import timedelta
    expired_token = create_access_token(data={"sub": "x"}, expires_delta=timedelta(seconds=-10))
    expired_result = decode_access_token(expired_token)
    record("Expired JWT returns None", expired_result is None, f"result={expired_result}")

    # 5. JWT garbage token
    garbage_result = decode_access_token("not.a.real.token")
    record("Garbage JWT returns None", garbage_result is None, f"result={garbage_result}")

    # 6. Middleware imports
    from app.middleware.auth import APIKeyMiddleware, get_valid_api_keys, Role, check_permission
    valid_keys = get_valid_api_keys()
    record("Middleware loads + has valid keys", len(valid_keys) > 0, f"keys={len(valid_keys)}")

    # 7. RBAC matrix
    record("RBAC: OPERATOR can read dashboard", check_permission("/api/v2/dashboard", Role.OPERATOR))
    record("RBAC: OPERATOR blocked from financial", not check_permission("/api/v2/financial", Role.OPERATOR))
    record("RBAC: MANAGER can access financial", check_permission("/api/v2/financial", Role.MANAGER))
    record("RBAC: ENGINEER can upload", check_permission("/api/v2/upload", Role.ENGINEER))
    record("RBAC: OPERATOR blocked from upload", not check_permission("/api/v2/upload", Role.OPERATOR))

    # 8. require_role supports JWT users
    import inspect
    from app.middleware.auth import require_role
    src = inspect.getsource(require_role)
    record("require_role checks user_id (JWT)", "user_id" in src)

    # 9. Rate limiter
    from app.middleware.auth import rate_limiter
    record("Rate limiter configured", rate_limiter.max_requests > 0, f"{rate_limiter.max_requests}/min")

    # 10. App loads with routes
    from app.main import app
    routes = [r.path for r in app.routes if hasattr(r, "path")]
    record("App loads with routes", len(routes) >= 80, f"{len(routes)} routes")

    print()


# ── HTTP Tests (server must be running) ───────────────────────────────────────

def run_http_tests():
    print("=" * 60)
    print("SECTION 1: Health + Public Endpoints")
    print("=" * 60)

    # Test 1: Health check (no auth required)
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        record("GET /health returns 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        record("GET /health returns 200", False, str(e))
        return  # Server not running, abort HTTP tests

    # Test 2: Root endpoint (no auth required)
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        record("GET / returns 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        record("GET / returns 200", False, str(e))

    # Test 3: Docs endpoint (no auth required)
    try:
        r = requests.get(f"{BASE_URL}/docs", timeout=5)
        record("GET /docs returns 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        record("GET /docs returns 200", False, str(e))

    print()
    print("=" * 60)
    print("SECTION 2: API Key Authentication")
    print("=" * 60)

    # Test 4: Protected endpoint WITHOUT auth → 401
    try:
        r = requests.get(f"{BASE_URL}/api/v2/health", timeout=5)
        record("No auth → 401", r.status_code == 401, f"status={r.status_code}, body={r.text[:100]}")
    except Exception as e:
        record("No auth → 401", False, str(e))

    # Test 5: Protected endpoint WITH invalid API key → 401
    try:
        r = requests.get(f"{BASE_URL}/api/v2/health", headers={"X-API-Key": "wrong-key"}, timeout=5)
        record("Invalid API key → 401", r.status_code == 401, f"status={r.status_code}")
    except Exception as e:
        record("Invalid API key → 401", False, str(e))

    # Test 6: Protected endpoint WITH valid API key → auth passes (200 or 503 = auth worked)
    try:
        r = requests.get(f"{BASE_URL}/api/v2/health", headers={"X-API-Key": API_KEY}, timeout=30)
        # 200 = healthy, 503 = degraded (Redis/Qdrant down) — both mean auth passed
        auth_passed = r.status_code in (200, 503)
        record("Valid API key → auth passes", auth_passed, f"status={r.status_code}")
    except Exception as e:
        record("Valid API key → auth passes", False, str(e))

    # Test 7: lowercase x-api-key header also works
    try:
        r = requests.get(f"{BASE_URL}/api/v2/health", headers={"x-api-key": API_KEY}, timeout=30)
        auth_passed = r.status_code in (200, 503)
        record("Lowercase x-api-key → auth passes", auth_passed, f"status={r.status_code}")
        record("Lowercase x-api-key → auth passes", auth_passed, f"status={r.status_code}")
    except Exception as e:
        record("Lowercase x-api-key → auth passes", False, str(e))

    print()
    print("=" * 60)
    print("SECTION 3: JWT Bearer Authentication")
    print("=" * 60)

    # Test 8: Register a test user
    test_email = f"test_{int(time.time())}@example.com"
    test_password = "TestPass123!"
    try:
        r = requests.post(f"{BASE_URL}/auth/register", json={
            "email": test_email,
            "password": test_password,
        }, timeout=10)
        if r.status_code == 201:
            data = r.json()
            jwt_token = data.get("access_token")
            user_id = data.get("user_id")
            record("POST /auth/register → 201", True, f"user_id={user_id}, has_token={bool(jwt_token)}")
        elif r.status_code == 400 and "already registered" in r.text:
            record("POST /auth/register → email exists", True, "expected for re-run")
            jwt_token = None
        else:
            record("POST /auth/register → 201", False, f"status={r.status_code}, body={r.text[:100]}")
            jwt_token = None
    except Exception as e:
        record("POST /auth/register → 201", False, str(e))
        jwt_token = None

    # Test 9: Login with the test user
    try:
        r = requests.post(f"{BASE_URL}/auth/login", json={
            "email": test_email,
            "password": test_password,
        }, timeout=10)
        if r.status_code == 200:
            data = r.json()
            jwt_token = data.get("access_token")
            record("POST /auth/login → 200", True, f"has_token={bool(jwt_token)}, has_user_id={bool(data.get('user_id'))}")
        else:
            record("POST /auth/login → 200", False, f"status={r.status_code}, body={r.text[:100]}")
    except Exception as e:
        record("POST /auth/login → 200", False, str(e))

    # Test 10: Access protected endpoint with JWT Bearer token
    if jwt_token:
        try:
            r = requests.get(f"{BASE_URL}/api/v2/health",
                             headers={"Authorization": f"Bearer {jwt_token}"}, timeout=30)
            auth_passed = r.status_code in (200, 503)
            record("Bearer JWT → auth passes on /api/v2/health", auth_passed, f"status={r.status_code}")
        except Exception as e:
            record("Bearer JWT → auth passes on /api/v2/health", False, str(e))

        # Test 11: JWT user blocked from MANAGER endpoint (RBAC)
        try:
            r = requests.get(f"{BASE_URL}/api/v2/financial",
                             headers={"Authorization": f"Bearer {jwt_token}"}, timeout=5)
            # ENGINEER should be blocked from /api/v2/financial (requires MANAGER)
            record("JWT ENGINEER blocked from /financial → 403", r.status_code == 403,
                   f"status={r.status_code}")
        except Exception as e:
            record("JWT OPERATOR blocked from /financial → 403", False, str(e))

        # Test 12: Invalid Bearer token → 401
        try:
            r = requests.get(f"{BASE_URL}/api/v2/health",
                             headers={"Authorization": "Bearer invalid.token.here"}, timeout=5)
            record("Invalid Bearer → 401", r.status_code == 401, f"status={r.status_code}")
        except Exception as e:
            record("Invalid Bearer → 401", False, str(e))
    else:
        record("Bearer JWT → 200 (skipped, no token)", False, "login failed")
        record("JWT RBAC block (skipped)", False, "login failed")
        record("Invalid Bearer → 401 (skipped)", False, "login failed")

    print()
    print("=" * 60)
    print("SECTION 4: Auth Endpoint Format Validation")
    print("=" * 60)

    # Test 13: /auth/login returns correct Token model shape
    try:
        r = requests.post(f"{BASE_URL}/auth/login", json={
            "email": test_email,
            "password": test_password,
        }, timeout=10)
        if r.status_code == 200:
            data = r.json()
            has_all = all(k in data for k in ["access_token", "token_type", "user_id", "email"])
            record("Token response has all fields", has_all, f"keys={list(data.keys())}")
            record("token_type is 'bearer'", data.get("token_type") == "bearer", f"got={data.get('token_type')}")
            record("email matches", data.get("email") == test_email, f"got={data.get('email')}")
        else:
            record("Token response shape", False, f"status={r.status_code}")
            record("token_type", False, "skipped")
            record("email matches", False, "skipped")
    except Exception as e:
        record("Token response shape", False, str(e))

    # Test 14: /auth/login with wrong password → 401
    try:
        r = requests.post(f"{BASE_URL}/auth/login", json={
            "email": test_email,
            "password": "wrong-password",
        }, timeout=10)
        record("Wrong password → 401", r.status_code == 401, f"status={r.status_code}")
    except Exception as e:
        record("Wrong password → 401", False, str(e))

    # Test 15: /auth/login with FormData (old frontend bug) → 422
    try:
        r = requests.post(f"{BASE_URL}/auth/login",
                          data={"email": test_email, "password": test_password},
                          timeout=10)
        record("FormData (not JSON) → 422", r.status_code == 422, f"status={r.status_code}")
    except Exception as e:
        record("FormData → 422", False, str(e))

    # Test 16: /auth/register with short password → 422
    try:
        r = requests.post(f"{BASE_URL}/auth/register", json={
            "email": "short@test.com",
            "password": "abc",
        }, timeout=10)
        record("Short password → 422", r.status_code == 422, f"status={r.status_code}")
    except Exception as e:
        record("Short password → 422", False, str(e))

    print()
    print("=" * 60)
    print("SECTION 5: Rate Limiter")
    print("=" * 60)

    # Test 17: Rate limiter fires after exceeding limit
    from core.config.settings import settings as s
    from app.middleware.auth import RateLimiter
    rl = RateLimiter(max_requests=3, window_seconds=60)
    test_key = "rate-test-key"
    rl.is_allowed(test_key)  # 1
    rl.is_allowed(test_key)  # 2
    rl.is_allowed(test_key)  # 3
    blocked = not rl.is_allowed(test_key)  # 4 — should be blocked
    record("Rate limiter blocks after max", blocked, f"max=3, 4th call blocked={blocked}")

    # Test 18: Rate limiter allows different keys independently
    rl2 = RateLimiter(max_requests=2, window_seconds=60)
    rl2.is_allowed("key-a")  # 1
    rl2.is_allowed("key-a")  # 2
    blocked_a = not rl2.is_allowed("key-a")  # 3 — blocked
    allowed_b = rl2.is_allowed("key-b")  # 1 for key-b — allowed
    record("Rate limiter isolates keys", blocked_a and allowed_b,
           f"key-a blocked={blocked_a}, key-b allowed={allowed_b}")


# ── Summary ─────────────────────────────────────────────────────────────────

def print_summary():
    print()
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    total = len(results)
    print(f"Total: {passed}/{total} passed, {failed} failed")
    print()
    if failed > 0:
        print("FAILURES:")
        for name, p, detail in results:
            if not p:
                print(f"  [FAIL] {name} — {detail}")
    print()
    print("VERDICT:", "PASS" if failed == 0 else f"PARTIAL ({failed} issues)")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_preflight()
    run_http_tests()
    print_summary()
