import { describe, it, expect } from 'vitest';
import React from 'react';

// ============================================================================
// Page Component Render Tests
// Validates that all page components can be imported without errors
// ============================================================================

describe('Page Components — Import Validation', () => {
  it('Observability page imports without errors', async () => {
    const mod = await import('@/pages/Observability');
    expect(mod.default).toBeDefined();
  });

  it('IntelligenceHub page imports without errors', async () => {
    const mod = await import('@/pages/IntelligenceHub');
    expect(mod.default).toBeDefined();
  });

  it('GraphExplorer page imports without errors', async () => {
    const mod = await import('@/pages/GraphExplorer');
    expect(mod.default).toBeDefined();
  });

  it('Auth page imports without errors', async () => {
    const mod = await import('@/pages/Auth');
    expect(mod.default).toBeDefined();
  });

  it('Upload page imports without errors', async () => {
    const mod = await import('@/pages/Upload');
    expect(mod.default).toBeDefined();
  });

  it('Dashboard page imports without errors', async () => {
    const mod = await import('@/pages/Dashboard');
    expect(mod.default).toBeDefined();
  });

  it('Search page imports without errors', async () => {
    const mod = await import('@/pages/Search');
    expect(mod.default).toBeDefined();
  });

  it('AgentLab page imports without errors', async () => {
    const mod = await import('@/pages/AgentLab');
    expect(mod.default).toBeDefined();
  });

  it('UserProfile page imports without errors', async () => {
    const mod = await import('@/pages/UserProfile');
    expect(mod.default).toBeDefined();
  });
});

describe('App — Route Configuration', () => {
  it('App component imports and exports default', async () => {
    const mod = await import('@/App');
    expect(mod.default).toBeDefined();
  });
});
