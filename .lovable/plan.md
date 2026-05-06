# TransIQ / IntelliDrill — Backend Rebuild Architecture

Production-grade plan to replace the legacy FastAPI backend with a cloud-native TypeScript stack on **Lovable Cloud (Supabase) + TanStack Start server functions + Lovable AI Gateway**. No code yet — architecture only.

---

## 1. System Architecture

**Runtime topology**

```text
 ┌─────────────────────────────────────────────────────────────┐
 │  Browser (React 18 + TanStack Router + shadcn + Tremor)     │
 │  - Supabase JS (auth + realtime + storage signed URLs)      │
 │  - useServerFn() RPCs                                       │
 └───────────────┬─────────────────────────────┬───────────────┘
                 │ HTTPS (RPC)                 │ WSS (Realtime/Stream)
 ┌───────────────▼─────────────────┐ ┌─────────▼────────────────┐
 │ TanStack Start Worker (Edge)    │ │ Supabase Realtime Channels│
 │ - createServerFn (RPC)          │ │ - telemetry.{rig_id}      │
 │ - /api/public/* (webhooks,cron) │ │ - jobs.{tenant_id}        │
 │ - SSE streaming routes          │ │ - dashboards.{doc_id}     │
 └───┬──────────────┬──────────┬───┘ └──────────────┬───────────┘
     │              │          │                    │
     ▼              ▼          ▼                    ▼
 ┌────────┐  ┌────────────┐ ┌──────────────┐ ┌──────────────┐
 │Postgres│  │ Storage    │ │ AI Gateway   │ │ pg_cron      │
 │+pgvector│ │ (buckets)  │ │ Gemini/GPT/  │ │ (jobs, SPC,  │
 │+FTS+RLS│  │ raw/derived│ │ Claude       │ │ retention)   │
 └────────┘  └────────────┘ └──────────────┘ └──────────────┘
```

**Boundaries**
- **Server functions** → all app logic (DDR CRUD, KPIs, search, Six Sigma, AI orchestration). User-scoped via `requireSupabaseAuth`.
- **Server routes `/api/public/*`** → webhooks, cron triggers, external ingest, signed-URL callbacks. HMAC-verified.
- **Realtime** → live telemetry, job progress, dashboard staged updates (Supabase channels, not custom WS).
- **SSE** → multi-stage AI dashboard generation (single long-lived Response).
- **Edge constraints** → no `child_process`, no `sharp`, no native binaries. PDF/OCR work goes through AI Gateway (Gemini multimodal) or async worker (Phase 3).

---

## 2. Database Design

All tables: `tenant_id uuid not null`, `created_at`, `updated_at`, RLS enabled, `(tenant_id, …)` composite indexes.

**Identity & tenancy**
| Table | Key columns | Notes |
|---|---|---|
| `tenants` | id, name, slug, plan, settings jsonb | Org root |
| `organizations` | id, tenant_id, name | Optional sub-org |
| `profiles` | id=auth.users.id, tenant_id, display_name, avatar_url | 1:1 with auth |
| `user_roles` | id, user_id, tenant_id, role app_role | Enum: `super_admin, tenant_admin, ops_manager, drilling_engineer, analyst, viewer, api_service` |
| `permissions` | role app_role, resource text, action text | Static seed |
| `audit_logs` | id, tenant_id, actor_id, action, resource, resource_id, diff jsonb, ip, ua, ts | Append-only, partitioned monthly |

**Drilling domain**
| Table | Key columns |
|---|---|
| `fleets` | id, tenant_id, name, region |
| `rigs` | id, tenant_id, fleet_id, rig_no, contractor, status, metadata jsonb |
| `wells` | id, tenant_id, rig_id, well_name, field, spud_date, td_date, status |
| `ddr_reports` | id, tenant_id, rig_id, well_id, report_date, source_file_id, status, raw jsonb |
| `ddr_sections` | id, ddr_report_id, section_type, content jsonb, citation jsonb |
| `drilling_parameters` | id, ddr_report_id, depth_md, wob, rpm, torque, flow, spp, rop |
| `realtime_telemetry` | id, rig_id, ts timestamptz, channel, value double precision | **Hypertable-style partition by day**, BRIN index on ts |
| `npt_events` | id, ddr_report_id, rig_id, start_ts, end_ts, duration_hr, category, sub_category, root_cause, cost_usd |
| `kpi_metrics` | id, tenant_id, rig_id, well_id, metric_key, value, unit, period_start, period_end |
| `six_sigma_results` | id, tenant_id, metric_key, scope jsonb, cp, cpk, dpmo, sigma_level, ucl, lcl, chart_data jsonb, computed_at |

