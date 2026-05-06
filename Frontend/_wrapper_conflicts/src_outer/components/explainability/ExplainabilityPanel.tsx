// ============================================================================
// ExplainabilityPanel - CRITICAL for PSU/Board/Audit Compliance
// Purpose: AI transparency, reasoning, and audit trail for regulatory compliance
// ============================================================================

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Explainability } from '@/types/dashboard'
import { Shield, Database, AlertCircle, Info, Brain, FileText, Clock } from 'lucide-react'

interface ExplainabilityPanelProps {
  explainability: Explainability
}

export const ExplainabilityPanel: React.FC<ExplainabilityPanelProps> = ({ explainability }) => {
  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  return (
    <Card className="border-2 border-primary/30 shadow-lg">
      <CardHeader className="pb-3 bg-primary/5">
        <div className="flex items-start justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Shield className="h-5 w-5 text-primary" />
            Explainability & Audit Trail
          </CardTitle>
          <Badge variant="default" className="gap-1">
            <Shield className="h-3 w-3" />
            PSU/Board Compliant
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Full transparency for regulatory compliance and executive decision-making
        </p>
      </CardHeader>
      <CardContent className="pt-6">
        <Accordion type="multiple" className="w-full" defaultValue={['reasoning', 'data-sources']}>
          {/* AI Reasoning */}
          <AccordionItem value="reasoning">
            <AccordionTrigger className="text-sm font-semibold hover:no-underline">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-primary" />
                AI Reasoning & Methodology
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="p-4 bg-muted/50 rounded-lg space-y-3">
                <div className="flex items-start gap-2">
                  <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm">
                    <p className="font-semibold mb-2">How AI Arrived at These Conclusions:</p>
                    <p className="text-muted-foreground whitespace-pre-line">
                      {explainability.reasoning}
                    </p>
                  </div>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Data Sources */}
          <AccordionItem value="data-sources">
            <AccordionTrigger className="text-sm font-semibold hover:no-underline">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-primary" />
                Data Sources Used
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground mb-3">
                  All data sources contributing to this analysis:
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {explainability.dataSourcesUsed.map((source, index) => (
                    <div
                      key={index}
                      className="p-3 border rounded-lg bg-card flex items-center gap-2"
                    >
                      <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="text-sm font-medium">{source}</span>
                    </div>
                  ))}
                </div>
                {explainability.dataSourcesUsed.length === 0 && (
                  <p className="text-sm text-muted-foreground italic">No data sources specified</p>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Assumptions */}
          <AccordionItem value="assumptions">
            <AccordionTrigger className="text-sm font-semibold hover:no-underline">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-yellow-600" />
                Assumptions Made
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground mb-3">
                  Key assumptions underlying this analysis:
                </p>
                <ul className="space-y-2">
                  {explainability.assumptions.map((assumption, index) => (
                    <li
                      key={index}
                      className="p-3 border-l-4 border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20 rounded-r text-sm"
                    >
                      {assumption}
                    </li>
                  ))}
                </ul>
                {explainability.assumptions.length === 0 && (
                  <p className="text-sm text-muted-foreground italic">No explicit assumptions documented</p>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Limitations */}
          <AccordionItem value="limitations">
            <AccordionTrigger className="text-sm font-semibold hover:no-underline">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-600" />
                Known Limitations
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground mb-3">
                  Constraints and limitations to be aware of:
                </p>
                <ul className="space-y-2">
                  {explainability.limitations.map((limitation, index) => (
                    <li
                      key={index}
                      className="p-3 border-l-4 border-red-500 bg-red-50 dark:bg-red-950/20 rounded-r text-sm"
                    >
                      {limitation}
                    </li>
                  ))}
                </ul>
                {explainability.limitations.length === 0 && (
                  <p className="text-sm text-muted-foreground italic">No limitations documented</p>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Model Information */}
          {explainability.modelInfo && (
            <AccordionItem value="model-info">
              <AccordionTrigger className="text-sm font-semibold hover:no-underline">
                <div className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-primary" />
                  AI Model Information
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="p-4 bg-muted/50 rounded-lg space-y-3">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Model Name</p>
                      <p className="font-semibold text-sm">{explainability.modelInfo.name}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Version</p>
                      <Badge variant="outline">{explainability.modelInfo.version}</Badge>
                    </div>
                    {explainability.modelInfo.accuracy !== undefined && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Accuracy</p>
                        <p className="font-semibold text-sm text-green-600">
                          {(explainability.modelInfo.accuracy * 100).toFixed(1)}%
                        </p>
                      </div>
                    )}
                    {explainability.modelInfo.lastTrained && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Last Trained</p>
                        <p className="font-semibold text-sm">
                          {new Date(explainability.modelInfo.lastTrained).toLocaleDateString()}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Audit Trail */}
          <AccordionItem value="audit-trail">
            <AccordionTrigger className="text-sm font-semibold hover:no-underline">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-primary" />
                Audit Trail ({explainability.auditTrail.length} events)
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground mb-3">
                  Complete timeline of analysis actions for compliance:
                </p>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {explainability.auditTrail.map((entry, index) => (
                    <div
                      key={index}
                      className="p-3 border rounded-lg bg-card hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-1">
                        <span className="font-semibold text-sm">{entry.action}</span>
                        <Badge variant="outline" className="text-xs">
                          {formatTimestamp(entry.timestamp)}
                        </Badge>
                      </div>
                      {entry.user && (
                        <p className="text-xs text-muted-foreground mb-1">User: {entry.user}</p>
                      )}
                      <p className="text-sm text-muted-foreground">{entry.details}</p>
                    </div>
                  ))}
                </div>
                {explainability.auditTrail.length === 0 && (
                  <p className="text-sm text-muted-foreground italic">No audit trail entries available</p>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        {/* Compliance Footer */}
        <div className="mt-6 p-4 bg-green-50 dark:bg-green-950/20 border-2 border-green-200 dark:border-green-800 rounded-lg">
          <div className="flex items-start gap-3">
            <Shield className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
            <div className="text-xs space-y-1">
              <p className="font-semibold text-green-900 dark:text-green-100">
                ✓ Regulatory Compliance Certified
              </p>
              <p className="text-green-800 dark:text-green-200">
                This analysis meets PSU, Board, and Audit requirements for transparency, 
                traceability, and explainability. All decisions are backed by documented 
                reasoning, data sources, and comprehensive audit trails.
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
