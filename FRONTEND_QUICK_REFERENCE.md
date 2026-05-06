# TransIQ Frontend Exploration - Quick Reference Card

## 📋 EXECUTIVE SUMMARY

| Aspect | Status | Details |
|--------|--------|---------|
| **Frontend Framework** | ✅ Ready | React 18.3 + TypeScript + Vite |
| **Dashboard Component** | ✅ Ready | DashboardRenderer can accept Phase 5 data |
| **State Management** | ✅ Ready | DashboardContext + localStorage |
| **API Integration** | ✅ Ready | axios, auth token, React Query |
| **Visualization** | ⚠️ Partial | recharts (charts only), no graph library |
| **Graph Visualization** | ❌ Missing | Need to install vis.js or D3.js |
| **Entity Components** | ❌ Missing | Need EntityNetworkView, EntityDetailPanel |
| **Testing** | ⚠️ Basic | Demo page exists, no unit tests |
| **Security** | ✅ Good | Bearer token + protected routes |
| **Phase 5 Ready** | 🟡 60% | Infrastructure ready, components needed |

---

## 🗂️ FILE STRUCTURE (Key Files)

```
TransIQ-frontend-main/
├── src/
│   ├── pages/
│   │   ├── Dashboard.tsx          ⭐ MAIN - fetches & displays dashboard
│   │   ├── Upload.tsx             - file upload interface
│   │   ├── Search.tsx             - hybrid search
│   │   └── ConfusionMatrix.tsx    - model metrics
│   │
│   ├── components/
│   │   ├── DashboardRenderer.tsx  ⭐ CORE - composes all sections
│   │   ├── ChartRenderer.tsx      - renders recharts
│   │   ├── KPICard.tsx            - metric display
│   │   ├── InsightsSection.tsx    - alerts & recommendations
│   │   ├── SixSigmaSection.tsx    - DMAIC framework
│   │   ├── progressive/
│   │   │   └── ProgressiveDisclosureView.tsx (CEO/Manager/Engineer/Boardroom tabs)
│   │   ├── predictive/
│   │   │   ├── PredictiveDashboard.tsx
│   │   │   └── WhatIfSimulator.tsx
│   │   ├── optimization/
│   │   ├── confusion/
│   │   ├── ui/                    - shadcn/ui components
│   │   └── layout/
│   │       └── DashboardLayout.tsx
│   │
│   ├── contexts/
│   │   └── DashboardContext.tsx   ⭐ STATE - central dashboard state
│   │
│   ├── services/
│   │   ├── api.ts                 ⭐ API - file upload, search, document ops
│   │   └── dashboardApi.ts        - dashboard queries (React Query)
│   │
│   ├── lib/
│   │   └── axios.ts               ⭐ HTTP - configured with auth interceptor
│   │
│   ├── types/
│   │   ├── dashboard.ts           - DashboardResponse schema
│   │   └── widget.ts
│   │
│   ├── utils/
│   │   ├── visualizationEngine.ts - widget generation & chart selection
│   │   └── pdfExport.ts
│   │
│   ├── App.tsx                    - route definitions
│   ├── main.tsx
│   └── index.css
│
├── package.json                   - dependencies (NO graph libs)
├── vite.config.ts                 - build config
├── tailwind.config.js             - Tailwind theme (dark mode)
└── tsconfig.json
```

---

## 🔌 API ENDPOINTS USED

### Dashboard
```
GET  /api/v2/dashboard/latest          fetch latest report
GET  /api/v2/dashboard/{reportId}      fetch specific report
GET  /api/v2/dashboard/status/{taskId} check processing
```

### Upload (POST with FormData)
```
POST /api/v2/generate                  single file (1)
POST /api/v2/generate-batch            batch (2-5 files)
POST /api/v2/generate-project          project (6-20 files)
```

