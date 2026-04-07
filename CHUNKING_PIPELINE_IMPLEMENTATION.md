# Complete Chunking Pipeline Implementation Guide

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [Installation & Setup](#installation--setup)
5. [Configuration](#configuration)
6. [Deployment](#deployment)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Performance Optimization](#performance-optimization)
10. [Advanced Customization](#advanced-customization)

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         HTTP API Layer                          │
│  (/api/documents/upload, /api/documents/batch, etc.)           │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    Processing Layer                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ process_document() [Celery]                              │  │
│  │ process_document_sync() [Synchronous]                   │  │
│  │ _process_document_impl() [Core Implementation]          │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────▼───────────────────────────────┐  │
│  │          ChunkingPipeline Orchestrator                   │  │
│  │                                                          │  │
│  │  - Coordinates all pipeline stages                      │  │
│  │  - Manages caching layer                                │  │
│  │  - Collects performance metrics                         │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────┴───────────────────────────────┐  │
│  │                  Pipeline Stages                        │  │
│  │                                                        │  │
│  │  ┌─────────────────┐  ┌─────────────────┐           │  │
│  │  │   Chunking      │  │   Embedding     │           │  │
│  │  │   ┌─────────┐   │  │   ┌─────────┐   │           │  │
│  │  │   │Adaptive │   │  │   │ Sentence│   │           │  │
│  │  │   │Semantic │───┼──┼───│ Vectors │   │           │  │
│  │  │   │Hierarchic   │  │   │Embedder │   │           │  │
│  │  │   └─────────┘   │  │   └─────────┘   │           │  │
│  │  └─────────────────┘  └─────────────────┘           │  │
│  │                                                        │  │
│  │  ┌─────────────────┐  ┌─────────────────┐           │  │
│  │  │   Indexing      │  │   Caching       │           │  │
│  │  │   ┌─────────┐   │  │   ┌─────────┐   │           │  │
│  │  │   │  FAISS  │   │  │   │ In-Memory   │           │  │
│  │  │   │ Index   │───┼──┼───│ Redis   │   │           │  │
│  │  │   └─────────┘   │  │   └─────────┘   │           │  │
│  │  └─────────────────┘  └─────────────────┘           │  │
│  │                                                        │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────┬─────────────────────────────────────────┘
                 │
┌────────────────┴──────────────────────────────────────────┐
│          Storage & Indexing Layer                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ LocalStorage                                     │  │
│  │ ├─ Documents (Metadata)                         │  │
│  │ ├─ Chunks (Content)                             │  │
│  │ ├─ Embeddings (Vectors)                         │  │
│  │ ├─ Knowledge Graph (Facts/Edges)                │  │
│  │ └─ Task Status                                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Search Indices                                   │  │
│  │ ├─ FAISS (Vector Search)                        │  │
│  │ ├─ BM25 (Full-Text Search)                      │  │
│  │ └─ Graph Index (Relationship Search)            │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                      │
┌─────────────────────┴──────────────────────────────────┐
│      External Services Integration                    │
│  ┌─────────────────────────────────────────────────┐ │
│  │ Embedding APIs                                  │ │
│  │ ├─ OpenAI Embeddings                           │ │
│  │ ├─ HuggingFace Embeddings                       │ │
│  │ └─ Local Embeddings                            │ │
│  └─────────────────────────────────────────────────┘ │
│                                                      │
│  ┌─────────────────────────────────────────────────┐ │
│  │ LLM Services                                    │ │
│  │ ├─ Deduction Engine                            │ │
│  │ ├─ GraphRAG Integration                        │ │
│  │ └─ Pattern Recognition                         │ │
│  └─────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

## Core Components

### 1. ChunkingPipeline (Orchestrator)

**File**: `app/processors/pipeline.py`

```python
class ChunkingPipeline:
    """Main orchestrator for document processing pipeline"""
    
    def __init__(
        self,
        strategy: str = 'adaptive',      # Chunking strategy
        max_embed_chunks: int = 400,     # Embedding cap
        enable_metrics: bool = True      # Performance tracking
    )
    
    def process(
        self,
        text: str,                       # Input text
        doc_id: str,                     # Document identifier
        doc_path: str,                   # File path
        storage: LocalStorage,           # Storage backend
        enable_caching: bool = True      # Cache chunks
    ) -> dict:
        """Execute full pipeline: chunk → embed → index → save"""
```

**Key Methods**:
- `process()` - Main entry point
- `_chunk_document()` - Applies selected strategy
- `_generate_embeddings()` - Creates vectors
- `_build_search_index()` - Indexes for retrieval
- `_save_to_storage()` - Persists data

### 2. Chunking Strategies

#### Adaptive Chunker
**File**: `app/processors/chunker/adaptive.py`

```python
class AdaptiveChunker(BaseChunker):
    """Dynamic chunk sizing based on content analysis"""
    
    # Features:
    # - Analyzes document structure
    # - Adjusts chunk size dynamically
    # - Handles mixed content types
    # - Fast execution
```

**Config**:
```python
ADAPTIVE_CONFIG = {
    'min_chunk_size': 64,        # Minimum tokens
    'max_chunk_size': 1024,      # Maximum tokens
    'target_chunk_size': 512,    # Ideal size
    'overlap_percent': 10,       # Overlap between chunks
}
```

#### Semantic Chunker
**File**: `app/processors/chunker/semantic.py`

```python
class SemanticChunker(BaseChunker):
    """Content-aware chunking using sentence embeddings"""
    
    # Features:
    # - Analyzes semantic similarity
    # - Creates conceptually coherent chunks
    # - High quality chunks
    # - Slower but better for semantic search
```

#### Hierarchical Chunker
**File**: `app/processors/chunker/hierarchical.py`

```python
class HierarchicalChunker(BaseChunker):
    """Maintains document structure in chunks"""
    
    # Features:
    # - Preserves sections/hierarchy
    # - Multi-level chunk relationships
    # - Excellent for structured documents
    # - Medium speed, high quality
```

### 3. Embedding Model

**File**: `app/embeddings/models.py`

```python
class EmbeddingModel:
    """Generates vector embeddings for chunks"""
    
    def embed(
        self,
        texts: List[str],
        show_progress: bool = True
    ) -> np.ndarray:
        """Generate embeddings for list of texts"""
```

**Supported Providers**:
- OpenAI (ada-002)
- HuggingFace (sentence-transformers)
- Local (CPU-based)

### 4. Search Indexing

**File**: `app/search/semantic.py`

```python
class FaissIndex:
    """FAISS-based vector search index"""
    
    def add(
        self,
        vectors: np.ndarray,
        chunk_ids: List[str]
    ) -> None:
        """Add vectors to search index"""
    
    def search(
        self,
        query_vector: np.ndarray,
        k: int = 5
    ) -> List[Tuple[str, float]]:
        """Search for similar chunks"""
```

### 5. Storage Backend

**File**: `app/storage/local.py`

```python
class LocalStorage:
    """Document and chunk storage management"""
    
    def save_document(self, doc_id: str, metadata: dict) -> None
    def save_chunk(self, chunk_id: str, doc_id: str, text: str, metadata: dict) -> None
    def save_edges(self, edge_id: str, doc_id: str, edge_data: dict) -> None
    def get_document(self, doc_id: str) -> dict
    def get_chunks(self, doc_id: str) -> List[dict]
```

## Data Flow

### Document Upload to Query

```
1. UPLOAD
   └─> File → LocalStorage → Trigger Processing
       
2. PROCESSING
   ├─> Read File
   │   └─> Extract Text (handle PDFs, Word, etc.)
   │
   ├─> Chunking Pipeline
   │   ├─> Apply Strategy (Adaptive/Semantic/Hierarchical)
   │   ├─> Generate Chunks with Metadata
   │   └─> Optimize Chunk Count
   │
   ├─> Embeddings
   │   ├─> Generate Vectors (via API or local model)
   │   ├─> Cache Results
   │   └─> Handle Rate Limits
   │
   ├─> Indexing
   │   ├─> Build FAISS Index
   │   ├─> Store Vector References
   │   └─> Enable Fast Retrieval
   │
   └─> Storage
       ├─> Save Chunks
       ├─> Save Document Metadata
       ├─> Save Task Status
       └─> Update Search Indices

3. QUERY
   ├─> Generate Query Embedding
   ├─> Search FAISS Index
   ├─> Retrieve Top-K Chunks
   ├─> Rank Results
   └─> Return to User

4. ANALYSIS
   ├─> Deduction Engine (optional)
   ├─> Knowledge Graph Building
   ├─> Pattern Recognition
   └─> Dashboard Generation
```

### Pipeline Execution Flow

```python
# 1. Initialize
pipeline = ChunkingPipeline(strategy='adaptive')

# 2. Read Document
text = read_file(doc_path)

# 3. Execute Pipeline
result = pipeline.process(
    text=text,
    doc_id=doc_id,
    storage=storage,
    enable_caching=True
)

# 4. Pipeline Steps (Internal)
# a. Chunk document
#    → chunks_data = chunker.chunk_with_metadata(text)
#    → chunks = [c['text'] for c in chunks_data]
#
# b. Generate embeddings
#    → embeddings = emb_model.embed(chunks)
#
# c. Build index
#    → faiss_index = FaissIndex()
#    → faiss_index.add(embeddings, chunk_ids)
#
# d. Save results
#    → storage.save_chunk(chunk_id, doc_id, text, metadata)
#    → storage.save_document(doc_id, doc_metadata)

# 5. Return results
return result  # Contains chunks_count, embeddings_count, metrics
```

## Installation & Setup

### Prerequisites

```bash
# Python 3.10+
python --version

# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Additional for chunking pipeline
pip install faiss-cpu        # or faiss-gpu for GPU support
pip install sentence-transformers
pip install openai          # For OpenAI embeddings (optional)
pip install scikit-learn    # For clustering algorithms
```

### Initialize Models

```python
# models/embeddings.py
from app.embeddings.models import EmbeddingModel

# Download embedding model (first run)
model = EmbeddingModel()
# This downloads the model to ~/.cache

# Test embedding
test_embedding = model.embed(["Hello world"])
print(f"Embedding shape: {test_embedding.shape}")  # Should be (1, 384) or similar
```

## Configuration

### Global Settings

Edit `app/config/settings.py`:

```python
# Chunking Configuration
CHUNKING_STRATEGY = "adaptive"  # Default strategy
CHUNKING_MIN_CHUNK_SIZE = 64    # Minimum tokens
CHUNKING_MAX_CHUNK_SIZE = 1024  # Maximum tokens
CHUNKING_OVERLAP = 200          # Overlap percentage

# Embedding Configuration
EMBEDDING_PROVIDER = "openai"   # "openai", "huggingface", "local"
EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_DIMENSION = 1536
EMBEDDING_MAX_RETRIES = 3
EMBEDDING_BATCH_SIZE = 100

# Indexing Configuration
INDEXING_TYPE = "faiss"         # "faiss" only for now
MAX_EMBED_CHUNKS = 400          # Max chunks to embed
FAISS_INDEX_PATH = "data/faiss_index"

# Cache Configuration
ENABLE_CHUNK_CACHE = True
CACHE_TTL_HOURS = 24
CACHE_MAX_SIZE_GB = 10

# Processing Configuration
MAX_TEXT_CHARS = 600_000        # Hard cap for document size
PROCESSING_TIMEOUT_SECONDS = 300
ENABLE_METRICS = True           # Collect performance metrics
```

### Per-Document Configuration

```python
# Override settings per document
result = process_document_sync(
    doc_path="document.pdf",
    doc_id="doc_123",
    # Override global settings for this document
    chunking_strategy="semantic",  # Use semantic instead of default
)
```

### Environment Variables

```bash
# .env file
CHUNKING_STRATEGY=adaptive
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379/0
```

## Deployment

### Single Machine (Development)

```bash
# Terminal 1: Redis server
redis-server

# Terminal 2: Celery worker
celery -A app.workers.processor worker --loglevel=info

# Terminal 3: FastAPI application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.10

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ app/
COPY config/ config/

# Download embedding models on build
RUN python -c "from app.embeddings.models import EmbeddingModel; EmbeddingModel()"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build
docker build -t transiq:latest .

# Run with dependencies
docker-compose up
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"

  celery:
    build: .
    command: celery -A app.workers.processor worker --loglevel=info
    depends_on:
      - redis
    environment:
      REDIS_URL: redis://redis:6379

  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - celery
    environment:
      REDIS_URL: redis://redis:6379
      CELERY_BROKER_URL: redis://redis:6379/0
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: transiq-processor
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: processor
        image: transiq:latest
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        env:
        - name: CHUNKING_STRATEGY
          value: "adaptive"
        - name: REDIS_URL
          value: "redis://redis:6379"
```

## Monitoring

### Logging Configuration

```python
# logging.conf
[loggers]
keys=root,app,pipeline,embedding

[logger_pipeline]
level=INFO
handlers=consoleHandler,fileHandler
qualname=app.processors.pipeline

[logger_embedding]
level=DEBUG
handlers=consoleHandler,fileHandler
qualname=app.embeddings
```

### Key Metrics to Monitor

```python
# Check pipeline performance
result = process_document_sync("doc.pdf", "doc_123")

metrics = result.get('metrics', {})
print(f"Chunking: {metrics['chunking_time_ms']}ms")
print(f"Embedding: {metrics['embedding_time_ms']}ms")
print(f"Indexing: {metrics['indexing_time_ms']}ms")
print(f"Total: {metrics['total_time_ms']}ms")
print(f"Cache hit: {metrics.get('cache_hit', False)}")
```

### Redis Monitoring

```bash
# Monitor pub/sub events
redis-cli
> SUBSCRIBE doc:*
# Watch for progress events as documents process
```

### Database Queries

```python
# Check document processing status
storage = LocalStorage()
doc = storage.get_document("doc_123")
print(doc['status'])           # completed, processing, failed
print(doc['chunks_count'])     # Number of chunks
print(doc['pipeline_metrics']) # Performance data
```

## Troubleshooting

### Issue: No Chunks Created

```python
# Debug: Check chunker output
from app.processors.chunker.adaptive import AdaptiveChunker

chunker = AdaptiveChunker()
chunks = chunker.chunk_with_metadata("Sample text")
print(f"Chunks created: {len(chunks)}")

# If 0:
# - Text might be too short
# - Min chunk size might be too large
# - Text encoding issues
```

### Issue: Embedding API Rate Limit

```python
# Solution: Use local embeddings
EMBEDDING_PROVIDER = "local"  # Use sentence-transformers

# Or: Implement retry logic
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
def embed_with_retry(texts):
    return embedding_model.embed(texts)
```

### Issue: FAISS Index Not Working

```python
# Check FAISS installation
import faiss
print(f"FAISS version: {faiss.__version__}")

# Verify GPU support (if enabled)
print(f"GPU available: {faiss.get_num_gpus()}")

# Rebuild index
faiss_index = FaissIndex()
# Reindex all documents
```

### Issue: Out of Memory

```python
# Reduce batch size
EMBEDDING_BATCH_SIZE = 10  # Down from 100

# Reduce max chunks
MAX_EMBED_CHUNKS = 200  # Down from 400

# Use sampling
step = len(chunks) // MAX_EMBED_CHUNKS
chunks_sampled = chunks[::step][:MAX_EMBED_CHUNKS]
```

### Issue: Slow Processing

```python
# 1. Check chunking strategy
# Semantic: 3890ms
# Hierarchical: 2100ms
# Adaptive: 2450ms

# 2. Check embedding provider
# OpenAI API: 2300ms
# Local model: 800ms

# 3. Enable caching to avoid re-processing
enable_caching=True

# 4. Reduce max_embed_chunks
max_embed_chunks=200
```

## Performance Optimization

### Strategy Selection Guide

| Strategy | Speed | Quality | Best For |
|----------|-------|---------|----------|
| **Adaptive** | Fast | Good | Most documents |
| **Semantic** | Slow | Excellent | Legal, technical |
| **Hierarchical** | Med | Good | Structured docs |

### Caching Strategy

```python
# Enable for repeated documents
pipeline_result = pipeline.process(
    text=text,
    doc_id=doc_id,
    enable_caching=True  # Cache chunks
)

# Check cache hit
metrics = pipeline_result['metrics']
print(f"Cache hit: {metrics['cache_hit']}")
# First run: false
# Repeated runs: true (much faster)
```

### Batch Processing

```python
# Process multiple documents efficiently
from celery import group

# Create group of tasks
job = group([
    process_document.s(f"doc{i}.pdf", f"doc_{i}")
    for i in range(100)
])

# Execute in parallel
results = job.apply_async()

# Wait for completion
for result in results.get():
    print(f"Chunks: {result['chunks']}")
```

### Resource Allocation

```python
# Adjust based on hardware
# 8GB RAM:
MAX_EMBED_CHUNKS = 200
EMBEDDING_BATCH_SIZE = 20

# 16GB RAM:
MAX_EMBED_CHUNKS = 400
EMBEDDING_BATCH_SIZE = 50

# 32GB+ RAM:
MAX_EMBED_CHUNKS = 800
EMBEDDING_BATCH_SIZE = 100
```

## Advanced Customization

### Custom Chunking Strategy

```python
from app.processors.chunker.base import BaseChunker

class CustomChunker(BaseChunker):
    """Implement your own chunking logic"""
    
    def chunk_with_metadata(self, text: str):
        # Custom logic here
        chunks = self._custom_chunk_algorithm(text)
        
        # Return with metadata
        return [
            {
                'text': chunk,
                'start_idx': start,
                'end_idx': end,
                'metadata': {}
            }
            for chunk, start, end in chunks
        ]

# Use custom chunker
class CustomPipeline(ChunkingPipeline):
    def __init__(self):
        super().__init__()
        self.chunker = CustomChunker()
```

### Custom Embedding Model

```python
from app.embeddings.base import BaseEmbeddingModel

class CustomEmbeddingModel(BaseEmbeddingModel):
    """Implement custom embedding logic"""
    
    def embed(self, texts: List[str]) -> np.ndarray:
        # Your embedding logic
        embeddings = [self._generate_embedding(text) for text in texts]
        return np.array(embeddings)

# Register in settings
EMBEDDING_PROVIDER = "custom"
CUSTOM_EMBEDDING_CLASS = "CustomEmbeddingModel"
```

### Custom Post-Processing

```python
def post_process_chunks(chunks, doc_id):
    """Add custom processing after chunking"""
    
    # Example: Add sentiment analysis
    for chunk in chunks:
        sentiment = analyze_sentiment(chunk['text'])
        chunk['metadata']['sentiment'] = sentiment
    
    # Example: Add entity extraction
    for chunk in chunks:
        entities = extract_entities(chunk['text'])
        chunk['metadata']['entities'] = entities
    
    return chunks

# Integrate with pipeline
class CustomPipeline(ChunkingPipeline):
    def process(self, **kwargs):
        result = super().process(**kwargs)
        result['chunks_data'] = post_process_chunks(
            result['chunks_data'],
            kwargs['doc_id']
        )
        return result
```

## Summary

The ChunkingPipeline system provides:

✅ **Flexibility** - Multiple strategies, custom implementations
✅ **Performance** - Caching, metrics, optimization
✅ **Reliability** - Error handling, retry logic
✅ **Observability** - Detailed metrics and logging
✅ **Scalability** - Distributed processing with Celery
✅ **Integration** - Works with existing systems

For questions or issues, refer to:
- [API Examples](/CHUNKING_PIPELINE_API_EXAMPLES.md)
- [Integration Guide](/CHUNKING_PIPELINE_INTEGRATION.md)
- Source code: `app/processors/pipeline.py`
