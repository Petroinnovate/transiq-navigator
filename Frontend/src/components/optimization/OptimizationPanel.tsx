// ============================================================================
// OptimizationPanel - Decision-First Optimization Suggestions
// Purpose: Executive-ready optimization with ROI, payback, and risk assessment
// ============================================================================

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Optimization } from '@/types/dashboard'
import { Lightbulb, DollarSign, Clock, AlertTriangle, CheckCircle2, XCircle, Timer } from 'lucide-react'

interface OptimizationPanelProps {
  optimizations: Optimization[]
}

export const OptimizationPanel: React.FC<OptimizationPanelProps> = ({ optimizations }) => {
  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'High': return 'bg-red-600'
      case 'Medium': return 'bg-yellow-600'
      case 'Low': return 'bg-blue-600'
      default: return 'bg-gray-600'
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

  const getRiskColor = (risk: string): string => {
    switch (risk) {
      case 'High': return 'text-red-600'
      case 'Medium': return 'text-yellow-600'
      case 'Low': return 'text-green-600'
      default: return 'text-gray-600'
    }
  }

  const getRiskBadge = (risk: string) => {
    switch (risk) {
      case 'High': return 'destructive'
      case 'Medium': return 'secondary'
      case 'Low': return 'default'
      default: return 'outline'
    }
  }

  const getApprovalStatusIcon = (status?: string) => {
    switch (status) {
      case 'Approved':
        return <CheckCircle2 className="h-4 w-4 text-green-600" />
      case 'Rejected':
        return <XCircle className="h-4 w-4 text-red-600" />
      case 'Under Review':
        return <Timer className="h-4 w-4 text-yellow-600" />
      case 'Pending':
        return <Clock className="h-4 w-4 text-blue-600" />
      default:
        return null
    }
  }

  const getApprovalStatusBadge = (status?: string) => {
    switch (status) {
      case 'Approved': return 'default'
      case 'Rejected': return 'destructive'
      case 'Under Review': return 'secondary'
      case 'Pending': return 'outline'
      default: return 'outline'
    }
  }

  const getCategoryIcon = (category: string) => {
    // You can expand this with more specific icons per category
    return <Lightbulb className="h-4 w-4" />
  }

  // Sort by priority: High > Medium > Low
  const sortedOptimizations = [...optimizations].sort((a, b) => {
    const priorityOrder = { High: 0, Medium: 1, Low: 2 }
    return priorityOrder[a.priority] - priorityOrder[b.priority]
  })

  return (
    <Card className="border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Lightbulb className="h-5 w-5 text-primary" />
            Optimization Suggestions
          </CardTitle>
          <Badge variant="secondary">{optimizations.length} Recommendations</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {sortedOptimizations.map((optimization, index) => (
            <div
              key={index}
              className={`p-4 border-2 rounded-lg transition-all hover:shadow-md ${
                optimization.priority === 'High' ? 'border-red-200 bg-red-50/50 dark:bg-red-950/20' :
                optimization.priority === 'Medium' ? 'border-yellow-200 bg-yellow-50/50 dark:bg-yellow-950/20' :
                'border-blue-200 bg-blue-50/50 dark:bg-blue-950/20'
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    {getCategoryIcon(optimization.category)}
                    <h3 className="font-semibold text-base">{optimization.title}</h3>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    {optimization.category}
                  </Badge>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <Badge variant={getPriorityBadge(optimization.priority) as any} className="whitespace-nowrap">
                    {optimization.priority} Priority
                  </Badge>
                  {optimization.approvalStatus && (
                    <div className="flex items-center gap-1">
                      {getApprovalStatusIcon(optimization.approvalStatus)}
                      <Badge variant={getApprovalStatusBadge(optimization.approvalStatus) as any} className="text-xs">
                        {optimization.approvalStatus}
                      </Badge>
                    </div>
                  )}
                </div>
              </div>

              {/* Description */}
              <p className="text-sm text-muted-foreground mb-4">
                {optimization.description}
              </p>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                {/* ROI */}
                {optimization.roi !== undefined && (
                  <div className="p-3 bg-white dark:bg-gray-900 rounded-lg border">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                      <DollarSign className="h-3 w-3" />
                      ROI
                    </div>
                    <p className="text-xl font-bold text-green-600">
                      {optimization.roi > 0 ? '+' : ''}{optimization.roi.toFixed(1)}%
                    </p>
                  </div>
                )}

                {/* Payback Period */}
                {optimization.paybackPeriod && (
                  <div className="p-3 bg-white dark:bg-gray-900 rounded-lg border">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                      <Clock className="h-3 w-3" />
                      Payback
                    </div>
                    <p className="text-xl font-bold">
                      {optimization.paybackPeriod}
                    </p>
                  </div>
                )}

                {/* Estimated Cost */}
                {optimization.estimatedCost !== undefined && (
                  <div className="p-3 bg-white dark:bg-gray-900 rounded-lg border">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                      <DollarSign className="h-3 w-3" />
                      Est. Cost
                    </div>
                    <p className="text-xl font-bold">
                      ${optimization.estimatedCost.toLocaleString()}
                    </p>
                  </div>
                )}

                {/* Timeline */}
                {optimization.timeline && (
                  <div className="p-3 bg-white dark:bg-gray-900 rounded-lg border">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                      <Clock className="h-3 w-3" />
                      Timeline
                    </div>
                    <p className="text-xl font-bold">
                      {optimization.timeline}
                    </p>
                  </div>
                )}
              </div>

              {/* Impact & Risk */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="p-3 bg-white dark:bg-gray-900 rounded-lg border">
                  <p className="text-xs text-muted-foreground mb-1">Expected Impact</p>
                  <p className="text-sm font-semibold">{optimization.impact}</p>
                </div>
                <div className="p-3 bg-white dark:bg-gray-900 rounded-lg border">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-muted-foreground mb-1">Risk if Ignored</p>
                    <Badge variant={getRiskBadge(optimization.riskIfIgnored) as any} className="text-xs">
                      {optimization.riskIfIgnored}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <AlertTriangle className={`h-4 w-4 ${getRiskColor(optimization.riskIfIgnored)}`} />
                    <p className={`text-sm font-semibold ${getRiskColor(optimization.riskIfIgnored)}`}>
                      {optimization.riskIfIgnored === 'High' 
                        ? 'Immediate action recommended' 
                        : optimization.riskIfIgnored === 'Medium'
                        ? 'Address within planning cycle'
                        : 'Monitor and evaluate'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Decision Indicator for High Priority */}
              {optimization.priority === 'High' && (
                <div className="mt-3 p-3 bg-red-100 dark:bg-red-950 rounded-lg border border-red-300 dark:border-red-800">
                  <p className="text-xs text-red-800 dark:text-red-200 font-semibold flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    Executive Decision Required - High priority optimization with significant impact
                  </p>
                </div>
              )}
            </div>
          ))}

          {optimizations.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <Lightbulb className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No optimization suggestions available</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
