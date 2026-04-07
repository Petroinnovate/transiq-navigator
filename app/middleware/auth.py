"""
API Key Authentication Middleware with Role-Based Access Control (RBAC)

Roles (hierarchical):
  OPERATOR  — read-only rig/fleet dashboards
  ENGINEER  — + DDR upload, what-if scenarios, report export
  MANAGER   — + financial engine, multi-report trends, audit
  ADMIN     — full access including user/key management
"""
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, List, Optional
from enum import IntEnum
import time
from collections import defaultdict
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Role hierarchy (higher int = more privilege)
# ---------------------------------------------------------------------------

class Role(IntEnum):
    OPERATOR = 10
    ENGINEER = 20
    MANAGER  = 30
    ADMIN    = 40


# Map API key → role. Configure via env: API_KEY_ROLES='{"key1":"admin","key2":"engineer"}'
# Fallback: all configured keys get ADMIN if no role mapping exists.
_KEY_ROLE_MAP: Dict[str, Role] = {}


def _load_key_roles() -> Dict[str, Role]:
    """Load API-key → role mapping from environment."""
    import os, json
    raw = os.environ.get("API_KEY_ROLES", "")
    mapping: Dict[str, Role] = {}
    if raw:
        try:
            parsed = json.loads(raw)
            role_lookup = {r.name.lower(): r for r in Role}
            for key, role_name in parsed.items():
                role = role_lookup.get(str(role_name).lower())
                if role is not None:
                    mapping[key] = role
        except (json.JSONDecodeError, TypeError):
            logger.warning("Invalid API_KEY_ROLES env var — ignored")
    return mapping


_KEY_ROLE_MAP = _load_key_roles()


def get_role_for_key(api_key: str) -> Role:
    """Resolve role for an API key (default: ADMIN if no mapping)."""
    return _KEY_ROLE_MAP.get(api_key, Role.ADMIN)


# ---------------------------------------------------------------------------
# Endpoint → minimum role requirements
# ---------------------------------------------------------------------------

# Path prefix → minimum required role
ENDPOINT_ROLE_REQUIREMENTS: Dict[str, Role] = {
    # Read-only dashboards — OPERATOR
    "/api/v2/dashboard":        Role.OPERATOR,
    "/api/v2/kpis":             Role.OPERATOR,
    "/api/ddr/fleet":           Role.OPERATOR,
    "/api/ddr/rig":             Role.OPERATOR,
    # DDR upload, what-if, export — ENGINEER
    "/api/v2/upload":           Role.ENGINEER,
    "/api/v2/whatif":           Role.ENGINEER,
    "/api/v2/export":           Role.ENGINEER,
    "/api/ddr/upload":          Role.ENGINEER,
    # Financial, trends, audit — MANAGER
    "/api/v2/financial":        Role.MANAGER,
    "/api/ddr/audit":           Role.MANAGER,
    "/api/v2/trends":           Role.MANAGER,
    # Admin
    "/auth/":                   Role.ADMIN,
}


def check_permission(path: str, role: Role) -> bool:
    """Check if a role has permission to access a path."""
    required = Role.OPERATOR  # default: any authenticated user
    for prefix, min_role in ENDPOINT_ROLE_REQUIREMENTS.items():
        if path.startswith(prefix):
            required = max(required, min_role)
    return role >= required


# ---------------------------------------------------------------------------
# Rate limiter (unchanged)
# ---------------------------------------------------------------------------

