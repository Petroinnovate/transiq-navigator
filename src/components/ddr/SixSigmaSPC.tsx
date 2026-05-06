// ============================================================================
// Six Sigma / SPC Analytics Module
// Fleet-wide Statistical Process Control with DMAIC visualizations
// ============================================================================

import React, { useState, useMemo } from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useFleetSPC, useFleetSummary } from '@/api/hooks/useDDRHooks';
import { LoadingState, ErrorState } from '@/components/ddr/state';
import { DDR_TOKENS } from '@/styles/tokens';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, ScatterChart, Scatter,
  Cell, BarChart, Bar, Legend,
} from 'recharts';
import { Activity, AlertTriangle, CheckCircle, Target, TrendingUp } from 'lucide-react';

const METRICS = [
  { key: 'rop', label: 'Rate of Penetration', unit: 'ft/hr' },
  { key: 'mud_weight', label: 'Mud Weight', unit: 'ppg' },
  { key: 'wob', label: 'Weight on Bit', unit: 'klbs' },
  { key: 'rpm', label: 'RPM', unit: 'rpm' },
  { key: 'torque', label: 'Torque', unit: 'kft-lbs' },
  { key: 'pump_pressure', label: 'Pump Pressure', unit: 'psi' },
  { key: 'flow_rate', label: 'Flow Rate', unit: 'gpm' },
];

