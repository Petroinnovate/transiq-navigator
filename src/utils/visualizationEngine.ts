import type { Widget, StoryBlock, WidgetType, WidgetMeta } from '@/types/widget';

const PALETTE = ['#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6', '#f97316', '#84cc16'];

// ── Metadata extraction ─────────────────────────────────────────────────
function extractMetadata(data: any[], xKey?: string): { numPoints: number; hasTime: boolean; hasCategories: boolean; numSeries: number } {
  if (!Array.isArray(data) || data.length === 0) {
    return { numPoints: 0, hasTime: false, hasCategories: false, numSeries: 0 };
  }
  const sample = data[0];
  const keys = Object.keys(sample || {});
  const TIME_HINTS = ['date', 'month', 'year', 'week', 'quarter', 'period', 'time', 'timestamp', 'day'];
  const hasTime = keys.some(k => TIME_HINTS.some(t => k.toLowerCase().includes(t)));
  const numericKeys = keys.filter(k => k !== xKey && typeof sample[k] === 'number');
  const stringKeys = keys.filter(k => k !== xKey && typeof sample[k] === 'string');
  return {
    numPoints: data.length,
    hasTime,
    hasCategories: stringKeys.length > 0 || data.length <= 8,
    numSeries: numericKeys.length,
  };
}

// ── Smart chart type selection (rule-based) ─────────────────────────────
function selectChartType(meta: ReturnType<typeof extractMetadata>, preferred?: string): WidgetType {
  const VALID: WidgetType[] = ['bar', 'line', 'area', 'pie', 'radar', 'scatter', 'funnel', 'composed'];
  if (preferred && VALID.includes(preferred as WidgetType)) return preferred as WidgetType;
  if (meta.numPoints === 0) return 'bar';
  if (meta.hasTime && meta.numPoints > 3) return meta.numSeries > 1 ? 'area' : 'line';
  if (meta.numPoints <= 5 && meta.hasCategories && meta.numSeries <= 1) return 'pie';
  if (meta.numSeries > 3) return 'radar';
  return 'bar';
}

// ── shouldCallLLM (determines if LLM optimization is worthwhile) ─────────
// In front-end context we simulate this as a rule gate — no external LLM cost.
function shouldOptimize(meta: ReturnType<typeof extractMetadata>, priority: number): boolean {
  // Only bother optimizing high-priority, ambiguous datasets
  if (meta.numPoints === 0) return false;
  const isAmbiguous = meta.hasTime && meta.hasCategories; // could be line OR bar
  const isHighPriority = priority <= 3;
  return isAmbiguous && isHighPriority;
}

// ── Optimized chart type (lightweight LLM-equivalent logic) ──────────────
function optimizeChartType(meta: ReturnType<typeof extractMetadata>, preferred: string): WidgetType {
  if (!shouldOptimize(meta, 1)) return preferred as WidgetType;
  // Time series with categories → prefer area for ≤2 series, line for 1
  if (meta.hasTime) {
    if (meta.numSeries === 1) return 'line';
    if (meta.numSeries === 2) return 'area';
  }
  return preferred as WidgetType;
}

// ── Auto-generate insights (rule-based fallback) ─────────────────────────
function generateInsights(data: any[], yKey?: string): string[] {
  if (!Array.isArray(data) || data.length === 0 || !yKey) return [];
  const values = data.map(d => Number(d[yKey])).filter(v => !isNaN(v));
  if (values.length === 0) return [];

  const max = Math.max(...values);
  const min = Math.min(...values);
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const maxItem = data.find(d => Number(d[yKey]) === max);
  const variance = values.reduce((a, b) => a + (b - avg) ** 2, 0) / values.length;
  const cv = avg !== 0 ? Math.sqrt(variance) / Math.abs(avg) : 0;

  const insights: string[] = [];
  if (maxItem) {
    const nameKey = Object.keys(maxItem).find(k => typeof maxItem[k] === 'string');
    insights.push(`Peak: ${nameKey ? maxItem[nameKey] + ' — ' : ''}${max.toLocaleString()}`);
  }
  if (values.length > 2) {
    const first = values[0], last = values[values.length - 1];
    const trend = last > first ? 'Increasing' : last < first ? 'Decreasing' : 'Stable';
    insights.push(`Trend: ${trend} (${min.toLocaleString()} → ${max.toLocaleString()})`);
  }
  if (cv > 0.3) insights.push(`High variance detected — coefficient of variation: ${(cv * 100).toFixed(0)}%`);

  return insights.slice(0, 3);
}

// ── DMAIC backend chart type → widget type mapping ───────────────────────
const CHART_TYPE_MAP: Record<string, WidgetType> = {
  BarChart: 'bar',
  LineChart: 'line',
  AreaChart: 'area',
  PieChart: 'pie',
  RadarChart: 'radar',
  RadialBarChart: 'radar',
  ScatterChart: 'scatter',
  FunnelChart: 'funnel',
  ComposedChart: 'composed',
  SankeyChart: 'sankey',
};

let _idCounter = 0;
const uid = (prefix: string) => `${prefix}_${++_idCounter}`;

// ── Widget generator contract ────────────────────────────────────────────
export type WidgetGenerator = {
  id: string;
  priority: number; // higher = more important; rendered first
  enabled: (data: any) => boolean;
  generate: (data: any) => Widget | Widget[];
};

const MAX_WIDGETS = 16;

function dedupeWidgets(widgets: Widget[]): Widget[] {
  const seen = new Set<string>();
  const out: Widget[] = [];
  for (const w of widgets) {
    if (!seen.has(w.id)) { seen.add(w.id); out.push(w); }
  }
  return out;
}

