import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Target,
  BarChart3,
  TrendingUp,
  Lightbulb,
  Shield,
  FileText,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Link,
  Users,
} from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────

interface BaselineKPI {
  name: string
  value: string | number
  unit: string
  source?: string
}

interface ProcessCapability {
  metric: string
  cpk?: number | null
  sigma_level?: number | null
  dpmo?: number | null
}

interface RootCause {
  cause: string
  category?: string
  confidence?: number
}

interface Solution {
  action: string
  linked_cause?: string
  expected_impact?: string
  cost?: number | null
  priority?: 'high' | 'medium' | 'low'
}

interface ControlPlanItem {
  what: string
  how: string
  frequency: string
  owner?: string
}

interface MonitoringKPI {
  kpi: string
  target: string
  alert_threshold: string
}

interface FinancialImpactItem {
  description: string
  amount?: number | null
  unit?: string
  type?: 'saving' | 'cost' | 'exposure'
}

interface KeyKPI {
  name: string
  baseline: string
  current_or_target: string
  improvement: string
}

interface DmaicReport {
  define: {
    problem_statement: string
    business_context: string
    project_scope: string
    voc: string[]
  }
  measure: {
    baseline_kpis: BaselineKPI[]
    data_collection: string
    process_capability: ProcessCapability[]
    data_issues: string[]
  }
  analyze: {
    root_causes: RootCause[]
    validated_causes: string[]
    key_drivers: string[]
    evidence: string[]
  }
  improve: {
    solutions: Solution[]
    impact_estimation: string[]
    cost_benefit: string[]
    risks: string[]
  }
  control: {
    control_plan: ControlPlanItem[]
    monitoring_kpis: MonitoringKPI[]
    standardization: string[]
    risks: string[]
  }
  executive_summary: {
    summary: string
    financial_impact: FinancialImpactItem[]
    key_kpis: KeyKPI[]
    top_risks: string[]
    recommendations: string[]
  }
  gaps: string[]
  compilation_confidence: number
  signal_flags?: Record<string, boolean>
  doc_type?: string
}

interface DmaicCompilerPanelProps {
  dmaicReport: DmaicReport
}

// ── Phase metadata ─────────────────────────────────────────────────────────

const PHASES = [
  {
    key: 'define' as const,
    label: 'Define',
    icon: Target,
    color: 'blue',
    borderColor: 'border-blue-500/40',
    headerBg: 'bg-blue-500/10',
    iconColor: 'text-blue-400',
    badgeClass: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    description: 'Problem, scope, VOC',
  },
  {
    key: 'measure' as const,
    label: 'Measure',
    icon: BarChart3,
    color: 'green',
    borderColor: 'border-emerald-500/40',
    headerBg: 'bg-emerald-500/10',
    iconColor: 'text-emerald-400',
    badgeClass: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    description: 'Baseline KPIs, data',
  },
  {
    key: 'analyze' as const,
    label: 'Analyze',
    icon: TrendingUp,
    color: 'yellow',
    borderColor: 'border-yellow-500/40',
    headerBg: 'bg-yellow-500/10',
    iconColor: 'text-yellow-400',
    badgeClass: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    description: 'Root causes, evidence',
  },
  {
    key: 'improve' as const,
    label: 'Improve',
    icon: Lightbulb,
    color: 'purple',
    borderColor: 'border-purple-500/40',
    headerBg: 'bg-purple-500/10',
    iconColor: 'text-purple-400',
    badgeClass: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    description: 'Solutions, impact',
  },
  {
    key: 'control' as const,
    label: 'Control',
    icon: Shield,
    color: 'cyan',
    borderColor: 'border-cyan-500/40',
    headerBg: 'bg-cyan-500/10',
    iconColor: 'text-cyan-400',
    badgeClass: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    description: 'Monitoring, sustainability',
  },
]

