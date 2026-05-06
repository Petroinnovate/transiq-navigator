// ============================================================================
// Six Sigma API Client
// Endpoints: /api/v2/six-sigma/*
// ============================================================================

import axios from '@/lib/axios';

const BASE = '/api/v2/six-sigma';

// ── Types ───────────────────────────────────────────────────────────────────

export interface SixSigmaAnalyzeRequest {
  data: number[];
  usl: number;
  lsl: number;
  sigma?: number | null;
  ppm?: number | null;
}

export interface MetricsBlock {
  n: number;
  mean: number;
  std_dev: number;
  cp: number;
  cpk: number;
  cpu: number;
  cpl: number;
  sigma_short_term: number;
  sigma_long_term: number;
  dpmo: number;
  yield_pct: number;
  fraction_defective: number;
  sigma_level: number | null;
}

export interface ChartDataBlock {
  values: number[];
  cl: number;
  ucl: number;
  lcl: number;
  mr_cl: number;
  mr_ucl: number;
  usl: number;
  lsl: number;
}

export interface RuleViolation {
  rule: string;
  description: string;
  indices: number[];
  severity: string;
}

export interface SixSigmaAnalyzeResponse {
  analysis_type: string;
  inputs: Record<string, unknown>;
  metrics: MetricsBlock;
  chart_data: ChartDataBlock;
  warnings: RuleViolation[];
  recommendations: string[];
}

// ── API Functions ───────────────────────────────────────────────────────────

export const analyzeSixSigma = async (
  params: SixSigmaAnalyzeRequest
): Promise<SixSigmaAnalyzeResponse> => {
  const { data } = await axios.post<SixSigmaAnalyzeResponse>(`${BASE}/analyze`, params);
  return data;
};