const SixSigmaSPC: React.FC = () => {
  const { reportDate } = useDDR();
  const [selectedMetric, setSelectedMetric] = useState('rop');
  const date = reportDate || '';
  const { data: spcData, isLoading, error } = useFleetSPC(selectedMetric, date);
  const { data: fleetSummary } = useFleetSummary(date);

  const metricInfo = METRICS.find(m => m.key === selectedMetric) || METRICS[0];

  const controlChartData = useMemo(() => {
    if (!spcData?.spc?.control_chart) return [];
    return spcData.spc.control_chart.map((pt: { index: number; value: number; rig_id?: string; violation?: string }, i: number) => ({
      index: i + 1,
      value: pt.value,
      rigId: pt.rig_id || `Point ${i + 1}`,
      violation: pt.violation || null,
    }));
  }, [spcData]);

  const spc = spcData?.spc;

  const sigmaLevel = useMemo(() => {
    if (!spc?.dpmo && spc?.dpmo !== 0) return null;
    const dpmo = spc.dpmo;
    if (dpmo === 0) return 6;
    if (dpmo <= 3.4) return 6;
    if (dpmo <= 233) return 5;
    if (dpmo <= 6210) return 4;
    if (dpmo <= 66807) return 3;
    if (dpmo <= 308538) return 2;
    return 1;
  }, [spc]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Target className="h-6 w-6 text-cyan-400" />
            Six Sigma / SPC Analytics
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Statistical Process Control across the fleet — {date}
          </p>
        </div>
      </div>

      {/* Metric selector */}
      <div className="flex flex-wrap gap-2">
        {METRICS.map(m => (
          <button
            key={m.key}
            onClick={() => setSelectedMetric(m.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              selectedMetric === m.key
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                : 'bg-slate-800/60 text-slate-400 border border-slate-700/40 hover:bg-slate-700/60'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <LoadingState message={`Loading SPC data for ${metricInfo.label}...`} />
      )}

      {error && (
        <ErrorState message={`Insufficient data for SPC analysis on ${metricInfo.label}. Need ≥2 data points.`} />
      )}

      {spc && (
        <>
          {/* SPC Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <SummaryCard label="Data Points" value={spc.n} />
            <SummaryCard label="Mean" value={spc.mean?.toFixed(2)} unit={metricInfo.unit} />
            <SummaryCard label="Std Dev" value={spc.std?.toFixed(3)} />
            <SummaryCard label="Cp" value={spc.cp?.toFixed(3) ?? 'N/A'} status={spc.cp && spc.cp >= 1.33 ? 'good' : spc.cp && spc.cp >= 1 ? 'warn' : 'bad'} />
            <SummaryCard label="Cpk" value={spc.cpk?.toFixed(3) ?? 'N/A'} status={spc.cpk && spc.cpk >= 1.33 ? 'good' : spc.cpk && spc.cpk >= 1 ? 'warn' : 'bad'} />
            <SummaryCard label="Sigma Level" value={sigmaLevel ? `${sigmaLevel}σ` : 'N/A'} status={sigmaLevel && sigmaLevel >= 4 ? 'good' : sigmaLevel && sigmaLevel >= 3 ? 'warn' : 'bad'} />
          </div>

          {/* Control Status */}
          <div
            className="rounded-xl p-4 flex items-center gap-3"
            style={{
              background: spc.in_control
                ? 'rgba(16, 185, 129, 0.1)'
                : 'rgba(239, 68, 68, 0.1)',
              borderLeft: `4px solid ${spc.in_control ? DDR_TOKENS.status.onTarget : DDR_TOKENS.status.critical}`,
            }}
          >
            {spc.in_control ? (
              <CheckCircle className="h-5 w-5 text-emerald-400" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-red-400" />
            )}
            <div>
              <span className="font-bold text-white">
                {spc.in_control ? 'Process In Control' : 'Out of Control'}
              </span>
              <span className="text-sm text-slate-400 ml-2">
                {spc.violations?.length ? `${spc.violations.length} violation(s) detected` : 'No violations detected'}
              </span>
            </div>
          </div>

          {/* Control Chart */}
          <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary }}>
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-cyan-400" />
              Control Chart — {metricInfo.label} ({metricInfo.unit})
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 30, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="index"
                    name="Observation"
                    type="number"
                    stroke="#64748b"
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                    label={{ value: 'Observation #', position: 'bottom', fill: '#64748b', fontSize: 11 }}
                  />
                  <YAxis
                    dataKey="value"
                    name={metricInfo.label}
                    stroke="#64748b"
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0].payload;
                      return (
                        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 text-xs shadow-lg">
                          <div className="font-bold text-white">{d.rigId}</div>
                          <div className="text-cyan-300">{metricInfo.label}: {d.value?.toFixed(2)} {metricInfo.unit}</div>
                          {d.violation && <div className="text-red-400 mt-1">⚠ {d.violation}</div>}
                        </div>
                      );
                    }}
                  />
                  {/* UCL / LCL / Mean lines */}
                  <ReferenceLine y={spc.ucl} stroke={DDR_TOKENS.status.critical} strokeDasharray="5 5" label={{ value: `UCL ${spc.ucl?.toFixed(1)}`, fill: '#ef4444', fontSize: 10, position: 'right' }} />
                  <ReferenceLine y={spc.mean} stroke={DDR_TOKENS.brand.aramcoGreen} strokeDasharray="3 3" label={{ value: `μ ${spc.mean?.toFixed(1)}`, fill: '#10b981', fontSize: 10, position: 'right' }} />
                  <ReferenceLine y={spc.lcl} stroke={DDR_TOKENS.status.critical} strokeDasharray="5 5" label={{ value: `LCL ${spc.lcl?.toFixed(1)}`, fill: '#ef4444', fontSize: 10, position: 'right' }} />

                  <Scatter data={controlChartData} shape="circle">
                    {controlChartData.map((entry: { violation: string | null }, idx: number) => (
                      <Cell
                        key={idx}
                        fill={entry.violation ? '#ef4444' : '#06b6d4'}
                        r={entry.violation ? 6 : 4}
                      />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* DPMO & Capability */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* DPMO Card */}
            <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary }}>
              <h3 className="text-sm font-bold text-white mb-3">Defects Per Million Opportunities</h3>
              <div className="text-3xl font-mono font-bold text-cyan-300">
                {spc.dpmo != null ? spc.dpmo.toLocaleString() : 'N/A'}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Target: &lt; 3.4 DPMO (Six Sigma)
              </p>
              <div className="mt-4 h-2 rounded-full bg-slate-700 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${Math.min(100, 100 - (Math.log10(Math.max(1, spc.dpmo || 1)) / 6) * 100)}%`,
                    background: `linear-gradient(90deg, ${DDR_TOKENS.status.critical}, ${DDR_TOKENS.status.warning}, ${DDR_TOKENS.status.onTarget})`,
                  }}
                />
              </div>
            </div>

            {/* Violations Table */}
            <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary }}>
              <h3 className="text-sm font-bold text-white mb-3">
                Western Electric Rule Violations ({spc.violations?.length || 0})
              </h3>
              {spc.violations?.length ? (
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {spc.violations.map((v: string, i: number) => (
                    <div key={i} className="flex items-start gap-2 text-xs">
                      <AlertTriangle className="h-3.5 w-3.5 text-red-400 mt-0.5 flex-shrink-0" />
                      <span className="text-slate-300">{v}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm text-emerald-400">
                  <CheckCircle className="h-4 w-4" /> No violations detected
                </div>
              )}
            </div>
          </div>

          {/* Fleet comparison */}
          {fleetSummary?.kpis?.length > 0 && selectedMetric === 'rop' && (
            <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary }}>
              <h3 className="text-sm font-bold text-white mb-4">Fleet ROP Comparison</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={fleetSummary.kpis.filter((k: { rop: number | null }) => k.rop != null).slice(0, 20)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="rig_name" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 10 }} angle={-45} textAnchor="end" height={60} />
                    <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }}
                    />
                    <Bar dataKey="rop" fill="#06b6d4" radius={[4, 4, 0, 0]} name="ROP (ft/hr)" />
                    {spc.mean && <ReferenceLine y={spc.mean} stroke="#10b981" strokeDasharray="5 5" label={{ value: 'μ', fill: '#10b981', fontSize: 10 }} />}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

const SummaryCard: React.FC<{
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  status?: 'good' | 'warn' | 'bad';
}> = ({ label, value, unit, status }) => {
  const statusColor = status === 'good' ? DDR_TOKENS.status.onTarget : status === 'warn' ? DDR_TOKENS.status.warning : status === 'bad' ? DDR_TOKENS.status.critical : DDR_TOKENS.text.primary;

  return (
    <div className="rounded-xl p-3" style={{ background: DDR_TOKENS.bg.secondary }}>
      <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">{label}</div>
      <div className="text-lg font-mono font-bold" style={{ color: statusColor }}>
        {value ?? '—'}
        {unit && <span className="text-xs text-slate-500 ml-1">{unit}</span>}
      </div>
    </div>
  );
};

export default SixSigmaSPC;