function sortByPriority(widgets: Widget[]): Widget[] {
  return [...widgets].sort((a, b) => b.priority - a.priority);
}

// ─────────────────────────────────────────────────────────────────────────
// INDIVIDUAL GENERATORS
// ─────────────────────────────────────────────────────────────────────────

const kpiSummaryGenerator: WidgetGenerator = {
  id: 'kpi-summary',
  priority: 100,
  enabled: (data) => (data.kpis || []).length > 0,
  generate: (data) => {
    // Prefer the AI-assigned widget slot if backend provided it
    const kpis: any[] = data.widgets?.kpi_summary || data.kpis || [];
    const allKpis: any[] = data.kpis || [];
    const pos = allKpis.filter((k: any) => k.changeType === 'positive').length;
    const neg = allKpis.filter((k: any) => k.changeType === 'negative').length;
    const cats = [...new Set(allKpis.map((k: any) => k.category).filter(Boolean))].length;
    const poolSize = data.widgets?.pool_size || allKpis.length;
    return {
      id: 'kpi_summary',
      title: 'Key Metrics Overview',
      type: 'kpi' as const,
      data: kpis.slice(0, 8),
      size: 'large' as const,
      priority: 100,
      insights: [
        `${poolSize} KPIs tracked across ${cats || 1} categories${poolSize > kpis.length ? ` — showing top ${kpis.length}` : ''}`,
        pos > 0 ? `${pos} metrics trending positively` : 'No positive trends detected',
        neg > 0 ? `${neg} metrics require attention` : 'All metrics stable or improving',
      ],
    };
  },
};

const financialImpactGenerator: WidgetGenerator = {
  id: 'financial-impact',
  priority: 90,
  enabled: (data) =>
    ((data.sections || []) as any[])
      .flatMap((s: any) => s.financialImpact?.items || [])
      .filter((i: any) => typeof i.amount === 'number' && i.amount !== 0).length >= 2,
  generate: (data) => {
    const items: any[] = ((data.sections || []) as any[])
      .flatMap((s: any) => s.financialImpact?.items || [])
      .filter((i: any) => typeof i.amount === 'number' && i.amount !== 0);
    const financialData = items.slice(0, 10).map((item: any) => ({
      name: String(item.description || 'Item').slice(0, 22),
      amount: Math.abs(item.amount),
      type: item.type || (item.amount > 0 ? 'benefit' : 'cost'),
    }));
    const totalBenefits = items.filter((i: any) => i.type === 'benefit' || i.amount > 0).reduce((a: number, i: any) => a + Math.abs(i.amount), 0);
    const totalCosts = items.filter((i: any) => i.type === 'cost' || i.amount < 0).reduce((a: number, i: any) => a + Math.abs(i.amount), 0);
    return {
      id: 'financial_impact',
      title: 'Financial Impact Analysis',
      type: 'bar' as const,
      data: financialData,
      size: 'large' as const,
      xKey: 'name',
      yKeys: ['amount'],
      insights: [
        `${items.length} financial items identified`,
        totalBenefits > 0 ? `Potential benefits: ${totalBenefits.toLocaleString()}` : '',
        totalCosts > 0 ? `Estimated costs: ${totalCosts.toLocaleString()}` : '',
      ].filter(Boolean),
      priority: 90,
      meta: { hasCategories: true, numSeries: 1 },
    };
  },
};

const docComparisonGenerator: WidgetGenerator = {
  id: 'doc-comparison',
  priority: 85,
  enabled: (data) => (data.documents || []).length > 1,
  generate: (data) => {
    const documents: any[] = data.documents || [];
    const allKPINames = [
      ...new Set(documents.flatMap((d: any) => (d.kpis || []).map((k: any) => k.name || k.title))),
    ].slice(0, 6) as string[];
    if (allKPINames.length === 0) return [];
    const compData = documents.map((doc: any) => {
      const row: Record<string, any> = { doc: String(doc.filename || doc.title || 'Doc').slice(0, 20) };
      allKPINames.forEach(name => {
        const kpi = (doc.kpis || []).find((k: any) => (k.name || k.title) === name);
        row[name] = kpi ? Number(kpi.value) || 0 : 0;
      });
      return row;
    });
    return {
      id: 'doc_comparison',
      title: 'KPI Comparison Across Documents',
      type: 'bar' as const,
      data: compData,
      size: 'large' as const,
      xKey: 'doc',
      yKeys: allKPINames,
      insights: [`Comparing ${documents.length} documents`, `${allKPINames.length} shared KPIs`],
      priority: 85,
      meta: { hasCategories: true, numSeries: allKPINames.length },
    };
  },
};

const kpiStatusGenerator: WidgetGenerator = {
  id: 'kpi-status',
  priority: 80,
  enabled: (data) => {
    const kpis: any[] = data.kpis || [];
    return kpis.length > 0 && new Set(kpis.map((k: any) => k.changeType || 'neutral')).size > 1;
  },
  generate: (data) => {
    // Use backend widget assignment (which includes hidden KPIs) when available
    const statusMap: Record<string, number> = data.widgets?.kpi_status || {};
    const kpis: any[] = data.kpis || [];
    const statusCounts: Record<string, number> = Object.keys(statusMap).length > 0
      ? statusMap
      : (() => {
          const counts: Record<string, number> = {};
          kpis.forEach((k: any) => { const ct = k.changeType || 'neutral'; counts[ct] = (counts[ct] || 0) + 1; });
          return counts;
        })();
    const total = Object.values(statusCounts).reduce((a, b) => a + b, 0) || 1;
    return {
      id: 'kpi_status',
      title: 'Performance Distribution',
      type: 'pie' as const,
      data: Object.entries(statusCounts).map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value })),
      size: 'medium' as const,
      priority: 80,
      insights: [
        `${statusCounts.positive || statusCounts.good || 0} improving, ${statusCounts.negative || statusCounts.warning || 0} declining, ${statusCounts.neutral || 0} stable`,
        `${Math.round(((statusCounts.positive || statusCounts.good || 0) / total) * 100)}% of metrics trending positively`,
      ],
      meta: { hasCategories: true, numSeries: 1 },
    };
  },
};

