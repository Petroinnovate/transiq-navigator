# 🔐 Multi-Tenant Architecture - Quick Reference

## 🎯 One-Page Developer Cheat Sheet

---

## Authentication Flow

```
Frontend                Backend                Database
   │                      │                      │
   │──── POST /auth/register ──────>            │
   │      {email, password}   │                  │
   │                      │                      │
   │                      │────── INSERT user ───>
   │                      │       (bcrypt hash)  │
   │                      │                      │
   │<──── JWT token ──────│                      │
   │      {access_token}  │                      │
   │                      │                      │
   │──── POST /api/v2/generate ─────>           │
   │      + X-API-Key     │                      │
   │      + Bearer token  │                      │
   │                      │                      │
   │                      │── Validate API key   │
   │                      │── Decode JWT         │
   │                      │── Extract user_id    │
   │                      │                      │
   │                      │────── INSERT document ─>
   │                      │       WHERE user_id  │
   │                      │                      │
   │<──── {doc_id, task_id} ────────|            │
```

---

## Request Headers (Both Required)

```http
POST /api/v2/generate
X-API-Key: abc123...           ← Layer 1: General API access
Authorization: Bearer eyJhbG...  ← Layer 2: User identity
Content-Type: multipart/form-data

file=@document.txt
```

---

## Code Patterns

### 1. Protected Endpoint

```python
from fastapi import Depends
from app.auth import get_current_user
from app.db import get_db
from app.db.models import User
from app.storage.orm_storage import ORMStorage

@router.get("/documents")
def get_my_documents(
    current_user: User = Depends(get_current_user),  # ← JWT validation
    db: Session = Depends(get_db)
):
    storage = ORMStorage(db)
    docs = storage.get_user_documents(current_user.id)  # ← User isolation
    return docs
```

### 2. Document Access (Ownership Check)

```python
@router.get("/documents/{doc_id}")
def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    storage = ORMStorage(db)
    doc = storage.get_document(doc_id, current_user.id)  # ← Validates ownership
    
    if not doc:
        raise HTTPException(404, "Document not found")  # ← User doesn't own it
    
    return doc
```

### 3. Celery Task (User Context)

```python
from app.db import get_db_context
from app.storage.orm_storage import ORMStorage

@celery.task
def process_document(doc_id: str, user_id: str):  # ← Pass user_id
    with get_db_context() as db:
        storage = ORMStorage(db)
        
        # Validates user owns document
        doc = storage.get_document(doc_id, user_id)
        if not doc:
            raise ValueError(f"User {user_id} doesn't own doc {doc_id}")
        
        # Process document...
        dashboard = generate_dashboard(doc)
        storage.save_dashboard(doc_id, user_id, dashboard)  # ← User validation
```

### 4. Storage Layer (Auto User Validation)

```python
from app.storage.orm_storage import ORMStorage

storage = ORMStorage(db)

# All methods enforce user_id:
storage.get_document(doc_id, user_id)           # ← Checks ownership
storage.get_user_documents(user_id)             # ← Filters by user
storage.save_chunks(chunks, user_id)            # ← Validates doc ownership
storage.get_dashboard(doc_id, user_id)          # ← Checks ownership
```

---

## Database Schema (Core Tables)

```sql
users (id, email, hashed_password)
  └──> documents (id, user_id FK, filename, metadata)
         ├──> chunks (id, doc_id FK, chunk_text)
         ├──> graph_edges (id, doc_id FK, edge)
         └──> task_status (task_id PK, doc_id FK, user_id FK, status)

batches (id, user_id FK, total_files)
  └──> batch_documents (id, batch_id FK, doc_id FK)
```

---

## Testing Commands

```bash
# 1. Register User
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "pass123"}'

# Save: TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 2. Login (Get Token Again)
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "pass123"}'

# 3. Get User Info
curl http://localhost:8001/auth/me \
  -H "Authorization: Bearer $TOKEN"

# 4. Upload Document
curl -X POST http://localhost:8001/api/v2/generate \
  -H "X-API-Key: your-api-key" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.txt"

# 5. Get My Documents
curl http://localhost:8001/api/v2/documents \
  -H "X-API-Key: your-api-key" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Multi-Tenancy Test

```bash
# User A creates document
TOKEN_A=$(curl -X POST http://localhost:8001/auth/register \
  -d '{"email": "usera@test.com", "password": "pass"}' | jq -r '.access_token')

