// ============================================================================
// Fleet Command Center — Module 1
// Hero KPIs, Fleet Heatmap, Top/Bottom Performers, Fleet Trends
// ============================================================================

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useDDR } from '@/contexts/DDRContext';
import { useFleetSummary, useFleetTopPerformers, useFleetTrends } from '@/api/hooks/useDDRHooks';
import KPICard from '@/components/KPICard';
import FleetHeatmap from '@/components/ddr/FleetHeatmap';
import { CitationBadge } from '@/components/citation/CitationBadge';
import { LoadingState, EmptyState } from '@/components/ddr/state';
import type { KPIValue, RigIdentity } from '@/types/ddr.types';
import { DDR_TOKENS } from '@/styles/tokens';
import { AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import { fadeInUp, staggerContainer } from '@/utils/animations';

// Placeholder identity for fleet-wide KPIs
const FLEET_IDENTITY: RigIdentity = {
  rig_id: 'FLEET',
  well_id: 'ALL',
  report_date: '',
  shift_period: '0500-0500',
  objective: 'Fleet Operations',
  charge_number: '',
  location: '',
  programme_name: 'Daily Drilling Fleet Report',
  programme_dates: '',
  classification: 'Saudi Aramco: Confidential',
  foremen: '',
  engineer: '',
  manager: '',
  thuraya: '',
};

interface FleetCommandCenterProps {
  onRigSelect?: (rigId: string) => void;
}

// ── Trend metric config ─────────────────────────────────────────────────────

type TrendMetricId = 'avg_rop' | 'total_npt_hours' | 'total_footage';

interface TrendMetric {
  id: TrendMetricId;
  label: string;
  unit: string;
  color: string;
  yAxisId: 'left' | 'right';
}

const TREND_METRICS: TrendMetric[] = [
  { id: 'avg_rop', label: 'Avg ROP', unit: 'ft/hr', color: DDR_TOKENS.chart.c1, yAxisId: 'left' },
  { id: 'total_npt_hours', label: 'NPT Hours', unit: 'hrs', color: DDR_TOKENS.chart.c3, yAxisId: 'right' },
  { id: 'total_footage', label: 'Fleet Footage', unit: 'ft', color: DDR_TOKENS.chart.c2, yAxisId: 'left' },
];

// ── Performers tab type ─────────────────────────────────────────────────────

type PerformerTab = 'top' | 'bottom';

const FleetCommandCenter: React.FC<FleetCommandCenterProps> = ({ onRigSelect }) => {
  const { reportDate } = useDDR();
  const { data: fleet, isLoading: fleetLoading } = useFleetSummary(reportDate);
  const { data: topPerformers } = useFleetTopPerformers(reportDate, 'daily_footage', 10);
  const { data: bottomPerformers } = useFleetTopPerformers(reportDate, 'rop_ft_hr', 10);
  const { data: trends } = useFleetTrends({ report_date: reportDate, days: 14 });

  const [performerTab, setPerformerTab] = useState<PerformerTab>('top');
  const [activeTrendMetrics, setActiveTrendMetrics] = useState<Set<TrendMetricId>>(
    new Set(['avg_rop', 'total_npt_hours', 'total_footage'])
  );

  const identity = { ...FLEET_IDENTITY, report_date: reportDate };

  const toggleTrendMetric = (id: TrendMetricId) => {
    setActiveTrendMetrics(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        if (next.size > 1) next.delete(id); // keep at least 1
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Helper to build KPI card data from a KPIValue
  const makeKPI = (id: string, title: string, kv: KPIValue | undefined, icon: string, fallbackValue?: number) => ({
    kpi: {
      id,
      title,
      value: typeof kv?.value === 'number' ? kv.value : (fallbackValue ?? 0),
      unit: kv?.unit || '',
      change: '',
      changeType: 'neutral' as const,
      icon,
      color: '#00A651',
      status: kv?.status === 'critical' ? 'critical' as const
            : kv?.status === 'warning' ? 'warning' as const
            : 'good' as const,
    },
    kpiValue: kv,
    identity,
    ddrStatus: kv?.status,
    showStatusRing: true,
  });

  if (fleetLoading) {
    return <LoadingState message="Loading fleet data..." />;
  }

  if (!fleet) {
    return <EmptyState title="No Fleet Data" message="Select a report date to view fleet operations." />;
  }

  return (
    <motion.div
      className="space-y-6"
      variants={staggerContainer}
      initial="initial"
      animate="animate"
    >
      {/* Priority Alert Banners */}
      {fleet && fleet.rigs_critical > 0 && (
        <motion.div
          variants={fadeInUp}
          transition={{ duration: 0.3 }}
          className="flex items-center gap-3 px-4 py-3 rounded-xl border"
          style={{
            background: 'rgba(255,77,79,0.08)',
            borderColor: 'rgba(255,77,79,0.3)',
          }}
        >
          <AlertTriangle className="h-5 w-5 text-red-400 flex-shrink-0 animate-pulse" />
          <span className="text-sm text-red-300">
            <strong>{fleet.rigs_critical} rigs</strong> in CRITICAL status — NPT &gt; 50% or stuck pipe active
          </span>
        </motion.div>
      )}

      {/* Hero Header */}
      <motion.div variants={fadeInUp} transition={{ duration: 0.4 }} className="rounded-xl p-6" style={{ background: DDR_TOKENS.bg.secondary }}>
        <h2 className="text-xl font-bold text-white mb-1">
          Fleet Operations — {reportDate}
        </h2>
        <p className="text-sm text-slate-400">
          {fleet?.total_rigs || 0} Rigs · OPERLMTDMRREP
        </p>
      </motion.div>

      {/* Hero KPI Row — 6 cards */}
      {fleet && (
        <motion.div variants={fadeInUp} transition={{ duration: 0.4 }} className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
          <KPICard {...makeKPI('total-rigs', 'Total Rigs', undefined, 'barchart', fleet.total_rigs)} />
          <KPICard {...makeKPI('rigs-drilling', 'Drilling', undefined, 'activity', fleet.rigs_drilling)} />
          <KPICard {...makeKPI('avg-rop', 'Avg ROP (ft/hr)', fleet.avg_rop_ft_hr, 'trending_up')} />
          <KPICard {...makeKPI('total-npt', 'Total NPT (hrs)', fleet.total_npt_hours, 'clock')} />
          <KPICard {...makeKPI('fleet-footage', 'Fleet Footage (ft)', fleet.total_daily_footage_ft, 'target')} />
          <KPICard {...makeKPI('total-personnel', 'Total Personnel', fleet.total_personnel, 'users')} />
        </motion.div>
      )}

      {/* Fleet Heatmap */}
      <motion.div variants={fadeInUp} transition={{ duration: 0.4 }}>
        <FleetHeatmap onRigSelect={onRigSelect} />
      </motion.div>

      {/* Top / Bottom Performers Table */}
      {(topPerformers || bottomPerformers) && (
        <motion.div variants={fadeInUp} transition={{ duration: 0.4 }} className="rounded-xl p-6 overflow-hidden" style={{ background: DDR_TOKENS.bg.secondary }}>
          {/* Tab header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {(['top', 'bottom'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setPerformerTab(tab)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    performerTab === tab
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'bg-slate-800/60 text-slate-400 border border-slate-700/40 hover:bg-slate-700/60'
                  }`}
                >
                  {tab === 'top' ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  {tab === 'top' ? 'Top 10' : 'Bottom 10'}
                </button>
              ))}
            </div>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">
              {performerTab === 'top' ? 'Daily Footage' : 'ROP (ft/hr)'}
            </span>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm" role="table">
              <thead>
                <tr className="border-b border-slate-700/40">
                  <th scope="col" className="text-left py-2 px-3 text-xs font-semibold text-slate-400 uppercase">Rank</th>
                  <th scope="col" className="text-left py-2 px-3 text-xs font-semibold text-slate-400 uppercase">Rig</th>
                  <th scope="col" className="text-left py-2 px-3 text-xs font-semibold text-slate-400 uppercase">Well</th>
                  <th scope="col" className="text-right py-2 px-3 text-xs font-semibold text-slate-400 uppercase">Value</th>
                  <th scope="col" className="text-right py-2 px-3 text-xs font-semibold text-slate-400 uppercase">Source</th>
                </tr>
              </thead>
              <tbody>
                {(performerTab === 'top' ? topPerformers : bottomPerformers)?.map((tp) => (
                  <tr
                    key={tp.rig_id}
                    className="border-b border-slate-700/20 hover:bg-slate-800/40 cursor-pointer transition-colors"
                    onClick={() => onRigSelect?.(tp.rig_id)}
                  >
                    <td className="py-2 px-3 font-mono text-slate-400">#{tp.rank}</td>
                    <td className="py-2 px-3 text-white font-bold">{tp.rig_id}</td>
                    <td className="py-2 px-3 text-slate-300">{tp.well_id}</td>
                    <td className="py-2 px-3 text-right font-mono" style={{ color: performerTab === 'top' ? DDR_TOKENS.status.excellent : DDR_TOKENS.status.warning }}>
                      {tp.metric_value.toLocaleString()} {tp.metric_unit}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded font-mono"
                        style={{
                          background: DDR_TOKENS.citation.badge,
                          border: `1px solid ${DDR_TOKENS.citation.badgeBorder}`,
                          color: DDR_TOKENS.citation.badgeText,
                        }}
                        title={tp.source_citation}
                      >
                        📋 {tp.source_citation.split('–').slice(0, 2).join('–').trim()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {/* Fleet Trend Chart with Metric Selector */}
      {trends && trends.length > 0 && (
        <motion.figure variants={fadeInUp} transition={{ duration: 0.4 }} role="img" aria-labelledby="fleet-trends-title">
          <div className="rounded-xl p-6" style={{ background: DDR_TOKENS.bg.secondary }}>
            {/* Header + metric toggle */}
            <div className="flex items-center justify-between mb-4">
              <figcaption id="fleet-trends-title" className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                Fleet Trends — 14 Day
              </figcaption>
              <div className="flex items-center gap-1.5">
                {TREND_METRICS.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => toggleTrendMetric(m.id)}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-medium transition-colors border ${
                      activeTrendMetrics.has(m.id)
                        ? 'border-opacity-40 text-white'
                        : 'border-slate-700/40 text-slate-500 hover:text-slate-300 hover:bg-slate-800/40'
                    }`}
                    style={activeTrendMetrics.has(m.id) ? {
                      background: `${m.color}15`,
                      borderColor: `${m.color}60`,
                    } : undefined}
                  >
                    <span className="w-2 h-2 rounded-full" style={{ background: activeTrendMetrics.has(m.id) ? m.color : DDR_TOKENS.text.muted }} />
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Chart — fixed 220px height */}
            <div style={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={DDR_TOKENS.surface.border} />
                  <XAxis dataKey="date" stroke={DDR_TOKENS.text.muted} tick={{ fontSize: 10 }} />
                  <YAxis yAxisId="left" stroke={DDR_TOKENS.text.muted} tick={{ fontSize: 10 }} />
                  <YAxis yAxisId="right" orientation="right" stroke={DDR_TOKENS.text.muted} tick={{ fontSize: 10 }} />
                  <RTooltip
                    contentStyle={{
                      background: 'hsl(222 40% 8%)',
                      border: `1px solid ${DDR_TOKENS.surface.border}`,
                      borderRadius: 8,
                      fontSize: 11,
                    }}
                    labelStyle={{ color: DDR_TOKENS.text.secondary, fontSize: 10, marginBottom: 4 }}
                    itemStyle={{ padding: '1px 0' }}
                  />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  {TREND_METRICS.filter(m => activeTrendMetrics.has(m.id)).map((m) => (
                    <Line
                      key={m.id}
                      yAxisId={m.yAxisId}
                      type="monotone"
                      dataKey={m.id}
                      name={`${m.label} (${m.unit})`}
                      stroke={m.color}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, strokeWidth: 0 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Accessible data table */}
            <table className="sr-only">
              <caption>Fleet Trends Data Table — 14 Day</caption>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Avg ROP (ft/hr)</th>
                  <th scope="col">Total NPT (hrs)</th>
                  <th scope="col">Total Footage (ft)</th>
                </tr>
              </thead>
              <tbody>
                {trends.map(t => (
                  <tr key={t.date}>
                    <td>{t.date}</td>
                    <td>{t.avg_rop}</td>
                    <td>{t.total_npt_hours}</td>
                    <td>{t.total_footage}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.figure>
      )}
    </motion.div>
  );
};

export default FleetCommandCenter;
