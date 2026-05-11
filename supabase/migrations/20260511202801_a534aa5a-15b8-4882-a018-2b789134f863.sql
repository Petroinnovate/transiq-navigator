-- Enable pgvector for embeddings
create extension if not exists vector;

-- =========================================================
-- DOCUMENTS
-- =========================================================
create table public.documents (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  owner_id uuid not null,
  file_id uuid references public.uploaded_files(id) on delete set null,
  file_name text not null,
  mime text,
  provider text,
  status text not null default 'queued',
  processing_time_ms integer,
  has_dashboard boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.documents(tenant_id);
create index on public.documents(status);
alter table public.documents enable row level security;
create policy "tenant read documents" on public.documents for select to authenticated using (tenant_id = current_tenant_id());
create policy "owner inserts documents" on public.documents for insert to authenticated with check (tenant_id = current_tenant_id() and owner_id = auth.uid());
create policy "owner or admin updates documents" on public.documents for update to authenticated using (tenant_id = current_tenant_id() and (owner_id = auth.uid() or has_tenant_role('tenant_admin')));
create policy "owner or admin deletes documents" on public.documents for delete to authenticated using (tenant_id = current_tenant_id() and (owner_id = auth.uid() or has_tenant_role('tenant_admin')));
create trigger documents_touch before update on public.documents for each row execute function public.touch_updated_at();

-- =========================================================
-- DOCUMENT CHUNKS (with pgvector embedding)
-- =========================================================
create table public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  document_id uuid not null references public.documents(id) on delete cascade,
  chunk_index integer not null,
  text text not null,
  embedding vector(1536),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (document_id, chunk_index)
);
create index on public.document_chunks(tenant_id);
create index on public.document_chunks(document_id);
create index document_chunks_embedding_idx on public.document_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);
alter table public.document_chunks enable row level security;
create policy "tenant read chunks" on public.document_chunks for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write chunks" on public.document_chunks for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('ops_manager') or has_tenant_role('drilling_engineer') or has_tenant_role('analyst') or has_tenant_role('api_service'))) with check (tenant_id = current_tenant_id());