const backendChartsGenerator: WidgetGenerator = {
  id: 'backend-charts',
  priority: 70,
  enabled: (data) => (data.charts || []).length > 0,
  generate: (data) => {
    const charts: any[] = data.charts || [];
    return charts.filter(Boolean).map((chart: any, i: number) => {
      const chartData = Array.isArray(chart.data) ? chart.data : [];
      const xKey: string | undefined = chart.chartConfig?.xAxis?.dataKey || chart.chartConfig?.xAxisKey;
      const yKeys: string[] = (chart.chartConfig?.series || []).map((s: any) => s.dataKey).filter(Boolean);
      const preferredType = CHART_TYPE_MAP[chart.type] || 'bar';
      const meta = extractMetadata(chartData, xKey);
      const refinedType = optimizeChartType(meta, selectChartType(meta, preferredType));
      return {
        id: chart.id || uid('chart'),
        title: chart.title || `Chart ${i + 1}`,
        subtitle: chart.subtitle,
        type: refinedType,
        data: chartData,
        size: (chart.size === 'full' ? 'large' : chart.size === 'quarter' ? 'small' : 'medium') as 'large' | 'medium' | 'small',
        xKey,
        yKeys,
        insights: chart.insights?.length > 0 ? chart.insights : generateInsights(chartData, yKeys[0]),
        priority: 70 - i,
        meta: { isTimeSeries: meta.hasTime, hasCategories: meta.hasCategories, numSeries: meta.numSeries },
      } as Widget;
    });
  },
};

const kpiBarGenerator: WidgetGenerator = {
  id: 'kpi-bar',
  priority: 65,
  enabled: (data) => (data.kpis || []).length > 0 && (data.charts || []).length === 0,
  generate: (data) => {
    // Use AI-assigned bar KPIs when available (already filtered for numeric comparability)
    const sourceKpis: any[] = data.widgets?.kpi_bar || data.kpis || [];
    const kpiBarData = sourceKpis
      .filter((k: any) => typeof k.value === 'number' && k.value !== 0)
      .slice(0, 10)
      .map((k: any) => ({ name: String(k.title || k.name || 'KPI').slice(0, 18), value: k.value }));
    if (kpiBarData.length === 0) return [];
    return {
      id: 'kpi_bar',
      title: 'KPI Comparison',
      type: 'bar' as const,
      data: kpiBarData,
      size: 'large' as const,
      xKey: 'name',
      yKeys: ['value'],
      insights: generateInsights(kpiBarData, 'value'),
      priority: 65,
      meta: { hasCategories: true, numSeries: 1 },
    };
  },
};

const kpiCategoryGenerator: WidgetGenerator = {
  id: 'kpi-category',
  priority: 60,
  enabled: (data) => new Set((data.kpis || []).map((k: any) => k.category || 'operational')).size > 1,
  generate: (data) => {
    // Use backend category distribution (includes hidden KPIs) when available
    const catMap: Record<string, number> = data.widgets?.kpi_cat || {};
    const catCounts = Object.keys(catMap).length > 0
      ? catMap
      : (() => {
          const counts: Record<string, number> = {};
          (data.kpis || []).forEach((k: any) => { const c = k.category || 'operational'; counts[c] = (counts[c] || 0) + 1; });
          return counts;
        })();
    return {
      id: 'kpi_cat',
      title: 'KPIs by Category',
      type: 'pie' as const,
      data: Object.entries(catCounts).map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value })),
      size: 'medium' as const,
      priority: 60,
      meta: { hasCategories: true, numSeries: 1 },
    };
  },
};

const riskSeverityGenerator: WidgetGenerator = {
  id: 'risk-severity',
  priority: 55,
  enabled: (data) => ((data.sections || []) as any[]).some((s: any) => (s.risks || []).length > 0),
  generate: (data) => {
    const allRisks: any[] = ((data.sections || []) as any[]).flatMap((s: any) => s.risks || []);
    const sev: Record<string, number> = { high: 0, medium: 0, low: 0 };
    allRisks.forEach((r: any) => { const k = (r.severity || 'medium').toLowerCase(); if (k in sev) sev[k]++; });
    return {
      id: 'risk_severity',
      title: 'Risk Severity Distribution',
      type: 'pie' as const,
      data: [{ name: 'High', value: sev.high }, { name: 'Medium', value: sev.medium }, { name: 'Low', value: sev.low }].filter(d => d.value > 0),
      size: 'medium' as const,
      priority: 55,
      insights: [`${allRisks.length} total risks identified`, `${sev.high} critical risks require immediate attention`],
      meta: { hasCategories: true, numSeries: 1 },
    };
  },
};

const findingsImpactGenerator: WidgetGenerator = {
  id: 'findings-impact',
  priority: 50,
  enabled: (data) => ((data.sections || []) as any[]).some((s: any) => (s.keyFindings || []).length > 0),
  generate: (data) => {
    const sections: any[] = data.sections || [];
    const allFindings: any[] = sections.flatMap((s: any) => s.keyFindings || []);
    const imp: Record<string, number> = { high: 0, medium: 0, low: 0 };
    allFindings.forEach((f: any) => { const k = (f.impact || 'medium').toLowerCase(); if (k in imp) imp[k]++; });
    return {
      id: 'findings_impact',
      title: 'Key Findings by Impact Level',
      type: 'bar' as const,
      data: [{ impact: 'High', count: imp.high }, { impact: 'Medium', count: imp.medium }, { impact: 'Low', count: imp.low }].filter(d => d.count > 0),
      size: 'medium' as const,
      xKey: 'impact',
      yKeys: ['count'],
      insights: [`${allFindings.length} total findings across ${sections.length} sections`, `${imp.high} high-impact findings require priority action`],
      priority: 50,
      meta: { hasCategories: true, numSeries: 1 },
    };
  },
};

