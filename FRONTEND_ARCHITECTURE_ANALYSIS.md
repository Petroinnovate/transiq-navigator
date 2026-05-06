# TransIQ Frontend Architecture Analysis
## Phase 5 Intelligence Engine Integration Readiness Assessment

**Analysis Date:** March 27, 2025  
**Scope:** Complete frontend codebase exploration  
**Focus:** Understanding current UI structure & Phase 5 integration requirements

---

## 1. PAGES & ROUTING STRUCTURE

### Current Pages (src/pages/)
```
├── Index.tsx              # Landing page
├── Auth.tsx               # Login/authentication
├── Upload.tsx            # File ingestion (CSV, Excel, PDF)
├── Dashboard.tsx         # PRIMARY: Main analytics dashboard
├── Search.tsx            # Hybrid document search (BM25 + semantic)
├── ConfusionMatrix.tsx   # ML model performance analysis
├── DemoPage.tsx          # Demo with hardcoded chart examples
├── UserProfile.tsx       # User settings (protected)
├── NotFound.tsx          # 404 error page
```

### Route Mapping (App.tsx)
```
/              → Landing
/auth          → Authentication page
/upload        → File upload & processing
/dashboard     → Main analytics dashboard ⭐
/search        → Search interface
/confusion-matrix → Model metrics (classification)
/demo          → Demo visualization page
/profile       → User profile (protected route)
*              → 404 Not Found
```

**Key Observation:** Dashboard is the primary display surface. All processed data flows here.

---

## 2. COMPONENT ARCHITECTURE

### Component Hierarchy for Dashboard Display

```
Dashboard.tsx (page)
├── DashboardLayout (wrapper)
└── DashboardRenderer (composition engine)
    ├── KPICard[] (metrics display)
    ├── ChartRenderer[] (dynamic charts)
    │   ├── AreaChart
    │   ├── BarChart
    │   ├── LineChart
    │   ├── PieChart
    │   ├── RadarChart
    │   ├── ScatterChart
    │   ├── FunnelChart
    │   ├── ComposedChart
    │   └── SankeyChart (flow/process)
    ├── DataTable[] (tabular data)
    ├── OptimizationSuggestions[]
    ├── InsightsSection (alerts & recs)
    ├── SixSigmaSection (DMAIC)
    ├── AlertPanel (critical issues)
    ├── ProgressiveDisclosureView (audience layers)
    │   ├── CEOView       # 30-sec snapshot
    │   ├── ManagerView   # DMAIC + KPIs
    │   ├── EngineerView  # Full technical depth
    │   ├── BoardroomMode # Slide-ready narrative
    │   ├── AuditTrail    # Explainability
    │   └── OutcomesView  # Decision → $ impact
    └── View ModeToggle (expandable/collapsible)
```

### Component Directory Structure

| Directory | Components | Purpose |
|-----------|-----------|---------|
| `/components/charts/` | ChartRenderer | Advanced chart rendering |
| `/components/insights/` | InsightsAlerts | Executive alerts & recommendations |
| `/components/predictive/` | Dashboard, Insights, WhatIfSimulator | Forecasting & scenario analysis |
| `/components/progressive/` | DisclosureView, CEOView, ManagerView, EngineerView, BoardroomMode | Audience-specific abstraction layers |
| `/components/confusion/` | Heatmap, MetricsPanel | ML model performance |
| `/components/optimization/` | Panel, Suggestions | Cost/efficiency recommendations |
| `/components/explainability/` | Model explanation components | Feature importance & reasoning |
| `/components/six-sigma/` | SixSigmaSection | DMAIC process framework |
| `/components/tremor-widgets/` | Custom tremor adaptations | Enhanced data viz |
| `/components/ui/` | shadcn/ui base components | Button, Card, Badge, etc. |
| `/components/layout/` | DashboardLayout | Dashboard wrapper & nav |

### Key Component Interfaces

```typescript
// Dashboard data structure
DashboardRenderer expects: {
  title: string
  description: string
  kpis: KPI[]                           // Metric cards
  charts: Chart[]                       // Visual charts
  tables: DataTable[]                   // Tabular data
  sections: SectionAnalysis[]           // Multi-page document analysis
  optimizationSuggestions: Suggestion[] // AI recommendations
  insights: Insights                    // Alerts + trends
  sixSigma: DMAIC                       // Structure improvement
  predictive: Forecast[]                // Time series predictions
  
  // Progressive disclosure layers
  ceo_view: CeoView
  manager_view: ManagerView
  engineer_view: EngineerView
  boardroom_mode: BoardroomMode
  audit_trail: AuditTrail
  outcome_driven_decisions: Decision[]
}
```

