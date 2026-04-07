# 🐳 Docker Setup Guide - TransIQ

## Architecture Overview

TransIQ uses **100% local infrastructure** except for LLM API calls:

```
┌─────────────────────────────────────────────────┐
│  EXTERNAL (Internet Required)                   │
│  └─ Gemini API (LLM only)                       │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  LOCAL (Docker Containers - No Internet)        │
│  ├─ FastAPI Backend (port 8001)                 │
│  ├─ Celery Workers (distributed processing)     │
│  ├─ Redis (task queue + caching)                │
│  ├─ Qdrant (vector database)                    │
│  └─ Flower (monitoring UI - port 5555)          │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  LOCAL (File System)                            │
│  ├─ ./storage/local_storage.db (SQLite)        │
│  ├─ ./qdrant_storage/ (vector backups)         │
│  ├─ ./local_file_storage/ (uploads)            │
│  └─ sentence-transformers models (cached)       │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **Docker Compose** v2.0+
- **Git** (to clone the repo)

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Gemini API keys
# You ONLY need to configure LLM API keys - everything else is local!
```

**Required in `.env`**:
```bash
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_API_KEY_2=your-backup-key-here  # Optional
```

### 3. Start All Services

```bash
# Build and start all containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

**What gets started**:
- ✅ **API** on `http://localhost:8001`
- ✅ **Redis** on `localhost:6379`
- ✅ **Qdrant** on `http://localhost:6333`
- ✅ **Celery Workers** (background)
- ✅ **Flower UI** on `http://localhost:5555`

### 4. Verify Setup

```bash
# Health check
curl http://localhost:8001/health

# Qdrant dashboard
open http://localhost:6333/dashboard

# Celery monitoring
open http://localhost:5555
```

---

## 📊 Monitoring

### Flower Dashboard (Celery Tasks)
**URL**: `http://localhost:5555`

Monitor:
- Active workers
- Task queue length
- Task success/failure rates
- Real-time task execution

### Qdrant Dashboard (Vector DB)
**URL**: `http://localhost:6333/dashboard`

View:
- Collection stats
- Vector count
- Memory usage
- Search performance

---

## 🔧 Common Commands

### Start/Stop Services

```bash
# Start all services
docker-compose up -d

# Stop all services (keeps data)
docker-compose down

# Stop and remove volumes (DELETES DATA!)
docker-compose down -v

# Restart specific service
docker-compose restart api
docker-compose restart worker
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f qdrant

# Last 100 lines
docker-compose logs --tail=100 api
```

### Scale Workers

```bash
# Run 5 Celery workers for parallel processing
docker-compose up -d --scale worker=5

# Check worker count
docker-compose ps worker
```

### Database Access

```bash
# Access SQLite database
docker-compose exec api sqlite3 /app/storage/local_storage.db

# Export data
docker-compose exec api sqlite3 /app/storage/local_storage.db ".dump" > backup.sql
```

---

## 🛠️ Development Mode

### Run Without Docker (Use Local Python)

```bash
# Start only Redis and Qdrant in Docker
docker-compose up -d redis qdrant

# Run API locally
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Run worker locally
celery -A app.workers.processor.celery worker --loglevel=info --pool=solo
```

**Benefits**:
- Faster code changes (no rebuild)
- Better debugging
- IDE integration

---

## 🔄 Backup & Restore

### Backup Data

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup SQLite database
docker-compose exec api cp /app/storage/local_storage.db /app/backups/$(date +%Y%m%d)/

# Backup Qdrant vectors
docker-compose exec qdrant tar -czf /qdrant/storage/backup.tar.gz /qdrant/storage

# Copy to host
docker cp $(docker-compose ps -q qdrant):/qdrant/storage/backup.tar.gz ./backups/$(date +%Y%m%d)/
```

### Restore Data

```bash
# Restore SQLite
docker cp ./backups/20260325/local_storage.db $(docker-compose ps -q api):/app/storage/

