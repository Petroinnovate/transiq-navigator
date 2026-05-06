// ============================================================================
// NPT Intelligence Module — Module 3
// Fleet NPT Pareto, NPT events table, SPC control chart for NPT
// ============================================================================

import React, { useState } from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useFleetNPTPareto, useFleetSPC, useRigNPT } from '@/api/hooks/useDDRHooks';
import NPTEventsTable from './NPTEventsTable';
import KPICard from '@/components/KPICard';
import { LoadingState, EmptyState } from '@/components/ddr/state';
import { DDR_TOKENS } from '@/styles/tokens';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  ResponsiveContainer, Line, ComposedChart, ReferenceLine,
  ScatterChart, Scatter, Cell,
} from 'recharts';

interface NPTIntelligenceProps {
  rigId?: string | null;
}

const NPTIntelligence: React.FC<NPTIntelligenceProps> = ({ rigId }) => {
  const { reportDate } = useDDR();
  const { data: pareto, isLoading: paretoLoading } = useFleetNPTPareto(reportDate);
  const { data: spc, isLoading: spcLoading } = useFleetSPC('npt_hours', reportDate);
  const { data: rigNPT } = useRigNPT(rigId || '', reportDate);

  if (paretoLoading || spcLoading) {
    return <LoadingState message="Loading NPT intelligence..." />;
  }

  if (!pareto || pareto.length === 0) {
    return <EmptyState title="No NPT Data" message="No NPT events recorded for this report date." />;
  }

  // NPT Hero KPIs (computed from pareto data)
  const totalFleetNPT = pareto?.reduce((sum, p) => sum + p.total_hours, 0) ?? 0;
  const topCause = pareto?.[0];
  const rigsWithNPT = pareto?.reduce((sum, p) => sum + p.rig_count, 0) ?? 0;

  return (
    <div className="space-y-6">
      {/* NPT Hero Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary, border: `1px solid ${DDR_TOKENS.surface.border}` }}>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Fleet NPT Today</div>
          <div className="text-2xl font-bold text-red-400 font-mono">{totalFleetNPT.toFixed(1)} hrs</div>
        </div>
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary, border: `1px solid ${DDR_TOKENS.surface.border}` }}>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Top Cause</div>
          <div className="text-2xl font-bold text-amber-400 font-mono">
            {topCause ? `${topCause.cause_code} ${topCause.cumulative_pct.toFixed(0)}%` : '—'}
          </div>
        </div>
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary, border: `1px solid ${DDR_TOKENS.surface.border}` }}>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Rigs w/ NPT</div>
          <div className="text-2xl font-bold text-white font-mono">{rigsWithNPT}</div>
        </div>
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary, border: `1px solid ${DDR_TOKENS.surface.border}` }}>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Most Affected</div>
          <div className="text-lg font-bold text-red-400 font-mono">
            {topCause?.rigs?.[0]?.rig_id ?? '—'}
          </div>
        </div>
      </div>

      {/* NPT Pareto Chart */}
      {pareto && pareto.length > 0 && (
        <figure role="img" aria-labelledby="npt-pareto-title">
          <div className="rounded-xl p-6" style={{ background: DDR_TOKENS.bg.secondary }}>
            <figcaption id="npt-pareto-title" className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-4">
              NPT Pareto Analysis — Cause Codes
            </figcaption>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={pareto} margin={{ top: 10, right: 30, left: 20, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={DDR_TOKENS.surface.border} />
                  <XAxis dataKey="cause_code" stroke={DDR_TOKENS.text.muted} tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="left" stroke={DDR_TOKENS.text.muted} tick={{ fontSize: 11 }} label={{ value: 'Hours', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: DDR_TOKENS.text.muted } }} />
                  <YAxis yAxisId="right" orientation="right" stroke={DDR_TOKENS.text.muted} tick={{ fontSize: 11 }} domain={[0, 100]} label={{ value: 'Cumulative %', angle: 90, position: 'insideRight', style: { fontSize: 10, fill: DDR_TOKENS.text.muted } }} />
                  <RTooltip
                    contentStyle={{
                      background: DDR_TOKENS.bg.overlay,
                      border: `1px solid ${DDR_TOKENS.surface.border}`,
                      borderRadius: 8, fontSize: 12,
                    }}
                    formatter={(value: number, name: string) => [
                      name === 'total_hours' ? `${value.toFixed(1)} hrs` : `${value.toFixed(1)}%`,
                      name === 'total_hours' ? 'Total Hours' : 'Cumulative %'
                    ]}
                  />
                  <Bar yAxisId="left" dataKey="total_hours" fill={DDR_TOKENS.status.critical} radius={[4, 4, 0, 0]} />
                  <Line yAxisId="right" type="monotone" dataKey="cumulative_pct" stroke={DDR_TOKENS.status.warning} strokeWidth={2} dot={{ fill: DDR_TOKENS.status.warning, r: 3 }} />
                  <ReferenceLine yAxisId="right" y={80} stroke={DDR_TOKENS.status.warning} strokeDasharray="3 3" label={{ value: '80%', position: 'right', style: { fontSize: 10, fill: DDR_TOKENS.status.warning } }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            {/* Accessible table */}
            <table className="sr-only">
              <caption>NPT Pareto Chart Data</caption>
              <thead><tr><th>Cause</th><th>Hours</th><th>Cumulative %</th><th>Rigs</th></tr></thead>
              <tbody>
                {pareto.map(p => <tr key={p.cause_code}><td>{p.cause_code}</td><td>{p.total_hours}</td><td>{p.cumulative_pct}%</td><td>{p.rig_count}</td></tr>)}
              </tbody>
            </table>
          </div>
        </figure>
      )}

      {/* SPC Control Chart for NPT */}
      {spc && spc.data_points.length > 0 && (
        <figure role="img" aria-labelledby="npt-spc-title">
          <div className="rounded-xl p-6" style={{ background: DDR_TOKENS.bg.secondary }}>
            <figcaption id="npt-spc-title" className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-2">
              NPT SPC Control Chart
            </figcaption>
            <div className="flex gap-4 mb-4 text-xs">
              <span className="text-slate-400">μ = {spc.mean.toFixed(2)}</span>
              <span className="text-slate-400">σ = {spc.std_dev.toFixed(2)}</span>
              <span className="text-emerald-400">UCL = {spc.ucl.toFixed(2)}</span>
              <span className="text-cyan-400">LCL = {spc.lcl.toFixed(2)}</span>
              <span className="text-red-400">Out of control: {spc.out_of_control_count}</span>
            </div>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 20, left: 20, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={DDR_TOKENS.surface.border} />
                  <XAxis dataKey="rig_id" name="Rig" stroke={DDR_TOKENS.text.muted} tick={{ fontSize: 8 }} interval={Math.floor(spc.data_points.length / 20)} />
                  <YAxis dataKey="value" name="NPT hrs" stroke={DDR_TOKENS.text.muted} tick={{ fontSize: 11 }} />
                  <RTooltip
                    contentStyle={{ background: DDR_TOKENS.bg.overlay, border: `1px solid ${DDR_TOKENS.surface.border}`, borderRadius: 8, fontSize: 11 }}
                    formatter={(v: number) => [`${v.toFixed(2)} hrs`, 'NPT']}
                    labelFormatter={(label: string) => `Rig: ${label}`}
                  />
                  <ReferenceLine y={spc.mean} stroke={DDR_TOKENS.status.normal} strokeDasharray="5 5" label={{ value: 'μ', position: 'right', style: { fontSize: 10, fill: DDR_TOKENS.status.normal } }} />
                  <ReferenceLine y={spc.ucl} stroke={DDR_TOKENS.status.critical} strokeDasharray="3 3" label={{ value: 'UCL', position: 'right', style: { fontSize: 10, fill: DDR_TOKENS.status.critical } }} />
                  <ReferenceLine y={spc.lcl} stroke={DDR_TOKENS.status.excellent} strokeDasharray="3 3" label={{ value: 'LCL', position: 'right', style: { fontSize: 10, fill: DDR_TOKENS.status.excellent } }} />
                  <Scatter data={spc.data_points} fill={DDR_TOKENS.status.normal}>
                    {spc.data_points.map((pt, i) => (
                      <Cell
                        key={i}
                        fill={pt.status === 'out_of_control' ? DDR_TOKENS.status.critical
                            : pt.status === 'warning' ? DDR_TOKENS.status.warning
                            : DDR_TOKENS.status.normal}
                      />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>
        </figure>
      )}

      {/* Rig-specific NPT Events */}
      {rigNPT && rigNPT.length > 0 && (
        <NPTEventsTable events={rigNPT} />
      )}
    </div>
  );
};

export default NPTIntelligence;