### Search & Documents
```
POST /api/v2/documents/search          hybrid search
GET  /api/v2/documents/{docId}         doc metadata
GET  /api/v2/documents/{docId}/chunks  doc chunks
```

### Export
```
GET  /api/v2/dashboard/{reportId}/export/pdf
GET  /api/v2/dashboard/{reportId}/export/excel
```

---

## 📊 DASHBOARD DATA STRUCTURE

What currently flows through the frontend:

```typescript
DashboardResponse {
  title: string
  description: string
  
  kpis: Array<{
    id, title, value, unit, change, changeType,
    icon, color, target, status, category, ...
  }>
  
  charts: Array<{
    id, type (Area/Bar/Line/Pie/Radar/etc),
    title, size, chartConfig, data, insights
  }>
  
  tables: Array<{
    id, title, columns, data, pagination, sortable
  }>
  
  sections?: Array<{
    sectionId, title, summary, keyFindings,
    kpis, risks, recommendations, charts, confidence, ...
  }>
  
  optimizationSuggestions: Array<{
    id, title, category, impact, savings,
    description, implementation, ...
  }>
  
  insights: {
    summary: string
    trends: string[]
    alerts: Array<{type, message, severity}>
    recommendations: string[]
  }
  
  sixSigma: {
    sigmaLevel, defectRate, processCapability,
    dmaic: {define, measure, analyze, improve, control}
  }
}
```

---

## 🚀 VISUALIZATION CAPABILITIES

### Current (✅ Working)
- **Area Charts** - Time series, trends
- **Bar Charts** - Categorical comparisons
- **Line Charts** - Trend lines
- **Pie Charts** - Proportions
- **Radar Charts** - Multi-dimensional
- **Scatter Charts** - Correlations
- **Funnel Charts** - Pipeline/funnel
- **Composed Charts** - Mixed types
- **Sankey Charts** - Flow visualization (custom)
- **KPI Cards** - Metrics with trends

### Missing for Phase 5 (❌)
- **Entity Network Graph** - Node-link diagrams
- **Interactive Graph** - Click-through entities
- **Relationship Visualization** - Connection strength
- **Timeline** - Temporal relationships
- **Interactive 3D** - 3D graph visualization

---

## 📦 DEPENDENCIES

### Installed ✅
```json
{
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "react-router-dom": "^6.26.2",
  "typescript": "^5.5.3",
  "vite": "^5.4.1",
  "recharts": "^2.12.7",          // Chart library
  "@tremor/react": "^3.18.7",     // Data viz components
  "@tanstack/react-query": "^5.56.2",  // Caching/queries
  "axios": "^1.10.0",             // HTTP client
  "tailwindcss": "^3.4.11",       // CSS framework (dark)
  "zod": "^3.23.8",              // Schema validation
  "react-hook-form": "^7.53.0",   // Form handling
  "lucide-react": "^0.462.0",     // Icons
  "@radix-ui/*": "^1.x.x",        // UI primitives (20+ modules)
  "sonner": "^1.5.0",             // Toast notifications
  "jspdf": "^3.0.1",              // PDF export
  "html2canvas": "^1.4.1"         // Screenshot for PDF
}
```

### NOT Installed ❌ (Need for Phase 5)
```
vis-network                         // Recommended for entity graph
vis-data
D3.js (d3)                         // Alternative: more powerful
Cytoscape                          // Alternative: graph analysis
socket.io-client                   // Real-time updates
date-fns                           // Already have! Date handling
graphql-request                    // If using GraphQL
```

---

## 🔄 DATA FLOW: Upload → Display

```
1. User selects files on /upload page
                    ↓
2. api.uploadProject(files, options)
   POST /api/v2/generate-project
                    ↓
3. Get {task_id, doc_id, status}
   Store in DashboardContext + localStorage
                    ↓
4. Poll GET /api/v2/dashboard/status/{task_id}
   (every 2 seconds)
                    ↓
5. When complete, fetch GET /api/v2/dashboard/latest
                    ↓
6. Store response in DashboardContext
   (persists to localStorage)
                    ↓
7. Dashboard.tsx reads from context
   → DashboardRenderer composes UI
                    ↓
8. User sees KPIs, charts, insights, DMAIC, etc.
                    ↓
9. On page reload:
   Dashboard.tsx loads from localStorage
   Falls back to /api/v2/dashboard/latest if needed
```

