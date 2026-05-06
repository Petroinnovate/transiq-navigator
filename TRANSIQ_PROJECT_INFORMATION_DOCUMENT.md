# TransIQ — Complete Project Information Document

> **Version**: 1.0  
> **Last Updated**: April 30, 2026  
> **Status**: Active Development  
> **Classification**: Internal / Stakeholder Reference

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement & Value Proposition](#2-problem-statement--value-proposition)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [Technology Stack](#4-technology-stack)
5. [Backend Architecture](#5-backend-architecture)
6. [Frontend Architecture](#6-frontend-architecture)
7. [AI/ML Engine](#7-aiml-engine)
8. [Multi-Tenant Architecture](#8-multi-tenant-architecture)
9. [Security Implementation](#9-security-implementation)
10. [Database & Storage](#10-database--storage)
11. [API Reference](#11-api-reference)
12. [Key Features](#12-key-features)
13. [Sub-Projects & Integrations](#13-sub-projects--integrations)
14. [Deployment Guide](#14-deployment-guide)
15. [Known Gaps & Roadmap](#15-known-gaps--roadmap)
16. [Glossary](#16-glossary)

---

## 1. Executive Summary

**TransIQ** is an **AI-powered, multi-tenant SaaS analytics platform** designed for industrial and manufacturing process optimization. It combines document intelligence, drilling analytics, and Six Sigma quality methodology into a single unified platform.

### What It Does (One-Liner)
> Upload any document (PDF, Excel, CSV) → AI extracts insights, builds knowledge graphs, runs statistical analysis → Get actionable dashboards with KPIs, forecasts, and optimization suggestions.

### Core Modules

| Module | Description |
|--------|-------------|
| **Document Intelligence** | Process and analyze complex documents using multi-LLM AI |
| **Drilling Analytics (DDR)** | Specialized module for drilling rig daily reports & fleet management |
| **Six Sigma / Quality** | DMAIC framework, SPC, control charts, process capability |
| **Knowledge Graph (GraphRAG)** | Entity extraction, relationship mapping, multi-hop reasoning |
| **Predictive Analytics** | Time-series forecasting, anomaly detection, pattern recognition |

### Target Users
- Manufacturing companies (quality engineers, process managers)
- Oil & Gas / Drilling operators (rig managers, fleet supervisors)
- Data analysts & business intelligence teams
- Executive leadership (CEO/Manager/Engineer progressive views)

---

## 2. Problem Statement & Value Proposition

### Problems Solved

| Problem | Traditional Approach | TransIQ Solution |
|---------|---------------------|-----------------|
| Manual document analysis | Analysts read 100s of pages | AI extracts facts in minutes |
| Siloed data insights | Spreadsheets & disconnected tools | Unified knowledge graph |
| Reactive quality control | Post-failure investigation | Real-time SPC & anomaly detection |
| Drilling report overload | Manual daily report parsing | Automated DDR extraction & trending |
| No cross-document intelligence | Each doc analyzed independently | GraphRAG connects entities across docs |

### Key Value Propositions

1. **Multi-LLM Intelligence**: Automatically falls back between Gemini, OpenAI, and Claude for reliability
2. **Adaptive Document Processing**: Understands tables, sections, hierarchies — not just text
3. **Graph-Based Reasoning**: Discovers indirect connections humans miss (A→B→C→D)
4. **Real-Time Analytics**: WebSocket-driven live progress & dashboard updates
5. **Enterprise-Ready**: Multi-tenant isolation, JWT auth, role-based access, audit trails
6. **Progressive Disclosure**: Same data presented for CEOs (30-sec view), Managers (DMAIC), Engineers (full depth)

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                      │
│                                                                              │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐│
│  │   React Frontend     │  │  DrillSight Analytics │  │  RigSight Analytics││
│  │   (Main Dashboard)   │  │  (Drilling Module)    │  │  (Rig Analytics)   ││
│  │   Port: 5173         │  │                       │  │                    ││
│  └──────────┬───────────┘  └──────────┬────────────┘  └────────┬───────────┘│
└─────────────┼──────────────────────────┼───────────────────────┼────────────┘
              │ HTTPS + JWT + API Key     │                       │
              ▼                           ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API GATEWAY LAYER                                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  FastAPI Application (Port 8001)                                    │    │
│  │  ├── CORS Middleware                                                 │    │
│  │  ├── API Key Authentication (X-API-Key)                             │    │
│  │  ├── Rate Limiting (60 req/min)                                     │    │
│  │  ├── JWT Token Validation (Bearer token)                            │    │
│  │  └── Request Routing → /api/v2/*                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SERVICE / BUSINESS LAYER                             │
│                                                                              │
│  ┌────────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────────────┐   │
│  │  Auth      │  │  Document    │  │  Search   │  │  DDR Analysis      │   │
│  │  Service   │  │  Processing  │  │  Engine   │  │  Service           │   │
│  └────────────┘  └──────────────┘  └───────────┘  └────────────────────┘   │
│  ┌────────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────────────┐   │
│  │  GraphRAG  │  │  KPI Impact  │  │  Six Sigma│  │  Predictive        │   │
│  │  Engine    │  │  Analysis    │  │  Engine   │  │  Analytics         │   │
│  └────────────┘  └──────────────┘  └───────────┘  └────────────────────┘   │
│  ┌────────────┐  ┌──────────────┐  ┌───────────┐                           │
│  │  AI Agent  │  │  Observ-     │  │  Dashboard│                           │
│  │  Framework │  │  ability     │  │  Engine   │                           │
│  └────────────┘  └──────────────┘  └───────────┘                           │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ASYNC PROCESSING LAYER                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Celery Workers                                                      │    │
│  │  ├── Document Processor (chunk → embed → analyze → store)           │    │
│  │  ├── Graph Processor (entity extraction → deduplication → edges)    │    │
│  │  ├── LLM Orchestrator (multi-provider with fallback)                │    │
│  │  └── Status Broadcaster (WebSocket notifications)                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA / STORAGE LAYER                                │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────────┐     │
│  │  PostgreSQL  │  │  Qdrant      │  │  Redis    │  │  File Storage  │     │
│  │  (Relational)│  │  (Vectors)   │  │  (Cache + │  │  (Documents)   │     │
│  │  Users, Docs │  │  Embeddings  │  │   Queue)  │  │  PDFs, Excel   │     │
│  │  Chunks,Tasks│  │  384-dim     │  │  Celery   │  │  CSV, Word     │     │
│  └──────────────┘  └──────────────┘  └───────────┘  └────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL AI SERVICES                                   │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐                     │
│  │  Google      │  │  OpenAI      │  │  Anthropic    │                     │
│  │  Gemini API  │  │  GPT-4 API   │  │  Claude API   │                     │
│  │  (Primary)   │  │  (Fallback)  │  │  (Fallback)   │                     │
│  └──────────────┘  └──────────────┘  └───────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Technology Stack

### Backend Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| Framework | FastAPI | Async Python API framework |
| Server | Uvicorn | ASGI production server |
| ORM | SQLAlchemy | Database abstraction |
| Task Queue | Celery | Background job processing |
| Message Broker | Redis | Celery broker + caching |
| Database | PostgreSQL (prod) / SQLite (dev) | Persistent data storage |
| Vector Database | Qdrant | Similarity search |
| Auth | python-jose (JWT) + passlib (bcrypt) | Authentication |
| LLM Primary | Google Gemini 1.5 Pro | AI text generation |
| LLM Fallback | OpenAI GPT-4, Anthropic Claude | Reliability fallback |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Text → vectors |
| ML | scikit-learn, XGBoost, Prophet, statsmodels | Analytics & forecasting |
| PDF Parsing | pdfplumber, PyMuPDF | Document extraction |
| Migrations | Alembic | Database schema versioning |

### Frontend Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| Framework | React 18 + TypeScript | UI framework |
| Build Tool | Vite | Fast dev server + bundling |
| Styling | Tailwind CSS | Utility-first CSS |
| UI Library | shadcn/ui (50+ components) | Pre-built accessible components |
| Charting | Recharts | Data visualization (8+ chart types) |
| Graph Viz | vis-network | Knowledge graph visualization |
| Advanced Viz | Tremor | Analytics-grade components |
| Forms | react-hook-form + Zod | Form handling + validation |
| HTTP | Axios | API client with interceptors |
| State | React Context API | Global state management |
| Routing | react-router-dom v6 | Client-side routing |
| Animations | Framer Motion | UI animations |
| PDF Export | jsPDF + html2canvas | Report generation |
| Data Fetching | @tanstack/react-query | Caching, polling, sync |
| Notifications | Sonner | Toast messages |
| Theme | next-themes | Light/dark mode |

### DevOps Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| Containers | Docker + Docker Compose | Deployment packaging |
| Migrations | Alembic | Schema version control |
| Package Mgr (BE) | pip / pyproject.toml | Python dependencies |
| Package Mgr (FE) | bun / npm | JavaScript dependencies |

---

## 5. Backend Architecture

### Directory Structure

```
Backend/
├── app/                          # FastAPI Application Root
│   ├── main.py                   # App initialization, middleware, router mounting
│   ├── api/
│   │   ├── v2/
│   │   │   ├── endpoints.py     # Core: generate, search, dashboard, health
│   │   │   ├── auth.py          # JWT auth: register, login, /me
│   │   │   ├── impact_endpoints.py      # KPI impact analysis
│   │   │   ├── dashboard_endpoints.py   # Dashboard data
│   │   │   ├── intelligence_graph_endpoints.py  # Entity intelligence
│   │   │   ├── graph_endpoints.py       # GraphRAG queries
│   │   │   └── observability_endpoints.py  # System health & monitoring
│   │   ├── ddr/                  # Drilling Daily Reports
│   │   │   ├── endpoints.py     # DDR parsing, SPC analysis
│   │   │   ├── fleet_endpoints.py
│   │   │   ├── rig_endpoints.py
│   │   │   ├── audit_endpoints.py
│   │   │   └── trend_endpoints.py
│   │   └── transiq/
│   │       └── analyze.py       # Six Sigma DMAIC analysis endpoint
│   ├── middleware/
│   │   └── auth.py              # API key validation + rate limiting
│   └── websocket/               # WebSocket handlers (real-time updates)
│
├── services/                     # Business Logic Layer
│   ├── db/
│   │   ├── session.py           # Database connection pooling
│   │   └── models.py           # SQLAlchemy ORM models
│   ├── chat/                    # Chat/conversation logic
│   ├── workers/
│   │   ├── processor.py        # Main document processing worker
│   │   ├── tasks.py            # Celery task definitions
│   │   └── graph_processing.py # GraphRAG background processing
│   ├── storage/                 # Chunk & document storage
│   ├── llm/                     # LLM provider abstraction layer
│   ├── cache/                   # Redis caching layer
│   └── vector_store/           # Qdrant integration
│
├── core/                         # Infrastructure & Configuration
│   ├── config/
│   │   └── settings.py         # Environment variables & app config
│   ├── logging/
│   │   └── logger.py           # Structured logging
│   ├── security/               # Auth utilities
│   └── errors.py              # Custom exception classes
│
├── domain/                       # Domain Models (Business Rules)
│   └── transiq/                # Six Sigma / Quality domain
│
├── features/                     # Feature Engineering & ML
│   ├── kpi/                    # KPI calculation engine
│   ├── predictive/             # Time-series forecasting
│   ├── risk/                   # Risk assessment models
│   ├── six_sigma/              # DMAIC, SPC, control charts
│   └── store/                  # Feature store (feature persistence)
│
├── models/                       # ML Model Registry
│   ├── evaluators/             # Model evaluation metrics
│   ├── loaders/                # Model loading utilities
│   ├── registry/               # Version management
│   └── artifacts/              # Trained model weights/configs
│
├── pipelines/                    # ML Processing Pipelines
│   ├── ingestion/              # File → chunk pipeline
│   ├── processing/             # Document processing
│   ├── training/               # Model training pipelines
│   ├── inference/              # Model inference
│   ├── monitoring/             # Performance monitoring
│   ├── orchestration/          # Pipeline coordination
│   ├── evaluation/             # Metrics calculation
│   └── workers/                # Pipeline workers
│
├── agents/                       # AI Agent Framework
│   ├── base_agent.py           # Base agent class
│   ├── decision_agents/        # Specialized decision-making agents
│   └── orchestrator/           # Multi-agent coordination
│
├── configs/                      # Configuration files
├── data/                         # Sample/seed data
├── docs/                         # API documentation
├── scripts/                      # Utility scripts
├── tests/                        # Test suite
└── storage/                      # Runtime storage
```

### Request Processing Flow

```
HTTP Request (with headers: X-API-Key, Authorization: Bearer <jwt>)
     │
     ▼
[1] API Key Middleware → Validates X-API-Key → Rate limit check (60/min)
     │
     ▼
[2] CORS Middleware → Checks origin against allowed list
     │
     ▼
[3] JWT Middleware → Decodes Bearer token → Extracts user_id
     │
     ▼
[4] FastAPI Router → Routes to correct endpoint handler
     │
     ▼
[5] Dependency Injection → get_current_user() provides User object
     │
     ▼
[6] Endpoint Handler → Business logic + ownership verification
     │
     ├──[Sync Response]──→ Return JSON immediately
     │
     └──[Async Task]──→ Celery enqueue → Return task_id
                              │
                              ▼
                    Celery Worker picks up task
                    ├── File parsing (PDF/Excel/CSV)
                    ├── Adaptive chunking
                    ├── LLM processing (Gemini → OpenAI → Claude)
                    ├── Vector embedding (sentence-transformers)
                    ├── GraphRAG processing (entities + relationships)
                    ├── Qdrant storage (vector insertion)
                    ├── Dashboard generation
                    └── WebSocket broadcast → Frontend receives update
```

### Task Status Lifecycle
```
pending → processing → chunking → embedding → analysis → complete
                                                        → failed (with error)
```

---

## 6. Frontend Architecture

### Directory Structure

```
Frontend/src/
├── api/                          # API Layer
│   ├── client.ts                # Axios instance + auth interceptor
│   ├── dashboardApi.ts          # Dashboard data fetching
│   ├── ddrClient.ts             # DDR-specific API calls
│   └── authClient.ts            # JWT login/register
│
├── components/ (200+ components)
│   ├── ui/                      # shadcn/ui base (50+ components)
│   ├── layout/                  # DashboardLayout, Sidebar, TopBar
│   ├── charts/                  # ChartRenderer + chart type wrappers
│   ├── ddr/                     # Drilling module (22 components)
│   ├── progressive/             # Audience-level views
│   │   ├── CEOView.tsx          # 30-second executive snapshot
│   │   ├── ManagerView.tsx      # DMAIC + KPI analysis
│   │   ├── EngineerView.tsx     # Full technical depth
│   │   ├── BoardroomMode.tsx    # Slide-ready presentation
│   │   ├── AuditTrail.tsx       # Decision explainability
│   │   └── OutcomesView.tsx     # Decision → dollar impact
│   ├── predictive/              # Forecasting & what-if
│   ├── intelligence/            # Entity intelligence & graph
│   ├── explainability/          # SHAP, feature importance
│   ├── confusion/               # ML performance analysis
│   ├── insights/                # Alerts & recommendations
│   ├── kpis/                    # KPI cards & trends
│   ├── optimization/            # Cost/efficiency suggestions
│   ├── sixSigma/                # DMAIC framework UI
│   ├── citation/                # Source citation display
│   └── classification/          # Document classification
│
├── contexts/                     # Global State (Context API)
│   ├── AuthContext.tsx          # User session, JWT
│   ├── DashboardContext.tsx     # Dashboard data & filters
│   └── DDRContext.tsx           # DDR-specific state
│
├── pages/ (10 pages)
│   ├── Index.tsx                # Landing page / hub navigation
│   ├── Auth.tsx                 # Login & registration
│   ├── Upload.tsx               # File upload (single/batch/project)
│   ├── Dashboard.tsx            # ★ Main analytics dashboard
│   ├── Search.tsx               # Hybrid document search
│   ├── ConfusionMatrix.tsx      # ML model performance
│   ├── DemoPage.tsx             # Demo with sample data
│   ├── UserProfile.tsx          # User settings & history
│   └── NotFound.tsx             # 404 page
│
├── hooks/                        # Custom React Hooks
├── lib/                          # Utility libraries (axios config)
├── services/                     # Typed API service layer
├── types/                        # TypeScript interfaces
├── utils/                        # Helper functions
└── main.tsx                      # App entry point
```

### Page Architecture: Dashboard (Core Page)

```
Dashboard.tsx
├── DashboardLayout (sidebar + top bar)
└── DashboardRenderer (composition engine)
    ├── KPICard[] (metric displays with trend arrows)
    ├── ChartRenderer[] (auto-generates appropriate chart types)
    │   ├── AreaChart (time series)
    │   ├── BarChart (categories)
    │   ├── LineChart (trends)
    │   ├── PieChart (proportions)
    │   ├── RadarChart (multi-dimensional)
    │   ├── ScatterChart (correlations)
    │   ├── FunnelChart (process funnels)
    │   ├── ComposedChart (mixed types)
    │   └── SankeyChart (flow diagrams)
    ├── DataTable[] (tabular data display)
    ├── OptimizationSuggestions[] (AI-driven recommendations)
    ├── InsightsSection (alerts + recommendations)
    ├── SixSigmaSection (DMAIC phases)
    ├── AlertPanel (critical issues)
    └── ProgressiveDisclosureView (audience-specific)
        ├── CEOView → 30-second snapshot
        ├── ManagerView → DMAIC + KPIs
        ├── EngineerView → Full depth + raw data
        ├── BoardroomMode → Slide-format narrative
        ├── AuditTrail → Explainability chain
        └── OutcomesView → Decision → $ impact
```

---

## 7. AI/ML Engine

### 7.1 LLM Integration (Multi-Provider)

```
Provider Priority:
  1. Google Gemini 1.5 Pro (primary — best cost/quality ratio)
  2. OpenAI GPT-4 (fallback #1)
  3. Anthropic Claude 3.5 (fallback #2)

Auto-Fallback Logic:
  - If provider #1 times out (30s) or returns error → try #2
  - If #2 fails → try #3
  - Exponential backoff between retries
  - All failures logged for observability

Use Cases:
  ├── Deduction: Extract facts, metrics, entities from text
  ├── Summarization: Generate insights and executive summaries
  ├── Classification: Detect document type and content categories
  ├── Entity Recognition: NER (people, organizations, metrics)
  ├── Relationship Extraction: Find causal and associative links
  └── Query Understanding: Parse user search intent
```

### 7.2 Document Processing Pipeline

```
File Upload
    │
    ▼
[1] Format Detection → PDF / Excel / CSV / Word / Text
    │
    ▼
[2] Content Extraction
    ├── PDF: pdfplumber (tables) + PyMuPDF (text/images)
    ├── Excel: openpyxl (with formula parsing)
    ├── CSV: pandas (with type inference)
    └── Word: python-docx (with style preservation)
    │
    ▼
[3] Adaptive Chunking
    ├── Semantic boundaries (paragraph/section breaks)
    ├── Table-aware (keeps rows together, never splits mid-cell)
    ├── Hierarchical (preserves section → subsection nesting)
    ├── Overlap: 10% context preservation between chunks
    └── Max size: 1024 tokens (optimized for LLM context)
    │
    ▼
[4] LLM Analysis (per chunk)
    ├── Fact extraction (with confidence scores)
    ├── Entity detection (with types)
    ├── Metric extraction (name, value, unit, trend)
    ├── Relationship identification
    └── Citation tracking (quotes with source location)
    │
    ▼
[5] Vector Embedding
    ├── Model: all-MiniLM-L6-v2 (384 dimensions)
    ├── Batch processing (efficient GPU utilization)
    └── Storage: Qdrant HNSW index
    │
    ▼
[6] Knowledge Graph Construction
    ├── Entity deduplication (85% fuzzy match threshold)
    ├── Relationship merging
    ├── Cross-document entity resolution
    └── Graph analytics (centrality, communities)
    │
    ▼
[7] Dashboard Generation
    ├── KPI synthesis (aggregate metrics)
    ├── Chart recommendations (auto-select best visualization)
    ├── Insight generation (anomalies, trends, alerts)
    └── Six Sigma analysis (if applicable)
```

### 7.3 Hybrid Search Engine

```
User Query
    │
    ├──[1] BM25 Keyword Search (fast, exact phrase matching)
    │       └── Returns: top-10 by term frequency
    │
    ├──[2] Semantic Search (meaning-based)
    │       ├── Query → embed (sentence-transformers)
    │       ├── Qdrant cosine similarity
    │       └── Returns: top-10 by semantic relevance
    │
    ├──[3] Graph-Based Search (relationship traversal)
    │       ├── Find entities matching query
    │       ├── Traverse 1-3 hops
    │       └── Returns: related entities & context
    │
    └──[4] LLM Re-Ranking
            ├── Combine all results
            ├── LLM scores relevance (0-1)
            └── Returns: top-5 final results with citations
```

### 7.4 GraphRAG (Knowledge Graph + RAG)

```
Entity Extraction:
  - Types: PERSON, ORGANIZATION, METRIC, PROCESS, EQUIPMENT, LOCATION
  - Confidence scoring (0-1)
  - Source citation (chunk_id + quote)

Entity Deduplication:
  - Fuzzy matching threshold: 85% similarity
  - Example: "Apple Inc" ≈ "Apple Corporation" → merged
  - Cross-document resolution

Relationship Types:
  - causes, affects, depends_on, related_to
  - measured_by, located_in, part_of, produces

Graph Analytics:
  - Centrality: degree, closeness, betweenness (importance ranking)
  - Community detection: clusters of related entities
  - Anomaly detection: unusual relationship patterns
  - Path finding: shortest path between any two entities
  - Impact analysis: cascade effects through the graph
```

### 7.5 Predictive Analytics

```
Time-Series Forecasting:
  ├── Prophet (Facebook): seasonal trends, holidays
  ├── ARIMA (statsmodels): autoregressive patterns
  └── Exponential smoothing: short-term predictions

Classification & Regression:
  ├── XGBoost: gradient boosting (KPI prediction)
  ├── Random Forest: feature importance
  └── Linear models: interpretable baselines

Anomaly Detection:
  ├── Isolation Forest (unsupervised)
  ├── Local Outlier Factor (density-based)
  └── One-Class SVM (boundary-based)

Statistical Process Control (SPC):
  ├── Control charts: X-bar, R, I-MR
  ├── Capability indices: Pp, Ppk, Cp, Cpk
  ├── Process center: Mean (μ), Std Dev (σ)
  └── Specification limits: USL, LSL, Target
```

---

## 8. Multi-Tenant Architecture

### Isolation Strategy

```
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: API Authentication                             │
│ ├── API Key validates the client application            │
│ └── JWT token identifies the specific user              │
├─────────────────────────────────────────────────────────┤
│ LAYER 2: Request-Level Isolation                        │
│ ├── get_current_user() extracts user_id from JWT        │
│ └── All endpoints receive user_id as dependency         │
├─────────────────────────────────────────────────────────┤
│ LAYER 3: Query-Level Isolation                          │
│ ├── Every DB query includes: WHERE user_id = ?          │
│ ├── Documents: doc.user_id == current_user.id           │
│ ├── Tasks: task.user_id == current_user.id              │
│ └── Batches: batch.user_id == current_user.id           │
├─────────────────────────────────────────────────────────┤
│ LAYER 4: Resource Ownership Verification                │
│ ├── Accessing doc_id → verify user owns document        │
│ ├── Accessing task_id → verify user owns task           │
│ └── Unauthorized access → 403 Forbidden                 │
└─────────────────────────────────────────────────────────┘
```

### Data Model (Multi-Tenant)

```sql
-- Every table has user_id for tenant isolation
users (id, email, hashed_password, is_active, is_admin)
  ├── documents (id, user_id FK, filename, metadata, status, dashboard_data)
  │     └── chunks (id, doc_id FK, chunk_text, metadata)
  ├── task_status (task_id, user_id FK, doc_id FK, status, progress, result)
  ├── batches (id, user_id FK, total_files, status)
  └── graph_edges (id, doc_id FK, edge JSON)

-- Performance indexes
idx_documents_user_id ON documents(user_id)
idx_documents_user_status ON documents(user_id, status)
idx_task_status_user_id ON task_status(user_id)
idx_chunks_doc_id ON chunks(doc_id)
```

---

## 9. Security Implementation

### Security Layers

| Layer | Mechanism | Details |
|-------|-----------|---------|
| Transport | HTTPS (production) | TLS 1.2+ encryption |
| API Auth | API Key header | `X-API-Key` validation, supports 3 keys |
| Rate Limiting | slowapi | 60 requests/minute per API key |
| User Auth | JWT (HS256) | 24-hour TTL, signed with secret |
| Password | bcrypt | Passlib hashing, salted |
| Data Isolation | Row-level security | user_id filtering on all queries |
| Input Validation | Pydantic | Strict type checking on all inputs |
| SQL Injection | SQLAlchemy ORM | Parameterized queries (no raw SQL) |
| CORS | FastAPI CORSMiddleware | Whitelist: localhost:5173 (dev) |
| Audit | Structured logging | All auth failures logged |

### Authentication Flow

```
                    ┌──────────────────────────────────┐
                    │        REGISTRATION               │
                    │                                    │
                    │  POST /auth/register               │
                    │  Body: { email, password }         │
                    │                                    │
                    │  1. Validate email format           │
                    │  2. Check uniqueness                │
                    │  3. Hash password (bcrypt)          │
                    │  4. Create user record              │
                    │  5. Generate JWT token              │
                    │  6. Return { access_token, user }   │
                    └──────────────────────────────────┘

                    ┌──────────────────────────────────┐
                    │           LOGIN                    │
                    │                                    │
                    │  POST /auth/login                  │
                    │  Body: { email, password }         │
                    │                                    │
                    │  1. Find user by email             │
                    │  2. Verify bcrypt hash             │
                    │  3. Generate JWT (24hr TTL)        │
                    │  4. Return { access_token }        │
                    └──────────────────────────────────┘

                    ┌──────────────────────────────────┐
                    │      AUTHENTICATED REQUEST         │
                    │                                    │
                    │  Headers:                          │
                    │   X-API-Key: <app_key>            │
                    │   Authorization: Bearer <jwt>      │
                    │                                    │
                    │  1. Validate API key               │
                    │  2. Check rate limit               │
                    │  3. Decode JWT → user_id           │
                    │  4. Inject user into handler       │
                    │  5. Verify resource ownership      │
                    └──────────────────────────────────┘
```

---

## 10. Database & Storage

### Storage Architecture

| Store | Technology | Data Type | Scale |
|-------|-----------|-----------|-------|
| Relational DB | PostgreSQL / SQLite | Users, documents, tasks, metadata | Millions of rows |
| Vector Store | Qdrant | Text embeddings (384-dim) | Millions of vectors |
| Cache | Redis | Session data, task status, LLM cache | Ephemeral |
| File Store | Local filesystem / Supabase | Original uploaded files | GBs of documents |
| Graph Store | PostgreSQL (JSON) | Entity relationships | Thousands of edges |

### Caching Strategy

```
Embedding Cache (Redis):
  Key: hash(chunk_text) → embedding vector
  TTL: 24 hours
  Purpose: Avoid re-computing embeddings for identical text

Search Cache (Redis):
  Key: hash(query + filters) → search results
  TTL: 1 hour (invalidated on new document upload)
  Purpose: Fast repeated queries

LLM Response Cache (Redis):
  Key: hash(prompt + model) → LLM response
  TTL: 7 days
  Purpose: Avoid duplicate LLM calls (expensive)

Dashboard Cache (PostgreSQL):
  Field: documents.dashboard_data (JSONB)
  TTL: Permanent until re-processed
  Purpose: Instant dashboard loading
```

---

## 11. API Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| POST | `/auth/register` | Create account | API Key only |
| POST | `/auth/login` | Get JWT token | API Key only |
| GET | `/auth/me` | Get current user profile | JWT |

### Document Processing

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| POST | `/api/v2/generate` | Upload & process single document | JWT |
| POST | `/api/v2/generate-batch` | Upload 2-5 documents | JWT |
| GET | `/api/v2/task/{task_id}` | Check processing status | JWT |
| GET | `/api/v2/documents/{doc_id}` | Get document metadata | JWT |
| GET | `/api/v2/dashboard/{doc_id}` | Get full dashboard data | JWT |

### Search

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| POST | `/api/v2/search` | Hybrid search (BM25 + semantic + graph) | JWT |

### GraphRAG

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| POST | `/api/v2/graph/entities/search` | Find entities by name/type | JWT |
| GET | `/api/v2/graph/entities/{id}` | Get entity details + relationships | JWT |
| POST | `/api/v2/graph/paths/find` | Find paths between entities | JWT |

### DDR (Drilling)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| GET | `/api/v2/ddr/fleet` | Fleet-wide overview | JWT |
| GET | `/api/v2/ddr/rigs/{rig_id}` | Rig-level details & metrics | JWT |
| GET | `/api/v2/ddr/trends` | Metric trend analysis | JWT |
| GET | `/api/v2/ddr/audit` | Audit trail for metric changes | JWT |

### Observability

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| GET | `/api/v2/observability/health` | System health check | API Key |
| GET | `/api/v2/observability/models` | ML model registry | JWT |
| GET | `/api/v2/observability/drift` | Data drift alerts | JWT |

### WebSocket

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS | `/api/v2/ws/{doc_id}` | Real-time processing progress |

---

## 12. Key Features

### 12.1 Document Intelligence
- **Multi-format support**: PDF, Excel, CSV, Word, plain text
- **Adaptive chunking**: Table-aware, hierarchical, semantic boundaries
- **Batch processing**: 2-5 files simultaneously, 6-20 with queuing
- **Real-time progress**: WebSocket updates during processing
- **Citation tracking**: Every insight linked to source text

### 12.2 AI-Powered Analytics
- **Multi-LLM fallback**: Gemini → OpenAI → Claude (automatic)
- **Deduction engine**: Fact extraction with confidence scores
- **Knowledge graph**: Entity resolution + relationship mapping
- **Hybrid search**: BM25 + semantic + graph-based + LLM re-ranking
- **Pattern recognition**: Anomaly detection, clustering, trends

### 12.3 Visualization & Dashboards
- **8+ chart types**: Area, bar, line, pie, radar, scatter, funnel, sankey
- **Auto-chart selection**: AI picks best visualization for data type
- **KPI cards**: Trend arrows, sparklines, comparisons
- **Progressive disclosure**: CEO / Manager / Engineer / Boardroom views
- **PDF/Excel export**: One-click report generation

### 12.4 Six Sigma Quality Framework
- **DMAIC phases**: Define → Measure → Analyze → Improve → Control
- **Statistical Process Control**: Pp, Ppk, Cp, Cpk indices
- **Control charts**: X-bar, R, I-MR with UCL/LCL
- **Root cause analysis**: Ishikawa diagrams, correlation matrices
- **Process capability**: Target vs actual performance

### 12.5 Drilling Analytics (DDR Module)
- **Fleet-wide view**: All rigs at a glance
- **Rig-level detail**: Individual rig metrics & trends
- **Metric extraction**: Automated parsing of drilling reports
- **SPC per rig**: Statistical control for each operational metric
- **Audit trails**: Who changed what, when, why

### 12.6 Enterprise Features
- **Multi-tenant isolation**: Complete data separation per user
- **JWT authentication**: Secure, stateless, 24-hour sessions
- **API key management**: Rate-limited client identification
- **Role-based access**: Admin and regular user roles
- **Structured logging**: Full audit trail of all operations

---

## 13. Sub-Projects & Integrations

### 13.1 Anton (MindsDB)
- **Location**: `anton-main/`
- **Purpose**: MindsDB's open-source BI agent — asks questions in plain language, runs analysis, builds dashboards
- **Integration**: Referenced as inspiration/utility for natural language analytics
- **Tech**: Python, MindsDB SDK

### 13.2 DrillSight Analytics
- **Location**: `drillsight-analytics-main/`
- **Purpose**: Dedicated frontend for drilling analytics visualization
- **Tech**: React + TypeScript + Vite + Tailwind (same stack as main frontend)
- **Status**: Development (Lovable-generated scaffold)

### 13.3 RigSight Analytics
- **Location**: `rigsight-analytics/`
- **Purpose**: Rig-specific analytics dashboard
- **Tech**: React + TypeScript + Vite + Tailwind
- **Status**: Development

### 13.4 Project Relationship

```
TransIQ Platform
├── Backend (FastAPI) ← Single unified API server
├── Frontend (Main Dashboard) ← Primary user interface
├── DrillSight Analytics ← Specialized drilling frontend
├── RigSight Analytics ← Specialized rig frontend
└── Anton (reference) ← NL-to-analytics inspiration
```

---

## 14. Deployment Guide

### 14.1 Development Setup

**Backend:**
```bash
cd Backend
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
.venv\Scripts\Activate.ps1       # Windows

pip install -r requirements.txt
cp .env.example .env             # Configure API keys

# Start API server
uvicorn app.main:app --reload --port 8001

# Start Celery worker (separate terminal)
celery -A services.workers.processor.celery worker --loglevel=info
```

**Frontend:**
```bash
cd Frontend
npm install                      # or: bun install
cp .env.example .env.local       # Set VITE_API_KEY, VITE_API_BASE_URL

npm run dev                      # Starts on http://localhost:5173
```

**Infrastructure (Docker):**
```bash
# Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Qdrant
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# PostgreSQL (optional, SQLite works for dev)
docker run -d --name postgres -p 5432:5432 -e POSTGRES_DB=transiq postgres:15
```

### 14.2 Environment Variables

```bash
# === Backend .env ===

# Core
DEBUG=true
HOST=localhost
PORT=8001
FRONTEND_URL=http://localhost:5173

# Security
API_KEY=your-generated-key-here
API_KEY_2=optional-second-key
API_KEY_3=optional-third-key
JWT_SECRET=your-jwt-secret-key
RATE_LIMIT_PER_MINUTE=60

# Database
DATABASE_URL=sqlite:///./transiq.db          # Development
# DATABASE_URL=postgresql://user:pass@host/db  # Production

# LLM APIs
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=optional-openai-key
ANTHROPIC_API_KEY=optional-claude-key

# Infrastructure
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# === Frontend .env.local ===
VITE_API_KEY=your-api-key
VITE_API_BASE_URL=http://localhost:8001
```

### 14.3 Production Deployment

```yaml
# docker-compose.yml (Production)
services:
  api:
    build: ./Backend
    ports: ["8001:8001"]
    env_file: .env
    depends_on: [redis, postgres, qdrant]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001

  worker:
    build: ./Backend
    env_file: .env
    depends_on: [redis]
    command: celery -A services.workers.processor.celery worker -l info

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  postgres:
    image: postgres:15
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: transiq
      POSTGRES_USER: transiq
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant
    ports: ["6333:6333"]
    volumes:
      - qdrant_data:/qdrant/storage

  frontend:
    build: ./Frontend
    ports: ["80:80"]
    depends_on: [api]

volumes:
  pgdata:
  qdrant_data:
```

### 14.4 Production Checklist

```
Backend:
  ☐ Set strong JWT_SECRET (min 32 chars, random)
  ☐ Set strong API_KEY values
  ☐ Configure PostgreSQL (not SQLite)
  ☐ Run: alembic upgrade head (database migrations)
  ☐ Set DEBUG=false
  ☐ Configure CORS for production domain only
  ☐ Enable HTTPS (TLS certificates)
  ☐ Set RATE_LIMIT_PER_MINUTE=100 (production tier)

Frontend:
  ☐ Set VITE_API_BASE_URL to production API URL
  ☐ Run: npm run build
  ☐ Deploy dist/ to CDN (Vercel, Netlify, S3+CloudFront)
  ☐ Configure SSL certificate

Infrastructure:
  ☐ PostgreSQL 15+ (multi-AZ, auto-backup)
  ☐ Redis 7+ (ElastiCache or managed)
  ☐ Qdrant (latest, persistent storage)
  ☐ Firewall: only expose ports 80, 443, 8001
  ☐ Monitoring: Prometheus / Datadog
  ☐ Logging: CloudWatch / ELK stack
  ☐ Backup: Daily DB snapshots
```

---

## 15. Known Gaps & Roadmap

### Current Integration Issues

| Issue | Description | Priority |
|-------|-------------|:--------:|
| `/generate-project` endpoint | Frontend calls it but backend only has `/generate-batch` | High |
| `/user/me` path | Frontend uses wrong path (should be `/auth/me`) | Medium |
| `/history/` endpoint | Frontend expects it but backend doesn't implement it | Medium |
| Confusion matrix router | Not mounted in backend app/main.py | Low |
| Observability UI | Backend has 5 endpoints but no frontend pages | Medium |
| Graph Explorer UI | Backend GraphRAG ready but no visual graph explorer | Medium |

### Features Not Yet Built (Frontend)

| Feature | Backend Status | Frontend Status |
|---------|:-:|:-:|
| Observability Dashboard | ✅ Ready | ❌ Missing |
| Graph Explorer (visual) | ✅ Ready | ❌ Missing |
| Intelligence Recommendations | ✅ Ready | ❌ Missing |
| DDR Inline Editing | ✅ Ready | ❌ Missing |
| Metric Audit Timeline | ✅ Ready | ❌ Missing |
| Scenario Planner | ✅ Ready | ❌ Missing |

### Future Roadmap

```
Phase 6: Advanced Intelligence
  ├── Interactive graph explorer (force-directed visualization)
  ├── Scenario planning ("what-if" simulations)
  ├── Cross-document comparison
  └── Natural language query interface

Phase 7: Enterprise Scale
  ├── Organization-level multi-tenancy (teams)
  ├── SSO integration (SAML, OAuth2)
  ├── Custom branding per tenant
  └── Usage analytics & billing

Phase 8: Operational Excellence
  ├── ML model drift monitoring dashboard
  ├── A/B testing for LLM prompts
  ├── Automated retraining pipelines
  └── SLA monitoring & alerts
```

---

## 16. Glossary

| Term | Definition |
|------|-----------|
| **TransIQ** | The platform name — "Trans" (transform) + "IQ" (intelligence quotient) |
| **DDR** | Drilling Daily Report — operational reports from drilling rigs |
| **DMAIC** | Define, Measure, Analyze, Improve, Control — Six Sigma methodology |
| **SPC** | Statistical Process Control — monitoring via control charts |
| **GraphRAG** | Graph-based Retrieval Augmented Generation — combining knowledge graphs with LLM retrieval |
| **RAG** | Retrieval Augmented Generation — fetching relevant context before LLM generation |
| **Qdrant** | Open-source vector similarity search engine |
| **HNSW** | Hierarchical Navigable Small World — algorithm for fast approximate nearest neighbor search |
| **BM25** | Best Matching 25 — probabilistic ranking algorithm for keyword search |
| **Celery** | Distributed task queue for Python |
| **JWT** | JSON Web Token — stateless authentication mechanism |
| **Cpk/Ppk** | Process capability indices measuring how well a process meets specifications |
| **Embedding** | Dense vector representation of text (384-dimension in this project) |
| **Multi-tenant** | Single system serving multiple isolated customers |
| **Progressive Disclosure** | UI pattern showing different detail levels for different audiences |
| **Hybrid Search** | Combining multiple search strategies (keyword + semantic + graph) |
| **Deduction Engine** | LLM-powered fact extraction and reasoning system |
| **Control Chart** | Statistical tool showing process variation over time with control limits |

---

## Document Metadata

| Field | Value |
|-------|-------|
| Project Name | TransIQ |
| Type | AI-Powered Multi-Tenant SaaS Analytics Platform |
| Primary Language (BE) | Python 3.11+ |
| Primary Language (FE) | TypeScript (React) |
| Repository Structure | Monorepo (Backend + Frontend + Sub-projects) |
| Development Status | Active — Phase 5 complete, Phase 6 planning |
| Team Size | Small team (startup) |
| License | Proprietary |

---

*End of Document*
