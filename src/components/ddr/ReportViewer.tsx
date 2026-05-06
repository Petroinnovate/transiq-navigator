// @ts-nocheck
// ============================================================================
// Report Viewer Module — Browse, upload, and view DDR reports
// Uses /api/v2/ddr/reports, /api/v2/ddr/parse-upload, /api/v2/ddr/metrics
// ============================================================================

import React, { useState, useCallback } from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useReportList, useUploadReport } from '@/api/hooks/useDDRHooks';
import axios from '@/lib/axios';
import { LoadingState, EmptyState } from '@/components/ddr/state';
import { DDR_TOKENS } from '@/styles/tokens';
import {
  FileText, Upload, Calendar, Search, ChevronRight,
  CheckCircle, AlertTriangle, Loader2, X, Eye,
} from 'lucide-react';

interface ReportMetric {
  id: string;
  field_name: string;
  value: string;
  numeric_value: number | null;
  confidence_score: number | null;
  extraction_method: string;
  citation: string | null;
  is_imputed: boolean;
}

const ReportViewer: React.FC = () => {
  const { setReportDate, setSelectedRigId } = useDDR();
  const { data: reports, isLoading, refetch } = useReportList();
  const uploadMutation = useUploadReport();

  const [searchQuery, setSearchQuery] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [uploadResult, setUploadResult] = useState<Record<string, unknown> | null>(null);
  const [selectedReport, setSelectedReport] = useState<string | null>(null);
  const [reportMetrics, setReportMetrics] = useState<ReportMetric[]>([]);
  const [metricsLoading, setMetricsLoading] = useState(false);

  const filteredReports = (reports || []).filter((r: { well_name?: string; rig_name?: string; field_name?: string; report_number?: string }) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (r.well_name || '').toLowerCase().includes(q) ||
      (r.rig_name || '').toLowerCase().includes(q) ||
      (r.field_name || '').toLowerCase().includes(q) ||
      (r.report_number || '').toLowerCase().includes(q)
    );
  });

  const handleUpload = async (file: File) => {
    try {
      const result = await uploadMutation.mutateAsync(file);
      setUploadResult(result as Record<string, unknown>);
      refetch();
    } catch {
      setUploadResult({ error: 'Upload failed. Please check the file format.' });
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
      handleUpload(file);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const viewReport = async (reportId: string) => {
    setSelectedReport(reportId);
    setMetricsLoading(true);
    try {
      const { data } = await axios.get(`/api/v2/ddr/metrics/${reportId}`);
      setReportMetrics(data?.metrics || []);
    } catch {
      setReportMetrics([]);
    }
    setMetricsLoading(false);
  };

  const navigateToReport = (report: { report_date?: string; rig_id?: string }) => {
    if (report.report_date) {
      const dateStr = report.report_date.split('T')[0];
      setReportDate(dateStr);
    }
    if (report.rig_id) {
      setSelectedRigId(report.rig_id);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <FileText className="h-6 w-6 text-cyan-400" />
            Report Viewer
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Browse parsed DDR reports and upload new ones
          </p>
        </div>
        <div className="text-xs text-slate-500">
          {(reports || []).length} reports in database
        </div>
      </div>

      {/* Upload Zone */}
      <div
        className={`rounded-xl border-2 border-dashed p-8 text-center transition-colors cursor-pointer ${
          dragOver ? 'border-cyan-400 bg-cyan-500/10' : 'border-slate-700 hover:border-slate-500'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById('ddr-file-input')?.click()}
        role="button"
        aria-label="Upload DDR report"
      >
        <input
          id="ddr-file-input"
          type="file"
          accept=".pdf"
          onChange={handleFileInput}
          className="hidden"
        />
        {uploadMutation.isPending ? (
          <div className="flex items-center justify-center gap-2 text-cyan-300">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="text-sm">Uploading & parsing...</span>
          </div>
        ) : (
          <>
            <Upload className="h-8 w-8 text-slate-500 mx-auto mb-3" />
            <div className="text-sm text-slate-300 font-medium">
              Drop a DDR PDF here or click to upload
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Supports DDR/IADC daily drilling report PDFs
            </div>
          </>
        )}
      </div>

      {/* Upload result */}
      {uploadResult && (
        <div
          className="rounded-xl p-4 flex items-start justify-between"
          style={{
            background: uploadResult.error ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
            borderLeft: `4px solid ${uploadResult.error ? DDR_TOKENS.status.critical : DDR_TOKENS.status.onTarget}`,
          }}
        >
          <div className="flex items-start gap-2">
            {uploadResult.error ? (
              <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5" />
            ) : (
              <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
            )}
            <div className="text-sm text-white">
              {uploadResult.error
                ? String(uploadResult.error)
                : `Report parsed successfully! ${uploadResult.total_pages || ''} pages processed.`}
            </div>
          </div>
          <button onClick={() => setUploadResult(null)} className="text-slate-500 hover:text-slate-300">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report List */}
        <div className={selectedReport ? 'lg:col-span-2' : 'lg:col-span-3'}>
          {/* Search */}
          <div
            className="rounded-xl p-3 mb-4 flex items-center gap-2"
            style={{ background: DDR_TOKENS.bg.secondary }}
          >
            <Search className="h-4 w-4 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by well, rig, field..."
              className="flex-1 bg-transparent text-white text-sm placeholder-slate-500 outline-none"
            />
          </div>

          {/* Reports table */}
          <div
            className="rounded-xl overflow-hidden"
            style={{ background: DDR_TOKENS.bg.secondary }}
          >
            {isLoading ? (
              <LoadingState message="Loading reports..." />
            ) : filteredReports.length === 0 ? (
              <EmptyState title="No Reports" message={searchQuery ? 'No reports match your search' : 'No DDR reports in database. Upload one to get started.'} />
            ) : (
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0" style={{ background: DDR_TOKENS.bg.secondary }}>
                    <tr className="text-left text-slate-500 border-b" style={{ borderColor: DDR_TOKENS.surface.border }}>
                      <th className="px-4 py-2 font-medium">Date</th>
                      <th className="px-4 py-2 font-medium">Rig</th>
                      <th className="px-4 py-2 font-medium">Well</th>
                      <th className="px-4 py-2 font-medium">Field</th>
                      <th className="px-4 py-2 font-medium">Report #</th>
                      <th className="px-4 py-2 font-medium">Status</th>
                      <th className="px-4 py-2 font-medium"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredReports.map((report: {
                      id: string;
                      report_date?: string;
                      rig_id?: string;
                      rig_name?: string;
                      well_name?: string;
                      field_name?: string;
                      report_number?: string;
                      status?: string;
                    }) => (
                      <tr
                        key={report.id}
                        className={`border-b hover:bg-slate-800/40 transition-colors cursor-pointer ${
                          selectedReport === report.id ? 'bg-cyan-500/10' : ''
                        }`}
                        style={{ borderColor: 'rgba(51, 65, 85, 0.3)' }}
                        onClick={() => viewReport(report.id)}
                      >
                        <td className="px-4 py-2 text-white whitespace-nowrap flex items-center gap-1.5">
                          <Calendar className="h-3 w-3 text-slate-500" />
                          {report.report_date?.split('T')[0] || '—'}
                        </td>
                        <td className="px-4 py-2 text-cyan-300 font-mono">
                          {report.rig_name || '—'}
                        </td>
                        <td className="px-4 py-2 text-slate-300">
                          {report.well_name || '—'}
                        </td>
                        <td className="px-4 py-2 text-slate-400">
                          {report.field_name || '—'}
                        </td>
                        <td className="px-4 py-2 text-slate-400 font-mono">
                          {report.report_number || '—'}
                        </td>
                        <td className="px-4 py-2">
                          <span
                            className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                            style={{
                              background: report.status === 'parsed' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                              color: report.status === 'parsed' ? DDR_TOKENS.status.onTarget : DDR_TOKENS.status.critical,
                            }}
                          >
                            {report.status || 'unknown'}
                          </span>
                        </td>
                        <td className="px-4 py-2">
                          <div className="flex items-center gap-1">
                            <button
                              onClick={(e) => { e.stopPropagation(); navigateToReport(report); }}
                              className="text-cyan-500 hover:text-cyan-300 transition-colors p-1"
                              title="Navigate to this report"
                            >
                              <ChevronRight className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Metrics Detail Panel */}
        {selectedReport && (
          <div
            className="rounded-xl overflow-hidden"
            style={{ background: DDR_TOKENS.bg.secondary }}
          >
            <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: DDR_TOKENS.surface.border }}>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Eye className="h-4 w-4 text-cyan-400" />
                Extracted Metrics
              </h3>
              <button
                onClick={() => { setSelectedReport(null); setReportMetrics([]); }}
                className="text-xs text-slate-500 hover:text-slate-300"
              >
                ✕ Close
              </button>
            </div>

            <div className="p-3 max-h-[500px] overflow-y-auto space-y-2">
              {metricsLoading ? (
                <LoadingState message="Loading metrics..." />
              ) : reportMetrics.length === 0 ? (
                <EmptyState title="No Extracted Metrics" message="No metrics were extracted from this report." />
              ) : (
                reportMetrics.map((m) => (
                  <div
                    key={m.id}
                    className="p-2.5 rounded-lg border"
                    style={{ background: DDR_TOKENS.bg.primary, borderColor: DDR_TOKENS.surface.border }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-cyan-300 font-mono text-xs">{m.field_name}</span>
                      <div className="flex items-center gap-2">
                        {m.is_imputed && (
                          <span className="text-[9px] px-1 py-0.5 rounded bg-red-500/15 text-red-400 uppercase">
                            imputed
                          </span>
                        )}
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded"
                          style={{
                            background: `${getMethodColor(m.extraction_method)}20`,
                            color: getMethodColor(m.extraction_method),
                          }}
                        >
                          {m.extraction_method}
                        </span>
                      </div>
                    </div>
                    <div className="text-white font-mono text-sm font-bold">
                      {m.value}
                      {m.numeric_value != null && m.value !== String(m.numeric_value) && (
                        <span className="text-slate-500 text-xs ml-2">({m.numeric_value})</span>
                      )}
                    </div>
                    {m.confidence_score != null && (
                      <div className="mt-1.5">
                        <div className="flex items-center justify-between text-[10px] text-slate-500 mb-0.5">
                          <span>Confidence</span>
                          <span>{(m.confidence_score * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1 rounded-full bg-slate-700 overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${m.confidence_score * 100}%`,
                              background: m.confidence_score >= 0.8 ? DDR_TOKENS.status.onTarget
                                : m.confidence_score >= 0.5 ? DDR_TOKENS.status.warning
                                : DDR_TOKENS.status.critical,
                            }}
                          />
                        </div>
                      </div>
                    )}
                    {m.citation && (
                      <div className="text-[10px] text-slate-500 mt-1.5 font-mono truncate" title={m.citation}>
                        📎 {m.citation}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

function getMethodColor(method: string): string {
  switch (method) {
    case 'regex': return '#06b6d4';
    case 'ocr': return '#8b5cf6';
    case 'llm': return '#f59e0b';
    case 'imputed': return '#ef4444';
    case 'manual': return '#10b981';
    default: return '#64748b';
  }
}

export default ReportViewer;