# 🔒 Securing Celery Workers with User Context

## Problem

Celery workers process documents in the background, but they need to know **which user** owns the data to maintain multi-tenant isolation.

**Without user_id**:
- Workers could mix data between users
- Security vulnerability (data leakage)
- No usage tracking per user

---

## Solution

Pass `user_id` to all Celery tasks and enforce it in worker functions.

---

## Implementation

### 1. Update Task Enqueue

**Before** ❌:
```python
from app.workers.tasks import process_document

task = process_document.delay(doc_id, file_path)
```

**After** ✅:
```python
from app.workers.tasks import process_document

task = process_document.delay(
    doc_id=doc_id,
    file_path=file_path,
    user_id=current_user.id  # ← Pass user context
)
```

---

### 2. Update Celery Task Signature

**File**: `app/workers/processor.py`

```python
from app.db import get_db_context
from app.storage.orm_storage import ORMStorage

@celery.task(bind=True, max_retries=3)
def process_document(
    self,
    doc_id: str,
    file_path: str,
    user_id: str,  # ← NEW: Required parameter
    provider: str = "gemini",
    enable_deduction: bool = True
):
    """Process document with user context"""
    
    # Use ORM storage with user validation
    with get_db_context() as db:
        storage = ORMStorage(db)
        
        # All storage operations now validate user_id
        document = storage.get_document(doc_id, user_id)
        if not document:
            raise ValueError(f"Document {doc_id} not found for user {user_id}")
        
        # Process document...
        chunks = extract_chunks(file_path)
        
        # Save chunks (validates user owns document)
        storage.save_chunks(chunks, user_id)
        
        # Generate dashboard
        dashboard = generate_dashboard(chunks)
        storage.save_dashboard(doc_id, user_id, dashboard)
        
        # Update task status
        storage.save_task_status(
            task_id=self.request.id,
            doc_id=doc_id,
            user_id=user_id,
            status="completed",
            progress=100
        )
```

---

### 3. Update Endpoint

**File**: `app/api/v2/endpoints.py`

```python
from app.auth import get_current_user
from app.db.models import User

@router.post("/generate")
async def generate_document(
    file: UploadFile,
    current_user: User = Depends(get_current_user),  # ← JWT auth
    db: Session = Depends(get_db)
):
    """Upload and process document (user-specific)"""
    
    # Save file
    file_path = save_uploaded_file(file)
    
    # Create document (with user_id)
    storage = ORMStorage(db)
    doc_id = str(uuid.uuid4())
    document = storage.save_document(
        doc_id=doc_id,
        user_id=current_user.id,  # ← User ownership
        metadata={"filename": file.filename},
        filename=file.filename
    )
    
    # Enqueue Celery task (with user_id)
    task = process_document.delay(
        doc_id=doc_id,
        file_path=file_path,
        user_id=current_user.id  # ← Pass to worker
    )
    
    return {
        "doc_id": doc_id,
        "task_id": task.id,
        "status": "processing"
    }
```

---

### 4. Update Redis Pub/Sub

**File**: `app/workers/processor.py`

```python
def _publish_progress(doc_id: str, user_id: str, stage: str, progress: int, message: str):
    """Publish progress to Redis (with user context)"""
    try:
        redis_client = redis.Redis.from_url(settings.REDIS_URL)
        
        event_data = {
            "doc_id": doc_id,
            "user_id": user_id,  # ← Include user_id
            "stage": stage,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Publish to user-specific channel
        redis_client.publish(
            f"doc:{doc_id}:user:{user_id}",  # ← User-specific channel
            json.dumps(event_data)
        )
    except Exception as e:
        logger.error(f"Redis publish failed: {e}")
```

---

### 5. Secure WebSocket Connections

**File**: `app/websocket/handlers.py`

```python
from app.auth import decode_access_token
from app.db import get_db_context
from app.db.models import User

@router.websocket("/ws/document/{doc_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    doc_id: str,
    token: str = Query(...)  # ← Require JWT token
):
    """WebSocket endpoint with authentication"""
    
    # Validate JWT token
    user_id = decode_access_token(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Validate user owns document
    with get_db_context() as db:
        storage = ORMStorage(db)
        document = storage.get_document(doc_id, user_id)
        
        if not document:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    
    # Accept connection
    await websocket.accept()
    
    # Subscribe to user-specific Redis channel
    redis_client = redis.Redis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"doc:{doc_id}:user:{user_id}")
    
    # Forward events to WebSocket
    async for message in pubsub.listen():
        if message['type'] == 'message':
            await websocket.send_text(message['data'])
```

---

## Usage Example

### Frontend WebSocket Connection

```typescript
// src/api/websocket.ts
const token = localStorage.getItem('access_token');
const ws = new WebSocket(
  `ws://localhost:8001/ws/document/${docId}?token=${token}`
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}% - ${data.message}`);
};
```

