// ============================================================================
// Dashboard API — Lovable Cloud (Supabase) implementation
// ----------------------------------------------------------------------------
// The dashboards table is the source of truth for generated dashboards.
// Each row is keyed by document_id and scoped to the user's tenant via RLS.
//
// Legacy axios calls to FastAPI (/api/v2/dashboard/*) have been removed —
// uploads, processing and dashboards live entirely in Lovable Cloud now.
// PDF/Excel export endpoints have not been ported yet; they throw a clear
// "pending migration" error so callers can show a friendly message.
// ============================================================================

import { supabase } from '@/integrations/supabase/client'
import type { DashboardResponse } from '@/types/dashboard'

function rowToDashboard(row: any, doc?: any): DashboardResponse {
  // Shape the renderer expects: { dashboard: { kpis, charts, insights, ... } }
  return {
    dashboard: {
      id: row.id,
      document_id: row.document_id,
      title: doc?.file_name ?? 'Dashboard',
      kpis: row.kpis ?? [],
      charts: row.charts ?? [],
      insights: row.insights ?? [],
      sixSigma: row.six_sigma ?? null,
      status: row.status,
      meta: {
        document_id: row.document_id,
        file_name: doc?.file_name,
        created_at: row.created_at,
      },
    },
  } as unknown as DashboardResponse
}

export const fetchDashboardData = async (reportId: string): Promise<DashboardResponse> => {
  const { data, error } = await supabase
    .from('dashboards')
    .select('*, documents(file_name, status)')
    .eq('document_id', reportId)
    .maybeSingle()

  if (error) throw new Error(error.message)
  if (!data) throw new Error('Dashboard not found')
  return rowToDashboard(data, (data as any).documents)
}

export const fetchLatestDashboard = async (): Promise<DashboardResponse> => {
  const { data, error } = await supabase
    .from('dashboards')
    .select('*, documents(file_name, status)')
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle()

  if (error) throw new Error(error.message)
  if (!data) throw new Error('No dashboards yet — upload a document to generate one.')
  return rowToDashboard(data, (data as any).documents)
}

export const processDashboardFromFile = async (_fileId: string): Promise<DashboardResponse> => {
  throw new Error('Use the upload flow — dashboards are generated automatically after processing.')
}

export const getDashboardProcessingStatus = async (taskId: string) => {
  // Task IDs map to document IDs in the Lovable Cloud pipeline.
  const { data, error } = await supabase
    .from('documents')
    .select('id, status, has_dashboard')
    .eq('id', taskId)
    .maybeSingle()
  if (error) throw new Error(error.message)
  return {
    task_id: taskId,
    status: data?.has_dashboard ? 'completed' : (data?.status ?? 'processing'),
  }
}

export const exportDashboardPDF = async (_reportId: string): Promise<Blob> => {
  throw new Error('PDF export is pending migration to Lovable Cloud.')
}

export const exportDashboardExcel = async (_reportId: string): Promise<Blob> => {
  throw new Error('Excel export is pending migration to Lovable Cloud.')
}

export const dashboardQueries = {
  byId: (reportId: string) => ({
    queryKey: ['dashboard', reportId],
    queryFn: () => fetchDashboardData(reportId),
    staleTime: 5 * 60 * 1000,
  }),
  latest: () => ({
    queryKey: ['dashboard', 'latest'],
    queryFn: fetchLatestDashboard,
    staleTime: 0,
    gcTime: 0,
    refetchOnMount: true,
  }),
  processing: (taskId: string) => ({
    queryKey: ['dashboard', 'processing', taskId],
    queryFn: () => getDashboardProcessingStatus(taskId),
    refetchInterval: 2000,
  }),
}
