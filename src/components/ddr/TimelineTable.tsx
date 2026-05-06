// ============================================================================
// Timeline Table — 24-hour operations timeline with color-coded rows
// ============================================================================

import React, { useState } from 'react';
import type { TimelineRow } from '@/types/ddr.types';
import { DDR_TOKENS } from '@/styles/tokens';

interface TimelineTableProps {
  rows: TimelineRow[];
}

const categoryColor = (category: string, ltType: string | null): string => {
  if (ltType && ltType !== '') return 'rgba(255,77,79,0.08)';   // NPT/Lost time = red tint
  switch (category?.toUpperCase()) {
    case 'PA': return 'rgba(0,208,132,0.06)';      // Productive = green tint
    case 'SDR1': return 'rgba(155,89,182,0.06)';   // Safety/meetings = purple tint
    case 'SB': return 'rgba(140,140,140,0.06)';    // Standby = gray tint
    default: return 'transparent';
  }
};

const TimelineTable: React.FC<TimelineTableProps> = ({ rows }) => {
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const totalHours = rows.reduce((sum, r) => sum + r.hours, 0);
  const nptHours = rows.filter(r => r.lt_type).reduce((sum, r) => sum + r.hours, 0);
  const productiveHours = totalHours - nptHours;

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: DDR_TOKENS.bg.secondary }}>
      <div className="p-4 border-b border-slate-700/40">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          24-Hour Operations Timeline
        </h3>
        <div className="flex gap-4 mt-2 text-xs">
          <span className="text-emerald-400">Productive: {productiveHours.toFixed(1)}h</span>
          <span className="text-red-400">NPT: {nptHours.toFixed(1)}h</span>
          <span className="text-slate-400">Total: {totalHours.toFixed(1)}h</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs" role="table">
          <thead>
            <tr className="border-b border-slate-700/40">
              {['Time', 'Hrs', 'Phase', 'Cat', 'Major OP', 'Action', 'Object', 'Resp', 'Hole Depth', 'Lt Type', '📋'].map(h => (
                <th key={h} scope="col" className="text-left py-2 px-2 font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <React.Fragment key={i}>
                <tr
                  className="border-b border-slate-700/20 hover:bg-slate-800/40 cursor-pointer transition-colors"
                  style={{ background: categoryColor(row.category, row.lt_type) }}
                  onClick={() => setExpandedRow(expandedRow === i ? null : i)}
                  aria-expanded={expandedRow === i}
                >
                  <td className="py-1.5 px-2 font-mono text-slate-300 whitespace-nowrap">
                    {row.time_from}–{row.time_to}
                  </td>
                  <td className="py-1.5 px-2 font-mono text-white">{row.hours}</td>
                  <td className="py-1.5 px-2 text-slate-300">{row.phase}</td>
                  <td className="py-1.5 px-2 text-slate-400">{row.category}</td>
                  <td className="py-1.5 px-2 text-slate-300">{row.major_op}</td>
                  <td className="py-1.5 px-2 text-slate-300">{row.action_code}</td>
                  <td className="py-1.5 px-2 text-slate-300">{row.object_code}</td>
                  <td className="py-1.5 px-2 text-slate-400">{row.resp_co}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-300">
                    {row.hole_depth_start.toLocaleString()}/{row.hole_depth_end.toLocaleString()}
                  </td>
                  <td className="py-1.5 px-2">
                    {row.lt_type && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold text-red-400 bg-red-900/30">
                        {row.lt_type}
                      </span>
                    )}
                  </td>
                  <td className="py-1.5 px-2">
                    <span
                      className="text-[10px] px-1 py-0.5 rounded font-mono cursor-help"
                      style={{
                        background: DDR_TOKENS.citation.badge,
                        border: `1px solid ${DDR_TOKENS.citation.badgeBorder}`,
                        color: DDR_TOKENS.citation.badgeText,
                      }}
                      title={row.source_citation}
                    >
                      📋
                    </span>
                  </td>
                </tr>
                {expandedRow === i && (
                  <tr className="border-b border-slate-700/20">
                    <td colSpan={11} className="p-3 text-slate-300 text-xs" style={{ background: DDR_TOKENS.bg.tertiary }}>
                      <div className="mb-1 text-slate-500 text-[10px] uppercase tracking-wider">Summary</div>
                      {row.summary_text}
                      <div className="mt-2 text-[10px] font-mono" style={{ color: DDR_TOKENS.citation.badgeText }}>
                        {row.source_citation}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TimelineTable;
