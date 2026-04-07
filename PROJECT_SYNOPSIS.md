# 📋 TransIQ Backend - Complete Project Synopsis

## 🎯 Project Overview

**TransIQ** is an intelligent document processing and analytics backend system that combines AI-powered analysis with vector-based semantic search. It processes documents (PDF, Excel, CSV) and generates comprehensive Six Sigma DMAIC-based dashboards with KPIs, charts, insights, and optimization suggestions.

**Current Version:** v1.0.0  
**Target Version:** v2.0.0

---

## 🏗️ Architecture & Technology Stack

### Core Framework
- **FastAPI** (v0.68+) - Modern Python web framework
- **Uvicorn** (v0.15+) - ASGI web server
- **Python 3.8+** - Runtime environment

### AI & Machine Learning
- **Google Gemini 2.0 Flash** - Document analysis and dashboard generation
- **Sentence-Transformers** (all-MiniLM-L6-v2) - Text embeddings (384 dimensions)
- **FAISS** - Vector similarity search (local mode)
- **NumPy** - Vector operations

### Data Processing
- **Pandas** - CSV/Excel data extraction and manipulation
- **PyMuPDF (fitz)** - PDF text extraction
- **python-docx** - Word document processing
- **openpyxl** - Excel file handling

### Storage Solutions
- **Supabase** (Optional) - Cloud PostgreSQL with pgvector extension
- **SQLite** (Fallback) - Local relational database
- **FAISS Index** - Local vector search index
- **Local File Storage** - File system storage for uploads

### Authentication & Security
- **Supabase Auth** - User authentication (optional)
- **JWT Tokens** - Token-based authentication
- **CORS Middleware** - Cross-origin resource sharing
- **Row-Level Security (RLS)** - Data isolation

---

## 🔄 System Workflow

```
1. Document Upload (PDF/Excel/CSV)
   ↓
2. Text Extraction (PyMuPDF/Pandas)
   ↓
3. Intelligent Chunking (10,000 char chunks, semantic boundaries)
   ↓
4. AI Analysis (Google Gemini)
   ├─→ Six Sigma DMAIC Report
   ├─→ KPIs Calculation
   ├─→ Chart Generation
   ├─→ Insights & Recommendations
   └─→ Optimization Suggestions
   ↓
5. Vector Embedding Generation (Sentence-Transformers)
   ↓
6. Storage
   ├─→ Document Metadata → SQLite/Supabase
   ├─→ Text Chunks → SQLite/Supabase
   ├─→ Vector Embeddings → FAISS/Supabase pgvector
   └─→ Original Files → Local Storage/Supabase Storage
   ↓
7. Return Dashboard JSON Response
```

---

## 📁 Project Structure

```
TransIQ-backend-master/
├── main.py                      # FastAPI application entry point
├── llm.py                        # AI processing & Gemini integration
├── chunker.py                    # Intelligent text chunking algorithm
├── vector_storage.py             # Embedding generation service
├── supabase_service.py           # Supabase integration (with local fallback)
├── local_storage.py              # SQLite + FAISS local storage
├── supa.py                       # API routes (auth, documents, search)
├── requirements.txt              # Python dependencies
├── supabase_schema.sql           # Database schema (Supabase)
│
├── Documentation/
│   ├── QUICK_START.md            # Setup guide
│   ├── DEMO_GUIDE.md             # Demo instructions
│   ├── VECTOR_STORAGE_SETUP.md   # Vector storage setup
│   └── PROJECT_SYNOPSIS.md       # This file
│
└── Storage/
    ├── local_storage.db          # SQLite database
    ├── faiss_index.bin           # FAISS vector index
    ├── faiss_index.bin.map       # Vector ID mapping
    └── local_file_storage/       # Uploaded files
```

---

## 🔌 API Endpoints

### Core Processing
- `POST /generate` - Upload and process documents (supports anonymous users)
- `GET /system/health` - Health check endpoint
- `GET /` - API information and endpoint listing

### Authentication (Optional)
- `POST /auth/signup` - User registration
- `POST /auth/signin` - User login
- `POST /auth/signout` - User logout
- `GET /auth/test/supabase` - Test Supabase connection