---

## Security Benefits

| Feature | Benefit |
|---------|---------|
| **User context in workers** | Workers can only access user's own data |
| **User-specific Redis channels** | Progress updates isolated per user |
| **JWT on WebSocket** | Only document owner receives updates |
| **Database validation** | All operations check user_id FK |

---

## Testing

### 1. Test User Isolation

```python
# User A enqueues task
user_a_id = "user-a-uuid"
task_a = process_document.delay(doc_id="doc-1", user_id=user_a_id, ...)

# Worker processes with User A context
# Tries to access User B's document → FAILS with ValueError
```

### 2. Test WebSocket Security

```bash
# User A's token
TOKEN_A="eyJhbGciOiJIUzI1..."

# Try to connect to User B's document → Should fail
wscat -c "ws://localhost:8001/ws/document/user-b-doc-id?token=$TOKEN_A"
# Result: Connection closed (policy violation)
```

---

## Migration Checklist

- [ ] Update all `process_document.delay()` calls to include `user_id`
- [ ] Update Celery task signatures to accept `user_id`
- [ ] Replace direct database access with `ORMStorage(db)`
- [ ] Update Redis Pub/Sub channels to include `user_id`
- [ ] Add JWT authentication to WebSocket endpoints
- [ ] Validate document ownership in WebSocket handler
- [ ] Test multi-user scenarios
- [ ] Update Celery worker deployment scripts

---

## Complete Example

**app/workers/processor.py** (Full implementation):

```python
from celery import Celery
import redis
import json
from datetime import datetime, timezone

from app.db import get_db_context
from app.storage.orm_storage import ORMStorage
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

celery = Celery('transiq', broker=settings.REDIS_URL)

def _publish_progress(doc_id: str, user_id: str, stage: str, progress: int, message: str):
    """Publish progress to user-specific Redis channel"""
    try:
        redis_client = redis.Redis.from_url(settings.REDIS_URL)
        event_data = {
            "doc_id": doc_id,
            "user_id": user_id,
            "stage": stage,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        redis_client.publish(f"doc:{doc_id}:user:{user_id}", json.dumps(event_data))
    except Exception as e:
        logger.error(f"Redis publish failed: {e}")

@celery.task(bind=True, max_retries=3)
def process_document(
    self,
    doc_id: str,
    file_path: str,
    user_id: str,
    provider: str = "gemini",
    enable_deduction: bool = True
):
    """Process document with user context and multi-tenant isolation"""
    
    task_id = self.request.id
    
    try:
        with get_db_context() as db:
            storage = ORMStorage(db)
            
            # Stage 1: Validate ownership
            _publish_progress(doc_id, user_id, "validating", 0, "Validating document ownership")
            document = storage.get_document(doc_id, user_id)
            if not document:
                raise ValueError(f"Document {doc_id} not found for user {user_id}")
            
            # Stage 2: Read file
            _publish_progress(doc_id, user_id, "reading_file", 10, "Reading document")
            content = read_file(file_path)
            
            # Stage 3: Chunk
            _publish_progress(doc_id, user_id, "chunking", 20, "Chunking text")
            chunks = extract_chunks(content)
            storage.save_chunks(chunks, user_id)
            
            # Stage 4: Embed
            _publish_progress(doc_id, user_id, "embedding", 40, "Generating embeddings")
            embeddings = generate_embeddings(chunks)
            
            # Stage 5: Dashboard
            _publish_progress(doc_id, user_id, "generating_dashboard", 75, "Creating dashboard")
            dashboard = generate_dashboard(chunks)
            storage.save_dashboard(doc_id, user_id, dashboard)
            
            # Stage 6: Complete
            _publish_progress(doc_id, user_id, "completed", 100, "Processing complete")
            storage.update_document_status(doc_id, user_id, "completed")
            storage.save_task_status(task_id, doc_id, user_id, "completed", "completed", 100)
            
            return {"doc_id": doc_id, "status": "completed"}
            
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        _publish_progress(doc_id, user_id, "failed", 0, f"Error: {str(e)}")
        
        with get_db_context() as db:
            storage = ORMStorage(db)
            storage.update_document_status(doc_id, user_id, "failed")
            storage.save_task_status(task_id, doc_id, user_id, "failed", error=str(e))
        
        raise
```

---

## 🎯 Key Takeaway

**Every background task MUST include `user_id` to maintain multi-tenant security.**

```python
# ❌ INSECURE: No user context
process_document.delay(doc_id, file_path)

# ✅ SECURE: User context enforced
process_document.delay(doc_id, file_path, user_id=current_user.id)
```

This ensures:
- Workers only access user's own data
- Progress updates go to correct user
- Database operations validate ownership
- Audit trail includes user_id
