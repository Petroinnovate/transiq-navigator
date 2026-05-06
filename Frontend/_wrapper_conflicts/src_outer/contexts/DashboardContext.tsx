// ============================================================================
// DashboardContext - Centralized Dashboard State Management
// Purpose: React Context for dashboard data with TypeScript support
// ============================================================================

import React, { createContext, useContext, useState, ReactNode } from 'react'
import { DashboardResponse } from '@/types/dashboard'

interface DashboardContextType {
  dashboardData: DashboardResponse | null
  setDashboardData: (data: DashboardResponse | null) => void
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
  error: string | null
  setError: (error: string | null) => void
  reportId: string | null
  setReportId: (id: string | null) => void
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined)

interface DashboardProviderProps {
  children: ReactNode
}

export const DashboardProvider: React.FC<DashboardProviderProps> = ({ children }) => {
  const [dashboardData, setDashboardData] = useState<DashboardResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [reportId, setReportId] = useState<string | null>(null)

  return (
    <DashboardContext.Provider
      value={{
        dashboardData,
        setDashboardData,
        isLoading,
        setIsLoading,
        error,
        setError,
        reportId,
        setReportId,
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
