// ============================================================================
// PredictiveInsights - Board-Level Forecasting and What-If Analysis
// Purpose: Executive forecasting with risk coding and scenario planning
// ============================================================================

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { PredictiveBlock } from '@/types/dashboard'
import { TrendingUp, AlertTriangle, Lightbulb, Target } from 'lucide-react'

interface PredictiveInsightsProps {
  predictive: PredictiveBlock
}

export const PredictiveInsights: React.FC<PredictiveInsightsProps> = ({ predictive }) => {
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

  const getRiskBgColor = (risk: string): string => {
    switch (risk) {
      case 'High': return 'bg-red-50 dark:bg-red-950/20 border-red-200'
      case 'Medium': return 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200'
      case 'Low': return 'bg-green-50 dark:bg-green-950/20 border-green-200'
      default: return 'bg-gray-50 dark:bg-gray-950/20 border-gray-200'
    }
  }

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'bg-green-600'
    if (confidence >= 0.6) return 'bg-yellow-600'
    return 'bg-red-600'
  }

  const getProbabilityColor = (probability: number): string => {
    if (probability >= 0.7) return 'bg-green-600'
    if (probability >= 0.4) return 'bg-yellow-600'
    return 'bg-red-600'
  }

  return (
    <Card className="border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <TrendingUp className="h-5 w-5 text-primary" />
            Predictive Insights & Forecasting
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{predictive.forecastHorizon}</Badge>
            <Badge variant={predictive.confidence >= 0.8 ? 'default' : predictive.confidence >= 0.6 ? 'secondary' : 'destructive'}>
              {(predictive.confidence * 100).toFixed(0)}% Confidence
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Overall Confidence Warning */}
          {predictive.confidence < 0.7 && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>Moderate Confidence:</strong> Predictions are based on available data patterns. 
                Consider collecting additional data or expert validation for critical decisions.
              </AlertDescription>
            </Alert>
          )}

          {/* Predictions Section */}
          <div className="space-y-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Target className="h-4 w-4" />
              Forecasted Metrics ({predictive.forecastHorizon})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {predictive.predictions.map((prediction, index) => (
                <div
                  key={index}
                  className={`p-4 border-2 rounded-lg ${getRiskBgColor(prediction.risk)}`}
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h4 className="font-semibold text-base mb-1">{prediction.metric}</h4>
                      <p className="text-xs text-muted-foreground">{prediction.timeframe}</p>
                    </div>
                    <Badge variant={getRiskBadge(prediction.risk) as any}>
                      {prediction.risk} Risk
                    </Badge>
                  </div>

                  {/* Forecasted Value */}
                  <div className="mb-3">
                    <p className="text-3xl font-bold">
                      {prediction.forecastedValue.toLocaleString()}
                    </p>
                  </div>

                  {/* Confidence Interval */}
                  {prediction.confidenceInterval && (
                    <div className="space-y-2 p-3 bg-white dark:bg-gray-900 rounded-lg border">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Confidence Interval</span>
                        <span className="font-semibold">
                          {(prediction.confidenceInterval.confidenceLevel * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm font-semibold">
                        <span className="text-red-600">
                          {prediction.confidenceInterval.lower.toLocaleString()}
                        </span>
                        <span className="text-muted-foreground">to</span>
                        <span className="text-green-600">
                          {prediction.confidenceInterval.upper.toLocaleString()}
                        </span>
                      </div>
                      <div className="relative pt-1">
                        <div className="h-2 bg-gradient-to-r from-red-200 via-yellow-200 to-green-200 rounded-full" />
                      </div>
                    </div>
                  )}

                  {/* Risk Indicator */}
                  <div className="mt-3 flex items-center gap-2">
                    <AlertTriangle className={`h-4 w-4 ${getRiskColor(prediction.risk)}`} />
                    <p className={`text-xs font-semibold ${getRiskColor(prediction.risk)}`}>
                      {prediction.risk === 'High' 
                        ? 'Requires immediate attention and mitigation planning' 
                        : prediction.risk === 'Medium'
                        ? 'Monitor closely and prepare contingency plans'
                        : 'Maintain current controls and monitoring'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* What-If Scenarios Section */}
          {predictive.whatIfScenarios && predictive.whatIfScenarios.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <Lightbulb className="h-4 w-4" />
                What-If Scenario Analysis
              </h3>
              <div className="space-y-3">
                {predictive.whatIfScenarios.map((scenario, index) => (
                  <div
                    key={index}
                    className="p-4 border-2 rounded-lg bg-card hover:shadow-md transition-all"
                  >
                    {/* Scenario Header */}
                    <div className="flex items-start justify-between mb-3">
                      <h4 className="font-semibold text-base">{scenario.name}</h4>
                      <div className="flex flex-col items-end gap-1">
                        <Badge variant="outline" className="text-xs">
                          {(scenario.probability * 100).toFixed(0)}% Probability
                        </Badge>
                        <Progress 
                          value={scenario.probability * 100} 
                          className="h-1.5 w-20"
                          indicatorClassName={getProbabilityColor(scenario.probability)}
                        />
                      </div>
                    </div>

                    {/* Assumptions */}
                    <div className="mb-3">
                      <p className="text-xs font-semibold text-muted-foreground mb-2">Assumptions:</p>
                      <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1">
                        {scenario.assumptions.map((assumption, i) => (
                          <li key={i}>{assumption}</li>
                        ))}
                      </ul>
                    </div>

                    {/* Outcome */}
                    <div className="p-3 bg-muted/50 rounded-lg">
                      <p className="text-xs font-semibold mb-1">Expected Outcome:</p>
                      <p className="text-sm">{scenario.outcome}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Model Confidence Footer */}
          <div className="pt-4 border-t">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-muted-foreground">
                Overall Forecast Confidence
              </span>
              <span className="text-lg font-bold">
                {(predictive.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <Progress 
              value={predictive.confidence * 100} 
              className="h-2"
              indicatorClassName={getConfidenceColor(predictive.confidence)}
            />
            <p className="text-xs text-muted-foreground mt-2">
              Based on historical data patterns, statistical models, and AI analysis. 
              Review assumptions and validate with domain experts before critical decisions.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
