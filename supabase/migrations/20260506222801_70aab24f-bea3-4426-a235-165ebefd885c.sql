
-- ─────────────────────────────────────────────────────────────
-- Phase 1: Tenancy, Roles, Core Drilling Tables, Files, Jobs, Audit
-- ─────────────────────────────────────────────────────────────

create extension if not exists pgcrypto;

-- App roles
create type public.app_role as enum (
  'super_admin','tenant_admin','ops_manager',
  'drilling_engineer','analyst','viewer','api_service'
);

-- Tenants
create table public.tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  plan text not null default 'free',
  settings jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Profiles (1:1 with auth.users)
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  email text not null,
  display_name text,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.profiles(tenant_id);

-- User roles (NEVER on profiles)
create table public.user_roles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  role public.app_role not null,
  created_at timestamptz not null default now(),
  unique(user_id, tenant_id, role)
);
create index on public.user_roles(user_id);
create index on public.user_roles(tenant_id);

-- Security definer helpers
create or replace function public.has_role(_user_id uuid, _role public.app_role)
returns boolean language sql stable security definer set search_path = public as $$
  select exists(select 1 from public.user_roles where user_id = _user_id and role = _role);
$$;

create or replace function public.current_tenant_id()
returns uuid language sql stable security definer set search_path = public as $$
  select tenant_id from public.profiles where id = auth.uid();
$$;

create or replace function public.has_tenant_role(_role public.app_role)
returns boolean language sql stable security definer set search_path = public as $$
  select exists(
    select 1 from public.user_roles
    where user_id = auth.uid()
      and tenant_id = public.current_tenant_id()
      and role = _role
  );
$$;

-- Self-serve onboarding trigger: create tenant + profile + tenant_admin
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  v_tenant_id uuid;
  v_slug text;
begin
  v_slug := lower(regexp_replace(split_part(new.email,'@',2), '[^a-z0-9]+','-','g'))
            || '-' || substr(replace(new.id::text,'-',''),1,8);

  insert into public.tenants(name, slug)
  values (coalesce(split_part(new.email,'@',2),'workspace'), v_slug)
  returning id into v_tenant_id;

  insert into public.profiles(id, tenant_id, email, display_name)
  values (new.id, v_tenant_id, new.email, coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email,'@',1)));

  insert into public.user_roles(user_id, tenant_id, role)
  values (new.id, v_tenant_id, 'tenant_admin');

  return new;
end; $$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Updated-at helper
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at := now(); return new; end; $$;

-- Drilling domain
create table public.fleets (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  name text not null,
  region text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.fleets(tenant_id);

create table public.rigs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  fleet_id uuid references public.fleets(id) on delete set null,
  rig_no text not null,
  contractor text,
  status text not null default 'idle',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(tenant_id, rig_no)
);
create index on public.rigs(tenant_id);
create index on public.rigs(fleet_id);