---

## 🎯 WHAT'S READY FOR PHASE 5

### ✅ Backend Integration Points
- Dashboard container can accept new data
- DashboardContext will persist it
- API layer configured
- Authentication working
- localStorage persistence ready

### ✅ UI Infrastructure
- Progressive disclosure tabs exist
- Layout system in place
- shadcn/ui components available
- Tailwind dark theme ready
- Error boundaries configured

### ✅ Data Flow
- Query caching (React Query)
- State management (Context)
- API clients ready
- Search integration done

---

## ❌ WHAT'S MISSING FOR PHASE 5

### 1. Graph Visualization Library
- [ ] Install: `npm install vis-network vis-data`
- [ ] Or: D3.js, Cytoscape, react-force-graph
- [ ] Estimated effort: 1-2 hours

### 2. Entity Components
- [ ] EntityNetworkView (render graph)
- [ ] EntityDetailPanel (show details)
- [ ] RootCauseChainView (show RCA)
- [ ] EntitySearchUI (filter entities)
- [ ] Estimated effort: 8-12 hours

### 3. Integration Points
- [ ] Extend DashboardRenderer with new sections
- [ ] Add Intelligence tab to ProgressiveDisclosure
- [ ] Wire up entity click handlers
- [ ] Estimated effort: 4-6 hours

### 4. Advanced Features
- [ ] Recommendation provenance UI
- [ ] Timeline visualization
- [ ] Graph export (JSON-LD, GraphML)
- [ ] Real-time WebSocket updates
- [ ] Estimated effort: 8-16 hours (optional)

---

## 🔐 AUTHENTICATION FLOW

```
Login credentials
        ↓
Auth.tsx calls login endpoint
        ↓
Backend returns token
        ↓
localStorage.setItem('auth_token', token)
        ↓
axios interceptor adds:
Authorization: Bearer {token}
        ↓
Protected routes wrapped with <ProtectedRoute>
        ↓
401 response → logout + redirect to /auth
```

---

## 📱 RESPONSIVE DESIGN

- **Mobile first** approach
- **Tailwind breakpoints:** sm (640px), md (768px), lg (1024px), xl (1280px)
- **Dark theme** consistent throughout
- **Grid layouts** responsive: `grid-cols-1 md:grid-cols-2 lg:grid-cols-4`
- **Charts**: ResponsiveContainer (auto-resize)

---

## ⚡ PERFORMANCE NOTES

### Current State
- React Query caching (5-min stale time)
- localStorage persistence for instant reload
- Lazy component loading via React Router
- No visible performance issues reported

### Phase 5 Considerations
- Large entity networks (>500 nodes) may need:
  - Virtualization / pagination
  - Clustering algorithms
  - Dynamic edge filtering (show only >70% confidence)
  - Progressive loading

---

## 🧪 TESTING & DEMO

### DemoPage.tsx
- Hardcoded demo data with all chart types
- Useful for UI development without backend

### ConfusionMatrix.tsx
- Test ML model metrics
- Accepts CSV or JSON input

### No Unit Tests
- No Jest/Vitest configuration found
- Consider adding before Phase 5 release

---

## 🎨 THEME & STYLING

### Color Palette
```
Primary:    Cyan/Teal    (#06b6d4, #10b981)
Secondary:  Amber/Orange (#f59e0b, #ef4444)
Accent:     Purple       (#8b5cf6, #3b82f6)
Success:    Green        (#10b981)
Warning:    Amber        (#f59e0b)
Error:      Red          (#ef4444)
```

