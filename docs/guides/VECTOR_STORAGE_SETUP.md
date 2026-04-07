# Vector Storage Setup Guide

This guide explains how to set up and use the long-term vector storage system for document chunks.

## Overview

The TransIQ backend now supports long-term storage of document chunks with semantic embeddings, enabling:
- ✅ Persistent storage of processed documents
- ✅ Semantic search across all your documents
- ✅ Finding similar documents
- ✅ Avoid reprocessing files
- ✅ Better AI context with RAG (Retrieval-Augmented Generation)

## Architecture

```
Upload → Extract → Chunk → Embed → Store in Supabase
                                  ↓
                            PostgreSQL + pgvector
                                  ↓
                         Semantic Search Available
```

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `sentence-transformers>=2.2.0` - For generating embeddings
- `numpy>=1.21.0` - For vector operations

### 2. Configure Supabase Database

#### A. Enable pgvector Extension

In your Supabase SQL Editor, run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

#### B. Run the Schema Script

Execute the complete schema from `supabase_schema.sql` in your Supabase SQL Editor:

```bash
# Copy contents of supabase_schema.sql and run in Supabase Dashboard
```

This creates:
- `documents` table - Stores document metadata
- `document_chunks` table - Stores chunks with 384-dimensional embeddings
- Storage bucket `documents` - For original file storage
- Row Level Security (RLS) policies - User can only access their own data
- Helper functions for semantic search

#### C. Create Storage Bucket

In Supabase Dashboard:
1. Go to **Storage** → **Create bucket**
2. Name: `documents`
3. Public: **No** (private bucket)
4. The SQL policies are already created in the schema

### 3. Configure Environment Variables

Create or update your `.env` file:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Gemini API
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Test the Setup

#### A. Test Vector Service

```bash
python vector_storage.py
```

Expected output:
```
Testing Vector Storage Service...
Model: all-MiniLM-L6-v2
Embedding dimension: 384
✓ Vector storage service test completed successfully!
```

#### B. Test Backend

Start the server:
```bash
python main.py
```

Visit: `http://localhost:8001/docs` to see the new endpoints.

## New API Endpoints

### Documents Management

#### 1. List User Documents
```http
GET /documents/
Authorization: Bearer {token}
```

Query parameters:
- `limit` (default: 50, max: 100)
- `offset` (default: 0)

#### 2. Get Specific Document
```http
GET /documents/{document_id}
Authorization: Bearer {token}
```

Returns document metadata and all chunks.

#### 3. Delete Document
```http
DELETE /documents/{document_id}
Authorization: Bearer {token}
```

Deletes document and all associated chunks.

#### 4. Get Document Chunks
```http
GET /documents/{document_id}/chunks
Authorization: Bearer {token}
```

### Semantic Search

#### 1. Search by Query
```http
POST /search/
Authorization: Bearer {token}
Content-Type: application/json

{
  "query": "What is Six Sigma DMAIC?",
  "match_threshold": 0.5,
  "match_count": 10
}
```

Returns most similar chunks across all user documents.

#### 2. Find Similar Documents
```http
GET /search/similar/{document_id}
Authorization: Bearer {token}
```

Query parameters:
- `match_count` (default: 5, max: 20)

## How It Works

### 1. Document Upload & Processing

When you upload files via `POST /generate`:

```python
# User uploads PDF/Excel/CSV
# ↓
# Files are extracted and chunked
# ↓
# For authenticated users:
#   1. Original files saved to Supabase Storage
#   2. Document record created in database
#   3. Chunks are embedded using sentence-transformers
#   4. Chunks + embeddings stored in database
#   5. Document status updated to "completed"
```

### 2. Embedding Generation

Using `all-MiniLM-L6-v2` model (384 dimensions):
- Fast and efficient
- Good quality for most use cases
- Multilingual support available

Alternative models (change in `vector_storage.py`):
- `all-mpnet-base-v2` (768 dims, better quality)
- `paraphrase-multilingual-MiniLM-L12-v2` (multilingual)

### 3. Vector Search

Uses PostgreSQL pgvector with cosine similarity:
```sql
-- Similarity calculation
1 - (embedding <=> query_embedding)
```

Results sorted by similarity score (0-1, higher = more similar).