---

## 3. VISUALIZATION CAPABILITIES

### Chart Types (via recharts library)

| Chart Type | Use Case | Example |
|-----------|----------|---------|
| **AreaChart** | Time series with area fill | Sales trend over time |
| **BarChart** | Categorical comparisons | Department performance |
| **LineChart** | Trend lines | Stock price movement |
| **ComposedChart** | Mixed bar + line | Sales vs. Target |
| **PieChart** | Proportional breakdown | Market share by segment |
| **RadarChart** | Multi-dimensional metrics | Capability assessment |
| **RadialBarChart** | Circular metrics | Gauge-like displays |
| **ScatterChart** | Correlation visualization | X vs. Y relationships |
| **FunnelChart** | Process funnel (drop-off) | Sales pipeline |
| **SankeyChart** | Flow/node-link diagrams | Process flow, relationships |

### Widget Priority System (visualizationEngine.ts)

Widgets auto-generate with priority ranking:
1. **KPI Summary** (priority 100) - Top metrics
2. **Alert Generator** (90) - Critical issues
3. **Trend Analysis** (80) - Historical patterns
4. **Performance Gaps** (70) - Under-performing areas
5. **Benchmarking** (60) - Comparisons
6. **Optimization** (50) - Cost/efficiency suggestions
7. **Forecasting** (40) - Predictions

**Smart chart selection rules:**
- Time series (>3 points) → Line or Area
- Categorical (≤5 items) → Pie
- Multi-series (>3) → Radar
- Default → Bar chart

---

## 4. API INTEGRATION PATTERNS

### Architecture Overview

```
Frontend (React)
    ↓ (axios with auth interceptor)
API Client (lib/axios.ts)
    ↓ 
Backend Service Layer (endpoints below)
    ↓
LLM/Analysis Engine
```

### API Base Configuration
- **Base URL:** `http://localhost:8001` (configurable via `VITE_API_URL`)
- **Authentication:** Bearer token (auto-injected via axios interceptor)
- **Request Timeout:** Default axios (30s)
- **Error Handling:** 401 → redirect to /auth

### API Endpoints Consumed

#### Dashboard Endpoints
```
GET  /api/v2/dashboard/latest           # Fetch latest dashboard
GET  /api/v2/dashboard/{reportId}       # Fetch specific report
GET  /api/v2/dashboard/{reportId}/export/pdf    # PDF export
GET  /api/v2/dashboard/{reportId}/export/excel  # Excel export
GET  /api/v2/dashboard/status/{taskId}  # Check processing status
```

#### File Upload Endpoints
```
POST /api/v2/generate                   # Single file (1 file)
POST /api/v2/generate-batch             # Batch (2-5 files)
POST /api/v2/generate-project           # Project (6-20 files, auto-batched)
```

#### Document Endpoints
```
GET  /api/v2/documents/{docId}          # Document metadata
GET  /api/v2/documents/{docId}/chunks   # Document chunks
```

#### Search Endpoints
```
POST /api/v2/documents/search           # Hybrid search (BM25 + semantic)
```

### Upload Response Shape
```typescript
{
  doc_id: string
  task_id: string
  status: 'processing' | 'completed' | 'failed'
  message: string
  dashboard?: DashboardResponse  // If synchronous
  processing_time?: number
  files_processed?: number
}
```

### API Service Layer (src/services/api.ts)

**Upload Functions:**
```typescript
api.uploadDocument(file, options)       // Single file
api.uploadDocuments(files, options)     // Batch (2-5)
api.uploadProject(files, options)       // Project (6-20)
```

**Options:**
```typescript
{
  provider?: 'gemini' | 'openai'
  enable_deduction?: boolean
  enable_patterns?: boolean
}
```

**Document Functions:**
```typescript
api.getDocument(docId)                  // Fetch metadata
api.getDocumentChunks(docId)            // Fetch chunks
api.searchDocuments(SearchRequest)      // Hybrid search
```

