# Chunking Pipeline API Integration Examples

## Overview

This guide shows how to use the new ChunkingPipeline system through the TransIQ API.

## Direct Python API

### Simple Document Processing

```python
from app.workers.processor import process_document_sync

# Basic usage - uses default adaptive chunking
result = process_document_sync(
    doc_path="reports/Q4_2024.pdf",
    doc_id="report_q4_2024"
)

print(f"✓ Document processed")
print(f"  - Chunks created: {result['chunks']}")
print(f"  - Embeddings generated: {result['embeddings']}")
print(f"  - Processing time: {result['metrics']['total_time_ms']}ms")
```

**Output**:
```
✓ Document processed
  - Chunks created: 156
  - Embeddings generated: 98
  - Processing time: 2450ms
```

### Strategy Selection

```python
# Choose chunking strategy
for strategy in ['adaptive', 'semantic', 'hierarchical']:
    result = process_document_sync(
        doc_path="manual.pdf",
        doc_id=f"manual_{strategy}",
        chunking_strategy=strategy
    )
    
    print(f"{strategy:15} | Chunks: {result['chunks']:3} | Time: {result['metrics']['total_time_ms']:4}ms")
```

**Output**:
```
adaptive        | Chunks: 156 | Time: 2450ms
semantic        | Chunks: 142 | Time: 3890ms
hierarchical    | Chunks: 178 | Time: 2100ms
```

### With Deduction Engine

```python
# Enable deduction/knowledge graph extraction
result = process_document_sync(
    doc_path="contract.pdf",
    doc_id="contract_2024",
    enable_deduction=True,  # Run deduction engine
    chunking_strategy="semantic"  # Better for structured data
)

print(f"Chunks: {result['chunks']}")
print(f"Facts extracted: {result['facts']}")
print(f"Knowledge graph: {result['has_knowledge_graph']}")
```

### With Progress Callback

```python
def progress_callback(status, data):
    """Called during processing to track progress"""
    step = data.get('step', 'unknown')
    print(f"[{status}] {step}")

result = process_document_sync(
    doc_path="document.pdf",
    doc_id="doc_123",
    progress_callback=progress_callback
)
```

**Output**:
```
[PROCESSING] reading_file
[PROCESSING] chunking
[PROCESSING] embedding
[PROCESSING] saving_chunks
[PROCESSING] indexing
✓ Processing complete
```

## HTTP API Integration

### Upload Document with Chunking Strategy

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@document.pdf" \
  -F "strategy=semantic" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "doc_id": "doc_abc123",
  "status": "completed",
  "chunks": 156,
  "embeddings": 89,
  "chunking_strategy": "semantic",
  "metrics": {
    "total_time_ms": 3450,
    "embedding_time_ms": 2800,
    "chunking_time_ms": 650
  }
}
```

### Batch Processing with Strategy

```bash
curl -X POST http://localhost:8000/api/documents/batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "documents": [
      {"path": "doc1.pdf", "strategy": "adaptive"},
      {"path": "doc2.pdf", "strategy": "semantic"},
      {"path": "doc3.pdf", "strategy": "hierarchical"}
    ],
    "enable_deduction": true
  }'
```

### Get Document with Pipeline Data

```bash
curl http://localhost:8000/api/documents/doc_123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response** (excerpt):
```json
{
  "doc_id": "doc_123",
  "filename": "document.pdf",
  "chunks_count": 156,
  "embeddings_count": 98,
  "chunking_strategy": "adaptive",
  "pipeline_metrics": {
    "chunking_time_ms": 450,
    "embedding_time_ms": 2300,
    "indexing_time_ms": 150,
    "total_time_ms": 2900,
    "avg_chunk_size": 512
  }
}
```

## Celery Task Integration

### Queue Document Processing

```python
from app.workers.processor import process_document

# Queue task with Celery
task = process_document.delay(
    doc_path="large_document.pdf",
    doc_id="doc_xyz",
    provider_name="openai",
    enable_deduction=False
)

print(f"Task queued: {task.id}")

# Check status
print(f"Status: {task.status}")

# Get result when ready
result = task.get(timeout=300)  # 5 minute timeout
print(f"Chunks: {result['chunks']}")
```

### Monitor Progress

```python
import time
from celery.result import AsyncResult

task_id = "abc123def456"
task = AsyncResult(task_id)

while not task.ready():
    # Check if progress info is available
    info = task.info
    if isinstance(info, dict) and 'status' in info:
        print(f"Progress: {info.get('progress', 0)}%")
        print(f"Stage: {info.get('stage', 'unknown')}")
    time.sleep(1)

print(f"✓ Task complete: {task.result}")
```

### Chain Multiple Documents