### User Management
- `GET /user/profile` - Get user profile
- `PUT /user/profile` - Update user profile
- `GET /user/me` - Get current user info

### Document Management (Requires Auth)
- `GET /documents/` - List user documents (paginated)
- `GET /documents/{id}` - Get document with chunks
- `DELETE /documents/{id}` - Delete document
- `GET /documents/{id}/chunks` - Get all chunks for a document

### Semantic Search (Requires Auth)
- `POST /search/` - Semantic search across documents
  - Body: `{query, match_threshold, match_count}`
- `GET /search/similar/{id}` - Find similar documents

### History & Analytics (Requires Auth)
- `GET /history/` - Get processing history
- `GET /history/{id}` - Get specific record
- `DELETE /history/{id}` - Delete record
- `GET /analytics/` - Full analytics
- `GET /analytics/summary` - Summary statistics

---

## 🎨 Key Features

### 1. Document Processing
- ✅ Multi-format support (PDF, Excel, CSV)
- ✅ Intelligent text extraction
- ✅ Semantic-aware chunking (preserves context)
- ✅ Batch file processing

### 2. AI-Powered Analytics
- ✅ Six Sigma DMAIC framework
- ✅ Automatic KPI extraction
- ✅ Chart generation (Bar, Line, Pie, Sankey, etc.)
- ✅ Statistical analysis
- ✅ Root cause analysis
- ✅ Optimization suggestions
- ✅ Anomaly detection

### 3. Vector Search
- ✅ Semantic similarity search
- ✅ Fast FAISS indexing
- ✅ Cosine similarity matching
- ✅ Multi-document search
- ✅ Similar document discovery

### 4. Storage Flexibility
- ✅ Cloud mode (Supabase PostgreSQL + pgvector)
- ✅ Local mode (SQLite + FAISS) - No external dependencies
- ✅ Automatic fallback to local storage
- ✅ File storage (Supabase Storage or local filesystem)

### 5. User Management
- ✅ Optional authentication
- ✅ Anonymous user support
- ✅ User-specific data isolation
- ✅ Profile management
- ✅ Usage tracking

---

## 📊 Data Models

### Documents Table
```sql
- id (UUID)
- user_id (UUID)
- file_name (TEXT)
- file_type (TEXT)
- file_size (INTEGER)
- original_file_path (TEXT)
- total_chunks (INTEGER)
- status (TEXT: processing/completed/failed)
- metadata (JSONB)
- created_at, updated_at (TIMESTAMPTZ)
```

### Document Chunks Table
```sql
- id (UUID)
- document_id (UUID)
- chunk_text (TEXT)
- chunk_index (INTEGER)
- embedding (VECTOR(384))
- metadata (JSONB)
- created_at (TIMESTAMPTZ)
```

### Service Usage Records
```sql
- id (UUID)
- user_id (UUID)
- file_names (TEXT[])
- ai_response (JSONB)
- metadata (JSONB)
- created_at (TIMESTAMPTZ)
```

---

## 🔧 Configuration

### Environment Variables (.env)
```env
# Supabase (Optional)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# AI Service
GEMINI_API_KEY=your-gemini-api-key

# Server
PORT=8001
HOST=localhost
```

### Storage Modes
1. **Cloud Mode**: Requires Supabase credentials
   - PostgreSQL with pgvector
   - Supabase Storage
   - Row-Level Security

2. **Local Mode**: No external dependencies
   - SQLite database
   - FAISS index
   - Local file storage

---

## 🚀 Current Capabilities

### ✅ Working Features
- Document upload and processing
- AI-powered dashboard generation
- Vector embeddings and semantic search
- Local storage (SQLite + FAISS)
- Cloud storage (Supabase) - optional
- Anonymous user support
- Authentication system
- Document management
- Search functionality
- Analytics and history tracking

### ⚠️ Known Limitations
- Chunk size fixed at 10,000 characters
- Single embedding model (all-MiniLM-L6-v2)
- Limited to English language
- No real-time processing updates
- No batch processing API
- No document versioning
- No collaborative features