### Dashboard Query Layer (src/api/dashboardApi.ts)

React Query integration with pre-configured queries:
```typescript
dashboardQueries.byId(reportId)         # Stale time: 5 min
dashboardQueries.latest()               # Always fresh, no cache
dashboardQueries.processing(taskId)     # Poll every 2 sec
```

---

## 5. STATE MANAGEMENT & DATA FLOW

### React Context: DashboardContext

**Purpose:** Centralized dashboard state with localStorage persistence

**Stored Properties:**
```typescript
dashboardData: DashboardResponse | null
projectMeta: ProjectMeta | null        # Multi-file project metadata
isLoading: boolean
error: string | null
files: File[]                           # Selected files
docId: string | null
taskId: string | null
reportId: string | null
progress: number                        # Processing %
```

**Storage Keys:**
- `transiq_dashboard_data` - Main dashboard
- `transiq_project_meta` - Project metadata

### Data Flow (Upload → Display)

```
1. User selects files in Upload.tsx
   ↓
2. Click "Process" → api.uploadProject(files)
   ↓
3. Backend returns { task_id, doc_id, status }
   ↓
4. Store in DashboardContext + localStorage
   ↓
5. Poll /api/v2/dashboard/status/{taskId} every 2s
   ↓
6. When complete, fetch /api/v2/dashboard/latest
   ↓
7. Store dashboard response in context
   ↓
8. Dashboard.tsx fetches from context (or localStorage if reload)
   ↓
9. DashboardRenderer composes UI from response
```

### React Query (TanStack Query)
- **QueryClient** configured with 5-minute stale time
- Used for `/dashboard` and `/dashboard/latest` endpoints
- Polling for async task status

### Search Data Flow
```
Search.tsx → handleSearch()
    ↓
api.searchDocuments({ query, top_k: 10, use_hybrid: true })
    ↓
Backend (hybrid BM25 + semantic)
    ↓
Response: { query, results[], count }
    ↓
Display in SearchPage component (top 10 results)
```

---

## 6. DASHBOARD DATA STRUCTURE (Backend Response)

### Top-Level Schema

```typescript
DashboardResponse {
  // Metadata
  meta: {
    reportId: string
    ingestedAt: string
    sourceType: string
    confidenceOverall: number
    decisionReadinessScore: number
    sectionsAnalyzed?: number
  }

  // Classification
  autoClassification: {
    reportType: string[]
    assetScope: string
    decisionLevel: string
    confidence: number
  }

  // Core Data
  kpis: KPI[]                           // Metric cards
  charts: Chart[]                       // Visual charts
  tables: DataTable[]                   // Tabular data
  sections: SectionAnalysis[]           # Multi-page analysis
  
  // Quality Framework
  sixSigma: {
    sigmaLevel: string
    defectRate: string
    dmaic: {
      define: { ... }
      measure: { ... }
      analyze: { ... }
      improve: { ... }
      control: { ... }
    }
  }

  // Recommendations
  optimizationSuggestions: Optimization[]
  insights: {
    summary: string
    trends: string[]
    alerts: Alert[]
    recommendations: Recommendation[]
  }

  // Forecasting
  predictive: Forecast[]

  // Explainability
  explainability: ModelExplanation

  // Progressive Disclosure Layers
  ceo_view: CeoView                     # 30-sec executive snapshot
  manager_view: ManagerView             # DMAIC + KPI tracking
  engineer_view: EngineerView           # Full technical depth
  boardroom_mode: BoardroomMode         # Slide-ready narrative
  audit_trail: AuditTrail               # Explainability & reasoning
  outcome_driven_decisions: Decision[]  # Decision → $ impact
}
```

### KPI Structure
```typescript
KPI {
  id: string
  title: string
  value: number
  unit: string
  change: string                        // E.g., "+12.5%"
  changeType: 'positive' | 'negative' | 'neutral'
  icon: string                          // Icon name
  color: string                         // Hex color
  sparkData?: Array<{ v: number }>    # Mini trend line
  category?: string                     // Financial, operational, etc.
  status?: 'good' | 'warning' | 'critical'
  target?: number
  priorityScore?: number                // AI-assigned priority
  visibility?: 'primary' | 'secondary' | 'hidden'
}
```

