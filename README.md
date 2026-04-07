# TransIQ Backend v2.0

Production-ready document processing and analytics backend with multi-LLM support, adaptive chunking, deduction engine, pattern recognition, and hybrid search.

## Features

- **Multi-LLM Provider Support**: Gemini, OpenAI, and more
- **Adaptive Chunking**: Hierarchical and table-aware text chunking
- **Deduction Engine**: LLM-powered fact extraction and knowledge graph building
- **GraphRAG Integration**: Advanced entity resolution, multi-hop reasoning, graph analytics
  - Entity Deduplication: Fuzzy matching with 85% similarity threshold
  - Knowledge Graph: Entities, relationships, and mentions across documents
  - Multi-hop Reasoning: Find indirect connections between entities
  - Graph Analytics: Centrality metrics, anomaly detection, community detection
  - Entity Impact Analysis: Understand entity importance in the overall graph
- **Pattern Recognition**: Anomaly detection and clustering
- **Hybrid Search**: BM25 + semantic search with re-ranking + graph-based search
- **Background Processing**: Celery workers with Redis queue
- **Real-time Updates**: WebSocket progress tracking
- **Vector Storage**: FAISS (local) + Supabase (optional)
- **🔒 Security**: API key authentication + CORS protection + rate limiting

## 🔐 Security (IMPORTANT)

**TransIQ now requires API key authentication for all endpoints.**

This protects your LLM API quota and prevents unauthorized access.

### Quick Security Setup:

1. **Generate an API key**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Add to `.env`**:
   ```bash
   API_KEY=your-generated-key-here
   FRONTEND_URL=http://localhost:5173
   ```

3. **Include in requests**:
   ```bash
   curl -H "X-API-Key: your-key-here" http://localhost:8001/api/v2/health
   ```

**📖 See [SECURITY.md](./SECURITY.md) for complete security guide**

---

## Quick Start

### Local Development

1. **Clone and setup environment**
   ```bash
   cp .env.example .env
   # Edit .env and add:
   # - API_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
   # - GEMINI_API_KEY (at least one LLM key required)
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Redis** (required for background workers)
   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis:7-alpine
   
   # Or install locally and run: redis-server
   ```

4. **Start the API server**
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Start Celery worker** (in another terminal)
   ```bash
   celery -A app.workers.processor.celery worker --loglevel=info
   ```

6. **Access API**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker Compose (Recommended)

1. **Setup environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start all services**
   ```bash
   docker-compose up --build
   ```

   This starts:
   - Redis (port 6379)
   - API server (port 8000)
   - Celery worker

## GraphRAG - Knowledge Graph Reasoning

TransIQ now includes GraphRAG (Graph-based Retrieval-Augmented Generation), an advanced system that builds and analyzes knowledge graphs from your documents.

**Key Capabilities:**
- Automatically deduplicate entities across documents (fuzzy matching at 85% threshold)
- Build a unified knowledge graph of entities and relationships
- Find indirect connections via multi-hop path finding (up to 10 hops)
- Analyze entity importance with centrality metrics (degree, closeness, betweenness)
- Detect anomalies and unusual patterns in the graph
- Understand impact of entities on the overall graph

**How It Works:**
When you process a document with deduction enabled, the system:
1. Extracts facts from the document using the deduction engine
2. Converts facts to entities and relationships
3. Resolves duplicate entities across documents
4. Stores in a knowledge graph with full relationship tracking
5. Periodically analyzes for quality, anomalies, and impact

