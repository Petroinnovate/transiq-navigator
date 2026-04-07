# 🎯 TransIQ Architecture - Local-First Design

## Overview

TransIQ uses a **local-first architecture** where all infrastructure runs on-premise or in Docker containers. The ONLY external dependency is the LLM API for natural language processing.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICES                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  LLM API (Gemini / OpenAI / Anthropic)                   │  │
│  │  - Document analysis                                     │  │
│  │  - KPI extraction                                        │  │
│  │  - Dashboard generation                                  │  │
│  │  - Natural language queries                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ↓
                         HTTPS/TLS
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                      DOCKER CONTAINERS                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   FastAPI   │  │   Celery    │  │   Flower    │            │
│  │   Backend   │  │   Worker    │  │  Monitor    │            │
│  │  :8001      │  │  (scalable) │  │   :5555     │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
│         │                │                 │                    │
│         └────────────────┴─────────────────┘                    │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Redis :6379                              │  │
│  │  - Task queue (Celery broker)                            │  │
│  │  - Pub/Sub (real-time progress)                          │  │
│  │  - Caching                                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Qdrant :6333                             │  │
│  │  - Vector database (embeddings)                           │  │
│  │  - Semantic search                                        │  │
│  │  - Persistent storage                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                      LOCAL FILE SYSTEM                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ./storage/local_storage.db (SQLite)                     │  │
│  │  - Document metadata                                      │  │
│  │  - Processing status                                      │  │
│  │  - Task history                                           │  │
│  │  - Batch tracking                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ./qdrant_storage/ (fallback)                            │  │
│  │  - Local Qdrant backup                                   │  │
│  │  - Used if Docker Qdrant unavailable                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ./local_file_storage/ (uploads)                         │  │
│  │  - User uploaded files                                   │  │
│  │  - PDF, Excel, Word, CSV                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ~/.cache/torch/sentence_transformers/                   │  │
│  │  - all-MiniLM-L6-v2 (384-dim embeddings)                 │  │
│  │  - Downloaded once, cached forever                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. **FastAPI Backend** (Port 8001)
**Purpose**: REST API server

**Responsibilities**:
- File upload handling
- Task dispatch (sends to Celery)
- WebSocket connections (real-time updates)
- Search queries (hybrid: BM25 + vector)
- Dashboard generation coordination