const sectionConfidenceGenerator: WidgetGenerator = {
  id: 'section-confidence',
  priority: 45,
  enabled: (data) => ((data.sections || []) as any[]).filter((s: any) => s.confidence != null).length >= 2,
  generate: (data) => {
    const confData = ((data.sections || []) as any[])
      .filter((s: any) => s.confidence != null)
      .slice(0, 12)
      .map((s: any) => ({ name: String(s.title || 'Section').slice(0, 20), confidence: Math.round((s.confidence || 0) * 100) }));
    return {
      id: 'section_conf',
      title: 'Section Analysis Confidence (%)',
      type: 'bar' as const,
      data: confData,
      size: 'large' as const,
      xKey: 'name',
      yKeys: ['confidence'],
      insights: generateInsights(confData, 'confidence'),
      priority: 45,
      meta: { hasCategories: true, numSeries: 1 },
    };
  },
};

const dmaicPhaseGenerator: WidgetGenerator = {
  id: 'dmaic-phase',
  priority: 40,
  enabled: (data) => {
    const counts: Record<string, number> = {};
    ((data.sections || []) as any[]).forEach((s: any) => { const p = s.dmaicPhase; if (p && p !== 'unassigned' && p !== 'none') counts[p] = (counts[p] || 0) + 1; });
    return Object.keys(counts).length >= 2;
  },
  generate: (data) => {
    const phaseCounts: Record<string, number> = {};
    ((data.sections || []) as any[]).forEach((s: any) => { const p = s.dmaicPhase; if (p && p !== 'unassigned' && p !== 'none') phaseCounts[p] = (phaseCounts[p] || 0) + 1; });
    const phaseOrder = ['define', 'measure', 'analyze', 'improve', 'control'];
    const phaseData = phaseOrder.filter(p => phaseCounts[p]).map((p, i) => ({ phase: p.charAt(0).toUpperCase() + p.slice(1), sections: phaseCounts[p], fill: PALETTE[i] }));
    return {
      id: 'dmaic_phase',
      title: 'DMAIC Phase Coverage',
      type: 'bar' as const,
      data: phaseData,
      size: 'medium' as const,
      xKey: 'phase',
      yKeys: ['sections'],
      insights: [`${Object.keys(phaseCounts).length} of 5 DMAIC phases have content`],
      priority: 40,
      meta: { hasCategories: true, numSeries: 1 },
    };
  },
};

const kpiRadarGenerator: WidgetGenerator = {
  id: 'kpi-radar',
  priority: 35,
  enabled: (data) => [...new Set((data.kpis || []).map((k: any) => k.category || 'operational').filter(Boolean))].length >= 3,
  generate: (data) => {
    const kpis: any[] = data.kpis || [];
    const radarCats = [...new Set(kpis.map((k: any) => k.category || 'operational').filter(Boolean))] as string[];
    const maxVals: Record<string, number> = {};
    radarCats.forEach(cat => { maxVals[cat] = Math.max(...kpis.filter((k: any) => (k.category || 'operational') === cat).map((k: any) => Math.abs(Number(k.value) || 0)), 1); });
    const radarData = radarCats.map(cat => {
      const catKpis = kpis.filter((k: any) => (k.category || 'operational') === cat);
      const avg = catKpis.reduce((a: number, k: any) => a + (Math.abs(Number(k.value) || 0) / maxVals[cat]) * 100, 0) / catKpis.length;
      return { category: cat.charAt(0).toUpperCase() + cat.slice(1), score: Math.round(avg) };
    });
    return {
      id: 'kpi_radar',
      title: 'Performance Radar by Category',
      type: 'radar' as const,
      data: radarData,
      size: 'medium' as const,
      xKey: 'category',
      yKeys: ['score'],
      insights: [`${radarCats.length} performance categories`, 'Normalized 0–100 scale'],
      priority: 35,
      meta: { hasCategories: true, numSeries: 1 },
    };
  },
};

const riskExposureGenerator: WidgetGenerator = {
  id: 'risk-exposure',
  priority: 30,
  enabled: (data) => ((data.sections || []) as any[]).filter((s: any) => (s.risks || []).length > 0).length >= 2,
  generate: (data) => {
    const riskPerSection = ((data.sections || []) as any[])
      .filter((s: any) => (s.risks || []).length > 0)
      .slice(0, 10)
      .map((s: any) => ({
        name: String(s.title || 'Section').slice(0, 20),
        risks: (s.risks as any[]).length,
        high: (s.risks as any[]).filter((r: any) => r.severity === 'high').length,
      }));
    const topRisk = [...riskPerSection].sort((a, b) => b.risks - a.risks)[0];
    return {
      id: 'risk_per_section',
      title: 'Risk Exposure by Section',
      type: 'bar' as const,
      data: riskPerSection,
      size: 'large' as const,
      xKey: 'name',
      yKeys: ['risks', 'high'],
      insights: [`"${topRisk?.name}" has highest risk exposure (${topRisk?.risks} risks)`],
      priority: 30,
      meta: { hasCategories: true, numSeries: 2 },
    };
  },
};

