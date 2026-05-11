// Shared helpers for edge functions
import { createClient, SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2.49.4";

export const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

export interface AuthContext {
  supabase: SupabaseClient;
  admin: SupabaseClient;
  userId: string;
  tenantId: string;
}

/** Resolve auth context: returns user-scoped client + admin client + tenant. */
export async function getAuthContext(req: Request): Promise<AuthContext> {
  const authHeader = req.headers.get("Authorization");
  if (!authHeader) throw new Response("Missing Authorization header", { status: 401 });

  const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
  const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
  const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

  const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    global: { headers: { Authorization: authHeader } },
  });
  const admin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

  const { data: userData, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userData.user) throw new Response("Unauthorized", { status: 401 });

  const { data: profile, error: profErr } = await supabase
    .from("profiles").select("tenant_id").eq("id", userData.user.id).single();
  if (profErr || !profile) throw new Response("No tenant for user", { status: 403 });

  return { supabase, admin, userId: userData.user.id, tenantId: profile.tenant_id };
}

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

export function errorResponse(err: unknown, fallbackStatus = 500): Response {
  if (err instanceof Response) {
    const text = err.statusText || "Error";
    return new Response(JSON.stringify({ error: text }), {
      status: err.status,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
  const msg = err instanceof Error ? err.message : String(err);
  console.error("[edge] error:", msg);
  return json({ error: msg }, fallbackStatus);
}

/** Split text into ~chunkChars chunks at sentence/paragraph boundaries. */
export function chunkText(text: string, chunkChars = 1200, overlap = 150): string[] {
  const clean = text.replace(/\s+/g, " ").trim();
  if (!clean) return [];
  const chunks: string[] = [];
  let i = 0;
  while (i < clean.length) {
    const end = Math.min(i + chunkChars, clean.length);
    let stop = end;
    if (end < clean.length) {
      const dot = clean.lastIndexOf(". ", end);
      if (dot > i + chunkChars / 2) stop = dot + 1;
    }
    chunks.push(clean.slice(i, stop).trim());
    if (stop >= clean.length) break;
    i = stop - overlap;
    if (i < 0) i = 0;
  }
  return chunks;
}
