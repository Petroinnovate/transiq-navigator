# 🚀 Database Migration Guide: SQLite → PostgreSQL + Multi-Tenancy

## 🔴 **Critical Architectural Upgrade**

This migration transforms TransIQ from a **single-node prototype** to a **distributed, multi-tenant SaaS platform**.

---

## What Changed

### Before ❌
- SQLite (single file database)
- No user authentication
- No data isolation
- Write locking (kills concurrency)
- Not production-ready

### After ✅
- PostgreSQL (or SQLite for dev) via SQLAlchemy ORM
- JWT authentication with user accounts
- Multi-tenant architecture (user_id on all tables)
- Horizontal scaling support
- Production-ready

---

## 🏗️ Architecture Changes

### Database Layer

**Old**:
```python
import sqlite3
conn = sqlite3.connect("storage.db")
```

**New**:
```python
from sqlalchemy.orm import Session
from app.db import get_db
from app.db.models import Document, User

def get_documents(db: Session = Depends(get_db)):
    return db.query(Document).all()
```

### Authentication Layer

**Old**:
```python
# No authentication
# Anyone could access any document
```

**New**:
```python
from app.auth import get_current_user
from app.db.models import User

def get_my_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only see your own documents
    return db.query(Document).filter(
        Document.user_id == current_user.id
    ).all()
```

---

## 📋 Migration Steps

### Step 1: Install Dependencies

```bash
cd TransIQ-backend-master
pip install -r requirements.txt
```

**New dependencies**:
- `sqlalchemy>=2.0.0` - ORM framework
- `alembic>=1.13.0` - Database migrations
- `python-jose[cryptography]>=3.3.0` - JWT tokens
- `passlib[bcrypt]>=1.7.4` - Password hashing
- `psycopg2-binary>=2.9.9` - PostgreSQL adapter

---

### Step 2: Configure Database URL

#### Option A: Keep SQLite (Development)

```bash
# .env
DATABASE_URL=sqlite:///./storage/local_storage.db
```

#### Option B: Use PostgreSQL (Production)

```bash
# .env
DATABASE_URL=postgresql://user:password@localhost:5432/transiq
```

#### Option C: Use Supabase (Recommended)

```bash
# .env
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```

---

### Step 3: Initialize Database

The database will auto-initialize on first startup:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**Expected logs**:
```
🚀 Starting TransIQ Backend v2.0...
Database engine initialized: local_storage.db
Database tables created/verified
✅ Database initialized
```

---

### Step 4: Create First User

```bash
# Register a new user
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "securepassword123"
  }'
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "admin@example.com"
}
```

**Save this token!** You'll need it for authenticated requests.

---

### Step 5: Test Authentication

```bash
# Test without token (should fail)
curl http://localhost:8001/api/v2/documents

# Test with token (should work)
curl http://localhost:8001/api/v2/documents \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

---

## 🔐 Multi-Tenancy Details

### User Isolation

Every table now has `user_id`:

| Table | User Isolation |
|-------|---------------|
| `users` | Primary user table |
| `documents` | `user_id` FK → only see your docs |
| `chunks` | Inherits from documents |
| `tasks` | `user_id` FK → only see your tasks |
| `batches` | `user_id` FK → only see your batches |
| `graph_edges` | Inherits from documents |

### Access Control

```python
# ❌ OLD: Anyone could access
@app.get("/documents/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.id == doc_id).first()

# ✅ NEW: Only owner can access
@app.get("/documents/{doc_id}")
def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == current_user.id  # ← Security check
    ).first()
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    return doc
```

---

## 🔄 Migrating Existing Data

If you have existing SQLite data, you can migrate it:

### Option 1: Manual Migration Script

```python
# scripts/migrate_data.py
from app.db.session import get_db_context
from app.db.models import User, Document
import sqlite3
import uuid

# Create a default user for existing data
with get_db_context() as db:
    default_user = User(
        id=str(uuid.uuid4()),
        email="migrated@example.com",
        hashed_password="change-me",
        is_active=1
    )
    db.add(default_user)
    db.commit()
    
    # Migrate documents
    old_conn = sqlite3.connect("storage/local_storage.db")
    old_cursor = old_conn.cursor()
    
    for row in old_cursor.execute("SELECT * FROM documents"):
        doc = Document(
            id=row[0],
            user_id=default_user.id,  # Assign to default user
            metadata=row[2],
            dashboard_data=row[3],
            status=row[4],
            created_at=row[5]
        )
        db.add(doc)
    
    db.commit()
    print("Migration complete! Update user password.")
```

### Option 2: Fresh Start (Recommended)

Just start fresh with the new system. Old data stays in `storage/local_storage.db` for reference.

---

## 🧪 Testing the New System

### 1. Test User Registration

```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'
```

### 2. Test User Login

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'
```

### 3. Test Document Upload (with JWT)

```bash
TOKEN="your-jwt-token-here"

curl -X POST http://localhost:8001/api/v2/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Key: your-api-key" \
  -F "file=@test.txt"
```

### 4. Test Data Isolation

