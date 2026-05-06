// ============================================================================
// DashboardContext - Centralized Dashboard State Management
// Purpose: React Context for dashboard data with TypeScript support
// ============================================================================ 

import React, { createContext, useContext, useState, ReactNode } from 'react'   
import { DashboardResponse } from '@/types/dashboard'

const LS_KEY = 'transiq_dashboard_data'
const LS_PROJECT_KEY = 'transiq_project_meta'

export interface DashboardData {
  dashboard?: any
}

export interface DocumentResult {
  id: string
  name: string
  kpis: { title: string; value: string | number; unit?: string }[]
  dmaic?: Record<string, string>
  sections?: { title: string; summary: string; confidence: number }[]
}

export interface ProjectMeta {
  filesProcessed: number
  batchesProcessed: number
  message?: string
  documents?: DocumentResult[]
  fileNames?: string[]
}

interface DashboardContextType {
  dashboardData: DashboardResponse | null
  setDashboardData: (data: DashboardResponse | null) => void
  projectMeta: ProjectMeta | null
  setProjectMeta: (meta: ProjectMeta | null) => void
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
  error: string | null
  setError: (error: string | null) => void
  reportId: string | null
  setReportId: (id: string | null) => void
  files: File[]
  setFiles: (files: File[]) => void
  docId: string | null
  setDocId: (id: string | null) => void
  taskId: string | null
  setTaskId: (id: string | null) => void
  progress: number
  setProgress: (progress: number) => void
  resetDashboard: () => void
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined)

interface DashboardProviderProps {
  children: ReactNode
}

function loadFromStorage(): DashboardResponse | null {
  try {
    const raw = localStorage.getItem(LS_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveToStorage(data: DashboardResponse | null) {
  try {
    if (data) {
      localStorage.setItem(LS_KEY, JSON.stringify(data))
    } else {
      localStorage.removeItem(LS_KEY)
    }
  } catch {
    // storage quota exceeded — ignore
  }
}

function loadProjectMetaFromStorage(): ProjectMeta | null {
  try {
    const raw = localStorage.getItem(LS_PROJECT_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveProjectMetaToStorage(meta: ProjectMeta | null) {
  try {
    if (meta) {
      localStorage.setItem(LS_PROJECT_KEY, JSON.stringify(meta))
    } else {
      localStorage.removeItem(LS_PROJECT_KEY)
    }
  } catch {
    // ignore
  }
}

export const DashboardProvider: React.FC<DashboardProviderProps> = ({ children }) => {
  const [dashboardData, _setDashboardData] = useState<DashboardResponse | null>(loadFromStorage)
  const [projectMeta, _setProjectMeta] = useState<ProjectMeta | null>(loadProjectMetaFromStorage)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [reportId, setReportId] = useState<string | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const [docId, setDocId] = useState<string | null>(null)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [progress, setProgress] = useState<number>(0)

  const setDashboardData = (data: DashboardResponse | null) => {
    saveToStorage(data)
    _setDashboardData(data)
  }

  const setProjectMeta = (meta: ProjectMeta | null) => {
    saveProjectMetaToStorage(meta)
    _setProjectMeta(meta)
  }

  const resetDashboard = () => {
    setDashboardData(null)
    setProjectMeta(null)
    setIsLoading(false)
    setError(null)
    setReportId(null)
    setFiles([])
    setDocId(null)
    setTaskId(null)
    setProgress(0)
  }

  return (
    <DashboardContext.Provider
      value={{
        dashboardData,
        setDashboardData,
        projectMeta,
        setProjectMeta,
        isLoading,
        setIsLoading,
        error,
        setError,
        reportId,
        setReportId,
        files,
        setFiles,
        docId,
        setDocId,
        taskId,
        setTaskId,
        progress,
        setProgress,
        resetDashboard,
      }}
    >
      {children}
    </DashboardContext.Provider>
  )
}

export const useDashboard = (): DashboardContextType => {
  const context = useContext(DashboardContext)
  if (context === undefined) {
    throw new Error('useDashboard must be used within a DashboardProvider')     
  }
  return context
}
