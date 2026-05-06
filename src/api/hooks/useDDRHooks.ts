// ============================================================================
// DDR Intelligence Platform — React Query Hooks
// One hook per API endpoint, all with proper caching & enabled guards
// ============================================================================

import { useQuery, useMutation } from '@tanstack/react-query';
import {
  fetchFleetSummary, fetchFleetNPTPareto, fetchFleetSPC,
  fetchFleetTopPerformers, fetchFleetHeatmap, fetchFleetTrends,
  fetchRigList, fetchRigDetail, fetchRigKPIs, fetchRigTimeline,
  fetchRigNPT, fetchRigSurvey, fetchRigMud, fetchRigPersonnel,
  fetchRigBHA, fetchRigBulk, fetchRigHSE, fetchRigForemanRemarks,
  fetchRigWellDesign, fetchRigAudit, searchDDR, fetchFieldAudit,
  fetchAuditChangeLog, uploadDDRReport, fetchETLStatus,
  fetchReportList, exportRig, exportFleet,
} from '@/api/ddrClient';
import type { RigListParams, FleetTrendParams, DDRSearchParams } from '@/types/ddr.types';

// ── Fleet Hooks ─────────────────────────────────────────────────────────────

export const useFleetSummary = (reportDate: string) =>
  useQuery({
    queryKey: ['fleet', 'summary', reportDate],
    queryFn: () => fetchFleetSummary(reportDate),
    staleTime: 5 * 60 * 1000,
    enabled: !!reportDate,
  });

export const useFleetNPTPareto = (reportDate: string) =>
  useQuery({
    queryKey: ['fleet', 'npt-pareto', reportDate],
    queryFn: () => fetchFleetNPTPareto(reportDate),
    staleTime: 5 * 60 * 1000,
    enabled: !!reportDate,
  });

export const useFleetSPC = (metric: string, reportDate: string) =>
  useQuery({
    queryKey: ['fleet', 'spc', metric, reportDate],
    queryFn: () => fetchFleetSPC(metric, reportDate),
    staleTime: 5 * 60 * 1000,
    enabled: !!metric && !!reportDate,
  });

export const useFleetTopPerformers = (reportDate: string, metric?: string, limit?: number) =>
  useQuery({
    queryKey: ['fleet', 'top-performers', reportDate, metric, limit],
    queryFn: () => fetchFleetTopPerformers(reportDate, metric, limit),
    staleTime: 5 * 60 * 1000,
    enabled: !!reportDate,
  });

export const useFleetHeatmap = (reportDate: string) =>
  useQuery({
    queryKey: ['fleet', 'heatmap', reportDate],
    queryFn: () => fetchFleetHeatmap(reportDate),
    staleTime: 5 * 60 * 1000,
    enabled: !!reportDate,
  });

export const useFleetTrends = (params: FleetTrendParams) =>
  useQuery({
    queryKey: ['fleet', 'trends', params],
    queryFn: () => fetchFleetTrends(params),
    staleTime: 5 * 60 * 1000,
    enabled: !!params.report_date,
  });

// ── Rig Hooks ───────────────────────────────────────────────────────────────

export const useRigList = (params: RigListParams) =>
  useQuery({
    queryKey: ['rigs', params],
    queryFn: () => fetchRigList(params),
    staleTime: 2 * 60 * 1000,
    enabled: !!params.report_date,
  });

export const useRigDetail = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, reportDate],
    queryFn: () => fetchRigDetail(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigKPIs = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'kpis', reportDate],
    queryFn: () => fetchRigKPIs(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigTimeline = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'timeline', reportDate],
    queryFn: () => fetchRigTimeline(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigNPT = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'npt', reportDate],
    queryFn: () => fetchRigNPT(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigSurvey = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'survey', reportDate],
    queryFn: () => fetchRigSurvey(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigMud = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'mud', reportDate],
    queryFn: () => fetchRigMud(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigPersonnel = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'personnel', reportDate],
    queryFn: () => fetchRigPersonnel(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigBHA = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'bha', reportDate],
    queryFn: () => fetchRigBHA(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigBulk = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'bulk', reportDate],
    queryFn: () => fetchRigBulk(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigHSE = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'hse', reportDate],
    queryFn: () => fetchRigHSE(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigForemanRemarks = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'foreman-remarks', reportDate],
    queryFn: () => fetchRigForemanRemarks(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigWellDesign = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'well-design', reportDate],
    queryFn: () => fetchRigWellDesign(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

export const useRigAudit = (rigId: string, reportDate: string) =>
  useQuery({
    queryKey: ['rig', rigId, 'audit', reportDate],
    queryFn: () => fetchRigAudit(rigId, reportDate),
    staleTime: 2 * 60 * 1000,
    enabled: !!rigId && !!reportDate,
  });

// ── Search / RAG ────────────────────────────────────────────────────────────

export const useDDRSearch = () =>
  useMutation({
    mutationFn: (params: DDRSearchParams) => searchDDR(params),
  });

// ── Audit Hooks ─────────────────────────────────────────────────────────────

export const useFieldAudit = (rigId: string, field: string, reportDate: string) =>
  useQuery({
    queryKey: ['audit', 'field', rigId, field, reportDate],
    queryFn: () => fetchFieldAudit(rigId, field, reportDate),
    staleTime: 5 * 60 * 1000,
    enabled: !!rigId && !!field && !!reportDate,
  });

export const useAuditChangeLog = (reportDate: string, rigId?: string) =>
  useQuery({
    queryKey: ['audit', 'changelog', reportDate, rigId],
    queryFn: () => fetchAuditChangeLog(reportDate, rigId),
    staleTime: 2 * 60 * 1000,
    enabled: !!reportDate,
  });

// ── Ingestion / Upload ──────────────────────────────────────────────────────

export const useUploadReport = () =>
  useMutation({
    mutationFn: (file: File) => uploadDDRReport(file),
  });

export const useETLStatus = (jobId: string) =>
  useQuery({
    queryKey: ['etl', 'status', jobId],
    queryFn: () => fetchETLStatus(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'processing' ? 2000 : false;
    },
    enabled: !!jobId,
  });

export const useReportList = () =>
  useQuery({
    queryKey: ['reports'],
    queryFn: fetchReportList,
    staleTime: 30 * 1000,
  });

// ── Export Hooks ─────────────────────────────────────────────────────────────

export const useExportRig = () =>
  useMutation({
    mutationFn: ({ rigId, reportDate, format }: { rigId: string; reportDate: string; format?: 'pdf' | 'excel' }) =>
      exportRig(rigId, reportDate, format),
  });

export const useExportFleet = () =>
  useMutation({
    mutationFn: ({ reportDate, format }: { reportDate: string; format?: 'pdf' | 'excel' }) =>
      exportFleet(reportDate, format),
  });
