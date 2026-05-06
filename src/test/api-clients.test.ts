import { describe, it, expect, vi, beforeEach } from 'vitest';

// ============================================================================
// API Client Integration Tests
// Validates that all API client files export the expected functions
// ============================================================================

describe('API Clients — Export Validation', () => {

  it('observabilityClient exports all 5 functions', async () => {
    const mod = await import('@/api/observabilityClient');
    expect(typeof mod.fetchSystemHealth).toBe('function');
    expect(typeof mod.fetchModelRegistry).toBe('function');
    expect(typeof mod.fetchFeatureStore).toBe('function');
    expect(typeof mod.fetchPredictions).toBe('function');
    expect(typeof mod.fetchDriftStatus).toBe('function');
  });

  it('graphClient exports all 8 functions', async () => {
    const mod = await import('@/api/graphClient');
    expect(typeof mod.searchEntities).toBe('function');
    expect(typeof mod.getEntity).toBe('function');
    expect(typeof mod.listEntities).toBe('function');
    expect(typeof mod.getRelatedEntities).toBe('function');
    expect(typeof mod.searchRelationships).toBe('function');
    expect(typeof mod.getRelationships).toBe('function');
    expect(typeof mod.findPaths).toBe('function');
    expect(typeof mod.getCentrality).toBe('function');
  });

  it('intelligenceClient exports all 5 functions', async () => {
    const mod = await import('@/api/intelligenceClient');
    expect(typeof mod.enrichFacts).toBe('function');
    expect(typeof mod.analyzeKPIImpact).toBe('function');
    expect(typeof mod.getDMAIC).toBe('function');
    expect(typeof mod.getRecommendations).toBe('function');
    expect(typeof mod.getScenario).toBe('function');
  });

  it('ddrClient exports fleet functions', async () => {
    const mod = await import('@/api/ddrClient');
    expect(typeof mod.fetchFleetSummary).toBe('function');
    expect(typeof mod.fetchFleetNPTPareto).toBe('function');
    expect(typeof mod.fetchFleetSPC).toBe('function');
    expect(typeof mod.fetchFleetTopPerformers).toBe('function');
    expect(typeof mod.fetchFleetHeatmap).toBe('function');
    expect(typeof mod.fetchFleetTrends).toBe('function');
  });

  it('dashboardApi exports all dashboard functions', async () => {
    const mod = await import('@/api/dashboardApi');
    expect(typeof mod.fetchDashboardData).toBe('function');
    expect(typeof mod.fetchLatestDashboard).toBe('function');
    expect(typeof mod.exportDashboardPDF).toBe('function');
    expect(typeof mod.exportDashboardExcel).toBe('function');
  });
});

describe('Main API service — methods', () => {
  it('api.ts exports all core methods', async () => {
    const mod = await import('@/services/api');
    const { api } = mod;
    expect(typeof api.uploadDocument).toBe('function');
    expect(typeof api.uploadDocuments).toBe('function');
    expect(typeof api.uploadProject).toBe('function');
    expect(typeof api.getDocument).toBe('function');
    expect(typeof api.getDocumentChunks).toBe('function');
    expect(typeof api.searchDocuments).toBe('function');
    expect(typeof api.runAgent).toBe('function');
    expect(typeof api.healthCheck).toBe('function');
    expect(typeof api.getTaskStatus).toBe('function');
    expect(typeof api.getBatchStatus).toBe('function');
    expect(typeof api.getDashboardData).toBe('function');
  });
});

describe('Hooks — Export Validation', () => {
  it('usePolling exports batch + drift hooks', async () => {
    const mod = await import('@/hooks/usePolling');
    expect(typeof mod.useBatchPolling).toBe('function');
    expect(typeof mod.useDriftAlerts).toBe('function');
  });
});
