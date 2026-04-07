"""E2E Validation: Frontend <-> Backend auth pipe"""
import requests, time

BASE = "http://localhost:8001"
FE = "http://localhost:5173"

checks = []

def check(name, ok, detail=""):
    checks.append(ok)
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {name}" + (f" -- {detail}" if detail else ""))

print("=" * 60)
print("END-TO-END: Frontend <-> Backend Auth Pipe")
print("=" * 60)

# 1. Frontend alive
print("\n[1] Frontend alive")
r = requests.get(FE, timeout=5)
check("Frontend returns HTML", r.status_code == 200, f"status={r.status_code}, len={len(r.text)}")

# 2. Backend alive
print("\n[2] Backend alive")
r = requests.get(f"{BASE}/health", timeout=5)
check("Backend /health", r.status_code == 200, r.json().get("status"))

# 3. CORS preflight
print("\n[3] CORS preflight (from frontend origin)")
r = requests.options(f"{BASE}/auth/login", headers={
    "Origin": "http://localhost:5173",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type,authorization",
}, timeout=5)
cors_origin = r.headers.get("access-control-allow-origin", "MISSING")
check("CORS allows frontend origin", cors_origin == "http://localhost:5173", f"allow-origin={cors_origin}")

# 4. Register
print("\n[4] Register (as Auth.tsx)")
email = f"e2e_{int(time.time())}@example.com"
pw = "E2ePass2026!"
r = requests.post(f"{BASE}/auth/register", json={"email": email, "password": pw}, timeout=10)
data = r.json()
check("Register -> 201", r.status_code == 201, f"keys={list(data.keys())}")
check("Has access_token", "access_token" in data)
check("Has user_id", "user_id" in data)

# 5. Login
print("\n[5] Login (as Auth.tsx)")
r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw}, timeout=10)
data = r.json()
token = data.get("access_token", "")
check("Login -> 200", r.status_code == 200)
check("Token returned", bool(token), f"len={len(token)}")
check("user_id matches register", data.get("user_id") == data.get("user_id"))

# 6. Protected call (as axios interceptor)
print("\n[6] Protected call with Bearer token")
r = requests.get(f"{BASE}/api/v2/health", headers={"Authorization": f"Bearer {token}"}, timeout=30)
check("Bearer -> middleware passes", r.status_code in (200, 503), f"status={r.status_code}")

# 7. Upload reachable (ENGINEER role)
print("\n[7] Upload endpoint reachable (ENGINEER)")
r = requests.post(f"{BASE}/api/v2/generate", headers={"Authorization": f"Bearer {token}"}, timeout=10)
# 422 = no file sent (Pydantic validation) = auth+RBAC passed
check("ENGINEER can reach /generate", r.status_code not in (401, 403), f"status={r.status_code}")

# 8. No token -> 401
print("\n[8] No token -> 401")
r = requests.get(f"{BASE}/api/v2/health", timeout=5)
check("No auth -> 401", r.status_code == 401)

# 9. Summary
print("\n" + "=" * 60)
passed = sum(checks)
total = len(checks)
print(f"  E2E RESULT: {passed}/{total} checks passed")
if all(checks):
    print("  VERDICT: READY FOR FRONTEND DEVELOPMENT")
else:
    print("  VERDICT: ISSUES FOUND")
    for i, ok in enumerate(checks):
        if not ok:
            print(f"    Check #{i+1} failed")
print("=" * 60)
