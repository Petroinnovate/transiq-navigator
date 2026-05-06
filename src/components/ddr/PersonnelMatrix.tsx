// ============================================================================
// Personnel Matrix Table — Full category breakdown with citations
// ============================================================================

import React from 'react';
import type { PersonnelRow, RigIdentity } from '@/types/ddr.types';
import { DDR_TOKENS } from '@/styles/tokens';

interface PersonnelMatrixProps {
  rows: PersonnelRow[];
  identity: RigIdentity;
}

const PersonnelMatrix: React.FC<PersonnelMatrixProps> = ({ rows, identity }) => {
  const totalPersons = rows.reduce((sum, r) => sum + r.num_persons, 0);

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: DDR_TOKENS.bg.secondary }}>
      <div className="p-4 border-b border-slate-700/40">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Personnel Matrix
        </h3>
        <span className="text-xs text-cyan-400">{totalPersons} total on location</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs" role="table">
          <thead>
            <tr className="border-b border-slate-700/40">
              <th scope="col" className="text-left py-2 px-3 font-semibold text-slate-500 uppercase">Category</th>
              <th scope="col" className="text-left py-2 px-3 font-semibold text-slate-500 uppercase">Code</th>
              <th scope="col" className="text-right py-2 px-3 font-semibold text-slate-500 uppercase"># Persons</th>
              <th scope="col" className="text-right py-2 px-3 font-semibold text-slate-500 uppercase">On Loc Hrs</th>
              <th scope="col" className="text-right py-2 px-3 font-semibold text-slate-500 uppercase">Oper Hrs</th>
              <th scope="col" className="text-right py-2 px-3 font-semibold text-slate-500 uppercase">📋</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.category_code}
                className="border-b border-slate-700/20 hover:bg-slate-800/40 transition-colors"
              >
                <td className="py-1.5 px-3 text-slate-300">{row.category_desc}</td>
                <td className="py-1.5 px-3 font-mono text-slate-400">{row.category_code}</td>
                <td className="py-1.5 px-3 text-right font-mono text-white font-bold">{row.num_persons}</td>
                <td className="py-1.5 px-3 text-right font-mono text-slate-400">{row.personnel_hrs}</td>
                <td className="py-1.5 px-3 text-right font-mono text-slate-400">{row.operating_hrs}</td>
                <td className="py-1.5 px-3 text-right">
                  <span
                    className="text-[10px] px-1 py-0.5 rounded font-mono"
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
            ))}
            {/* Total row */}
            <tr className="border-t-2 border-slate-600/60 bg-slate-800/40">
              <td className="py-2 px-3 text-white font-bold">TOTAL</td>
              <td className="py-2 px-3" />
              <td className="py-2 px-3 text-right font-mono text-white font-bold">{totalPersons}</td>
              <td className="py-2 px-3 text-right font-mono text-slate-400">—</td>
              <td className="py-2 px-3 text-right font-mono text-slate-400">—</td>
              <td className="py-2 px-3" />
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PersonnelMatrix;
