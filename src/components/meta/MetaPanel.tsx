// ============================================================================
// MetaPanel - Trust & Audit Confidence Display
// Purpose: Executive-level trust indicators and audit trail
// ============================================================================

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { MetaInfo } from '@/types/dashboard'
import { Shield, Clock, FileText, TrendingUp } from 'lucide-react'

interface MetaPanelProps {
  meta: MetaInfo
}

export const MetaPanel: React.FC<MetaPanelProps> = ({ meta }) => {
  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getConfidenceBadgeVariant = (confidence: number) => {
    if (confidence >= 0.8) return 'default'
    if (confidence >= 0.6) return 'secondary'
    return 'destructive'
  }

  const getReadinessColor = (score: number): string => {
    if (score >= 80) return 'bg-green-600'
    if (score >= 60) return 'bg-yellow-600'
    return 'bg-red-600'
  }

  const formatDate = (isoString: string): string => {
    const date = new Date(isoString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <Card className="border-2 border-primary/20 shadow-lg">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Shield className="h-5 w-5 text-primary" />
          Report Intelligence & Trust Indicators
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Report ID */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileText className="h-4 w-4" />
              Report ID
            </div>
            <div className="font-mono text-sm font-semibold truncate" title={meta.reportId}>
              {meta.reportId}
            </div>
          </div>

          {/* Ingestion Time */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              Ingested At
            </div>
            <div className="text-sm font-semibold">
              {formatDate(meta.ingestedAt)}
            </div>
          </div>

          {/* Source Type */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileText className="h-4 w-4" />
              Source Type
            </div>
            <Badge variant="outline" className="font-semibold">
              {meta.sourceType.toUpperCase()}
            </Badge>
          </div>

          {/* Overall Confidence */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <TrendingUp className="h-4 w-4" />
              AI Confidence
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-2xl font-bold ${getConfidenceColor(meta.confidenceOverall)}`}>
                {(meta.confidenceOverall * 100).toFixed(0)}%
              </span>
              <Badge variant={getConfidenceBadgeVariant(meta.confidenceOverall)}>
                {meta.confidenceOverall >= 0.8 ? 'High' : meta.confidenceOverall >= 0.6 ? 'Medium' : 'Low'}
              </Badge>
            </div>
          </div>
        </div>

        {/* Decision Readiness Score */}
        <div className="mt-6 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">
              Decision Readiness Score
            </span>
            <span className={`text-lg font-bold ${getConfidenceColor(meta.decisionReadinessScore / 100)}`}>
              {meta.decisionReadinessScore.toFixed(0)}%
            </span>
          </div>
          <Progress 
            value={meta.decisionReadinessScore} 
            className="h-3"
            indicatorClassName={getReadinessColor(meta.decisionReadinessScore)}
          />
          <p className="text-xs text-muted-foreground">
            {meta.decisionReadinessScore >= 80 
              ? '✓ Report is ready for executive decision-making' 
              : meta.decisionReadinessScore >= 60
              ? '⚠ Report requires validation before critical decisions'
              : '⚠ Report needs additional data or review before use'}
          </p>
        </div>

        {/* Trust Indicators */}
        <div className="mt-4 p-3 bg-muted/50 rounded-lg">
          <div className="flex items-start gap-2">
            <Shield className="h-4 w-4 text-primary mt-0.5" />
            <div className="text-xs space-y-1">
              <p className="font-semibold">PSU/Board/Audit Compliance</p>
              <p className="text-muted-foreground">
                This report includes full audit trail, explainability, and confidence metrics required for regulatory compliance.
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
