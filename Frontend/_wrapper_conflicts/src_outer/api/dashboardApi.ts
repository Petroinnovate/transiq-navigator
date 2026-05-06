// ============================================================================
// Dashboard API - Backend Integration Layer
// React Query / TanStack Query Compatible
// ============================================================================

import axios from '@/lib/axios'
import { DashboardResponse } from '@/types/dashboard'

/**
 * Fetch dashboard data for a specific report
 * @param reportId - Unique report identifier
 * @returns Promise<DashboardResponse>
 */
export const fetchDashboardData = async (reportId: string): Promise<DashboardResponse> => {
  const response = await axios.get<DashboardResponse>(`/api/v2/dashboard/${reportId}`)
  return response.data
}

/**
 * Fetch latest dashboard data (most recent ingestion)
 * @returns Promise<DashboardResponse>
 */
export const fetchLatestDashboard = async (): Promise<DashboardResponse> => {
  const response = await axios.get<DashboardResponse>('/api/v2/dashboard/latest')
  return response.data
}

/**
 * Process and generate dashboard from uploaded file
 * @param fileId - ID of uploaded file
 * @returns Promise<DashboardResponse>
 */
export const processDashboardFromFile = async (fileId: string): Promise<DashboardResponse> => {
  const response = await axios.post<DashboardResponse>('/api/v2/generate', { fileId })
  return response.data
}

/**
 * Get dashboard processing status
 * @param taskId - Processing task ID
 * @returns Promise with processing status
 */
export const getDashboardProcessingStatus = async (taskId: string) => {
  const response = await axios.get(`/api/v2/dashboard/status/${taskId}`)
  return response.data
}

/**
 * Export dashboard data as PDF
 * @param reportId - Report ID to export
 * @returns Promise<Blob>
 */
export const exportDashboardPDF = async (reportId: string): Promise<Blob> => {
  const response = await axios.get(`/api/v2/dashboard/${reportId}/export/pdf`, {
    responseType: 'blob'
  })
  return response.data
}

/**
 * Export dashboard data as Excel
 * @param reportId - Report ID to export
 * @returns Promise<Blob>
 */
export const exportDashboardExcel = async (reportId: string): Promise<Blob> => {
  const response = await axios.get(`/api/v2/dashboard/${reportId}/export/excel`, {
    responseType: 'blob'
  })
  return response.data
}

/**
 * React Query hook-friendly functions
 */
export const dashboardQueries = {
  byId: (reportId: string) => ({
    queryKey: ['dashboard', reportId],
    queryFn: () => fetchDashboardData(reportId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  }),
  
  latest: () => ({
    queryKey: ['dashboard', 'latest'],
    queryFn: fetchLatestDashboard,
    staleTime: 2 * 60 * 1000, // 2 minutes
  }),
  
  processing: (taskId: string) => ({
    queryKey: ['dashboard', 'processing', taskId],
    queryFn: () => getDashboardProcessingStatus(taskId),
    refetchInterval: 2000, // Poll every 2 seconds
  }),
}
