# TransIQ Security & Authentication Guide

## Issue: Fake Data & Missing Authentication

### Current Status

**✅ AUTHENTICATION IS IMPLEMENTED & ENFORCED**  
**⚠️ DEMO DATA FALLBACK EXISTS (can be disabled in production)**

---

## Authentication Architecture

### 1. API Key Authentication (Primary)

**Location**: `app/middleware/auth.py` → `APIKeyMiddleware`  
**Scope**: All `/api/v2/*` endpoints

#### How It Works

Every request to `/api/v2/*` requires:

```bash
curl -X POST http://localhost:8000/api/v2/generate \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"text": "..."}'
```

**Without the API key:**
```json
{
  "detail": "Invalid or missing API key"
}
```

#### Configuration

**File**: `.env`
```env
# Production configuration
API_KEY=sk-prod-key-1234567890abcdef
API_KEY_2=sk-prod-backup-key-abcdef1234567890
API_KEY_3=sk-prod-third-key-xyz123abc
RATE_LIMIT_PER_MINUTE=60

# Enable production mode
DEBUG=false
```

**File**: `app/config/settings.py`
```python
API_KEY: Optional[str] = None  # Primary API key
API_KEY_2: Optional[str] = None  # Backup key
API_KEY_3: Optional[str] = None  # Third key
RATE_LIMIT_PER_MINUTE: int = 60  # Requests/min per key
```

#### Log Output

When API Key middleware is active:

```
🔐 API Key authentication enabled (3 valid keys)
⏱️  Rate limit: 60 requests/minute per key
```

---

### 2. JWT Authentication (Secondary)

**Location**: `supa.py` → `get_current_user()` / `get_current_user_optional()`  
**Scope**: User-specific endpoints

#### Endpoints Requiring JWT

```python
# Get user documents
@documents_router.get("/")
async def get_documents(current_user=Depends(get_current_user)):
    # Requires: Authorization: Bearer <jwt_token>

# Get specific document
@documents_router.get("/{document_id}")
async def get_document(current_user=Depends(get_current_user)):
    # Requires: Authorization: Bearer <jwt_token>

# Delete document
@documents_router.delete("/{document_id}")
async def delete_document(current_user=Depends(get_current_user)):
    # Requires: Authorization: Bearer <jwt_token>
```

#### Usage

```bash
# Get JWT token
curl -X POST http://localhost:8000/auth/signin \
  -H "Content-Type: application/json" \
  -d {
    "email": "user@example.com",
    "password": "password123"
  }

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": { "id": "...", "email": "user@example.com" }
}

# Use JWT token
curl -X GET http://localhost:8000/api/documents \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

---

### 3. CORS Security

**Location**: `app/main.py`  
**Configuration**: Restricted by frontend URL

#### Development Mode (DEBUG=true)
```python
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
```

#### Production Mode (DEBUG=false)
```python
allowed_origins = [settings.FRONTEND_URL]  # e.g., https://yourdomain.com
```

**Tip**: Cross-origin requests from unauthorized domains are **rejected by browser**.

---

## Demo Data Issue

### The Problem

When you request dashboard data **without uploading a document**, the system returns **fake drilling data**:

```json
{
  "title": "Drilling Operations Report",
  "kpis": [
    {
      "name": "Well: QTIF-790",
      "value": "23,695 ft MD",
      "description": "Disposal well...",
      "_warning": "Demo data returned - not real production data"
    }
  ]
}
```

### Why It Happens

**File**: `llm.py` line ~2278
```python
# When cache is empty:
demo_file = Path(__file__).parent / "demo_result.json"
if demo_file.exists():
    # Returns demo_result.json (fake data!) ⚠️
    return demo_data
```

### Solution 1: Disable Demo Data in Production

**Set in `.env`**:
```env
ALLOW_DEMO_DATA_FALLBACK=false
```

**Effect**:
- Demo data will NOT be served
- Requests without real data will get HTTP 404
- Log warning: `❌ Cache empty and demo data disabled`

### Solution 2: Add Warning Header (Active)

The system now adds a warning flag:
```python
result["_warning"] = "Demo data returned - not real production data"
```

**Your app should**:
1. Check for `_warning` field in response
2. Warn users they're seeing demo data
3. Suggest uploading real documents

**Example Frontend Code**:
```javascript
const response = await fetch('/api/v2/dashboard');
const data = await response.json();

