// Process an uploaded document: download → extract text → chunk → embed → store.
// Body: { document_id: string }
import { corsHeaders, getAuthContext, json, errorResponse, chunkText } from "../_shared/utils.ts";

const OPENAI_API_KEY = Deno.env.get("OPENAI_API_KEY");
const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY");

async function extractText(file: Blob, mime: string | null, fileName: string): Promise<string> {
  const lower = (mime ?? "").toLowerCase();
  const name = fileName.toLowerCase();

  // Text-like: read directly
  if (lower.startsWith("text/") || name.endsWith(".txt") || name.endsWith(".md") || name.endsWith(".csv") || name.endsWith(".json") || name.endsWith(".log")) {
    return await file.text();
  }

  // PDF / image: use Gemini multimodal for OCR + extraction
  if (!GEMINI_API_KEY) {
    throw new Error(`Cannot extract text from ${mime ?? "binary"} without GEMINI_API_KEY`);
  }
  const buffer = new Uint8Array(await file.arrayBuffer());
  const b64 = btoa(String.fromCharCode(...buffer));
  const payload = {
    contents: [{
      parts: [
        { inline_data: { mime_type: mime || "application/pdf", data: b64 } },
        { text: "Extract ALL text content from this document. Preserve tables as pipe-delimited rows. Return ONLY the extracted text, no commentary." },
      ],
    }],
  };
  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) },
  );
  if (!res.ok) throw new Error(`Gemini extraction failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  const text = data.candidates?.[0]?.content?.parts?.map((p: { text?: string }) => p.text ?? "").join("\n") ?? "";
  if (!text.trim()) throw new Error("Gemini returned empty text");
  return text;
}

async function embedBatch(texts: string[]): Promise<number[][]> {
  if (!OPENAI_API_KEY) throw new Error("OPENAI_API_KEY not configured");
  const res = await fetch("https://api.openai.com/v1/embeddings", {
    method: "POST",
    headers: { "Authorization": `Bearer ${OPENAI_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: "text-embedding-3-small", input: texts }),
  });
  if (!res.ok) throw new Error(`OpenAI embeddings failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  return data.data.map((d: { embedding: number[] }) => d.embedding);
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
  try {
    const { admin, tenantId } = await getAuthContext(req);
    const { document_id } = await req.json();
    if (!document_id) return json({ error: "document_id required" }, 400);

    // Load document (use admin to bypass RLS - we've already verified tenant)
    const { data: doc, error: docErr } = await admin
      .from("documents").select("*").eq("id", document_id).eq("tenant_id", tenantId).single();
    if (docErr || !doc) return json({ error: "Document not found" }, 404);

    // Look up file path
    const { data: file } = await admin
      .from("uploaded_files").select("path,bucket,mime").eq("id", doc.file_id).single();
    if (!file) return json({ error: "Source file not found" }, 404);

    await admin.from("documents").update({ status: "processing" }).eq("id", document_id);

    const t0 = Date.now();
    // Download
    const { data: blob, error: dlErr } = await admin.storage.from(file.bucket).download(file.path);
    if (dlErr || !blob) throw new Error(`Download failed: ${dlErr?.message}`);

    // Extract → chunk → embed
    const text = await extractText(blob, file.mime, doc.file_name);
    const chunks = chunkText(text);
    if (chunks.length === 0) throw new Error("No text extracted from document");

    // Embed in batches of 32
    const BATCH = 32;
    const rows: Array<Record<string, unknown>> = [];
    for (let i = 0; i < chunks.length; i += BATCH) {
      const slice = chunks.slice(i, i + BATCH);
      const embs = await embedBatch(slice);
      slice.forEach((t, j) => {
        rows.push({
          tenant_id: tenantId,
          document_id,
          chunk_index: i + j,
          text: t,
          embedding: embs[j],
        });
      });
    }

    // Clear old chunks then insert new
    await admin.from("document_chunks").delete().eq("document_id", document_id);
    const { error: insErr } = await admin.from("document_chunks").insert(rows);
    if (insErr) throw new Error(`Insert chunks failed: ${insErr.message}`);

    const ms = Date.now() - t0;
    await admin.from("documents").update({
      status: "processed",
      processing_time_ms: ms,
    }).eq("id", document_id);

    return json({ document_id, chunks: chunks.length, processing_time_ms: ms });
  } catch (err) {
    return errorResponse(err);
  }
});