create table public.wells (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  rig_id uuid references public.rigs(id) on delete set null,
  well_name text not null,
  field text,
  spud_date date,
  td_date date,
  status text not null default 'planned',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.wells(tenant_id);
create index on public.wells(rig_id);

-- Files
create table public.uploaded_files (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  owner_id uuid not null references auth.users(id) on delete cascade,
  bucket text not null default 'raw',
  path text not null,
  mime text,
  size bigint,
  sha256 text,
  status text not null default 'uploaded',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.uploaded_files(tenant_id);
create index on public.uploaded_files(owner_id);
create index on public.uploaded_files(sha256);

-- Job queue
create table public.job_queue (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  type text not null,
  payload jsonb not null default '{}'::jsonb,
  priority int not null default 5,
  status text not null default 'queued',
  attempts int not null default 0,
  max_attempts int not null default 5,
  run_after timestamptz not null default now(),
  locked_by text,
  locked_at timestamptz,
  result jsonb,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.job_queue(tenant_id);
create index on public.job_queue(status, run_after);

-- Audit log
create table public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  actor_id uuid references auth.users(id) on delete set null,
  action text not null,
  resource text not null,
  resource_id text,
  diff jsonb,
  ip text,
  ua text,
  ts timestamptz not null default now()
);
create index on public.audit_logs(tenant_id, ts desc);
create index on public.audit_logs(resource, resource_id);

-- updated_at triggers
do $$ declare t text; begin
  for t in select unnest(array['tenants','profiles','fleets','rigs','wells','uploaded_files','job_queue']) loop
    execute format('create trigger trg_touch_%I before update on public.%I for each row execute function public.touch_updated_at();', t, t);
  end loop;
end $$;

-- Enable RLS
alter table public.tenants enable row level security;
alter table public.profiles enable row level security;
alter table public.user_roles enable row level security;
alter table public.fleets enable row level security;
alter table public.rigs enable row level security;
alter table public.wells enable row level security;
alter table public.uploaded_files enable row level security;
alter table public.job_queue enable row level security;
alter table public.audit_logs enable row level security;

-- RLS: tenant scoped reads, role-gated writes
create policy "tenant member can read tenant"
  on public.tenants for select to authenticated
  using (id = public.current_tenant_id());

create policy "tenant_admin can update tenant"
  on public.tenants for update to authenticated
  using (id = public.current_tenant_id() and public.has_tenant_role('tenant_admin'));

create policy "user reads own profile"
  on public.profiles for select to authenticated
  using (id = auth.uid() or tenant_id = public.current_tenant_id());

create policy "user updates own profile"
  on public.profiles for update to authenticated
  using (id = auth.uid());

create policy "tenant member reads roles in tenant"
  on public.user_roles for select to authenticated
  using (tenant_id = public.current_tenant_id());

create policy "tenant_admin manages roles"
  on public.user_roles for all to authenticated
  using (tenant_id = public.current_tenant_id() and public.has_tenant_role('tenant_admin'))
  with check (tenant_id = public.current_tenant_id() and public.has_tenant_role('tenant_admin'));

-- Generic tenant-scoped policies for fleets/rigs/wells/files/jobs/audit
create policy "tenant read fleets" on public.fleets for select to authenticated
  using (tenant_id = public.current_tenant_id());
create policy "tenant write fleets" on public.fleets for all to authenticated
  using (tenant_id = public.current_tenant_id() and (public.has_tenant_role('tenant_admin') or public.has_tenant_role('ops_manager')))
  with check (tenant_id = public.current_tenant_id());

create policy "tenant read rigs" on public.rigs for select to authenticated
  using (tenant_id = public.current_tenant_id());
create policy "tenant write rigs" on public.rigs for all to authenticated
  using (tenant_id = public.current_tenant_id() and (public.has_tenant_role('tenant_admin') or public.has_tenant_role('ops_manager')))
  with check (tenant_id = public.current_tenant_id());

create policy "tenant read wells" on public.wells for select to authenticated
  using (tenant_id = public.current_tenant_id());
create policy "tenant write wells" on public.wells for all to authenticated
  using (tenant_id = public.current_tenant_id() and (public.has_tenant_role('tenant_admin') or public.has_tenant_role('ops_manager') or public.has_tenant_role('drilling_engineer')))
  with check (tenant_id = public.current_tenant_id());

create policy "tenant read files" on public.uploaded_files for select to authenticated
  using (tenant_id = public.current_tenant_id());
create policy "owner inserts files" on public.uploaded_files for insert to authenticated
  with check (tenant_id = public.current_tenant_id() and owner_id = auth.uid());
create policy "owner or admin updates files" on public.uploaded_files for update to authenticated
  using (tenant_id = public.current_tenant_id() and (owner_id = auth.uid() or public.has_tenant_role('tenant_admin')));
create policy "owner or admin deletes files" on public.uploaded_files for delete to authenticated
  using (tenant_id = public.current_tenant_id() and (owner_id = auth.uid() or public.has_tenant_role('tenant_admin')));

create policy "tenant read jobs" on public.job_queue for select to authenticated
  using (tenant_id = public.current_tenant_id());
create policy "tenant_admin manages jobs" on public.job_queue for all to authenticated
  using (tenant_id = public.current_tenant_id() and public.has_tenant_role('tenant_admin'))
  with check (tenant_id = public.current_tenant_id());

create policy "tenant read audit" on public.audit_logs for select to authenticated
  using (tenant_id = public.current_tenant_id() and public.has_tenant_role('tenant_admin'));
-- audit_logs are written only by service role / triggers — no insert policy

-- Storage bucket for raw uploads (private)
insert into storage.buckets (id, name, public)
values ('raw','raw', false)
on conflict (id) do nothing;

create policy "tenant read own raw files"
  on storage.objects for select to authenticated
  using (bucket_id = 'raw' and (storage.foldername(name))[1] = public.current_tenant_id()::text);

create policy "tenant upload own raw files"
  on storage.objects for insert to authenticated
  with check (bucket_id = 'raw' and (storage.foldername(name))[1] = public.current_tenant_id()::text);

create policy "owner deletes own raw files"
  on storage.objects for delete to authenticated
  using (bucket_id = 'raw' and owner = auth.uid());
