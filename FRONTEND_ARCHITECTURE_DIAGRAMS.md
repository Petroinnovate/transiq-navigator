# TransIQ Frontend - Current Architecture Diagram

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRANSIQ FRONTEND (React + Vite)                      │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        React Router (BrowserRouter)                  │   │
│  │                                                                      │   │
│  │  /upload ──→ Upload.tsx           /dashboard ──→ Dashboard.tsx     │   │
│  │             (file selection)                    (primary display)   │   │
│  │  /search ──→ Search.tsx           /auth ──────→ Auth.tsx          │   │
│  │             (hybrid search)                    (login)              │   │
│  │  /confusion-matrix ──→ ConfusionMatrix.tsx (model metrics)        │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    State Management (DashboardContext)              │   │
│  │                                                                      │   │
│  │  • dashboardData: DashboardResponse  (React Context)               │   │
│  │  • files: File[]                    (Selected files)               │   │
│  │  • projectMeta: ProjectMeta         (Upload metadata)              │   │
│  │  • isLoading, error, progress       (UI state)                     │   │
│  │                                                                      │   │
│  │  ↔ localStorage persistence (keys: transiq_dashboard_data)        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       Authentication Layer                          │   │
│  │                                                                      │   │
│  │  Token stored in localStorage                                      │   │
│  │  axios interceptor adds: Authorization: Bearer {token}            │   │
│  │  401 response → logout & redirect to /auth                        │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ axios (http client)
                                      │
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BACKEND API (FastAPI @ localhost:8001)                    │
│                                                                               │
│  Endpoints:                                                                  │
│  ├─ POST   /api/v2/generate              (single file upload)               │
│  ├─ POST   /api/v2/generate-batch        (2-5 files)                       │
│  ├─ POST   /api/v2/generate-project      (6-20 files, auto-batched)       │
│  ├─ GET    /api/v2/dashboard/latest      (fetch latest report)            │
│  ├─ GET    /api/v2/dashboard/{reportId}  (fetch specific report)          │
│  ├─ GET    /api/v2/dashboard/status/{taskId} (check progress)            │
│  ├─ GET    /api/v2/documents/{docId}     (document metadata)              │
│  ├─ GET    /api/v2/documents/{docId}/chunks (document chunks)           │
│  ├─ POST   /api/v2/documents/search      (hybrid search)                 │
│  └─ GET    /api/v2/dashboard/{reportId}/export/pdf (PDF export)         │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Dashboard Component Hierarchy

```
┌──────────────────────────────────────────────────────────────────┐
│ Dashboard.tsx (Page Container)                                   │
│  • Fetches data from DashboardContext or /dashboard/latest       │
│  • Error boundary for rendering crashes                          │
│  • Loading skeleton display                                      │
└──────────────────────────────────────────────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────────────────────────────┐
│ DashboardLayout (Visual Wrapper)                                 │
│  • Navigation, branding, layout structure                        │
└──────────────────────────────────────────────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────────────────────────────┐
│ DashboardRenderer (Composition Engine)                           │
│  • Renders KPIs, charts, tables, insights, sections              │
│  • Handles progressive disclosure view switching                 │
└──────────────────────────────────────────────────────────────────┘
               │
    ┌──────────┼──────────┬─────────┬─────────┬────────────┐
    ↓          ↓          ↓         ↓         ↓            ↓
  KPIs      Charts     Tables   Insights   Sections  Optimization
  ────      ──────     ──────   ────────   ─────────  ────────────
  • Card    • Area     • Paged  • Summary  • Title    • Suggestions
  • Trend   • Bar      • Sort   • Alerts   • Findings • Impact
  • Status  • Line     • Export • Recom.   • KPIs     • Risks
  • Target  • Pie                         • Insights • Cost
  • Color   • Radar
  • Icon    • Scatter
            • Funnel
            • Composed
            • Sankey

    └──────┬──────────────────────┬────────────────────┘
           ↓                      ↓
       ┌────────────────────────────────────────────────┐
       │ Progressive Disclosure View (6 Tabs)           │
       │                                                │
       │ CEO View      → 3 decisions, 3 risks, 3 actions│
       │ Manager View  → DMAIC + KPI tracking           │
       │ Engineer View → Full technical depth           │
       │ Boardroom     → Slide-ready narrative          │
       │ Audit Trail   → Model explainability           │
       │ Outcomes      → Decision → $ impact            │
       └────────────────────────────────────────────────┘
```

## Data Flow: Upload → Processing → Display

```
┌─────────────┐
│ User Uploads│
│  CSV/Excel  │
│    /PDF     │
└──────┬──────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ Upload.tsx                               │
│ • File selection / drag-drop             │
│ • Provider selection (Gemini/OpenAI)     │
│ • Options: deduction, patterns, etc.    │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│ api.uploadProject(files, options)        │
│ POST /api/v2/generate-project            │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│ Backend Processing                       │
│ • LLM analysis                           │
│ • DMAIC framework                        │
│ • KPI extraction                         │
│ • Chart generation                       │
│ • Six Sigma analysis                     │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│ Return { task_id, doc_id, status }       │
│ Store in DashboardContext + localStorage │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│ Poll Processing Status                   │
│ GET /api/v2/dashboard/status/{taskId}    │
│ Every 2 seconds until complete           │
└──────────┬───────────────────────────────┘
           │
           ↓ (when complete)
┌──────────────────────────────────────────┐
│ Fetch Dashboard Data                     │
│ GET /api/v2/dashboard/latest             │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│ Store in DashboardContext                │
│ (also persists to localStorage)          │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│ Dashboard.tsx displays data              │
│ • useEffect checks context first         │
│ • Falls back to /dashboard/latest        │
│ • Renders via DashboardRenderer          │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│ User sees:                               │
│ ✓ KPI cards with metrics                │
│ ✓ Charts and visualizations             │
│ ✓ Insights and recommendations          │
│ ✓ DMAIC framework breakdown             │
│ ✓ Progressive disclosure tabs           │
└──────────────────────────────────────────┘
```