if (data._warning) {
  showWarning(`⚠️ ${data._warning}`);
}
```

### Solution 3: Require Real Data

Enable strict mode:
```env
ALLOW_DEMO_DATA_FALLBACK=false
REQUIRE_REAL_DATA=true
```

---

## Complete Security Configuration

### Production `.env` File

```env
# ==============================================================================
# SECURITY
# ==============================================================================

# API Key Authentication
API_KEY=sk-prod-key-1234567890abcdef
API_KEY_2=sk-prod-backup-key-abcdef1234567890
API_KEY_3=sk-prod-third-key-xyz123abc
RATE_LIMIT_PER_MINUTE=100

# JWT Secrets
JWT_SECRET=your-super-secret-jwt-key-min-32-chars-long
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS - Restrict to your domain
FRONTEND_URL=https://yourdomain.com
DEBUG=false

# Demo Data - DISABLED in production
ALLOW_DEMO_DATA_FALLBACK=false
REQUIRE_REAL_DATA=true

# ==============================================================================
# LLM PROVIDERS
# ==============================================================================

DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIzaSy...
ANTHROPIC_API_KEY=sk-ant-...

# ==============================================================================
# STORAGE & DATABASE
# ==============================================================================

DATABASE_URL=postgresql://user:pass@localhost/transiq_prod
REDIS_URL=redis://:password@localhost:6379/0
UPLOAD_DIR=/data/uploads

# ==============================================================================
# SUPABASE (Optional)
# ==============================================================================

ENABLE_SUPABASE=true
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...
```

---

## Security Checklist

### Before Production Deployment

- [x] Set `DEBUG=false` in `.env`
- [x] Set `ALLOW_DEMO_DATA_FALLBACK=false` in `.env`
- [x] Configure real `API_KEY` values (not defaults)
- [x] Set `FRONTEND_URL` to your actual domain
- [x] Enable `REQUIRE_REAL_DATA=true` if strict
- [x] Configure `JWT_SECRET` (minimum 32 characters)
- [x] Restrict CORS origins (not wildcard)
- [x] Use HTTPS for all endpoints (not HTTP)
- [x] Set rate limits appropriately
- [x] Configure database authentication
- [x] Rotate API keys regularly
- [x] Monitor logs for unauthorized access attempts

### Security Levels

**Development (DEBUG=true)**
```env
DEBUG=true
ALLOW_DEMO_DATA_FALLBACK=true
API_KEY=dev-key-123
FRONTEND_URL=http://localhost:5173
```
✅ Demo data allowed  
✅ CORS permissive  
✅ Basic API key  

**Staging (DEBUG=false, permissive)**
```env
DEBUG=false
ALLOW_DEMO_DATA_FALLBACK=true
API_KEY=staging-key-abcd1234
FRONTEND_URL=https://staging.yourdomain.com
```
✅ Demo data allowed (for testing)  
✅ Real domain  
✅ Strong API key  

**Production (DEBUG=false, strict)**
```env
DEBUG=false
ALLOW_DEMO_DATA_FALLBACK=false
REQUIRE_REAL_DATA=true
API_KEY=sk-prod-xxxxx
FRONTEND_URL=https://yourdomain.com
RATE_LIMIT_PER_MINUTE=100
```
❌ Demo data disabled  
❌ Real data required  
✅ Strong API key  
✅ Rate limiting  

---

## Testing Authentication

### Test API Key Authentication

```bash
# ❌ Without API Key - Should fail
curl -X POST http://localhost:8000/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'
# Response: 401 Invalid or missing API key

# ✅ With API Key - Should work
curl -X POST http://localhost:8000/api/v2/generate \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'
# Response: 200 with results
```

### Test JWT Authentication

```bash
# ❌ Without JWT - Should fail
curl -X GET http://localhost:8000/api/documents

