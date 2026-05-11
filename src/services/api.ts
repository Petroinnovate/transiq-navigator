// Supabase-native API client. Replaces the FastAPI-based one.
// Uploads go directly to the `raw` storage bucket; processing/dashboard/search happen via edge functions.
import { supabase } from "@/integrations/supabase/client";

export interface UploadResponse {
  doc_id: string;
  task_id: string;
  status: "processing" | "completed" | "failed";
  message: string;
  files_processed?: number;
}

export interface KPIBlock {
  label: string;
  value: string | number;
  unit?: string;
  trend?: "up" | "down" | "neutral";
}

export interface ChartBlock {
  type: string;
  title: string;
  data: Record<string, unknown>[];
  config?: Record<string, unknown>;
}

export interface DashboardData {
  status?: string;
  kpis: KPIBlock[];
  charts: ChartBlock[];
  insights?: string[];
  [key: string]: unknown;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  document_id?: string;
  /** @deprecated kept for compat with legacy UI */
  use_hybrid?: boolean;
}

export interface BatchStatus {
  batch_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  total_files: number;
  completed_files: number;
  failed_files: number;
  progress: number;
  documents: Array<{ doc_id: string; task_id: string; file_name: string; status: string }>;
}

export interface AgentRunResponse {
  status: "success" | "failed";
  steps: Array<{
    step: number;
    thought?: string;
    action?: string;
    input?: Record<string, unknown>;
    result?: Record<string, unknown>;
    error?: string;
  }>;
  final_result: Record<string, unknown>;
}

export interface SearchResult {
  query: string;
  count: number;
  results: Array<{
    index: number;
    chunk_id: string;
    document_id: string;
    chunk_index: number;
    text: string;
    bm25_score: number;
    semantic_score: number;
    combined_score: number;
  }>;
}

async function getTenantId(): Promise<{ userId: string; tenantId: string }> {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Not authenticated");
  const { data: profile, error } = await supabase
    .from("profiles").select("tenant_id").eq("id", user.id).single();
  if (error || !profile) throw new Error("No tenant for user");
  return { userId: user.id, tenantId: profile.tenant_id };
}

async function uploadOne(file: File): Promise<{ doc_id: string }> {
  const { userId, tenantId } = await getTenantId();
  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const path = `${tenantId}/${userId}/${crypto.randomUUID()}-${safeName}`;

  const { error: upErr } = await supabase.storage.from("raw").upload(path, file, {
    contentType: file.type || "application/octet-stream",
    upsert: false,
  });
  if (upErr) throw new Error(`Upload failed: ${upErr.message}`);

  const { data: fileRow, error: fileErr } = await supabase.from("uploaded_files").insert({
    tenant_id: tenantId,
    owner_id: userId,
    bucket: "raw",
    path,
    mime: file.type,
    size: file.size,
  }).select("id").single();
  if (fileErr || !fileRow) throw new Error(`Register file failed: ${fileErr?.message}`);

  const { data: doc, error: docErr } = await supabase.from("documents").insert({
    tenant_id: tenantId,
    owner_id: userId,
    file_id: fileRow.id,
    file_name: file.name,
    mime: file.type,
    status: "queued",
  }).select("id").single();
  if (docErr || !doc) throw new Error(`Register document failed: ${docErr?.message}`);

  // Fire-and-forget processing
  void supabase.functions.invoke("process-document", { body: { document_id: doc.id } });

  return { doc_id: doc.id };
}