## Usage Examples

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:8001"
TOKEN = "your_jwt_token"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# Search for content
search_response = requests.post(
    f"{BASE_URL}/search/",
    headers=headers,
    json={
        "query": "defect rate and process capability",
        "match_threshold": 0.6,
        "match_count": 5
    }
)

results = search_response.json()
for result in results["results"]:
    print(f"File: {result['file_name']}")
    print(f"Similarity: {result['similarity']:.2f}")
    print(f"Text: {result['chunk_text'][:200]}...")
    print("---")
```

### JavaScript/TypeScript Example

```typescript
const searchDocuments = async (query: string) => {
  const response = await fetch('http://localhost:8001/search/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: query,
      match_threshold: 0.5,
      match_count: 10
    })
  });
  
  const data = await response.json();
  return data.results;
};
```

## Performance Considerations

### Indexing

The schema uses IVFFlat indexing for vector search:
```sql
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

For better accuracy (but slower inserts), use HNSW:
```sql
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops);
```

### Batch Processing

Chunks are stored in batches of 50 to optimize database performance:
```python
batch_size = 50
for i in range(0, len(chunks_data), batch_size):
    batch = chunks_data[i:i + batch_size]
    await supabase_service.store_chunks(batch)
```

### Memory Usage

The sentence-transformers model loads once and stays in memory (~100MB).
For production, consider:
- Using a smaller model for lower memory
- Deploying on GPU for faster embedding generation
- Caching frequently used embeddings

## Benefits of This Approach

### 1. Cost Reduction
- **Before**: Send all document content to AI every time
- **After**: Only send relevant chunks based on semantic search
- **Savings**: Up to 90% reduction in AI API costs

### 2. Better AI Responses
- Context limited to relevant information
- Reduces hallucination from irrelevant context
- More focused and accurate answers

### 3. Historical Analysis
- Search across all historical documents
- Find patterns and trends over time
- Compare current vs past documents

### 4. Scalability
- Documents processed once, queried many times
- Incremental updates (add new docs without reprocessing old ones)
- Efficient storage with PostgreSQL

## Monitoring

### Check Storage Usage

```sql
-- Total documents per user
SELECT user_id, COUNT(*) as doc_count
FROM documents
GROUP BY user_id;

-- Total chunks stored
SELECT COUNT(*) as total_chunks FROM document_chunks;

-- Average chunks per document
SELECT 
  d.file_name,
  COUNT(dc.id) as chunk_count
FROM documents d
LEFT JOIN document_chunks dc ON dc.document_id = d.id
GROUP BY d.id, d.file_name
ORDER BY chunk_count DESC;
```

### Database Size

```sql
-- Check table sizes
SELECT 
  pg_size_pretty(pg_total_relation_size('document_chunks')) as chunks_size,
  pg_size_pretty(pg_total_relation_size('documents')) as documents_size;
```

## Troubleshooting

### 1. "sentence-transformers not found"
```bash
pip install sentence-transformers
```

### 2. "pgvector extension not enabled"
Run in Supabase SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. "Storage bucket doesn't exist"
Create bucket in Supabase Dashboard or run the storage policies from `supabase_schema.sql`.

### 4. Embeddings not being stored
Check:
- User is authenticated (only auth users get storage)
- Supabase credentials are correct in `.env`
- Database schema is properly created
- Check backend logs for errors

### 5. Search returns no results
- Lower `match_threshold` (try 0.3 instead of 0.5)
- Increase `match_count`
- Verify embeddings were actually stored
- Check user_id matches (RLS policies)

## Next Steps

### Advanced Features to Add

1. **Multi-document RAG**: Query multiple documents for comprehensive answers
2. **Chunk summarization**: Store summaries alongside chunks
3. **Metadata filtering**: Search within specific file types or date ranges
4. **Hybrid search**: Combine semantic + keyword search
5. **Embedding caching**: Cache embeddings for common queries
6. **Analytics dashboard**: Visualize document usage and search patterns

### Production Deployment

1. Use environment-specific configs
2. Enable query caching
3. Set up monitoring (Sentry, New Relic)
4. Configure backup policies for Supabase
5. Implement rate limiting
6. Add request logging

## Support

For issues or questions:
1. Check backend logs for detailed errors
2. Verify Supabase configuration in dashboard
3. Test vector service independently
4. Review API documentation at `/docs`

---

**Created**: November 2025  
**Version**: 1.0  
**Embedding Model**: all-MiniLM-L6-v2 (384 dimensions)