class RateLimiter:
    """In-memory rate limiter per API key"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)  # api_key -> [timestamps]
    
    def is_allowed(self, api_key: str) -> bool:
        """Check if request is allowed under rate limit"""
        now = time.time()
        
        # Clean old timestamps
        self.requests[api_key] = [
            ts for ts in self.requests[api_key]
            if now - ts < self.window_seconds
        ]
        
        # Check limit
        if len(self.requests[api_key]) >= self.max_requests:
            return False
        
        # Add new timestamp
        self.requests[api_key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60
)


def get_valid_api_keys() -> List[str]:
    """Get list of valid API keys from settings"""
    keys = []
    if settings.API_KEY:
        keys.append(settings.API_KEY)
    if settings.API_KEY_2:
        keys.append(settings.API_KEY_2)
    if settings.API_KEY_3:
        keys.append(settings.API_KEY_3)
    return keys


# ---------------------------------------------------------------------------
# FastAPI dependency for route-level RBAC
# ---------------------------------------------------------------------------

def require_role(min_role: Role):
    """
    FastAPI dependency — enforce minimum role on a specific endpoint.

    Usage:
        @router.get("/admin/users", dependencies=[Depends(require_role(Role.ADMIN))])
        async def list_users(): ...
    """
    async def _check(request: Request):
        api_key = getattr(request.state, "api_key", None)
        if not api_key:
            raise HTTPException(status_code=401, detail="Authentication required")
        role = get_role_for_key(api_key)
        if role < min_role:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {min_role.name}, your role: {role.name}",
            )
        return role
    return _check


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce authentication + RBAC.

    Authentication priority:
      1. X-API-Key header  (existing API key flow)
      2. Authorization: Bearer <jwt>  (React frontend flow)

    Excludes /docs, /openapi.json, /health, /auth/* from authentication.
    Includes rate limiting and role-based access control.
    """
    
    EXCLUDED_PATHS = [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    
    EXCLUDED_PREFIXES = [
        "/auth/",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and validate API key + RBAC"""
        
        # Skip authentication for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Skip authentication for excluded prefixes
        for prefix in self.EXCLUDED_PREFIXES:
            if request.url.path.startswith(prefix):
                return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Check if API keys are configured
        valid_keys = get_valid_api_keys()
        
        # If no API keys configured, allow all (development mode)
        if not valid_keys:
            logger.warning("No API keys configured - authentication disabled (development mode)")
            request.state.api_key = None
            request.state.role = Role.ADMIN
            return await call_next(request)
        
        # ── Authentication: API Key OR Bearer JWT ──────────────────────────

        # 1. Try X-API-Key header (existing integrations)
        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")

        # 2. Fallback: try Bearer JWT (React frontend sends this via axios interceptor)
        if not api_key:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                jwt_token = auth_header[7:]
                try:
                    from core.security.jwt import decode_access_token
                    user_id = decode_access_token(jwt_token)
                    if not user_id:
                        raise ValueError("Invalid or expired JWT token")

                    logger.debug(f"JWT authenticated: user_id={user_id} path={request.url.path}")

                    # JWT users get OPERATOR role by default.
                    # Extend with per-user DB roles when needed.
                    request.state.api_key = None
                    request.state.user_id = user_id
                    request.state.role = Role.OPERATOR

                    # RBAC check for JWT users
                    if not check_permission(request.url.path, Role.OPERATOR):
                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "error": "Forbidden",
                                "message": "Your role (OPERATOR) does not have access to this endpoint.",
                            },
                        )

                    return await call_next(request)

                except Exception as e:
                    logger.warning(f"Invalid Bearer JWT from {request.client.host}: {e}")
                    # Fall through to 401 below

        # 3. No valid credential found
        if not api_key:
            logger.warning(f"Unauthorized: {request.client.host} — no X-API-Key or valid Bearer token")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Unauthorized",
                    "message": "Authentication required. Include either 'X-API-Key' header or 'Authorization: Bearer <token>'.",
                }
            )
        
        # Validate API key
        if api_key not in valid_keys:
            logger.warning(f"Unauthorized access attempt from {request.client.host} - Invalid API key: {api_key[:8]}...")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Unauthorized",
                    "message": "Invalid API key"
                }
            )
        
        # Rate limiting
        if not rate_limiter.is_allowed(api_key):
            logger.warning(f"Rate limit exceeded for API key: {api_key[:8]}... from {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate Limit Exceeded",
                    "message": f"Maximum {settings.RATE_LIMIT_PER_MINUTE} requests per minute exceeded. Please slow down."
                }
            )
        
        # Resolve role and check RBAC
        role = get_role_for_key(api_key)
        if not check_permission(request.url.path, role):
            logger.warning(
                f"Forbidden: {request.client.host} role={role.name} path={request.url.path}"
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Forbidden",
                    "message": f"Your role ({role.name}) does not have access to this endpoint.",
                }
            )
        
        # API key valid, role sufficient — proceed
        logger.debug(f"Authenticated: {request.client.host} key={api_key[:8]}... role={role.name}")
        
        # Add API key and role to request state for downstream use
        request.state.api_key = api_key
        request.state.role = role
        
        return await call_next(request)
