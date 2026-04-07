# Chunking Pipeline Integration Guide

## Overview

The **ChunkingPipeline** system has been integrated into the TransIQ document processing workflow, replacing the previous ad-hoc chunking, embedding, and indexing approach with a unified, modular system.

## Architecture

### Previous System (Pre-Integration)
```
Document → Read → Manual Chunking → Manual Embedding → Manual Indexing → Search
```

### New System (Post-Integration)
```
Document → Read → ChunkingPipeline {
    ├─ Chunking (Adaptive/Semantic/Hierarchical)
    ├─ Embedding (Automatic)
    ├─ Indexing (Automatic)
    ├─ Caching (Performance)
    └─ Metrics (Observability)
} → Search
```

## Integration Points

### 1. **Celery Task: `process_document` (Distributed Processing)**

**Location**: [app/workers/processor.py](app/workers/processor.py#L140)

The Celery task now uses the ChunkingPipeline:

```python
from app.processors.pipeline import ChunkingPipeline

# Initialize pipeline with adaptive chunking strategy
pipeline = ChunkingPipeline(
    strategy='adaptive',           # Strategy: adaptive, semantic, hierarchical
    max_embed_chunks=400,          # Cap for embedding model
    enable_metrics=True            # Collect performance metrics
)

# Execute: chunk → embed → index → save (all in one call)
pipeline_result = pipeline.process(
    text=text,
    doc_id=doc_id,
    doc_path=doc_path,
    storage=storage,
    enable_caching=True
)
```

**Key Benefits**:
- Single unified call replaces 5+ steps
- Automatic chunk size optimization
- Integrated caching for repeated documents
- Performance metrics collected automatically
- Progress tracking via Redis Pub/Sub

### 2. **Synchronous Implementation: `_process_document_impl()`**

**Location**: [app/workers/processor.py](app/workers/processor.py#L270)

Same pipeline approach for non-Celery/non-distributed processing:

```python
pipeline = ChunkingPipeline(
    strategy='adaptive',
    max_embed_chunks=400,
    enable_metrics=True
)

pipeline_result = pipeline.process(
    text=text,
    doc_id=doc_id,
    doc_path=doc_path,
    storage=storage,
    enable_caching=True
)
```

**Callback Support**:
```python
# Optional progress callback for real-time updates
if progress_callback:
    progress_callback('PROCESSING', {'step': 'chunking'})
```

### 3. **Fallback Processing: `process_document_sync()`**

**Location**: [app/workers/processor.py](app/workers/processor.py#L445)

Supports strategy selection:

```python
def process_document_sync(
    doc_path: str,
    doc_id: str,
    provider_name: str = None,
    chunking_strategy: str = "adaptive",  # NEW: Strategy support
    # ... other parameters
):
    pipeline = ChunkingPipeline(
        strategy=chunking_strategy,
        max_embed_chunks=400,
        enable_metrics=True
    )
```

## Pipeline Results

All pipeline implementations return consistent metadata:

```json
{
    "chunks_data": [...],           // Raw chunk data with metadata
    "chunks_count": 234,             // Total chunks created
    "embeddings_count": 45,          // Embeddings generated (may be sampled)
    "metrics": {                     // Performance metrics
        "chunking_time_ms": 150,
        "embedding_time_ms": 2300,
        "indexing_time_ms": 450,
        "total_time_ms": 2900,
        "cache_hit": false,
        "avg_chunk_size": 512
    }
}
```

## Document Metadata Updates

Documents now store additional pipeline data:

```python
doc_metadata = {
    "status": "completed",
    "chunks_count": 234,              # NEW: From pipeline
    "embeddings_count": 45,           # NEW: From pipeline
    "facts_count": 12,
    "has_knowledge_graph": true,
    "file_name": "document.pdf",
    "chunking_strategy": "adaptive",  # NEW: Strategy used
    "pipeline_metrics": {...}         # NEW: Performance data
}
```

## Chunking Strategies

The pipeline supports three strategies:

### 1. **Adaptive Chunking** (Default)
```python
ChunkingPipeline(strategy='adaptive')
```
- Dynamic chunk size based on document structure
- Optimizes for semantic boundaries
- Best for diverse document types
- **Use Case**: General purpose, mixed content

### 2. **Semantic Chunking**
```python
ChunkingPipeline(strategy='semantic')
```
- Uses sentence-level embeddings to find natural breaks
- Higher quality chunks
- Slower, more compute-intensive
- **Use Case**: Legal documents, technical papers

### 3. **Hierarchical Chunking**
```python
ChunkingPipeline(strategy='hierarchical')
```
- Multi-level chunking (sections → paragraphs → sentences)
- Maintains document structure
- Excellent for structured documents
- **Use Case**: Manuals, reports, textbooks

## Performance Metrics

The pipeline collects detailed metrics:

```json
{
    "chunking_time_ms": 150,      // Time to chunk document
    "embedding_time_ms": 2300,    // Time to generate embeddings
    "indexing_time_ms": 450,      // Time to build vector index
    "total_time_ms": 2900,        // Total pipeline time
    "cache_hit": false,            // Cache hit/miss
    "avg_chunk_size": 512,         // Average chunk size
    "min_chunk_size": 128,         // Minimum chunk size
    "max_chunk_size": 1024,        // Maximum chunk size
    "chunks_per_second": 156       // Throughput
}
```

Access via API:
```python
result = process_document(doc_path, doc_id)
# result['metrics'] contains all performance data
```

## Configuration

### Global Settings

Edit [app/config/settings.py](app/config/settings.py):

```python
# Default chunking strategy
CHUNKING_STRATEGY = "adaptive"  # or "semantic", "hierarchical"

# Maximum chunk size (tokens)
CHUNKING_MAX_CHUNK_SIZE = 1024

# Minimum chunk size (tokens)
CHUNKING_MIN_CHUNK_SIZE = 64

# Overlap between chunks (tokens)
CHUNKING_OVERLAP = 200

# Maximum embeddings to generate
CHUNKING_MAX_EMBED_CHUNKS = 400

# Enable caching
CHUNKING_ENABLE_CACHE = True
```

### Per-Document Override

```python
# Override strategy for specific documents
result = process_document_sync(
    doc_path="document.pdf",
    doc_id="doc_123",
    chunking_strategy="semantic"  # Use semantic for this document
)
```

## Backward Compatibility

**✅ Fully backward compatible** - All existing code continues to work:

```python
# Old API still works
result = process_document(doc_path, doc_id)

# Returns same result structure
# + additional metrics and strategy fields
```

## Migration Checklist

If upgrading existing deployments:

- [x] Update imports (remove `AdaptiveChunker`, `EmbeddingModel`, `FaissIndex` from processor.py)
- [x] Update processor.py with new pipeline calls
- [x] Test with Celery enabled
- [x] Test with Celery disabled (synchronous mode)
- [x] Verify document metadata includes new fields
- [x] Monitor metrics in logs
- [x] Update API response handlers if needed

## Troubleshooting

### Issue: Pipeline fails silently
**Solution**: Check logs for pipeline initialization errors
```bash
grep "ChunkingPipeline" logs/*.log
```

### Issue: Too many chunks created
**Solution**: Adjust max_embed_chunks or use semantic strategy
```python
pipeline = ChunkingPipeline(
    strategy='semantic',      # Fewer, higher-quality chunks
    max_embed_chunks=200      # Reduce cap
)
```

### Issue: Embeddings take too long
**Solution**: Reduce max_embed_chunks or sample chunks
```python
pipeline = ChunkingPipeline(
    max_embed_chunks=100  # Embed fewer chunks
)
```

### Issue: Out of memory on large documents
**Solution**: ProcessorReducer automatically truncates to 600K chars
- Already handled in processor.py
- Check MAX_TEXT_CHARS constant if needed

## API Endpoints Affected

The following API endpoints now return enhanced metadata:

- `POST /api/documents/upload` - Returns pipeline metrics
- `GET /api/documents/{doc_id}` - Includes chunking_strategy
- `GET /api/documents/{doc_id}/chunks` - Returns chunk metadata
- `POST /api/documents/batch` - Tracks chunking per document

## Testing

### Test Synchronous Processing
```python
from app.workers.processor import process_document_sync

result = process_document_sync(
    doc_path="test_document.pdf",
    doc_id="test_123",
    chunking_strategy="adaptive"
)

print(f"Chunks: {result['chunks']}")
print(f"Metrics: {result['metrics']}")
```

### Test Celery Processing
```python
from app.workers.processor import process_document

task = process_document.delay(
    doc_path="test_document.pdf",
    doc_id="test_123"
)

result = task.get()
print(f"Chunks: {result['chunks']}")
print(f"Metrics: {result['metrics']}")
```

### Test Strategy Comparison
```python
for strategy in ['adaptive', 'semantic', 'hierarchical']:
    result = process_document_sync(
        doc_path="document.pdf",
        doc_id=f"test_{strategy}",
        chunking_strategy=strategy
    )
    print(f"{strategy}: {result['chunks']} chunks, "
          f"{result['metrics']['total_time_ms']}ms")
```

## Monitoring

### Log Statements
The pipeline logs key events:
```
✓ [Task xyz] Initializing chunking pipeline
✓ [Task xyz] Executing chunking pipeline
✓ Pipeline results: 234 chunks, 45 embeddings
✓ Pipeline metrics: {...}
✓ Document xyz processed successfully
```

### Redis Pub/Sub Progress
Real-time progress via [_publish_progress()](app/workers/processor.py#L75):
```json
{
    "doc_id": "doc_123",
    "stage": "chunking",
    "progress": 20,
    "message": "Breaking document into chunks"
}
```

### Document Metadata
Query completed documents:
```python
storage = LocalStorage()
doc = storage.get_document("doc_123")
print(doc['pipeline_metrics'])  # Performance data
print(doc['chunking_strategy'])  # Strategy used
```

## Future Enhancements

Planned improvements:

1. **Multi-strategy comparison**: Auto-select best strategy per document
2. **Adaptive sampling**: Intelligently select chunks to embed
3. **Streaming embeddings**: Process chunks as they're created
4. **Distributed embedding**: Scale to multiple GPU nodes
5. **Plugin system**: Allow custom chunking strategies
6. **Cost tracking**: Monitor embedding API costs

## References

- [ChunkingPipeline Source](app/processors/pipeline.py)
- [Adaptive Chunker](app/processors/chunker/adaptive.py)
- [Semantic Chunker](app/processors/chunker/semantic.py)
- [Hierarchical Chunker](app/processors/chunker/hierarchical.py)
- [LocalStorage API](app/storage/local.py)
- [Embedding Model](app/embeddings/models.py)

## Support

For issues or questions:
1. Check logs: `tail -f logs/app.log | grep -i chunking`
2. Test pipeline directly: See "Testing" section above
3. Review metrics: Check document metadata for pipeline_metrics
4. Check this guide: You're reading it!