```python
from celery import chain

# Process multiple documents in sequence
workflow = chain([
    process_document.s("doc1.pdf", "doc_1"),
    process_document.s("doc2.pdf", "doc_2"),
    process_document.s("doc3.pdf", "doc_3"),
])

result = workflow.apply_async()
print(f"Workflow queued: {result}")
```

## Advanced Examples

### Comparing Strategies

```python
from app.workers.processor import process_document_sync
import time

document = "financial_report.pdf"
strategies = ['adaptive', 'semantic', 'hierarchical']

results = {}
for strategy in strategies:
    start = time.time()
    result = process_document_sync(
        doc_path=document,
        doc_id=f"comparison_{strategy}",
        chunking_strategy=strategy
    )
    elapsed = time.time() - start
    
    results[strategy] = {
        'chunks': result['chunks'],
        'embeddings': result['embeddings'],
        'time_ms': result['metrics']['total_time_ms'],
        'avg_chunk_size': result['metrics']['avg_chunk_size']
    }

# Print comparison
print("Strategy Comparison:")
print("-" * 60)
print(f"{'Strategy':<15} {'Chunks':<10} {'Embeddings':<12} {'Time (ms)':<10}")
print("-" * 60)
for strategy, data in results.items():
    print(f"{strategy:<15} {data['chunks']:<10} {data['embeddings']:<12} {data['time_ms']:<10}")
```

**Output**:
```
Strategy Comparison:
------------------------------------------------------------
Strategy        Chunks     Embeddings   Time (ms) 
------------------------------------------------------------
adaptive        156        89           2450     
semantic        142        85           3890     
hierarchical    178        95           2100     
```

### Custom Processing Pipeline

```python
from app.processors.pipeline import ChunkingPipeline
from app.storage.local import LocalStorage

def process_with_cache(doc_path, doc_id):
    """Process document with caching enabled"""
    
    pipeline = ChunkingPipeline(
        strategy='semantic',
        max_embed_chunks=200,
        enable_metrics=True
    )
    
    storage = LocalStorage()
    
    # Read document
    with open(doc_path, 'r') as f:
        text = f.read()
    
    # Hard cap size
    if len(text) > 600_000:
        text = text[:600_000]
    
    # Execute pipeline with caching
    result = pipeline.process(
        text=text,
        doc_id=doc_id,
        doc_path=doc_path,
        storage=storage,
        enable_caching=True  # Enable caching
    )
    
    return result

# First run - will cache
result1 = process_with_cache("report.pdf", "report_v1")
print(f"First run: {result1['metrics']['total_time_ms']}ms")

# Second run - faster due to cache
result2 = process_with_cache("report.pdf", "report_v1") 
print(f"Cached run: {result2['metrics']['total_time_ms']}ms")
```

### Process and Analyze

```python
from app.workers.processor import process_document_sync
from app.storage.local import LocalStorage

def analyze_document(doc_path, doc_id):
    """Process and analyze document"""
    
    # Process with semantic chunking
    result = process_document_sync(
        doc_path=doc_path,
        doc_id=doc_id,
        chunking_strategy="semantic",
        enable_deduction=True
    )
    
    # Get details from storage
    storage = LocalStorage()
    doc = storage.get_document(doc_id)
    chunks = storage.get_chunks(doc_id)
    
    # Print analysis
    print(f"Document Analysis: {doc_id}")
    print(f"=" * 60)
    print(f"File: {doc['file_name']}")
    print(f"Status: {doc['status']}")
    print(f"")
    print(f"Chunking:")
    print(f"  - Strategy: {doc['chunking_strategy']}")
    print(f"  - Total chunks: {len(chunks)}")
    print(f"  - Embeddings: {doc['embeddings_count']}")
    print(f"")
    print(f"Content Analysis:")
    print(f"  - Facts extracted: {doc.get('facts_count', 0)}")
    print(f"  - Has knowledge graph: {doc.get('has_knowledge_graph', False)}")
    print(f"")
    print(f"Performance:")
    metrics = doc.get('pipeline_metrics', {})
    print(f"  - Total time: {metrics.get('total_time_ms', 0)}ms")
    print(f"  - Avg chunk size: {metrics.get('avg_chunk_size', 0)} tokens")
    print(f"")
    print(f"Chunks Preview:")
    for i, chunk in enumerate(chunks[:3]):
        preview = chunk['text'][:60] + "..."
        print(f"  [{i+1}] {preview}")
    if len(chunks) > 3:
        print(f"  ... and {len(chunks) - 3} more chunks")

# Usage
analyze_document("report.pdf", "report_001")
```

