-- Storage RLS for the `raw` bucket. Folder layout: {tenant_id}/{owner_id}/{filename}
create policy "raw read in tenant"
on storage.objects for select to authenticated
using (
  bucket_id = 'raw'
  and (storage.foldername(name))[1] = public.current_tenant_id()::text
);

create policy "raw upload to own tenant"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'raw'
  and (storage.foldername(name))[1] = public.current_tenant_id()::text
  and (storage.foldername(name))[2] = auth.uid()::text
);

create policy "raw update own or admin"
on storage.objects for update to authenticated
using (
  bucket_id = 'raw'
  and (storage.foldername(name))[1] = public.current_tenant_id()::text
  and (
    (storage.foldername(name))[2] = auth.uid()::text
    or public.has_tenant_role('tenant_admin')
  )
);

create policy "raw delete own or admin"
on storage.objects for delete to authenticated
using (
  bucket_id = 'raw'
  and (storage.foldername(name))[1] = public.current_tenant_id()::text
  and (
    (storage.foldername(name))[2] = auth.uid()::text
    or public.has_tenant_role('tenant_admin')
  )
);

-- Vector search RPC: callable by authenticated clients, scoped via RLS
create or replace function public.match_document_chunks(
  query_embedding extensions.vector(1536),
  match_count int default 10,
  filter_document_id uuid default null
)
returns table (
  id uuid,
  document_id uuid,
  chunk_index int,
  text text,
  similarity float
)
language plpgsql
stable
security invoker
set search_path = public, extensions
as $$
begin
  return query
  select c.id, c.document_id, c.chunk_index, c.text,
         1 - (c.embedding <=> query_embedding) as similarity
  from public.document_chunks c
  where c.tenant_id = public.current_tenant_id()
    and c.embedding is not null
    and (filter_document_id is null or c.document_id = filter_document_id)
  order by c.embedding <=> query_embedding
  limit match_count;
end;
$$;