---

## 📈 Performance Metrics

- **Processing Time**: 10-20 seconds per document
- **Embedding Generation**: 2-3 seconds per document
- **Search Latency**: < 100ms (local), < 500ms (cloud)
- **Concurrent Requests**: Limited by server resources
- **File Size Limits**: Configurable (default: no limit)

---

## 🎯 Use Cases

1. **Business Intelligence**
   - Sales data analysis
   - Financial report processing
   - Performance metrics extraction

2. **Quality Management**
   - Six Sigma analysis
   - Process improvement
   - Defect tracking

3. **Document Intelligence**
   - Contract analysis
   - Report summarization
   - Data extraction

4. **Research & Analytics**
   - Academic paper analysis
   - Survey data processing
   - Statistical analysis

---

## 🔄 Migration Path to v2.0

### Potential Improvements

1. **Enhanced AI Capabilities**
   - Support for multiple LLM providers (OpenAI, Anthropic, etc.)
   - Custom prompt templates
   - Multi-language support
   - Fine-tuned models

2. **Advanced Chunking**
   - Adaptive chunk sizes
   - Overlap strategies
   - Hierarchical chunking
   - Table-aware chunking

3. **Better Vector Search**
   - Hybrid search (keyword + semantic)
   - Re-ranking models
   - Multi-vector search
   - Query expansion

4. **Scalability**
   - Async processing queue
   - Background jobs
   - Caching layer
   - CDN integration

5. **User Experience**
   - Real-time progress updates
   - WebSocket support
   - Batch processing API
   - Export functionality

6. **Enterprise Features**
   - Multi-tenancy
   - Role-based access control
   - Audit logging
   - API rate limiting

7. **Data Management**
   - Document versioning
   - Collaborative editing
   - Data export/import
   - Backup/restore

8. **Monitoring & Analytics**
   - Usage analytics dashboard
   - Performance monitoring
   - Error tracking
   - Cost tracking

---

## 📝 Dependencies Summary

### Core Dependencies
- fastapi>=0.68.0
- uvicorn>=0.15.0
- pydantic>=1.8.2
- python-multipart>=0.0.5

### AI & ML
- google-genai>=1.15.0
- sentence-transformers>=2.2.0
- numpy>=1.21.0

### Document Processing
- PyMuPDF>=1.18.0
- python-docx>=0.8.11
- pandas>=1.3.0
- openpyxl>=3.0.9

### Storage
- supabase>=2.0.0
- psycopg2>=2.9.1
- sqlalchemy>=1.4.22
- faiss-cpu (for local mode)

### Utilities
- python-dotenv>=0.19.0
- tqdm>=4.62.0
- python-jose[cryptography]>=3.3.0

---

## 🐛 Known Issues & Technical Debt

1. **Error Handling**
   - Some endpoints lack comprehensive error handling
   - Error messages could be more user-friendly

2. **Testing**
   - Limited unit tests
   - No integration tests
   - No load testing

3. **Documentation**
   - API documentation could be enhanced
   - Missing architecture diagrams
   - No deployment guide

4. **Security**
   - API key management could be improved
   - Rate limiting not implemented
   - Input validation could be stricter

5. **Performance**
   - No caching layer
   - Synchronous processing
   - No connection pooling optimization

---

## 🎓 Learning Resources

- FastAPI Documentation: https://fastapi.tiangolo.com/
- Supabase Documentation: https://supabase.com/docs
- Sentence Transformers: https://www.sbert.net/
- FAISS Documentation: https://github.com/facebookresearch/faiss

---

## 📞 Support & Maintenance

### Current Status
- ✅ Core functionality working
- ✅ Local storage operational
- ✅ Cloud storage optional
- ⚠️ Needs v2.0 improvements

### Next Steps for v2.0
1. Review and prioritize feature requests
2. Design v2.0 architecture
3. Create migration plan
4. Implement improvements incrementally
5. Add comprehensive testing
6. Update documentation

---

**Last Updated:** 2025-01-27  
**Version:** 1.0.0  
**Status:** Production Ready (with limitations)

