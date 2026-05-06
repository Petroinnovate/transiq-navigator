# TransIQ Complete Stack - Quick Reference

## 📋 Project Overview

TransIQ is a world-class AI reporting system with:
- **Backend**: FastAPI (Python) with Gemini API integration, vector database, and document chunking
- **Frontend**: React with TypeScript, Vite, and Tailwind CSS
- **Features**: AI analysis, Six Sigma methodology, KPIs, predictions, and explainability

---

## 🚀 Quick Start (3 Steps)

### Option 1: Automated Full Stack Launch
1. **Double-click**: `START_FULL_STACK.bat`
2. Wait 15-30 seconds for services to initialize
3. Open browser to: **http://localhost:5173**

### Option 2: Interactive Menu
1. **Double-click**: `QUICK_START.bat`
2. Choose option 2 (Start Complete Stack)
3. Open browser to: **http://localhost:5173**

### Option 3: Manual Launch

**Backend** (Terminal 1):
```bash
cd "C:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master"
python -m uvicorn main:app --host localhost --port 8001 --reload
```

**Frontend** (Terminal 2):
```bash
cd "C:\github-copiolot\1 A TransIQ\TransIQ-frontend-main\TransIQ-frontend-main"
bun run dev
# or
npm run dev
```

---

## 📍 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | Main application UI |
| Backend API | http://localhost:8001 | API endpoints |
| API Docs | http://localhost:8001/docs | Swagger documentation |

---

## 🔧 Available Commands

### Frontend
```bash
bun run dev      # Start dev server (port 5173)
bun run build    # Build for production
npm run dev      # Alternative (if bun not available)
npm run build    # Alternative build command
```

### Backend
```bash
python -m uvicorn main:app --host localhost --port 8001 --reload
# Or use: python main.py
```

---

## 🎯 Key Features

### Upload & Processing
1. Navigate to **Upload** page
2. Select a file (Excel, PDF, CSV)
3. Choose AI Provider: Gemini or OpenAI
4. Enable/disable Feature Flags
5. Click **Generate Dashboard**
6. View real-time progress with WebSocket updates

### Dashboard Features
- **KPI Cards**: Key performance indicators with confidence scores
- **Charts**: Interactive visualizations (line, bar, area, pie, etc.)
- **Six Sigma**: DMAIC framework for process improvement
- **Explainability**: AI reasoning and audit trail for compliance
- **Insights**: Actionable recommendations and alerts
- **Optimization**: Risk assessment and ROI calculations

---

## 🔑 Environment Setup

### Required
- Python 3.8+ 
- Node.js (or Bun)
- Gemini API Key (optional, for Gemini provider)

### Environment Variables
Edit `.env` file in frontend:
```
VITE_API_URL=http://localhost:8001
```

Backend `.env` (if required):
```
GEMINI_API_KEY=your_key_here
DATABASE_URL=your_db_url
```

---

## 📦 API Endpoints

### File Upload & Processing
```
POST /api/v2/generate
Parameters:
  - provider: 'gemini' | 'openai' (default: 'gemini')
  - enable_deduction: boolean (default: true)
  - enable_patterns: boolean (default: true)

Response:
{
  "doc_id": "string",
  "task_id": "string",
  "status": "processing"
}
```

### Dashboard Data
```
GET /api/v2/dashboard/latest          # Latest dashboard
GET /api/v2/dashboard/{reportId}      # Specific dashboard
```

### Real-time Progress
```
WebSocket: ws://localhost:8001/api/v2/ws/{task_id}

Message Types:
- progress: { "type": "progress", "progress": 50, "step": "chunking" }
- completed: { "type": "completed", "doc_id": "...", "report_id": "..." }
- error: { "type": "error", "message": "..." }
```

### Search
```
POST /api/v2/search
Body: {
  "query": "search text",
  "top_k": 5,
  "use_hybrid": true
}
```

---

## 🧪 Testing Workflow

### Manual Testing
1. **Upload File**: 
   - Go to http://localhost:5173/upload
   - Select Excel or PDF file
   - Click Generate Dashboard
   
2. **View Dashboard**:
   - Dashboard should auto-load when processing completes
   - Verify all components display correctly
   
3. **Test Features**:
   - Check KPI confidence scores
   - Verify Six Sigma DMAIC tabs
   - Review explainability sections
   - Test chart interactions

### Demo Page
Visit http://localhost:5173/demo for sample data and visualizations

---

## 🐛 Troubleshooting

### Backend not responding
```
✗ Error: Connection refused to localhost:8001

Fix:
1. Ensure backend is running (check terminal)
2. Verify Python is installed: python --version
3. Check port 8001 is not in use: netstat -an | findstr 8001
4. Restart backend service
```

### Frontend won't load
```
✗ Error: Cannot find module '@/...'

Fix:
1. Install dependencies: bun install (or npm install)
2. Clear cache: rm -rf node_modules .bun
3. Reinstall: bun install --force
4. Restart dev server
```

### File upload fails
```
✗ Error: 413 Payload too large

Fix:
1. Check backend is running
2. Verify file format (Excel, PDF, CSV only)
3. Check file size (max typically 50MB)
4. Check browser console for detailed error
```

### WebSocket connection fails
```
✗ Error: WebSocket connection failed

Fix:
1. Ensure backend is running on port 8001
2. Check task_id is valid
3. Verify firewall allows WebSocket connections
4. Check browser console for CORS errors
```

---

## 📚 Documentation

- **FRONTEND_INTEGRATION_COMPLETE.md** - Complete frontend features
- **TESTING_GUIDE.md** - Detailed testing instructions
- **FRONTEND_V2_UPGRADE_GUIDE.md** - v2.0 migration guide
- **IMPLEMENTATION_SUMMARY.md** - Implementation details

---

## 🛠️ Stack Overview

### Backend Stack
- **Framework**: FastAPI (Python)
- **AI**: Google Gemini API / OpenAI
- **Vector DB**: Chroma or Pinecone
- **Processing**: Document chunking, embeddings, semantic search
- **APIs**: RESTful + WebSocket

### Frontend Stack
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **UI Components**: shadcn/ui (Radix UI)
- **Styling**: Tailwind CSS
- **State Management**: React Context + Hooks
- **Charts**: Recharts
- **HTTP**: Axios with interceptors

---

## 📞 Support

For issues or questions:
1. Check the documentation files
2. Review browser console for errors
3. Check backend logs in terminal
4. Verify environment configuration
5. Try resetting the stack (restart services)

---

**Last Updated**: February 22, 2026
**Version**: 2.0
