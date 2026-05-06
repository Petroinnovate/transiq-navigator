// ============================================================================
// Audit Trail Module — Append-only change log viewer for all DDR metrics
// Uses /api/v2/audit/changelog and /api/v2/audit/{rig_id}/{field_name}
// ============================================================================

import React, { useState } from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useAuditChangeLog, useFieldAudit, useRigList } from '@/api/hooks/useDDRHooks';
import { LoadingState, EmptyState } from '@/components/ddr/state';
import { DDR_TOKENS } from '@/styles/tokens';
import { Shield, Clock, Search, Filter, ChevronDown, ChevronRight, Eye } from 'lucide-react';

const SOURCE_COLORS: Record<string, string> = {
  regex: '#06b6d4',  // cyan
  ocr: '#8b5cf6',    // violet
  llm: '#f59e0b',    // amber
  imputed: '#ef4444', // red
  manual: '#10b981',  // emerald
};

const SOURCE_LABELS: Record<string, string> = {
  regex: 'Pattern Match',
  ocr: 'OCR Extraction',
  llm: 'LLM Extraction',
  imputed: 'Imputed Value',
  manual: 'Manual Edit',
};

const AuditTrail: React.FC = () => {
  const { reportDate, selectedRigId } = useDDR();
  const date = reportDate || '';
  const [filterRig, setFilterRig] = useState<string | undefined>(selectedRigId || undefined);
  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [detailRig, setDetailRig] = useState<string | null>(null);

  const { data: changeLog, isLoading } = useAuditChangeLog(date, filterRig);
  const { data: fieldDetail } = useFieldAudit(detailRig || '', selectedField || '', date);
  const { data: rigListData } = useRigList({ report_date: date });

  const rigs = rigListData?.rigs || rigListData || [];

  const handleViewField = (rigId: string, fieldName: string) => {
    setDetailRig(rigId);
    setSelectedField(fieldName);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Shield className="h-6 w-6 text-cyan-400" />
            Audit Trail
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Append-only change log for all extracted DDR metrics
          </p>
        </div>

        {/* Source legend */}
        <div className="flex items-center gap-3 flex-wrap">
          {Object.entries(SOURCE_LABELS).map(([key, label]) => (
            <div key={key} className="flex items-center gap-1.5 text-xs">
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: SOURCE_COLORS[key] }} />
              <span className="text-slate-400">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div
        className="rounded-xl p-4 flex items-center gap-4 flex-wrap"
        style={{ background: DDR_TOKENS.bg.secondary }}
      >
        <Filter className="h-4 w-4 text-slate-500" />

        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500">Rig:</label>
          <select
            value={filterRig || ''}
            onChange={(e) => setFilterRig(e.target.value || undefined)}
            className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-white text-xs focus:border-cyan-500 focus:outline-none"
          >
            <option value="">All Rigs</option>
            {(Array.isArray(rigs) ? rigs : []).map((r: { rig_id: string; name: string }) => (
              <option key={r.rig_id} value={r.rig_id}>{r.name}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Clock className="h-3.5 w-3.5" />
          Report Date: {date || 'All dates'}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Change Log Table */}
        <div className={`${selectedField ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
          <div
            className="rounded-xl overflow-hidden"
            style={{ background: DDR_TOKENS.bg.secondary }}
          >
            <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: DDR_TOKENS.surface.border }}>
              <h3 className="text-sm font-bold text-white">Recent Changes</h3>
              <span className="text-xs text-slate-500">
                {Array.isArray(changeLog) ? changeLog.length : 0} entries
              </span>
            </div>

            {isLoading ? (
              <LoadingState message="Loading audit trail..." />
            ) : !changeLog || (Array.isArray(changeLog) && changeLog.length === 0) ? (
              <EmptyState title="No Audit Entries" message="No audit entries found for the selected filters" />
            ) : (
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0" style={{ background: DDR_TOKENS.bg.secondary }}>
                    <tr className="text-left text-slate-500 border-b" style={{ borderColor: DDR_TOKENS.surface.border }}>
                      <th className="px-4 py-2 font-medium">Timestamp</th>
                      <th className="px-4 py-2 font-medium">Rig</th>
                      <th className="px-4 py-2 font-medium">Field</th>
                      <th className="px-4 py-2 font-medium">Old</th>
                      <th className="px-4 py-2 font-medium">New</th>
                      <th className="px-4 py-2 font-medium">Source</th>
                      <th className="px-4 py-2 font-medium">Origin</th>
                      <th className="px-4 py-2 font-medium"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {(Array.isArray(changeLog) ? changeLog : []).map((entry: {
                      id: string;
                      timestamp?: string;
                      rig_name?: string;
                      field_name: string;
                      old_value?: string;
                      new_value?: string;
                      source_method?: string;
                      origin?: string;
                      change_reason?: string;
                      report_id?: string;
                    }, idx: number) => (
                      <tr
                        key={entry.id || idx}
                        className="border-b hover:bg-slate-800/40 transition-colors"
                        style={{ borderColor: 'rgba(51, 65, 85, 0.3)' }}
                      >
                        <td className="px-4 py-2 text-slate-400 whitespace-nowrap">
                          {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : '—'}
                        </td>
                        <td className="px-4 py-2 text-white font-mono">
                          {entry.rig_name || '—'}
                        </td>
                        <td className="px-4 py-2 text-cyan-300 font-mono">
                          {entry.field_name}
                        </td>
                        <td className="px-4 py-2 text-red-400/70 font-mono">
                          {entry.old_value || '—'}
                        </td>
                        <td className="px-4 py-2 text-emerald-400 font-mono font-bold">
                          {entry.new_value || '—'}
                        </td>
                        <td className="px-4 py-2">
                          <span
                            className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                            style={{
                              background: `${SOURCE_COLORS[entry.source_method || ''] || '#64748b'}20`,
                              color: SOURCE_COLORS[entry.source_method || ''] || '#64748b',
                            }}
                          >
                            {entry.source_method || 'unknown'}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-slate-500">
                          {entry.origin || '—'}
                        </td>
                        <td className="px-4 py-2">
                          <button
                            onClick={() => handleViewField(entry.report_id || '', entry.field_name)}
                            className="text-cyan-500 hover:text-cyan-300 transition-colors"
                            title="View field history"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Field Detail Panel */}
        {selectedField && (
          <div
            className="rounded-xl overflow-hidden"
            style={{ background: DDR_TOKENS.bg.secondary }}
          >
            <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: DDR_TOKENS.surface.border }}>
              <h3 className="text-sm font-bold text-white">
                Field History
              </h3>
              <button
                onClick={() => { setSelectedField(null); setDetailRig(null); }}
                className="text-xs text-slate-500 hover:text-slate-300"
              >
                ✕ Close
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div className="text-xs">
                <span className="text-slate-500">Field:</span>{' '}
                <span className="text-cyan-300 font-mono">{selectedField}</span>
              </div>

              {fieldDetail && typeof fieldDetail === 'object' && (
                <div className="space-y-2">
                  {(fieldDetail as { history?: Array<{ id: string; value: string; old_value?: string; timestamp?: string; source?: string; origin?: string; change_reason?: string }> })?.history?.map((h, idx: number) => (
                    <div
                      key={h.id || idx}
                      className="p-2 rounded-lg border"
                      style={{ background: DDR_TOKENS.bg.primary, borderColor: DDR_TOKENS.surface.border }}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-white font-mono text-sm">{h.value}</span>
                        <span
                          className="px-1.5 py-0.5 rounded text-[10px]"
                          style={{
                            background: `${SOURCE_COLORS[h.source || ''] || '#64748b'}20`,
                            color: SOURCE_COLORS[h.source || ''] || '#64748b',
                          }}
                        >
                          {h.source}
                        </span>
                      </div>
                      {h.old_value && (
                        <div className="text-[10px] text-slate-500 mt-1">
                          Changed from: <span className="text-red-400/70">{h.old_value}</span>
                        </div>
                      )}
                      {h.change_reason && (
                        <div className="text-[10px] text-slate-400 mt-1">
                          Reason: {h.change_reason}
                        </div>
                      )}
                      <div className="text-[10px] text-slate-600 mt-1 flex items-center gap-1">
                        <Clock className="h-2.5 w-2.5" />
                        {h.timestamp ? new Date(h.timestamp).toLocaleString() : '—'}
                        {h.origin && <> • {h.origin}</>}
                      </div>
                    </div>
                  )) ?? (
                    <div className="text-xs text-slate-500">No history found</div>
                  )}
                </div>
              )}

              {!fieldDetail && (
                <div className="text-xs text-slate-500">Loading field history...</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditTrail;
