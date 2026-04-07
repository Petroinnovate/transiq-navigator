# 🎬 TransIQ Backend - Complete Demo Guide

## 🚀 Current Status

✅ **Backend Server Running**: http://localhost:8001
✅ **Interactive API Docs**: http://localhost:8001/docs
✅ **Local Storage Active**: SQLite + FAISS (No Supabase required)

---

## 📋 What You're Seeing

### 1. **Backend Server** (Separate PowerShell Window)
The backend is running with:
- **FastAPI** web framework
- **Google Gemini AI** for document analysis
- **FAISS** for vector similarity search
- **SQLite** for document storage
- **Auto-reload** enabled for development

### 2. **Interactive API Documentation** (Browser)
The Swagger UI at http://localhost:8001/docs shows all available endpoints.

---

## 🎯 How the System Works

### **Document Processing Workflow:**

```
1. Upload File (CSV/Excel/PDF)
   ↓
2. Extract & Chunk Text
   ↓
3. AI Analysis (Google Gemini)
   ↓
4. Generate Dashboard (KPIs, Charts, Insights)
   ↓
5. Create Embeddings (Sentence-Transformers)
   ↓
6. Store in Database (SQLite + FAISS)
   ↓
7. Return Analytics Dashboard
```

---

## 🧪 Live Demo - Step by Step

### **Test 1: Health Check**

**Via Browser:**
Open: http://localhost:8001/system/health

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": 1763412000.567295,
  "service": "document-processing-api"
}
```

---

### **Test 2: Upload & Process a Document**

**Using the Interactive Docs:**

1. Go to: http://localhost:8001/docs
2. Find the **POST /generate** endpoint
3. Click "Try it out"
4. Upload a file (CSV, Excel, or PDF)
5. Click "Execute"

**Sample CSV you can create:**
```csv
Product,Sales,Cost,Profit,Region
Widget A,50000,30000,20000,North
Widget B,45000,25000,20000,South
Widget C,60000,35000,25000,East
```

**Expected Response Structure:**
```json
{
  "dashboard": {
    "title": "Sales Performance Dashboard",
    "description": "Analysis of product sales data...",
    "kpis": [
      {
        "label": "Total Sales",
        "value": 155000,
        "change": "+12%",
        "trend": "up"
      }
    ],
    "charts": [
      {
        "title": "Sales by Product",
        "type": "BarChart",
        "data": [...]
      }
    ],
    "insights": [
      "Widget C shows highest profit margin...",
      "North region outperforming others..."
    ]
  }
}
```

---

### **Test 3: What Happens Behind the Scenes**

When you upload a file, the system:

1. ✅ **Receives the file** via FastAPI endpoint
2. ✅ **Extracts data** (pandas for CSV/Excel, PyMuPDF for PDF)
3. ✅ **Chunks the content** (10,000 char chunks with semantic boundaries)
4. ✅ **Sends to Google Gemini AI** for analysis
5. ✅ **Generates embeddings** (384-dimensional vectors via sentence-transformers)
6. ✅ **Stores in database**:
   - Document metadata → SQLite
   - Text chunks → SQLite
   - Vector embeddings → FAISS index
7. ✅ **Returns dashboard** with charts, KPIs, insights, and suggestions

---

## 🔍 Available Endpoints

### **Core Processing**
- `POST /generate` - Upload and process documents

### **System**
- `GET /system/health` - Health check
- `GET /` - API information

### **Documents** (Requires Auth)
- `GET /documents/` - List user documents
- `GET /documents/{id}` - Get specific document
- `DELETE /documents/{id}` - Delete document
- `GET /documents/{id}/chunks` - Get document chunks

### **Search** (Requires Auth)
- `POST /search/` - Semantic search across documents
- `GET /search/similar/{id}` - Find similar documents

### **Authentication** (Optional - Local Storage Mode)
- `POST /auth/signup` - Create account
- `POST /auth/signin` - Login
- `POST /auth/signout` - Logout

---

## 🎨 Visual Demonstration

### **What the AI Generates:**

For a sales data file, you'll see:

**📊 KPIs (Key Performance Indicators):**
- Total Revenue: $545,000 (+8%)
- Average Profit Margin: 42% (+2%)
- Units Sold: 10,750 (+5%)
- Best Performing Product: Widget C

**📈 Charts:**
- Sales Trend Over Time (Line Chart)
- Sales by Region (Bar Chart)
- Product Distribution (Pie Chart)
- Profit vs Cost Analysis (Scatter Plot)

**💡 Insights:**
- "Widget C consistently outperforms with 27% higher profit"
- "North region showing strongest growth at 15% YoY"
- "Cost optimization opportunity in South region"

**🔧 Optimization Suggestions:**
- "Focus marketing efforts on Widget C line"
- "Investigate cost structure in underperforming regions"
- "Consider seasonal pricing strategy based on trends"

---

## 🗄️ Storage & Search Demo

### **Document Storage:**

Every uploaded document is stored with:
- **Document ID**: Unique identifier
- **User ID**: Owner (or "anonymous" for non-authenticated)
- **File Name**: Original filename
- **File Size**: Size in bytes
- **Status**: processing → completed
- **Created At**: Timestamp
- **File Location**: Path to uploaded file

### **Vector Search:**

Documents are automatically searchable:

```python
# Example: Search for "profit optimization"
POST /search/
{
  "query": "profit optimization strategies",
  "top_k": 5
}

