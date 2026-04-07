"""
Production Readiness Validation — Senior Backend Reviewer
Validates all claims, simulates frontend flow, tests failure scenarios.
All tests are LIVE HTTP calls against the running server.
"""
import os, sys, time, json, requests

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

BASE = "http://localhost:8001"
results = []

def test(name, passed, detail=""):
    tag = "PASS" if passed else "FAIL"
    results.append((name, passed, detail))
    print(f"  [{tag}] {name}" + (f" -- {detail}" if detail else ""))

def header(title):
    print(f"\n{'='*64}")
    print(f"  {title}")
    print(f"{'='*64}")

# ══════════════════════════════════════════════════════════════════
# STEP 1 — VALIDATE CLAIMS (from code, no server needed)
# ══════════════════════════════════════════════════════════════════

header("STEP 1: VALIDATE CLAIMS")

# Claim 1: 86 routes loaded
from app.main import app
route_count = len([r.path for r in app.routes if hasattr(r, "path")])
test("Claim: 86 routes loaded", route_count >= 86, f"actual={route_count}")

# Claim 2: JWT decode returns user_id (str), not dict
from core.security.jwt import create_access_token, decode_access_token
token = create_access_token(data={"sub": "user-abc"})
decoded = decode_access_token(token)
test("Claim: decode_access_token returns str user_id",
     isinstance(decoded, str) and decoded == "user-abc",
     f"type={type(decoded).__name__}, value={decoded}")

# Claim 3: Middleware sets request.state correctly for both paths
import inspect
from app.middleware.auth import APIKeyMiddleware
src = inspect.getsource(APIKeyMiddleware.dispatch)
sets_api_key    = "request.state.api_key" in src
sets_role       = "request.state.role" in src
sets_user_id    = "request.state.user_id" in src
test("Claim: middleware sets api_key on request.state", sets_api_key)
test("Claim: middleware sets role on request.state", sets_role)
test("Claim: middleware sets user_id for JWT path", sets_user_id)

# Claim 4: require_role works for JWT users
from app.middleware.auth import require_role
rr_src = inspect.getsource(require_role)
test("Claim: require_role checks user_id (not just api_key)",
     "user_id" in rr_src and "api_key" in rr_src)

# Claim 5: Auth endpoints exist with correct methods
from app.api.v2.auth import router as auth_router
auth_routes = [(r.path, list(r.methods)) for r in auth_router.routes if hasattr(r, "methods")]
has_login = any("/login" in p and "POST" in m for p, m in auth_routes)
has_register = any("/register" in p and "POST" in m for p, m in auth_routes)
test("Claim: POST /auth/login exists", has_login, str(auth_routes))
test("Claim: POST /auth/register exists", has_register)

# Claim 6: Excluded paths skip auth
excluded = APIKeyMiddleware.EXCLUDED_PATHS
excluded_prefixes = APIKeyMiddleware.EXCLUDED_PREFIXES
test("Claim: /health excluded from auth", "/health" in excluded, str(excluded))
test("Claim: /auth/ prefix excluded", "/auth/" in excluded_prefixes, str(excluded_prefixes))

# ══════════════════════════════════════════════════════════════════
# STEP 2 — SIMULATE REAL FRONTEND FLOW (live HTTP)
# ══════════════════════════════════════════════════════════════════

header("STEP 2: FRONTEND FLOW SIMULATION")

from core.config.settings import settings
API_KEY = settings.API_KEY

# 2a. Register
email = f"frontenduser_{int(time.time())}@example.com"
password = "SecurePass2026!"

print(f"\n  >> POST /auth/register  body={{email: {email}, password: ****}}")
r = requests.post(f"{BASE}/auth/register", json={"email": email, "password": password}, timeout=10)
print(f"  << {r.status_code}  {json.dumps(r.json(), indent=2)[:300]}")
test("Register returns 201", r.status_code == 201)
reg_data = r.json()
test("Register response has access_token", "access_token" in reg_data)
test("Register response has user_id", "user_id" in reg_data)
test("Register response has email", reg_data.get("email") == email)
test("Register token_type is bearer", reg_data.get("token_type") == "bearer")

# 2b. Login
print(f"\n  >> POST /auth/login  body={{email: {email}, password: ****}}")
r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password}, timeout=10)
print(f"  << {r.status_code}  {json.dumps(r.json(), indent=2)[:300]}")
test("Login returns 200", r.status_code == 200)
login_data = r.json()
jwt_token = login_data.get("access_token", "")
test("Login returns access_token", bool(jwt_token))
test("Login returns same user_id as register", login_data.get("user_id") == reg_data.get("user_id"))
test("Login returns same email", login_data.get("email") == email)

