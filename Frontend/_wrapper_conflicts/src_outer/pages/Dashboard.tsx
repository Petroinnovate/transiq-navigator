// ============================================================================
// Dashboard Page - Main Executive Dashboard View
// Purpose: Board-grade AI analytics dashboard with full schema integration
// ============================================================================

import React, { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { MetaPanel } from '@/components/meta/MetaPanel'
import { AutoClassificationCard } from '@/components/classification/AutoClassificationCard'
import { KPICard } from '@/components/kpis/KPICard'
import { SixSigmaDMAIC } from '@/components/sixSigma/SixSigmaDMAIC'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { OptimizationPanel } from '@/components/optimization/OptimizationPanel'
import { PredictiveInsights } from '@/components/predictive/PredictiveInsights'
import { ExplainabilityPanel } from '@/components/explainability/ExplainabilityPanel'
import { InsightsAlerts } from '@/components/insights/InsightsAlerts'
import { AlertCallouts } from '@/components/tremor-widgets/AlertCallouts'
import { KPIProgressCircles } from '@/components/tremor-widgets/KPIProgressCircles'
import { RootCauseBarList } from '@/components/tremor-widgets/RootCauseBarList'
import { OptimizationCategoryBar } from '@/components/tremor-widgets/OptimizationCategoryBar'
import { RigTracker } from '@/components/tremor-widgets/RigTracker'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { dashboardQueries } from '@/api/dashboardApi'
import { useDashboard } from '@/contexts/DashboardContext'
import { AlertTriangle, RefreshCw, TrendingUp } from 'lucide-react'

interface DashboardProps {
  reportId?: string
}

export const Dashboard: React.FC<DashboardProps> = ({ reportId }) => {
  const { setDashboardData, setIsLoading, setError, setReportId } = useDashboard()

  // Use React Query for data fetching
  const { data, isLoading, error, refetch } = useQuery(
    reportId ? dashboardQueries.byId(reportId) : dashboardQueries.latest()
  )

  // Update context when data changes
  useEffect(() => {
    if (data) {
      setDashboardData(data)
      if (data.meta?.reportId) setReportId(data.meta.reportId)
    }
    setIsLoading(isLoading)
    setError(error ? (error as Error).message : null)
  }, [data, isLoading, error, setDashboardData, setIsLoading, setError, setReportId])

  // Loading State
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <Skeleton className="h-32 w-full" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
      </DashboardLayout>
    )
  }

  // Error State
  if (error) {
    return (
      <DashboardLayout>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">Failed to load dashboard data</p>
              <p className="text-sm">{(error as Error).message}</p>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => refetch()}
                className="mt-2"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      </DashboardLayout>
    )
  }

  // No Data State
  if (!data) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-4">
            <TrendingUp className="h-16 w-16 mx-auto text-muted-foreground opacity-50" />
            <h2 className="text-2xl font-bold">No Dashboard Data Available</h2>
            <p className="text-muted-foreground">
              Upload a report or wait for data processing to complete
            </p>
            <Button onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Check Again
            </Button>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  // Main Dashboard Render
  return (
    <DashboardLayout
      header={
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Executive AI Dashboard</h1>
            <p className="text-muted-foreground">
              Board-grade analytics with full transparency and compliance
            </p>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => refetch()}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      }
    >
      {/* Tremor: Priority alert banners — shown first so urgent items are never missed */}
      {data.insights?.alerts && data.insights.alerts.length > 0 && (
        <AlertCallouts alerts={data.insights.alerts} />
      )}

      {/* Meta Information - Always Visible at Top */}
      <MetaPanel meta={data.meta} />

      {/* Auto-Classification Card */}
      <AutoClassificationCard classification={data.autoClassification} />

      {/* KPI Cards Grid */}
      {data.kpis && data.kpis.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Key Performance Indicators</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {data.kpis.map((kpi, index) => (
              <KPICard key={index} kpi={kpi} />
            ))}
          </div>
        </div>
      )}

      {/* Tremor: KPI circular progress gauges */}
      {data.kpis && data.kpis.length > 0 && (
        <KPIProgressCircles kpis={data.kpis} />
      )}

      {/* Tremor: KPI health tracker strip */}
      {data.kpis && data.kpis.length > 0 && (
        <RigTracker kpis={data.kpis} />
      )}

      {/* Six Sigma DMAIC */}
      {data.sixSigma && <SixSigmaDMAIC sixSigma={data.sixSigma} />}

      {/* Charts Section */}
      {data.charts && data.charts.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Visualizations & Analytics</h2>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {data.charts.map((chart) => (
              <ChartRenderer key={chart.chartId} chart={chart} />
            ))}
          </div>
        </div>
      )}

      {/* Tremor: Root cause ranked bar list (from DMAIC Analyze) */}
      {data.sixSigma?.dmaic?.analyze?.rootCauses && (
        <RootCauseBarList rootCauses={data.sixSigma.dmaic.analyze.rootCauses} />
      )}

      {/* Optimization Suggestions */}
      {data.optimizationSuggestions && data.optimizationSuggestions.length > 0 && (
        <OptimizationPanel optimizations={data.optimizationSuggestions} />
      )}

      {/* Tremor: Optimization savings distribution category bar */}
      {data.optimizationSuggestions && data.optimizationSuggestions.length > 0 && (
        <OptimizationCategoryBar optimizations={data.optimizationSuggestions} />
      )}

      {/* Predictive Insights (Optional) */}
      {data.predictive && (
        <PredictiveInsights predictive={data.predictive} />
      )}

      {/* Explainability Panel (CRITICAL - Always Show if Available) */}
      {data.explainability && (
        <ExplainabilityPanel explainability={data.explainability} />
      )}

      {/* Insights & Alerts */}
      {data.insights && <InsightsAlerts insights={data.insights} />}
    </DashboardLayout>
  )
}

export default Dashboard
