// ============================================================================
// Mud Comparison Table — Record 1 (Current) vs Record 2 (Previous)
// ============================================================================

import React from 'react';
import type { MudRecord, RigIdentity } from '@/types/ddr.types';
import { CitationBadge } from '@/components/citation/CitationBadge';
import { DDR_TOKENS } from '@/styles/tokens';

interface MudComparisonTableProps {
  records: MudRecord[];
  identity: RigIdentity;
}

const mudProperties = [
  { key: 'weight_pcf', label: 'Weight (PCF)' },
  { key: 'fl_temp_f', label: 'FL Temp (°F)' },
  { key: 'funnel_vis_sec', label: 'Funnel Vis (sec)' },
  { key: 'water_vol_pct', label: 'Water Vol (%)' },
  { key: 'oil_vol_pct', label: 'Oil Vol (%)' },
  { key: 'solids_vol_pct', label: 'Solids Vol (%)' },
  { key: 'pv', label: 'PV' },
  { key: 'yp', label: 'YP' },
  { key: 'ph', label: 'pH' },
  { key: 'cl_ppm', label: 'CL (PPM)' },
  { key: 'ca_ppm', label: 'CA (PPM)' },
  { key: 'gels_10sec', label: 'Gels 10sec' },
  { key: 'gels_10min', label: 'Gels 10min' },
] as const;

const MudComparisonTable: React.FC<MudComparisonTableProps> = ({ records, identity }) => {
  const rec1 = records.find(r => r.record_no === 1);
  const rec2 = records.find(r => r.record_no === 2);

  const getValue = (record: MudRecord | undefined, key: string): number | null => {
    const kv = (record as any)?.[key];
    if (!kv || kv.value === null || kv.value === undefined) return null;
    return typeof kv.value === 'number' ? kv.value : null;
  };

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: DDR_TOKENS.bg.secondary }}>
      <div className="p-4 border-b border-slate-700/40">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Mud Properties Comparison
        </h3>
        {rec1 && (
          <span className="text-xs text-slate-400">
            Mud Type: <span className="text-cyan-400">{rec1.mud_type}</span>
          </span>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-700/40">
              <th scope="col" className="text-left py-2 px-3 font-semibold text-slate-500 uppercase w-1/4">Property</th>
              <th scope="col" className="text-right py-2 px-3 font-semibold text-slate-500 uppercase w-1/4">Current</th>
              <th scope="col" className="text-right py-2 px-3 font-semibold text-slate-500 uppercase w-1/4">Previous</th>
              <th scope="col" className="text-right py-2 px-3 font-semibold text-slate-500 uppercase w-1/6">Δ Change</th>
              <th scope="col" className="text-right py-2 px-3 font-semibold text-slate-500 uppercase w-1/12">📋</th>
            </tr>
          </thead>
          <tbody>
            {mudProperties.map(({ key, label }) => {
              const v1 = getValue(rec1, key);
              const v2 = getValue(rec2, key);
              const delta = v1 !== null && v2 !== null ? v1 - v2 : null;
              const kv1 = (rec1 as any)?.[key];

              return (
                <tr key={key} className="border-b border-slate-700/20 hover:bg-slate-800/40 transition-colors">
                  <td className="py-1.5 px-3 text-slate-300">{label}</td>
                  <td className="py-1.5 px-3 text-right font-mono text-white">
                    {v1 !== null ? v1.toLocaleString() : '—'}
                  </td>
                  <td className="py-1.5 px-3 text-right font-mono text-slate-400">
                    {v2 !== null ? v2.toLocaleString() : '—'}
                  </td>
                  <td className="py-1.5 px-3 text-right font-mono">
                    {delta !== null ? (
                      <span className={delta > 0 ? 'text-amber-400' : delta < 0 ? 'text-cyan-400' : 'text-slate-500'}>
                        {delta > 0 ? '+' : ''}{delta.toFixed(1)}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="py-1.5 px-3 text-right">
                    {kv1 && (
                      <CitationBadge kpiValue={kv1} identity={identity} compact />
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default MudComparisonTable;
