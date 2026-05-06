# TransIQ System Integration Report

**Date:** April 8, 2026  
**Scope:** Full Frontend-Backend gap analysis  
**Backend:** 73+ REST endpoints + 1 WebSocket across 20 domains  
**Frontend:** 10 routes, 200+ components, ~45 API integrations  

---

## 1. INTEGRATION STATUS

### Verdict: **PARTIALLY INTEGRATED** (~60%)

The frontend covers **core document workflows** and **DDR drilling intelligence** well,
but has **zero coverage** of the backend's ML Ops / Observability / GraphRAG / Intelligence
subsystems — which represent roughly 40% of backend capability.

| Domain | Backend Endpoints | Frontend Coverage | Status |
|--------|:-:|:-:|--------|
| Auth | 5 | 3 of 5 | **Partial** — missing OAuth2 login, `/auth/me` (uses wrong `/user/me`) |
| Health | 3 | 1 of 3 | Partial — only `/api/v2/health` |
| Document Processing | 4 | 3 of 4 | **Good** — missing `GET /batch/{batch_id}` polling |
| Dashboard & Export | 5 | 5 of 5 | **Complete** |
| Search | 1 | 1 of 1 | **Complete** |
| Agent Lab | 1 | 1 of 1 | **Complete** |
| WebSocket | 1 | 1 of 1 | **Complete** |
| Six Sigma Analyze | 1 | 1 of 1 | **Complete** (SixSigmaAnalyzer.tsx) |
| DDR Parsing | 5 | 2 of 5 | Partial — missing parse, parse-batch, detect |
| DDR Metrics | 3 | 0 of 3 | **Missing** — no metric editing UI |
| SPC Analysis | 2 | 0 of 2 | **Missing** — uses fleet SPC, not direct SPC |
| Fleet Analytics | 6 | 6 of 6 | **Complete** |
| Rig Analytics | 15 | 15 of 15 | **Complete** (all sub-routes) |
| DDR Audit | 3 | 3 of 3 | **Complete** |
| DDR Trends | 5 | 1 of 5 | **Weak** — only generic `/trends/{metric}` |
| **Observability** | **5** | **0 of 5** | **ZERO** |
| **Intelligence / Impact** | **5** | **0 of 5** | **ZERO** |
| **Intelligence Graph** | **4** | **2 of 4** | Partial — has graph-network + cross-engine, missing recommendations + scenario |
| **GraphRAG** | **8** | **0 of 8** | **ZERO** |
| Confusion Matrix | 1 | 1 of 1 | **Complete** (but router NOT mounted in main.py) |

---

## 2. CRITICAL FINDINGS

### 2.1 Phantom Endpoints (Frontend calls endpoints that DON'T EXIST)