```bash
# User A uploads document
TOKEN_A="user-a-token"
curl -X POST http://localhost:8001/api/v2/generate \
  -H "Authorization: Bearer $TOKEN_A" \
  -F "file=@doc_a.txt"

# User B tries to access User A's documents
TOKEN_B="user-b-token"
curl http://localhost:8001/api/v2/documents \
  -H "Authorization: Bearer $TOKEN_B"

# Result: User B sees ONLY their own documents (empty list)
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/transiq  # Or sqlite:///./storage/db.sqlite

# Security (both API key and JWT work together)
API_KEY=your-api-key-for-general-access
JWT_SECRET_KEY=your-jwt-secret-for-user-tokens  # Uses API_KEY if not set

# Frontend
FRONTEND_URL=http://localhost:5173
```

### Dual Authentication System

TransIQ now has **two layers** of security:

1. **API Key** (outer layer) - General API access
   - Required for ALL `/api/*` endpoints
   - Prevents unauthorized public access
   - Set via `X-API-Key` header

2. **JWT Token** (inner layer) - User identity
   - Required for user-specific operations
   - Enables multi-tenancy and data isolation
   - Set via `Authorization: Bearer <token>` header

**Example authenticated request**:
```bash
curl -X POST http://localhost:8001/api/v2/generate \
  -H "X-API-Key: your-api-key" \           # ← Layer 1: API access
  -H "Authorization: Bearer jwt-token" \   # ← Layer 2: User identity
  -F "file=@document.txt"
```

---

## 🚀 Scaling to Production

### Option 1: Single PostgreSQL Server

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: transiq
      POSTGRES_PASSWORD: securepass
      POSTGRES_DB: transiq
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  api:
    build: .
    environment:
      DATABASE_URL: postgresql://transiq:securepass@postgres:5432/transiq
    depends_on:
      - postgres
```

### Option 2: Managed PostgreSQL (Recommended)

Use a managed service:
- **Supabase** (PostgreSQL + Auth + Storage) - $25/month
- **AWS RDS** - $50-200/month
- **DigitalOcean** - $15/month

### Option 3: High Availability Setup

- PostgreSQL primary + replica
- Connection pooling (PgBouncer)
- Read replicas for analytics

---

## 📊 Performance Comparison

| Metric | SQLite (Old) | PostgreSQL (New) |
|--------|-------------|------------------|
| Concurrent writes | ❌ 1 | ✅ 1000+ |
| Horizontal scaling | ❌ No | ✅ Yes |
| Connection pooling | ❌ No | ✅ Yes |
| JSONB queries | ❌ Limited | ✅ Fast |
| Backup/restore | ⚠️ File copy | ✅ Point-in-time |
| Multi-tenant | ❌ No | ✅ Yes |

---

## 🐛 Troubleshooting

### Issue: "Could not translate host name to address"

**Problem**: Wrong DATABASE_URL format

**Solution**:
```bash
# ❌ Wrong
DATABASE_URL=postgres://user:pass@host/db

# ✅ Correct
DATABASE_URL=postgresql://user:pass@host/db
```

### Issue: "relation 'users' does not exist"

**Problem**: Database not initialized

**Solution**:
```bash
# Restart backend to auto-create tables
python -m uvicorn app.main:app --reload
```

### Issue: "JWT decode error"

**Problem**: Invalid or expired token

**Solution**:
```bash
# Login again to get fresh token
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpass"}'
```

### Issue: "User does not own this document"

**Problem**: Trying to access another user's data

**Solution**: This is **by design** (multi-tenancy working correctly). Only access your own documents.

---

## 🎯 Next Steps

After completing this migration:

1. ✅ **Update frontend** to send JWT tokens ([FRONTEND_SECURITY_INTEGRATION.md](../../TransIQ-frontend-main/FRONTEND_SECURITY_INTEGRATION.md))
2. ✅ **Test multi-user scenarios** (create multiple accounts, verify isolation)
3. ✅ **Set up production PostgreSQL** (Supabase or AWS RDS)
4. ⏳ **Implement usage tracking** (per-user LLM costs, quotas)
5. ⏳ **Add billing integration** (Stripe subscriptions)
6. ⏳ **Set up monitoring** (Sentry, DataDog)

---

## 📚 Related Documentation

- [SECURITY.md](./SECURITY.md) - API key authentication
- [FRONTEND_SECURITY_INTEGRATION.md](../../TransIQ-frontend-main/FRONTEND_SECURITY_INTEGRATION.md) - Frontend JWT integration
- [DOCKER_SETUP.md](./DOCKER_SETUP.md) - Docker deployment
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture

---

## ✅ Migration Checklist

- [ ] Install new dependencies (`pip install -r requirements.txt`)
- [ ] Set `DATABASE_URL` in `.env`
- [ ] Restart backend (auto-creates tables)
- [ ] Register first user (`POST /auth/register`)
- [ ] Test authentication (`POST /auth/login`)
- [ ] Update frontend to send JWT tokens
- [ ] Test document upload with authentication
- [ ] Verify data isolation (create 2 users, verify separation)
- [ ] Deploy to production PostgreSQL
- [ ] Update Celery workers to use ORM
- [ ] Set up database backups

---

## 🎉 Success!

You now have:
- ✅ Production-grade database (PostgreSQL)
- ✅ Multi-tenant architecture
- ✅ JWT authentication
- ✅ Data isolation per user
- ✅ Horizontal scaling capability
- ✅ Enterprise-ready security

**TransIQ is now a real SaaS platform!** 🚀
