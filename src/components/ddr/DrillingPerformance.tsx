// ============================================================================
// Drilling Performance Module — Module 2
// Rig detail: identity, depth KPIs, timeline, formation tops, well design
// ============================================================================

import React from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useRigDetail, useRigTimeline } from '@/api/hooks/useDDRHooks';
import RigIdentityBanner from './RigIdentityBanner';
import TimelineTable from './TimelineTable';
import KPICard from '@/components/KPICard';
import { LoadingState, EmptyState } from '@/components/ddr/state';
import { DDR_TOKENS } from '@/styles/tokens';
import { Check } from 'lucide-react';

interface DrillingPerformanceProps {
  rigId: string;
}

const DrillingPerformance: React.FC<DrillingPerformanceProps> = ({ rigId }) => {
  const { reportDate } = useDDR();
  const { data: rig, isLoading: rigLoading } = useRigDetail(rigId, reportDate);
  const { data: timeline, isLoading: timelineLoading } = useRigTimeline(rigId, reportDate);

  if (rigLoading) {
    return <LoadingState message="Loading drilling performance..." />;
  }

  if (!rig) {
    return <EmptyState title="No Rig Selected" message="Select a rig to view drilling performance" />;
  }

  const identity = rig.identity;
  const ds = rig.depth_summary;

  const makeKPI = (id: string, title: string, kv: any, icon: string) => ({
    kpi: {
      id,
      title,
      value: typeof kv?.value === 'number' ? kv.value : 0,
      unit: kv?.unit || '',
      change: '', changeType: 'neutral' as const,
      icon, color: '#00A651',
      status: kv?.status === 'critical' ? 'critical' as const
            : kv?.status === 'warning' ? 'warning' as const
            : 'good' as const,
    },
    kpiValue: kv,
    identity,
    ddrStatus: kv?.status,
    showStatusRing: true,
  });

  return (
    <div className="space-y-6">
      {/* Rig Identity Banner */}
      <RigIdentityBanner
        identity={identity}
        daysOnWell={typeof ds?.days_since_spud?.value === 'number' ? ds.days_since_spud.value : undefined}
      />

      {/* Depth KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <KPICard {...makeKPI('md', 'Current MD (ft)', ds?.current_md_ft, 'target')} />
        <KPICard {...makeKPI('tvd', 'Current TVD (ft)', ds?.current_tvd_ft, 'activity')} />
        <KPICard {...makeKPI('footage', 'Daily Footage (ft)', ds?.daily_footage_ft, 'trending_up')} />
        <KPICard {...makeKPI('days-spud', 'Days Since Spud', ds?.days_since_spud, 'clock')} />
        <KPICard {...makeKPI('circ', 'Circ %', ds?.circ_pct, 'percent')} />
        <KPICard {...makeKPI('rop', 'ROP (ft/hr)', rig.rop_ft_hr, 'trending_up')} />
      </div>

      {/* Current Operation */}
      {rig.current_operation && (
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary, border: `1px solid ${DDR_TOKENS.surface.border}` }}>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">Current Operation</div>
          <div className="text-sm text-white">{rig.current_operation}</div>
          <div className="mt-1 text-[10px] font-mono" style={{ color: DDR_TOKENS.citation.badgeText }}>
            {rig.current_operation_citation}
          </div>
        </div>
      )}

      {/* Depth Progress Bar */}
      {ds && (
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary }}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400">Depth Progress</span>
            <span className="text-xs font-mono text-cyan-400">
              {typeof ds.current_md_ft?.value === 'number' ? ds.current_md_ft.value.toLocaleString() : 0} ft
              → TD: {ds.target_td_ft.toLocaleString()} ft
            </span>
          </div>
          <div className="w-full h-3 rounded-full overflow-hidden" style={{ background: DDR_TOKENS.surface.s1 }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(ds.progress_pct, 100)}%`,
                background: ds.progress_pct >= 95 ? DDR_TOKENS.status.excellent : DDR_TOKENS.status.normal,
              }}
            />
          </div>
          <div className="text-right mt-1 text-xs font-bold" style={{ color: DDR_TOKENS.status.excellent }}>
            {ds.progress_pct.toFixed(1)}%
          </div>
        </div>
      )}

      {/* Well Design Milestones */}
      {rig.well_design_milestones && rig.well_design_milestones.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary }}>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-3">
            Well Design Milestones
          </h3>
          <div className="space-y-1.5">
            {rig.well_design_milestones.map((m, i) => (
              <div key={i} className="flex items-center gap-3 text-xs">
                <span className={`flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center ${
                  m.completed ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700/50 text-slate-500'
                }`}>
                  {m.completed ? <Check className="h-3 w-3" /> : <span className="w-1.5 h-1.5 rounded-full bg-current" />}
                </span>
                <span className="text-slate-300">
                  {m.hole_size} hole / {m.casing_size} @ {m.depth_ft.toLocaleString()} ft
                </span>
                <span
                  className="text-[10px] font-mono ml-auto"
                  style={{ color: DDR_TOKENS.citation.badgeText }}
                  title={m.source_citation}
                >
                  📋
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Formation Tops */}
      {rig.formation_tops && rig.formation_tops.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary }}>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-3">Formation Tops</h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-700/40">
                <th scope="col" className="text-left py-1.5 px-2 text-slate-500 uppercase font-semibold">Formation</th>
                <th scope="col" className="text-right py-1.5 px-2 text-slate-500 uppercase font-semibold">Top Depth (ft)</th>
                <th scope="col" className="text-left py-1.5 px-2 text-slate-500 uppercase font-semibold">Comments</th>
                <th scope="col" className="text-right py-1.5 px-2 text-slate-500 uppercase font-semibold">📋</th>
              </tr>
            </thead>
            <tbody>
              {rig.formation_tops.map((ft, i) => (
                <tr key={i} className="border-b border-slate-700/20">
                  <td className="py-1.5 px-2 text-white font-bold">{ft.formation}</td>
                  <td className="py-1.5 px-2 text-right font-mono text-cyan-400">{ft.top_depth_ft.toLocaleString()}</td>
                  <td className="py-1.5 px-2 text-slate-400">{ft.comments}</td>
                  <td className="py-1.5 px-2 text-right">
                    <span className="text-[10px] font-mono" style={{ color: DDR_TOKENS.citation.badgeText }} title={ft.source_citation}>📋</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 24-Hour Timeline */}
      {timelineLoading ? (
        <LoadingState message="Loading timeline..." />
      ) : timeline && timeline.length > 0 ? (
        <TimelineTable rows={timeline} />
      ) : null}
    </div>
  );
};

export default DrillingPerformance;