const PRIORITY_COLOR: Record<string, string> = {
  high:   'bg-red-500/20 text-red-400 border-red-500/30',
  medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  low:    'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
}

const FIN_TYPE_COLOR: Record<string, string> = {
  saving:   'text-emerald-400',
  cost:     'text-red-400',
  exposure: 'text-amber-400',
}

// ── Sub-panels ─────────────────────────────────────────────────────────────

function DefinePanel({ data }: { data: DmaicReport['define'] }) {
  return (
    <div className="space-y-4">
      {data.problem_statement && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-1">Problem Statement</p>
          <p className="text-sm text-white/85 leading-relaxed bg-white/5 rounded-lg p-3 border border-white/5">
            {data.problem_statement}
          </p>
        </div>
      )}
      {data.business_context && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-1">Business Context</p>
          <p className="text-sm text-white/70 leading-relaxed">{data.business_context}</p>
        </div>
      )}
      {data.project_scope && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-1">Project Scope</p>
          <p className="text-sm text-white/70 leading-relaxed">{data.project_scope}</p>
        </div>
      )}
      {data.voc && data.voc.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">
            <Users className="inline h-3 w-3 mr-1" />Voice of Customer / CTQs
          </p>
          <ul className="space-y-1">
            {data.voc.map((v, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-white/75">
                <span className="text-blue-400 mt-0.5 flex-shrink-0">▸</span>
                {v}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function MeasurePanel({ data }: { data: DmaicReport['measure'] }) {
  return (
    <div className="space-y-4">
      {data.baseline_kpis && data.baseline_kpis.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Baseline KPIs</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {data.baseline_kpis.map((kpi, i) => (
              <div key={i} className="p-3 bg-white/5 rounded-lg border border-white/5">
                <div className="text-[10px] text-white/40 truncate">{kpi.name}</div>
                <div className="text-lg font-bold text-emerald-400">
                  {kpi.value ?? '—'}
                  <span className="text-xs font-normal text-white/40 ml-1">{kpi.unit}</span>
                </div>
                {kpi.source && <div className="text-[10px] text-white/30 mt-0.5">{kpi.source}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
      {data.process_capability && data.process_capability.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Process Capability</p>
          {data.process_capability.map((pc, i) => (
            <div key={i} className="flex flex-wrap gap-3 p-2 bg-white/5 rounded border border-white/5 text-xs mb-1">
              <span className="text-white/70 font-medium">{pc.metric}</span>
              {pc.sigma_level != null && <span className="text-cyan-400">σ = {pc.sigma_level}</span>}
              {pc.cpk != null && <span className="text-teal-400">Cpk = {pc.cpk}</span>}
              {pc.dpmo != null && <span className="text-amber-400">{pc.dpmo.toLocaleString()} DPMO</span>}
            </div>
          ))}
        </div>
      )}
      {data.data_collection && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-1">Data Collection</p>
          <p className="text-sm text-white/70 leading-relaxed">{data.data_collection}</p>
        </div>
      )}
      {data.data_issues && data.data_issues.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Data Quality Issues</p>
          <ul className="space-y-1">
            {data.data_issues.map((issue, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-amber-300 p-1.5 bg-amber-500/5 border-l-2 border-amber-500/30 rounded-r">
                <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                {issue}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function AnalyzePanel({ data }: { data: DmaicReport['analyze'] }) {
  return (
    <div className="space-y-4">
      {data.root_causes && data.root_causes.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Root Causes</p>
          <ul className="space-y-2">
            {data.root_causes.map((rc, i) => {
              const conf = typeof rc === 'object' ? (rc.confidence ?? null) : null
              const cause = typeof rc === 'object' ? rc.cause : String(rc)
              const cat = typeof rc === 'object' ? rc.category : null
              return (
                <li key={i} className="p-3 bg-white/5 rounded-lg border border-white/5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2">
                      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-red-500/20 text-red-400
                                       text-[10px] font-bold flex items-center justify-center mt-0.5">
                        {i + 1}
                      </span>
                      <span className="text-sm text-white/85 leading-relaxed">{cause}</span>
                    </div>
                    <div className="flex-shrink-0 flex items-center gap-1.5">
                      {cat && <Badge className="text-[10px] px-1.5 py-0 bg-slate-600/30 text-slate-400 border-slate-600/40">{cat}</Badge>}
                      {conf != null && (
                        <span className={`text-[10px] font-semibold ${conf >= 0.7 ? 'text-emerald-400' : conf >= 0.4 ? 'text-amber-400' : 'text-red-400'}`}>
                          {Math.round(conf * 100)}%
                        </span>
                      )}
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}
      {data.validated_causes && data.validated_causes.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Validated Causes</p>
          <ul className="space-y-1">
            {data.validated_causes.map((vc, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-white/75">
                <CheckCircle className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                {vc}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.evidence && data.evidence.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Evidence</p>
          <ul className="space-y-1">
            {data.evidence.map((e, i) => (
              <li key={i} className="text-xs text-white/60 p-2 bg-white/3 border-l-2 border-yellow-500/40 rounded-r">
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.key_drivers && data.key_drivers.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Key Drivers</p>
          <ul className="space-y-1">
            {data.key_drivers.map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-white/75">
                <span className="text-yellow-400 mt-0.5">▸</span>
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function ImprovePanel({ data }: { data: DmaicReport['improve'] }) {
  return (
    <div className="space-y-4">
      {data.solutions && data.solutions.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Solutions</p>
          <ul className="space-y-2">
            {data.solutions.map((sol, i) => {
              const s = typeof sol === 'string' ? { action: sol } : sol
              return (
                <li key={i} className="p-3 bg-white/5 rounded-lg border border-white/5 space-y-1">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-sm text-white/85 font-medium">{s.action}</span>
                    {s.priority && (
                      <Badge className={`text-[10px] px-1.5 py-0 flex-shrink-0 ${PRIORITY_COLOR[s.priority] ?? PRIORITY_COLOR.medium}`}>
                        {s.priority}
                      </Badge>
                    )}
                  </div>
                  {s.linked_cause && (
                    <div className="flex items-center gap-1.5 text-[11px] text-purple-400">
                      <Link className="h-3 w-3" />
                      Linked to: {s.linked_cause}
                    </div>
                  )}
                  {s.expected_impact && (
                    <div className="text-[11px] text-emerald-400">Impact: {s.expected_impact}</div>
                  )}
                  {s.cost != null && (
                    <div className="text-[11px] text-white/40">Cost: ${s.cost.toLocaleString()}</div>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      )}
      {data.impact_estimation && data.impact_estimation.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Impact Estimation</p>
          <ul className="space-y-1">
            {data.impact_estimation.map((ie, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-emerald-300">
                <TrendingUp className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                {ie}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.cost_benefit && data.cost_benefit.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Cost-Benefit / ROI</p>
          <ul className="space-y-1">
            {data.cost_benefit.map((cb, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-white/75">
                <DollarSign className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                {cb}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.risks && data.risks.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Implementation Risks</p>
          <ul className="space-y-1">
            {data.risks.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-amber-300 p-1.5 bg-amber-500/5 border-l-2 border-amber-500/30 rounded-r">
                <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function ControlPanel({ data }: { data: DmaicReport['control'] }) {
  return (
    <div className="space-y-4">
      {data.control_plan && data.control_plan.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Control Plan</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/10">
                  {['What', 'How', 'Frequency', 'Owner'].map(h => (
                    <th key={h} className="text-left text-white/40 font-semibold py-1.5 pr-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.control_plan.map((cp, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/3 transition-colors">
                    <td className="py-1.5 pr-3 text-white/80">{cp.what}</td>
                    <td className="py-1.5 pr-3 text-white/65">{cp.how}</td>
                    <td className="py-1.5 pr-3 text-cyan-400">{cp.frequency}</td>
                    <td className="py-1.5 text-white/50">{cp.owner ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {data.monitoring_kpis && data.monitoring_kpis.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Monitoring KPIs</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {data.monitoring_kpis.map((kpi, i) => (
              <div key={i} className="p-3 bg-cyan-500/5 rounded-lg border border-cyan-500/15">
                <div className="text-sm font-semibold text-white/85">{kpi.kpi}</div>
                <div className="flex gap-3 mt-1 text-[11px]">
                  <span className="text-emerald-400">Target: {kpi.target}</span>
                  <span className="text-red-400">Alert: {kpi.alert_threshold}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {data.standardization && data.standardization.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Standardization</p>
          <ul className="space-y-1">
            {data.standardization.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-white/75">
                <CheckCircle className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0 mt-0.5" />
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function ExecutiveSummaryPanel({ data }: { data: DmaicReport['executive_summary'] }) {
  return (
    <div className="space-y-4">
      {data.summary && (
        <p className="text-sm text-white/85 leading-relaxed bg-white/5 rounded-lg p-4 border border-white/5 italic">
          {data.summary}
        </p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Financial Impact */}
        {data.financial_impact && data.financial_impact.length > 0 && (
          <div>
            <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">
              <DollarSign className="inline h-3 w-3 mr-1" />Financial Impact
            </p>
            <ul className="space-y-2">
              {data.financial_impact.map((fi, i) => (
                <li key={i} className="flex items-start justify-between gap-2 p-2 bg-white/5 rounded border border-white/5">
                  <span className="text-xs text-white/70">{fi.description}</span>
                  {fi.amount != null && (
                    <span className={`text-sm font-bold flex-shrink-0 ${FIN_TYPE_COLOR[fi.type ?? 'saving'] ?? 'text-white'}`}>
                      {fi.unit ?? '$'}{fi.amount.toLocaleString()}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Key KPIs */}
        {data.key_kpis && data.key_kpis.length > 0 && (
          <div>
            <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Key KPIs</p>
            <ul className="space-y-2">
              {data.key_kpis.map((kpi, i) => (
                <li key={i} className="p-2 bg-white/5 rounded border border-white/5 text-xs">
                  <div className="font-semibold text-white/85 mb-0.5">{kpi.name}</div>
                  <div className="flex gap-2 text-white/50">
                    <span>Base: {kpi.baseline}</span>
                    <span>→</span>
                    <span className="text-emerald-400">{kpi.current_or_target}</span>
                  </div>
                  {kpi.improvement && (
                    <div className="text-emerald-400 font-semibold mt-0.5">{kpi.improvement}</div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Top Risks */}
      {data.top_risks && data.top_risks.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Top Risks</p>
          <ul className="space-y-1">
            {data.top_risks.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-red-300 p-1.5 bg-red-500/5 border-l-2 border-red-500/30 rounded-r">
                <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {data.recommendations && data.recommendations.length > 0 && (
        <div>
          <p className="text-[10px] text-white/40 uppercase tracking-widest font-semibold mb-2">Recommendations</p>
          <ul className="space-y-1.5">
            {data.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-white/80">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 text-[10px] font-bold flex items-center justify-center mt-0.5">
                  {i + 1}
                </span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

const DmaicCompilerPanel: React.FC<DmaicCompilerPanelProps> = ({ dmaicReport }) => {
  const [activePhase, setActivePhase] = useState<string>('executive_summary')

  const conf = dmaicReport.compilation_confidence ?? 0
  const confColor = conf >= 0.7 ? 'text-emerald-400' : conf >= 0.4 ? 'text-amber-400' : 'text-red-400'

  return (
    <div className="space-y-4">
      {/* Header card */}
      <Card className="bg-slate-900/60 border-slate-700/50 backdrop-blur-sm">
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="flex items-center gap-2 text-white text-base">
              <FileText className="h-5 w-5 text-violet-400" />
              Compiled DMAIC Report
            </CardTitle>
            <div className="flex items-center gap-2 flex-wrap">
              {dmaicReport.doc_type && (
                <Badge className="bg-slate-700/60 text-slate-300 border-slate-600/40 text-xs">
                  {dmaicReport.doc_type}
                </Badge>
              )}
              {dmaicReport.signal_flags && (
                <>
                  {dmaicReport.signal_flags.has_financials && (
                    <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-xs">
                      <DollarSign className="h-3 w-3 mr-1" />Financial data
                    </Badge>
                  )}
                  {dmaicReport.signal_flags.has_kpis && (
                    <Badge className="bg-cyan-500/20 text-cyan-400 border-cyan-500/30 text-xs">
                      <BarChart3 className="h-3 w-3 mr-1" />KPI data
                    </Badge>
                  )}
                  {!dmaicReport.signal_flags.has_control_data && (
                    <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30 text-xs">
                      <AlertTriangle className="h-3 w-3 mr-1" />No control data
                    </Badge>
                  )}
                </>
              )}
              <span className={`text-xs font-semibold ${confColor}`}>
                {Math.round(conf * 100)}% compiled confidence
              </span>
            </div>
          </div>
          <p className="text-xs text-white/40 mt-1">
            Strict Six Sigma structure reconstructed from all section analyses and phase syntheses
          </p>
        </CardHeader>
      </Card>

      {/* Phase tabs */}
      <div className="flex flex-wrap gap-2">
        {/* Executive Summary tab */}
        <button
          onClick={() => setActivePhase('executive_summary')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all
            ${activePhase === 'executive_summary'
              ? 'bg-violet-500/20 text-violet-300 border border-violet-500/40'
              : 'text-white/50 hover:text-white border border-transparent hover:bg-white/5'}`}
        >
          <FileText className="h-3.5 w-3.5" />
          Summary
        </button>

        {PHASES.map(ph => {
          const Icon = ph.icon
          const isActive = activePhase === ph.key
          return (
            <button
              key={ph.key}
              onClick={() => setActivePhase(ph.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all
                ${isActive
                  ? `${ph.headerBg} ${ph.iconColor} ${ph.borderColor} border`
                  : 'text-white/50 hover:text-white border border-transparent hover:bg-white/5'}`}
            >
              <Icon className="h-3.5 w-3.5" />
              {ph.label}
            </button>
          )
        })}
      </div>

      {/* Active phase content */}
      <Card className="bg-slate-800/50 border-slate-700/40 backdrop-blur-sm">
        <CardContent className="p-5">
          {activePhase === 'executive_summary' && (
            <ExecutiveSummaryPanel data={dmaicReport.executive_summary} />
          )}
          {activePhase === 'define' && <DefinePanel data={dmaicReport.define} />}
          {activePhase === 'measure' && <MeasurePanel data={dmaicReport.measure} />}
          {activePhase === 'analyze' && <AnalyzePanel data={dmaicReport.analyze} />}
          {activePhase === 'improve' && <ImprovePanel data={dmaicReport.improve} />}
          {activePhase === 'control' && <ControlPanel data={dmaicReport.control} />}
        </CardContent>
      </Card>

      {/* Gaps */}
      {dmaicReport.gaps && dmaicReport.gaps.length > 0 && (
        <Card className="bg-amber-500/5 border-amber-500/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-amber-400 mb-2">
              <AlertTriangle className="h-3.5 w-3.5" />
              Gap Analysis ({dmaicReport.gaps.length} gaps detected)
            </div>
            <ul className="space-y-1">
              {dmaicReport.gaps.map((gap, i) => (
                <li key={i} className="text-xs text-amber-200/70 flex items-start gap-1.5">
                  <span className="text-amber-400 flex-shrink-0">•</span>
                  {gap}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default DmaicCompilerPanel