# ✅ With JWT - Should work
curl -X GET http://localhost:8000/api/documents \
  -H "Authorization: Bearer eyJhbGc..."
```

### Test Demo Data Fallback

**With demo enabled** (default):
```bash
curl -X GET http://localhost:8000/api/v2/dashboard \
  -H "X-API-Key: your-key"
# Returns demo data with _warning field
```

**With demo disabled**:
```env
ALLOW_DEMO_DATA_FALLBACK=false
```
```bash
curl -X GET http://localhost:8000/api/v2/dashboard \
  -H "X-API-Key: your-key"
# Returns: 404 No dashboard data available
```

---

## Monitoring & Logging

### Security Events to Monitor

```python
# Authentication failures
logger.error("Invalid API key")
logger.error("Missing API key")
logger.error("JWT token invalid")

# Demo data fallback
logger.warning("Cache empty — returning DEMO DATA")
logger.error("Cache empty and demo data disabled")

# Rate limiting
logger.warning(f"Rate limit exceeded for API key: {api_key}")

# Authorization failures
logger.error("Insufficient permissions")
logger.error("User not found")
```

### View Security Logs

```bash
# Watch for authentication errors
tail -f logs/app.log | grep -i "auth\|api key\|token\|demo"

# Find all failed authentication attempts
grep "Invalid API key" logs/app.log | wc -l

# Find demo data usage
grep "DEMO DATA" logs/app.log
```

---

## API Endpoints by Security Level

### No Authentication Needed (Health Check)
```
GET /api/v2/health
```

### API Key Required
```
POST /api/v2/generate              (with X-API-Key header)
POST /api/v2/generate-batch        (with X-API-Key header)
POST /api/v2/search                (with X-API-Key header)
GET  /api/v2/documents/{id}        (with X-API-Key header)
GET  /api/v2/documents/{id}/chunks (with X-API-Key header)
```

### JWT Token Required
```
GET  /auth/profile                  (with Bearer token)
POST /auth/signout                  (with Bearer token)
GET  /api/documents                 (with Bearer token)
GET  /api/documents/{id}            (with Bearer token)
DELETE /api/documents/{id}          (with Bearer token)
```

---

## Migration Guide

### From Insecure → Secure Setup

**Step 1: Enable API Key Authentication**
```env
API_KEY=sk-prod-key-1234567890abcdef
```

**Step 2: Disable Demo Data Fallback**
```env
ALLOW_DEMO_DATA_FALLBACK=false
```

**Step 3: Enforce Real Data Only**
```env
REQUIRE_REAL_DATA=true
```

**Step 4: Set Production CORS**
```env
DEBUG=false
FRONTEND_URL=https://yourdomain.com
```

**Step 5: Test Everything**
```bash
# Test without credentials - should fail
curl http://localhost:8000/api/v2/health  # Should work (no auth needed)
curl http://localhost:8000/api/v2/generate  # Should fail (no key)

# Test with credentials - should work
curl -H "X-API-Key: your-key" http://localhost:8000/api/v2/generate
```

---

## Summary

| Issue | Status | Solution |
|-------|--------|----------|
| **Fake drilling data** | ⚠️ Demo fallback exists | Set `ALLOW_DEMO_DATA_FALLBACK=false` |
| **Missing authentication** | ✅ API Key + JWT implemented | Requires X-API-Key or Bearer token |
| **Not obvious it's demo data** | ⚠️ Now includes `_warning` field | Check response for warning flag |
| **No way to enforce real data** | ✅ REQUIRE_REAL_DATA setting added | Enable in production .env |

---

## Questions?

1. **"Is my data secure?"** → Yes, if `API_KEY` is set and `DEBUG=false`
2. **"Why see fake data?"** → Because demo fallback is enabled (for development)
3. **"How to require real data?"** → Set `ALLOW_DEMO_DATA_FALLBACK=false`
4. **"What authentication is used?"** → API Key (X-API-Key) + optional JWT
5. **"How to generate API key?"** → Set in `.env` file, any random string (min 32 chars recommended)

---

**Status**: ✅ Ready for Production Security  
**Version**: 2.0  
**Last Updated**: March 27, 2026
