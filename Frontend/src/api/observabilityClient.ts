// ============================================================================
// Observability API Client
// Endpoints: /api/v2/observability/*
// ============================================================================

import axios from '@/lib/axios';

const BASE = '/api/v2/observability';

// ── Types ───────────────────────────────────────────────────────────────────

export interface SystemHealth {
  status: string;
  timestamp: string;
  checks: {
    database: { status: string; latency_ms?: number };
    redis: { status: string; latency_ms?: number };
    celery: { status: string; workers?: number };
    model_registry: { status: string; models_count?: number };
    feature_store: { status: string; features_count?: number };
  };
}

export interface ModelInfo {
  model_id: string;
  name: string;
  version: string;
  stage: string;
  metrics: Record<string, number>;
  created_at: string;
  tags: Record<string, string>;
}

export interface ModelRegistry {
  total: number;
  models: ModelInfo[];
}

export interface FeatureInfo {
  name: string;
  version: string;
  columns: string[];
  row_count: number;
  stale: boolean;
  created_at: string;
  staleness_hours: number;
}

export interface FeatureStore {
  total: number;
  stale_count: number;
  features: FeatureInfo[];
}

export interface PredictionRecord {
  id: string;
  model_id: string;
  input_hash: string;
  output: Record<string, unknown>;
  confidence: number;
  latency_ms: number;
  timestamp: string;
}

export interface PredictionStats {
  count: number;
  stats: {
    avg_latency_ms: number;
    p95_latency_ms: number;
    max_latency_ms: number;
    avg_confidence: number;
    low_confidence_pct: number;
  };
  recent: PredictionRecord[];
}

export interface DriftAlert {
  metric: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: string;
}

export interface DriftStatus {
  timestamp: string;
  data_drift: Record<string, unknown>;
  model_drift: Record<string, unknown>;
  alerts: DriftAlert[];
}

// ── API Functions ───────────────────────────────────────────────────────────

export const fetchSystemHealth = async (): Promise<SystemHealth> => {
  const { data } = await axios.get<SystemHealth>(`${BASE}/health`);
  return data;
};

export const fetchModelRegistry = async (): Promise<ModelRegistry> => {
  const { data } = await axios.get<ModelRegistry>(`${BASE}/models`);
  return data;
};

export const fetchFeatureStore = async (): Promise<FeatureStore> => {
  const { data } = await axios.get<FeatureStore>(`${BASE}/features`);
  return data;
};

export const fetchPredictions = async (limit = 100): Promise<PredictionStats> => {
  const { data } = await axios.get<PredictionStats>(`${BASE}/predictions`, {
    params: { limit },
  });
  return data;
};

export const fetchDriftStatus = async (): Promise<DriftStatus> => {
  const { data } = await axios.get<DriftStatus>(`${BASE}/drift`);
  return data;
};
