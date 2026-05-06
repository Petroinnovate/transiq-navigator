// ============================================================================
// KPICard - Enhanced Key Performance Indicator Card
// Purpose: Confidence-aware KPI display with CTQ linkage and trend indicators
// ============================================================================

import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { KPI } from '@/types/dashboard'
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Target } from 'lucide-react'

interface KPICardProps {
  kpi: KPI
}

export const KPICard: React.FC<KPICardProps> = ({ kpi }) => {
  const getTrendIcon = () => {
    switch (kpi.trend) {
      case 'up':
        return <TrendingUp className="h-5 w-5 text-green-600" />
      case 'down':
        return <TrendingDown className="h-5 w-5 text-red-600" />
      case 'stable':
        return <Minus className="h-5 w-5 text-yellow-600" />
      default:
        return null
    }
  }

  const getTrendColor = () => {
    switch (kpi.trend) {
      case 'up':
        return 'text-green-600'
      case 'down':
        return 'text-red-600'
      case 'stable':
        return 'text-yellow-600'
      default:
        return 'text-gray-600'
    }
  }

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'bg-green-600'
    if (confidence >= 0.6) return 'bg-yellow-600'
    return 'bg-red-600'
  }

  const getTargetAchievement = (): number | null => {
    if (!kpi.target) return null
    return (kpi.value / kpi.target) * 100
  }

  const targetAchievement = getTargetAchievement()

  const showWarning = kpi.confidence < 0.6

  return (
    <Card className={`relative overflow-hidden transition-all hover:shadow-lg ${showWarning ? 'border-yellow-500 border-2' : ''}`}>
      {showWarning && (
        <div className="absolute top-2 right-2 z-10">
          <Badge variant="destructive" className="gap-1">
            <AlertTriangle className="h-3 w-3" />
            Low Confidence
          </Badge>
        </div>
      )}
      
      <CardContent className="p-6">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-1 flex-1">
              <h3 className="font-semibold text-lg text-muted-foreground">{kpi.name}</h3>
              {kpi.linkedCTQ && (
                <div className="flex items-center gap-1 text-xs text-blue-600">
                  <Target className="h-3 w-3" />
                  <span>CTQ: {kpi.linkedCTQ}</span>
                </div>
              )}
            </div>
            {kpi.trend && (
              <div className="flex items-center gap-1">
                {getTrendIcon()}
              </div>
            )}
          </div>

          {/* Value Display */}
          <div className="space-y-1">
            <div className="flex items-baseline gap-2">
              <span className={`text-4xl font-bold ${getTrendColor()}`}>
                {kpi.value.toLocaleString()}
              </span>
              <span className="text-lg text-muted-foreground">{kpi.unit}</span>
            </div>
            
            {/* Target Comparison */}
            {kpi.target && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">Target: {kpi.target.toLocaleString()} {kpi.unit}</span>
                {targetAchievement !== null && (
                  <Badge 
                    variant={targetAchievement >= 100 ? 'default' : targetAchievement >= 80 ? 'secondary' : 'destructive'}
                    className="text-xs"
                  >
                    {targetAchievement.toFixed(0)}%
                  </Badge>
                )}
              </div>
            )}
          </div>

          {/* Target Progress Bar */}
          {kpi.target && targetAchievement !== null && (
            <div className="space-y-1">
              <Progress 
                value={Math.min(targetAchievement, 100)} 
                className="h-2"
                indicatorClassName={targetAchievement >= 100 ? 'bg-green-600' : targetAchievement >= 80 ? 'bg-yellow-600' : 'bg-red-600'}
              />
            </div>
          )}

          {/* Context */}
          {kpi.context && (
            <p className="text-xs text-muted-foreground italic">
              {kpi.context}
            </p>
          )}

          {/* Confidence Indicator */}
          <div className="pt-3 border-t space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Data Confidence</span>
              <span className="font-semibold">{(kpi.confidence * 100).toFixed(0)}%</span>
            </div>
            <Progress 
              value={kpi.confidence * 100} 
              className="h-1.5"
              indicatorClassName={getConfidenceColor(kpi.confidence)}
            />
            {showWarning && (
              <p className="text-xs text-yellow-700 bg-yellow-50 dark:bg-yellow-950 p-2 rounded">
                ⚠ Confidence below 60% - verify data quality before critical decisions
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