### Chart Structure
```typescript
Chart {
  id: string
  type: 'AreaChart' | 'BarChart' | 'LineChart' | ...
  title: string
  subtitle?: string
  size: 'full' | 'half' | 'third' | 'quarter'
  chartConfig: {
    xAxis?: { dataKey: string; label: string; type: 'category' | 'number' | 'time' }
    yAxis?: { label: string; domain: [min, max] }
    series?: Array of data series
    composedComponents?: Mixed series for ComposedChart
  }
  data: Array<Record<string, any>>     # Actual data points
  insights?: string[]                  # Auto-generated or backend-provided
}
```

---

## 7. STATE OF INTELLIGENCE ENGINE INTEGRATION

### ✅ WHAT'S READY FOR PHASE 5

1. **Dashboard Container** - DashboardRenderer can accept new data structures
2. **Progressive Disclosure UI** - ProgressiveDisclosureView already exists with CEO/Manager/Engineer/Audit layers
3. **Insights Infrastructure** - Alerts, recommendations, explainability structure defined
4. **API Layer** - Axios configured, authentication working, query caching ready
5. **Data Persistence** - localStorage + React Context for state management
6. **Search Integration** - Hybrid search endpoint available
7. **Section Analysis** - Multi-section/multi-page document support built-in
8. **DMAIC Framework** - Six Sigma structure in types, SixSigmaSection component ready

### ❌ WHAT'S MISSING FOR PHASE 5

1. **Graph/Network Visualization**
   - No D3.js, vis.js, Cytoscape, or similar libraries installed
   - Sankey diagram exists (flow visualization) but not entity networks
   - **Impact:** Cannot visualize entity relationships, intelligence network, RCA chains

2. **Entity Display Components**
   - No EntityCard, EntityDetail, EntityRelationship components
   - No entity filtering/search UI
   - No entity type badges or hierarchy visualization
   - **Impact:** Cannot display entities from intelligent entity network

3. **Real-time Updates**
   - No WebSocket support
   - No live update streaming
   - **Impact:** Dashboard is request-response only, no live intelligence feed

4. **Knowledge Graph Export**
   - No graph serialization (JSON-LD, GraphML, etc.)
   - **Impact:** Cannot export Phase 5 intelligence data

5. **Relationship Confidence UI**
   - No visualization of relationship confidence/similarity scores
   - Edge weight/opacity visualization not available
   - **Impact:** Cannot show connection strength in graphs

6. **Intelligent Navigation**
   - No drill-down from KPIs → entities → source documents
   - No provenance tracking (showing why a recommendation was made)
   - **Impact:** Users cannot trace recommendations back to intelligence source

7. **Timeline/Temporal Visualization**
   - No interactive timeline component
   - No temporal clustering visualization
   - **Impact:** Cannot show relationship evolution over time

### Libraries in Use (package.json)

**Visualization:**
- recharts 2.12.7 (charts, Sankey support)
- @tremor/react 3.18.7 (additional data viz)
- lucide-react 0.462.0 (icons)

**NOT installed:**
- D3.js
- vis.js
- Cytoscape
- Three.js
- Graphviz
- Any graph visualization tool

---

## 8. AUTHENTICATION & SECURITY

### Flow
```
User logs in (Auth.tsx)
    ↓
Token stored in localStorage['auth_token']
    ↓
axios interceptor injects: Authorization: Bearer {token}
    ↓
Protected routes wrapped with <ProtectedRoute> component
    ↓
401 response → logout + redirect to /auth
```

### Protected Route
```typescript
<Route path="/profile" element={
  <ProtectedRoute>
    <UserProfile />
  </ProtectedRoute>
} />
```

---

## 9. TESTING & DEMO

### DemoPage.tsx
- Hardcoded demo data with all chart types
- Useful for UI testing without backend
- Shows expected data shapes

### ConfusionMatrix.tsx
- Accepts CSV file with y_true, y_pred columns
- Or manual JSON input for quick testing
- Returns: metrics, per-class analysis, risk flags, insights

### No Unit Testing
- No Jest/Vitest setup detected
- No test files in repository

---

## 10. TESTING THE CURRENT SYSTEM

### Quick Test Flow

1. **Start Backend**
   ```bash
   cd TransIQ-backend-master
   python main.py
   ```

2. **Start Frontend**
   ```bash
   cd TransIQ-frontend-main
   npm run dev
   ```

