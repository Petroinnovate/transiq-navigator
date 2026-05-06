// ============================================================================
// NPT Events Table — Sortable, filterable, expandable NPT/Lost Time events
// ============================================================================

import React, { useState, useMemo } from 'react';
import type { NPTEvent } from '@/types/ddr.types';
import { DDR_TOKENS } from '@/styles/tokens';
import { ArrowUpDown } from 'lucide-react';

interface NPTEventsTableProps {
  events: NPTEvent[];
}

type SortKey = 'hours_lost' | 'cause_code' | 'depth_ft' | 'event_from';

const NPTEventsTable: React.FC<NPTEventsTableProps> = ({ events }) => {
  const [sortBy, setSortBy] = useState<SortKey>('hours_lost');
  const [sortDesc, setSortDesc] = useState(true);
  const [filterCause, setFilterCause] = useState('');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const causeCodes = useMemo(() =>
    [...new Set(events.map(e => e.cause_code))].sort(),
    [events]
  );

  const sorted = useMemo(() => {
    let filtered = filterCause
      ? events.filter(e => e.cause_code === filterCause)
      : events;

    return [...filtered].sort((a, b) => {
      const va = a[sortBy];
      const vb = b[sortBy];
      if (typeof va === 'number' && typeof vb === 'number') {
        return sortDesc ? vb - va : va - vb;
      }
      return sortDesc
        ? String(vb).localeCompare(String(va))
        : String(va).localeCompare(String(vb));
    });
  }, [events, sortBy, sortDesc, filterCause]);

  const handleSort = (key: SortKey) => {
    if (sortBy === key) setSortDesc(!sortDesc);
    else { setSortBy(key); setSortDesc(true); }
  };

  const totalHours = sorted.reduce((sum, e) => sum + e.hours_lost, 0);

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: DDR_TOKENS.bg.secondary }}>
      <div className="p-4 border-b border-slate-700/40 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            NPT / Lost Time Events
          </h3>
          <span className="text-xs text-red-400">{sorted.length} events · {totalHours.toFixed(1)} total hours</span>
        </div>
        {/* Filter */}
        <select
          value={filterCause}
          onChange={(e) => setFilterCause(e.target.value)}
          className="text-xs bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-300"
          aria-label="Filter by cause code"
        >
          <option value="">All Causes</option>
          {causeCodes.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs" role="table">
          <thead>
            <tr className="border-b border-slate-700/40">
              <SortHeader label="From" sortKey="event_from" current={sortBy} desc={sortDesc} onClick={handleSort} />
              <SortHeader label="Hrs" sortKey="hours_lost" current={sortBy} desc={sortDesc} onClick={handleSort} />
              <th scope="col" className="text-left py-2 px-2 font-semibold text-slate-500 uppercase">Cum.Hrs</th>
              <th scope="col" className="text-left py-2 px-2 font-semibold text-slate-500 uppercase">Lt ID</th>
              <th scope="col" className="text-left py-2 px-2 font-semibold text-slate-500 uppercase">Type</th>
              <SortHeader label="Cause" sortKey="cause_code" current={sortBy} desc={sortDesc} onClick={handleSort} />
              <th scope="col" className="text-left py-2 px-2 font-semibold text-slate-500 uppercase">Object</th>
              <th scope="col" className="text-left py-2 px-2 font-semibold text-slate-500 uppercase">Resp</th>
              <SortHeader label="Depth" sortKey="depth_ft" current={sortBy} desc={sortDesc} onClick={handleSort} />
              <th scope="col" className="text-right py-2 px-2 font-semibold text-slate-500 uppercase">📋</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((evt) => (
              <React.Fragment key={evt.lt_id}>
                <tr
                  className="border-b border-slate-700/20 hover:bg-red-900/10 cursor-pointer transition-colors"
                  onClick={() => setExpandedRow(expandedRow === evt.lt_id ? null : evt.lt_id)}
                  aria-expanded={expandedRow === evt.lt_id}
                >
                  <td className="py-1.5 px-2 font-mono text-slate-300">{evt.event_from}</td>
                  <td className="py-1.5 px-2 font-mono text-red-400 font-bold">{evt.hours_lost}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-400">{evt.cum_hours}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-400">{evt.lt_id}</td>
                  <td className="py-1.5 px-2">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold text-red-400 bg-red-900/30">
                      {evt.npt_type}
                    </span>
                  </td>
                  <td className="py-1.5 px-2 text-slate-300">{evt.cause_code}</td>
                  <td className="py-1.5 px-2 text-slate-400">{evt.object_code}</td>
                  <td className="py-1.5 px-2 text-slate-400">{evt.resp_co}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-300">{evt.depth_ft.toLocaleString()}</td>
                  <td className="py-1.5 px-2 text-right">
                    <span
                      className="text-[10px] px-1 py-0.5 rounded font-mono"
                      style={{
                        background: DDR_TOKENS.citation.badge,
                        border: `1px solid ${DDR_TOKENS.citation.badgeBorder}`,
                        color: DDR_TOKENS.citation.badgeText,
                      }}
                      title={evt.source_citation}
                    >
                      📋
                    </span>
                  </td>
                </tr>
                {expandedRow === evt.lt_id && (
                  <tr className="border-b border-slate-700/20">
                    <td colSpan={10} className="p-3" style={{ background: DDR_TOKENS.bg.tertiary }}>
                      <div className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Lost Time Summary</div>
                      <div className="text-xs text-slate-300 mb-2">{evt.summary_text}</div>
                      <div className="text-xs text-slate-400">
                        <strong>Cause:</strong> {evt.cause_desc}
                      </div>
                      <div className="mt-2 text-[10px] font-mono" style={{ color: DDR_TOKENS.citation.badgeText }}>
                        {evt.source_citation}
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

// Sortable column header
const SortHeader: React.FC<{
  label: string;
  sortKey: SortKey;
  current: SortKey;
  desc: boolean;
  onClick: (key: SortKey) => void;
}> = ({ label, sortKey, current, desc, onClick }) => (
  <th scope="col" className="text-left py-2 px-2">
    <button
      onClick={() => onClick(sortKey)}
      className="flex items-center gap-1 text-slate-500 uppercase font-semibold text-xs hover:text-slate-300 transition-colors"
      aria-sort={current === sortKey ? (desc ? 'descending' : 'ascending') : 'none'}
    >
      {label}
      <ArrowUpDown className={`h-3 w-3 ${current === sortKey ? 'text-cyan-400' : ''}`} />
    </button>
  </th>
);

export default NPTEventsTable;
