import React, { useState } from 'react';
import type { RigSummary } from '@/data/mockData';

interface Props {
  rigs: RigSummary[];
}

const statusColors: Record<string, string> = {
  normal: 'bg-ddr-drilling',
  warning: 'bg-ddr-warning',
  critical: 'bg-ddr-critical',
  standby: 'bg-ddr-standby',
};

export const RigHeatmap: React.FC<Props> = ({ rigs }) => {
  const [hovered, setHovered] = useState<RigSummary | null>(null);

  return (
    <div className="card-surface p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">Rig Status Heatmap — {rigs.length} Rigs</h3>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-ddr-drilling" /> Drilling</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-ddr-warning" /> Warning</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-ddr-critical" /> Critical</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-ddr-standby" /> Standby</span>
        </div>
      </div>
      <div className="flex flex-wrap gap-[3px] relative">
        {rigs.map(rig => (
          <div
            key={rig.rig_id}
            className={`w-4 h-4 rounded-[2px] ${statusColors[rig.status]} cursor-pointer transition-transform hover:scale-150 hover:z-10`}
            onMouseEnter={() => setHovered(rig)}
            onMouseLeave={() => setHovered(null)}
            title={`${rig.rig_id} · ${rig.well_id}`}
          />
        ))}
      </div>
      {hovered && (
        <div className="mt-3 card-surface p-2 text-xs flex flex-wrap gap-x-4 gap-y-1 border border-border">
          <span><span className="text-muted-foreground">Rig:</span> <span className="font-medium">{hovered.rig_id}</span></span>
          <span><span className="text-muted-foreground">Well:</span> {hovered.well_id}</span>
          <span><span className="text-muted-foreground">Depth:</span> {hovered.current_depth_ft.toLocaleString()} ft</span>
          <span><span className="text-muted-foreground">ROP:</span> {hovered.rop_ft_hr} ft/hr</span>
          <span><span className="text-muted-foreground">NPT:</span> <span className={hovered.npt_pct > 20 ? 'text-ddr-critical' : hovered.npt_pct > 10 ? 'text-ddr-warning' : 'text-ddr-excellent'}>{hovered.npt_pct}%</span></span>
        </div>
      )}
    </div>
  );
};