const findingConfidenceGenerator: WidgetGenerator = {
  id: 'finding-confidence',
  priority: 25,
  enabled: (data) => ((data.sections || []) as any[]).filter((s: any) => (s.keyFindings || []).length > 0).length >= 2,
  generate: (data) => {
    const confPerSection = ((data.sections || []) as any[])
      .filter((s: any) => (s.keyFindings || []).length > 0)
      .slice(0, 10)
      .map((s: any) => {
        const findings: any[] = s.keyFindings;
        const avgConf = findings.reduce((a: number, f: any) => a + (f.confidence || 0), 0) / findings.length;
        return { name: String(s.title || 'Section').slice(0, 20), confidence: Math.round(avgConf * 100), findings: findings.length };
      })
      .sort((a, b) => a.confidence - b.confidence); // ascending — low confidence visible first
    return {
      id: 'findings_conf',
      title: 'Finding Confidence by Section',
      type: 'composed' as const,
      data: confPerSection,
      size: 'large' as const,
      xKey: 'name',
      yKeys: ['findings', 'confidence'],
      insights: [
        ...generateInsights(confPerSection, 'confidence'),
        confPerSection.some(d => d.confidence < 60) ? 'Sections below 60% confidence need verification' : '',
      ].filter(Boolean),
      priority: 25,
      meta: { hasCategories: true, numSeries: 2 },
    };
  },
};

// ── Sankey helpers ──────────────────────────────────────────────────────────

/** Build {nodes, links} for a sankey from a source→target count map.
 *  Returns null when there isn't at least 1 link. */
function _buildSankey(
  leftLabels: string[],
  rightLabels: string[],
  rawLinks: { source: number; target: number; value: number }[],
  rightSuffix = '',
) {
  if (rawLinks.length < 1) return null;
  const usedLeft  = new Set(rawLinks.map(l => l.source));
  const usedRight = new Set(rawLinks.map(l => l.target - leftLabels.length));
  const activeLeft  = leftLabels.filter((_, i) => usedLeft.has(i));
  const activeRight = rightLabels.filter((_, i) => usedRight.has(i));

  const nodes = [
    ...activeLeft.map(n => ({ name: n })),
    ...activeRight.map(n => ({ name: n + rightSuffix })),
  ];
  const leftRemap:  Record<number, number> = {};
  const rightRemap: Record<number, number> = {};
  activeLeft.forEach((n, ni)  => { leftRemap[leftLabels.indexOf(n)]   = ni; });
  activeRight.forEach((n, ni) => { rightRemap[rightLabels.indexOf(n)] = activeLeft.length + ni; });

  const links = rawLinks
    .filter(l => leftRemap[l.source] !== undefined && rightRemap[l.target - leftLabels.length] !== undefined)
    .map(l => ({ source: leftRemap[l.source], target: rightRemap[l.target - leftLabels.length], value: l.value }));

  return links.length >= 1 ? { nodes, links } : null;
}