**Getting Started with GraphRAG:**
- 📖 **[GRAPHRAG_USER_GUIDE.md](./GRAPHRAG_USER_GUIDE.md)** - Complete user guide with API examples
- 📑 **[GRAPHRAG_IMPLEMENTATION_PLAN.md](./GRAPHRAG_IMPLEMENTATION_PLAN.md)** - Architecture and design details
- 🔧 **[REST API Documentation](#graphrag-api-endpoints)** - All GraphRAG endpoints listed below

**Example Query:**
```bash
# Find entities related to "Apple Inc"
curl -X POST http://localhost:8000/api/v2/graph/entities/search \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Apple Inc",
    "entity_type": "ORGANIZATION",
    "limit": 10
  }'

# Find all paths between two entities (multi-hop reasoning)
curl -X POST http://localhost:8000/api/v2/graph/paths \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "source_entity_id": "entity-123",
    "target_entity_id": "entity-789",
    "max_depth": 5
  }'

# Get the most central entities in the graph
curl -X POST http://localhost:8000/api/v2/graph/analytics/centrality \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"metric": "degree", "limit": 10}'
```

## API Endpoints

### Document Processing

**POST** `/api/v2/generate`
- Upload and process a document
- Returns: `doc_id` and `task_id`

**Example:**
```bash
curl -X POST "http://localhost:8001/api/v2/generate" \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@document.txt" \
  -F "provider=gemini" \
  -F "enable_deduction=true"
```

### Search

**POST** `/api/v2/search`
- Search across processed documents
- Body: `{"query": "search text", "top_k": 10}`

**Example:**
```bash1/api/v2/search" \
  -H "X-API-Key: your-api-key-here
curl -X POST "http://localhost:8000/api/v2/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "profit margins", "top_k": 5}'
```

### Document Management

**GET** `/api/v2/documents/{doc_id}`
- Get document information

**GET** `/api/v2/documents/{doc_id}/chunks`
- Get document chunks

### WebSocket Progress

**WS** `/api/v2/ws/{task_id}`
- Real-time progress updates for document processing

**Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v2/ws/{task_id}');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data);
};
```

### GraphRAG API Endpoints

**Entity Search**
**POST** `/api/v2/graph/entities/search`
- Search for entities by name and type
- Body: `{"query": "entity name", "entity_type": "ORGANIZATION", "limit": 10}`

**Get Entity Profile**
**GET** `/api/v2/graph/entities/{entity_id}`
- Get full entity profile with relationships and statistics

**Relationship Search**
**POST** `/api/v2/graph/relationships/search`
- Search relationships by type
- Body: `{"query": "OWNS", "limit": 10}`

**Find Paths Between Entities**
**POST** `/api/v2/graph/paths`
- Find all paths connecting two entities (multi-hop reasoning)
- Body: `{"source_entity_id": "id1", "target_entity_id": "id2", "max_depth": 5}`

**Graph Centrality Analysis**
**POST** `/api/v2/graph/analytics/centrality`
- Get most central entities (hub nodes)
- Metrics: `degree`, `closeness`, `betweenness`

**Detect Anomalies**
**GET** `/api/v2/graph/analytics/anomalies`
- Detect unusual patterns and outliers in the graph

**Analyze Entity Impact**
**GET** `/api/v2/graph/analytics/impact/{entity_id}`
- Understand how important an entity is to the overall graph

**For complete GraphRAG documentation, see [GRAPHRAG_USER_GUIDE.md](./GRAPHRAG_USER_GUIDE.md)**

## Configuration

See `.env.example` for all configuration options. Key settings:

- **LLM Providers**: Set `GEMINI_API_KEY` and/or `OPENAI_API_KEY`
- **Redis**: Configure `REDIS_URL` for Celery
- **Storage**: Use SQLite (default) or Supabase
- **Feature Flags**: Enable/disable features via environment variables

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI REST API                      │
│  /documents, /search, /graph, /analytics endpoints      │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┴─────────────────────────┐
         │                                       │
    ┌────▼───────────────┐            ┌────────▼───────────┐
    │   Celery Workers   │            │  Request Serving   │
    └──────┬─────────────┘            └────────────────────┘
           │
           ├──► Document Processing Pipeline
           │    ├── Chunking (Adaptive/Hierarchical)
           │    ├── Embeddings (Multiple Models)
           │    ├── Deduction Engine (Fact Extraction)
           │    └── Pattern Recognition (Anomalies)
           │
           └──► GraphRAG Processing
                ├── Fact-to-Graph Conversion
                ├── Entity Resolution & Deduplication
                ├── Knowledge Graph Construction
                └── Graph Analytics & Maintenance
       
┌──────────────────────────────────────────────────────────┐
│              Persistent Storage Layer                     │
├────────────────┬──────────────┬────────────┬─────────────┤
│  SQLite        │  Redis       │  FAISS     │  Graph DB   │
│  (Documents,   │  (Cache,     │  (Vector   │  (Entities, │
│   Chunks,      │   Queue)     │   Index)   │   Relations)│
│   Deductions)  │              │            │             │
└──────────────────────────────────────────────────────────┘
```