# Returns similar chunks with similarity scores
# Uses FAISS L2 distance search on 384-dim vectors
```

---

## 🛠️ Technology Stack in Action

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | FastAPI | REST API endpoints |
| **AI Analysis** | Google Gemini 2.0 Flash | Dashboard generation |
| **Embeddings** | Sentence-Transformers | Text → 384D vectors |
| **Vector Search** | FAISS | Similarity search |
| **Database** | SQLite | Document storage |
| **File Processing** | Pandas, PyMuPDF | Extract text from files |
| **Server** | Uvicorn | ASGI web server |

---

## 📊 Real-Time Monitoring

Watch the backend terminal for live logs:

```
INFO: 127.0.0.1:12345 - "POST /generate HTTP/1.1" 200 OK
INFO: Processing file: sales_data.csv (1.2 KB)
INFO: Created 3 chunks from document
INFO: Generated embeddings for 3 chunks
INFO: Stored document with ID: abc123...
```

---

## 🎯 Key Features Demonstrated

1. ✅ **Zero Configuration Required**
   - No Supabase setup needed
   - Works with local storage out of the box

2. ✅ **AI-Powered Analysis**
   - Automatic dashboard generation
   - Context-aware insights
   - Data-driven suggestions

3. ✅ **Vector Search**
   - Semantic similarity search
   - Fast FAISS indexing
   - Finds related content across documents

4. ✅ **Flexible Authentication**
   - Works without login (anonymous mode)
   - Supports authenticated users
   - JWT token-based security

5. ✅ **Production Ready**
   - Error handling
   - CORS configured
   - Health monitoring
   - Auto-reload for development

---

## 🎬 Next Steps

### **Try These:**

1. **Upload Different File Types**
   - CSV with sales data
   - Excel spreadsheet
   - PDF document

2. **Check Storage**
   - Look at `local_storage.db` (SQLite database)
   - Check `faiss_index.bin` (vector index)
   - View `local_file_storage/` (uploaded files)

3. **Test Search** (after uploading multiple documents)
   - Search for keywords
   - Find similar documents
   - Compare similarity scores

4. **Monitor Performance**
   - Watch processing times
   - Check embedding generation
   - View API response times

---

## 🌐 Access Points Summary

| Service | URL | Status |
|---------|-----|--------|
| **API Root** | http://localhost:8001 | ✅ Running |
| **Interactive Docs** | http://localhost:8001/docs | ✅ Open in Browser |
| **OpenAPI Schema** | http://localhost:8001/openapi.json | ✅ Available |
| **Health Check** | http://localhost:8001/system/health | ✅ Healthy |

---

## 🎉 What Makes This Special

**TransIQ automatically:**
- 📊 Analyzes your data
- 📈 Creates visualizations
- 💡 Generates insights
- 🔧 Suggests optimizations
- 🔍 Makes content searchable
- 💾 Stores everything locally

**All powered by:**
- 🤖 Advanced AI (Google Gemini)
- 🧠 Machine Learning (Sentence-Transformers)
- ⚡ Fast Vector Search (FAISS)
- 🐍 Modern Python (FastAPI)

---

## 📞 Support

If something doesn't work:
1. Check the backend terminal for errors
2. Visit http://localhost:8001/docs for API testing
3. Verify server is running on port 8001
4. Check logs in the console

**Backend is LIVE and READY to process your documents!** 🚀
