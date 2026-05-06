// ============================================================================
// Intelligence / Impact Analysis API Client
// Endpoints: /api/v2/intelligence/*
// ============================================================================

import axios from '@/lib/axios';

const BASE = '/api/v2/intelligence';

// ── Types ───────────────────────────────────────────────────────────────────

export interface EnrichedFact {
  subject: string;
  predicate: string;
  object: string;
  confidence: number;
  entity_type?: string;
}

export interface FactEnrichmentResult {
  enriched_facts: EnrichedFact[];
  entities: Array<{ name: string; type: string }>;
  relationships: Array<{ source: string; target: string; type: string }>;
  entity_count: number;
  relationship_count: number;
}

export interface ImpactPath {
  source: string;
  target: string;
  impact_type: string;
  strength: number;
  path: string[];
}

export interface KPIImpactResult {
  impact_paths: ImpactPath[];
  affected_entities: Array<{ name: string; type: string; impact_level: string }>;
  financial_summary: Record<string, unknown>;
  recommendations: string[];
}

export interface DMAICPhase {
  title: string;
  description: string;
  findings: string[];
  metrics?: Record<string, unknown>;
}

export interface DMAICResult {
  define_phase: DMAICPhase;
  measure_phase: DMAICPhase;
  analyze_phase: DMAICPhase;
  improve_phase: DMAICPhase;
  control_phase: DMAICPhase;
  summary: string;
}

export interface Recommendation {
  engine: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  action: string;
  impact_estimate: string;
  timeline: string;
}

export interface RecommendationsResult {
  primary_entity_id: string;
  recommendations: Recommendation[];
  portfolio_summary: Record<string, unknown>;
  next_steps: string[];
}

export interface ScenarioResult {
  scenario: string;
  baseline: Record<string, unknown>;
  projected_outcomes: Record<string, unknown>;
  key_changes: Array<{ metric: string; before: unknown; after: unknown; delta: string }>;
  recommendations: string[];
}

// ── API Functions ───────────────────────────────────────────────────────────

export const enrichFacts = async (
  facts: Array<{ subject: string; predicate: string; object: string; confidence: number }>
): Promise<FactEnrichmentResult> => {
  const { data } = await axios.post<FactEnrichmentResult>(`${BASE}/enrich-facts`, { facts });
  return data;
};

export const analyzeKPIImpact = async (params: {
  kpi_name: string;
  kpi_type: string;
  entities: Array<{ name: string; type: string }>;
  relationships: Array<{ source: string; target: string; type: string }>;
  financial_impact_usd?: number;
}): Promise<KPIImpactResult> => {
  const { data } = await axios.post<KPIImpactResult>(`${BASE}/analyze-kpi-impact`, params);
  return data;
};

export const getDMAIC = async (kpiId: string): Promise<DMAICResult> => {
  const { data } = await axios.get<DMAICResult>(`${BASE}/dmaic/${kpiId}`);
  return data;
};

export const getRecommendations = async (
  entityId: string,
  sortBy: 'priority' | 'impact' = 'priority'
): Promise<RecommendationsResult> => {
  const { data } = await axios.get<RecommendationsResult>(
    `${BASE}/unified-recommendations/${entityId}`,
    { params: { sort_by: sortBy } }
  );
  return data;
};

export const getScenario = async (
  entityId: string,
  scenarioType?: string
): Promise<ScenarioResult> => {
  const { data } = await axios.get<ScenarioResult>(
    `${BASE}/scenario/${entityId}`,
    { params: { scenario_type: scenarioType } }
  );
  return data;
};

// ── Intelligence Dashboard & Impact Network ─────────────────────────────────

export interface DashboardSummary {
  kpi_id: string;
  kpi_name: string;
  total_impact: number;
  direct_impact: number;
  cascading_impact: number;
  affected_entities_count: number;
  confidence_score: number;
  primary_drivers: string[];
  affected_departments: string[];
  timestamp: string;
}

export interface ImpactNode {
  id: string;
  label: string;
  type: string;
  value: number;
  color: string;
  size: number;
  metadata: Record<string, unknown>;
}

export interface ImpactEdge {
  source: string;
  target: string;
  weight: number;
  type: string;
  label: string;
  metadata: Record<string, unknown>;
}

export interface ImpactNetworkResult {
  nodes: ImpactNode[];
  edges: ImpactEdge[];
  metadata: Record<string, unknown>;
  stats: Record<string, unknown>;
}

export const getIntelligenceDashboard = async (
  kpiId: string
): Promise<DashboardSummary> => {
  const { data } = await axios.get<DashboardSummary>(`${BASE}/dashboard/${kpiId}`);
  return data;
};

export const getImpactNetwork = async (
  kpiId: string,
  maxDepth = 3
): Promise<ImpactNetworkResult> => {
  const { data } = await axios.get<ImpactNetworkResult>(
    `${BASE}/impact-network/${kpiId}`,
    { params: { max_depth: maxDepth } }
  );
  return data;
};
