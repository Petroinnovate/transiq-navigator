// ============================================================================
// Fleet Heatmap — 267 coloured tiles showing all rigs at a glance
// flex-wrap layout with w-4 h-4 tiles for compact density
// ============================================================================

import React, { useMemo } from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useFleetHeatmap } from '@/api/hooks/useDDRHooks';
import { LoadingState, EmptyState } from '@/components/ddr/state';
import type { FleetHeatmapTile } from '@/types/ddr.types';
import { DDR_TOKENS } from '@/styles/tokens';

const statusColor = (status: FleetHeatmapTile['status']): string => {
  switch (status) {
    case 'drilling': return DDR_TOKENS.status.drilling;
    case 'critical': return DDR_TOKENS.status.critical;
    case 'standby': return DDR_TOKENS.status.standby;
    case 'completion': return DDR_TOKENS.status.completion;
    default: return DDR_TOKENS.status.normal;
  }
};

const statusLabel = (status: FleetHeatmapTile['status']): string => {
  switch (status) {
    case 'drilling': return 'Drilling';
    case 'critical': return 'Critical';
    case 'standby': return 'Standby';
    case 'completion': return 'Completion';
    default: return 'Normal';
  }
};

const nptColor = (nptPct: number): string => {
  if (nptPct > 20) return DDR_TOKENS.status.critical;
  if (nptPct > 10) return DDR_TOKENS.status.warning;
  return DDR_TOKENS.status.excellent;
};

interface FleetHeatmapProps {
  onRigSelect?: (rigId: string) => void;
}

const FleetHeatmap: React.FC<FleetHeatmapProps> = ({ onRigSelect }) => {
  const { reportDate } = useDDR();
  const { data: tiles, isLoading } = useFleetHeatmap(reportDate);

  const legend = useMemo(() => [
    { status: 'drilling' as const, label: 'Drilling', color: DDR_TOKENS.status.drilling },
    { status: 'normal' as const, label: 'Normal', color: DDR_TOKENS.status.normal },
    { status: 'standby' as const, label: 'Standby', color: DDR_TOKENS.status.standby },
    { status: 'completion' as const, label: 'Completion', color: DDR_TOKENS.status.completion },
    { status: 'critical' as const, label: 'Critical', color: DDR_TOKENS.status.critical },
  ], []);

  // Count rigs per status
  const statusCounts = useMemo(() => {
    if (!tiles) return {};
    return tiles.reduce<Record<string, number>>((acc, t) => {
      acc[t.status] = (acc[t.status] || 0) + 1;
      return acc;
    }, {});
  }, [tiles]);

  if (isLoading) {
    return <LoadingState message="Loading fleet heatmap..." />;
  }

  if (!tiles || tiles.length === 0) {
    return <EmptyState title="No Heatmap Data" message="No heatmap data available for the selected report date" />;
  }

  return (
    <figure role="img" aria-labelledby="fleet-heatmap-title">
      <div className="rounded-xl p-6" style={{ background: DDR_TOKENS.bg.secondary }}>
        {/* Header + Legend */}
        <div className="flex items-center justify-between mb-4">
          <figcaption id="fleet-heatmap-title" className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            Fleet Status Heatmap — {tiles.length} Rigs
          </figcaption>
          <div className="flex items-center gap-3">
            {legend.map(l => (
              <div key={l.status} className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-[2px]" style={{ background: l.color }} />
                <span className="text-[10px] text-slate-400">
                  {l.label}
                  {statusCounts[l.status] != null && (
                    <span className="text-slate-500 ml-0.5">({statusCounts[l.status]})</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Flex-wrap tile grid — drillsight pattern */}
        <div
          className="flex flex-wrap gap-[3px]"
          role="grid"
          aria-label="Rig status grid"
        >
          {tiles.map((tile) => (
            <button
              key={tile.rig_id}
              onClick={() => onRigSelect?.(tile.rig_id)}
              className="w-4 h-4 rounded-[2px] transition-all duration-150 hover:scale-150 hover:z-10 relative group cursor-pointer border border-transparent hover:border-white/40"
              style={{ background: statusColor(tile.status) }}
              aria-label={`Rig ${tile.rig_id}: ${tile.well_id}, ${statusLabel(tile.status)}, ${tile.current_md_ft.toLocaleString()} ft MD${tile.rop_ft_hr != null ? `, ROP ${tile.rop_ft_hr} ft/hr` : ''}, NPT ${tile.npt_pct}%`}
              title={`${tile.rig_id} | ${tile.well_id}`}
            >
              {/* Tooltip */}
              <div
                className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-52 p-2.5 rounded-lg opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 text-[10px] shadow-lg"
                style={{
                  background: 'hsl(222 40% 8%)',
                  border: `1px solid ${DDR_TOKENS.surface.border}`,
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-white font-bold">{tile.rig_id}</span>
                  <span
                    className="px-1.5 py-0.5 rounded-[3px] text-[8px] font-bold uppercase"
                    style={{ background: statusColor(tile.status), color: '#fff' }}
                  >
                    {tile.status}
                  </span>
                </div>
                <div className="text-cyan-400 text-[9px] mt-0.5 font-mono">{tile.well_id}</div>
                <div className="mt-1.5 space-y-0.5 text-slate-400">
                  <div className="flex justify-between">
                    <span>Depth:</span>
                    <span className="text-white font-mono">{tile.current_md_ft.toLocaleString()} ft</span>
                  </div>
                  <div className="flex justify-between">
                    <span>ROP:</span>
                    <span className="text-white font-mono">{tile.rop_ft_hr != null ? `${tile.rop_ft_hr.toFixed(1)} ft/hr` : 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>NPT:</span>
                    <span className="font-mono font-bold" style={{ color: nptColor(tile.npt_pct) }}>
                      {tile.npt_pct}%
                    </span>
                  </div>
                </div>
                <div className="mt-1.5 text-[9px] text-slate-500 border-t border-slate-700/50 pt-1 truncate">
                  {tile.last_operation}
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Accessible data table (screen reader only) */}
        <table className="sr-only">
          <caption>Fleet Status Heatmap — {tiles.length} Rigs Data Table</caption>
          <thead>
            <tr>
              <th scope="col">Rig ID</th>
              <th scope="col">Well ID</th>
              <th scope="col">Status</th>
              <th scope="col">Current MD (ft)</th>
              <th scope="col">ROP (ft/hr)</th>
              <th scope="col">NPT %</th>
            </tr>
          </thead>
          <tbody>
            {tiles.map(t => (
              <tr key={t.rig_id}>
                <td>{t.rig_id}</td>
                <td>{t.well_id}</td>
                <td>{t.status}</td>
                <td>{t.current_md_ft}</td>
                <td>{t.rop_ft_hr ?? 'N/A'}</td>
                <td>{t.npt_pct}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
};

export default FleetHeatmap;
