import axios from '@/lib/axios';

const API_V2_BASE = '/api/v2';

export interface UploadResponse {
  doc_id: string;
  task_id: string;
  status: 'processing' | 'completed' | 'failed';
  message: string;
  dashboard?: DashboardData;
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

export interface BatchStatus {
  batch_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  total_files: number;
  completed_files: number;
  failed_files: number;
  progress: number;
  documents: Array<{
    doc_id: string;
    task_id: string;
    file_name: string;
    status: string;
  }>;
}

// Dashboard types
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
  [key: string]: unknown;
}

export const api = {
  // Upload document
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
    if (options?.enable_deduction !== undefined) {
      params.append('enable_deduction', String(options.enable_deduction));
    }
    if (options?.enable_patterns !== undefined) {
      params.append('enable_patterns', String(options.enable_patterns));
    }
    
    const response = await axios.post<UploadResponse>(
      `${API_V2_BASE}/generate?${params.toString()}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
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
    if (options?.enable_deduction !== undefined) {
      params.append('enable_deduction', String(options.enable_deduction));
    }
    if (options?.enable_patterns !== undefined) {
      params.append('enable_patterns', String(options.enable_patterns));
    }

    const response = await axios.post<UploadResponse>(
      `${API_V2_BASE}/generate-batch?${params.toString()}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  // Upload a project (6–20 files, auto-batched via generate-batch)
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
    if (options?.enable_deduction !== undefined) {
      params.append('enable_deduction', String(options.enable_deduction));
    }
    if (options?.enable_patterns !== undefined) {
      params.append('enable_patterns', String(options.enable_patterns));
    }

    const response = await axios.post<UploadResponse>(
      `${API_V2_BASE}/generate-batch?${params.toString()}`,
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
    const response = await axios.get<DocumentChunk[]>(`${API_V2_BASE}/documents/${docId}/chunks`);
    return response.data;
  },
  
  // Search documents
  async searchDocuments(request: SearchRequest): Promise<SearchResult> {
    const response = await axios.post<SearchResult>(`${API_V2_BASE}/search`, request);
    return response.data;
  },

  async runAgent(goal: string, context: Record<string, unknown>): Promise<AgentRunResponse> {
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

  // Get dashboard data for a document
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

  // Get task/job status for polling
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await axios.get<TaskStatus>(`${API_V2_BASE}/task/${taskId}`);
    return response.data;
  },

  // Get batch processing status
  async getBatchStatus(batchId: string): Promise<BatchStatus> {
    const response = await axios.get<BatchStatus>(`${API_V2_BASE}/batch/${batchId}`);
    return response.data;
  },
};

// ---------------------------------------------------------------------------
// SSE Dashboard Streaming
// ---------------------------------------------------------------------------

export interface DashboardStreamEvent {
  stage: 'context_ready' | 'kpis' | 'charts' | 'insights' | 'sixSigma' | 'complete' | 'error';
  data?: Record<string, any>;
  error?: string;
}

/**
 * Connect to the dashboard SSE stream.  Calls ``onEvent`` for each
 * stage as it arrives and returns a close function.
 *
 * Usage:
 * ```ts
 * const close = streamDashboard(docId, (event) => {
 *   if (event.stage === 'kpis') setKpis(event.data.kpis);
 *   if (event.stage === 'complete') close();
 * });
 * ```
 */
export function streamDashboard(
  docId: string,
  onEvent: (event: DashboardStreamEvent) => void,
  onError?: (err: Event) => void,
): () => void {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const url = `${apiUrl}${API_V2_BASE}/documents/${docId}/dashboard/stream`;

  const es = new EventSource(url);

  es.onmessage = (msg) => {
    try {
      const event: DashboardStreamEvent = JSON.parse(msg.data);
      onEvent(event);
      if (event.stage === 'complete' || event.stage === 'error') {
        es.close();
      }
    } catch (err) {
      console.error('[SSE] Parse error:', err);
    }
  };

  es.onerror = (err) => {
    console.error('[SSE] Connection error:', err);
    if (onError) onError(err);
    es.close();
  };

  return () => es.close();
}

// WebSocket helper
export class ProgressWebSocket {
  private ws: WebSocket | null = null;
  
  connect(taskId: string, onMessage: (data: TaskStatus) => void) {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001';
    const wsProtocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = apiUrl.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${wsHost}${API_V2_BASE}/ws/${taskId}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onmessage = (event) => {
      const data: TaskStatus = JSON.parse(event.data);
      onMessage(data);
    };
    
    this.ws.onerror = (error) => {
      console.error('[WebSocket] error:', error);
    };
    
    this.ws.onclose = () => {
      console.log('[WebSocket] closed');
    };
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

