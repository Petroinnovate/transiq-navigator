
import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Download, RefreshCw, Plus, Activity, BarChart3, Sigma, Lightbulb, Zap, Database, ChevronDown, ChevronUp, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, XCircle, FileText, BookOpen, Shield, Brain } from 'lucide-react';
import KPICard from './KPICard';
import ChartRenderer from './ChartRenderer';
import DataTable from './DataTable';
import OptimizationSuggestions from './OptimizationSuggestions';
import DCIRecommendationCard from './DCIRecommendationCard';
import InsightsSection from './InsightsSection';
import SixSigmaSection from './SixSigmaSection';
import SixSigmaAnalyzer from './SixSigmaAnalyzer';
import SectionNav from './SectionNav';
import SectionDetail from './SectionDetail';
import QualityScoreCard from './QualityScoreCard';
import DmaicCompilerPanel from './DmaicCompilerPanel';
import { exportDashboardToPDF } from '@/utils/pdfExport';
import { AlertCallouts } from '@/components/tremor-widgets/AlertCallouts';
import ProjectBanner from './ProjectBanner';
import ViewModeToggle, { ViewMode } from './ViewModeToggle';
import KPIComparisonTable from './KPIComparisonTable';
import DocumentTabs from './DocumentTabs';
import BenchmarkTable from './BenchmarkTable';
import StorySection from './StorySection';
import { generateWidgets, mapToStoryBlocks } from '@/utils/visualizationEngine';
import { useDashboard } from '@/contexts/DashboardContext';
import ProgressiveDisclosureView from './progressive/ProgressiveDisclosureView';
import AlertPanel from './AlertPanel';
import PredictiveDashboard from './predictive/PredictiveDashboard';
import WhatIfSimulator from './predictive/WhatIfSimulator';
import EntityIntelligenceTab from './intelligence/EntityIntelligenceTab';

interface DashboardProps {
  dashboardData: {
    title: string;
    description: string;
    generatedAt?: string;
    confidence?: number;
    sixSigma?: {
      dmaic: {
        define: string;
        measure: string;
        analyze: string;
        improve: string;
        control: string;
      };
      sigmaLevel: string;
      defectRate: string;
      processCapability: 'Low' | 'Medium' | 'High';
      rootCauses: string[];
    };
    kpis: Array<{
      id: string;
      title: string;
      value: number;
      unit: string;
      change: string;
      changeType: 'positive' | 'negative' | 'neutral';
      icon: string;
      color: string;
      sparkData?: Array<{ v: number }>;
      category?: 'financial' | 'customer' | 'operational' | 'team' | string;
      status?: 'good' | 'warning' | 'critical';
      target?: number;
      // AI scoring fields
      priorityScore?: number;
      visibility?: 'primary' | 'secondary' | 'hidden';
      selectionReason?: string;
    }>;
    // AI widget assignments from kpi_engine
    widgets?: {
      kpi_summary?: Array<any>;
      kpi_bar?: Array<any>;
      kpi_status?: Record<string, number>;
      kpi_cat?: Record<string, number>;
      alerts?: Array<any>;
      pool_size?: number;
      primary_count?: number;
      secondary_count?: number;
      hidden_count?: number;
    };
    predictive?: Array<{
      metric: string;
      forecastValue: number;
      unit: string;
      period: string;
      confidence: number;
      trend: 'up' | 'down' | 'stable';
    }>;
    charts: Array<{
      id: string;
      type: 'AreaChart' | 'BarChart' | 'LineChart' | 'ComposedChart' | 'PieChart' | 'RadarChart' | 'RadialBarChart' | 'ScatterChart' | 'FunnelChart' | 'SankeyChart';
      title: string;
      subtitle?: string;
      size: 'full' | 'half' | 'third' | 'quarter';
      chartConfig: {
        xAxis?: { dataKey: string; label: string; type: 'category' | 'number' | 'time'; };
        yAxis?: { label: string; domain: [string | number, string | number]; };
        series?: Array<{ dataKey: string; name: string; type: 'bar' | 'line' | 'area'; color?: string; fill?: string; stroke?: string; }>;
        composedComponents?: Array<{ type: 'Bar' | 'Line' | 'Area'; dataKey: string; name: string; color?: string; fill?: string; stroke?: string; }>;
      };
      data: Array<Record<string, any>>;
      insights?: string[];
    }>;
    tables: Array<{
      id: string;
      title: string;
      columns: Array<{ key: string; label: string; type: string; format?: string; }>;
      data: Array<Record<string, any>>;
      pagination: boolean;
      sortable: boolean;
    }>;
    optimizationSuggestions?: Array<{
      id: string;
      title: string;
      category: 'cost' | 'efficiency' | 'performance' | 'risk' | 'quality';
      impact: 'high' | 'medium' | 'low';
      savings: { value: number; unit: string; percentage: string; timeframe: string; };
      description: string;
      implementation: string;
      metrics: string[];
      priority: 'high' | 'medium' | 'low';
      confidence: 'high' | 'medium' | 'low';
      tags: string[];
      actionable: boolean;
      color: string;
    }>;
    insights?: {
      summary: string;
      trends: string[];
      alerts: Array<{ type: 'warning' | 'error' | 'info' | 'success'; message: string; severity: 'high' | 'medium' | 'low'; action: string; }>;
      recommendations: string[];
    };
    sections?: Array<{
      sectionId: string;
      title: string;
      pageRange?: string;
      summary: string;
      keyFindings: Array<{ finding: string; impact: 'high' | 'medium' | 'low'; confidence: number }>;
      kpis: Array<any>;
      risks: Array<{ risk: string; severity: 'high' | 'medium' | 'low'; probability?: 'high' | 'medium' | 'low' }>;
      recommendations: string[];
      financialImpact?: { identified?: boolean; items?: Array<{ description: string; amount?: number; unit?: string; type?: string }> };
      charts: Array<any>;
      confidence: number;
      tier?: 1 | 2 | 3;
      dmaicPhase?: string;
      modelUsed?: 'cheap' | 'balanced' | 'powerful';
    }>;
  };
  onRefresh?: () => void;
}

