// Generate KPIs + charts JSON for a document. Stores into `dashboards`.
// Body: { document_id: string }
import { corsHeaders, getAuthContext, json, errorResponse } from "../_shared/utils.ts";

const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY");

const SCHEMA = {
  type: "object",
  properties: {
    kpis: {
      type: "array",
      items: {
        type: "object",
        properties: {
          label: { type: "string" },
          value: { type: "string" },
          unit: { type: "string" },
          trend: { type: "string", enum: ["up", "down", "neutral"] },
        },
        required: ["label", "value"],
      },
    },
    charts: {
      type: "array",
      items: {
        type: "object",
        properties: {
          type: { type: "string", enum: ["line", "bar", "pie", "area"] },
          title: { type: "string" },
          data: { type: "array", items: { type: "object" } },
        },
        required: ["type", "title", "data"],
      },
    },
    insights: { type: "array", items: { type: "string" } },
  },
  required: ["kpis", "charts", "insights"],
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
  try {
    if (!GEMINI_API_KEY) return json({ error: "GEMINI_API_KEY not configured" }, 500);
    const { admin, tenantId } = await getAuthContext(req);
    const { document_id } = await req.json();
    if (!document_id) return json({ error: "document_id required" }, 400);

    // Pull chunks (first ~40 — bound prompt size)
    const { data: chunks } = await admin
      .from("document_chunks")
      .select("text")
      .eq("document_id", document_id)
      .eq("tenant_id", tenantId)
      .order("chunk_index", { ascending: true })
      .limit(40);

    if (!chunks || chunks.length === 0) return json({ error: "Document not yet processed" }, 409);
    const corpus = chunks.map((c) => c.text).join("\n\n").slice(0, 60000);

    const prompt = `You are analyzing a drilling operations document. Extract KPIs, propose 2-4 charts using data found in the document, and write 3-5 concise insights. Return JSON ONLY matching the provided schema.\n\n=== DOCUMENT ===\n${corpus}\n=== END ===`;

    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: {
            responseMimeType: "application/json",
            responseSchema: SCHEMA,
            temperature: 0.2,
          },
        }),
      },
    );
    if (!res.ok) throw new Error(`Gemini failed: ${res.status} ${await res.text()}`);
    const data = await res.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text ?? "{}";
    let parsed: { kpis?: unknown[]; charts?: unknown[]; insights?: unknown[] } = {};
    try { parsed = JSON.parse(text); } catch { /* keep empty */ }

    const payload = {
      tenant_id: tenantId,
      document_id,
      kpis: parsed.kpis ?? [],
      charts: parsed.charts ?? [],
      insights: parsed.insights ?? [],
      status: "ready",
    };

    // Upsert dashboard
    const { error: upErr } = await admin
      .from("dashboards")
      .upsert(payload, { onConflict: "document_id" });
    if (upErr) throw new Error(`Upsert dashboard failed: ${upErr.message}`);

    await admin.from("documents").update({ has_dashboard: true }).eq("id", document_id);

    return json(payload);
  } catch (err) {
    return errorResponse(err);
  }
});