### Dark Mode
```
Background: slate-900, slate-800
Text:       white, slate-300, slate-400
Border:     slate-700, slate-600
```

---

## 📋 PAGES AT A GLANCE

| Page | Route | Component | Purpose |
|------|-------|-----------|---------|
| Landing | `/` | Index.tsx | Intro/navigation |
| Login | `/auth` | Auth.tsx | Authentication |
| Upload | `/upload` | Upload.tsx | File ingestion |
| **Dashboard** | `/dashboard` | **Dashboard.tsx** | **PRIMARY display** |
| Search | `/search` | Search.tsx | Hybrid search |
| Metrics | `/confusion-matrix` | ConfusionMatrix.tsx | Model performance |
| Demo | `/demo` | DemoPage.tsx | Hardcoded demo |
| Profile | `/profile` | UserProfile.tsx | User settings |
| 404 | `*` | NotFound.tsx | Error page |

---

## 🚦 QUICK START (With Phase 5 Data)

1. **Backend sends** `intelligent_entity_network` in dashboard response
2. **Frontend installs:** `npm install vis-network vis-data`
3. **Create EntityNetworkView** component (see guide)
4. **Modify DashboardRenderer** to display it
5. **Test:** Upload file, see graph render
6. **Deploy:** Push to production

**Total Time:** ~2-3 days for experienced dev

---

## 📚 RECOMMENDED READING

| File | Purpose |
|------|---------|
| FRONTEND_ARCHITECTURE_ANALYSIS.md | Deep dive (detailed) |
| FRONTEND_ARCHITECTURE_DIAGRAMS.md | Visual overview (diagrams) |
| PHASE5_FRONTEND_IMPLEMENTATION_GUIDE.md | Step-by-step integration |
| src/types/dashboard.ts | Current data schema |
| src/components/DashboardRenderer.tsx | Main composition logic |

---

## 🎯 IMPLEMENTATION CHECKLIST FOR PHASE 5

### Phase 5a: Preparation
- [ ] Review this document with frontend team
- [ ] Choose graph visualization library (recommend: vis.js)
- [ ] Design EntityNetworkView component
- [ ] Plan backend API extensions

### Phase 5b: Development (2-3 days)
- [ ] Install vis-network + vis-data
- [ ] Create EntityNetworkView component
- [ ] Create EntityDetailPanel component
- [ ] Create RootCauseChainView component
- [ ] Modify DashboardRenderer.tsx
- [ ] Extend ProgressiveDisclosureView with Intelligence tab
- [ ] Wire up entity click handlers
- [ ] Test with mock data

### Phase 5c: Backend Integration
- [ ] Backend extends DashboardResponse
- [ ] Add intelligent_entity_network field
- [ ] Add root_cause_analysis field
- [ ] Add recommendations_with_provenance
- [ ] Test with real Phase 5 data

### Phase 5d: Testing & Polish
- [ ] Unit test components
- [ ] Integration test data flow
- [ ] Responsive design checks
- [ ] Performance testing (large graphs)
- [ ] Accessibility audit
- [ ] User acceptance testing

### Phase 5e: Deployment
- [ ] Code review
- [ ] Security audit
- [ ] Performance optimization
- [ ] Deploy to staging
- [ ] Deploy to production
- [ ] Monitor for errors

---

## ✅ SUMMARY

**Current State:** 60% ready for Phase 5
- ✅ Dashboard infrastructure ready
- ✅ State management ready
- ✅ API layer ready
- ❌ Graph visualization library missing
- ❌ Entity display components missing
- ❌ Integration code needed

**Time to Production:** 2-3 weeks (development + testing)

**Complexity:** Medium (straightforward integration, well-documented)

**Risk:** Low (existing infrastructure solid, new components can be added incrementally)

---

**Last Updated:** March 27, 2025  
**For Questions:** See PHASE5_FRONTEND_IMPLEMENTATION_GUIDE.md
