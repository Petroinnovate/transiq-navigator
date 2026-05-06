# TransIQ — Lovable-Ready UI/UX Design Specification

> **Purpose:** This document is a complete, copy-paste-ready specification for regenerating the TransIQ AI-powered drilling analytics dashboard in [Lovable](https://lovable.dev). Every section includes exact layout rules, component APIs, color tokens, API endpoints, and JSON response shapes so that Lovable can produce production-quality code with **minimal ambiguity**.

---

## Table of Contents

1. [App Shell & Global Layout](#1-app-shell--global-layout)
2. [Design System](#2-design-system)
3. [Page Specifications](#3-page-specifications)
4. [Reusable Component Library](#4-reusable-component-library)
5. [API → UI Mapping](#5-api--ui-mapping)
6. [Interaction Design](#6-interaction-design)
7. [State Management](#7-state-management)
8. [Technology Stack](#8-technology-stack)

---

## 1. App Shell & Global Layout

### 1.1 Architecture

TransIQ is a **single-page React application** with the following shell:

```
┌──────────────────────────────────────────────────┐
│  Top Bar (sticky, z-50)                          │
│  [Logo] [Page Title]          [Alerts] [Avatar]  │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌────────────┐  ┌─────────────────────────────┐ │
│  │  Sidebar   │  │  Main Content Area           │ │
│  │  Nav       │  │  (scrollable)                │ │
│  │  (240px)   │  │                              │ │
│  │            │  │                              │ │
│  │  collapsed │  │                              │ │
│  │  = 64px    │  │                              │ │
│  └────────────┘  └─────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

> **Current state:** The existing app uses a **landing-page hub** pattern (Index.tsx has buttons to every page). For production, add a **persistent collapsible sidebar** on all authenticated pages. On mobile (< 768px), the sidebar becomes a slide-out sheet.

### 1.2 Sidebar Navigation

| Order | Label | Icon (Lucide) | Route | Badge |
|-------|-------|---------------|-------|-------|
| 1 | Home | `LayoutDashboard` | `/` | — |
| 2 | Upload | `Upload` | `/upload` | — |
| 3 | Dashboard | `BarChart3` | `/dashboard` | — |
| 4 | Search | `Search` | `/search` | — |
| 5 | Agent Lab | `Bot` | `/agent-lab` | — |
| 6 | Confusion Matrix | `Grid3X3` | `/confusion-matrix` | — |
| — | **— separator —** | | | |
| 7 | Observability | `Activity` | `/observability` | Drift alert count (red dot) |
| 8 | Intelligence Hub | `Zap` | `/intelligence` | — |
| 9 | Knowledge Graph | `Network` | `/graph-explorer` | — |
| — | **— separator —** | | | |
| 10 | Demo | `Eye` | `/demo` | — |
| 11 | Profile | `User` | `/profile` | — |

**Sidebar Styling:**
```
Background: bg-slate-900 border-r border-slate-700/50
Active Item: bg-cyan-500/10 text-cyan-400 border-l-2 border-cyan-400
Inactive Item: text-slate-400 hover:text-slate-200 hover:bg-slate-800/50
Section Label: text-[10px] uppercase tracking-widest text-slate-500 px-4 mt-4 mb-1
Logo area: px-4 py-5, logo text "TransIQ" with bg-gradient-to-r from-cyan-400 to-teal-400 bg-clip-text text-transparent font-bold text-xl
Collapse button: bottom of sidebar, ChevronLeft/ChevronRight icon
```

### 1.3 Top Bar

```
Height: h-14
Background: bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50
Left: Page title (text-lg font-semibold text-white)
Right cluster:
  - Drift Alert bell icon with red badge (count from /observability/drift)
  - System health dot (green/yellow/red from /observability/health)
  - User avatar circle (initials, bg-cyan-500/20 text-cyan-400)
    → Dropdown: Profile, Sign Out
```

### 1.4 Route Protection

| Route | Access |
|-------|--------|
| `/`, `/auth`, `/demo` | Public |
| All others | Require auth token (redirect to `/auth` if missing) |

---

## 2. Design System

### 2.1 Color Palette

#### Background Scale (Dark Mode — Primary)
| Token | Value | Usage |
|-------|-------|-------|
| `--bg-app` | `slate-950` (#020617) | Body background |
| `--bg-page` | `bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900` | Page container |
| `--bg-card` | `slate-800/60` | Card backgrounds |
| `--bg-card-hover` | `slate-800/80` | Card hover state |
| `--bg-input` | `slate-700/50` | Text inputs, selects |
| `--bg-panel` | `slate-700/30` | Inset panels, accordion content |
| `--bg-overlay` | `slate-900/80 backdrop-blur-md` | Modals, sheets, top bar |

#### Accent Colors
| Token | Value | Usage |
|-------|-------|-------|
| `--accent-primary` | `cyan-400` (#22d3ee) | Icons, active nav, links |
| `--accent-gradient` | `from-cyan-400 to-teal-400` | Logo, headings, highlights |
| `--accent-cta` | `from-cyan-500 to-teal-500` | Primary buttons |
| `--accent-cta-hover` | `from-cyan-600 to-teal-600` | Primary button hover |
| `--accent-subtle` | `cyan-500/20` | Active tab bg, icon containers |

#### Semantic Status Colors
| Status | Background | Text | Border | Usage |
|--------|-----------|------|--------|-------|
| Success | `emerald-500/20` | `emerald-400` | `emerald-500/30` | Healthy, positive trend, ✓ passed |
| Warning | `yellow-500/20` | `yellow-400` | `yellow-500/30` | Degraded, moderate drift |
| Danger | `red-500/20` | `red-400` | `red-500/30` | Critical, negative trend, errors |
| Info | `blue-500/20` | `blue-400` | `blue-500/30` | Informational badges |
| Neutral | `slate-700/60` | `slate-400` | `slate-600/30` | Disabled, N/A |

#### Priority Colors (Recommendations)
| Priority | Background | Text | Border |
|----------|-----------|------|--------|
| Critical | `red-500/20` | `red-400` | `red-500/30` |
| High | `orange-500/20` | `orange-400` | `orange-500/30` |
| Medium | `yellow-500/20` | `yellow-400` | `yellow-500/30` |
| Low | `blue-500/20` | `blue-400` | `blue-500/30` |

#### Chart Color Palette (ordered series)
```
['#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6', '#f97316', '#84cc16']
 Cyan      Emerald    Amber      Red        Violet     Blue       Orange     Lime
```

### 2.2 Typography

| Element | Classes |
|---------|---------|
| Page Title | `text-3xl md:text-4xl font-bold text-white` |
| Page Subtitle | `text-lg text-slate-400` |
| Section Title | `text-xl font-semibold text-white` |
| Card Title | `text-lg font-semibold text-white flex items-center gap-2` |
| Body Text | `text-sm text-slate-300` |
| Label | `text-[11px] uppercase tracking-wider text-slate-400 font-medium` |
| KPI Value | `text-2xl font-bold text-white tabular-nums` |
| Caption / Helper | `text-xs text-slate-500` |
| Code / Mono | `font-mono text-sm text-slate-300` |

### 2.3 Spacing & Layout

| Token | Value |
|-------|-------|
| Page padding | `p-6 md:p-8` |
| Card padding | `p-4 md:p-6` |
| Section gap | `space-y-6` |
| Card grid gap | `gap-4 md:gap-6` |
| Card border radius | `rounded-lg` (8px) |
| Card border | `border border-slate-700` |
| Card shadow | `shadow-sm`, hover: `shadow-lg shadow-cyan-500/5` |

### 2.4 Animations & Transitions

```css
/* Card hover */
transition-all duration-300

/* Fade in on mount */
@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
.animate-fade-in { animation: fade-in 0.3s ease-out; }

/* Skeleton loader pulse */
@keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 0.8; } }
.animate-pulse { animation: pulse 1.5s ease-in-out infinite; }

/* Spinner */
.animate-spin { animation: spin 1s linear infinite; }

/* Backdrop blur for overlays */
backdrop-blur-md = backdrop-filter: blur(12px);
```

### 2.5 Chart Tooltip

```ts
const tooltipStyle = {
  backgroundColor: '#1e293b',   // slate-800
  border: '1px solid #475569',  // slate-600
  borderRadius: '8px',
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
  color: '#f1f5f9',             // slate-100
  fontSize: '12px',
  padding: '8px 12px'
};
```

---

## 3. Page Specifications

### 3.1 Landing Page (`/` — Index.tsx)

**Purpose:** App entry point. Showcases capabilities, routes users to key features.

**Layout:**
```
Full-screen gradient background:
  bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900

┌─────────────────────────────────────────────┐
│ Navbar: [Logo "TransIQ"]     [New Viz] [👤] │
├─────────────────────────────────────────────┤
│                                             │
│  ✦ Sparkle icon                             │
│  "TransIQ" (gradient text, 4xl/5xl bold)    │
│  "AI-Powered" (gradient text)               │
│  Subtitle (text-slate-400)                  │
│                                             │
│  [Upload Data] [View Demo] [Agent Lab]      │
│  (Primary CTA)  (Ghost)    (Ghost)          │
│                                             │
│  Platform Tools:                            │
│  [Observability] [Intelligence] [Graph]     │
│  (outline cyan buttons)                     │
│                                             │
│  ── Feature Cards Grid (3 cols) ──          │
│  │ Upload │ AI │ Charts │ RT │ Security │   │
│                                             │
│  ── Stats Row ──                            │
│  10M+ Data Points | 94% Accuracy | <30s     │
│                                             │
│  [Bottom CTA]                               │
│  Footer                                     │
└─────────────────────────────────────────────┘
```

**Component Breakdown:**
| Component | Classes | API |
|-----------|---------|-----|
| Logo | `bg-gradient-to-r from-cyan-400 to-teal-400 bg-clip-text text-transparent font-bold text-2xl` | — |
| Primary CTA button | `bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-600 hover:to-teal-600 text-white font-semibold px-8 py-3 rounded-lg shadow-lg shadow-cyan-500/25` | — |
| Ghost button | `border border-slate-600 text-slate-300 hover:bg-slate-700/50 hover:text-white px-6 py-3 rounded-lg` | — |
| Platform tool button | `border border-cyan-500/30 text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20 px-4 py-2 rounded-lg` | — |
| Feature card | `bg-slate-800/40 border border-slate-700/50 rounded-xl p-6 text-center hover:border-cyan-500/30 transition-all` | — |
| Stat block | `text-3xl font-bold text-white` value + `text-sm text-slate-400` label | — |

**State Logic:**
- If `dashboardData` exists in context → show "Go to Dashboard" button instead of "Upload"
- If authenticated → show avatar; else "Sign In"

---

### 3.2 Auth Page (`/auth`)

**Purpose:** Login and registration.

**Layout:**
```
Centered card on gradient background.
Max-width: max-w-md mx-auto

┌──────────────────────────────┐
│  ← Back to Home              │
│                              │
│  "Welcome to TransIQ"        │
│                              │
│  [Sign In] [Sign Up]  ← Tabs │
│                              │
│  ┌────────────────────────┐  │
│  │ Email                  │  │
│  │ Password       [👁]   │  │
│  │ [Sign In Button]       │  │
│  └────────────────────────┘  │
│                              │
│  Sign Up tab adds:           │
│  │ Full Name              │  │
│  │ Confirm Password       │  │
└──────────────────────────────┘
```

**Validation (zod):**
| Field | Sign In | Sign Up |
|-------|---------|---------|
| name | — | min 2 chars |
| email | valid email | valid email |
| password | min 6 | min 8 |
| confirmPassword | — | must match password |

**API Mapping:**
| Action | Endpoint | Request | Response |
|--------|----------|---------|----------|
| Login | `POST /auth/login` | `{ email, password }` | `{ access_token, token_type, user_id, email }` |
| Register | `POST /auth/register` | `{ email, password, name }` | `{ access_token, token_type, user_id, email }` |

**Behavior:**
- On success → store `access_token` in `localStorage` as `auth_token`, store `{ user_id, email, name }` as `user_data`
- Redirect to `/` after login
- If already authenticated → auto-redirect to `/`
- Password toggle: Eye/EyeOff icon

---

### 3.3 Upload Page (`/upload`)

**Purpose:** Upload DDR (Deep Drilling Report) files for AI processing.

**Layout:**
```
┌──────────────────────────────────────────┐
│ "Upload Your Data"                       │
│ "Drag & drop or click to upload"         │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │                                      │ │
│ │       [Drag & Drop Zone]             │ │
│ │       Upload (cloud icon)            │ │
│ │       Supports: PDF, DOCX, CSV       │ │
│ │       Max: 50MB                      │ │
│ │                                      │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ File list (if files selected):           │
│ ┌──────────────────────────────────────┐ │
│ │ file1.pdf  12.3 MB  [✕ Remove]      │ │
│ │ file2.docx  3.1 MB  [✕ Remove]      │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ [Generate Dashboard]  ← Primary CTA      │
│                                          │
│ ── Processing Progress ──                │
│ ┌──────────────────────────────────────┐ │
│ │ ▓▓▓▓▓▓▓▓▓▓░░░░░░░░  45%            │ │
│ │ Stage: Analyzing sections...          │ │
│ │ ETA: ~20s remaining                   │ │
│ └──────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

**Drop Zone Styling:**
```
Default: border-2 border-dashed border-slate-600 rounded-xl p-12 text-center bg-slate-800/30
Drag Over: border-cyan-400 bg-cyan-500/5
Has Files: border-emerald-500/50 bg-emerald-500/5
```

**API Mapping:**
| Action | Endpoint | Request | Response |
|--------|----------|---------|----------|
| Upload files | `POST /api/v2/upload` | `multipart/form-data` | `{ task_id, status }` |
| Generate dashboard | `POST /api/v2/generate-batch` | `{ project_name, document_ids }` | `{ batch_id, status }` |
| Poll batch status | `GET /api/v2/batch-status/{batch_id}` | — | `{ status, progress, dashboard_data }` |

**Behavior:**
- After upload → poll batch status every 3 seconds
- Show progress bar with stages: Uploading → Analyzing → Generating → Complete
- On complete → store dashboard data in DashboardContext → navigate to `/dashboard`

---

### 3.4 Dashboard Page (`/dashboard`)

**Purpose:** Primary analytics dashboard with AI-generated KPIs, charts, and insights.

**Layout:**
```
┌─────────────────────────────────────────────────┐
│ Floating Mode Switcher (top-right, z-50):       │
│   [📊 Analytics] [⛏ Drilling]                   │
├─────────────────────────────────────────────────┤
│                                                 │
│ MODE = "analytics":                             │
│ ┌────────────────────────────────────────────┐  │
│ │ Project Banner                             │  │
│ │ Title, timestamp, quality score            │  │
│ └────────────────────────────────────────────┘  │
│                                                 │
│ ── KPI Grid (2-4 cols responsive) ──            │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐            │
│ │ KPI1 │ │ KPI2 │ │ KPI3 │ │ KPI4 │            │
│ └──────┘ └──────┘ └──────┘ └──────┘            │
│                                                 │
│ ── Charts Grid ──                               │
│ ┌─────────────────┐ ┌─────────────────┐         │
│ │ Chart (full/half)│ │ Chart (half)    │         │
│ └─────────────────┘ └─────────────────┘         │
│                                                 │
│ ── Insights Section ──                          │
│ ┌────────────────────────────────────────────┐  │
│ │ AI-generated narrative insights            │  │
│ │ With citations [Source: DDR p.3]           │  │
│ └────────────────────────────────────────────┘  │
│                                                 │
│ ── Six Sigma Section ──                         │
│ ┌────────────────────────────────────────────┐  │
│ │ DMAIC phases, process capability           │  │
│ └────────────────────────────────────────────┘  │
│                                                 │
│ ── Optimization Suggestions ──                  │
│ ┌────────────────────────────────────────────┐  │
│ │ AI recommendations cards                   │  │
│ └────────────────────────────────────────────┘  │
│                                                 │
│ MODE = "drilling":                              │
│ ┌────────────────────────────────────────────┐  │
│ │ <DDRDashboard /> (full drilling analytics) │  │
│ └────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**Mode Switcher Styling:**
```
Container: fixed top-4 right-4 z-50 flex bg-slate-800/90 backdrop-blur-sm rounded-lg border border-slate-700 p-1
Active tab: bg-cyan-500/20 text-cyan-400 rounded-md px-3 py-1.5
Inactive tab: text-slate-400 hover:text-slate-200 px-3 py-1.5
```

**API Mapping:**
| Component | Endpoint | Response Shape |
|-----------|----------|---------------|
| Full dashboard | `GET /api/v2/dashboard/latest` | `DashboardData` (see §5.1) |
| Specific report | `GET /api/v2/dashboard/{reportId}` | `DashboardData` |
| Export PDF | `GET /api/v2/dashboard/export/pdf/{id}` | Binary PDF |
| Export Excel | `GET /api/v2/dashboard/export/excel/{id}` | Binary XLSX |

**DashboardData Shape:**
```json
{
  "report_id": "uuid",
  "project_name": "West Africa Drilling Campaign",
  "generated_at": "2025-01-15T10:30:00Z",
  "quality_score": 0.87,
  "kpis": [
    {
      "kpi_id": "rop_avg",
      "label": "Avg ROP",
      "value": 48.5,
      "unit": "ft/hr",
      "change_pct": 12.3,
      "trend": "up",
      "target": 55.0,
      "priority_score": 82,
      "sparkline": [42, 44, 45, 48, 50, 48.5],
      "status": "warning"
    }
  ],
  "charts": [
    {
      "chart_id": "rop_over_depth",
      "title": "ROP vs Depth",
      "chart_type": "line",
      "size": "half",
      "data": [{"depth": 1000, "rop": 42}, ...],
      "x_axis": "depth",
      "y_axis": ["rop"]
    }
  ],
  "insights": [
    {
      "title": "Drilling Performance Insight",
      "content": "ROP showed 12% improvement in the 12¼\" section...",
      "citations": [{"source": "DDR", "page": 3, "quote": "..."}],
      "confidence": 0.91
    }
  ],
  "sections": [...],
  "six_sigma": {...},
  "recommendations": [...]
}
```

**Sub-Components:**

| Component | Description | Grid |
|-----------|-------------|------|
| `ProjectBanner` | Title, date, quality score badge | Full width |
| `KPICard` | Metric with sparkline, trend arrow, priority badge | `grid-cols-2 md:grid-cols-3 lg:grid-cols-4` |
| `ChartRenderer` | Recharts wrapper (Line, Bar, Area, Pie, Radar, Scatter, Sankey, Funnel) | Per chart `size` field |
| `InsightsSection` | AI narrative with citations | Full width |
| `SixSigmaSection` | DMAIC analysis accordion | Full width |
| `OptimizationSuggestions` | Recommendation cards | Full width |
| `QualityScoreCard` | Circular score gauge | Sidebar or inline |

---

### 3.5 DDR Drilling Dashboard (mode: drilling)

**Purpose:** Deep drilling report analytics with fleet view, rig performance, SPC charts, and NPT analysis.

**Layout:**
```
┌──────────────────────────────────────────────────┐
│ DDR Sidebar (left, 280px)                         │
│ ┌─────────┐ ┌──────────────────────────────────┐ │
│ │ Fleet   │ │  Main Content                    │ │
│ │ summary │ │                                  │ │
│ │ Rig list│ │  Tab: Overview | Performance |   │ │
│ │ ┌─────┐ │ │       AI Assistant | Audit       │ │
│ │ │Rig 1│ │ │                                  │ │
│ │ │Rig 2│ │ │  ── KPI Row ──                   │ │
│ │ │Rig 3│ │ │  [ROP] [Footage] [NPT] [Mud]    │ │
│ │ └─────┘ │ │                                  │ │
│ │         │ │  ── Charts ──                    │ │
│ │         │ │  [SPC Chart] [NPT Pareto]        │ │
│ │         │ │  [Trend Lines] [Heatmap]         │ │
│ │         │ │                                  │ │
│ │         │ │  ── AI Assistant Panel ──         │ │
│ │         │ │  Chat interface for drilling Q&A  │ │
│ └─────────┘ └──────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

**API Mapping:**
| Component | Endpoint | Response Key Fields |
|-----------|----------|-------------------|
| Fleet summary | `GET /api/v2/fleet/summary` | `total_rigs`, `avg_rop`, `total_footage`, `total_npt_hours`, `kpis[]` |
| NPT Pareto | `GET /api/v2/fleet/npt-pareto` | `pareto[].cause_code`, `.hours`, `.percentage`, `.cumulative_pct` |
| SPC chart | `GET /api/v2/fleet/spc/{metric}` | `spc.mean`, `.ucl`, `.lcl`, `.data_points` |
| Rig detail | `GET /api/v2/fleet/rig/{rig_id}` | Rig-specific KPIs and trends |
| Rig trends | `GET /api/v2/fleet/rig/{rig_id}/trends` | Time-series arrays |
| Audit trail | `GET /api/v2/fleet/rig/{rig_id}/audit` | Extraction audit log entries |

---

### 3.6 Search Page (`/search`)

**Purpose:** AI-powered semantic search across uploaded documents.

**Layout:**
```
┌────────────────────────────────────────────┐
│ "Search Your Documents"                    │
│                                            │
│ ┌────────────────────────────────────────┐ │
│ │ 🔍 [Search query input...........  ]  │ │
│ │ Filters: [Document ▾] [Date Range ▾]  │ │
│ └────────────────────────────────────────┘ │
│                                            │
│ Results:                                   │
│ ┌────────────────────────────────────────┐ │
│ │ Result 1                               │ │
│ │ "...matched text with highlights..."   │ │
│ │ Source: DDR-001 p.12  Score: 0.94      │ │
│ ├────────────────────────────────────────┤ │
│ │ Result 2                               │ │
│ │ "...matched text..."                   │ │
│ │ Source: DDR-002 p.5   Score: 0.87      │ │
│ └────────────────────────────────────────┘ │
└────────────────────────────────────────────┘
```

**API Mapping:**
| Action | Endpoint | Request | Response |
|--------|----------|---------|----------|
| Search | `POST /api/v2/search` | `{ query, top_k?, filters? }` | `{ results[].text, .score, .source, .page }` |

---

### 3.7 Agent Lab (`/agent-lab`)

**Purpose:** Interactive AI agent chat interface for drilling Q&A and analysis.

**Layout:**
```
┌──────────────────────────────────────────┐
│ "Agent Lab"                              │
│ "Ask AI about your drilling data"        │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ Chat history (scrollable)            │ │
│ │                                      │ │
│ │ [User]: What caused the NPT on...   │ │
│ │ [Agent]: Based on the DDR data...    │ │
│ │         Citation: [DDR p.5]          │ │
│ │                                      │ │
│ │ [User]: Compare rig performance...   │ │
│ │ [Agent]: Analysis shows...           │ │
│ │         [Inline Chart]               │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ ┌──────────────────────────────────────┐ │
│ │ [Message input.........] [Send ▶]   │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ Suggested prompts:                       │
│ [Risk assessment] [Performance compare]  │
└──────────────────────────────────────────┘
```

**Chat Message Styling:**
```
User message: bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-3 text-slate-200 ml-12
Agent message: bg-slate-800/60 border border-slate-700 rounded-lg p-3 text-slate-300 mr-12
Agent thinking: animate-pulse bg-slate-700/50 rounded-lg p-3 (3 dots animation)
Citation badge: text-xs bg-slate-700 text-cyan-400 px-2 py-0.5 rounded cursor-pointer hover:bg-slate-600
```

**API Mapping:**
| Action | Endpoint | Request | Response |
|--------|----------|---------|----------|
| Send message | `POST /api/v2/agent/query` | `{ query, context? }` | `{ response, citations[], charts?[] }` |
| WebSocket stream | `WS /api/v2/ws/agent` | `{ query }` | Streaming text chunks |

---

### 3.8 Confusion Matrix (`/confusion-matrix`)

**Purpose:** Model evaluation with interactive confusion matrix visualization.

**Layout:**
```
┌────────────────────────────────────────────┐
│ "Confusion Matrix Analysis"                │
│                                            │
│ ┌──────┐ Upload CSV or select model        │
│ │ [Upload CSV] [Select Model ▾]            │
│ └──────┘                                   │
│                                            │
│ ┌────────────────────────────────────────┐ │
│ │         Predicted                      │ │
│ │        A    B    C    D                │ │
│ │   A  [85] [ 3] [ 2] [ 1]              │ │
│ │ A B  [ 5] [72] [ 4] [ 2]              │ │
│ │ c C  [ 1] [ 6] [68] [ 3]              │ │
│ │ t D  [ 2] [ 1] [ 5] [80]              │ │
│ │                                        │ │
│ │ Heatmap colors: green (diagonal) →     │ │
│ │                  red (off-diagonal)     │ │
│ └────────────────────────────────────────┘ │
│                                            │
│ Metrics Row:                               │
│ [Accuracy: 0.87] [Precision: 0.84]        │
│ [Recall: 0.82]   [F1: 0.83]               │
│                                            │
│ Per-class breakdown table                  │
└────────────────────────────────────────────┘
```

**API Mapping:**
| Action | Endpoint | Request | Response |
|--------|----------|---------|----------|
| Upload CSV | `POST /api/v2/confusion-matrix` | `multipart/form-data { file }` | `{ matrix, labels, metrics }` |
| Get analysis | `GET /api/v2/confusion-matrix/{id}` | — | Same shape |

---

### 3.9 Observability Page (`/observability`)

**Purpose:** ML Ops monitoring — system health, model registry, feature store, prediction stats, drift detection.

**Layout:**
```
┌─────────────────────────────────────────────────┐
│ "Observability Center"                          │
│ Activity icon (cyan-400)                        │
│ "Monitor models, features, and system health"   │
│                                                 │
│ [Health] [Models] [Features] [Predictions]      │
│ [Drift Monitor]                     ← Tab bar   │
│                                                 │
│ ═══ TAB: System Health ═══                      │
│ ┌─────────────────────────────────────────────┐ │
│ │ Overall: ● Healthy                          │ │
│ │                                             │ │
│ │ Health Checks Grid (2→3→5 cols):            │ │
│ │ ┌─────────┐ ┌─────────┐ ┌─────────┐        │ │
│ │ │ API     │ │ Database│ │ Redis   │        │ │
│ │ │ ● pass  │ │ ● pass  │ │ ● warn  │        │ │
│ │ │ 12ms    │ │ 45ms    │ │ timeout │        │ │
│ │ └─────────┘ └─────────┘ └─────────┘        │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ═══ TAB: Model Registry ═══                    │
│ ┌─────────────────────────────────────────────┐ │
│ │ Model Cards Grid (1→2→3 cols):              │ │
│ │ ┌───────────────────────┐                   │ │
│ │ │ Model: NPT Predictor  │                   │ │
│ │ │ Version: v2.3          │                   │ │
│ │ │ Stage: production ●    │                   │ │
│ │ │ Accuracy: 0.91         │                   │ │
│ │ │ F1: 0.88    AUC: 0.94  │                   │ │
│ │ └───────────────────────┘                   │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ═══ TAB: Feature Store ═══                     │
│ Table: name | type | stale? | staleness_hours   │
│ Stale badge: bg-red-500/20 text-red-400         │
│ Fresh badge: bg-emerald-500/20 text-emerald-400 │
│ Auto-refresh: 60s                               │
│                                                 │
│ ═══ TAB: Predictions ═══                       │
│ Stats cards + Latency chart (Area):             │
│ [Total] [Avg Latency] [P95] [Max] [Error Rate] │
│ Recharts AreaChart of latency over time         │
│                                                 │
│ ═══ TAB: Drift Monitor ═══                     │
│ Confidence trend LineChart                      │
│ Stale features count with alert threshold       │
│ Auto-refresh: 30s                               │
└─────────────────────────────────────────────────┘
```

**API Mapping:**
| Tab | Endpoint | Refresh | Response Shape |
|-----|----------|---------|---------------|
| Health | `GET /api/v2/observability/health` | 30s | `{ status: "healthy"│"degraded"│"unhealthy", checks: { [name]: { status, latency_ms?, message? } } }` |
| Models | `GET /api/v2/observability/models` | 60s | `{ models: [{ model_id, name, version, stage, metrics: { accuracy, f1, auc } }] }` |
| Features | `GET /api/v2/observability/features` | 60s | `{ features: [{ name, type, stale, staleness_hours }] }` |
| Predictions | `GET /api/v2/observability/predictions` | 30s | `{ stats: { total, avg_latency_ms, p95_latency_ms, max_latency_ms, error_rate }, recent: [{ timestamp, latency_ms }] }` |
| Drift | `GET /api/v2/observability/drift` | 30s | `{ confidence_trend: [{ timestamp, confidence }], stale_features: number, alert_threshold }` |

**Status Badge Component:**
```
healthy/pass: bg-emerald-500/20 text-emerald-400 border-emerald-500/30
degraded/warn: bg-yellow-500/20 text-yellow-400 border-yellow-500/30
unhealthy/fail: bg-red-500/20 text-red-400 border-red-500/30
```

---

### 3.10 Intelligence Hub (`/intelligence`)

**Purpose:** KPI impact analysis, DMAIC process control, AI recommendations, scenario planning.

**Layout:**
```
┌─────────────────────────────────────────────────┐
│ "Intelligence Hub"                              │
│ Zap icon (cyan-400)                             │
│ "Advanced analytics and impact analysis"        │
│                                                 │
│ Controls Row:                                   │
│ [Entity ID input] [KPI ID input]                │
│                                                 │
│ [DMAIC Analysis] [Recommendations] [Scenarios]  │
│                                       ← Tabs    │
│                                                 │
│ ═══ TAB: DMAIC Analysis ═══                    │
│ ┌─────────────────────────────────────────────┐ │
│ │ Accordion per DMAIC phase:                  │ │
│ │                                             │ │
│ │ ▼ Define  (Target icon)                     │ │
│ │   Problem statement, scope, objectives      │ │
│ │                                             │ │
│ │ ▼ Measure (TrendingUp icon)                 │ │
│ │   Current performance baseline metrics      │ │
│ │                                             │ │
│ │ ▼ Analyze (Zap icon)                        │ │
│ │   Root causes, contributing factors         │ │
│ │                                             │ │
│ │ ▼ Improve (Lightbulb icon)                  │ │
│ │   Recommended improvements, priority matrix │ │
│ │                                             │ │
│ │ ▼ Control (Shield icon)                     │ │
│ │   Monitoring plan, alert thresholds         │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ═══ TAB: Recommendations ═══                   │
│ ┌─────────────────────────────────────────────┐ │
│ │ Card per recommendation:                    │ │
│ │ ┌─────────────────────────────────────────┐ │ │
│ │ │ [Priority badge] Engine: financial      │ │ │
│ │ │ Action: "Optimize mud weight to..."     │ │ │
│ │ │ Impact: $140K savings                   │ │ │
│ │ │ Timeline: 2 weeks                       │ │ │
│ │ │ Confidence: 87%                         │ │ │
│ │ └─────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ═══ TAB: Scenario Planner ═══                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ Scenario Config:                            │ │
│ │ [Parameter input] [Adjustment % slider]     │ │
│ │ [Run Scenario] button                       │ │
│ │                                             │ │
│ │ Results:                                    │ │
│ │ BarChart comparing Baseline vs Projected    │ │
│ │ for each affected KPI                       │ │
│ │                                             │ │
│ │ Impact summary text                         │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**API Mapping:**
| Tab | Endpoint | Request | Response Shape |
|-----|----------|---------|---------------|
| DMAIC | `POST /api/v2/impact/dmaic` | `{ entity_id, kpi_id }` | `{ phases: { define: { problem, scope, objectives }, measure: { baseline, metrics }, analyze: { root_causes, factors }, improve: { recommendations, matrix }, control: { plan, thresholds } } }` |
| Recommendations | `POST /api/v2/intelligence/recommendations` | `{ entity_id }` | `{ recommendations: [{ engine, priority, action, impact_estimate, timeline, confidence }] }` |
| Scenario | `POST /api/v2/impact/scenario` | `{ entity_id, parameter, adjustment_pct }` | `{ scenario_results: [{ kpi, baseline, projected, delta_pct }], summary }` |
| KPI Impact | `POST /api/v2/impact/analyze-kpi-impact` | `{ entity_id, kpi_id }` | `{ total_impact, direct_impact, cascading_impact, cascading_paths[], root_cause_chain[], recommendations }` |

**DMAIC Phase Icons:**
| Phase | Icon | Color |
|-------|------|-------|
| Define | `Target` | `text-cyan-400` |
| Measure | `TrendingUp` | `text-emerald-400` |
| Analyze | `Zap` | `text-yellow-400` |
| Improve | `Lightbulb` | `text-orange-400` |
| Control | `Shield` | `text-blue-400` |

---

### 3.11 Knowledge Graph Explorer (`/graph-explorer`)

**Purpose:** Browse entity knowledge graph, find paths between entities, view centrality analysis.

**Layout:**
```
┌─────────────────────────────────────────────────┐
│ "Knowledge Graph Explorer"                      │
│ Network icon (cyan-400)                         │
│ "Explore entity relationships and connections"  │
│                                                 │
│ [Search & Browse] [Path Finder] [Centrality]    │
│                                       ← Tabs    │
│                                                 │
│ ═══ TAB: Search & Browse ═══                   │
│ ┌──────────────────┐ ┌────────────────────────┐ │
│ │ Entity Search    │ │ Entity Detail          │ │
│ │                  │ │                        │ │
│ │ [🔍 Search...]  │ │ Name: Stuck Pipe       │ │
│ │                  │ │ Type: NPT Event        │ │
│ │ Results:         │ │ Mentions: 23           │ │
│ │ ├ Stuck Pipe     │ │ PageRank: 0.042        │ │
│ │ ├ BHA Failure    │ │                        │ │
│ │ ├ Mud Weight     │ │ Properties:            │ │
│ │ └ ROP            │ │ ├ severity: high       │ │
│ │                  │ │ ├ avg_hours: 8.5       │ │
│ │                  │ │                        │ │
│ │                  │ │ Relationships:          │ │
│ │                  │ │ → causes: NPT (0.92)   │ │
│ │                  │ │ → affects: ROP (0.78)   │ │
│ └──────────────────┘ └────────────────────────┘ │
│                                                 │
│ ═══ TAB: Path Finder ═══                       │
│ ┌─────────────────────────────────────────────┐ │
│ │ [Source Entity ▾] → [Target Entity ▾]       │ │
│ │ Max Depth: [3 ▾]                            │ │
│ │ [Find Paths]                                │ │
│ │                                             │ │
│ │ Paths found: 3                              │ │
│ │ Path 1: A → B → C (depth: 2, conf: 0.85)   │ │
│ │ Path 2: A → D → E → C (depth: 3)            │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ═══ TAB: Centrality ═══                        │
│ ┌─────────────────────────────────────────────┐ │
│ │ Top entities by PageRank:                   │ │
│ │ Horizontal BarChart (Recharts)              │ │
│ │ ██████████████████ ROP (0.089)              │ │
│ │ ██████████████ NPT (0.067)                  │ │
│ │ ████████████ Mud Weight (0.054)             │ │
│ │ ████████ BHA (0.041)                        │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**API Mapping:**
| Tab | Endpoint | Request | Response Shape |
|-----|----------|---------|---------------|
| Search | `GET /api/v2/graph/entities?q={query}` | query param | `{ entities: [{ entity_id, name, type, mention_count }] }` |
| Detail | `GET /api/v2/graph/entities/{id}` | — | `{ entity_id, name, type, mention_count, pagerank, properties: {}, relationships: [{ target, type, weight }] }` |
| Paths | `POST /api/v2/intelligence/entity-relationships` | `{ entity_ids[], max_depth }` | `{ paths[], direct_relationships[], indirect_paths[], summary }` |
| Centrality | `GET /api/v2/graph/centrality` | — | `{ entities: [{ entity_id, name, pagerank, degree }] }` |

**Entity Type Colors:**
| Type | Color |
|------|-------|
| KPI / Metric | `cyan-400` |
| Equipment | `emerald-400` |
| NPT Event | `red-400` |
| Formation | `amber-400` |
| Personnel | `violet-400` |
| Location | `blue-400` |

---

### 3.12 Demo Page (`/demo`)

**Purpose:** Pre-loaded demo dashboard showcasing all features with realistic drilling data.

**Behavior:**
- Loads a hardcoded demo `DashboardData` object
- Renders the same `<DashboardRenderer>` as the real dashboard
- Banner indicates "Demo Mode" with option to upload real data
- No API calls needed (all data is bundled)

---

### 3.13 User Profile (`/profile`)

**Purpose:** User profile info and upload history. Protected route (requires auth).

**Layout:**
```
┌────────────────────────────────────────────┐
│ "Your Profile"                             │
│                                            │
│ ┌────────────────────────────────────────┐ │
│ │ Avatar (large, initials)               │ │
│ │ Name: John Smith                       │ │
│ │ Email: john@company.com                │ │
│ │ Role: Engineer                         │ │
│ │ Member since: Jan 2025                 │ │
│ └────────────────────────────────────────┘ │
│                                            │
│ "Upload History"                           │
│ ┌────────────────────────────────────────┐ │
│ │ file1.pdf  2025-01-15  ● Complete     │ │
│ │ file2.docx 2025-01-12  ● Complete     │ │
│ │ file3.csv  2025-01-10  ● Failed       │ │
│ └────────────────────────────────────────┘ │
│                                            │
│ [Sign Out]                                 │
└────────────────────────────────────────────┘
```

**API Mapping:**
| Action | Endpoint | Response |
|--------|----------|----------|
| Get profile | `GET /auth/me` | `{ user_id, email, name, role, created_at }` |
| Logout | `POST /auth/logout` | `{ message: "Logged out" }` |

**Upload History:** Loaded from `localStorage` (key: `upload_history`). Each entry: `{ filename, date, status }`.

---

## 4. Reusable Component Library

### 4.1 KPICard

**Props:**
```ts
interface KPICardProps {
  label: string;
  value: number | string;
  unit?: string;
  change_pct?: number;
  trend?: 'up' | 'down' | 'flat';
  target?: number;
  priority_score?: number;
  sparkline?: number[];
  status?: 'good' | 'warning' | 'critical';
}
```

**Visual Spec:**
```
┌──────────────────────────────────┐
│ [Icon]  Label       [Priority]   │
│                                  │
│ 48.5 ft/hr          ▲ +12.3%    │
│                                  │
│ ▁▂▃▅▆▅▇  (sparkline)           │
│                                  │
│ Target: ████████░░  87%         │
│ ● Good                          │
└──────────────────────────────────┘

Card: bg-slate-800/60 border-slate-700/60 backdrop-blur-sm
      hover:shadow-lg hover:shadow-cyan-500/5 transition-all duration-300
Icon container: w-8 h-8 bg-gradient-to-br from-cyan-400/20 to-teal-400/10
                rounded-lg border border-cyan-500/20
Value: text-2xl font-bold text-white tabular-nums
Label: text-[11px] uppercase tracking-wider text-slate-400
Change (+): text-emerald-400 with TrendingUp icon
Change (-): text-red-400 with TrendingDown icon
Priority badge (>=80): bg-red-900/40 text-red-400 border-red-500/30
Priority badge (>=60): bg-amber-900/40 text-amber-400 border-amber-500/30
Priority badge (<60): bg-slate-700/60 text-slate-400 border-slate-600/30
Sparkline: Recharts <Sparklines> or tiny AreaChart (h-8)
Target bar: h-1.5 rounded-full bg-slate-700, fill color per status
```

### 4.2 ChartContainer

**Props:**
```ts
interface ChartContainerProps {
  title: string;
  size: 'full' | 'half' | 'third' | 'quarter';
  children: React.ReactNode;
  loading?: boolean;
  error?: string;
  onRefresh?: () => void;
}
```

**Visual Spec:**
```
┌──────────────────────────────────┐
│ Chart Title            [↻] [⋮]  │
│                                  │
│  [Recharts content or Skeleton]  │
│                                  │
└──────────────────────────────────┘

Card: bg-slate-800/60 border-slate-700 rounded-lg p-4
Title: text-sm font-medium text-slate-300
Sizes: full=w-full, half=w-1/2, third=w-1/3, quarter=w-1/4
Loading: <Skeleton className="h-48 bg-slate-700/50 animate-pulse rounded" />
Error: "Failed to load" text-red-400 + [Retry] button
```

### 4.3 StatusBadge

**Props:**
```ts
interface StatusBadgeProps {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'pass' | 'warn' | 'fail'
         | 'success' | 'warning' | 'error' | 'info';
  label?: string;
  dot?: boolean; // show colored dot prefix
}
```

**Mapping:**
```
healthy/pass/success → bg-emerald-500/20 text-emerald-400 border-emerald-500/30
degraded/warn/warning → bg-yellow-500/20 text-yellow-400 border-yellow-500/30
unhealthy/fail/error → bg-red-500/20 text-red-400 border-red-500/30
info → bg-blue-500/20 text-blue-400 border-blue-500/30

Base: text-xs font-medium px-2 py-0.5 rounded-full border
Dot: w-1.5 h-1.5 rounded-full inline-block mr-1
```

### 4.4 DataTable

**Props:**
```ts
interface DataTableProps<T> {
  columns: { key: keyof T; label: string; sortable?: boolean; render?: (val: T[keyof T], row: T) => ReactNode }[];
  data: T[];
  loading?: boolean;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
}
```

**Visual Spec:**
```
Header row: bg-slate-800/80 text-xs uppercase text-slate-400 tracking-wider
Data rows: border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors
Cell text: text-sm text-slate-300
Empty state: text-center py-8 text-slate-500 italic
Loading: 5 skeleton rows (animate-pulse bg-slate-700/50 h-10 rounded)
```

### 4.5 LoadingSpinner

```
Container: flex items-center justify-center p-8
Spinner: <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
Optional text: text-sm text-slate-400 mt-2
```

### 4.6 EmptyState

```
Container: flex flex-col items-center justify-center py-12
Icon: h-12 w-12 text-slate-600
Title: text-lg font-medium text-slate-400 mt-4
Description: text-sm text-slate-500 mt-1 max-w-sm text-center
CTA button: mt-4 bg-cyan-500/20 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/30
```

### 4.7 PageHeader

```ts
interface PageHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle: string;
}
```

```
Icon: h-5 w-5 text-cyan-400
Title: text-3xl font-bold text-white
Subtitle: text-slate-400 mt-1
Container: mb-6
```

### 4.8 TabBar

Use shadcn/ui `<Tabs>` with custom dark styling:
```
TabsList: bg-slate-800/60 border border-slate-700 rounded-lg p-1
TabsTrigger (inactive): text-slate-400
TabsTrigger (active): bg-cyan-500/20 text-cyan-400 rounded-md
TabsContent: mt-4
```

### 4.9 CardGrid

```ts
interface CardGridProps {
  cols?: { sm: number; md: number; lg: number };
  gap?: number;
  children: ReactNode;
}
```

```
Default: grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4
KPI: grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4
Health: grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3
```

### 4.10 ProcessingProgress

```ts
interface ProcessingProgressProps {
  progress: number; // 0-100
  stage: string;    // "Analyzing sections..."
  eta?: string;     // "~20s remaining"
}
```

```
Container: bg-slate-800/60 border border-slate-700 rounded-lg p-4
Progress bar track: h-2 bg-slate-700 rounded-full overflow-hidden
Progress bar fill: h-full bg-gradient-to-r from-cyan-500 to-teal-500 rounded-full transition-all duration-500
Stage text: text-sm text-slate-300
ETA text: text-xs text-slate-500
Percentage: text-sm font-bold text-cyan-400 tabular-nums
```

---

## 5. API → UI Mapping

### 5.1 Complete Endpoint Registry

All endpoints use base URL: `http://localhost:8001` (configurable via `VITE_API_URL` env var).

**Headers (all requests):**
```
Content-Type: application/json
X-API-Key: {api_key}
Authorization: Bearer {jwt_token}  (if authenticated)
```

| # | Endpoint | Method | Used By Page | UI Component |
|---|----------|--------|-------------|--------------|
| 1 | `/auth/login` | POST | Auth | Login form |
| 2 | `/auth/register` | POST | Auth | Signup form |
| 3 | `/auth/me` | GET | Profile | Profile card |
| 4 | `/auth/logout` | POST | Profile, Sidebar | Sign out button |
| 5 | `/api/v2/upload` | POST | Upload | Dropzone |
| 6 | `/api/v2/generate-batch` | POST | Upload | Generate button |
| 7 | `/api/v2/batch-status/{id}` | GET | Upload | Progress bar (poll 3s) |
| 8 | `/api/v2/dashboard/latest` | GET | Dashboard | DashboardRenderer |
| 9 | `/api/v2/dashboard/{id}` | GET | Dashboard | DashboardRenderer |
| 10 | `/api/v2/dashboard/export/pdf/{id}` | GET | Dashboard | Export button |
| 11 | `/api/v2/dashboard/export/excel/{id}` | GET | Dashboard | Export button |
| 12 | `/api/v2/search` | POST | Search | Search results list |
| 13 | `/api/v2/agent/query` | POST | Agent Lab | Chat message |
| 14 | `/api/v2/ws/agent` | WS | Agent Lab | Streaming response |
| 15 | `/api/v2/confusion-matrix` | POST | Confusion Matrix | Matrix upload |
| 16 | `/api/v2/confusion-matrix/{id}` | GET | Confusion Matrix | Matrix display |
| 17 | `/api/v2/observability/health` | GET | Observability, Top Bar | Health tab, status dot |
| 18 | `/api/v2/observability/models` | GET | Observability | Models tab |
| 19 | `/api/v2/observability/features` | GET | Observability | Features tab |
| 20 | `/api/v2/observability/predictions` | GET | Observability | Predictions tab |
| 21 | `/api/v2/observability/drift` | GET | Observability, Top Bar | Drift tab, alert badge |
| 22 | `/api/v2/impact/dmaic` | POST | Intelligence Hub | DMAIC tab |
| 23 | `/api/v2/impact/analyze-kpi-impact` | POST | Intelligence Hub | KPI Impact analysis |
| 24 | `/api/v2/impact/scenario` | POST | Intelligence Hub | Scenario tab |
| 25 | `/api/v2/intelligence/recommendations` | POST | Intelligence Hub | Recommendations tab |
| 26 | `/api/v2/intelligence/enrich-facts` | POST | Intelligence Hub | Fact enrichment |
| 27 | `/api/v2/intelligence/entity-relationships` | POST | Graph Explorer | Path finder |
| 28 | `/api/v2/intelligence/cross-engine` | POST | Graph Explorer, Intelligence | Cross-engine analysis |
| 29 | `/api/v2/graph/entities` | GET | Graph Explorer | Entity search |
| 30 | `/api/v2/graph/entities/{id}` | GET | Graph Explorer | Entity detail |
| 31 | `/api/v2/graph/centrality` | GET | Graph Explorer | Centrality chart |
| 32 | `/api/v2/fleet/summary` | GET | DDR Dashboard | Fleet sidebar, KPIs |
| 33 | `/api/v2/fleet/npt-pareto` | GET | DDR Dashboard | NPT Pareto chart |
| 34 | `/api/v2/fleet/spc/{metric}` | GET | DDR Dashboard | SPC control chart |
| 35 | `/api/v2/fleet/rig/{id}` | GET | DDR Dashboard | Rig detail panel |
| 36 | `/api/v2/fleet/rig/{id}/trends` | GET | DDR Dashboard | Rig trend charts |
| 37 | `/api/v2/fleet/rig/{id}/audit` | GET | DDR Dashboard | Audit trail table |

### 5.2 Polling Strategy

| What | Interval | Hook | Active When |
|------|----------|------|-------------|
| Batch status (upload) | 3s | `useBatchPolling(batchId)` | Upload page, status = "processing" |
| Drift alerts | 30s | `useDriftAlerts()` | Global (top bar badge) |
| Health status | 30s | `useQuery` refetchInterval | Observability health tab visible |
| Predictions | 30s | `useQuery` refetchInterval | Observability predictions tab visible |
| Models | 60s | `useQuery` refetchInterval | Observability models tab visible |
| Features | 60s | `useQuery` refetchInterval | Observability features tab visible |

### 5.3 Error Response Shape

All API errors follow:
```json
{
  "detail": "Error message string"
}
```
HTTP status codes: `401` (unauthorized), `403` (forbidden), `404` (not found), `422` (validation), `500` (server error).

---

## 6. Interaction Design

### 6.1 Loading States

| Context | Component | Behavior |
|---------|-----------|----------|
| Initial page load | `<LoadingSpinner />` | Centered spinner with "Loading..." text |
| Data fetching within card | `<Skeleton />` | Pulsing rectangles matching expected content shape |
| Button action pending | Button with `<Loader2 className="animate-spin" />` | Disable button, replace text with spinner |
| Dashboard generation | `<ProcessingProgress />` | Progress bar + stage text + ETA |
| Chart loading | Skeleton inside ChartContainer | Pulsing rectangle at chart height |

### 6.2 Error States

| Context | Behavior |
|---------|----------|
| API error (toast) | `toast.error("Failed to load: " + detail)` via Sonner, dark theme |
| Component crash | `<ErrorBoundary>` shows card with "Something went wrong" + [Retry] button |
| Network offline | Banner at top: "No connection" with auto-retry countdown |
| 401 Unauthorized | Clear auth state → redirect to `/auth` |
| 404 Not Found | Show `<EmptyState icon={Search} title="Not Found" />` |
| Empty data | Show `<EmptyState>` with contextual CTA ("Upload your first report") |

### 6.3 Form Interactions

| Pattern | Implementation |
|---------|---------------|
| Validation | `react-hook-form` + `zod` schema, errors shown below fields |
| Error text | `text-xs text-red-400 mt-1` |
| Input focus | `focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500` |
| Disabled | `opacity-50 cursor-not-allowed` |
| Submit | Button shows spinner, fields disabled during submission |

### 6.4 Navigation Transitions

| Action | Behavior |
|--------|----------|
| Page navigation | React Router `<Link>`, instant transition (SPA) |
| Tab switch | Content swap with subtle fadeIn (no page reload) |
| Modal open | Overlay with `backdrop-blur-md`, content slide-up |
| Sidebar collapse | Width transition 240px → 64px, labels fade out |

### 6.5 Real-time Updates

| Feature | Method | Visual Cue |
|---------|--------|------------|
| Upload progress | Polling (3s) | Progress bar animation, stage text updates |
| Drift alerts | Polling (30s) | Red badge count on bell icon pulses on change |
| Agent chat | WebSocket | Typing indicator (3 dots), text streams in character-by-character |
| Dashboard data | React Query staleTime | Background refetch, subtle refresh icon spin |

### 6.6 Responsive Breakpoints

| Breakpoint | Sidebar | Grid Cols | Typography |
|------------|---------|-----------|------------|
| < 640px (sm) | Hidden (sheet) | 1 col | text-2xl titles |
| 640-768px (md) | Collapsed (64px) | 2 cols | text-3xl titles |
| 768-1024px (lg) | Expanded (240px) | 3 cols | text-3xl titles |
| > 1280px (xl) | Expanded (240px) | 4 cols | text-4xl titles |

---

## 7. State Management

### 7.1 Context Providers

```
QueryClientProvider (React Query)
  └─ AuthProvider
      ├─ user: User | null
      ├─ isAuthenticated: boolean
      ├─ token: string | null
      ├─ login(user, token): void
      └─ logout(): Promise<void>
      └─ DashboardProvider
          ├─ dashboardData: DashboardData | null
          ├─ setDashboardData(data): void
          ├─ isLoading: boolean
          └─ resetDashboard(): void
          └─ DDRDataProvider
              ├─ mode: 'analytics' | 'drilling'
              ├─ setMode(mode): void
              ├─ selectedRig: string | null
              ├─ setSelectedRig(id): void
              └─ fleetData: FleetSummary | null
```

### 7.2 React Query Configuration

```ts
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30s before refetch
      retry: 2,                // 2 retries on failure
      refetchOnWindowFocus: false,
    }
  }
});
```

### 7.3 localStorage Keys

| Key | Value Type | Purpose |
|-----|-----------|---------|
| `auth_token` | string (JWT) | Authentication token |
| `user_data` | JSON `{ user_id, email, name }` | Cached user info |
| `dashboard_data` | JSON `DashboardData` | Persisted dashboard across sessions |
| `upload_history` | JSON `UploadEntry[]` | File upload log |

---

## 8. Technology Stack

### 8.1 Dependencies

| Category | Library | Version | Purpose |
|----------|---------|---------|---------|
| Framework | React | 18.3.x | UI framework |
| Build | Vite | 5.x | Dev server + bundler |
| Language | TypeScript | 5.x | Type safety |
| Routing | react-router-dom | 6.x | Client-side routing |
| UI Components | shadcn/ui | latest | 50+ Radix-based primitives (Card, Badge, Button, Tabs, Dialog, Sheet, Accordion, ScrollArea, Tooltip, etc.) |
| Styling | Tailwind CSS | 3.x | Utility-first CSS |
| Charts (primary) | Recharts | 2.x | Line, Bar, Area, Pie, Radar, Scatter, Sankey, Funnel, Radial |
| Charts (secondary) | Tremor | 3.x | Pre-built dashboard widgets |
| Graph viz | vis-network | 9.x | Network/graph visualization (Knowledge Graph) |
| Data fetching | @tanstack/react-query | 5.56.x | Server state, caching, polling |
| Forms | react-hook-form | 7.53.x | Form state management |
| Validation | zod | 3.23.x | Schema validation |
| HTTP | axios | 1.x | API client with interceptors |
| Icons | lucide-react | latest | Icon library |
| Toasts | sonner | latest | Toast notifications (dark theme) |
| Testing | vitest + @testing-library/react | 4.1.x | Unit + component tests |

### 8.2 Axios Configuration

```ts
// src/services/axios.ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8001',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': import.meta.env.VITE_API_KEY || 'default-dev-key'
  }
});

// Request interceptor: attach JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_data');
      window.location.href = '/auth';
    }
    return Promise.reject(error);
  }
);
```

### 8.3 Environment Variables

```env
VITE_API_URL=http://localhost:8001
VITE_API_KEY=your-api-key
VITE_APP_NAME=TransIQ
```

---

## Appendix A: File Structure (Target)

```
src/
├── api/
│   ├── axios.ts              # Axios instance + interceptors
│   ├── dashboardApi.ts       # Dashboard endpoints
│   ├── ddrClient.ts          # Fleet/DDR endpoints
│   ├── observabilityClient.ts # Observability endpoints
│   ├── graphClient.ts        # Knowledge graph endpoints
│   └── intelligenceClient.ts # Impact/intelligence endpoints
├── components/
│   ├── ui/                   # shadcn/ui primitives (50+)
│   ├── layout/
│   │   ├── AppShell.tsx      # Sidebar + TopBar + content area
│   │   ├── Sidebar.tsx       # Collapsible nav sidebar
│   │   └── TopBar.tsx        # Header with alerts + avatar
│   ├── KPICard.tsx
│   ├── ChartRenderer.tsx     # Universal Recharts wrapper
│   ├── ChartContainer.tsx    # Card wrapper for charts
│   ├── DashboardRenderer.tsx # Dynamic dashboard from JSON
│   ├── DataTable.tsx
│   ├── StatusBadge.tsx
│   ├── LoadingSpinner.tsx
│   ├── EmptyState.tsx
│   ├── ProcessingProgress.tsx
│   ├── PageHeader.tsx
│   ├── ErrorBoundary.tsx
│   ├── ProtectedRoute.tsx
│   ├── charts/               # Specialized chart components
│   ├── ddr/                  # DDR-specific components
│   ├── intelligence/         # Intelligence tab components
│   ├── confusion/            # Confusion matrix components
│   └── insights/             # Insight rendering components
├── contexts/
│   ├── AuthContext.tsx
│   ├── DashboardContext.tsx
│   └── DDRContext.tsx
├── hooks/
│   ├── usePolling.ts         # useBatchPolling, useDriftAlerts
│   └── useLocalStorage.ts
├── pages/
│   ├── Index.tsx
│   ├── Auth.tsx
│   ├── Upload.tsx
│   ├── Dashboard.tsx
│   ├── Search.tsx
│   ├── AgentLab.tsx
│   ├── ConfusionMatrix.tsx
│   ├── Observability.tsx
│   ├── IntelligenceHub.tsx
│   ├── GraphExplorer.tsx
│   ├── DemoPage.tsx
│   ├── UserProfile.tsx
│   └── NotFound.tsx
├── App.tsx
├── main.tsx
└── index.css                 # Tailwind directives + CSS variables
```

---

## Appendix B: CSS Custom Properties

```css
@layer base {
  :root {
    /* Light mode (secondary) */
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
    --sidebar-background: 0 0% 98%;
    --sidebar-foreground: 240 5.3% 26.1%;
    --sidebar-primary: 240 5.9% 10%;
    --sidebar-primary-foreground: 0 0% 98%;
    --sidebar-accent: 240 4.8% 95.9%;
    --sidebar-accent-foreground: 240 5.9% 10%;
    --sidebar-border: 220 13% 91%;
    --sidebar-ring: 217.2 91.2% 59.8%;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
    --sidebar-background: 240 5.9% 10%;
    --sidebar-foreground: 240 4.8% 95.9%;
    --sidebar-primary: 224.3 76.3% 48%;
    --sidebar-primary-foreground: 0 0% 100%;
    --sidebar-accent: 240 3.7% 15.9%;
    --sidebar-accent-foreground: 240 4.8% 95.9%;
    --sidebar-border: 240 3.7% 15.9%;
    --sidebar-ring: 217.2 91.2% 59.8%;
  }
}
```

---

## Appendix C: Lovable Prompt Template

When pasting into Lovable, use this structure:

```
Build a React + TypeScript + Vite dashboard app called "TransIQ" with the following requirements:

TECH STACK:
- React 18 + TypeScript + Vite
- shadcn/ui components (50+ Radix primitives)
- Tailwind CSS (dark mode primary)
- Recharts for all charts
- @tanstack/react-query for data fetching
- react-hook-form + zod for forms
- react-router-dom v6 for routing
- axios for HTTP
- lucide-react for icons
- sonner for toasts

DESIGN:
- Dark theme: slate-900/800 backgrounds, cyan-400/teal-400 accent gradient
- Status colors: emerald (success), yellow (warning), red (danger)
- Cards: bg-slate-800/60 border-slate-700 rounded-lg backdrop-blur
- All text: white/slate-300/slate-400 hierarchy

PAGES: [list from §3]
COMPONENTS: [list from §4]
API ENDPOINTS: [list from §5]

[Paste relevant sections from this spec for the specific page/feature being built]
```

---

*Generated for TransIQ AI Drilling Analytics Platform. This specification reflects the current implemented state plus production-ready enhancements (persistent sidebar, route protection).*