| Frontend Call | File | Issue | Fix |
|---|---|---|---|
| `POST /api/v2/generate-project` | [api.ts](Frontend/src/services/api.ts#L183) | Endpoint does not exist on backend | Use `/api/v2/generate-batch` instead |
| `GET /user/me` | [UserProfile.tsx](Frontend/src/pages/UserProfile.tsx#L50) | Wrong path — backend has `/auth/me` | Change to `/auth/me` |
| `GET /history/` | [UserProfile.tsx](Frontend/src/pages/UserProfile.tsx#L73) | Endpoint does not exist on backend | Build backend endpoint or use local storage |
| `GET /history/{id}` | [UserProfile.tsx](Frontend/src/pages/UserProfile.tsx#L131) | Endpoint does not exist on backend | Same as above |
| `GET /api/v2/intelligence/cross-engine-analysis/{id}` | [EntityIntelligenceTab.tsx](Frontend/src/components/intelligence/EntityIntelligenceTab.tsx#L65) | Wrong path — backend has `/cross-engine/{id}` (no `-analysis`) | Fix URL |

### 2.2 Backend Router NOT Mounted

| Router | File | Issue |
|---|---|---|
| `confusion_matrix_router` | [confusion_matrix_router.py](Backend/pipelines/evaluation/confusion_matrix_router.py) | Exists in codebase but NOT included in `app/main.py` — frontend will get 404 |

### 2.3 Completely Dark Backend Subsystems (0% Frontend Visibility)

These backend capabilities have **no UI at all**:

#### A. Observability Suite (5 endpoints)
```
GET /api/v2/observability/health       — System health (DB, Redis, Celery, models)
GET /api/v2/observability/models       — Model registry (versions, stages, metrics)
GET /api/v2/observability/features     — Feature store (staleness, versions, row counts)
GET /api/v2/observability/predictions  — Prediction logs (latency p95, confidence stats)
GET /api/v2/observability/drift        — Data & model drift alerts
```

#### B. GraphRAG Knowledge Graph (8 endpoints)
```
POST /api/v2/graph/entities/search     — Search entities by name
GET  /api/v2/graph/entities/{id}       — Entity details + mentions
POST /api/v2/graph/entities/list       — Filter entities by type
GET  /api/v2/graph/entities/{id}/related — Related entities (graph walk)
POST /api/v2/graph/relationships/search — Search relationships
GET  /api/v2/graph/relationships/{id}  — Relationships for entity
POST /api/v2/graph/paths/find          — Shortest path between entities
POST /api/v2/graph/centrality          — Centrality analysis (degree/betweenness)
```

#### C. Intelligence Impact Analysis (3 endpoints, partial)
```
POST /api/v2/intelligence/enrich-facts         — Fact enrichment with entity types
POST /api/v2/intelligence/analyze-kpi-impact   — KPI cascading effect analysis
GET  /api/v2/intelligence/dmaic/{kpi_id}       — DMAIC analysis per KPI
```

#### D. Intelligence Scenario & Recommendations (2 endpoints)
```
GET /api/v2/intelligence/recommendations/{id}  — Unified recommendation package
GET /api/v2/intelligence/scenario/{id}         — What-if scenario planning
```

#### E. DDR Metrics Editing (2 endpoints)
```
PUT /api/v2/ddr/metrics/{metric_id}    — Edit extracted metric (with audit trail!)
GET /api/v2/ddr/audit/{metric_id}      — Per-metric audit history
```

---

## 3. DETAILED GAP ANALYSIS

### 3.1 Missing Frontend Pages

| Missing Page | Backend Support | Priority | Complexity |
|---|---|:-:|:-:|
| **Observability Dashboard** | 5 endpoints ready | **P0** | Medium |
| **Knowledge Graph Explorer** | 8 endpoints ready | **P1** | High |
| **Intelligence Hub** (Impact + DMAIC + Scenarios) | 5 endpoints ready | **P1** | High |
| **Metric Editor** (inline DDR metric correction) | 2 endpoints ready | **P2** | Low |
| **DDR Batch Upload** (multi-PDF parsing) | 2 endpoints ready | **P2** | Low |
| **Report Classifier** (DDR vs generic detection) | 1 endpoint ready | **P3** | Low |

### 3.2 Missing Frontend Components

| Missing Component | Where It Goes | Backend API | Notes |
|---|---|---|---|
| Model Registry Table | Observability page | `GET /observability/models` | Version, stage, metrics per model |
| Feature Store Explorer | Observability page | `GET /observability/features` | Staleness indicators, version compare |
| Drift Monitor Panel | Observability page | `GET /observability/drift` | Alerts, data drift charts, model drift |
| Prediction Logger | Observability page | `GET /observability/predictions` | Latency histogram, confidence distribution |
| Entity Search + Detail | Graph Explorer page | `POST /graph/entities/search`, `GET /graph/entities/{id}` | Search bar + entity card |
| Relationship Browser | Graph Explorer page | `GET /graph/relationships/{id}` | Edge list with types |
| Path Finder Visualizer | Graph Explorer page | `POST /graph/paths/find` | Source → Target path animation |
| Centrality Heatmap | Graph Explorer page | `POST /graph/centrality` | Degree/betweenness ranking |
| KPI Impact Cascade | Intelligence Hub | `POST /intelligence/analyze-kpi-impact` | Visual causality chain |
| DMAIC Phase View | Intelligence Hub | `GET /intelligence/dmaic/{kpi_id}` | 5-phase accordion |
| Scenario Planner | Intelligence Hub | `GET /intelligence/scenario/{id}` | Baseline vs projected diff |
| Recommendation Cards | Intelligence Hub | `GET /intelligence/recommendations/{id}` | Priority-sorted action items |
| Inline Metric Editor | DDR Rig Detail page | `PUT /ddr/metrics/{id}` | Edit-in-place with reason field |
| Metric Audit Trail | DDR Rig Detail page | `GET /ddr/audit/{metric_id}` | Change history timeline |

### 3.3 Missing UI Capabilities

| Capability | Current State | Needed |
|---|---|---|
| **Real-time drift alerts** | Not implemented | WebSocket or polling for drift events |
| **Model comparison** | Not implemented | Side-by-side model version metrics |
| **Prediction explanations** | Partial (explainability field in dashboard) | Dedicated SHAP/LIME visualization |
| **Batch upload progress** | No batch status polling | Poll `GET /batch/{batch_id}` with progress bar |
| **OAuth2 / SSO login** | Not implemented | Use `/auth/login/oauth2` endpoint |
| **User upload history** | Calls phantom `/history/` | Build backend endpoint or track in localStorage |

---

## 4. FRONTEND ARCHITECTURE ASSESSMENT

### 4.1 Current Structure (Good)

```
Frontend/src/
├── api/              ✅ Dedicated API layer (dashboardApi, ddrClient)
├── components/       ✅ 200+ components, well-organized by domain
│   ├── ui/           ✅ 50+ shadcn components
│   ├── ddr/          ✅ 22 DDR modules
│   ├── progressive/  ✅ Progressive disclosure views
│   ├── predictive/   ✅ Predictive analytics
│   ├── intelligence/  ✅ Entity intelligence (partial)
│   └── confusion/    ✅ ML analysis
├── contexts/         ✅ AuthContext, DashboardContext, DDRContext
├── hooks/            ⚠️  Only 2 hooks (toast, mobile)
├── lib/              ✅ axios config
├── pages/            ✅ 10 routes
├── services/         ✅ api.ts (typed)
├── types/            ✅ TypeScript definitions
└── utils/            ✅ Visualization engine, PDF export
```

### 4.2 What's Missing in Architecture

```
Frontend/src/
├── api/
│   ├── observabilityClient.ts    ❌ MISSING — needs 5 API functions
│   ├── graphClient.ts            ❌ MISSING — needs 8 API functions
│   └── intelligenceClient.ts     ❌ MISSING — needs 5 API functions
├── components/
│   ├── observability/            ❌ MISSING — entire folder
│   │   ├── ModelRegistryTable.tsx
│   │   ├── FeatureStoreExplorer.tsx
│   │   ├── DriftMonitor.tsx
│   │   └── PredictionLogger.tsx
│   ├── graph/                    ❌ MISSING — entire folder
│   │   ├── EntitySearch.tsx
│   │   ├── RelationshipBrowser.tsx
│   │   ├── PathFinder.tsx
│   │   └── CentralityView.tsx
│   └── intelligence/             ⚠️  PARTIAL — missing 4 components
│       ├── KPIImpactCascade.tsx
│       ├── DMAICPhaseView.tsx
│       ├── ScenarioPlanner.tsx
│       └── RecommendationCards.tsx
├── pages/
│   ├── Observability.tsx         ❌ MISSING page
│   ├── GraphExplorer.tsx         ❌ MISSING page
│   └── IntelligenceHub.tsx       ❌ MISSING page
└── hooks/
    ├── useObservability.ts       ❌ MISSING — polling hooks for live data
    └── useGraphQuery.ts          ❌ MISSING — entity search hooks
```

### 4.3 Technical Quality Assessment

| Area | Grade | Notes |
|---|:-:|---|
| TypeScript coverage | **A** | Fully typed, no `any` in api.ts |
| Error handling | **B+** | Error boundaries + toast, but no retry for non-429 errors |
| Loading states | **A-** | Skeletons, spinners, progress bars |
| State management | **B** | Context-based — adequate but no global store for cross-page data |
| API layer | **B** | Good for existing APIs, but no centralized error transform |
| Charting | **A** | Recharts + Tremor + vis-network — excellent variety |
| Responsive design | **A-** | Tailwind breakpoints, mobile-aware |
| Accessibility | **C** | No ARIA labels, no keyboard nav patterns, no screen reader testing |
| Testing | **F** | Zero frontend tests (no Jest, no Vitest, no Cypress) |

---

## 5. PRIORITY ROADMAP

### Phase 1: Fix Broken Integrations (1-2 days) — **CRITICAL**

| # | Task | Impact |
|:-:|---|---|
| 1 | Fix `GET /user/me` → `GET /auth/me` in UserProfile.tsx | Profile page is broken |
| 2 | Remove `POST /api/v2/generate-project` — use `generate-batch` | Upload fails for 6+ files |
| 3 | Fix `cross-engine-analysis` → `cross-engine` URL in EntityIntelligenceTab | Intelligence tab crashes |
| 4 | Mount `confusion_matrix_router` in `main.py` | Confusion Matrix page returns 404 |
| 5 | Build `GET /history/` backend endpoint OR replace with localStorage | Profile history broken |
| 6 | Add `GET /batch/{batch_id}` polling to batch upload flow | No batch progress visibility |

### Phase 2: Observability Dashboard (3-5 days) — **HIGH**

| # | Task | API |
|:-:|---|---|
| 1 | Create `observabilityClient.ts` — 5 API functions | All `/observability/*` |
| 2 | Build `Observability.tsx` page with 4 panels | — |
| 3 | Model Registry Table — name, version, stage, metrics | `GET /observability/models` |
| 4 | Feature Store Explorer — staleness badges, version compare | `GET /observability/features` |
| 5 | Drift Monitor — data drift chart + model drift + alerts | `GET /observability/drift` |
| 6 | Prediction Logger — latency histogram, confidence dist | `GET /observability/predictions` |
| 7 | Auto-refresh polling (30s interval) | `useQuery` refetchInterval |

### Phase 3: Knowledge Graph Explorer (5-7 days) — **HIGH**

| # | Task | API |
|:-:|---|---|
| 1 | Create `graphClient.ts` — 8 API functions | All `/graph/*` |
| 2 | Build `GraphExplorer.tsx` page | — |
| 3 | Entity Search — type-ahead search bar + entity cards | `POST /graph/entities/search` |
| 4 | Entity Detail Drawer — mentions, relationships, metadata | `GET /graph/entities/{id}` |
| 5 | Relationship Browser — edge list with type badges | `GET /graph/relationships/{id}` |
| 6 | Path Finder — source/target picker + vis-network path viz | `POST /graph/paths/find` |
| 7 | Centrality Leaderboard — sortable table + bar chart | `POST /graph/centrality` |
| 8 | Reuse vis-network from EntityIntelligenceTab | Already imported |

### Phase 4: Intelligence Hub (5-7 days) — **MEDIUM**

| # | Task | API |
|:-:|---|---|
| 1 | Create `intelligenceClient.ts` — 5+ API functions | All `/intelligence/*` |
| 2 | Build `IntelligenceHub.tsx` page | — |
| 3 | KPI Impact Cascade — visual causality chain (tree/sankey) | `POST /intelligence/analyze-kpi-impact` |
| 4 | DMAIC Phase Accordion — 5 collapsible sections | `GET /intelligence/dmaic/{kpi_id}` |
| 5 | Scenario Planner — baseline vs projected side-by-side | `GET /intelligence/scenario/{id}` |
| 6 | Recommendation Cards — priority-sorted with action buttons | `GET /intelligence/recommendations/{id}` |
| 7 | Fact Enrichment Panel — entity type tagging on deductions | `POST /intelligence/enrich-facts` |

### Phase 5: DDR Enhancements (3-4 days) — **MEDIUM**

| # | Task | API |
|:-:|---|---|
| 1 | Inline Metric Editor on Rig Detail page | `PUT /ddr/metrics/{id}` |
| 2 | Per-metric Audit Trail popover | `GET /ddr/audit/{metric_id}` |
| 3 | DDR Batch Upload page | `POST /ddr/parse-batch` |
| 4 | Report Type Auto-Detection badge | `POST /ddr/detect` |
| 5 | Direct SPC Analysis component | `POST /ddr/spc` |
| 6 | Specific trend endpoints (depth, npt, rop, mud-weight) | `GET /ddr/trends/*` |
| 7 | Multi-rig comparison chart | `GET /ddr/trends/multi-rig-comparison` |

### Phase 6: Production Hardening (Ongoing) — **MEDIUM**

| # | Task |
|:-:|---|
| 1 | Add Vitest + React Testing Library |
| 2 | Add Cypress E2E tests for critical flows (auth → upload → dashboard) |
| 3 | Add ARIA labels and keyboard navigation |
| 4 | Add centralized API error transformer (standardize error shapes) |
| 5 | Add OAuth2/SSO login support |
| 6 | Add global state (Zustand) for cross-page data (selected entity, active report) |
| 7 | Add service worker for offline dashboard caching |

---

## 6. ENDPOINT-LEVEL COVERAGE MATRIX

### ✅ Fully Integrated (35 endpoints)

```
POST /auth/login                        → Auth.tsx
POST /auth/register                     → Auth.tsx
POST /auth/logout                       → AuthContext.tsx
GET  /api/v2/health                     → api.ts
POST /api/v2/generate                   → Upload.tsx
POST /api/v2/generate-batch             → Upload.tsx
GET  /api/v2/task/{task_id}             → api.ts
WS   /api/v2/ws/{task_id}              → api.ts (ProgressWebSocket)
GET  /api/v2/documents/{doc_id}         → api.ts
GET  /api/v2/documents/{doc_id}/chunks  → api.ts
POST /api/v2/search                     → Search.tsx
POST /api/v2/agent/run                  → AgentLab.tsx
GET  /api/v2/dashboard/latest           → Dashboard.tsx
GET  /api/v2/dashboard/{doc_id}         → dashboardApi.ts
GET  /api/v2/documents/{doc_id}/dashboard → Dashboard.tsx
GET  /api/v2/dashboard/{id}/export/pdf  → dashboardApi.ts
GET  /api/v2/dashboard/{id}/export/excel → dashboardApi.ts
POST /api/v2/six-sigma/analyze          → SixSigmaAnalyzer.tsx
GET  /api/v2/intelligence/graph-network/{id} → EntityIntelligenceTab.tsx
GET  /api/v2/fleet/summary              → ddrClient.ts
GET  /api/v2/fleet/npt-pareto           → ddrClient.ts
GET  /api/v2/fleet/spc/{metric}         → ddrClient.ts
GET  /api/v2/fleet/top-performers       → ddrClient.ts
GET  /api/v2/fleet/heatmap              → ddrClient.ts
GET  /api/v2/fleet/export               → ddrClient.ts
GET  /api/v2/rigs                       → ddrClient.ts
GET  /api/v2/rigs/{id}                  → ddrClient.ts
GET  /api/v2/rigs/{id}/timeline         → ddrClient.ts
GET  /api/v2/rigs/{id}/kpis             → ddrClient.ts
GET  /api/v2/rigs/{id}/npt             → ddrClient.ts
GET  /api/v2/rigs/{id}/survey          → ddrClient.ts
GET  /api/v2/rigs/{id}/mud             → ddrClient.ts
GET  /api/v2/rigs/{id}/personnel       → ddrClient.ts
GET  /api/v2/rigs/{id}/bha             → ddrClient.ts
GET  /api/v2/rigs/{id}/hse             → ddrClient.ts
GET  /api/v2/rigs/{id}/bulk            → ddrClient.ts
GET  /api/v2/rigs/{id}/export          → ddrClient.ts
POST /api/v2/ddr/parse-upload           → ddrClient.ts
GET  /api/v2/ddr/reports                → ddrClient.ts
GET  /api/v2/audit/{rigId}/{field}      → ddrClient.ts
GET  /api/v2/audit/changelog            → ddrClient.ts
GET  /api/ddr/trends/{metric}           → ddrClient.ts
```

### ⚠️ Partially Integrated (3 endpoints)

```
GET  /auth/me                → Frontend calls /user/me (WRONG PATH)
GET  /api/v2/intelligence/cross-engine/{id} → Frontend calls /cross-engine-analysis/{id} (WRONG PATH)
POST /api/v2/confusion-matrix/upload → Frontend has page but router NOT MOUNTED in main.py
```

### 🔴 Frontend Calls That Hit Nothing (3 phantom calls)

```
POST /api/v2/generate-project           → Does not exist
GET  /user/me                           → Does not exist (should be /auth/me)
GET  /history/                          → Does not exist
```

### ❌ Not Integrated — Backend Ready, No Frontend (26 endpoints)

```
# Observability (5) — ZERO coverage
GET  /api/v2/observability/health
GET  /api/v2/observability/models
GET  /api/v2/observability/features
GET  /api/v2/observability/predictions
GET  /api/v2/observability/drift

# GraphRAG (8) — ZERO coverage
POST /api/v2/graph/entities/search
GET  /api/v2/graph/entities/{id}
POST /api/v2/graph/entities/list
GET  /api/v2/graph/entities/{id}/related
POST /api/v2/graph/relationships/search
GET  /api/v2/graph/relationships/{id}
POST /api/v2/graph/paths/find
POST /api/v2/graph/centrality

# Intelligence (5) — ZERO coverage
POST /api/v2/intelligence/enrich-facts
POST /api/v2/intelligence/analyze-kpi-impact
GET  /api/v2/intelligence/dmaic/{kpi_id}
GET  /api/v2/intelligence/recommendations/{id}
GET  /api/v2/intelligence/scenario/{id}

# DDR Advanced (5)
POST /api/v2/ddr/parse
POST /api/v2/ddr/parse-batch
POST /api/v2/ddr/detect
PUT  /api/v2/ddr/metrics/{id}
GET  /api/v2/ddr/audit/{metric_id}

# Other (3)
POST /auth/login/oauth2
GET  /api/v2/batch/{batch_id}
GET  /api/v2/dashboard/status/{task_id}
```

---

## 7. SUMMARY

| Metric | Value |
|---|---|
| Total backend endpoints | **73+** |
| Frontend integrations (correct) | **~42** (57%) |
| Frontend integrations (broken path) | **3** |
| Frontend phantom calls (no backend) | **3** |
| Backend endpoints with ZERO frontend | **26** (36%) |
| Missing frontend pages | **3** (Observability, Graph Explorer, Intelligence Hub) |
| Missing frontend components | **14** |
| Frontend test coverage | **0%** |

### Bottom Line

The **core workflow** (upload → process → dashboard → export) is solid and fully wired.  
The **DDR drilling intelligence** module is comprehensive (22 components, 25+ endpoints).  
But the **ML Ops platform** (observability, drift, model registry, feature store, GraphRAG) —
which is arguably what makes TransIQ an *AI system* rather than just a document processor —
**is completely invisible to users**. No UI exists for any of it.

**Fix priority: (1) Broken paths, (2) Observability, (3) Graph Explorer, (4) Intelligence Hub.**
