// @ts-nocheck
// ============================================================================
// Dashboard Page - Main Executive Dashboard View
// ============================================================================

import React, { useEffect, useState, useCallback, Component, ErrorInfo, ReactNode } from 'react'
import DashboardRenderer from '@/components/DashboardRenderer'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { AlertTriangle, RefreshCw, TrendingUp, BarChart3, Pickaxe } from 'lucide-react'
import { useDashboard } from '@/contexts/DashboardContext'
import { useDDR, type DashboardMode } from '@/contexts/DDRContext'
import DDRDashboard from '@/components/ddr/DDRDashboard'
import { fetchDashboardData, fetchLatestDashboard } from '@/api/dashboardApi'

// ── Error Boundary to catch rendering crashes ─────────────────────────────
interface EBState { hasError: boolean; error: string }
class DashboardErrorBoundary extends Component<{ children: ReactNode; onReset: () => void }, EBState> {
  state: EBState = { hasError: false, error: '' }
  static getDerivedStateFromError(err: Error): EBState {
    return { hasError: true, error: err.message }
  }
  componentDidCatch(err: Error, info: ErrorInfo) {
    console.error('Dashboard render error:', err, info)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-4">
            <AlertTriangle className="h-16 w-16 mx-auto text-red-400 opacity-70" />
            <h2 className="text-2xl font-bold">Dashboard Render Error</h2>
            <p className="text-muted-foreground text-sm font-mono bg-muted px-3 py-1.5 rounded max-w-md mx-auto">{this.state.error}</p>
            <Button onClick={() => { this.setState({ hasError: false, error: '' }); this.props.onReset(); }}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

interface DashboardProps {
  reportId?: string
}

export const Dashboard: React.FC<DashboardProps> = ({ reportId }) => {
  const { dashboardData: contextData, setDashboardData } = useDashboard()
  const { mode, setMode, setIsDDRReport } = useDDR()

  const [dashboard, setDashboard] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setFetchError(null)
    try {
      const json = reportId
        ? await fetchDashboardData(reportId)
        : await fetchLatestDashboard()

      // Support both { dashboard: {...} } and flat { kpis, charts, title, ... }
      const data = (json as any).dashboard ?? json
      if (!data || typeof data !== 'object') throw new Error('Unexpected response shape')
      // Persist fetched dashboard into context (and therefore localStorage)
      setDashboardData({ dashboard: data } as any)
      setDashboard(data)
    } catch (err: any) {
      setFetchError(err.message ?? 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }, [reportId, setDashboardData])

  useEffect(() => {
    // If context already has data (persisted from upload or previous session), use it immediately
    if (contextData) {
      // Unwrap nested dashboard structure.
      // Upload.tsx now flattens, but handle legacy localStorage entries too.
      // Possible shapes:
      //   { dashboard: { title, kpis, charts, meta, ceo_view, ... } }     — flattened (new)
      //   { dashboard: { meta, dashboard: { title, kpis }, ceo_view } }   — nested (old)
      //   { title, kpis, charts, ... }                                     — raw flat
      let data: any = (contextData as any).dashboard ?? contextData

      // If data has a nested "dashboard" key but no direct kpis/charts, flatten it
      if (data && !data.kpis && !data.charts && !data.title && data.dashboard && typeof data.dashboard === 'object') {
        // Merge inner dashboard with outer fields (meta, ceo_view, etc.)
        const inner = data.dashboard;
        const merged: any = { ...inner };
        for (const key of Object.keys(data)) {
          if (key !== 'dashboard' && !(key in merged)) {
            merged[key] = data[key];
          }
        }
        data = merged;
      }
      // Handle one more level of nesting (triple-nested legacy)
      if (data && !data.kpis && !data.charts && !data.title && data.dashboard && typeof data.dashboard === 'object') {
        data = data.dashboard;
      }

      if (data && (data.kpis !== undefined || data.charts !== undefined || data.title || data.sections !== undefined)) {
        setDashboard(data)
        setLoading(false)
        return
      }
    }
    // No valid persisted data — fetch from backend (returns most recent uploaded dashboard)
    loadDashboard()
  }, [contextData, loadDashboard])

  // DDR mode check — always render DDR if mode is set, even before dashboard loads
  if (mode === 'drilling') {
    return <DDRDashboard />;
  }

  // Mode switcher component — reused across loading, error, and empty states
  const ModeSwitcher = () => (
    <div className="fixed top-2 right-4 z-50 flex items-center gap-1 bg-slate-800/90 backdrop-blur-sm border border-slate-700/60 rounded-lg p-1">
      <button
        onClick={() => setMode('analytics')}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
          mode === 'analytics'
            ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
            : 'text-slate-400 hover:text-white'
        }`}
      >
        <BarChart3 className="h-3.5 w-3.5" />
        Analytics
      </button>
      <button
        onClick={() => setMode('drilling')}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
          mode === 'drilling'
            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
            : 'text-slate-400 hover:text-white'
        }`}
      >
        <Pickaxe className="h-3.5 w-3.5" />
        DDR Drilling
      </button>
    </div>
  );

  if (loading) {
    return (
      <DashboardLayout>
        <ModeSwitcher />
        <div className="space-y-6 p-2">
          <Skeleton className="h-32 w-full" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28 w-full" />)}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Skeleton className="h-72 w-full" />
            <Skeleton className="h-72 w-full" />
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
      </DashboardLayout>
    )
  }

  if (fetchError) {
    return (
      <DashboardLayout>
        <ModeSwitcher />
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-4">
            <AlertTriangle className="h-16 w-16 mx-auto text-red-400 opacity-70" />
            <h2 className="text-2xl font-bold">Failed to load dashboard</h2>
            <p className="text-muted-foreground text-sm font-mono bg-muted px-3 py-1.5 rounded">{fetchError}</p>
            <div className="flex gap-3 justify-center">
              <Button onClick={loadDashboard}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
              <Button variant="outline" onClick={() => setMode('drilling')}>
                <Pickaxe className="h-4 w-4 mr-2" />
                Open DDR Dashboard
              </Button>
            </div>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  if (!dashboard) {
    return (
      <DashboardLayout>
        <ModeSwitcher />
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-4">
            <TrendingUp className="h-16 w-16 mx-auto text-muted-foreground opacity-50" />
            <h2 className="text-2xl font-bold">No Dashboard Data</h2>
            <p className="text-muted-foreground">Upload a report to generate a dashboard, or switch to DDR mode.</p>
            <div className="flex gap-3 justify-center">
              <Button onClick={loadDashboard}><RefreshCw className="h-4 w-4 mr-2" />Check Again</Button>
              <Button variant="outline" onClick={() => setMode('drilling')}>
                <Pickaxe className="h-4 w-4 mr-2" />
                Open DDR Dashboard
              </Button>
            </div>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  // Auto-detect DDR report from meta / autoClassification
  const reportType = dashboard?.autoClassification?.reportType
    || dashboard?.meta?.reportType
    || '';
  const isDDR = /ddr|drilling|morning\s*report|operlmtdmrrep/i.test(reportType);

  // If DDR detected from data, switch mode
  if (isDDR) {
    return <DDRDashboard />;
  }

  return (
    <>
      <ModeSwitcher />
      <DashboardErrorBoundary onReset={loadDashboard}>
        <DashboardRenderer dashboardData={dashboard} onRefresh={loadDashboard} />
      </DashboardErrorBoundary>
    </>
  )
}

export default Dashboard