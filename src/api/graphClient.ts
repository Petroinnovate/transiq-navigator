// ============================================================================
// GraphRAG API Client
// Endpoints: /api/v2/graph/*
// ============================================================================

import axios from '@/lib/axios';

const BASE = '/api/v2/graph';

// ── Types ───────────────────────────────────────────────────────────────────

export interface GraphEntity {
  entity_id: string;
  name: string;
  entity_type: string;
  mention_count: number;
  pagerank?: number;
  betweenness?: number;
  doc_id?: string;
}

export interface EntityDetail extends GraphEntity {
  mentions: Array<{ text: string; context: string; doc_id: string }>;
  relationships: GraphRelationship[];
}

export interface GraphRelationship {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: string;
  confidence: number;
  impact_type?: string;
  source_name?: string;
  target_name?: string;
}

export interface PathResult {
  path: GraphEntity[];
  length: number;
  hops: Array<{ from: string; to: string; relationship: string }>;
}

export interface CentralityResult {
  metric: 'degree' | 'closeness' | 'betweenness';
  results: Array<{ entity: GraphEntity; score: number }>;
}

export interface EntitySearchResult {
  query: string;
  results: GraphEntity[];
  count: number;
}

export interface RelationshipSearchResult {
  results: GraphRelationship[];
  count: number;
}

// ── API Functions ───────────────────────────────────────────────────────────

export const searchEntities = async (
  query: string,
  entityType?: string,
  limit = 20
): Promise<EntitySearchResult> => {
  const { data } = await axios.post<EntitySearchResult>(`${BASE}/entities/search`, {
    query,
    entity_type: entityType,
    limit,
  });
  return data;
};

export const getEntity = async (entityId: string): Promise<EntityDetail> => {
  const { data } = await axios.get<EntityDetail>(`${BASE}/entities/${entityId}`);
  return data;
};

export const listEntities = async (
  entityType?: string,
  minMentions?: number,
  limit = 50
): Promise<{ entities: GraphEntity[]; count: number }> => {
  const { data } = await axios.post(`${BASE}/entities/list`, {
    entity_type: entityType,
    min_mentions: minMentions,
    limit,
  });
  return data;
};

export const getRelatedEntities = async (
  entityId: string
): Promise<{ entity_id: string; related: GraphEntity[]; depth: number }> => {
  const { data } = await axios.get(`${BASE}/entities/${entityId}/related`);
  return data;
};

export const searchRelationships = async (
  query: string,
  limit = 20
): Promise<RelationshipSearchResult> => {
  const { data } = await axios.post<RelationshipSearchResult>(`${BASE}/relationships/search`, {
    query,
    limit,
  });
  return data;
};

export const getRelationships = async (
  entityId: string
): Promise<{ entity_id: string; relationships: GraphRelationship[] }> => {
  const { data } = await axios.get(`${BASE}/relationships/${entityId}`);
  return data;
};

export const findPaths = async (
  sourceId: string,
  targetId: string,
  maxDepth = 4
): Promise<PathResult> => {
  const { data } = await axios.post<PathResult>(`${BASE}/paths`, {
    source_entity_id: sourceId,
    target_entity_id: targetId,
    max_depth: maxDepth,
  });
  return data;
};

export const getCentrality = async (
  metric: 'degree' | 'closeness' | 'betweenness' = 'degree',
  limit = 20
): Promise<CentralityResult> => {
  const { data } = await axios.post<CentralityResult>(`${BASE}/analytics/centrality`, {
    metric,
    limit,
  });
  return data;
};