**Output**:
```
Document Analysis: report_001
============================================================
File: report.pdf
Status: completed

Chunking:
  - Strategy: semantic
  - Total chunks: 156
  - Embeddings: 89

Content Analysis:
  - Facts extracted: 12
  - Has knowledge graph: true

Performance:
  - Total time: 3450ms
  - Avg chunk size: 512 tokens

Chunks Preview:
  [1] This report covers the financial performance of Q4 2024. The...
  [2] Revenue increased by 15% year-over-year, driven by strong...
  [3] Operating expenses decreased due to efficiency improvements...
  ... and 153 more chunks
```

## Error Handling

```python
from app.workers.processor import process_document_sync
import logging

logger = logging.getLogger(__name__)

def safe_process_document(doc_path, doc_id):
    """Process with error handling"""
    
    try:
        result = process_document_sync(
            doc_path=doc_path,
            doc_id=doc_id,
            chunking_strategy="adaptive"
        )
        
        return {
            'success': True,
            'result': result
        }
        
    except FileNotFoundError:
        logger.error(f"Document not found: {doc_path}")
        return {
            'success': False,
            'error': 'Document not found',
            'doc_id': doc_id
        }
        
    except MemoryError:
        logger.error(f"Document too large: {doc_path}")
        return {
            'success': False,
            'error': 'Document too large for processing',
            'doc_id': doc_id
        }
        
    except Exception as e:
        logger.error(f"Unexpected error processing {doc_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'doc_id': doc_id
        }

# Usage
result = safe_process_document("document.pdf", "doc_123")
if result['success']:
    print(f"✓ Processed: {result['result']['chunks']} chunks")
else:
    print(f"✗ Error: {result['error']}")
```

## Performance Tuning

### For Speed

```python
# Minimize embeddings, use fastest chunker
result = process_document_sync(
    doc_path="document.pdf",
    doc_id="doc_speed",
    chunking_strategy="adaptive",  # Fastest
    # Other customizations in pipeline...
)
```

### For Quality

```python
# Maximize chunk quality
result = process_document_sync(
    doc_path="document.pdf",
    doc_id="doc_quality",
    chunking_strategy="semantic",  # Best quality
    enable_deduction=True,          # Extract relationships
)
```

### For Balance

```python
# Balanced approach
result = process_document_sync(
    doc_path="document.pdf",
    doc_id="doc_balanced",
    chunking_strategy="hierarchical",  # Good balance
)
```

## Monitoring and Logging

```python
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('app.processors.pipeline')

# Now you'll see:
# INFO:app.processors.pipeline:ChunkingPipeline initialized
# INFO:app.processors.pipeline:Processing document doc_123
# INFO:app.processors.pipeline:Chunking: 156 chunks created
# INFO:app.processors.pipeline:Embedding: 98 vectors generated
# INFO:app.processors.pipeline:Indexing: FAISS index updated
# INFO:app.processors.pipeline:Pipeline complete: 3450ms
```

## Common Use Cases

### Legal Document Processing

```python
# Legal docs benefit from hierarchical structuring
result = process_document_sync(
    doc_path="contract.pdf",
    doc_id="contract_2024",
    chunking_strategy="hierarchical",  # Maintains section structure
    enable_deduction=True,              # Extract terms and clauses
)
```

### Scientific Paper Analysis

```python
# Papers benefit from semantic understanding
result = process_document_sync(
    doc_path="research_paper.pdf",
    doc_id="paper_xyz",
    chunking_strategy="semantic",  # Understand concepts
    enable_deduction=True,         # Extract methodology
)
```

### Financial Report Processing

```python
# Reports need balanced chunking
result = process_document_sync(
    doc_path="earnings_report.pdf",
    doc_id="earnings_q4",
    chunking_strategy="adaptive",  # Balance speed and quality
    enable_patterns=True,          # Extract financial patterns
)
```

## Testing

```python
import unittest
from app.workers.processor import process_document_sync

class TestChunkingPipeline(unittest.TestCase):
    
    def test_adaptive_chunking(self):
        result = process_document_sync(
            doc_path="test_document.pdf",
            doc_id="test_adaptive",
            chunking_strategy="adaptive"
        )
        self.assertGreater(result['chunks'], 0)
        self.assertIn('metrics', result)
    
    def test_semantic_chunking(self):
        result = process_document_sync(
            doc_path="test_document.pdf",
            doc_id="test_semantic",
            chunking_strategy="semantic"
        )
        self.assertGreater(result['chunks'], 0)
        self.assertLess(result['metrics']['total_time_ms'], 10000)
    
    def test_with_deduction(self):
        result = process_document_sync(
            doc_path="test_document.pdf",
            doc_id="test_deduction",
            enable_deduction=True
        )
        self.assertEqual(result['status'], 'completed')

if __name__ == '__main__':
    unittest.main()
```

## Conclusion

The ChunkingPipeline provides a powerful, flexible API for document processing. Choose the right strategy for your use case and leverage the detailed metrics to optimize performance.