## Current Technology Stack

```
Frontend Layer:
├─ React 18.3           (UI framework)
├─ TypeScript 5.5       (type safety)
├─ React Router 6       (routing)
├─ Vite                 (build tool)
│
Visualization:
├─ recharts 2.12        (charts: area, bar, line, pie, radar, etc.)
├─ @tremor/react 3      (additional data viz)
├─ lucide-react         (icons)
│
State & Data Fetching:
├─ React Context        (DashboardContext)
├─ TanStack Query 5     (React Query - caching)
├─ axios 1.10           (HTTP client)
├─ localStorage         (persistence)
│
Forms & Validation:
├─ react-hook-form 7   (form handling)
├─ zod 3.23             (schema validation)
│
Styling:
├─ Tailwind CSS 3       (utility CSS)
├─ shadcn/ui            (component library)
├─ Radix UI             (unstyled primitives)
├─ classnames (clsx)    (class composition)
│
UI Components:
├─ Radix UI dialogs, tooltips, dropdowns, etc.
├─ shadcn/ui buttons, cards, forms, etc.
├─ embla-carousel       (carousel)
└─ sonner               (toast notifications)

NOT INSTALLED (would be needed for Phase 5):
├─ vis.js / vis-network (graph visualization)
├─ D3.js                (advanced visualization)
├─ Cytoscape            (graph analysis)
├─ Three.js             (3D rendering)
├─ Socket.io            (WebSocket)
└─ GraphQL client       (if using GraphQL)
```

## Search Architecture

```
┌──────────────────────┐
│   Search.tsx         │
│  (User enters query) │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│ api.searchDocuments({                    │
│   query: string                          │
│   top_k: 10                              │
│   use_hybrid: true                       │
│ })                                       │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│ Backend Hybrid Search                    │
│                                          │
│ BM25 Search       +    Semantic Search   │
│ (keyword match)        (vector embed)    │
│       │                      │           │
│       └──────────┬───────────┘           │
│                  ↓                       │
│         Combined Ranking                │
│         (hybrid score)                   │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│ SearchResult[]                           │
│ [                                        │
│   {                                      │
│     index: 1,                            │
│     text: string,                        │
│     bm25_score: 0.8,                     │
│     semantic_score: 0.85,                │
│     combined_score: 0.83                 │
│   },                                     │
│   ...                                    │
│ ]                                        │
└──────────┬───────────────────────────────┘
           │
           ↓
┌──────────────────────────────────────────┐
│ Display results in SearchPage            │
│ • Show top 10 results                    │
│ • Display scores                         │
│ • Show document source                   │
│ • Highlight matches                      │
└──────────────────────────────────────────┘
```

## Missing Components for Phase 5

```
Intelligence Engine Data (from backend):
├─ Entities (discovered)
├─ Relationships (connections)
├─ Root Causes (analysis)
├─ Impact Chains (cascading effects)
└─ Confidence Scores (model certainty)
        │
        ↓ (needs visualization)
        
Missing Components:
├─ EntityNetworkView ❌
│  └─ Interactive graph of entities + relationships
│
├─ EntityDetailPanel ❌
│  └─ Slide-in showing entity properties & connections
│
├─ RootCauseChainDiagram ❌
│  └─ Visualizes cause-effect relationships
│
├─ RecommendationProvenanceView ❌
│  └─ Explains why each recommendation was made
│
├─ IntelligenceTimelineView ❌
│  └─ Temporal view of entity/relationship discovery
│
├─ EntitySearchUI ❌
│  └─ Filter & search entities by type, name, confidence
│
├─ KnowledgeGraphExport ❌
│  └─ Download graph as JSON-LD, GraphML, etc.
│
└─ Graph Visualization Library ❌
   └─ vis.js, D3.js, or Cytoscape (not in dependencies)
```

## Upload Processing Batch Limits

```
User uploads files
│
├─ 1 file          → api.uploadDocument()
│                    Async processing
│
├─ 2-5 files       → api.uploadDocuments()
│                    Batch processing
│
└─ 6-20 files      → api.uploadProject()
                     Auto-batched by backend (5-file chunks)
                     Results: merged_dashboard

Max 20 files per upload.
```

---

This diagram illustrates:
1. ✅ **Current working components** - Upload, Dashboard, Search
2. ✅ **Existing infrastructure** - DashboardContext, API layer, authentication
3. ❌ **Missing for Phase 5** - Graph visualization, entity display, intelligence UI
4. 📊 **Data flow** - How data moves from upload to display
5. 🔌 **Integration points** - Where Phase 5 intelligence data would connect
