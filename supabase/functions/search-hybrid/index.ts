// Hybrid search across document chunks. Body: { query: string, top_k?: number, document_id?: string }
import { corsHeaders, getAuthContext, json, errorResponse } from "../_shared/utils.ts";

const OPENAI_API_KEY = Deno.env.get("OPENAI_API_KEY");

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
  try {
    if (!OPENAI_API_KEY) return json({ error: "OPENAI_API_KEY not configured" }, 500);
    const { supabase } = await getAuthContext(req);
    const { query, top_k = 10, document_id } = await req.json();
    if (!query || typeof query !== "string") return json({ error: "query required" }, 400);

    // Embed query
    const embRes = await fetch("https://api.openai.com/v1/embeddings", {
      method: "POST",
      headers: { "Authorization": `Bearer ${OPENAI_API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: "text-embedding-3-small", input: query }),
    });
    if (!embRes.ok) throw new Error(`Embed failed: ${embRes.status}`);
    const embJson = await embRes.json();
    const queryEmbedding = embJson.data[0].embedding;

    const { data: matches, error } = await supabase.rpc("match_document_chunks", {
      query_embedding: queryEmbedding,
      match_count: top_k,
      filter_document_id: document_id ?? null,
    });
    if (error) throw new Error(`Search RPC failed: ${error.message}`);

    return json({
      query,
      count: matches?.length ?? 0,
      results: (matches ?? []).map((m: { id: string; document_id: string; chunk_index: number; text: string; similarity: number }, idx: number) => ({
        index: idx,
        chunk_id: m.id,
        document_id: m.document_id,
        chunk_index: m.chunk_index,
        text: m.text,
        semantic_score: m.similarity,
        bm25_score: 0,
        combined_score: m.similarity,
      })),
    });
  } catch (err) {
    return errorResponse(err);
  }
});