**External Dependencies**: 
- ❌ None (receives LLM keys, doesn't require external services)

**Local Dependencies**:
- ✅ Redis (task queue)
- ✅ Qdrant (vector search)
- ✅ SQLite (metadata)

---

### 2. **Celery Worker** (Scalable)
**Purpose**: Distributed document processing

**Responsibilities**:
- Read uploaded files
- Chunk documents (AdaptiveChunker)
- Generate embeddings (sentence-transformers)
- Store vectors in Qdrant
- Call LLM for dashboard generation
- Update task status via Redis Pub/Sub

**External Dependencies**:
- ⚠️ LLM API (Gemini/OpenAI/Anthropic) - ONLY external call

**Local Dependencies**:
- ✅ Redis (task queue)
- ✅ Qdrant (vector storage)
- ✅ SQLite (metadata)
- ✅ sentence-transformers (local model)

**Scaling**: 
```bash
docker-compose up -d --scale worker=5  # Run 5 workers
```

---

### 3. **Redis** (Port 6379)
**Purpose**: Task queue, caching, Pub/Sub

**Responsibilities**:
- Celery broker (distributes tasks to workers)
- Celery result backend (stores task results)
- Pub/Sub channel for real-time progress (`doc:{doc_id}`)
- Cache layer for frequent queries

**External Dependencies**: 
- ❌ None (100% local)

**Persistence**: 
- ✅ Data persists in Docker volume `redis_data`

---

### 4. **Qdrant** (Port 6333)
**Purpose**: Vector database for semantic search

**Responsibilities**:
- Store 384-dim embeddings (all-MiniLM-L6-v2)
- Cosine similarity search
- Hybrid search (combine with BM25)
- PageIndex chunk storage

**External Dependencies**: 
- ❌ None (100% local)

**Persistence**: 
- ✅ Data persists in Docker volume `qdrant_data`
- ✅ Fallback to `./qdrant_storage/` folder if Docker unavailable

**Dashboard**: `http://localhost:6333/dashboard`

---

### 5. **Flower** (Port 5555) - Optional
**Purpose**: Celery monitoring UI

**Responsibilities**:
- Show active workers
- Display task queue length
- Track task success/failure rates
- Real-time task execution visualization

**External Dependencies**: 
- ❌ None

**Dashboard**: `http://localhost:5555`

---

### 6. **SQLite Database**
**Purpose**: Metadata storage

**Stored Data**:
- Documents table (id, user_id, status, metadata, dashboard_data)
- Chunks table (id, doc_id, chunk_text, metadata)
- Batches table (batch processing tracking)
- Task status (Celery task progress)
- Knowledge graph edges (deduction engine)

**External Dependencies**: 
- ❌ None (file-based DB)

**Location**: `./storage/local_storage.db`

---

### 7. **Embedding Model** (sentence-transformers)
**Purpose**: Generate vector embeddings

**Model**: `all-MiniLM-L6-v2`
- **Size**: ~80MB
- **Dimensions**: 384
- **Speed**: ~1000 sentences/second (CPU)
- **Quality**: Good balance of speed vs accuracy

**External Dependencies**:
- ⚠️ Downloads from HuggingFace on first run (then cached locally)

**Cache Location**: `~/.cache/torch/sentence_transformers/`

---

## Data Flow: Document Upload → Dashboard

```
1. User uploads PDF
   ↓
2. FastAPI saves to ./local_file_storage/
   ↓
3. FastAPI dispatches Celery task
   ↓
4. Celery worker picks up task from Redis
   ↓
5. Worker reads file, chunks it (AdaptiveChunker)
   ↓
6. Worker generates embeddings (sentence-transformers - LOCAL)
   ↓
7. Worker stores vectors in Qdrant (Docker container)
   ↓
8. Worker stores chunks in SQLite
   ↓
9. Worker calls LLM API (Gemini) ← ONLY EXTERNAL CALL
   ↓
10. Worker saves dashboard JSON to SQLite
    ↓
11. Worker publishes "completed" event to Redis Pub/Sub
    ↓
12. WebSocket forwards event to frontend
    ↓
13. Frontend displays dashboard
```

**Total external API calls**: 1 (LLM dashboard generation)

---

## What Happens If Services Go Down?

| Service | Impact | Fallback | Recovery |
|---------|--------|----------|----------|
| **Gemini API** | ❌ Can't generate dashboards | Use OpenAI/Anthropic/Ollama | Retry with next provider |
| **Redis** | ⚠️ Falls back to threading | Process in-memory (non-distributed) | Auto-reconnect when Redis available |
| **Qdrant Docker** | ⚠️ Uses local file | Falls back to `./qdrant_storage/` | Auto-reconnect when Qdrant available |
| **SQLite** | ❌ Can't save metadata | None (file-based, rarely fails) | Check file permissions |
| **Celery Worker** | ⚠️ Tasks queue up in Redis | Wait for worker to restart | `docker-compose restart worker` |
| **Internet** | ⚠️ Can't call LLM API | Search/retrieval still works | Wait for connection |

**Key Insight**: If internet goes down, you can still:
- ✅ Search existing documents (hybrid search)
- ✅ View existing dashboards
- ✅ Upload new files (processed when LLM available)

---

## Resource Requirements

### Minimum (Development)
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 10GB
- **Network**: 10 Mbps (for LLM API calls)

### Recommended (Production)
- **CPU**: 4+ cores
- **RAM**: 8GB
- **Storage**: 50GB SSD
- **Network**: 100 Mbps

### Storage Breakdown
- Docker images: ~2GB
- sentence-transformers model: ~80MB
- Qdrant vectors: ~1GB per 1M chunks
- SQLite database: ~10MB per 10K documents
- Uploaded files: Variable (user data)

---

## Deployment Options

### Option 1: Single Server (Docker Compose)
**Best for**: Small teams, POC, development

```bash
docker-compose up -d
```

**Cost**: $10-20/month (DigitalOcean, AWS EC2)

---

### Option 2: Kubernetes (Multi-Server)
**Best for**: Enterprise, high availability

**Architecture**:
- API pods (multiple replicas)
- Worker pods (auto-scaling)
- Redis cluster (3 nodes)
- Qdrant StatefulSet (persistent volumes)

**Cost**: $100-500/month (depends on scale)

---

### Option 3: Hybrid (Local Backend + Cloud Frontend)
**Best for**: Privacy-sensitive data

**Architecture**:
- Backend runs on-premise (behind firewall)
- Frontend served from CDN (Vercel/Netlify)
- VPN tunnel for API access

**Benefit**: User data never leaves your network

---

## Security Features

### 1. No External Data Storage
- ✅ All vectors stored locally (Qdrant)
- ✅ All metadata stored locally (SQLite)
- ✅ Embeddings generated locally (sentence-transformers)
- ⚠️ Only prompts sent to LLM API (no raw documents)

### 2. Network Isolation
- ✅ Redis: Only accessible to Docker network
- ✅ Qdrant: Only accessible to Docker network
- ✅ SQLite: File-based, no network exposure

### 3. API Key Management
- ✅ Stored in `.env` file (never committed)
- ✅ Loaded via environment variables
- ✅ Rotation supported (GEMINI_API_KEY_2, _3, _4)

---

## Monitoring & Observability

### Built-in Dashboards
1. **Flower** (Celery): `http://localhost:5555`
2. **Qdrant**: `http://localhost:6333/dashboard`
3. **FastAPI Docs**: `http://localhost:8001/docs`

### Health Check Endpoint
```bash
curl http://localhost:8001/api/v2/health
```

**Returns**:
```json
{
  "status": "ok",
  "services": {
    "redis": "ok",
    "qdrant": "ok",
    "qdrant_mode": "docker",
    "database": "ok",
    "llm": "ok",
    "llm_providers": ["gemini"],
    "celery": "ok",
    "worker_count": 2
  }
}
```

---

## Comparison: TransIQ vs Cloud-Native AI Platforms

| Feature | TransIQ (Local-First) | Typical Cloud AI Platform |
|---------|----------------------|--------------------------|
| **Vector DB** | ✅ Qdrant (local Docker) | ❌ Pinecone ($70/month) |
| **Task Queue** | ✅ Redis (local Docker) | ❌ AWS SQS (pay per request) |
| **Database** | ✅ SQLite (local file) | ❌ PostgreSQL Cloud ($25/month) |
| **Embeddings** | ✅ sentence-transformers (local) | ❌ OpenAI Embeddings API ($0.0001/1K) |
| **LLM** | ⚠️ Gemini API (required) | ❌ OpenAI API (required) |
| **Scalability** | ⚠️ Single-server or K8s | ✅ Auto-scaling cloud |
| **Data Privacy** | ✅ 100% on-premise | ❌ Data in cloud |
| **Monthly Cost** | 💰 $10-20 (server only) | 💰 $200-1000 (all services) |

**Savings**: ~90% lower operational costs

---

## Summary

✅ **100% local infrastructure** (except LLM API)  
✅ **Self-contained Docker deployment**  
✅ **Horizontal scaling** (Celery workers)  
✅ **Zero vendor lock-in**  
✅ **Data sovereignty** (all data on-premise)  
✅ **Cost-effective** ($10-20/month vs $200-1000)  
✅ **Production-ready** (health checks, monitoring, auto-restart)  
⚠️ **Single external dependency**: LLM API (Gemini/OpenAI)

**Philosophy**: "Run the infrastructure locally, use cloud AI for what it's good at (language understanding)."