3. **Upload a File**
   - Navigate to `/upload`
   - Select CSV/Excel/PDF
   - Choose provider (Gemini/OpenAI)
   - Click "Process"

4. **View Dashboard**
   - Redirects to `/dashboard` when processing completes
   - Shows KPIs, charts, insights, DMAIC info

5. **Search Documents**
   - Go to `/search`
   - Enter query
   - Get hybrid search results

---

## 11. FRONTEND INTEGRATION POINTS FOR PHASE 5

### Recommended Integration Points

#### A. Dashboard Extension (Minimal Changes)
```typescript
// Phase 5 data added to existing DashboardResponse
DashboardResponse {
  ...existing fields...
  
  // NEW: Intelligent Entity Network
  intelligent_entity_network?: {
    entities: Entity[]                    // Discovered entities
    relationships: Relationship[]         // Entity connections
    confidence_distribution: {}           // Confidence stats
    top_entities: Entity[]                // Ranked by impact
  }
  
  // NEW: Root Cause Analysis
  root_cause_analysis?: {
    root_causes: RootCause[]
    impact_chain: ImpactChain[]           // How RCA affects KPIs
    remediation: Remediation[]
  }
  
  // NEW: Recommendations Provenance
  recommendations_with_provenance?: Array<{
    recommendation: Recommendation
    source_entities: Entity[]
    confidence: number
    reasoning: string
  }>
  
  // NEW: Entity-KPI Links
  entity_kpi_links?: Array<{
    entity: Entity
    kpis: string[]                        // KPI IDs impacted
    impact_type: 'positive' | 'negative'
    impact_magnitude: number
  }>
}
```

#### B. New Components Needed

**High Priority:**
1. `EntityNetworkView` component
   - Renders interactive entity graph
   - Uses vis.js or similar library
   - Shows entities as nodes, relationships as edges

2. `EntityDetailPanel` component
   - Slide-in panel for entity details
   - Shows properties, connections, source documents
   - Confidence score display

3. `RootCauseChainView` component
   - Visualizes cause-effect relationships
   - Shows impact on KPIs
   - Links to remediation suggestions

**Medium Priority:**
4. `RecommendationProvenanceView` component
   - Explains why a recommendation was made
   - Links to supporting entities
   - Shows confidence & source data

5. `IntelligenceTimelineView` component
   - Temporal view of relationships
   - Shows how understanding evolved

6. `ComparisonMatrixView` component
   - Compare entities side-by-side
   - Show similarity scores

**Low Priority:**
7. `KnowledgeGraphExportUI` component
   - Export graph as JSON-LD, GraphML
   - Download options

#### C. API Endpoints Expected

```
GET  /api/v2/intelligence/entities              # All entities
GET  /api/v2/intelligence/entities/{entityId}   # Entity details
GET  /api/v2/intelligence/relationships         # All relationships
GET  /api/v2/intelligence/graph                 # Full graph data
GET  /api/v2/intelligence/root-causes           # RCA chains
POST /api/v2/intelligence/search-entities       # Search entities
GET  /api/v2/intelligence/entity-types          # Entity type metadata
```

#### D. Extension Points in DashboardRenderer

```typescript
// Current flow:
export const DashboardRenderer = ({ dashboardData }) => {
  // Render KPIs, charts, insights...
  
  // NEW: Add intelligence sections
  if (dashboardData.intelligent_entity_network) {
    return (
      <>
        {/* Existing sections */}
        {/* NEW */}
        <EntityNetworkView data={dashboardData.intelligent_entity_network} />
        <RootCauseChainView data={dashboardData.root_cause_analysis} />
        <RecommendationsProvenanceView 
          recs={dashboardData.recommendations_with_provenance} 
        />
      </>
    )
  }
}
```

#### E. Progressive Disclosure Updates

Extend ProgressiveDisclosureView tabs:
```typescript
const TABS = [
  { id: 'ceo', label: 'CEO View' },          // ✅ Exists
  { id: 'manager', label: 'Manager View' },  // ✅ Exists
  { id: 'engineer', label: 'Engineer View' },// ✅ Exists
  { id: 'boardroom', label: 'Boardroom' },   // ✅ Exists
  { id: 'audit', label: 'Audit Trail' },     // ✅ Exists
  { id: 'outcomes', label: 'Outcomes' },     // ✅ Exists
  
  // NEW for Phase 5:
  { id: 'intelligence', label: 'Intelligence Network' },  // Entity graph
  { id: 'root-causes', label: 'Root Causes' },           // RCA chains
  { id: 'recommendations', label: 'Recommendations' },   // With provenance
];
```