-- =========================================================
-- DOCUMENT EDGES (knowledge graph)
-- =========================================================
create table public.document_edges (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  document_id uuid references public.documents(id) on delete cascade,
  source_id uuid not null,
  target_id uuid not null,
  edge_type text not null,
  weight numeric,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index on public.document_edges(tenant_id);
create index on public.document_edges(document_id);
create index on public.document_edges(source_id);
create index on public.document_edges(target_id);
alter table public.document_edges enable row level security;
create policy "tenant read edges" on public.document_edges for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write edges" on public.document_edges for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('analyst') or has_tenant_role('api_service'))) with check (tenant_id = current_tenant_id());

-- =========================================================
-- DASHBOARDS
-- =========================================================
create table public.dashboards (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  document_id uuid not null references public.documents(id) on delete cascade,
  kpis jsonb not null default '[]'::jsonb,
  charts jsonb not null default '[]'::jsonb,
  insights jsonb not null default '[]'::jsonb,
  six_sigma jsonb,
  status text not null default 'ready',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (document_id)
);
create index on public.dashboards(tenant_id);
alter table public.dashboards enable row level security;
create policy "tenant read dashboards" on public.dashboards for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write dashboards" on public.dashboards for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('ops_manager') or has_tenant_role('drilling_engineer') or has_tenant_role('analyst') or has_tenant_role('api_service'))) with check (tenant_id = current_tenant_id());
create trigger dashboards_touch before update on public.dashboards for each row execute function public.touch_updated_at();

-- =========================================================
-- DDR REPORTS
-- =========================================================
create table public.ddr_reports (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  well_id uuid references public.wells(id) on delete set null,
  rig_id uuid references public.rigs(id) on delete set null,
  document_id uuid references public.documents(id) on delete set null,
  report_date date not null,
  report_no text,
  shift text,
  prepared_by text,
  status text not null default 'draft',
  summary text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.ddr_reports(tenant_id);
create index on public.ddr_reports(well_id);
create index on public.ddr_reports(report_date);
alter table public.ddr_reports enable row level security;
create policy "tenant read ddr" on public.ddr_reports for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write ddr" on public.ddr_reports for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('ops_manager') or has_tenant_role('drilling_engineer'))) with check (tenant_id = current_tenant_id());
create trigger ddr_reports_touch before update on public.ddr_reports for each row execute function public.touch_updated_at();

-- =========================================================
-- DDR METRICS
-- =========================================================
create table public.ddr_metrics (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  ddr_id uuid not null references public.ddr_reports(id) on delete cascade,
  name text not null,
  unit text,
  value_num numeric,
  value_text text,
  category text,
  confidence numeric,
  source text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.ddr_metrics(tenant_id);
create index on public.ddr_metrics(ddr_id);
alter table public.ddr_metrics enable row level security;
create policy "tenant read ddr metrics" on public.ddr_metrics for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write ddr metrics" on public.ddr_metrics for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('ops_manager') or has_tenant_role('drilling_engineer') or has_tenant_role('analyst'))) with check (tenant_id = current_tenant_id());
create trigger ddr_metrics_touch before update on public.ddr_metrics for each row execute function public.touch_updated_at();

-- =========================================================
-- DDR AUDIT EVENTS
-- =========================================================
create table public.ddr_audit_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  ddr_id uuid not null references public.ddr_reports(id) on delete cascade,
  actor_id uuid not null,
  action text not null,
  before jsonb,
  after jsonb,
  note text,
  ts timestamptz not null default now()
);
create index on public.ddr_audit_events(tenant_id);
create index on public.ddr_audit_events(ddr_id);
alter table public.ddr_audit_events enable row level security;
create policy "tenant read ddr audit" on public.ddr_audit_events for select to authenticated using (tenant_id = current_tenant_id());
create policy "actor inserts ddr audit" on public.ddr_audit_events for insert to authenticated with check (tenant_id = current_tenant_id() and actor_id = auth.uid());

-- =========================================================
-- SPC SERIES + POINTS
-- =========================================================
create table public.spc_series (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  well_id uuid references public.wells(id) on delete set null,
  rig_id uuid references public.rigs(id) on delete set null,
  metric_name text not null,
  unit text,
  ucl numeric,
  lcl numeric,
  target numeric,
  chart_type text not null default 'individuals',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.spc_series(tenant_id);
alter table public.spc_series enable row level security;
create policy "tenant read spc series" on public.spc_series for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write spc series" on public.spc_series for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('ops_manager') or has_tenant_role('drilling_engineer') or has_tenant_role('analyst'))) with check (tenant_id = current_tenant_id());
create trigger spc_series_touch before update on public.spc_series for each row execute function public.touch_updated_at();

create table public.spc_points (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  series_id uuid not null references public.spc_series(id) on delete cascade,
  ts timestamptz not null,
  value numeric not null,
  out_of_control boolean not null default false,
  rule_flags text[] not null default '{}',
  metadata jsonb not null default '{}'::jsonb
);
create index on public.spc_points(tenant_id);
create index on public.spc_points(series_id, ts);
alter table public.spc_points enable row level security;
create policy "tenant read spc points" on public.spc_points for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write spc points" on public.spc_points for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('ops_manager') or has_tenant_role('drilling_engineer') or has_tenant_role('analyst') or has_tenant_role('api_service'))) with check (tenant_id = current_tenant_id());

-- =========================================================
-- CAPABILITY STUDIES
-- =========================================================
create table public.capability_studies (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  series_id uuid not null references public.spc_series(id) on delete cascade,
  cp numeric,
  cpk numeric,
  pp numeric,
  ppk numeric,
  sample_size integer,
  computed_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);
create index on public.capability_studies(tenant_id);
create index on public.capability_studies(series_id);
alter table public.capability_studies enable row level security;
create policy "tenant read capability" on public.capability_studies for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write capability" on public.capability_studies for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('ops_manager') or has_tenant_role('analyst') or has_tenant_role('api_service'))) with check (tenant_id = current_tenant_id());

-- =========================================================
-- ENTITIES + RELATIONS + INSIGHTS
-- =========================================================
create table public.entities (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  name text not null,
  type text not null,
  canonical_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.entities(tenant_id);
create index on public.entities(type);
alter table public.entities enable row level security;
create policy "tenant read entities" on public.entities for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write entities" on public.entities for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('analyst') or has_tenant_role('api_service'))) with check (tenant_id = current_tenant_id());
create trigger entities_touch before update on public.entities for each row execute function public.touch_updated_at();

create table public.entity_relations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  source_entity uuid not null references public.entities(id) on delete cascade,
  target_entity uuid not null references public.entities(id) on delete cascade,
  relation text not null,
  weight numeric,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index on public.entity_relations(tenant_id);
create index on public.entity_relations(source_entity);
create index on public.entity_relations(target_entity);
alter table public.entity_relations enable row level security;
create policy "tenant read entity relations" on public.entity_relations for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write entity relations" on public.entity_relations for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('analyst') or has_tenant_role('api_service'))) with check (tenant_id = current_tenant_id());

create table public.insights (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  entity_id uuid references public.entities(id) on delete set null,
  document_id uuid references public.documents(id) on delete set null,
  title text not null,
  body text,
  severity text not null default 'info',
  tags text[] not null default '{}',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.insights(tenant_id);
create index on public.insights(entity_id);
alter table public.insights enable row level security;
create policy "tenant read insights" on public.insights for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write insights" on public.insights for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('analyst') or has_tenant_role('drilling_engineer') or has_tenant_role('api_service'))) with check (tenant_id = current_tenant_id());
create trigger insights_touch before update on public.insights for each row execute function public.touch_updated_at();

-- =========================================================
-- AGENT RUNS + STEPS
-- =========================================================
create table public.agent_runs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  owner_id uuid not null,
  goal text not null,
  context jsonb not null default '{}'::jsonb,
  final_result jsonb,
  status text not null default 'running',
  started_at timestamptz not null default now(),
  finished_at timestamptz
);
create index on public.agent_runs(tenant_id);
create index on public.agent_runs(owner_id);
alter table public.agent_runs enable row level security;
create policy "tenant read agent runs" on public.agent_runs for select to authenticated using (tenant_id = current_tenant_id());
create policy "owner inserts agent runs" on public.agent_runs for insert to authenticated with check (tenant_id = current_tenant_id() and owner_id = auth.uid());
create policy "owner or admin updates agent runs" on public.agent_runs for update to authenticated using (tenant_id = current_tenant_id() and (owner_id = auth.uid() or has_tenant_role('tenant_admin')));

create table public.agent_steps (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  run_id uuid not null references public.agent_runs(id) on delete cascade,
  step_index integer not null,
  thought text,
  action text,
  input jsonb,
  observation jsonb,
  error text,
  ts timestamptz not null default now(),
  unique (run_id, step_index)
);
create index on public.agent_steps(tenant_id);
create index on public.agent_steps(run_id);
alter table public.agent_steps enable row level security;
create policy "tenant read agent steps" on public.agent_steps for select to authenticated using (tenant_id = current_tenant_id());
create policy "tenant write agent steps" on public.agent_steps for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('analyst') or has_tenant_role('api_service'))) with check (tenant_id = current_tenant_id());

-- =========================================================
-- MODEL EVALUATIONS + CONFUSION MATRIX
-- =========================================================
create table public.model_evaluations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  model_name text not null,
  version text,
  task text,
  accuracy numeric,
  precision numeric,
  recall numeric,
  f1 numeric,
  metrics jsonb not null default '{}'::jsonb,
  computed_at timestamptz not null default now()
);
create index on public.model_evaluations(tenant_id);
alter table public.model_evaluations enable row level security;
create policy "tenant read evals" on public.model_evaluations for select to authenticated using (tenant_id = current_tenant_id());
create policy "admin writes evals" on public.model_evaluations for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('api_service'))) with check (tenant_id = current_tenant_id());

create table public.confusion_matrix_cells (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  evaluation_id uuid not null references public.model_evaluations(id) on delete cascade,
  predicted_label text not null,
  actual_label text not null,
  count integer not null default 0
);
create index on public.confusion_matrix_cells(tenant_id);
create index on public.confusion_matrix_cells(evaluation_id);
alter table public.confusion_matrix_cells enable row level security;
create policy "tenant read cm" on public.confusion_matrix_cells for select to authenticated using (tenant_id = current_tenant_id());
create policy "admin writes cm" on public.confusion_matrix_cells for all to authenticated using (tenant_id = current_tenant_id() and (has_tenant_role('tenant_admin') or has_tenant_role('api_service'))) with check (tenant_id = current_tenant_id());