export const api = {
  async uploadDocument(file: File): Promise<UploadResponse> {
    const { doc_id } = await uploadOne(file);
    return { doc_id, task_id: doc_id, status: "processing", message: "Processing started" };
  },

  async uploadDocuments(files: File[]): Promise<UploadResponse> {
    const results = await Promise.all(files.map(uploadOne));
    return {
      doc_id: results[0]?.doc_id ?? "",
      task_id: results[0]?.doc_id ?? "",
      status: "processing",
      message: `Processing ${results.length} files`,
      files_processed: results.length,
    };
  },

  async uploadProject(files: File[]): Promise<UploadResponse> {
    return this.uploadDocuments(files);
  },

  async getDocument(docId: string) {
    const { data, error } = await supabase
      .from("documents").select("*").eq("id", docId).single();
    if (error || !data) throw new Error(error?.message ?? "Document not found");
    const { count: chunksCount } = await supabase
      .from("document_chunks").select("*", { count: "exact", head: true }).eq("document_id", docId);
    return {
      document: {
        id: data.id,
        file_name: data.file_name,
        status: data.status,
        created_at: data.created_at,
        has_dashboard: data.has_dashboard,
      },
      chunks_count: chunksCount ?? 0,
      edges_count: 0,
    };
  },

  async getDocumentChunks(docId: string) {
    const { data, error } = await supabase
      .from("document_chunks").select("id,chunk_index,text,metadata")
      .eq("document_id", docId).order("chunk_index", { ascending: true });
    if (error) throw new Error(error.message);
    return (data ?? []).map((c) => ({ id: c.id, index: c.chunk_index, text: c.text, metadata: c.metadata as Record<string, unknown> }));
  },

  async searchDocuments(request: SearchRequest): Promise<SearchResult> {
    const { data, error } = await supabase.functions.invoke("search-hybrid", { body: request });
    if (error) throw new Error(error.message);
    return data as SearchResult;
  },

  async getDashboardData(docId: string): Promise<DashboardData> {
    const { data, error } = await supabase
      .from("dashboards").select("*").eq("document_id", docId).maybeSingle();

    if (data) {
      return {
        status: data.status,
        kpis: (data.kpis as unknown as KPIBlock[]) ?? [],
        charts: (data.charts as unknown as ChartBlock[]) ?? [],
        insights: (data.insights as unknown as string[]) ?? [],
      };
    }

    // No dashboard yet → check doc state
    const doc = await this.getDocument(docId);
    if (doc.document.status === "processed" && !data) {
      // Trigger generation, return empty for now
      void supabase.functions.invoke("generate-dashboard", { body: { document_id: docId } });
    }
    if (error) console.warn("[dashboard] fetch:", error.message);
    return { status: doc.document.status, kpis: [], charts: [] };
  },

  async getTaskStatus(taskId: string) {
    // taskId == doc_id in the new model
    const { data, error } = await supabase
      .from("documents").select("id,status,has_dashboard").eq("id", taskId).single();
    if (error || !data) throw new Error(error?.message ?? "Task not found");
    const status =
      data.status === "queued" ? "queued" :
      data.status === "processing" ? "processing" :
      data.status === "processed" ? "completed" : "failed";
    return {
      task_id: data.id,
      status: status as "queued" | "processing" | "completed" | "failed",
      progress: data.status === "processed" ? 100 : data.status === "processing" ? 50 : 0,
      message: `Status: ${data.status}`,
    };
  },

  async getBatchStatus(_batchId: string): Promise<BatchStatus> {
    throw new Error("Batch status not implemented in Supabase backend yet");
  },

  async runAgent(_goal: string, _context: Record<string, unknown>): Promise<AgentRunResponse> {
    throw new Error("Agent runs not implemented in Supabase backend yet");
  },

  async listDocuments(limit = 20, offset = 0): Promise<{
    items: Array<{
      id: string;
      file_name: string;
      status: string;
      mime: string | null;
      has_dashboard: boolean;
      created_at: string;
      updated_at: string;
    }>;
    total: number;
  }> {
    const { data, error, count } = await supabase
      .from("documents")
      .select("id,file_name,status,mime,has_dashboard,created_at,updated_at", { count: "exact" })
      .order("created_at", { ascending: false })
      .range(offset, offset + limit - 1);
    if (error) throw new Error(error.message);
    return { items: data ?? [], total: count ?? 0 };
  },

  async reprocessDocument(docId: string): Promise<void> {
    const { error: updErr } = await supabase
      .from("documents")
      .update({ status: "queued", has_dashboard: false })
      .eq("id", docId);
    if (updErr) throw new Error(updErr.message);
    const { error } = await supabase.functions.invoke("process-document", {
      body: { document_id: docId },
    });
    if (error) throw new Error(error.message);
  },

  async deleteDocument(docId: string): Promise<void> {
    const { error } = await supabase.from("documents").delete().eq("id", docId);
    if (error) throw new Error(error.message);
  },

  async healthCheck() {
    return { status: "ok" };
  },
};

/**
 * Subscribe to live document status changes via realtime.
 * Returns an unsubscribe function.
 */
export function streamDocumentStatus(
  docId: string,
  onUpdate: (status: { status: string; has_dashboard: boolean }) => void,
): () => void {
  const channel = supabase
    .channel(`doc-${docId}`)
    .on("postgres_changes",
      { event: "UPDATE", schema: "public", table: "documents", filter: `id=eq.${docId}` },
      (payload) => {
        const row = payload.new as { status: string; has_dashboard: boolean };
        onUpdate({ status: row.status, has_dashboard: row.has_dashboard });
      },
    )
    .subscribe();
  return () => { supabase.removeChannel(channel); };
}