const sankeyFlowGenerator: WidgetGenerator = {
  id: 'sankey-flow',
  priority: 33,
  // Enable when ANY of the 3 fallback data sources has usable data
  enabled: (data) => {
    const sections: any[] = data.sections || [];
    const hasSectionFlow =
      sections.some((s: any) => s.dmaicPhase && s.dmaicPhase !== 'unassigned' && s.dmaicPhase !== 'none') &&
      sections.some((s: any) => (s.keyFindings || []).length > 0);
    const opts: any[] = data.optimizationSuggestions || [];
    const hasOptFlow = opts.length >= 2 && opts.some((o: any) => o.category) && opts.some((o: any) => o.impact);
    const kpis: any[] = data.kpis || [];
    const hasKpiFlow = kpis.length >= 3;
    return hasSectionFlow || hasOptFlow || hasKpiFlow;
  },
  generate: (data) => {
    const phases  = ['define', 'measure', 'analyze', 'improve', 'control'];
    const impacts = ['high', 'medium', 'low'];
    const sections: any[] = data.sections || [];

    // ── Tier 1: DMAIC Phase → Finding Impact (from sections) ──────────────
    const sectionLinkMap: Record<string, number> = {};
    sections.forEach((s: any) => {
      const phase = (s.dmaicPhase || '').toLowerCase();
      if (!phases.includes(phase)) return;
      const phaseIdx = phases.indexOf(phase);
      (s.keyFindings || []).forEach((f: any) => {
        const impact = (f.impact || 'medium').toLowerCase();
        if (!impacts.includes(impact)) return;
        const key = `${phaseIdx}-${phases.length + impacts.indexOf(impact)}`;
        sectionLinkMap[key] = (sectionLinkMap[key] || 0) + 1;
      });
    });
    const sectionRawLinks = Object.entries(sectionLinkMap).map(([key, value]) => {
      const [src, tgt] = key.split('-').map(Number);
      return { source: src, target: tgt, value };
    });
    const sectionSankey = _buildSankey(
      phases.map(p => p.charAt(0).toUpperCase() + p.slice(1)),
      impacts.map(i => i.charAt(0).toUpperCase() + i.slice(1)),
      sectionRawLinks,
      ' Impact',
    );
    if (sectionSankey) {
      const totalFindings = sectionSankey.links.reduce((a: number, l: any) => a + l.value, 0);
      return {
        id: 'sankey_flow',
        title: 'DMAIC Phase → Finding Impact Flow',
        type: 'sankey' as const,
        data: sectionSankey as any,
        size: 'large' as const,
        insights: [
          `${totalFindings} findings mapped across ${sectionSankey.nodes.filter((_: any, i: number) => i < phases.length).length} DMAIC phases`,
          'Flow shows how each phase contributes to high / medium / low impact findings',
        ],
        priority: 33,
        meta: { hasCategories: true },
      };
    }

    // ── Tier 2: Optimization Suggestion Category → Impact ─────────────────
    const opts: any[] = data.optimizationSuggestions || [];
    const categories = ['cost', 'efficiency', 'performance', 'risk', 'quality'];
    const optLinkMap: Record<string, number> = {};
    opts.forEach((o: any) => {
      const cat = (o.category || '').toLowerCase();
      const imp = (o.impact || 'medium').toLowerCase();
      if (!impacts.includes(imp)) return;
      const catIdx = categories.includes(cat) ? categories.indexOf(cat) : categories.length;
      const impIdx = categories.length + 1 + impacts.indexOf(imp);
      const key = `${catIdx}-${impIdx}`;
      optLinkMap[key] = (optLinkMap[key] || 0) + 1;
    });
    const allOptCategories = [...categories, 'other'];
    const optRawLinks = Object.entries(optLinkMap).map(([key, value]) => {
      const [src, tgt] = key.split('-').map(Number);
      return { source: src, target: tgt, value };
    });
    const optSankey = _buildSankey(
      allOptCategories.map(c => c.charAt(0).toUpperCase() + c.slice(1)),
      impacts.map(i => i.charAt(0).toUpperCase() + i.slice(1)),
      optRawLinks,
      ' Impact',
    );
    if (optSankey) {
      const totalOpts = optSankey.links.reduce((a: number, l: any) => a + l.value, 0);
      return {
        id: 'sankey_flow',
        title: 'Optimization Category → Impact Flow',
        type: 'sankey' as const,
        data: optSankey as any,
        size: 'large' as const,
        insights: [
          `${totalOpts} optimization opportunities across ${optSankey.nodes.length} nodes`,
          'Shows which improvement categories drive the highest impact',
        ],
        priority: 33,
        meta: { hasCategories: true },
      };
    }

    // ── Tier 3: KPI Category → Trend ──────────────────────────────────────
    const kpis: any[] = data.kpis || [];
    const kpiCategories = ['finance', 'operations', 'safety', 'quality', 'hr', 'other'];
    const trends        = ['positive', 'negative', 'neutral'];
    const kpiLinkMap: Record<string, number> = {};
    kpis.forEach((k: any) => {
      const cat  = (k.category || '').toLowerCase();
      const trend = (k.changeType || k.trend || 'neutral').toLowerCase();
      const catIdx  = kpiCategories.includes(cat) ? kpiCategories.indexOf(cat) : kpiCategories.length - 1;
      const trendIdx = kpiCategories.length + (trends.includes(trend) ? trends.indexOf(trend) : 2);
      const key = `${catIdx}-${trendIdx}`;
      kpiLinkMap[key] = (kpiLinkMap[key] || 0) + 1;
    });
    const kpiRawLinks = Object.entries(kpiLinkMap).map(([key, value]) => {
      const [src, tgt] = key.split('-').map(Number);
      return { source: src, target: tgt, value };
    });
    const kpiSankey = _buildSankey(
      kpiCategories.map(c => c.charAt(0).toUpperCase() + c.slice(1)),
      ['Positive', 'Negative', 'Neutral'],
      kpiRawLinks,
      ' Trend',
    );
    if (kpiSankey) {
      const totalKpis = kpis.length;
      return {
        id: 'sankey_flow',
        title: 'KPI Category → Performance Trend',
        type: 'sankey' as const,
        data: kpiSankey as any,
        size: 'large' as const,
        insights: [
          `${totalKpis} KPIs mapped across ${kpiSankey.nodes.filter((_: any, i: number) => i < kpiCategories.length).length} categories`,
          'Flow shows positive vs negative trends by KPI category',
        ],
        priority: 33,
        meta: { hasCategories: true },
      };
    }

    return [];
  },
};

const sectionChartsGenerator: WidgetGenerator = {
  id: 'section-charts',
  priority: 20,
  enabled: (data) =>
    ((data.sections || []) as any[]).some((s: any) =>
      (s.charts || []).some((c: any) => Array.isArray(c?.data) && c.data.length > 0 && (s.confidence == null || s.confidence >= 0.5))
    ),
  generate: (data) => {
    const out: Widget[] = [];
    ((data.sections || []) as any[]).forEach((section: any) => {
      if (section.confidence != null && section.confidence < 0.5) return; // skip low-confidence sections
      (section.charts || []).forEach((chart: any) => {
        if (!chart || !Array.isArray(chart.data) || chart.data.length === 0) return;
        const xKey: string | undefined = chart.chartConfig?.xAxis?.dataKey || chart.chartConfig?.xAxisKey;
        const yKeys: string[] = (chart.chartConfig?.series || []).map((s: any) => s.dataKey).filter(Boolean);
        const preferredType = CHART_TYPE_MAP[chart.type] || 'bar';
        const meta = extractMetadata(chart.data, xKey);
        const refinedType = optimizeChartType(meta, selectChartType(meta, preferredType));
        out.push({
          id: chart.id ? `sec_${chart.id}` : uid('sec_chart'),
          title: chart.title || `${String(section.title || 'Section').slice(0, 20)} Chart`,
          subtitle: section.title,
          type: refinedType,
          data: chart.data,
          size: chart.size === 'full' ? 'large' : 'medium',
          xKey,
          yKeys,
          insights: chart.insights?.length > 0 ? chart.insights : generateInsights(chart.data, yKeys[0]),
          priority: 20,
          meta: { isTimeSeries: meta.hasTime, hasCategories: meta.hasCategories, numSeries: meta.numSeries },
        });
      });
    });
    return out;
  },
};