**GraphRAG Layer Details:**
- Entity Resolver: Fuzzy matching and deduplication across documents
- Knowledge Graph Engine: CRUD operations on entities and relationships
- Graph Analytics: Path finding, centrality metrics, community detection
- Storage Coordinator: Integration between components

## Project Structure

```
app/
├── main.py              # FastAPI application
├── config/              # Configuration
├── api/v2/              # API endpoints
├── llm/                 # LLM providers
├── processors/          # Document processors
│   ├── chunker/        # Adaptive chunking
│   ├── deduction.py    # Deduction engine
│   └── patterns.py     # Pattern recognition
├── embeddings/          # Embedding models
├── storage/             # Storage backends
├── search/              # Search functionality
├── workers/             # Celery workers
└── websocket/           # WebSocket handlers
```

## Development

### Running Tests
```bash
# TODO: Add pytest tests
pytest tests/
```

### Code Formatting
```bash
# TODO: Add formatting tools
black app/
isort app/
```

## Production Deployment

1. Set `DEBUG=false` in `.env`
2. Configure proper CORS origins
3. Use production Redis instance
4. Set up Supabase for cloud storage (optional)
5. Configure proper logging
6. Set up monitoring and alerting

---

## Six Sigma Analysis API

### `POST /api/v2/six-sigma/analyze`

Deterministic process capability analysis. Zero LLM calls — all math uses the `transiq` library.

**Authentication:** Requires `X-API-Key` header (same as all `/api/*` endpoints).

#### Request Schema

```json
{
  "data": [2.1, 4.3, 4.0, 5.1, 5.0, 7.2, 9.0],
  "usl": 10.0,
  "lsl": 0.0,
  "sigma": null,
  "ppm": null
}
```

| Field   | Type            | Default | Description                                   |
|---------|-----------------|---------|-----------------------------------------------|
| `data`  | `float[]`       | —       | Process measurements (min 1 value, required)   |
| `usl`   | `float`         | `10.0`  | Upper specification limit                      |
| `lsl`   | `float`         | `0.0`   | Lower specification limit (must be < usl)      |
| `sigma` | `float \| null` | `null`  | Known std dev (auto-computed from data if null) |
| `ppm`   | `float \| null` | `null`  | Defects per million (triggers sigma_level calc) |

#### Response Schema (Locked Contract)

Every response returns the same six top-level keys:

```json
{
  "analysis_type": "process_capability",
  "inputs": {
    "n": 7, "usl": 10.0, "lsl": 0.0,
    "sigma_provided": null, "ppm_provided": null
  },
  "metrics": {
    "n": 7, "mean": 5.242857, "std_dev": 2.195476,
    "cp": 0.7589, "cpk": 0.7217, "cpu": 0.7217, "cpl": 0.7961,
    "sigma_short_term": 2.17, "sigma_long_term": 3.67,
    "dpmo": 24393.8, "yield_pct": 97.5606,
    "fraction_defective": 0.02439376, "sigma_level": null
  },
  "chart_data": {
    "values": [2.1, 4.3, 4.0, 5.1, 5.0, 7.2, 9.0],
    "cl": 5.242857, "ucl": 10.303, "lcl": 0.183,
    "mr_cl": 1.9, "mr_ucl": 6.207, "usl": 10.0, "lsl": 0.0
  },
  "warnings": [
    {"rule": "Rule 1", "description": "Point(s) outside ±3σ", "indices": [6], "severity": "critical"}
  ],
  "recommendations": [
    "Cpk=0.72 — process is not capable. Reduce variation or re-centre the process."
  ]
}
```

#### Example: curl

```bash
curl -X POST http://localhost:8001/api/v2/six-sigma/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"data":[2,4,4,4,5,5,7,9],"usl":10,"lsl":0}'
```

#### Example: Python

```python
import requests
resp = requests.post(
    "http://localhost:8001/api/v2/six-sigma/analyze",
    headers={"X-API-Key": "YOUR_KEY"},
    json={"data": [2, 4, 4, 4, 5, 5, 7, 9], "usl": 10, "lsl": 0, "ppm": 3.4},
)
result = resp.json()
print(f"Cpk={result['metrics']['cpk']}, σ={result['metrics']['sigma_level']}")
```

### `GET /api/v2/six-sigma/history?limit=20`

Returns the most recent saved analyses (persisted automatically on each POST).

---

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.

