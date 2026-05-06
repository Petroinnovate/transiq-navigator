import axios from '@/lib/axios';

const API_V2_BASE = '/api/v2';

// ── Response types ────────────────────────────────────────────────────────────

export interface UploadResponse {
  doc_id: string;
  task_id: string;
  status: 'processing' | 'completed' | 'failed';
  message: string;
  dashboard?: DashboardData;   // typed — was `any`
  processing_time?: number;
  files_processed?: number;
}

export interface DocumentInfo {
  document: {
    id: string;
    file_name: string;
    status: string;
    created_at: string;
    has_dashboard?: boolean;
  };
  chunks_count: number;
  edges_count: number;
}

export interface DocumentChunk {
  id: string;
  text: string;
  index: number;
  metadata?: Record<string, unknown>;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  use_hybrid?: boolean;
}

export interface SearchResult {
  query: string;
  results: Array<{
    index: number;
    text: string;
    bm25_score: number;
    semantic_score: number;
    combined_score: number;
  }>;
  count: number;
}

export interface AgentRunResponse {
  status: 'success' | 'failed';
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

export interface TaskStatus {
  task_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress?: number;
  message?: string;
  result?: Record<string, unknown>;
  error?: string;
}

// Dashboard types — was `any` everywhere
export interface KPIBlock {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'neutral';
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
  [key: string]: unknown; // allow extra fields from backend without losing type safety
}

// ── API client ────────────────────────────────────────────────────────────────

export const api = {
  // Upload a single document
  async uploadDocument(
    file: File,
    options?: {
      provider?: 'gemini' | 'openai';
      enable_deduction?: boolean;
      enable_patterns?: boolean;
    }
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams();
    if (options?.provider) params.append('provider', options.provider);
    if (options?.enable_deduction !== undefined)
      params.append('enable_deduction', String(options.enable_deduction));
    if (options?.enable_patterns !== undefined)
      params.append('enable_patterns', String(options.enable_patterns));

    const response = await axios.post<UploadResponse>(
      `${API_V2_BASE}/generate?${params.toString()}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  // Upload multiple documents for batch analysis (max 5 files)
  async uploadDocuments(
    files: File[],
    options?: {
      provider?: 'gemini' | 'openai';
      enable_deduction?: boolean;
      enable_patterns?: boolean;
    }
  ): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));

    const params = new URLSearchParams();
    if (options?.provider) params.append('provider', options.provider);
    if (options?.enable_deduction !== undefined)
      params.append('enable_deduction', String(options.enable_deduction));
    if (options?.enable_patterns !== undefined)
      params.append('enable_patterns', String(options.enable_patterns));

    const response = await axios.post<UploadResponse>(
      `${API_V2_BASE}/generate-batch?${params.toString()}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  // Upload a project (6–20 files, auto-batched server-side into groups of 5)
  async uploadProject(
    files: File[],
    options?: {
      provider?: 'gemini' | 'openai';
      enable_deduction?: boolean;
      enable_patterns?: boolean;
    }
  ): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));

    const params = new URLSearchParams();
    if (options?.provider) params.append('provider', options.provider);
    if (options?.enable_deduction !== undefined)
      params.append('enable_deduction', String(options.enable_deduction));
    if (options?.enable_patterns !== undefined)
      params.append('enable_patterns', String(options.enable_patterns));

    const response = await axios.post<UploadResponse>(
      `${API_V2_BASE}/generate-project?${params.toString()}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  // Get document info
  async getDocument(docId: string): Promise<DocumentInfo> {
    const response = await axios.get<DocumentInfo>(`${API_V2_BASE}/documents/${docId}`);
    return response.data;
  },

  // Get document chunks
  async getDocumentChunks(docId: string): Promise<DocumentChunk[]> {
    const response = await axios.get<DocumentChunk[]>(
      `${API_V2_BASE}/documents/${docId}/chunks`
    );
    return response.data;
  },

  // Search documents
  async searchDocuments(request: SearchRequest): Promise<SearchResult> {
    const response = await axios.post<SearchResult>(`${API_V2_BASE}/search`, request);
    return response.data;
  },

  async runAgent(
    goal: string,
    context: Record<string, unknown>
  ): Promise<AgentRunResponse> {
    const response = await axios.post<AgentRunResponse>(`${API_V2_BASE}/agent/run`, {
      goal,
      context,
    });
    return response.data;
  },

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await axios.get<{ status: string }>(`${API_V2_BASE}/health`);
    return response.data;
  },

  // Get dashboard data for a document — was `Promise<any>`
  async getDashboardData(docId: string): Promise<DashboardData> {
    try {
      const response = await axios.get<DashboardData>(
        `${API_V2_BASE}/documents/${docId}/dashboard`
      );
      return response.data;
    } catch (error: unknown) {
      const status = (error as { response?: { status?: number } })?.response?.status;

      if (status === 404) {
        try {
          const docInfo = await this.getDocument(docId);
          if (docInfo.document.has_dashboard) {
            // Race condition — retry once
            const retry = await axios.get<DashboardData>(
              `${API_V2_BASE}/documents/${docId}/dashboard`
            );
            return retry.data;
          }
          // Still processing — return a typed placeholder
          return {
            status: docInfo.document.status ?? 'processing',
            kpis: [],
            charts: [],
          };
        } catch {
          return { status: 'processing', kpis: [], charts: [] };
        }
      }
      throw new Error('Failed to fetch dashboard data');
    }
  },

  // Get task/job status for polling — was `Promise<any>`
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await axios.get<TaskStatus>(`${API_V2_BASE}/task/${taskId}`);
    return response.data;
  },
};

// ── WebSocket helper ──────────────────────────────────────────────────────────

export class ProgressWebSocket {
  private ws: WebSocket | null = null;

  connect(taskId: string, onMessage: (data: TaskStatus) => void): void {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001';
    const wsProtocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = apiUrl.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${wsHost}${API_V2_BASE}/ws/${taskId}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onmessage = (event) => {
      const data: TaskStatus = JSON.parse(event.data as string);
      onMessage(data);
    };

    this.ws.onerror = (error) => {
      console.error('[WebSocket] error:', error);
    };

    this.ws.onclose = () => {
      console.log('[WebSocket] closed');
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
