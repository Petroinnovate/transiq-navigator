# 🚀 TransIQ - Complete Stack Setup & Launch Guide

## 📋 Overview

This guide walks you through setting up and running the complete TransIQ AI Reporting System, which includes:

- **Backend**: FastAPI with Gemini API integration, vector database, and document chunking
- **Frontend**: React with TypeScript and Vite
- **Database**: Vector database for semantic search
- **AI Services**: Gemini and OpenAI support

---

## ✅ Prerequisites

Before starting, ensure you have:

### Required
- **Python 3.8 or higher** - [Download](https://www.python.org/downloads/)
  - Verify: `python --version`
- **Node.js 16+ or Bun** - [Node](https://nodejs.org/) or [Bun](https://bun.sh/)
  - Verify: `node --version` or `bun --version`

### Recommended
- **Git** - For version control
- **VS Code** - For code editing
- **Postman** - For API testing

### API Keys (Optional but Recommended)
- **Gemini API Key** - [Get free key](https://ai.google.dev/)
- **OpenAI API Key** - [Get key](https://platform.openai.com/api-keys)

---

## 🎯 Quick Start (Recommended)

### Option 1: Automated Setup & Run (EASIEST)
This is the recommended way - just one click!

1. **Navigate to the frontend folder**:
   ```
   C:\github-copiolot\1 A TransIQ\TransIQ-frontend-main\TransIQ-frontend-main
   ```

2. **Double-click**: `INSTALL_AND_RUN.bat`

3. **The script will automatically**:
   ✅ Check Python and Node/Bun installation  
   ✅ Install backend Python dependencies  
   ✅ Install frontend npm/bun packages  
   ✅ Start the backend on port 8001  
   ✅ Start the frontend on port 5173  
   ✅ Display access instructions  

4. **Wait for initialization**:
   - Backend will show: `Uvicorn running on http://0.0.0.0:8001`
   - Frontend will show: `VITE v... ready in ... ms`

5. **Open browser**: http://localhost:5173

---

### Option 2: Interactive Menu
For more control over the startup process:

1. **Double-click**: `QUICK_START.bat`
2. **Choose option 2** from the menu
3. Follow prompts

---

### Option 3: Manual Launch
If you prefer manual control:

**Terminal 1 - Backend**:
```bash
cd "C:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master"
pip install -r requirements.txt  # Install dependencies (first time only)
python -m uvicorn main:app --host localhost --port 8001 --reload
```

**Terminal 2 - Frontend**:
```bash
cd "C:\github-copiolot\1 A TransIQ\TransIQ-frontend-main\TransIQ-frontend-main"
bun install  # Install dependencies (first time only)
bun run dev
```

---

## 🔍 Verify Setup

### Check environment:
```bash
# Run this before starting
cd "C:\github-copiolot\1 A TransIQ\TransIQ-frontend-main\TransIQ-frontend-main"
CHECK_SETUP.bat
```

This will verify:
- ✅ Python installation
- ✅ Node.js/Bun installation
- ✅ Backend folder exists
- ✅ Frontend folder exists

---

## 📍 Access Points

Once running, access the application at:

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:5173 | Main web application |
| **Backend API** | http://localhost:8001 | REST API endpoints |
| **API Documentation** | http://localhost:8001/docs | Interactive Swagger UI |

---

## 🎮 First Steps in Application

### 1. Authentication
- Navigate to: http://localhost:5173
- You may see login page first
- Create account or use demo credentials if available

### 2. Upload Document
1. Click **"Upload"** button
2. Select a file (Excel, PDF, or CSV)
3. Choose **AI Provider** (Gemini or OpenAI)
4. Enable/disable feature flags:
   - ✓ Enable Fact Extraction
   - ✓ Enable Pattern Analysis
5. Click **"Generate Dashboard"**

### 3. Monitor Processing
- Real-time progress bar appears
- WebSocket updates show processing steps:
  - Reading file
  - Chunking text
  - Generating embeddings
  - Extracting facts
  - Indexing

### 4. View Dashboard
After processing completes, you'll see:
- **KPI Cards** - Key metrics with confidence scores
- **Charts** - Interactive visualizations
- **Six Sigma DMAIC** - Process improvement framework
- **Explainability** - AI reasoning and audit trail
- **Insights & Alerts** - Actionable recommendations
- **Optimizations** - Risk and ROI analysis

---

## 🛠️ Available Batch Scripts

In the frontend folder, you have these convenient scripts:

| Script | Purpose |
|--------|---------|
| `INSTALL_AND_RUN.bat` | 🌟 **RECOMMENDED** - Install deps & run full stack |
| `START_FULL_STACK.bat` | Run backend + frontend immediately |
| `QUICK_START.bat` | Interactive menu for all options |
| `CHECK_SETUP.bat` | Verify environment is properly configured |
| `start_frontend.bat` | Start frontend only |

---

## 📦 Troubleshooting

### Problem: "Python is not recognized"
```
Solution:
1. Install Python from https://www.python.org/
2. During installation, CHECK "Add Python to PATH"
3. Restart your computer
4. Verify: python --version
```

### Problem: "npm/bun is not recognized"
```
Solution:
1. Install Node.js from https://nodejs.org/
2. Or install Bun from https://bun.sh/
3. Restart your computer
4. Verify: npm --version  (or bun --version)
```

### Problem: "Backend starts but frontend can't connect"
```
Solution:
1. Verify backend is actually running (check port 8001)
2. Check firewall isn't blocking connections
3. Verify .env file has: VITE_API_URL=http://localhost:8001
4. Check browser console (F12) for detailed error
```

### Problem: "Port 8001 or 5173 already in use"
```
Solution:
1. Find what's using the port:
   - Windows: netstat -ano | findstr 8001
2. Kill the process or close the app using it
3. Or change port in vite.config.ts (frontend) or backend startup
```

### Problem: "WebSocket connection fails during upload"
```
Solution:
1. Ensure backend is actually running
2. Check backend logs for errors
3. Clear browser cache (Ctrl+Shift+Delete)
4. Try uploading again
5. Check firewall WebSocket settings
```

### Problem: "File upload gives 413 Payload Too Large"
```
Solution:
1. Try a smaller file first (test with < 10MB)
2. Check backend configuration for max upload size
3. Verify CORS settings are correct
```

---

## 🧪 Testing the Application

### Quick Test Workflow:
1. **Login/Auth**
   - Navigate to http://localhost:5173/auth
   - Create test account or login

2. **Upload File**
   - Go to http://localhost:5173/upload
   - Select test Excel or PDF file
   - Watch progress updates in real-time

3. **View Dashboard**
   - Dashboard loads automatically when done
   - Or go to http://localhost:5173/dashboard

4. **Test Features**
   - Click through all tabs and sections
   - Expand accordion items
   - Interact with charts
   - Check explainability section

### Demo Page:
Visit http://localhost:5173/demo for pre-loaded sample data and visualizations

---

## 🔧 Configuration Files

### Frontend (.env)
```
# Location: C:\github-copiolot\1 A TransIQ\TransIQ-frontend-main\TransIQ-frontend-main\.env
VITE_API_URL=http://localhost:8001
```

### Backend (if needed)
```
# Create in: C:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master\.env
GEMINI_API_KEY=your_key_here
DATABASE_URL=your_db_url
```

---

## 📚 API Endpoints

### Core Endpoints

**Upload & Process File**
```
POST /api/v2/generate
Parameters:
  - file: File (multipart)
  - provider: 'gemini' | 'openai'
  - enable_deduction: boolean
  - enable_patterns: boolean

Response:
{
  "doc_id": "string",
  "task_id": "string",
  "status": "processing"
}
```

**Get Dashboard**
```
GET /api/v2/dashboard/latest
GET /api/v2/dashboard/{reportId}

Response: Complete dashboard data with all sections
```

**Real-time Progress**
```
WebSocket: ws://localhost:8001/api/v2/ws/{task_id}

Messages:
{
  "type": "progress",
  "progress": 0-100,
  "step": "reading_file" | "chunking" | "embedding" | etc.
}
```

**Search**
```
POST /api/v2/search
{
  "query": "search text",
  "top_k": 5,
  "use_hybrid": true
}
```

---

## 🚀 Deployment Considerations

### For Production:
1. Set appropriate environment variables
2. Configure proper API keys
3. Set up vector database (Chroma, Pinecone, etc.)
4. Configure CORS properly
5. Use HTTPS instead of HTTP
6. Set up proper logging
7. Configure rate limiting
8. Set up monitoring/alerting

---

## 📞 Getting Help

### If something doesn't work:

1. **Check Prerequisites**
   - Run `CHECK_SETUP.bat`
   - Verify Python and Node/Bun are installed

2. **Check Logs**
   - Backend logs in terminal window
   - Frontend logs in browser console (F12)
   - Check Application tab in browser DevTools

3. **Verify Services**
   - Backend running: Open http://localhost:8001/docs
   - Frontend running: Open http://localhost:5173
   - API responding: Check backend terminal

4. **Reset & Try Again**
   - Close both terminal windows
   - Run `INSTALL_AND_RUN.bat` again
   - Clear browser cache
   - Try with a fresh file

5. **Read Documentation**
   - `QUICK_REFERENCE.md` - Quick lookup guide
   - `TESTING_GUIDE.md` - Testing procedures
   - `FRONTEND_V2_UPGRADE_GUIDE.md` - Technical details

---

## 📊 Project Structure

```
TransIQ Frontend (Port 5173)
├── src/
│   ├── api/              # API integration layer
│   ├── components/       # React components
│   ├── pages/           # Page components
│   ├── contexts/        # React context (auth, dashboard)
│   ├── services/        # API services
│   ├── types/          # TypeScript types
│   └── lib/            # Utilities
├── .env                 # Environment variables
├── vite.config.ts      # Vite configuration
└── package.json        # Dependencies

TransIQ Backend (Port 8001)
├── main.py             # FastAPI app entry point
├── requirements.txt    # Python dependencies
├── api/               # API routes
├── services/          # Business logic
├── db/               # Database layer
└── config/           # Configuration
```

---

## ✨ Key Features

- **AI Analysis**: Gemini or OpenAI integration
- **Vector Search**: Semantic search across documents
- **Document Processing**: Automatic chunking and embedding
- **Six Sigma DMAIC**: Process improvement framework
- **Explainability**: Full audit trail for compliance
- **Real-time Progress**: WebSocket updates during processing
- **Multi-Provider Support**: Choose AI model per upload
- **Executive Dashboard**: Professional visualizations
- **Responsive Design**: Works on desktop and tablet

---

## 🎓 Learning Resources

- FastAPI docs: https://fastapi.tiangolo.com/
- React docs: https://react.dev/
- Vite docs: https://vitejs.dev/
- Recharts: https://recharts.org/
- shadcn/ui: https://ui.shadcn.com/

---

**Last Updated**: February 22, 2026  
**Version**: 2.0  
**Status**: Production Ready ✅