**AI / search / graph**
| Table | Key columns |
|---|---|
| `uploaded_files` | id, tenant_id, owner_id, bucket, path, mime, size, sha256, status |
| `processing_status` | id, tenant_id, file_id, stage, progress, message, error |
| `ai_extractions` | id, tenant_id, file_id, model, prompt_hash, output jsonb, tokens_in, tokens_out, cost_usd, confidence, reviewed_by |
| `embeddings` | id, tenant_id, source_type, source_id, chunk_idx, content text, embedding vector(1536), metadata jsonb | **HNSW** index, FTS `tsvector` generated col |
| `knowledge_nodes` | id, tenant_id, node_type, label, props jsonb, embedding vector(768) |
| `knowledge_edges` | id, tenant_id, src uuid, dst uuid, edge_type, weight, props jsonb | btree(src), btree(dst), partial(edge_type) |

**Ops**
| Table | Key columns |
|---|---|
| `job_queue` | id, tenant_id, type, payload jsonb, priority, status, attempts, max_attempts, run_after, locked_by, locked_at, result jsonb |
| `notifications` | id, tenant_id, user_id, kind, title, body, link, read_at |

**Indexing rules**
- Every FK + `(tenant_id, hot_filter_col)` composite.
- Vector: HNSW `(m=16, ef_construction=64)` per tenant filter via partial index when tenant cardinality is low.
- Time-series: BRIN on `ts`; monthly partitions for `realtime_telemetry`, `audit_logs`.

---

## 3. Authentication & Security