DOC_ID=$(curl -X POST http://localhost:8001/api/v2/generate \
  -H "X-API-Key: key" -H "Authorization: Bearer $TOKEN_A" \
  -F "file=@doc.txt" | jq -r '.doc_id')

# User B tries to access User A's document
TOKEN_B=$(curl -X POST http://localhost:8001/auth/register \
  -d '{"email": "userb@test.com", "password": "pass"}' | jq -r '.access_token')

curl http://localhost:8001/api/v2/documents/$DOC_ID \
  -H "X-API-Key: key" -H "Authorization: Bearer $TOKEN_B"

# Expected: 404 Not Found ✅
```

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Missing/invalid JWT token | Login again, check token |
| `404 Document not found` | User doesn't own document | This is correct (multi-tenancy) |
| `relation 'users' does not exist` | Database not initialized | Restart backend (auto-creates tables) |
| `JWT decode error` | Token expired | Login again (24h expiration) |
| `Missing X-API-Key` | Forgot API key header | Add X-API-Key header |

---

## Environment Variables (Critical)

```bash
# .env
API_KEY=your-api-key                           # Layer 1 auth
JWT_SECRET_KEY=your-jwt-secret                 # Optional (uses API_KEY if not set)
DATABASE_URL=postgresql://u:p@host/db          # Production DB
FRONTEND_URL=http://localhost:5173             # CORS
GEMINI_API_KEY=your-gemini-key                 # LLM
```

---

## Migration Checklist

- [x] SQLAlchemy ORM + PostgreSQL support
- [x] JWT authentication system
- [x] Multi-tenant database schema
- [x] ORM storage layer with user isolation
- [ ] Update ALL endpoints to require JWT
- [ ] Update Celery tasks with user_id
- [ ] Secure WebSocket with JWT
- [ ] Update frontend to send JWT tokens
- [ ] Test multi-user scenarios
- [ ] Deploy to production PostgreSQL

---

## Security Rules

### ✅ DO

```python
# ✅ Always require current_user
@router.get("/documents")
def get_documents(current_user: User = Depends(get_current_user)):
    ...

# ✅ Always pass user_id to storage
storage.get_document(doc_id, current_user.id)

# ✅ Always pass user_id to Celery tasks
process_document.delay(doc_id, file_path, user_id=current_user.id)
```

### ❌ DON'T

```python
# ❌ Never skip authentication
@router.get("/documents")
def get_documents():  # Missing current_user
    ...

# ❌ Never access documents without user_id
db.query(Document).filter(Document.id == doc_id).first()

# ❌ Never trust doc_id alone
process_document.delay(doc_id, file_path)  # Missing user_id
```

---

## Performance Tips

1. **Use connection pooling** (automatically enabled for PostgreSQL)
2. **Index user_id columns** (already done in models)
3. **Use JSONB for metadata** (PostgreSQL only, fast queries)
4. **Cache user lookups** (consider Redis cache for `current_user`)
5. **Batch database operations** (use `db.bulk_insert_mappings()`)

---

## 📚 Documentation Links

- [DATABASE_MIGRATION.md](DATABASE_MIGRATION.md) - Complete migration guide
- [CELERY_MULTI_TENANT.md](CELERY_MULTI_TENANT.md) - Worker security
- [MULTI_TENANT_COMPLETE.md](MULTI_TENANT_COMPLETE.md) - Full implementation details
- [SECURITY.md](SECURITY.md) - API key authentication

---

## 🎯 Remember

**Every resource MUST have user_id for multi-tenancy.**

```python
# The golden rule:
if not user_owns_resource(resource_id, user_id):
    raise HTTPException(404, "Not found")  # Never 403, always 404
```

**Why 404 and not 403?**
- 404 = "Not found" (user doesn't know resource exists)
- 403 = "Forbidden" (user knows it exists, can't access)
- Use 404 to avoid information disclosure

---

## 🚀 Next Steps

1. **Test locally**: Register 2 users, verify isolation
2. **Update endpoints**: Add `current_user` dependency
3. **Update Celery**: Pass `user_id` to all tasks
4. **Update frontend**: Send JWT tokens
5. **Deploy**: Switch to PostgreSQL in production

**You're ready to scale!** 🎉
