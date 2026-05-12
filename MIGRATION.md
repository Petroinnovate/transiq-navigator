# Backend Migration: FastAPI → Lovable Cloud → Google Cloud

This project originally ran a Python **FastAPI** service on `localhost:8001`.
That host is unreachable from the Lovable preview / production environment, so
the backend is being incrementally ported to **Lovable Cloud** (Supabase +
edge functions). When you're ready, you can lift-and-shift the same edge
functions (or rewrite as Cloud Run services) onto **Google Cloud**.

---

## Current status (May 2026)

### ✅ Ported to Lovable Cloud — works in preview & production

| Feature | Implementation | Files |
|---|---|---|
| Auth (signup, login, password reset, Google) | Supabase Auth | `src/contexts/AuthContext.tsx`, `src/pages/Auth.tsx` |
| File upload to storage | Supabase Storage `raw` bucket | `src/services/api.ts` → `uploadOne()` |
| Document text extraction (PDF, image, text) | Edge function using **Gemini 2.0 Flash** | `supabase/functions/process-document/index.ts` |
| Chunking + OpenAI embeddings (`text-embedding-3-small`) | Same edge function | `supabase/functions/process-document/index.ts` |
| Dashboard generation (KPIs, charts, insights) | Edge function calling **Gemini 2.0 Flash** with structured-output schema | `supabase/functions/generate-dashboard/index.ts` |
| Hybrid (BM25 + semantic) search | Edge function | `supabase/functions/search-hybrid/index.ts` |
| Document history / list | Direct Supabase query | `src/services/api.ts` → `listDocuments()` |
| Live document status | Supabase Realtime | `src/services/api.ts` → `streamDocumentStatus()` |
| Multi-tenant RLS isolation | Postgres RLS + `current_tenant_id()` | DB schema |

The frontend consumes these via **`@/services/api`** (the single source of truth).

### ⏳ Not yet ported — pending Google Cloud migration

These modules still call the (currently unreachable) FastAPI service through
`@/lib/axios`. With no `VITE_API_URL` configured the axios interceptor returns
a clear error (`LEGACY_BACKEND_UNAVAILABLE`) so consuming pages display a
friendly message instead of "Network Error".

| Module | Endpoint count | Frontend client | Pages affected |
|---|---|---|---|
| DDR fleet/rig analytics | ~30 | `src/api/ddrClient.ts` | `/dashboard` (fleet view), `/ddr-metric-edit` |
| Entity intelligence / impact | ~10 | `src/api/intelligenceClient.ts` | `/intelligence`, `/intelligence-insights` |
| Six Sigma SPC | ~6 | `src/api/sixSigmaClient.ts` | `/six-sigma` |
| GraphRAG | ~8 | `src/api/graphClient.ts` | `/graph-explorer` |
| Observability / MLOps | ~12 | `src/api/observabilityClient.ts` | `/observability` |
| Legacy dashboard endpoints | 6 | `src/api/dashboardApi.ts` | (superseded by `services/api`) |

Why these aren't in edge functions yet:
- **DDR** has its own data model (rigs, NPT events, mud, BHA, surveys) and
  performs statistical analysis (SPC, Pareto). Estimated 8–12 hours.
- **Intelligence / Graph** depend on entity extraction + a graph store.
  Estimated 4–6 hours each.
- **Six Sigma** is small but needs port of `numpy`/`scipy` math to JS.
- **Observability** mostly returns mock data in FastAPI; can be replaced by
  Supabase logs + edge function metrics.

---

## How to bring the unported modules online (3 options)

### Option A — Deploy FastAPI to Google Cloud (fastest)
Containerize the existing FastAPI app and deploy to Google Cloud Run:

```bash
# In the FastAPI repo:
gcloud run deploy ddr-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=...,SUPABASE_URL=...,SUPABASE_SERVICE_ROLE_KEY=...
```

Then in **Lovable → Project Settings → Environment** set:
```
VITE_API_URL=https://ddr-api-xxxxxxxx-uc.a.run.app
```

Also add the lovable.app preview origin to your FastAPI CORS allowlist:
```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.lovable.app", "https://*.lovableproject.com", "http://localhost:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
```

The unported modules light up automatically — no frontend code changes needed.

### Option B — Port modules to Lovable Cloud edge functions (long-term)
Repeat the pattern used for `process-document` / `generate-dashboard`:
1. Create `supabase/functions/<name>/index.ts`
2. Use shared helpers from `supabase/functions/_shared/utils.ts` (auth, CORS, JSON)
3. Replace the corresponding `src/api/*Client.ts` to call `supabase.functions.invoke(<name>, …)` instead of `axios.get(…)`

Suggested order (lightest first):
1. Six Sigma (pure math, single endpoint)
2. Observability (mostly metadata)
3. Intelligence (entity extraction with Gemini)
4. Graph (depends on intelligence)
5. DDR (largest — split into sub-functions per resource)

### Option C — Migrate to Google Cloud entirely (portable)
The Lovable Cloud edge functions are vanilla Deno + standard Web APIs (`fetch`,
`Response`, `Deno.serve`). To move them to Google Cloud:
- Edge functions → **Cloud Run** (Deno or Node container)
- Supabase Postgres → **Cloud SQL for Postgres** (`pgvector` extension supported)
- Supabase Storage → **Cloud Storage** bucket
- Supabase Auth → **Identity Platform** or keep Supabase Auth
- Realtime → **Pub/Sub + WebSockets** or keep Supabase Realtime

Roughly 1–2 days of integration work per service when the time comes.

---

## Frontend architecture cheat sheet

```
src/
├── services/api.ts          ← Lovable Cloud API (works ✅) — use this for new features
├── lib/axios.ts             ← Legacy FastAPI client (gated; throws if no VITE_API_URL)
├── api/
│   ├── ddrClient.ts         ← Pending migration
│   ├── intelligenceClient.ts ← Pending migration
│   ├── sixSigmaClient.ts    ← Pending migration
│   ├── graphClient.ts       ← Pending migration
│   ├── observabilityClient.ts ← Pending migration
│   └── dashboardApi.ts      ← Legacy; superseded by services/api.ts
├── hooks/useHealthCheck.ts  ← Pings Supabase + FastAPI separately
└── components/BackendStatusBanner.tsx  ← Shows which backends are online
```

## Environment variables

| Var | Purpose | Where set |
|---|---|---|
| `VITE_SUPABASE_URL` | Lovable Cloud URL | Auto-injected (`.env`, do not edit) |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Lovable Cloud anon key | Auto-injected |
| `VITE_API_URL` | Legacy FastAPI base URL | **You set this** in Lovable → Settings → Environment when the FastAPI service is deployed. Leave unset (or pointing at localhost) and the unported modules will return friendly errors. |
| `GEMINI_API_KEY`, `OPENAI_API_KEY` | Used by edge functions | Lovable Cloud secrets (already configured ✅) |