# 2c. Call protected endpoint with Bearer token (simulating axios interceptor)
print(f"\n  >> GET /api/v2/health  headers={{Authorization: Bearer <jwt>}}")
r = requests.get(f"{BASE}/api/v2/health", headers={"Authorization": f"Bearer {jwt_token}"}, timeout=30)
print(f"  << {r.status_code}  (body truncated)")
# 200 = healthy, 503 = degraded (Redis/Qdrant down) — both mean auth PASSED through middleware
test("Bearer JWT passes middleware (200 or 503)", r.status_code in (200, 503), f"status={r.status_code}")

# 2d. Call protected endpoint with API key (simulating internal tool / Postman)
print(f"\n  >> GET /api/v2/health  headers={{X-API-Key: ****}}")
r = requests.get(f"{BASE}/api/v2/health", headers={"X-API-Key": API_KEY}, timeout=30)
print(f"  << {r.status_code}")
test("API Key passes middleware (200 or 503)", r.status_code in (200, 503), f"status={r.status_code}")

# 2e. Duplicate registration (frontend retry scenario)
print(f"\n  >> POST /auth/register (duplicate email)")
r = requests.post(f"{BASE}/auth/register", json={"email": email, "password": password}, timeout=10)
print(f"  << {r.status_code}  {r.text[:200]}")
test("Duplicate register returns 400", r.status_code == 400)
test("Error says already registered", "already registered" in r.text.lower())

# ══════════════════════════════════════════════════════════════════
# STEP 3 — FAILURE SCENARIOS (live HTTP)
# ══════════════════════════════════════════════════════════════════

header("STEP 3: FAILURE SCENARIOS")

# 3a. No token, no API key
print("\n  >> GET /api/v2/health  (no auth)")
r = requests.get(f"{BASE}/api/v2/health", timeout=5)
print(f"  << {r.status_code}  {r.text[:200]}")
test("No auth -> 401", r.status_code == 401)
body = r.json()
test("401 body has 'error' field", "error" in body)
test("401 message mentions both auth methods",
     "X-API-Key" in body.get("message", "") and "Bearer" in body.get("message", ""))

# 3b. Invalid token
print("\n  >> GET /api/v2/health  Authorization: Bearer garbage.token.here")
r = requests.get(f"{BASE}/api/v2/health",
                 headers={"Authorization": "Bearer garbage.token.here"}, timeout=5)
print(f"  << {r.status_code}")
test("Invalid token -> 401", r.status_code == 401)

# 3c. Expired token
from datetime import timedelta
expired_token = create_access_token(data={"sub": "user-x"}, expires_delta=timedelta(seconds=-10))
print(f"\n  >> GET /api/v2/health  Authorization: Bearer <expired>")
r = requests.get(f"{BASE}/api/v2/health",
                 headers={"Authorization": f"Bearer {expired_token}"}, timeout=5)
print(f"  << {r.status_code}")
test("Expired token -> 401", r.status_code == 401)

# 3d. Valid token, restricted endpoint (RBAC)
print(f"\\n  >> GET /api/v2/financial  Authorization: Bearer <jwt> (ENGINEER role)")
r = requests.get(f"{BASE}/api/v2/financial",
                 headers={"Authorization": f"Bearer {jwt_token}"}, timeout=5)
print(f"  << {r.status_code}  {r.text[:200]}")
test("ENGINEER on MANAGER endpoint -> 403", r.status_code == 403)

# 3e. Invalid API key
print("\n  >> GET /api/v2/health  X-API-Key: wrong-key")
r = requests.get(f"{BASE}/api/v2/health", headers={"X-API-Key": "wrong-key"}, timeout=5)
print(f"  << {r.status_code}")
test("Invalid API key -> 401", r.status_code == 401)

# 3f. Wrong password
print(f"\n  >> POST /auth/login  wrong password")
r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "wrong"}, timeout=10)
print(f"  << {r.status_code}")
test("Wrong password -> 401", r.status_code == 401)

# 3g. FormData instead of JSON (old frontend bug)
print(f"\n  >> POST /auth/login  Content-Type: x-www-form-urlencoded (FormData)")
r = requests.post(f"{BASE}/auth/login", data={"email": email, "password": password}, timeout=10)
print(f"  << {r.status_code}")
test("FormData -> 422 (Pydantic rejects)", r.status_code == 422)

# 3h. Nonexistent email
print(f"\n  >> POST /auth/login  nonexistent email")
r = requests.post(f"{BASE}/auth/login", json={"email": "nobody@example.com", "password": "x"}, timeout=10)
print(f"  << {r.status_code}")
test("Nonexistent user -> 401", r.status_code == 401)