- **Auth**: Supabase Email/Password + Google OAuth (defaults). Optional SAML for enterprise tenants.
- **Roles** in `user_roles` (NEVER on profiles). `has_role(_user, _role)` SECURITY DEFINER for RLS.
- **Tenant isolation**: `current_tenant_id()` SECURITY DEFINER reads JWT `app_metadata.tenant_id`. Every RLS policy: `tenant_id = current_tenant_id() AND has_role(auth.uid(), …)`.
- **Service operations** via `supabaseAdmin` only inside verified server routes (HMAC) or trusted server fns.
- **Uploads**: client → signed upload URL → bucket `raw/{tenant}/{yyyy}/{mm}/{uuid}`. Antivirus & sha256 dedupe in post-upload trigger (`/api/public/file-finalized`).
- **Secrets**: `LOVABLE_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, webhook HMACs — server only.
- **Audit**: trigger-based row diffs into `audit_logs` for all DDR/KPI/role-change tables.
- **Rate limiting**: per-user token bucket in `job_queue` for AI endpoints; per-IP for `/api/public/*`.

---

## 4. API Architecture (`/api/v2/*` mapped to server fns; `/api/public/*` for raw HTTP)

| Group | Surface | Auth |
|---|---|---|
| Auth | handled by Supabase JS (signUp/signIn/OAuth/reset) | — |
| Tenancy | `getMyTenant`, `inviteUser`, `setUserRole` | tenant_admin |
| Fleet | `listFleets`, `listRigs`, `getRigDetail`, `getRigKPIs` | viewer+ |
| DDR | `listDDR`, `getDDR`, `uploadDDR`, `parseDDRJob`, `updateDDRMetric`, `getAuditTrail` | engineer+ |
| Telemetry | `getTelemetryRange`, realtime channel `telemetry.{rig_id}` | viewer+ |
| KPIs | `getFleetSummary`, `getNPTPareto`, `getTopPerformers`, `getHeatmap`, `getTrends` | viewer+ |
| Six Sigma | `analyzeSixSigma`, `getSPC`, `listSixSigmaResults` | analyst+ |
| Search | `hybridSearch`, `semanticSearch`, `keywordSearch` | viewer+ |
| Graph | `getNodeNeighbors`, `traverse`, `findPaths`, `topEntities` | analyst+ |
| AI | `generateDashboard` (SSE), `runAgent`, `extractDocument` | engineer+ |
| Admin | `listJobs`, `retryJob`, `cancelJob`, `getMetrics` | tenant_admin |
| Public | `/api/public/webhooks/{provider}`, `/api/public/cron/{task}`, `/api/public/file-finalized` | HMAC |

Each endpoint specifies: input Zod schema, output type, RLS scope, p95 latency target, cache TTL.

---

## 5. AI Pipeline

```text
upload → uploaded_files → job_queue(type=extract)
  → stage:ocr (Gemini multimodal on PDF pages or text passthrough)
  → stage:chunk (semantic-aware, drilling-section heuristics, 800–1500 tok)
  → stage:embed (Gemini text-embedding-004, batched)
  → stage:extract (Gemini 2.5 Pro structured output → ddr_sections, npt_events, kpis)
  → stage:classify (event taxonomy, confidence)
  → stage:enrich (entity linking → knowledge_nodes/edges)
  → stage:dashboard (SSE: kpis → charts → insights → six_sigma → complete)
  → status=ready
```

- **Retry**: exponential backoff in `job_queue` (max 5).
- **Confidence < 0.75** → `needs_review`, surfaced in admin queue.
- **Idempotency** via `prompt_hash` on `ai_extractions`.
- **Cost capture** per row (tokens × price table).

---

## 6. Hybrid Search

- Single `embeddings` table with `embedding vector(1536)` + generated `tsv tsvector`.
- Query: parallel `ORDER BY embedding <=> $q LIMIT 50` and `ts_rank_cd(tsv, plainto_tsquery)` → **RRF fusion** (k=60).
- Metadata pre-filter on `(tenant_id, source_type, rig_id, date_range)`.
- Drilling boost: weight by `metadata->>'section_type' IN ('npt','operations','remarks')`.
- Cache by `(tenant, query_hash, filters_hash)` in `kv_cache` table (TTL 10 min).

---

## 7. Knowledge Graph

- Node types: `Rig, Well, Crew, Equipment, NPTCategory, Hazard, Vendor, Formation, Operation, Document`.
- Edge types: `OCCURRED_ON, CAUSED_BY, OPERATED_BY, USES_EQUIPMENT, MENTIONS, CORRELATES_WITH, PRECEDES`.
- Recursive CTE traversal capped at depth 4.
- Anomaly linkage: nightly job links Six Sigma out-of-control points to NPT events sharing rig+window.
- Optional Phase 3: Apache AGE upgrade if multi-hop perf < target.

---

## 8. Six Sigma Engine

- Pure TS module (no Python). Functions: `mean, stdev, cp, cpk, cpu, cpl, dpmo, sigmaLevel, IMR control limits, Nelson rules`.
- Inputs: time-window slice from `kpi_metrics` or `drilling_parameters`.
- Outputs persisted to `six_sigma_results` (chart_data jsonb for fast reload).
- Realtime SPC: subscription on telemetry triggers incremental window recompute (Welford).

---

## 9. Realtime & Streaming

- **Supabase Realtime** channels (RLS-aware):
  - `telemetry:{tenant}:{rig}` — INSERT broadcasts on `realtime_telemetry`.
  - `jobs:{tenant}:{user}` — `processing_status` updates.
  - `notifications:{user}`.
- **SSE** for dashboard generation (one Response per doc, stages: context_ready→kpis→charts→insights→sixSigma→complete).
- Backpressure: throttle telemetry to 5 Hz server-side, downsample on client.

---

## 10. Async Job System

- `job_queue` with `FOR UPDATE SKIP LOCKED` worker pattern.
- **pg_cron** every 30s invokes `/api/public/cron/drain-jobs` (HMAC) → server fn pulls N jobs, runs in worker, updates status.
- Long AI jobs split into stages so each stage fits well within edge timeout.
- Cancellation flag on row honored between stages.
- Dead-letter after `max_attempts`.

---

## 11. Observability

- Structured server logs (level, tenant_id, user_id, route, latency_ms, error_code).
- `audit_logs` for security & data lineage.
- `api_metrics` rollup table (hourly): count, p50/p95/p99 latency, error rate per endpoint.
- AI cost dashboard from `ai_extractions`.
- Public health route `/api/public/health` (no secrets).

---

## 12. Production Deployment

- Environments: **preview** (auto on every change) + **published** (manual promote).
- Stable URLs: `project--{id}-dev.lovable.app`, `project--{id}.lovable.app` (cron + webhooks point here).
- Backups: Supabase PITR enabled; nightly logical export of `ddr_*`, `kpi_*`, `audit_logs` to storage bucket `backups/`.
- Disaster recovery: documented restore runbook; RPO 24h / RTO 4h MVP, tighten in Phase 3.
- Scaling: bump Cloud instance size when telemetry write rate > threshold; partition pruning keeps queries flat.

---

## 13. Migration from FastAPI

| Phase | Action |
|---|---|
| M0 | Freeze FastAPI schema; export reference fixtures |
| M1 | Stand up new schema + RLS; dual-write shim (FastAPI → `/api/public/ingest/legacy`) |
| M2 | Port read endpoints (fleet, rigs, KPIs, search) — frontend toggled per-route via `VITE_USE_NEW_API` |
| M3 | Port write/AI endpoints (DDR upload, extraction, dashboard SSE) |
| M4 | Backfill historical DDR + telemetry via batch jobs into `job_queue` |
| M5 | Cut over; FastAPI read-only for 2 weeks; then decommission |
| Rollback | Feature flag flip to legacy base URL; data dual-written during M1–M4 |

---

## 14. Cost Optimization

- Prompt caching + `prompt_hash` dedupe on `ai_extractions`.
- Tiered model routing: Gemini Flash for chunk/classify, Pro for extraction, Claude only for complex reasoning.
- Embedding batch size 64; only re-embed on content hash change.
- pgvector HNSW (not IVFFlat) for read-heavy; `lists` tuned per tenant size.
- Storage lifecycle: raw uploads → cold bucket after 90 days; derived artifacts retained.
- Realtime: server-side throttle + client downsampling.
- Cache hot KPI rollups in `kpi_rollups_daily` materialized view, refreshed by cron.

---

## 15. Build Phases / Roadmap

**Phase 1 — Foundation (MVP, ~Sprint 1–2)**
- Enable Lovable Cloud, auth (email + Google), tenants, roles, RLS, audit.
- Schema: tenants, profiles, user_roles, fleets, rigs, wells, uploaded_files, job_queue, audit_logs.
- File upload + signed URLs + finalize webhook.
- Frontend: Auth, Dashboard shell, Fleet/Rig list backed by new API.

**Phase 2 — DDR + AI (SPE/OTC demo target)**
- DDR ingest pipeline (upload → extract → sections → KPIs).
- AI Gateway extraction (Gemini Pro structured), confidence + review queue.
- KPI summaries, NPT Pareto, top performers, heatmap.
- SSE dashboard generation.
- Hybrid search MVP (FTS + embeddings, RRF).

**Phase 3 — Intelligence & Realtime (Enterprise)**
- Telemetry ingestion + Realtime channels + SPC live.
- Six Sigma engine + persisted results + control charts.
- Knowledge graph + traversal API + Intelligence Hub wiring.
- Agent runner, what-if simulator.
- Admin: jobs, metrics, cost dashboard, multi-tenant onboarding.

**Phase 4 — Production hardening**
- Partitioning, backups, DR drills, SAML, rate limits, abuse protection, SOC2-track logging, cost guardrails.

---

## Risks & Mitigations
- **Edge timeout on long AI** → split into staged jobs + SSE.
- **No Python ML libs** → math in TS; offload heavy ML to Phase 3 external worker behind `/api/public/ml`.
- **Vector cost at scale** → per-tenant partial HNSW + content-hash dedupe.
- **PDF parsing fidelity** → Gemini multimodal first, fallback to AI Gateway file-API; manual review queue for low confidence.
- **Tenant data leak** → RLS-by-default + integration tests asserting cross-tenant 0-row reads.

---

Approve this and I'll start **Phase 1 Step 1**: enable Lovable Cloud, create the tenant/role/RLS foundation, and wire auth + file upload end-to-end.