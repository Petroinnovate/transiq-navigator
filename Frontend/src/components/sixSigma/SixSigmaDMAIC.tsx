// ============================================================================
// SixSigmaDMAIC - Executive Six Sigma Quality Framework
// Purpose: Board-grade DMAIC visualization with statistical validity
// ============================================================================

import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { SixSigma } from '@/types/dashboard'
import { Activity, AlertTriangle, CheckCircle2, Target, TrendingUp } from 'lucide-react'

interface SixSigmaDMAICProps {
  sixSigma?: SixSigma
}

export const SixSigmaDMAIC: React.FC<SixSigmaDMAICProps> = ({ sixSigma }) => {
  const [activeTab, setActiveTab] = useState('define')

  // Handle missing data
  if (!sixSigma) {
    return (
      <Card className="border-primary/20">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Activity className="h-5 w-5 text-primary" />
            Six Sigma Quality Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Six Sigma analysis will be available after uploading data.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  const getCapabilityColor = (capability: string): string => {
    switch (capability) {
      case 'High': return 'text-green-600'
      case 'Medium': return 'text-yellow-600'
      case 'Low': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const getCapabilityBadge = (capability: string) => {
    switch (capability) {
      case 'High': return 'default'
      case 'Medium': return 'secondary'
      case 'Low': return 'destructive'
      default: return 'outline'
    }
  }

  const getConfidenceBar = (confidence: number) => {
    const color = confidence >= 0.8 ? 'bg-green-600' : confidence >= 0.6 ? 'bg-yellow-600' : 'bg-red-600'
    return (
      <div className="space-y-1">
        <Progress value={confidence * 100} className="h-2" indicatorClassName={color} />
        <span className="text-xs text-muted-foreground">{(confidence * 100).toFixed(0)}% confidence</span>
      </div>
    )
  }

  return (
    <Card className="border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Activity className="h-5 w-5 text-primary" />
            Six Sigma Quality Analysis
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-lg font-bold">
              {sixSigma.sigmaLevel}σ
            </Badge>
            <Badge variant={getCapabilityBadge(sixSigma.processCapability) as any}>
              {sixSigma.processCapability} Capability
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Statistical Validity Warning */}
        {!sixSigma.statisticalValidity && (
          <Alert variant="destructive" className="mb-4">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              <strong>Statistical Validity Warning:</strong> Data sample size or distribution may not meet Six Sigma requirements. 
              Results should be interpreted with caution and may require additional data collection.
            </AlertDescription>
          </Alert>
        )}

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 p-4 bg-muted/50 rounded-lg">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Sigma Level</p>
            <p className="text-2xl font-bold">{sixSigma.sigmaLevel}σ</p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Defect Rate</p>
            <p className="text-2xl font-bold text-red-600">{sixSigma.defectRate}</p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Process Capability</p>
            <p className={`text-2xl font-bold ${getCapabilityColor(sixSigma.processCapability)}`}>
              {sixSigma.processCapability}
            </p>
          </div>
        </div>

        {/* DMAIC Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="define">Define</TabsTrigger>
            <TabsTrigger value="measure">Measure</TabsTrigger>
            <TabsTrigger value="analyze">Analyze</TabsTrigger>
            <TabsTrigger value="improve">Improve</TabsTrigger>
            <TabsTrigger value="control">Control</TabsTrigger>
          </TabsList>

          {/* Define Phase */}
          <TabsContent value="define" className="space-y-4 mt-4">
            <div className="space-y-3">
              <div>
                <h4 className="font-semibold text-sm mb-2">Problem Statement</h4>
                <p className="text-sm text-muted-foreground">{sixSigma.dmaic.define.problemStatement}</p>
              </div>
              <div>
                <h4 className="font-semibold text-sm mb-2">Goal</h4>
                <p className="text-sm text-muted-foreground">{sixSigma.dmaic.define.goal}</p>
              </div>
              <div>
                <h4 className="font-semibold text-sm mb-2">Scope</h4>
                <p className="text-sm text-muted-foreground">{sixSigma.dmaic.define.scope}</p>
              </div>
              <div>
                <h4 className="font-semibold text-sm mb-2">Stakeholders</h4>
                <div className="flex flex-wrap gap-2">
                  {sixSigma.dmaic.define.stakeholders.map((stakeholder, index) => (
                    <Badge key={index} variant="outline">{stakeholder}</Badge>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                  <Target className="h-4 w-4" />
                  CTQ Characteristics (Critical to Quality)
                </h4>
                <div className="space-y-3">
                  {sixSigma.dmaic.define.ctqCharacteristics.map((ctq, index) => (
                    <div key={index} className="p-3 border rounded-lg bg-card">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                        <div>
                          <p className="text-muted-foreground">Name</p>
                          <p className="font-semibold">{ctq.name}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Specification</p>
                          <p className="font-semibold">{ctq.specification}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Current</p>
                          <p className="font-semibold text-red-600">{ctq.currentPerformance}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Target</p>
                          <p className="font-semibold text-green-600">{ctq.target}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Measure Phase */}
          <TabsContent value="measure" className="space-y-4 mt-4">
            <div className="space-y-3">
              <div>
                <h4 className="font-semibold text-sm mb-2">Data Collection Plan</h4>
                <p className="text-sm text-muted-foreground">{sixSigma.dmaic.measure.dataCollectionPlan}</p>
              </div>
              <div>
                <h4 className="font-semibold text-sm mb-2">Measurement System</h4>
                <p className="text-sm text-muted-foreground">{sixSigma.dmaic.measure.measurementSystem}</p>
              </div>
              <div>
                <h4 className="font-semibold text-sm mb-3">Baseline Metrics</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {sixSigma.dmaic.measure.baselineMetrics.map((metric, index) => (
                    <div key={index} className="p-3 border rounded-lg bg-card">
                      <p className="text-sm text-muted-foreground">{metric.metric}</p>
                      <p className="text-xl font-bold">
                        {metric.value} <span className="text-sm font-normal">{metric.unit}</span>
                      </p>
                      {metric.timestamp && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(metric.timestamp).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
              <div className="p-4 bg-muted/50 rounded-lg">
                <h4 className="font-semibold text-sm mb-3">Data Quality Assessment</h4>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Completeness</span>
                      <span className="font-semibold">{(sixSigma.dmaic.measure.dataQuality.completeness * 100).toFixed(0)}%</span>
                    </div>
                    <Progress value={sixSigma.dmaic.measure.dataQuality.completeness * 100} className="h-2" />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Accuracy</span>
                      <span className="font-semibold">{(sixSigma.dmaic.measure.dataQuality.accuracy * 100).toFixed(0)}%</span>
                    </div>
                    <Progress value={sixSigma.dmaic.measure.dataQuality.accuracy * 100} className="h-2" />
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Reliability</span>
                    <Badge variant="outline">{sixSigma.dmaic.measure.dataQuality.reliability}</Badge>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Analyze Phase */}
          <TabsContent value="analyze" className="space-y-4 mt-4">
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  Root Cause Analysis (with Confidence)
                </h4>
                <div className="space-y-3">
                  {sixSigma.dmaic.analyze.rootCauseAnalysis.map((cause, index) => (
                    <div key={index} className="p-3 border rounded-lg bg-card">
                      <div className="flex items-start justify-between mb-2">
                        <p className="font-semibold text-sm">{cause.cause}</p>
                        <Badge variant={cause.impact === 'High' ? 'destructive' : cause.impact === 'Medium' ? 'secondary' : 'outline'}>
                          {cause.impact} Impact
                        </Badge>
                      </div>
                      {getConfidenceBar(cause.confidence)}
                      <div className="mt-2">
                        <p className="text-xs text-muted-foreground mb-1">Evidence:</p>
                        <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1">
                          {cause.evidence.map((ev, i) => (
                            <li key={i}>{ev}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-sm mb-3">Statistical Tests</h4>
                <div className="space-y-2">
                  {sixSigma.dmaic.analyze.statisticalTests.map((test, index) => (
                    <div key={index} className="p-3 border rounded-lg bg-card flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-sm">{test.testName}</p>
                        <p className="text-xs text-muted-foreground">{test.result}</p>
                        {test.pValue !== undefined && (
                          <p className="text-xs text-muted-foreground">p-value: {test.pValue.toFixed(4)}</p>
                        )}
                      </div>
                      {test.significance ? (
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 text-yellow-600" />
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-sm mb-3">Variation Sources</h4>
                <div className="space-y-2">
                  {sixSigma.dmaic.analyze.variationSources.map((source, index) => (
                    <div key={index} className="p-3 border rounded-lg bg-card">
                      <div className="flex items-center justify-between mb-2">
                        <p className="font-semibold text-sm">{source.source}</p>
                        <Badge variant={source.controllable ? 'default' : 'destructive'}>
                          {source.controllable ? 'Controllable' : 'Uncontrollable'}
                        </Badge>
                      </div>
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span>Contribution</span>
                          <span className="font-semibold">{(source.contribution * 100).toFixed(1)}%</span>
                        </div>
                        <Progress value={source.contribution * 100} className="h-2" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Improve Phase */}
          <TabsContent value="improve" className="space-y-4 mt-4">
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Improvement Solutions
                </h4>
                <div className="space-y-3">
                  {sixSigma.dmaic.improve.solutions.map((solution, index) => (
                    <div key={index} className="p-3 border rounded-lg bg-card">
                      <div className="flex items-start justify-between mb-2">
                        <p className="font-semibold text-sm">{solution.description}</p>
                        <Badge variant={solution.priority === 'High' ? 'default' : solution.priority === 'Medium' ? 'secondary' : 'outline'}>
                          {solution.priority} Priority
                        </Badge>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs mt-2">
                        <div>
                          <p className="text-muted-foreground">Expected Impact</p>
                          <p className="font-semibold">{solution.expectedImpact}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Cost</p>
                          <p className="font-semibold">${solution.cost.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Timeline</p>
                          <p className="font-semibold">{solution.timeline}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {sixSigma.dmaic.improve.pilotResults.length > 0 && (
                <div>
                  <h4 className="font-semibold text-sm mb-3">Pilot Results</h4>
                  <div className="space-y-3">
                    {sixSigma.dmaic.improve.pilotResults.map((pilot, index) => (
                      <div key={index} className="p-3 border rounded-lg bg-card">
                        <p className="font-semibold text-sm mb-1">{pilot.solution}</p>
                        <p className="text-xs text-muted-foreground mb-2">{pilot.outcome}</p>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(pilot.metrics).map(([key, value]) => (
                            <Badge key={key} variant="secondary">
                              {key}: {value}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="p-4 bg-muted/50 rounded-lg">
                <h4 className="font-semibold text-sm mb-3">Implementation Plan</h4>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-muted-foreground mb-2">Timeline: {sixSigma.dmaic.improve.implementationPlan.timeline}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold mb-2">Phases:</p>
                    {sixSigma.dmaic.improve.implementationPlan.phases.map((phase, index) => (
                      <div key={index} className="mb-2 text-xs">
                        <p className="font-semibold">{phase.name} ({phase.duration})</p>
                        <ul className="list-disc list-inside text-muted-foreground ml-2">
                          {phase.milestones.map((milestone, i) => (
                            <li key={i}>{milestone}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                  <div>
                    <p className="text-xs font-semibold mb-2">Risks:</p>
                    {sixSigma.dmaic.improve.implementationPlan.risks.map((risk, index) => (
                      <div key={index} className="p-2 border rounded text-xs mb-2">
                        <p className="font-semibold">{risk.description}</p>
                        <div className="flex gap-2 mt-1">
                          <Badge variant="outline" className="text-xs">P: {risk.probability}</Badge>
                          <Badge variant="outline" className="text-xs">I: {risk.impact}</Badge>
                        </div>
                        <p className="text-muted-foreground mt-1">Mitigation: {risk.mitigation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Control Phase */}
          <TabsContent value="control" className="space-y-4 mt-4">
            <div className="space-y-4">
              <div className="p-4 bg-muted/50 rounded-lg">
                <h4 className="font-semibold text-sm mb-3">Control Plan</h4>
                <p className="text-xs text-muted-foreground mb-3">
                  Monitoring Frequency: {sixSigma.dmaic.control.controlPlan.frequency}
                </p>
                <div className="space-y-2">
                  {sixSigma.dmaic.control.controlPlan.metrics.map((metric, index) => (
                    <div key={index} className="p-3 border rounded-lg bg-card">
                      <p className="font-semibold text-sm">{metric.name}</p>
                      <div className="grid grid-cols-3 gap-2 text-xs mt-2">
                        <div>
                          <p className="text-muted-foreground">Target</p>
                          <p className="font-semibold">{metric.target}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Alert Threshold</p>
                          <p className="font-semibold text-red-600">{metric.alertThreshold}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Method</p>
                          <p className="font-semibold">{metric.method}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-3">
                  <p className="text-xs font-semibold mb-1">Responsibilities:</p>
                  <div className="flex flex-wrap gap-2">
                    {sixSigma.dmaic.control.controlPlan.responsibilities.map((resp, index) => (
                      <Badge key={index} variant="outline">{resp}</Badge>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-sm mb-3">Monitoring</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3 border rounded-lg bg-card">
                    <p className="text-xs text-muted-foreground mb-2">Tools</p>
                    <div className="flex flex-wrap gap-1">
                      {sixSigma.dmaic.control.monitoring.tools.map((tool, index) => (
                        <Badge key={index} variant="secondary" className="text-xs">{tool}</Badge>
                      ))}
                    </div>
                  </div>
                  <div className="p-3 border rounded-lg bg-card">
                    <p className="text-xs text-muted-foreground mb-2">Dashboards</p>
                    <div className="flex flex-wrap gap-1">
                      {sixSigma.dmaic.control.monitoring.dashboards.map((dashboard, index) => (
                        <Badge key={index} variant="secondary" className="text-xs">{dashboard}</Badge>
                      ))}
                    </div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Frequency: {sixSigma.dmaic.control.monitoring.frequency}
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-sm mb-3">Documentation & Sustainability</h4>
                <div className="space-y-2 text-xs">
                  <div>
                    <p className="font-semibold mb-1">Procedures:</p>
                    <ul className="list-disc list-inside text-muted-foreground ml-2">
                      {sixSigma.dmaic.control.documentation.procedures.map((proc, index) => (
                        <li key={index}>{proc}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="font-semibold mb-1">Training:</p>
                    <ul className="list-disc list-inside text-muted-foreground ml-2">
                      {sixSigma.dmaic.control.documentation.training.map((train, index) => (
                        <li key={index}>{train}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="flex items-center gap-2">
                    <p className="font-semibold">Audit Trail:</p>
                    {sixSigma.dmaic.control.documentation.auditTrail ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                    )}
                  </div>
                  <div className="p-3 bg-blue-50 dark:bg-blue-950 rounded border border-blue-200 dark:border-blue-800">
                    <p className="font-semibold mb-1">Sustainability Plan</p>
                    <p className="text-muted-foreground">Review: {sixSigma.dmaic.control.sustainability.reviewSchedule}</p>
                    <p className="text-muted-foreground">Owner: {sixSigma.dmaic.control.sustainability.ownership}</p>
                    <p className="font-semibold mt-2 mb-1">Continuous Improvement:</p>
                    <ul className="list-disc list-inside text-muted-foreground ml-2">
                      {sixSigma.dmaic.control.sustainability.continuousImprovement.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
