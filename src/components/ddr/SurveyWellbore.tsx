// ============================================================================
// Survey & Wellbore Module — Module 8
// Survey table, directional notes, DLS chart
// ============================================================================

import React from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useRigDetail, useRigSurvey } from '@/api/hooks/useDDRHooks';
import RigIdentityBanner from './RigIdentityBanner';
import { LoadingState, EmptyState } from '@/components/ddr/state';
import { DDR_TOKENS } from '@/styles/tokens';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';

interface SurveyWellboreProps {
  rigId: string;
}

const SurveyWellbore: React.FC<SurveyWellboreProps> = ({ rigId }) => {
  const { reportDate } = useDDR();
  const { data: rig } = useRigDetail(rigId, reportDate);
  const { data: surveys, isLoading } = useRigSurvey(rigId, reportDate);

  if (isLoading) return <LoadingState message="Loading survey & wellbore data..." />;
  if (!rig || !surveys) return <EmptyState title="No Survey Data" message="Select a rig to view survey & wellbore data" />;

  return (
    <div className="space-y-6">
      <RigIdentityBanner identity={rig.identity} />

      {/* Survey Table */}
      <div className="rounded-xl overflow-hidden" style={{ background: DDR_TOKENS.bg.secondary }}>
        <div className="p-4 border-b border-slate-700/40">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Daily Survey Table</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-700/40">
                {['Lateral', 'MD (ft)', 'Incl (°)', 'Azim (°)', 'TVD (ft)', 'N/S (ft)', 'E/W (ft)', 'V.Sec (ft)', 'DLS (°/100ft)', '📋'].map(h => (
                  <th key={h} scope="col" className="text-left py-2 px-2 font-semibold text-slate-500 uppercase whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {surveys.map((s, i) => (
                <tr key={i} className="border-b border-slate-700/20 hover:bg-slate-800/40">
                  <td className="py-1.5 px-2 font-mono text-slate-400">{s.lateral}</td>
                  <td className="py-1.5 px-2 font-mono text-white">{s.survey_md_ft.toLocaleString()}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-300">{s.angle_deg.toFixed(1)}°</td>
                  <td className="py-1.5 px-2 font-mono text-slate-300">{s.azimuth_deg.toFixed(1)}°</td>
                  <td className="py-1.5 px-2 font-mono text-cyan-400">{s.tvd_ft.toLocaleString()}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-300">{s.ns_coord.toFixed(2)}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-300">{s.ew_coord.toFixed(2)}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-300">{s.vertical_sec.toFixed(1)}</td>
                  <td className="py-1.5 px-2 font-mono">
                    <span className={s.dls_deg_100ft > 3 ? 'text-red-400 font-bold' : 'text-slate-300'}>
                      {s.dls_deg_100ft.toFixed(2)}
                    </span>
                  </td>
                  <td className="py-1.5 px-2">
                    <span
                      className="text-[10px] px-1 py-0.5 rounded font-mono"
                      style={{ background: DDR_TOKENS.citation.badge, border: `1px solid ${DDR_TOKENS.citation.badgeBorder}`, color: DDR_TOKENS.citation.badgeText }}
                      title={s.source_citation}
                    >📋</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* DLS Chart */}
      {surveys.length > 1 && (
        <figure role="img" aria-labelledby="dls-chart-title">
          <div className="rounded-xl p-6" style={{ background: DDR_TOKENS.bg.secondary }}>
            <figcaption id="dls-chart-title" className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-4">
              Dog Leg Severity (DLS) vs Measured Depth
            </figcaption>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={surveys} margin={{ top: 10, right: 30, left: 20, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={DDR_TOKENS.surface.border} />
                  <XAxis dataKey="survey_md_ft" stroke={DDR_TOKENS.text.muted} tick={{ fontSize: 10 }} label={{ value: 'MD (ft)', position: 'insideBottom', offset: -5, style: { fontSize: 10, fill: DDR_TOKENS.text.muted } }} />
                  <YAxis stroke={DDR_TOKENS.text.muted} tick={{ fontSize: 10 }} label={{ value: 'DLS (°/100ft)', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: DDR_TOKENS.text.muted } }} />
                  <RTooltip
                    contentStyle={{ background: DDR_TOKENS.bg.overlay, border: `1px solid ${DDR_TOKENS.surface.border}`, borderRadius: 8, fontSize: 11 }}
                    formatter={(v: number) => [`${v.toFixed(2)} °/100ft`, 'DLS']}
                    labelFormatter={(v: number) => `MD: ${Number(v).toLocaleString()} ft`}
                  />
                  <ReferenceLine y={3} stroke={DDR_TOKENS.status.critical} strokeDasharray="3 3" label={{ value: 'Alert 3°', position: 'right', style: { fontSize: 10, fill: DDR_TOKENS.status.critical } }} />
                  <Line type="monotone" dataKey="dls_deg_100ft" stroke={DDR_TOKENS.chart.c1} strokeWidth={2} dot={{ fill: DDR_TOKENS.chart.c1, r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </figure>
      )}
    </div>
  );
};

export default SurveyWellbore;
