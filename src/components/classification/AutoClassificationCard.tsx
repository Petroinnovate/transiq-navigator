// ============================================================================
// AutoClassificationCard - AI Report Understanding Display
// Purpose: Show how AI understands and categorizes the report
// ============================================================================

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { AutoClassification } from '@/types/dashboard'
import { Brain, Building2, Calendar, Target } from 'lucide-react'

interface AutoClassificationCardProps {
  classification: AutoClassification
}

export const AutoClassificationCard: React.FC<AutoClassificationCardProps> = ({ classification }) => {
  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getProgressColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'bg-green-600'
    if (confidence >= 0.6) return 'bg-yellow-600'
    return 'bg-red-600'
  }

  const getReportTypeBadgeVariant = (type: string) => {
    const typeMap: Record<string, string> = {
      operations: 'default',
      hse: 'destructive',
      finance: 'secondary',
      maintenance: 'outline',
      production: 'default',
      quality: 'secondary',
    }
    return typeMap[type.toLowerCase()] || 'outline'
  }

  return (
    <Card className="border-primary/20">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Brain className="h-5 w-5 text-primary" />
          AI Classification - Report Understanding
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-5">
          {/* Report Types */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Target className="h-4 w-4" />
              Report Type(s)
            </div>
            <div className="flex flex-wrap gap-2">
              {classification.reportType.map((type, index) => (
                <Badge 
                  key={index} 
                  variant={getReportTypeBadgeVariant(type) as any}
                  className="text-sm px-3 py-1"
                >
                  {type}
                </Badge>
              ))}
            </div>
          </div>

          {/* Asset Scope */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Building2 className="h-4 w-4" />
              Asset Scope
            </div>
            <Badge variant="outline" className="text-base px-4 py-2 font-semibold">
              {classification.assetScope}
            </Badge>
          </div>

          {/* Time Horizon */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Calendar className="h-4 w-4" />
              Time Horizon
            </div>
            <Badge variant="secondary" className="text-base px-4 py-2 font-semibold">
              {classification.timeHorizon}
            </Badge>
          </div>

          {/* Decision Level */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Target className="h-4 w-4" />
              Decision Level
            </div>
            <Badge 
              variant={classification.decisionLevel.toLowerCase().includes('board') ? 'default' : 'outline'}
              className="text-base px-4 py-2 font-semibold"
            >
              {classification.decisionLevel}
            </Badge>
          </div>

          {/* Classification Confidence */}
          <div className="space-y-3 pt-2 border-t">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Classification Confidence
              </span>
              <span className={`text-lg font-bold ${getConfidenceColor(classification.confidence)}`}>
                {(classification.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <Progress 
              value={classification.confidence * 100} 
              className="h-2"
              indicatorClassName={getProgressColor(classification.confidence)}
            />
            {classification.confidence < 0.8 && (
              <p className="text-xs text-yellow-600 bg-yellow-50 p-2 rounded">
                ⚠ Lower confidence - AI may need additional context or clearer data patterns
              </p>
            )}
          </div>

          {/* Info Box */}
          <div className="p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
            <p className="text-xs text-blue-800 dark:text-blue-200">
              <strong>What this means:</strong> AI has analyzed the report structure, content patterns, 
              and context to automatically categorize it. This ensures proper routing, analysis depth, 
              and stakeholder alignment without manual classification.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