const DashboardRenderer = ({ dashboardData, onRefresh }: DashboardProps) => {
  // Guard: if called with undefined/null data, render nothing meaningful
  if (!dashboardData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 border-2 border-cyan-500/50 border-t-cyan-400 rounded-full animate-spin mx-auto" />
          <p className="text-slate-400 text-sm">Loading dashboard data…</p>
        </div>
      </div>
    );
  }
  // ── Normalize a chart from simple xAxisKey/yAxisKey format to full format ──
  const normalizeChart = (chart: any) => {
    if (!chart) return chart;
    const cfg = chart.chartConfig || {};
    const palette = ['#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];
    const GREY_COLORS = new Set(['#ccc', '#cccccc', '#888', '#888888', '#999', '#999999', '#aaa', '#aaaaaa', 'grey', 'gray', '#c0c0c0']);
    const isPie = chart.type?.toLowerCase().includes('pie') || chart.type?.toLowerCase().includes('sankey');

    // Coerce string-numbers in data so numeric detection works when Gemini returns "2" instead of 2
    let data = Array.isArray(chart.data) ? chart.data.map((row: any) => {
      if (!row || typeof row !== 'object') return row;
      const coerced: any = {};
      for (const k of Object.keys(row)) {
        const v = row[k];
        coerced[k] = (typeof v === 'string' && v !== '' && !isNaN(Number(v))) ? Number(v) : v;
      }
      return coerced;
    }) : chart.data;

    const sample = Array.isArray(data) && data.length > 0 ? data[0] : null;

    // Determine xAxis key: from cfg, or auto-detect first string field in data
    let xKey: string | undefined = cfg.xAxis?.dataKey || cfg.xAxisKey;
    if (!xKey && sample && !isPie) {
      xKey = Object.keys(sample).find(k => typeof sample[k] === 'string') || undefined;
    }

    // Determine series
    let series: any[] | undefined = cfg.series;
    if (!series || series.length === 0) {
      const yKey = cfg.yAxisKey;
      if (yKey) {
        series = [{ dataKey: yKey, name: yKey, type: 'bar' as const, color: palette[0] }];
      } else if (!isPie && sample) {
        // Prefer numeric keys; fall back to ALL non-xKey keys so chart is never empty
        const numericKeys = Object.keys(sample).filter(k => typeof sample[k] === 'number' && k !== xKey);
        const fallbackKeys = numericKeys.length > 0 ? numericKeys
          : Object.keys(sample).filter(k => k !== xKey);
        if (fallbackKeys.length > 0) {
          series = fallbackKeys.map((k, i) => ({ dataKey: k, name: k, type: 'bar' as const, color: palette[i % palette.length] }));
        }
      }
    } else {
      // Validate existing series: fix grey/missing colors; fix dataKey refs that don't exist in data
      series = series.map((s: any, i: number) => {
        const hasGoodColor = s.color && !GREY_COLORS.has(s.color.toLowerCase());
        const fixedColor = hasGoodColor ? s.color : palette[i % palette.length];
        let fixedDataKey = s.dataKey;
        if (sample && fixedDataKey && sample[fixedDataKey] === undefined) {
          const numericKeys = Object.keys(sample).filter(k => typeof sample[k] === 'number' && k !== xKey);
          const anyKeys = Object.keys(sample).filter(k => k !== xKey);
          const candidates = numericKeys.length > 0 ? numericKeys : anyKeys;
          if (candidates[i] || candidates[0]) fixedDataKey = candidates[i] || candidates[0];
        }
        return { ...s, dataKey: fixedDataKey, color: fixedColor };
      });
    }

    return {
      ...chart,
      data,
      chartConfig: {
        ...cfg,
        xAxis: xKey ? { dataKey: xKey, label: xKey, type: 'category' as const } : cfg.xAxis,
        series,
      },
    };
  };

  // ── Derive sixSigma from dmaicReport if present ──────────────────
  const deriveSixSigma = () => {
    if ((dashboardData as any).sixSigma) return (dashboardData as any).sixSigma;
    const dmaic = (dashboardData as any).dmaicReport;
    if (!dmaic) return undefined;
    return {
      sigmaLevel: '3.8σ',
      defectRate: 'Calculating…',
      processCapability: 'High' as const,
      rootCauses: [
        dmaic.analyzePhase?.keyDriversAndCorrelations,
        dmaic.analyzePhase?.paretoAnalysis,
      ].filter(Boolean),
      dmaic: {
        define: [
          dmaic.definePhase?.problemStatement,
          dmaic.definePhase?.goalStatement,
          dmaic.definePhase?.businessImpact,
        ].filter(Boolean).join(' — '),
        measure: dmaic.measurePhase?.dataQualityAnalysis || '',
        analyze: dmaic.analyzePhase?.keyDriversAndCorrelations || '',
        improve: dmaic.improvePhase?.optimizationOpportunities || '',
        control: dmaic.controlPhase?.kpiMonitoringStrategy || '',
      },
    };
  };

  const sixSigmaData = deriveSixSigma();

  // Build charts: use backend-provided ones, or auto-generate from KPI/section data
  const buildFallbackCharts = () => {
    const palette = ['#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];
    const autoCharts: any[] = [];
    const kpis: any[] = dashboardData.kpis || [];
    const sections: any[] = (dashboardData as any).sections || [];

    // 1. KPI values bar
    const kpiBarData = kpis
      .filter((k: any) => typeof k.value === 'number' && k.value !== 0)
      .slice(0, 10)
      .map((k: any) => ({ name: (k.title || 'KPI').slice(0, 20), value: k.value }));
    if (kpiBarData.length > 0) {
      autoCharts.push({
        id: 'auto_kpi_bar', type: 'BarChart', title: 'Key Performance Indicators', size: 'full',
        data: kpiBarData,
        chartConfig: {
          xAxis: { dataKey: 'name', label: 'KPI', type: 'category' },
          series: [{ dataKey: 'value', name: 'Value', type: 'bar', color: '#06b6d4' }],
        },
      });
    }

    // 2. KPI status pie
    const statusCounts: Record<string, number> = {};
    kpis.forEach((k: any) => { const ct = k.changeType || 'neutral'; statusCounts[ct] = (statusCounts[ct] || 0) + 1; });
    if (Object.keys(statusCounts).length > 0) {
      autoCharts.push({
        id: 'auto_kpi_status', type: 'PieChart', title: 'KPI Performance Distribution', size: 'half',
        data: Object.entries(statusCounts).map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value })),
        chartConfig: { nameKey: 'name', dataKey: 'value', colors: ['#10b981', '#ef4444', '#94a3b8'] },
      });
    }

    // 3. Section confidence bar
    const confData = sections
      .filter((s: any) => s.confidence != null)
      .slice(0, 12)
      .map((s: any) => ({ name: (s.title || 'Section').slice(0, 20), confidence: Math.round((s.confidence || 0) * 100) }));
    if (confData.length > 0) {
      autoCharts.push({
        id: 'auto_section_conf', type: 'BarChart', title: 'Section Analysis Confidence (%)', size: 'full',
        data: confData,
        chartConfig: {
          xAxis: { dataKey: 'name', label: 'Section', type: 'category' },
          series: [{ dataKey: 'confidence', name: 'Confidence %', type: 'bar', color: '#10b981' }],
        },
      });
    }

    // 4. DMAIC phase coverage
    const phaseCounts: Record<string, number> = {};
    sections.forEach((s: any) => { const p = s.dmaicPhase; if (p && p !== 'unassigned') phaseCounts[p] = (phaseCounts[p] || 0) + 1; });
    if (Object.keys(phaseCounts).length > 0) {
      const phaseOrder = ['define', 'measure', 'analyze', 'improve', 'control'];
      autoCharts.push({
        id: 'auto_dmaic_phase', type: 'BarChart', title: 'DMAIC Phase Coverage', size: 'half',
        data: phaseOrder.map((p, i) => ({ phase: p.charAt(0).toUpperCase() + p.slice(1), sections: phaseCounts[p] || 0, fill: palette[i] })),
        chartConfig: {
          xAxis: { dataKey: 'phase', label: 'Phase', type: 'category' },
          series: [{ dataKey: 'sections', name: 'Sections', type: 'bar', color: '#8b5cf6' }],
        },
      });
    }

    // 5. KPI category donut
    const catCounts: Record<string, number> = {};
    kpis.forEach((k: any) => { const c = k.category || 'operational'; catCounts[c] = (catCounts[c] || 0) + 1; });
    if (Object.keys(catCounts).length > 1) {
      autoCharts.push({
        id: 'auto_kpi_cat', type: 'PieChart', title: 'KPIs by Category', size: 'half',
        data: Object.entries(catCounts).map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value })),
        chartConfig: { nameKey: 'name', dataKey: 'value', colors: palette },
      });
    }

    return autoCharts;
  };

  const rawCharts: any[] = dashboardData.charts || [];
  const normalizedCharts = (rawCharts.length > 0 ? rawCharts : buildFallbackCharts()).map(normalizeChart);

  const dashboardTitle = dashboardData.title || 'AI Analytics Dashboard';
  const dashboardDesc = dashboardData.description || 'Powered by TransIQ — AI-driven business intelligence.';

  // ── Project Mode state ──────────────────────────────────────
  const { projectMeta } = useDashboard();
  const [viewMode, setViewMode] = useState<ViewMode>('aggregate');
  const isProjectMode = (projectMeta?.filesProcessed ?? 1) > 1;

  // ── Visualization engine ─────────────────────────────────────
  const widgets = useMemo(() => generateWidgets(dashboardData), [dashboardData]);
  const storyBlocks = useMemo(() => mapToStoryBlocks(widgets, dashboardData), [widgets, dashboardData]);
  const [storyMode, setStoryMode] = useState(false);
  const [vizTab, setVizTab] = useState<'charts' | 'predictive' | 'intelligence'>('charts');

  // ── Collapsible section state ──────────────────────────────────────────
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const toggleSection = (key: string) => setCollapsed(prev => ({ ...prev, [key]: !prev[key] }));

  // ── Section navigation state ───────────────────────────────────────────
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);
  const sections = (dashboardData as any).sections || [];
  const activeSection = sections.find((s: any) => s.sectionId === activeSectionId) || null;

  // ── AI Filter Mode: how many KPIs to surface on the dashboard ─────────
  type KpiFilter = 'top5' | 'top10' | 'all';
  const [kpiFilter, setKpiFilter] = useState<KpiFilter>('top10');

  const aiWidgets = (dashboardData as any).widgets;

  const filteredKpis = (() => {
    const allKpis: any[] = dashboardData.kpis || [];
    if (kpiFilter === 'top5') {
      // Use AI widget summary (top 6 primary) when available, else top 5 by priorityScore
      const summary = aiWidgets?.kpi_summary;
      if (summary && summary.length > 0) return summary.slice(0, 5);
      return [...allKpis].sort((a, b) => (b.priorityScore ?? 0) - (a.priorityScore ?? 0)).slice(0, 5);
    }
    if (kpiFilter === 'top10') {
      const summary = aiWidgets?.kpi_summary;
      if (summary && summary.length > 0) return summary.slice(0, 10);
      return [...allKpis].sort((a, b) => (b.priorityScore ?? 0) - (a.priorityScore ?? 0)).slice(0, 10);
    }
    return allKpis; // 'all'
  })();



  // ── Normalize tables from simple format (string columns, array rows) ──
  const normalizeTables = (tables: any[]) => {
    if (!tables || tables.length === 0) return [];
    return tables.map((table: any) => {
      if (!table) return table;
      const cols = table.columns || [];

      let columnObjects: any[];

      if (cols.length > 0 && typeof cols[0] === 'object') {
        // Columns are objects — normalize to { key, label, type } format
        // Pipeline may send { title, dataIndex, key } or { key, label, type }
        columnObjects = cols.map((c: any) => ({
          key: c.key || c.dataIndex || c.label || c.title || 'col',
          label: c.label || c.title || c.key || c.dataIndex || 'Column',
          type: c.type || 'string',
          format: c.format,
        }));
      } else {
        // columns is an array of strings — convert to objects
        columnObjects = cols.map((c: string) => ({ key: c, label: c, type: 'string' }));
      }

      // If data is array-of-arrays, convert to array-of-objects
      const rowData = (table.data || []).map((row: any) => {
        if (Array.isArray(row)) {
          const obj: Record<string, any> = {};
          cols.forEach((col: string, i: number) => { obj[col] = row[i]; });
          return obj;
        }
        return row;
      });

      return {
        ...table,
        columns: columnObjects,
        data: rowData,
        pagination: table.pagination ?? true,
        sortable: table.sortable ?? true,
      };
    });
  };

  const normalizedTables = normalizeTables(dashboardData.tables || []);
  const getSizeClass = (size: string) => {
    switch (size) {
      case 'full': return 'col-span-12';
      case 'half': return 'col-span-12 lg:col-span-6';
      case 'third': return 'col-span-12 lg:col-span-4';
      case 'quarter': return 'col-span-12 lg:col-span-3';
      default: return 'col-span-12';
    }
  };

  const SectionHeader = ({ icon: Icon, label, color = 'cyan' }: { icon: any; label: string; color?: string }) => {
    const colorStyles: Record<string, { wrapper: string; icon: string; line: string }> = {
      cyan:    { wrapper: 'bg-cyan-500/10 border-cyan-500/30',   icon: 'text-cyan-400',   line: 'from-cyan-500/30' },
      teal:    { wrapper: 'bg-teal-500/10 border-teal-500/30',   icon: 'text-teal-400',   line: 'from-teal-500/30' },
      violet:  { wrapper: 'bg-violet-500/10 border-violet-500/30', icon: 'text-violet-400', line: 'from-violet-500/30' },
      amber:   { wrapper: 'bg-amber-500/10 border-amber-500/30',  icon: 'text-amber-400',  line: 'from-amber-500/30' },
      emerald: { wrapper: 'bg-emerald-500/10 border-emerald-500/30', icon: 'text-emerald-400', line: 'from-emerald-500/30' },
      slate:   { wrapper: 'bg-slate-600/20 border-slate-600/40', icon: 'text-slate-400',   line: 'from-slate-500/30' },
    };
    const c = colorStyles[color] ?? colorStyles.cyan;
    return (
      <div className="flex items-center gap-3 mb-6">
        <div className={`w-9 h-9 rounded-lg border flex items-center justify-center ${c.wrapper}`}>
          <Icon className={`h-5 w-5 ${c.icon}`} />
        </div>
        <h2 className="text-xl font-semibold text-white tracking-wide">{label}</h2>
        <div className={`flex-1 h-px bg-gradient-to-r ${c.line} to-transparent`} />
      </div>
    );
  };

  const generatedAt = dashboardData.generatedAt
    ? new Date(dashboardData.generatedAt).toLocaleString()
    : new Date().toLocaleString();

  const handleExportPDF = () => {
    exportDashboardToPDF(dashboardTitle).catch(() => window.print());
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* ── Top Navigation Bar ─────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-slate-700/60 bg-slate-900/80 backdrop-blur-md">
        <div className="max-w-screen-2xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-teal-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Activity className="h-5 w-5 text-slate-900" />
            </div>
            <span className="text-lg font-bold text-white tracking-tight">Trans<span className="text-cyan-400">IQ</span></span>
            <div className="h-5 w-px bg-slate-700 hidden sm:block" />
            <span className="text-sm text-slate-400 hidden sm:block">Industrial Decision OS</span>
          </div>

          {/* Status badges */}
          <div className="flex items-center gap-2 hidden md:flex">
            <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse inline-block" />
              Live
            </Badge>
            <Badge className="bg-slate-700/60 text-slate-300 border-slate-600/40 text-xs">
              {(dashboardData as any).widgets?.pool_size
                ? `${(dashboardData as any).widgets.pool_size} KPIs (pool) · ${dashboardData.charts?.length ?? 0} Charts${sections.length > 0 ? ` · ${sections.length} Sections` : ''}`
                : `${dashboardData.kpis?.length ?? 0} KPIs · ${dashboardData.charts?.length ?? 0} Charts${sections.length > 0 ? ` · ${sections.length} Sections` : ''}`
              }
            </Badge>
            <Badge className="bg-slate-700/60 text-slate-400 border-slate-600/40 text-xs">
              {generatedAt}
            </Badge>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {onRefresh && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRefresh}
                className="text-slate-300 hover:text-white hover:bg-slate-700/60 border border-slate-700/60 h-8"
              >
                <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                <span className="hidden sm:inline">Refresh</span>
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleExportPDF}
              className="text-slate-300 hover:text-white hover:bg-slate-700/60 border border-slate-700/60 h-8"
            >
              <Download className="h-3.5 w-3.5 mr-1.5" />
              <span className="hidden sm:inline">Export PDF</span>
            </Button>
            <Button
              size="sm"
              className="bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-400 hover:to-teal-400 text-slate-900 font-semibold h-8 shadow-lg shadow-cyan-500/20"
              onClick={() => window.location.href = '/upload'}
            >
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              <span className="hidden sm:inline">New Analysis</span>
            </Button>
          </div>
        </div>
      </header>

      {/* ── Main Content ──────────────────────────────────────────── */}
      <main id="dashboard-content" className="max-w-screen-2xl mx-auto px-6 py-8 space-y-10">

        {/* ── Tremor: Priority alert banners ──────────────────────── */}
        {dashboardData.insights?.alerts && dashboardData.insights.alerts.length > 0 && (
          <AlertCallouts alerts={dashboardData.insights.alerts} />
        )}

        {/* ── Project Mode: Banner + View Mode Toggle ─────────────── */}
        {isProjectMode && projectMeta && (
          <ProjectBanner meta={projectMeta} />
        )}
        {isProjectMode && (
          <div className="flex items-center justify-between flex-wrap gap-3">
            <ViewModeToggle mode={viewMode} onChange={setViewMode} />
            {viewMode !== 'aggregate' && (
              <button
                onClick={() => setViewMode('aggregate')}
                className="text-xs text-slate-500 hover:text-slate-300 underline transition-colors"
              >
                ← Back to full dashboard
              </button>
            )}
          </div>
        )}

        {/* ── Project comparison views (non-aggregate modes) ────────── */}
        {isProjectMode && viewMode === 'compare' && projectMeta?.documents && (
          <KPIComparisonTable documents={projectMeta.documents} />
        )}
        {isProjectMode && viewMode === 'document' && projectMeta?.documents && (
          <DocumentTabs documents={projectMeta.documents} />
        )}
        {isProjectMode && viewMode === 'benchmark' && projectMeta?.documents && (
          <BenchmarkTable documents={projectMeta.documents} />
        )}

        {/* ── Non-aggregate modes: hide remaining content ───────────── */}
        {isProjectMode && viewMode !== 'aggregate' ? null : (
          <>

        {/* Dashboard Hero Header */}
        <div className="relative rounded-xl border border-slate-700/50 bg-gradient-to-r from-slate-800/60 via-slate-800/40 to-slate-800/60 px-6 py-5 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-transparent to-teal-500/5 pointer-events-none" />
          <div className="absolute right-0 top-0 w-64 h-full bg-gradient-to-l from-cyan-500/3 to-transparent pointer-events-none" />
          <div className="relative flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div className="flex-1 min-w-0">
              <h1 className="text-xl md:text-2xl font-bold text-white leading-tight mb-1 truncate">
                {dashboardTitle}
              </h1>
              <p className="text-slate-400 text-sm leading-relaxed line-clamp-2">
                {dashboardDesc}
              </p>
            </div>
            <div className="flex flex-wrap gap-2 flex-shrink-0">
              {dashboardData.confidence !== undefined && (
                <div className="flex items-center gap-1.5 bg-slate-700/50 rounded-lg px-3 py-1.5 border border-slate-600/40">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  <span className="text-xs text-slate-300 font-medium">
                    {Math.round((dashboardData.confidence || 0) * 100)}% confidence
                  </span>
                </div>
              )}
              <div className="flex items-center gap-1.5 bg-slate-700/50 rounded-lg px-3 py-1.5 border border-slate-600/40">
                <span className="text-xs text-slate-400">
                  {(dashboardData as any).widgets?.pool_size
                    ? `${(dashboardData as any).widgets.pool_size} KPI pool · ${dashboardData.charts?.length ?? 0} Charts`
                    : `${dashboardData.kpis?.length ?? 0} KPIs · ${dashboardData.charts?.length ?? 0} Charts`
                  }
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Progressive Disclosure: CEO / Manager / Engineer / Boardroom ── */}
        <ProgressiveDisclosureView dashboardData={dashboardData as any} />

        {/* ── AI Critical Alerts ──────────────────────────────────── */}
        {dashboardData.widgets?.alerts && dashboardData.widgets.alerts.length > 0 && (
          <section>
            <AlertPanel alerts={dashboardData.widgets.alerts} />
          </section>
        )}

        {/* ── KPI Cards ───────────────────────────────────────────── */}
        {dashboardData.kpis && dashboardData.kpis.length > 0 && (
          <section>
            {/* Section header with collapse toggle */}
            <div className="flex items-center justify-between mb-4">
              <SectionHeader icon={Activity} label="Key Performance Indicators" color="cyan" />
              <div className="flex items-center gap-2">
                {/* AI Filter Mode toggle */}
                <div className="flex items-center gap-1 bg-slate-800/60 border border-slate-700/50 rounded-lg p-1">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider px-1.5 font-semibold">AI Filter</span>
                  {(['top5', 'top10', 'all'] as const).map(f => (
                    <button
                      key={f}
                      onClick={() => setKpiFilter(f)}
                      className={`text-[11px] font-semibold px-2.5 py-1 rounded transition-all ${
                        kpiFilter === f
                          ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                          : 'text-slate-500 hover:text-slate-300'
                      }`}
                    >
                      {f === 'top5' ? 'Top 5' : f === 'top10' ? 'Top 10' : 'All'}
                    </button>
                  ))}
                </div>
                {/* Pool size indicator */}
                {aiWidgets?.pool_size != null && (
                  <span className="text-[10px] text-slate-500 bg-slate-800/40 border border-slate-700/40 rounded px-2 py-1">
                    {filteredKpis.length} shown / {aiWidgets.pool_size} in pool
                  </span>
                )}
                <button
                  onClick={() => toggleSection('kpis')}
                  className="text-slate-500 hover:text-slate-300 transition-colors p-1"
                >
                  {collapsed['kpis'] ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {!collapsed['kpis'] && (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {filteredKpis.map((kpi: any) => (
                  <KPICard key={kpi.id || kpi.name} kpi={kpi} />
                ))}
              </div>
            )}
          </section>
        )}



        {/* ── Report Sections Deep Dive ───────────────────────────── */}
        {sections.length > 0 && (
          <section id="section-report-sections">
            <SectionHeader icon={BookOpen} label={`Report Sections (${sections.length} analyzed)`} color="teal" />

            {activeSection ? (
              /* Show detail view for selected section */
              <SectionDetail
                section={activeSection}
                sectionIndex={sections.indexOf(activeSection)}
                totalSections={sections.length}
                onBack={() => setActiveSectionId(null)}
              />
            ) : (
              /* Show section grid overview */
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {sections.map((sec: any, idx: number) => {
                  const highRisks = (sec.risks || []).filter((r: any) => r.severity === 'high').length;
                  const tierLabel = sec.tier === 1 ? 'Full' : sec.tier === 2 ? 'Light' : 'Min';
                  const tierColor = sec.tier === 1 ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' : sec.tier === 2 ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' : 'bg-slate-600/20 text-slate-400 border-slate-600/40';
                  const modelColor = sec.modelUsed === 'powerful' ? 'text-violet-400' : sec.modelUsed === 'balanced' ? 'text-teal-400' : 'text-slate-500';
                  const phaseColors: Record<string, string> = { define: 'text-blue-400', measure: 'text-teal-400', analyze: 'text-violet-400', improve: 'text-emerald-400', control: 'text-amber-400' };
                  return (
                    <Card
                      key={sec.sectionId}
                      className="bg-slate-800/40 border-slate-700/40 hover:border-cyan-500/40 transition-all duration-200 cursor-pointer group"
                      onClick={() => setActiveSectionId(sec.sectionId)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-slate-500">{String(idx + 1).padStart(2, '0')}</span>
                            <h4 className="text-sm font-semibold text-white group-hover:text-cyan-400 transition-colors line-clamp-1">
                              {sec.title}
                            </h4>
                          </div>
                          <div className="flex items-center gap-1.5">
                            {sec.tier && (
                              <Badge className={`text-[10px] px-1.5 py-0 ${tierColor}`}>T{sec.tier}</Badge>
                            )}
                            {highRisks > 0 && (
                              <Badge className="bg-red-500/20 text-red-400 border-red-500/30 text-[10px]">
                                <AlertTriangle className="h-2.5 w-2.5 mr-0.5" />{highRisks}
                              </Badge>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 mb-1">
                          {sec.pageRange && <span className="text-[11px] text-slate-500">{sec.pageRange}</span>}
                          {sec.dmaicPhase && sec.dmaicPhase !== 'unassigned' && sec.dmaicPhase !== 'none' && (
                            <span className={`text-[10px] font-medium uppercase ${phaseColors[sec.dmaicPhase] || 'text-slate-400'}`}>
                              {sec.dmaicPhase}
                            </span>
                          )}
                          {sec.modelUsed && (
                            <span className={`text-[10px] ${modelColor}`}>{sec.modelUsed}</span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400 mt-1 line-clamp-2">{sec.summary}</p>
                        <div className="flex items-center gap-3 mt-3 text-[11px] text-slate-500">
                          {(sec.kpis || []).length > 0 && <span>{sec.kpis.length} KPIs</span>}
                          {(sec.keyFindings || []).length > 0 && <span>{sec.keyFindings.length} findings</span>}
                          <span className={`ml-auto ${(sec.confidence ?? 0) >= 0.7 ? 'text-emerald-400' : (sec.confidence ?? 0) >= 0.4 ? 'text-amber-400' : 'text-red-400'}`}>
                            {Math.round((sec.confidence ?? 0) * 100)}% conf.
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </section>
        )}



        {/* ── Quality Score ────────────────────────────────────────── */}
        {(dashboardData as any).qualityScore && (
          <section id="section-quality-score">
            <SectionHeader icon={Shield} label="Six Sigma Quality Score" color="violet" />
            <QualityScoreCard qualityScore={(dashboardData as any).qualityScore} />
          </section>
        )}



        {/* ── DMAIC Compiled Report ───────────────────────────────────── */}
        {(dashboardData as any).dmaicReport && (
          <section id="section-dmaic-compiler">
            <SectionHeader icon={FileText} label="DMAIC Compiled Report" color="teal" />
            <DmaicCompilerPanel dmaicReport={(dashboardData as any).dmaicReport} />
          </section>
        )}



        {/* ── Six Sigma DMAIC ─────────────────────────────────────── */}
        {sixSigmaData && (
          <section>
            <SectionHeader icon={Sigma} label="Six Sigma · DMAIC Analysis" color="violet" />
            <SixSigmaSection sixSigma={sixSigmaData} />
            <div className="mt-4">
              <SixSigmaAnalyzer />
            </div>
          </section>
        )}



        {/* ── Visualizations & Analytics (Charts tab + Predictive tab) ─── */}
        {(widgets.length > 0 || (dashboardData as any).predictive) && (
          <section>
            {/* Section header */}
            <div className="flex items-center gap-3 mb-4">
              <div className="w-9 h-9 rounded-lg border flex items-center justify-center bg-teal-500/10 border-teal-500/30">
                <BarChart3 className="h-5 w-5 text-teal-400" />
              </div>
              <h2 className="text-xl font-semibold text-white tracking-wide">Visualizations &amp; Analytics</h2>
              <div className="flex-1 h-px bg-gradient-to-r from-teal-500/30 to-transparent" />
              {/* Main tab: Charts / Predictive / Intelligence */}
              <div className="flex rounded-lg overflow-hidden border border-slate-600 text-xs shrink-0">
                <button
                  onClick={() => setVizTab('charts')}
                  className={`px-3 py-1.5 flex items-center gap-1.5 transition-colors ${vizTab === 'charts' ? 'bg-teal-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
                >
                  <BarChart3 className="h-3 w-3" />
                  Charts
                </button>
                <button
                  onClick={() => setVizTab('intelligence')}
                  className={`px-3 py-1.5 flex items-center gap-1.5 transition-colors ${vizTab === 'intelligence' ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
                >
                  <Database className="h-3 w-3" />
                  Entity Intelligence
                </button>
                <button
                  onClick={() => setVizTab('predictive')}
                  className={`px-3 py-1.5 flex items-center gap-1.5 transition-colors ${vizTab === 'predictive' ? 'bg-violet-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
                >
                  <TrendingUp className="h-3 w-3" />
                  Predictive
                </button>
              </div>
            </div>

            {/* ── Charts Tab ────────────────────────────────────── */}
            {vizTab === 'charts' && widgets.length > 0 && (
              <>
                {/* Grid / Story sub-toggle */}
                <div className="flex justify-end mb-4">
                  <div className="flex rounded-lg overflow-hidden border border-slate-700 text-xs">
                    <button
                      onClick={() => setStoryMode(false)}
                      className={`px-3 py-1.5 flex items-center gap-1.5 transition-colors ${!storyMode ? 'bg-slate-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
                      title="Grid layout"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                        <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
                      </svg>
                      Grid
                    </button>
                    <button
                      onClick={() => setStoryMode(true)}
                      className={`px-3 py-1.5 flex items-center gap-1.5 transition-colors ${storyMode ? 'bg-slate-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
                      title="DMAIC story mode"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M4 6h16M4 12h16M4 18h10"/>
                      </svg>
                      Story
                    </button>
                  </div>
                </div>

                {storyMode ? (
                  <div className="space-y-6">
                    {storyBlocks.map(block => (
                      <StorySection key={block.id} block={block} />
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-12 gap-5">
                    {widgets.map(widget => {
                      const colClass =
                        widget.size === 'large'  ? 'col-span-12' :
                        widget.size === 'medium' ? 'col-span-12 lg:col-span-6' :
                                                   'col-span-12 lg:col-span-4';
                      return (
                        <div key={widget.id} className={colClass}>
                          <ChartRenderer widget={widget} />
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            )}

            {vizTab === 'charts' && widgets.length === 0 && (
              <div className="text-center py-12 text-slate-500">No chart widgets generated.</div>
            )}

            {/* ── Entity Intelligence Tab ────────────────────────── */}
            {vizTab === 'intelligence' && (
              <EntityIntelligenceTab 
                reportId={(dashboardData as any).reportId || (dashboardData as any).documentId || 'default'}
                primaryEntityId={(dashboardData as any).reportId || (dashboardData as any).documentId || 'default'}
              />
            )}

            {/* ── Predictive Tab ─────────────────────────────────── */}
            {vizTab === 'predictive' && (() => {
              const rawPredictive = (dashboardData as any).predictive;
              const predictiveData = rawPredictive ?? {};
              return (
                <div className="space-y-8">
                  <PredictiveDashboard predictive={predictiveData} />
                  {Array.isArray(predictiveData.whatIfScenarios) && predictiveData.whatIfScenarios.length > 0 && (
                    <div>
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-8 h-8 rounded-lg border flex items-center justify-center bg-violet-500/10 border-violet-500/30">
                          <TrendingUp className="h-4 w-4 text-violet-400" />
                        </div>
                        <h3 className="text-lg font-semibold text-white">What-If Scenario Simulator</h3>
                        <div className="flex-1 h-px bg-gradient-to-r from-violet-500/30 to-transparent" />
                      </div>
                      <WhatIfSimulator scenarios={predictiveData.whatIfScenarios} />
                    </div>
                  )}
                </div>
              );
            })()}
          </section>
        )}

        {/* ── Insights & Alerts ───────────────────────────────────── */}
        {dashboardData.insights && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <SectionHeader icon={Lightbulb} label="AI Insights & Alerts" color="amber" />
              <button onClick={() => toggleSection('insights')} className="text-slate-500 hover:text-slate-300 transition-colors p-1">
                {collapsed['insights'] ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
              </button>
            </div>
            {!collapsed['insights'] && (
              <InsightsSection insights={dashboardData.insights} />
            )}
          </section>
        )}

        {/* ── Optimization Suggestions / DCI Recommendations ─────── */}
        {dashboardData.optimizationSuggestions && dashboardData.optimizationSuggestions.length > 0 && (
          <section>
            <SectionHeader icon={Zap} label="Optimization Opportunities" color="emerald" />
            {/* DCI cards — show when any item has DCI data */}
            {dashboardData.optimizationSuggestions.some((opt: any) =>
              opt.decision_confidence_index || opt.decision_traceability || opt.industry_benchmarking
            ) ? (
              <div className="space-y-4">
                <p className="text-xs text-slate-500 flex items-center gap-1.5 mb-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-cyan-400" />
                  Enterprise Decision Intelligence — each recommendation includes full audit trail, DCI score, and benchmarking
                </p>
                {dashboardData.optimizationSuggestions.map((opt: any, idx: number) => (
                  <DCIRecommendationCard key={opt.id || idx} recommendation={opt} index={idx} />
                ))}
              </div>
            ) : (
              <OptimizationSuggestions suggestions={dashboardData.optimizationSuggestions} />
            )}
          </section>
        )}



        {/* ── Explainability & Audit Trail ──────────────────────── */}
        {(() => {
          const expl = (dashboardData as any).explainability
          if (!expl) return null
          const whyConcl: string[] = Array.isArray(expl.whyThisConclusion) ? expl.whyThisConclusion : []
          const dataUsed: string[] = Array.isArray(expl.dataUsed) ? expl.dataUsed : []
          const assumptions: string[] = Array.isArray(expl.assumptions) ? expl.assumptions : []
          const limitations: string[] = Array.isArray(expl.limitations) ? expl.limitations : []
          const approach: string = expl.analysisApproach || ''
          const sectionsCovered: number | undefined = expl.sectionsCovered
          const totalPages: number | undefined = expl.totalPages
          if (!whyConcl.length && !dataUsed.length && !assumptions.length && !limitations.length && !approach) return null
          return (
            <section>
              <div className="flex items-center justify-between mb-4">
                <SectionHeader icon={Shield} label="Explainability & Audit Trail" color="violet" />
                <button onClick={() => toggleSection('explainability')} className="text-slate-500 hover:text-slate-300 transition-colors p-1">
                  {collapsed['explainability'] ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
                </button>
              </div>
              {!collapsed['explainability'] && (
                <div className="space-y-4">
                  {/* Header stats */}
                  {(sectionsCovered !== undefined || totalPages !== undefined || approach) && (
                    <Card className="bg-violet-500/5 border-violet-500/20">
                      <CardContent className="p-4">
                        <div className="flex flex-wrap items-center gap-4 text-sm">
                          {sectionsCovered !== undefined && (
                            <div className="flex items-center gap-1.5">
                              <Brain className="h-4 w-4 text-violet-400" />
                              <span className="text-slate-400">Sections Covered:</span>
                              <span className="text-white font-semibold">{sectionsCovered}</span>
                            </div>
                          )}
                          {totalPages !== undefined && (
                            <div className="flex items-center gap-1.5">
                              <FileText className="h-4 w-4 text-violet-400" />
                              <span className="text-slate-400">Total Pages:</span>
                              <span className="text-white font-semibold">{totalPages}</span>
                            </div>
                          )}
                          {approach && (
                            <div className="flex items-center gap-1.5 flex-1 min-w-0">
                              <Shield className="h-4 w-4 text-violet-400 flex-shrink-0" />
                              <span className="text-slate-400 flex-shrink-0">Approach:</span>
                              <span className="text-violet-300 text-xs">{approach}</span>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Why This Conclusion */}
                    {whyConcl.length > 0 && (
                      <Card className="bg-slate-800/40 border-slate-700/40">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm flex items-center gap-2 text-white">
                            <Brain className="h-4 w-4 text-violet-400" />
                            AI Reasoning
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <ul className="space-y-2">
                            {whyConcl.map((w, i) => (
                              <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                                <span className="text-violet-400 mt-0.5 flex-shrink-0">•</span>
                                {w}
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    )}

                    {/* Data Used */}
                    {dataUsed.length > 0 && (
                      <Card className="bg-slate-800/40 border-slate-700/40">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm flex items-center gap-2 text-white">
                            <Database className="h-4 w-4 text-cyan-400" />
                            Data Sources Used
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <ul className="space-y-2">
                            {dataUsed.map((d, i) => (
                              <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                                <CheckCircle className="h-3.5 w-3.5 text-cyan-400 mt-0.5 flex-shrink-0" />
                                {d}
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    )}

                    {/* Assumptions */}
                    {assumptions.length > 0 && (
                      <Card className="bg-slate-800/40 border-amber-500/20">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm flex items-center gap-2 text-white">
                            <AlertTriangle className="h-4 w-4 text-amber-400" />
                            Assumptions Made
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <ul className="space-y-2">
                            {assumptions.map((a, i) => (
                              <li key={i} className="flex items-start gap-2 text-xs text-slate-300 p-2 bg-amber-500/5 border-l-2 border-amber-500/40 rounded-r">
                                {a}
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    )}

                    {/* Limitations */}
                    {limitations.length > 0 && (
                      <Card className="bg-slate-800/40 border-red-500/20">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm flex items-center gap-2 text-white">
                            <XCircle className="h-4 w-4 text-red-400" />
                            Known Limitations
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <ul className="space-y-2">
                            {limitations.map((l, i) => (
                              <li key={i} className="flex items-start gap-2 text-xs text-slate-300 p-2 bg-red-500/5 border-l-2 border-red-500/40 rounded-r">
                                {l}
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </div>
              )}
            </section>
          )
        })()}

        {/* ── Data Tables ─────────────────────────────────────────── */}
        {normalizedTables.map((table: any) => (
          <section key={table.id}>
            <SectionHeader icon={Database} label={table.title || 'Data Table'} color="slate" />
            <DataTable tableData={table} />
          </section>
        ))}

        {/* ── Footer ──────────────────────────────────────────────── */}
        <footer className="border-t border-slate-700/40 pt-6 pb-2 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-gradient-to-br from-cyan-400 to-teal-500 flex items-center justify-center">
              <Activity className="h-3 w-3 text-slate-900" />
            </div>
            <span className="text-xs text-slate-500">TransIQ · AI-Powered Business Intelligence</span>
          </div>
          <span className="text-xs text-slate-600">Generated {generatedAt}</span>
        </footer>

          </>
        )}
      </main>
    </div>
  );
};

export default DashboardRenderer;
