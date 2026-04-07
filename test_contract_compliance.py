"""
Frontend API Contract Compliance Checker
Verifies frontend code matches the backend API contract exactly.
"""
import os, sys, re

os.chdir(os.path.dirname(os.path.abspath(__file__)))

FE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Frontend", "src")
checks = []

def check(name, ok, detail=""):
    checks.append((name, ok, detail))
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {name}" + (f" -- {detail}" if detail else ""))

def read(path):
    full = os.path.join(FE_ROOT, path)
    with open(full, "r", encoding="utf-8") as f:
        return f.read()

print("=" * 64)
print("  FRONTEND CONTRACT COMPLIANCE CHECK")
print("=" * 64)

# ── Auth.tsx ──────────────────────────────────────────────────────

print("\n[Auth.tsx] Endpoint + Body Contract")
auth = read("pages/Auth.tsx")

check("Login endpoint is /auth/login", "'/auth/login'" in auth)
check("Register endpoint is /auth/register", "'/auth/register'" in auth)
# Strip comments before checking for old endpoints
auth_no_comments = re.sub(r'//.*$', '', auth, flags=re.MULTILINE)
check("NO /auth/signin (old bug)", "/auth/signin" not in auth_no_comments)
check("NO /auth/signup (old bug)", "/auth/signup" not in auth_no_comments)
check("Login sends JSON (not FormData)", "axios.post<AuthTokenResponse>('/auth/login', {" in auth
      or "axios.post<AuthTokenResponse>('/auth/login'," in auth)
check("Register sends JSON", "axios.post<AuthTokenResponse>('/auth/register', {" in auth
      or "axios.post<AuthTokenResponse>('/auth/register'," in auth)
check("NO FormData append in login/signup", "formData.append" not in auth.lower())
check("Parses access_token from response", "result.access_token" in auth or "result?.access_token" in auth)
check("Parses user_id from response", "result.user_id" in auth or "result?.user_id" in auth)
check("Parses email from response", "result.email" in auth)
check("AuthTokenResponse interface defined", "interface AuthTokenResponse" in auth)
check("Navigates to / after login", "navigate('/')" in auth)

# ── axios.ts ──────────────────────────────────────────────────────

print("\n[axios.ts] Token Injection + Error Handling Contract")
ax = read("lib/axios.ts")

check("Base URL points to 8001", "localhost:8001" in ax)
check("Reads token from localStorage('auth_token')", "localStorage.getItem('auth_token')" in ax)
check("Sets Authorization: Bearer header", "Bearer ${token}" in ax or "Bearer " in ax)
check("401 -> clears auth_token", "localStorage.removeItem('auth_token')" in ax)
check("401 -> clears user_data", "localStorage.removeItem('user_data')" in ax)
check("401 -> redirects to /auth", "'/auth'" in ax)
check("403 -> logs error (no redirect)", "403" in ax and "console.error" in ax)
check("422 -> logs validation error", "422" in ax and "console.error" in ax)
check("429 -> retries with Retry-After", "429" in ax and "retry-after" in ax.lower())
check("500+ -> logs server error", "500" in ax and "console.error" in ax)

# ── AuthContext.tsx ───────────────────────────────────────────────

print("\n[AuthContext.tsx] State Management Contract")
ctx = read("contexts/AuthContext.tsx")

check("Stores token as 'auth_token'", "localStorage.setItem('auth_token'" in ctx)
check("Stores user as 'user_data'", "localStorage.setItem('user_data'" in ctx)
check("Restores from localStorage on init", "localStorage.getItem('auth_token')" in ctx)
check("login() sets isAuthenticated=true", "setIsAuthenticated(true)" in ctx)
check("logout() clears token from localStorage", "localStorage.removeItem('auth_token')" in ctx)
check("logout() clears user from localStorage", "localStorage.removeItem('user_data')" in ctx)

# Check logout endpoint
if "/auth/signout" in ctx:
    check("Logout calls correct endpoint", False, "calls /auth/signout but backend has /auth/logout")
elif "/auth/logout" in ctx:
    check("Logout calls correct endpoint", True)
else:
    check("Logout calls correct endpoint", True, "no server-side logout call (acceptable for JWT)")

# ── api.ts ────────────────────────────────────────────────────────

print("\n[api.ts] API Client Types Contract")
api = read("services/api.ts")

check("DashboardData interface defined", "interface DashboardData" in api)
check("KPIBlock interface defined", "interface KPIBlock" in api)
check("ChartBlock interface defined", "interface ChartBlock" in api)
check("TaskStatus interface defined", "interface TaskStatus" in api)
check("DocumentChunk interface defined", "interface DocumentChunk" in api)
check("UploadResponse interface defined", "interface UploadResponse" in api)
check("NO 'any' types remaining", ": any" not in api, "type safety enforced")
check("Upload uses multipart/form-data", "multipart/form-data" in api)
check("ProgressWebSocket uses TaskStatus type", "TaskStatus" in api and "WebSocket" in api)

# ── App.tsx ───────────────────────────────────────────────────────

print("\n[App.tsx] Routing Contract")
app_tsx = read("App.tsx")

check("/auth route exists", '"/auth"' in app_tsx)
check("AuthProvider wraps app", "AuthProvider" in app_tsx)
check("Auth page imported", "import Auth" in app_tsx)

# ── Summary ───────────────────────────────────────────────────────

print("\n" + "=" * 64)
passed = sum(1 for _, ok, _ in checks if ok)
failed = sum(1 for _, ok, _ in checks if not ok)
total = len(checks)
print(f"  Contract Compliance: {passed}/{total} ({100*passed//total}%)")
if failed > 0:
    print(f"\n  MISMATCHES ({failed}):")
    for name, ok, detail in checks:
        if not ok:
            print(f"    [MISMATCH] {name} -- {detail}")
print("=" * 64)