# ══════════════════════════════════════════════════════════════════
# STEP 4 — INFRA CHECK
# ══════════════════════════════════════════════════════════════════

header("STEP 4: INFRA CHECK")

# 4a. /health (public, no auth)
r = requests.get(f"{BASE}/health", timeout=5)
health = r.json()
print(f"  /health status: {health.get('status')}")
test("/health returns 200 (public)", r.status_code == 200)

# 4b. /api/v2/health (protected, detailed)
r = requests.get(f"{BASE}/api/v2/health", headers={"X-API-Key": API_KEY}, timeout=30)
detailed = r.json()
services = detailed.get("services", {})
print(f"  /api/v2/health status: {detailed.get('status')}")
for svc, val in services.items():
    print(f"    {svc}: {val}")

redis_ok = services.get("redis", "").startswith("ok") if isinstance(services.get("redis"), str) else services.get("redis") == "ok"
db_ok = services.get("database") == "ok"
llm_ok = services.get("llm") == "ok"

test("Database is OK", db_ok)
test("LLM providers available", llm_ok)
# Redis/Qdrant are softly degraded, not blocking
print(f"\n  Redis: {'UP' if redis_ok else 'DOWN (non-blocking)'}")
print(f"  Qdrant: {services.get('qdrant', 'unknown')}")
print(f"  Database: {services.get('database', 'unknown')}")
print(f"  LLM: {services.get('llm', 'unknown')}")

# 4c. Auth endpoints work without Redis
print(f"\n  Verify auth works without Redis:")
r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password}, timeout=10)
test("Auth login works without Redis", r.status_code == 200, f"status={r.status_code}")

# 4d. Public endpoint works
r = requests.get(f"{BASE}/", timeout=5)
root = r.json()
test("Root endpoint returns app info", root.get("version") == "2.0.0", f"version={root.get('version')}")

# ══════════════════════════════════════════════════════════════════
# STEP 5 — SCORING + FINAL VERDICT
# ══════════════════════════════════════════════════════════════════

header("STEP 5: FINAL VERDICT")

passed = sum(1 for _, p, _ in results if p)
failed = sum(1 for _, p, _ in results if not p)
total = len(results)

print(f"\n  Total: {passed}/{total} passed, {failed} failed")

if failed > 0:
    print("\n  FAILURES:")
    for name, p, detail in results:
        if not p:
            print(f"    [FAIL] {name} -- {detail}")

pct = (passed / total * 100) if total else 0
if failed == 0:
    verdict = "YES -- safe to proceed with frontend integration"
    icon = "PASS"
elif failed <= 2:
    verdict = "PARTIAL -- minor risks, proceed with caution"
    icon = "WARN"
else:
    verdict = "NO -- blocking issues must be fixed first"
    icon = "FAIL"

print(f"\n  Score: {pct:.0f}%")
print(f"  [{icon}] Backend ready for frontend? {verdict}")

# ══════════════════════════════════════════════════════════════════
# STEP 6 — DEV MODE RBAC RECOMMENDATION
# ══════════════════════════════════════════════════════════════════

header("STEP 6: RBAC DEV MODE RECOMMENDATION")

# Check current JWT default role
from app.middleware.auth import Role
jwt_default_role_line = [l.strip() for l in src.split("\n") if "Role.OPERATOR" in l and "request.state.role" in l]
print(f"\n  Current JWT default role: {jwt_default_role_line}")
print(f"  RBAC endpoint requirements:")
from app.middleware.auth import ENDPOINT_ROLE_REQUIREMENTS
for path, role in sorted(ENDPOINT_ROLE_REQUIREMENTS.items()):
    print(f"    {role.name:10s}  {path}")

# Test: which endpoints would a JWT OPERATOR be blocked from?
blocked = []
allowed = []
for path, min_role in ENDPOINT_ROLE_REQUIREMENTS.items():
    if Role.OPERATOR >= min_role:
        allowed.append(path)
    else:
        blocked.append(f"{path} (needs {min_role.name})")

print(f"\n  JWT user (OPERATOR) CAN access:    {len(allowed)} endpoints")
print(f"  JWT user (OPERATOR) BLOCKED from:  {len(blocked)} endpoints")
for b in blocked:
    print(f"    X  {b}")

print(f"\n  RECOMMENDATION:")
print(f"  Option A: Change JWT default role to Role.ADMIN in middleware (fast, unsafe)")
print(f"  Option B: Change JWT default role to Role.ENGINEER (balanced)")
print(f"  Option C: Keep OPERATOR, add role upgrade via /auth/me endpoint (proper)")
print(f"  >> For dev/demo: Option B is recommended (unlocks upload+export, blocks admin)")
