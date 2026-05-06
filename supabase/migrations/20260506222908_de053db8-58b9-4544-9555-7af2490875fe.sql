
-- Lock search_path on touch_updated_at and handle_new_user (already set, re-affirm)
alter function public.touch_updated_at() set search_path = public;

-- Revoke EXECUTE from anon and authenticated on internal helpers.
-- They are still callable from RLS policies (which run as the function owner).
revoke execute on function public.has_role(uuid, public.app_role) from anon, authenticated, public;
revoke execute on function public.current_tenant_id() from anon, authenticated, public;
revoke execute on function public.has_tenant_role(public.app_role) from anon, authenticated, public;
revoke execute on function public.handle_new_user() from anon, authenticated, public;
revoke execute on function public.touch_updated_at() from anon, authenticated, public;