// ─────────────────────────────────────────────────────────────────────────
// GENERATOR REGISTRY — add new generators here; order is cosmetic only
// ─────────────────────────────────────────────────────────────────────────
const GENERATORS: WidgetGenerator[] = [
  kpiSummaryGenerator,        // priority 100
  financialImpactGenerator,   // priority 90
  docComparisonGenerator,     // priority 85
  kpiStatusGenerator,         // priority 80
  backendChartsGenerator,     // priority 70
  kpiBarGenerator,            // priority 65 (only when no backend charts)
  kpiCategoryGenerator,       // priority 60
  riskSeverityGenerator,      // priority 55
  findingsImpactGenerator,    // priority 50
  sectionConfidenceGenerator, // priority 45
  dmaicPhaseGenerator,        // priority 40
  kpiRadarGenerator,          // priority 35
  sankeyFlowGenerator,        // priority 33
  riskExposureGenerator,      // priority 30
  findingConfidenceGenerator, // priority 25
  sectionChartsGenerator,     // priority 20
];

// ─────────────────────────────────────────────────────────────────────────
// MAIN ENGINE
// ─────────────────────────────────────────────────────────────────────────
export function generateWidgets(dashboardData: any): Widget[] {
  _idCounter = 0;
  const all: Widget[] = [];

  for (const gen of GENERATORS) {
    try {
      if (!gen.enabled(dashboardData)) continue;
      const result = gen.generate(dashboardData);
      if (Array.isArray(result)) all.push(...result);
      else all.push(result);
    } catch {
      // a single generator failure must never crash the dashboard
    }
  }

  return dedupeWidgets(sortByPriority(all)).slice(0, MAX_WIDGETS);
}

// ── Narrative generator (rule-based, no LLM cost) ───────────────────────
/** Return val only if it is a non-empty string; otherwise return ''. */
function safeStr(val: any): string {
  return typeof val === 'string' && val.length > 0 ? val : '';
}

/**
 * Extract a readable summary string from a DMAIC phase value.
 * Handles both legacy string fields and the new structured agent objects.
 */
function phaseNarrative(phaseVal: any): string {
  if (!phaseVal) return '';
  // Legacy: the phase value is already a plain string
  if (typeof phaseVal === 'string') return phaseVal;
  // New agent schema: object with known summary fields
  if (typeof phaseVal === 'object') {
    return (
      safeStr(phaseVal.problem_statement) ||
      safeStr(phaseVal.goal_statement) ||
      safeStr(phaseVal.fishbone_summary) ||
      safeStr(phaseVal.primary_metric) ||
      safeStr(phaseVal.expected_financial_benefit) ||
      safeStr(phaseVal.measurement_system_adequacy) ||
      // fallback: join the first array field found
      (() => {
        for (const key of Object.keys(phaseVal)) {
          const v = phaseVal[key];
          if (Array.isArray(v) && v.length > 0) {
            const first = v[0];
            if (typeof first === 'string') return first;
            if (first && typeof first === 'object') {
              return safeStr(first.cause || first.action || first.finding || first.kpi || '');
            }
          }
        }
        return '';
      })()
    );
  }
  return '';
}

function generateNarrative(phase: string, widgets: Widget[], dmaic: any, dashboardData: any): string {
  const kpis: any[] = dashboardData.kpis || [];
  const sections: any[] = dashboardData.sections || [];
  const positiveCount = kpis.filter((k: any) => k.changeType === 'positive').length;
  const negativeCount = kpis.filter((k: any) => k.changeType === 'negative').length;

  switch (phase) {
    case 'exec':
      return (
        `This analysis covers ${widgets.length} key visualizations and ${kpis.length} performance metrics. ` +
        (positiveCount > 0 ? `${positiveCount} indicators show positive momentum. ` : '') +
        (negativeCount > 0 ? `${negativeCount} areas require immediate attention.` : 'Overall performance trajectory is stable.')
      );
    case 'define':
      return (
        safeStr(dmaic?.definePhase?.problemStatement) ||
        phaseNarrative(dmaic?.define) ||
        `Problem scope defined across ${sections.length} analyzed document sections. The core issue and business impact have been captured in the analysis below.`
      );
    case 'measure':
      return (
        phaseNarrative(dmaic?.measure) ||
        `Current performance baseline established with ${kpis.length} KPIs. ` +
        `${positiveCount} trending positively, ${negativeCount} requiring intervention. ` +
        `Data quality and measurement system analysis completed.`
      );
    case 'analyze':
      return (
        safeStr(dmaic?.analyzePhase?.keyDriversAndCorrelations) ||
        phaseNarrative(dmaic?.analyze) ||
        `Root cause analysis complete. Key drivers and correlations have been identified. High-variance metrics indicate systemic process variation requiring targeted interventions.`
      );
    case 'improve':
      return (
        safeStr(dmaic?.improvePhase?.optimizationOpportunities) ||
        phaseNarrative(dmaic?.improve) ||
        `Improvement opportunities prioritized by impact and feasibility. Recommended actions target root causes identified in the Analyze phase.`
      );
    case 'control':
      return (
        safeStr(dmaic?.controlPhase?.kpiMonitoringStrategy) ||
        phaseNarrative(dmaic?.control) ||
        `Control mechanisms established to sustain improvements. KPI monitoring cadence and escalation thresholds are defined to prevent regression.`
      );
    default:
      return '';
  }
}

// ── Widget classifier for DMAIC story mapping ────────────────────────────
function classifyWidget(w: Widget): string[] {
  const phases: string[] = [];
  if (w.type === 'kpi' || w.id.includes('kpi_summary') || w.id.includes('kpi_bar')) phases.push('exec', 'measure');
  if (w.id.includes('kpi_status') || w.id.includes('kpi_cat')) phases.push('measure');
  if (w.id.includes('section_conf') || w.id.includes('dmaic_phase') || w.id.includes('conf')) phases.push('analyze');
  if (w.type === 'sankey' || w.id.includes('sankey')) phases.push('analyze');
  if (w.meta?.isTimeSeries || w.type === 'line' || w.type === 'area') phases.push('control');
  if (w.id.includes('doc_comparison') || w.id.includes('compare')) phases.push('improve');
  if (phases.length === 0) phases.push('measure');
  return phases;
}