# Restore Qdrant
docker cp ./backups/20260325/backup.tar.gz $(docker-compose ps -q qdrant):/qdrant/storage/
docker-compose exec qdrant tar -xzf /qdrant/storage/backup.tar.gz
docker-compose restart qdrant
```

---

## 🚨 Troubleshooting

### Problem: "Address already in use"

**Cause**: Port conflict (another service using 8001, 6379, or 6333)

**Solution**:
```bash
# Check what's using the port
netstat -ano | findstr :8001

# Kill the process (Windows)
taskkill /PID <PID> /F

# Or change port in docker-compose.yml
ports:
  - '8002:8001'  # Use 8002 instead
```

### Problem: "Cannot connect to Redis"

**Cause**: Redis container not started or unhealthy

**Solution**:
```bash
# Check Redis health
docker-compose ps redis

# View Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

### Problem: "Qdrant connection failed"

**Cause**: Qdrant container not ready or local path conflict

**Solution**:
```bash
# Check Qdrant health
curl http://localhost:6333/health

# Force use local Qdrant (fallback)
# Add to .env:
USE_LOCAL_QDRANT=true

# Restart API
docker-compose restart api
```

### Problem: "Worker not processing tasks"

**Cause**: Celery worker crashed or Redis connection lost

**Solution**:
```bash
# Check worker logs
docker-compose logs worker

# Restart worker
docker-compose restart worker

# Scale up workers
docker-compose up -d --scale worker=3
```

---

## 🎯 Production Deployment

### AWS EC2 / DigitalOcean Droplet

```bash
# 1. SSH into server
ssh user@your-server.com

# 2. Install Docker + Docker Compose
curl -fsSL https://get.docker.com | sh
sudo apt install docker-compose-plugin

# 3. Clone repo
git clone https://github.com/your-org/transiq-backend.git
cd transiq-backend

# 4. Configure .env
cp .env.example .env
nano .env  # Add Gemini API keys

# 5. Start services
docker-compose up -d

# 6. Enable auto-restart on boot
docker-compose up -d --restart unless-stopped
```

**Recommended Instance**:
- **CPU**: 2+ cores
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 20GB SSD
- **Cost**: ~$10-20/month

---

## 📦 What's Stored Where

| Data Type | Docker Volume | Host Path | Size | Persistent? |
|-----------|--------------|-----------|------|-------------|
| SQLite DB | N/A | `./storage/` | ~10MB | ✅ Yes |
| Vector DB | `qdrant_data` | `./qdrant_storage/` | ~100MB-1GB | ✅ Yes |
| Redis Cache | `redis_data` | N/A | ~10MB | ✅ Yes |
| Uploads | N/A | `./local_file_storage/` | Variable | ✅ Yes |
| Embeddings Model | N/A | `~/.cache/torch/` | ~80MB | ✅ Yes (cached) |
| Logs | N/A | `./logs/` | ~5MB | ✅ Yes |

**On `docker-compose down`**: Host paths persist, Docker volumes persist  
**On `docker-compose down -v`**: Host paths persist, Docker volumes DELETED

---

## 🔐 Security Best Practices

### 1. Protect API Keys

```bash
# Never commit .env file
echo ".env" >> .gitignore

# Use environment variables in production
export GEMINI_API_KEY="..."
```

### 2. Restrict Network Access

```yaml
# docker-compose.yml
services:
  redis:
    ports: []  # Remove external access
    expose:
      - "6379"  # Only accessible to other containers
```

### 3. Enable HTTPS (Production)

```bash
# Use Nginx reverse proxy
docker run -d \
  --name nginx \
  -p 80:80 \
  -p 443:443 \
  -v ./nginx.conf:/etc/nginx/nginx.conf \
  nginx:alpine
```

---

## 📚 Additional Resources

- **Qdrant Docs**: https://qdrant.tech/documentation/
- **Celery Docs**: https://docs.celeryq.dev/
- **Docker Compose Docs**: https://docs.docker.com/compose/

---

## ✅ Summary

✅ **Zero external dependencies** except Gemini API  
✅ **All data stored locally** (SQLite + Qdrant + Redis)  
✅ **Horizontal scaling** via worker replication  
✅ **Auto-restart** on crash (`restart: unless-stopped`)  
✅ **Monitoring UI** (Flower + Qdrant dashboard)  
✅ **Production-ready** infrastructure  

**Total setup time**: 5 minutes 🚀
