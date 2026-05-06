// ============================================================================
// Drill String / BHA Diagram — Visual representation of Bottom Hole Assembly
// ============================================================================

import React from 'react';
import type { BHAComponent } from '@/types/ddr.types';
import { DDR_TOKENS } from '@/styles/tokens';

interface DrillStringDiagramProps {
  components: BHAComponent[];
}

const DrillStringDiagram: React.FC<DrillStringDiagramProps> = ({ components }) => {
  const sorted = [...components].sort((a, b) => a.order - b.order);
  const maxLength = Math.max(...sorted.map(c => c.cum_length_ft), 1);

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: DDR_TOKENS.bg.secondary }}>
      <div className="p-4 border-b border-slate-700/40">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Drill String / BHA Composition
        </h3>
        <span className="text-xs text-slate-400">{sorted.length} components</span>
      </div>

      {/* Visual diagram */}
      <div className="p-4 flex gap-6">
        {/* Bar diagram */}
        <div className="w-24 flex-shrink-0 flex flex-col items-center gap-0.5">
          {sorted.map((c) => {
            const heightPct = Math.max((c.length_ft / maxLength) * 100, 3);
            return (
              <div
                key={c.order}
                className="w-12 rounded-sm relative group cursor-help"
                style={{
                  height: `${heightPct}%`,
                  minHeight: 8,
                  background: c.provider === 'RIG' ? DDR_TOKENS.chart.c1
                            : c.provider === 'HCB' ? DDR_TOKENS.chart.c3
                            : DDR_TOKENS.chart.c2,
                  border: `1px solid ${DDR_TOKENS.surface.border}`,
                }}
                title={`${c.component} — ${c.length_ft.toLocaleString()} ft`}
              >
                <span className="absolute inset-0 flex items-center justify-center text-[7px] text-white/80 font-mono">
                  {c.order}
                </span>
              </div>
            );
          })}
        </div>

        {/* Detail table */}
        <div className="flex-1 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-700/40">
                {['#', 'Component', 'Provider', 'JTS', 'OD"', 'ID"', 'Length', 'Cum Len', 'Wt lb/ft', '📋'].map(h => (
                  <th key={h} scope="col" className="text-left py-1.5 px-2 font-semibold text-slate-500 uppercase whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map(c => (
                <tr key={c.order} className="border-b border-slate-700/20 hover:bg-slate-800/40">
                  <td className="py-1 px-2 font-mono text-slate-400">{c.order}</td>
                  <td className="py-1 px-2 text-white font-medium truncate max-w-[200px]" title={c.component}>
                    {c.component}
                  </td>
                  <td className="py-1 px-2 text-slate-400">{c.provider}</td>
                  <td className="py-1 px-2 font-mono text-slate-300">{c.joints}</td>
                  <td className="py-1 px-2 font-mono text-slate-300">{c.od_in}</td>
                  <td className="py-1 px-2 font-mono text-slate-300">{c.id_in}</td>
                  <td className="py-1 px-2 font-mono text-cyan-400">{c.length_ft.toLocaleString()}</td>
                  <td className="py-1 px-2 font-mono text-slate-300">{c.cum_length_ft.toLocaleString()}</td>
                  <td className="py-1 px-2 font-mono text-slate-400">{c.weight_lb_ft}</td>
                  <td className="py-1 px-2">
                    <span
                      className="text-[10px] px-1 py-0.5 rounded font-mono"
                      style={{
                        background: DDR_TOKENS.citation.badge,
                        border: `1px solid ${DDR_TOKENS.citation.badgeBorder}`,
                        color: DDR_TOKENS.citation.badgeText,
                      }}
                      title={c.source_citation}
                    >
                      📋
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DrillStringDiagram;