// ── Story block builder ──────────────────────────────────────────────────
export function mapToStoryBlocks(widgets: Widget[], dashboardData: any): StoryBlock[] {
  const dmaic = (dashboardData as any).dmaicReport;
  const dmaicPhases = (dashboardData as any).sixSigma?.dmaic;
  const dmaicSrc = dmaic || dmaicPhases || null;

  // Build phase → widget map
  const phaseWidgets: Record<string, Widget[]> = {
    exec: [],
    define: [],
    measure: [],
    analyze: [],
    improve: [],
    control: [],
  };

  const used = new Set<string>();

  widgets.forEach(w => {
    const phases = classifyWidget(w);
    phases.forEach(p => {
      if (phaseWidgets[p] && phaseWidgets[p].length < 4 && !used.has(w.id)) {
        phaseWidgets[p].push(w);
        // Don't mark kpi_summary as used — it can appear in exec and measure
        if (p !== 'exec') used.add(w.id);
      }
    });
  });

  const blocks: StoryBlock[] = [
    {
      id: 'exec',
      phase: 'exec',
      title: 'Executive Summary',
      narrative: generateNarrative('exec', widgets, dmaicSrc, dashboardData),
      widgets: phaseWidgets.exec,
      priority: 1,
      icon: 'activity',
    },
    {
      id: 'define',
      phase: 'define',
      title: 'Define — Problem Statement',
      narrative: generateNarrative('define', widgets, dmaicSrc, dashboardData),
      widgets: phaseWidgets.define,
      priority: 2,
      icon: 'target',
    },
    {
      id: 'measure',
      phase: 'measure',
      title: 'Measure — Current Performance',
      narrative: generateNarrative('measure', widgets, dmaicSrc, dashboardData),
      widgets: phaseWidgets.measure,
      priority: 3,
      icon: 'bar-chart',
    },
    {
      id: 'analyze',
      phase: 'analyze',
      title: 'Analyze — Root Cause Analysis',
      narrative: generateNarrative('analyze', widgets, dmaicSrc, dashboardData),
      widgets: phaseWidgets.analyze,
      priority: 4,
      icon: 'search',
    },
    {
      id: 'improve',
      phase: 'improve',
      title: 'Improve — Recommendations',
      narrative: generateNarrative('improve', widgets, dmaicSrc, dashboardData),
      widgets: phaseWidgets.improve,
      priority: 5,
      icon: 'trending-up',
    },
    {
      id: 'control',
      phase: 'control',
      title: 'Control — Monitoring Plan',
      narrative: generateNarrative('control', widgets, dmaicSrc, dashboardData),
      widgets: phaseWidgets.control,
      priority: 6,
      icon: 'shield',
    },
  ];

  // Only emit blocks that have a narrative OR widgets
  return blocks.filter(b => b.narrative.length > 0 || b.widgets.length > 0);
}

// ── Widget → ChartData adapter (used by ChartRenderer) ──────────────────
export function widgetToChartConfig(widget: Widget) {
  // Sankey needs its own data shape — bypass normal series detection
  if (widget.type === 'sankey') {
    return {
      id: widget.id,
      type: 'SankeyChart' as any,
      title: widget.title,
      subtitle: widget.subtitle,
      size: widget.size === 'large' ? 'full' : widget.size === 'small' ? 'quarter' : 'half',
      chartConfig: { series: [] },
      data: widget.data,
      insights: widget.insights,
    };
  }

  const WIDGET_TO_CHART: Record<string, string> = {
    bar: 'BarChart',
    line: 'LineChart',
    area: 'AreaChart',
    pie: 'PieChart',
    radar: 'RadarChart',
    scatter: 'ScatterChart',
    funnel: 'FunnelChart',
    composed: 'ComposedChart',
    sankey: 'SankeyChart',
    kpi: 'BarChart', // fallback (kpi handled separately)
  };

  const chartType = WIDGET_TO_CHART[widget.type] || 'BarChart';

  // Auto-detect series from data if yKeys not specified
  const sample = Array.isArray(widget.data) && widget.data.length > 0 ? widget.data[0] : null;
  let yKeys = widget.yKeys || [];
  if (yKeys.length === 0 && sample) {
    const numericKeys = Object.keys(sample).filter(
      k => k !== widget.xKey && typeof sample[k] === 'number'
    );
    yKeys = numericKeys.length > 0 ? numericKeys : Object.keys(sample).filter(k => k !== widget.xKey);
  }

  // Auto-detect xKey
  let xKey = widget.xKey;
  if (!xKey && sample) {
    xKey = Object.keys(sample).find(k => typeof sample[k] === 'string') || Object.keys(sample)[0];
  }

  const series = yKeys.map((key, i) => ({
    dataKey: key,
    name: key,
    type: 'bar' as const,
    color: PALETTE[i % PALETTE.length],
  }));

  return {
    id: widget.id,
    type: chartType as any,
    title: widget.title,
    subtitle: widget.subtitle,
    size: widget.size === 'large' ? 'full' : widget.size === 'small' ? 'quarter' : 'half',
    chartConfig: {
      xAxis: xKey ? { dataKey: xKey, label: xKey, type: 'category' as const } : undefined,
      series,
    },
    data: widget.data,
    insights: widget.insights,
  };
}
