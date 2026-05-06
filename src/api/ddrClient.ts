// @ts-nocheck
// ============================================================================
// DDR Intelligence Platform — API Client
// Reuses existing axios instance from lib/axios.ts
// ============================================================================

import axios from '@/lib/axios';
import type {
  FleetSummary, RigSummary, RigDetail, RigKPIs,
  TimelineRow, NPTEvent, SurveyStation, MudRecord,
  PersonnelRow, BHAComponent, BulkData, HSEData,
  ForemanRemarks, WellDesign, FieldAuditRecord,
  FleetNPTPareto, FleetSPCResult, FleetTopPerformer,
  FleetHeatmapTile, FleetTrendPoint, DDRSearchResult,
  ETLProgress, ReportListItem, AuditChangeLogEntry,
  RigListParams, FleetTrendParams, DDRSearchParams,
} from '@/types/ddr.types';

const DDR_BASE = '/api/v2';

// ── Fleet Endpoints ─────────────────────────────────────────────────────────

export const fetchFleetSummary = async (reportDate: string): Promise<FleetSummary> => {
  const { data } = await axios.get(`${DDR_BASE}/fleet/summary`, { params: { report_date: reportDate } });
  return data;
};

export const fetchFleetNPTPareto = async (reportDate: string): Promise<FleetNPTPareto[]> => {
  const { data } = await axios.get(`${DDR_BASE}/fleet/npt-pareto`, { params: { report_date: reportDate } });
  return data;
};

export const fetchFleetSPC = async (metric: string, reportDate: string): Promise<FleetSPCResult> => {
  const { data } = await axios.get(`${DDR_BASE}/fleet/spc/${metric}`, { params: { report_date: reportDate } });
  return data;
};

export const fetchFleetTopPerformers = async (reportDate: string, metric?: string, limit?: number): Promise<FleetTopPerformer[]> => {
  const { data } = await axios.get(`${DDR_BASE}/fleet/top-performers`, { params: { report_date: reportDate, metric, limit } });
  return data;
};

export const fetchFleetHeatmap = async (reportDate: string): Promise<FleetHeatmapTile[]> => {
  const { data } = await axios.get(`${DDR_BASE}/fleet/heatmap`, { params: { report_date: reportDate } });
  return data;
};

export const fetchFleetTrends = async (params: FleetTrendParams): Promise<FleetTrendPoint[]> => {
  const metric = params.metric || 'rop';
  const { data } = await axios.get(`/api/ddr/trends/${metric}`, {
    params: { rig_id: params.rig_id, days: params.days },
  });
  return data?.data ?? data;
};

// ── Rig Endpoints ───────────────────────────────────────────────────────────

export const fetchRigList = async (params: RigListParams): Promise<RigSummary[]> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs`, { params });
  return data;
};

export const fetchRigDetail = async (rigId: string, reportDate: string): Promise<RigDetail> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigKPIs = async (rigId: string, reportDate: string): Promise<RigKPIs> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/kpis`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigTimeline = async (rigId: string, reportDate: string): Promise<TimelineRow[]> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/timeline`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigNPT = async (rigId: string, reportDate: string): Promise<NPTEvent[]> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/npt`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigSurvey = async (rigId: string, reportDate: string): Promise<SurveyStation[]> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/survey`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigMud = async (rigId: string, reportDate: string): Promise<MudRecord[]> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/mud`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigPersonnel = async (rigId: string, reportDate: string): Promise<PersonnelRow[]> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/personnel`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigBHA = async (rigId: string, reportDate: string): Promise<BHAComponent[]> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/bha`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigBulk = async (rigId: string, reportDate: string): Promise<BulkData> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/bulk`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigHSE = async (rigId: string, reportDate: string): Promise<HSEData> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/hse`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigForemanRemarks = async (rigId: string, reportDate: string): Promise<ForemanRemarks> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/foreman-remarks`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigWellDesign = async (rigId: string, reportDate: string): Promise<WellDesign> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/well-design`, { params: { report_date: reportDate } });
  return data;
};

export const fetchRigAudit = async (rigId: string, _reportDate: string): Promise<FieldAuditRecord[]> => {
  const { data } = await axios.get(`${DDR_BASE}/audit/${rigId}/all`);
  return data?.history ?? data;
};

// ── Search / RAG ────────────────────────────────────────────────────────────

export const searchDDR = async (params: DDRSearchParams): Promise<DDRSearchResult> => {
  const { data } = await axios.post(`${DDR_BASE}/search`, params);
  return data;
};

// ── Field Audit ─────────────────────────────────────────────────────────────

export const fetchFieldAudit = async (rigId: string, field: string, _reportDate: string): Promise<FieldAuditRecord> => {
  const { data } = await axios.get(`${DDR_BASE}/audit/${rigId}/${field}`);
  return data;
};

export const fetchAuditChangeLog = async (reportDate: string, rigId?: string): Promise<AuditChangeLogEntry[]> => {
  const { data } = await axios.get(`${DDR_BASE}/audit/changelog`, { params: { report_date: reportDate, rig_id: rigId } });
  return data?.entries ?? data;
};

// ── Ingestion / Upload ──────────────────────────────────────────────────────

export const uploadDDRReport = async (file: File): Promise<{ job_id: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await axios.post(`${DDR_BASE}/ddr/parse-upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const fetchETLStatus = async (jobId: string): Promise<ETLProgress> => {
  const { data } = await axios.get(`${DDR_BASE}/task/${jobId}`);
  return data;
};

export const fetchReportList = async (): Promise<ReportListItem[]> => {
  const { data } = await axios.get(`${DDR_BASE}/ddr/reports`);
  return data;
};

// ── Export ───────────────────────────────────────────────────────────────────

export const exportRig = async (rigId: string, reportDate: string, format: 'pdf' | 'excel' = 'pdf'): Promise<Blob> => {
  const { data } = await axios.get(`${DDR_BASE}/rigs/${rigId}/export`, {
    params: { report_date: reportDate, format },
    responseType: 'blob',
  });
  return data;
};

export const exportFleet = async (reportDate: string, format: 'pdf' | 'excel' = 'pdf'): Promise<Blob> => {
  const { data } = await axios.get(`${DDR_BASE}/fleet/export`, {
    params: { report_date: reportDate, format },
    responseType: 'blob',
  });
  return data;
};

// ── Metric Editing ──────────────────────────────────────────────────────────

export interface MetricUpdateRequest {
  new_value: string;
  reason?: string;
  source_method?: string;
  origin?: string;
}

export interface MetricUpdateResponse {
  id: string;
  field_name: string;
  value: string;
  citation: string;
  updated: boolean;
}

export const updateDDRMetric = async (
  metricId: string,
  payload: MetricUpdateRequest
): Promise<MetricUpdateResponse> => {
  const { data } = await axios.put<MetricUpdateResponse>(
    `${DDR_BASE}/ddr/metrics/${metricId}`,
    payload
  );
  return data;
};