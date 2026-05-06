import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  AlertTriangle,
  CheckCircle,
  FileText,
  TrendingUp,
  TrendingDown,
  Minus,
  DollarSign,
  Shield,
  Lightbulb,
  BarChart3,
  ChevronLeft,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import ChartRenderer from '@/components/ChartRenderer'
import type { SectionAnalysis } from '@/types/dashboard'

interface SectionDetailProps {
  section: SectionAnalysis
  sectionIndex: number
  totalSections: number
  onBack: () => void
}

const impactColor: Record<string, string> = {
  high: 'bg-red-500/20 text-red-400 border-red-500/30',
  medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  low: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
}

const confidenceBadge = (c: number) => {
  if (c >= 0.8) return { label: 'High Confidence', cls: 'bg-emerald-500/20 text-emerald-400' }
  if (c >= 0.5) return { label: 'Medium Confidence', cls: 'bg-amber-500/20 text-amber-400' }
  return { label: 'Low Confidence', cls: 'bg-red-500/20 text-red-400' }
}

const trendIcon = (trend?: string) => {
  if (!trend) return <Minus className="h-4 w-4 text-white/40" />
  const t = trend.toLowerCase()
  if (t === 'improving' || t === 'up') return <TrendingUp className="h-4 w-4 text-emerald-400" />
  if (t === 'deteriorating' || t === 'down') return <TrendingDown className="h-4 w-4 text-red-400" />
  return <Minus className="h-4 w-4 text-white/40" />
}

const SectionDetail: React.FC<SectionDetailProps> = ({
  section,
  sectionIndex,
  totalSections,
  onBack,
}) => {
  const conf = confidenceBadge(section.confidence ?? 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className="text-white/50 hover:text-white mb-2 -ml-2"
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Back to Overview
          </Button>
          <h2 className="text-2xl font-bold text-white">
            {section.title}
          </h2>
          <div className="flex items-center gap-3 mt-1">
            {section.pageRange && (
              <span className="text-sm text-white/50">{section.pageRange}</span>
            )}
            <span className="text-sm text-white/40">
              Section {sectionIndex + 1} of {totalSections}
            </span>
            <Badge className={conf.cls}>{conf.label}</Badge>
            {(section as any).tier && (
              <Badge className={
                (section as any).tier === 1 ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
                  : (section as any).tier === 2 ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                  : 'bg-slate-600/20 text-slate-400 border-slate-600/40'
              }>
                Tier {(section as any).tier} {(section as any).tier === 1 ? '(Full)' : (section as any).tier === 2 ? '(Light)' : '(Minimal)'}
              </Badge>
            )}
            {(section as any).dmaicPhase && (section as any).dmaicPhase !== 'unassigned' && (section as any).dmaicPhase !== 'none' && (
              <Badge className="bg-violet-500/20 text-violet-400 border-violet-500/30">
                DMAIC: {((section as any).dmaicPhase as string).toUpperCase()}
              </Badge>
            )}
            {(section as any).modelUsed && (
              <Badge className={
                (section as any).modelUsed === 'powerful' ? 'bg-violet-500/10 text-violet-300 border-violet-500/20'
                  : (section as any).modelUsed === 'balanced' ? 'bg-teal-500/10 text-teal-300 border-teal-500/20'
                  : 'bg-slate-600/10 text-slate-400 border-slate-600/20'
              }>
                {(section as any).modelUsed}
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Summary */}
      {section.summary && (
        <Card className="border-white/10 bg-white/5">
          <CardContent className="pt-4">
            <p className="text-white/80 leading-relaxed">{section.summary}</p>
          </CardContent>
        </Card>
      )}

      {/* Key Findings */}
      {section.keyFindings && section.keyFindings.length > 0 && (
        <Card className="border-white/10 bg-white/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2 text-white">
              <Lightbulb className="h-5 w-5 text-amber-400" />
              Key Findings ({section.keyFindings.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {section.keyFindings.map((f, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/5"
              >
                <Badge variant="outline" className={impactColor[f.impact] || impactColor.medium}>
                  {f.impact}
                </Badge>
                <p className="text-sm text-white/80 flex-1">{f.finding}</p>
                <span className="text-xs text-white/40 flex-shrink-0">
                  {Math.round((f.confidence ?? 0) * 100)}%
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* KPIs */}
      {section.kpis && section.kpis.length > 0 && (
        <Card className="border-white/10 bg-white/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2 text-white">
              <TrendingUp className="h-5 w-5 text-cyan-400" />
              Section KPIs ({section.kpis.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {section.kpis.map((kpi, i) => (
                <div
                  key={(kpi as any).id || kpi.name || i}
                  className="p-3 rounded-lg bg-white/5 border border-white/10"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-white/50 uppercase tracking-wider">
                      {kpi.name || (kpi as any).title || `KPI ${i + 1}`}
                    </span>
                    {trendIcon((kpi as any).trend)}
                  </div>
                  <div className="text-xl font-bold text-white">
                    {typeof kpi.value === 'number'
                      ? kpi.value.toLocaleString()
                      : kpi.value}
                    <span className="text-sm font-normal text-white/40 ml-1">
                      {kpi.unit}
                    </span>
                  </div>
                  {kpi.target != null && (
                    <div className="text-xs text-white/40 mt-1">
                      Target: {kpi.target.toLocaleString()} {kpi.unit}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Risks */}
      {section.risks && section.risks.length > 0 && (
        <Card className="border-white/10 bg-white/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2 text-white">
              <Shield className="h-5 w-5 text-red-400" />
              Risks ({section.risks.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {section.risks.map((r, i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/5"
              >
                <Badge variant="outline" className={impactColor[r.severity] || impactColor.medium}>
                  {r.severity}
                </Badge>
                <p className="text-sm text-white/80 flex-1">{r.risk}</p>
                {r.probability && (
                  <span className="text-xs text-white/40">P: {r.probability}</span>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Financial Impact */}
      {section.financialImpact?.items && section.financialImpact.items.length > 0 && (
        <Card className="border-white/10 bg-white/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2 text-white">
              <DollarSign className="h-5 w-5 text-emerald-400" />
              Financial Impact
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {section.financialImpact.items.map((item, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5"
              >
                <div>
                  <p className="text-sm text-white/80">{item.description}</p>
                  <span className="text-xs text-white/40">{item.type}</span>
                </div>
                {item.amount != null && (
                  <span className="text-lg font-bold text-emerald-400">
                    {item.unit || '$'}{item.amount.toLocaleString()}
                  </span>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Charts */}
      {section.charts && section.charts.length > 0 && (
        <Card className="border-white/10 bg-white/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2 text-white">
              <BarChart3 className="h-5 w-5 text-teal-400" />
              Section Charts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {section.charts.map((chart, i) => (
                <div key={chart.chartId || (chart as any).id || i}>
                  <ChartRenderer chartData={chart as any} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {section.recommendations && section.recommendations.length > 0 && (
        <Card className="border-white/10 bg-white/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2 text-white">
              <CheckCircle className="h-5 w-5 text-cyan-400" />
              Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {section.recommendations.map((rec, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-white/80"
                >
                  <span className="text-cyan-400 mt-0.5">•</span>
                  {rec}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default SectionDetail
