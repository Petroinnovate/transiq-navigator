import React, { useState } from 'react';
import type { RigSummary } from '@/data/mockData';
import { CitationBadge } from './CitationBadge';

interface Props {
  rigs: RigSummary[];
}

export const TopPerformersTable: React.FC<Props> = ({ rigs }) => {
  const [tab, setTab] = useState<'top' | 'bottom'>('top');
  const activeRigs = rigs.filter(r => r.status !== 'standby');
  const sorted = [...activeRigs].sort((a, b) => tab === 'top' ? b.daily_footage_ft - a.daily_footage_ft : a.rop_ft_hr - b.rop_ft_hr);
  const top10 = sorted.slice(0, 10);

  return (
    <div className="card-surface p-4 h-full">
      <div className="flex items-center gap-3 mb-3">
        <h3 className="text-sm font-semibold text-foreground">Fleet Performers</h3>
        <div className="flex gap-1 text-[10px]">
          <button onClick={() => setTab('top')} className={`px-2 py-0.5 rounded ${tab === 'top' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>Top 10</button>
          <button onClick={() => setTab('bottom')} className={`px-2 py-0.5 rounded ${tab === 'bottom' ? 'bg-ddr-critical text-foreground' : 'bg-muted text-muted-foreground'}`}>Bottom 10</button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-foreground border-b border-border">
              <th className="text-left py-1.5 font-medium">#</th>
              <th className="text-left py-1.5 font-medium">Rig</th>
              <th className="text-left py-1.5 font-medium">Well</th>
              <th className="text-right py-1.5 font-medium">Footage</th>
              <th className="text-right py-1.5 font-medium">ROP</th>
              <th className="text-right py-1.5 font-medium">NPT%</th>
              <th className="text-right py-1.5 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {top10.map((r, i) => (
              <tr key={r.rig_id} className="border-b border-border/50 hover:bg-accent/30">
                <td className="py-1.5 text-muted-foreground">{i + 1}</td>
                <td className="py-1.5 font-medium font-mono-data">{r.rig_id}</td>
                <td className="py-1.5 text-muted-foreground">{r.well_id}</td>
                <td className="py-1.5 text-right font-mono-data">{r.daily_footage_ft}</td>
                <td className="py-1.5 text-right font-mono-data">{r.rop_ft_hr}</td>
                <td className={`py-1.5 text-right font-mono-data ${r.npt_pct > 20 ? 'text-ddr-critical' : r.npt_pct > 10 ? 'text-ddr-warning' : 'text-ddr-excellent'}`}>{r.npt_pct}%</td>
                <td className="py-1.5 text-right">
                  <CitationBadge citation={`${r.rig_id}–Pg1–Summary`} compact />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
