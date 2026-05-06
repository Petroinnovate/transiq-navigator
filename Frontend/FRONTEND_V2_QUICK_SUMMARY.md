# Frontend v2.0 Integration - Quick Summary

## 🎯 What Needs to Change

### Critical Updates (Must Do)

1. **API Base URL** (`src/lib/axios.ts`)
   - Change port: `8001` → `8000`
   - Add v2 prefix helper

2. **Upload Endpoint** (`src/pages/Upload.tsx`)
   - Change: `/generate` → `/api/v2/generate`
   - Handle async response: `{doc_id, task_id}` instead of dashboard data
   - Add WebSocket for progress tracking

3. **Response Handling**
   - v1.0: Returns dashboard immediately
   - v2.0: Returns task_id, dashboard comes later via WebSocket or separate fetch

### New Features Available

- ✅ **WebSocket Progress**: Real-time processing updates
- ✅ **Provider Selection**: Choose Gemini or OpenAI
- ✅ **Feature Flags**: Enable/disable deduction engine and pattern recognition
- ✅ **Search API**: Hybrid search across documents
- ✅ **Document Management**: Get document info and chunks

---

## 📝 Quick Implementation Steps

### Step 1: Update API Configuration
```typescript
// src/lib/axios.ts
baseURL: "http://localhost:8000"  // Changed from 8001
```

### Step 2: Create API Service
```typescript
// src/services/api.ts (NEW FILE)
// Copy from FRONTEND_V2_UPGRADE_GUIDE.md
```

### Step 3: Update Upload Page
```typescript
// src/pages/Upload.tsx
// Change endpoint to /api/v2/generate
// Handle {doc_id, task_id} response
// Add WebSocket connection
```

### Step 4: Add Progress Component
```typescript
// src/components/ProcessingProgress.tsx (NEW FILE)
// Copy from FRONTEND_V2_UPGRADE_GUIDE.md
```

---

## 🔄 Migration Path

### Option A: Direct Migration (Recommended)
- Update all endpoints to v2.0
- Remove v1.0 support
- Cleaner codebase

### Option B: Gradual Migration
- Add feature flag `VITE_USE_V2_API`
- Support both versions temporarily
- Migrate gradually

---

## ⚠️ Breaking Changes

| Item | v1.0 | v2.0 |
|------|------|------|
| Endpoint | `/generate` | `/api/v2/generate` |
| Port | 8001 | 8000 |
| Response | Dashboard data | `{doc_id, task_id}` |
| Processing | Synchronous | Async with WebSocket |

---

## 🚀 Quick Start

1. **Update axios config**
   ```bash
   # Edit src/lib/axios.ts
   ```

2. **Create API service**
   ```bash
   # Create src/services/api.ts
   ```

3. **Update Upload page**
   ```bash
   # Edit src/pages/Upload.tsx
   ```

4. **Test**
   ```bash
   npm run dev
   # Upload a file and verify WebSocket connection
   ```

---

## 📚 Full Documentation

See `FRONTEND_V2_UPGRADE_GUIDE.md` for complete implementation details.

---

**Priority**: High  
**Estimated Time**: 2-4 hours  
**Complexity**: Medium

