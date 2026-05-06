// ============================================================================
// InsightsAlerts - Actionable Insights and Critical Alerts
// Purpose: Executive summary with prioritized alerts and recommendations
// ============================================================================

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Insights } from '@/types/dashboard'
import { AlertTriangle, AlertCircle, Info, CheckCircle2, Lightbulb, TrendingUp } from 'lucide-react'

interface InsightsAlertsProps {
  insights?: Insights
}

export const InsightsAlerts: React.FC<InsightsAlertsProps> = ({ insights }) => {
  // Handle missing data
  if (!insights || !insights.alerts || !insights.recommendations) {
    return (
      <Card className="border-primary/20">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Lightbulb className="h-5 w-5 text-primary" />
            Insights & Alerts
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Insights and alerts will be available after uploading and analyzing data.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'Critical':
        return <AlertTriangle className="h-5 w-5" />
      case 'High':
        return <AlertCircle className="h-5 w-5" />
      case 'Medium':
        return <Info className="h-5 w-5" />
      case 'Low':
        return <CheckCircle2 className="h-5 w-5" />
      default:
        return <Info className="h-5 w-5" />
    }
  }

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'Critical': return 'text-red-600'
      case 'High': return 'text-orange-600'
      case 'Medium': return 'text-yellow-600'
      case 'Low': return 'text-blue-600'
      default: return 'text-gray-600'
    }
  }

  const getSeverityBgColor = (severity: string): string => {
    switch (severity) {
      case 'Critical': return 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800'
      case 'High': return 'bg-orange-50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-800'
      case 'Medium': return 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-800'
      case 'Low': return 'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800'
      default: return 'bg-gray-50 dark:bg-gray-950/20 border-gray-200 dark:border-gray-800'
    }
  }

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'High': return 'destructive'
      case 'Medium': return 'secondary'
      case 'Low': return 'outline'
      default: return 'outline'
    }
  }

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  // Sort alerts by severity: Critical > High > Medium > Low
  const sortedAlerts = [...insights.alerts].sort((a, b) => {
    const severityOrder = { Critical: 0, High: 1, Medium: 2, Low: 3 }
    return severityOrder[a.severity] - severityOrder[b.severity]
  })

  // Sort recommendations by priority
  const sortedRecommendations = [...insights.recommendations].sort((a, b) => {
    const priorityOrder = { High: 0, Medium: 1, Low: 2 }
    return priorityOrder[a.priority] - priorityOrder[b.priority]
  })

  return (
    <div className="space-y-6">
      {/* Executive Summary */}
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <TrendingUp className="h-5 w-5 text-primary" />
            Executive Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed">{insights.summary}</p>
        </CardContent>
      </Card>

      {/* Alerts Section */}
      <Card className="border-primary/20">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <AlertTriangle className="h-5 w-5 text-primary" />
              Critical Alerts & Issues
            </CardTitle>
            <Badge variant={sortedAlerts.length > 0 ? 'destructive' : 'secondary'}>
              {sortedAlerts.length} Alert{sortedAlerts.length !== 1 ? 's' : ''}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {sortedAlerts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <CheckCircle2 className="h-12 w-12 mx-auto mb-3 text-green-600 opacity-50" />
                <p>No active alerts - All systems operating normally</p>
              </div>
            ) : (
              sortedAlerts.map((alert, index) => (
                <div
                  key={index}
                  className={`p-4 border-2 rounded-lg ${getSeverityBgColor(alert.severity)}`}
                >
                  {/* Alert Header */}
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-start gap-2 flex-1">
                      <span className={getSeverityColor(alert.severity)}>
                        {getSeverityIcon(alert.severity)}
                      </span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant={alert.severity === 'Critical' || alert.severity === 'High' ? 'destructive' : 'secondary'}>
                            {alert.severity}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {alert.category}
                          </Badge>
                        </div>
                        <p className="font-semibold text-sm mt-1">{alert.message}</p>
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground whitespace-nowrap ml-2">
                      {formatTimestamp(alert.timestamp)}
                    </span>
                  </div>

                  {/* Action Required */}
                  {alert.actionRequired && (
                    <div className="mt-3 p-2 bg-white dark:bg-gray-900 rounded border-l-4 border-red-600">
                      <p className="text-xs font-semibold mb-1">Action Required:</p>
                      <p className="text-sm">{alert.actionRequired}</p>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Recommendations Section */}
      <Card className="border-primary/20">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Lightbulb className="h-5 w-5 text-primary" />
              AI-Powered Recommendations
            </CardTitle>
            <Badge variant="secondary">
              {sortedRecommendations.length} Recommendation{sortedRecommendations.length !== 1 ? 's' : ''}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {sortedRecommendations.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Lightbulb className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No recommendations available at this time</p>
              </div>
            ) : (
              sortedRecommendations.map((recommendation, index) => (
                <div
                  key={index}
                  className={`p-4 border-2 rounded-lg transition-all hover:shadow-md ${
                    recommendation.priority === 'High' 
                      ? 'border-red-200 bg-red-50/50 dark:bg-red-950/20' 
                      : recommendation.priority === 'Medium'
                      ? 'border-yellow-200 bg-yellow-50/50 dark:bg-yellow-950/20'
                      : 'border-blue-200 bg-blue-50/50 dark:bg-blue-950/20'
                  }`}
                >
                  {/* Recommendation Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h4 className="font-semibold text-base mb-2">{recommendation.title}</h4>
                      <div className="flex items-center gap-2">
                        <Badge variant={getPriorityBadge(recommendation.priority) as any}>
                          {recommendation.priority} Priority
                        </Badge>
                        <span className={`text-xs font-semibold ${getConfidenceColor(recommendation.confidence)}`}>
                          {(recommendation.confidence * 100).toFixed(0)}% Confidence
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-sm text-muted-foreground mb-3">
                    {recommendation.description}
                  </p>

                  {/* Estimated Impact */}
                  <div className="p-3 bg-white dark:bg-gray-900 rounded-lg border">
                    <p className="text-xs font-semibold text-muted-foreground mb-1">
                      Estimated Impact:
                    </p>
                    <p className="text-sm font-semibold text-green-600">
                      {recommendation.estimatedImpact}
                    </p>
                  </div>

                  {/* High Priority Indicator */}
                  {recommendation.priority === 'High' && recommendation.confidence >= 0.7 && (
                    <div className="mt-3 p-2 bg-red-100 dark:bg-red-950 rounded border border-red-300 dark:border-red-800">
                      <p className="text-xs font-semibold text-red-800 dark:text-red-200 flex items-center gap-2">
                        <AlertTriangle className="h-3 w-3" />
                        High-confidence, high-priority recommendation - Consider immediate action
                      </p>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