---

## 12. IMPLEMENTATION ROADMAP FOR PHASE 5 FRONTEND

### Phase 5a: Install Graph Visualization
```bash
npm install vis-network vis-data
# OR
npm install cytoscape cytoscape-fcose
# OR
npm install react-force-graph
```

### Phase 5b: Create Core Intelligence Components
1. `IntelligenceNetworkView` - Entity graph visualization
2. `EntityDetailPanel` - Entity information display
3. `RootCauseChainDiagram` - Cause-effect visualization
4. `RecommendationProvenanceCard` - Explanation of recommendations

### Phase 5c: Add Intelligence Tab to Dashboard
1. Extend ProgressiveDisclosureView with "Intelligence" tab
2. Add EntityNetworkView to DashboardRenderer
3. Wire up new API endpoints

### Phase 5d: Search Enhancement
1. Extend Search.tsx for entity search
2. Add entity type filters
3. Show confidence scores

### Phase 5e: Real-time Updates (Optional)
1. Add WebSocket support
2. Implement live intelligence feed
3. Real-time relationship updates

---

## 13. KEY FINDINGS SUMMARY

| Aspect | Status | Notes |
|--------|--------|-------|
| **Dashboard Container** | ✅ Ready | Can extend with new data sections |
| **Chart Visualization** | ✅ Good | Recharts covers basic needs |
| **Progressive Disclosure** | ✅ Ready | CEO/Manager/Engineer/Boardroom layers exist |
| **API Integration** | ✅ Ready | Axios, auth, query caching all configured |
| **State Management** | ✅ Ready | Context + localStorage working |
| **Graph Visualization** | ❌ Missing | Critical for Phase 5 intelligence display |
| **Entity Components** | ❌ Missing | No entity display infrastructure |
| **Real-time Updates** | ❌ Missing | No WebSocket support |
| **Testing** | ⚠️ Basic | Demo page exists, no unit tests |
| **Security** | ✅ Good | Bearer token + protected routes |

---

## 14. RECOMMENDED ACTIONS

### Immediate (This Sprint)
1. ✅ Review this analysis with frontend team
2. ✅ Choose graph visualization library (rec: vis.js for simplicity)
3. ✅ Design EntityNetworkView component
4. ✅ Plan API extensions for intelligence endpoints

### Short-term (Next 1-2 Sprints)
1. Create EntityNetworkView component
2. Create EntityDetailPanel component
3. Add intelligence sections to DashboardRenderer
4. Implement entity search in frontend
5. Create root cause chain visualization
6. Extend ProgressiveDisclosureView tabs

### Medium-term (Phase 5 Full)
1. Implement full recommendation provenance
2. Add intelligence timeline visualization
3. Support graph export (JSON-LD, GraphML)
4. Add real-time WebSocket updates
5. Create entity comparison UI

---

## APPENDIX: FILE REFERENCE

### Core Files
- [src/pages/Dashboard.tsx](src/pages/Dashboard.tsx) - Main dashboard page
- [src/components/DashboardRenderer.tsx](src/components/DashboardRenderer.tsx) - Composition engine
- [src/components/ChartRenderer.tsx](src/components/ChartRenderer.tsx) - Chart rendering
- [src/contexts/DashboardContext.tsx](src/contexts/DashboardContext.tsx) - State management
- [src/services/api.ts](src/services/api.ts) - API integration
- [src/lib/axios.ts](src/lib/axios.ts) - HTTP client
- [src/utils/visualizationEngine.ts](src/utils/visualizationEngine.ts) - Widget generation

### Type Definitions
- [src/types/dashboard.ts](src/types/dashboard.ts) - Dashboard schema
- [src/types/widget.ts](src/types/widget.ts) - Widget types

### Configuration
- [package.json](package.json) - Dependencies
- [src/App.tsx](src/App.tsx) - Route setup
- [vite.config.ts](vite.config.ts) - Build config (likely exists)

---

**Document Version:** 1.0  
**Last Updated:** March 27, 2025  
**Author:** GitHub Copilot Analysis
