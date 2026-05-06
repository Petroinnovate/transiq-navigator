import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Shield,
  AlertTriangle,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  XCircle,
  Target,
  BarChart3,
  DollarSign,
  Link,
} from 'lucide-react'

interface QualityBreakdown {
  define: number
  measure: number
  analyze: number
  improve: number
  control: number
  data_strength: number
  financial_impact: number
  consistency: number
}

interface QualityScore {
  overall_score: number
  rule_score: number
  rating: string
  rating_color: string
  breakdown: QualityBreakdown
  gaps: string[]
  llm_feedback: string
  reprocess_phases: string[]
  max_score: number
}

interface QualityScoreCardProps {
  qualityScore: QualityScore
}

const DIMENSION_META: {
  key: keyof QualityBreakdown
  label: string
  icon: React.ElementType
  description: string
  color: string
}[] = [
  { key: 'define',          label: 'Define',           icon: Target,    description: 'Problem statement, scope, business context',           color: 'blue'   },
  { key: 'measure',         label: 'Measure',          icon: BarChart3, description: 'Baseline KPIs, data collection, process capability',   color: 'green'  },
  { key: 'analyze',         label: 'Analyze',          icon: TrendingUp,description: 'Root causes, validation, statistical evidence',        color: 'yellow' },
  { key: 'improve',         label: 'Improve',          icon: CheckCircle,description: 'Solutions linked to causes, quantified impact, ROI',  color: 'purple' },
  { key: 'control',         label: 'Control',          icon: Shield,    description: 'Monitoring KPIs, control plan, sustainability',        color: 'cyan'   },
  { key: 'data_strength',   label: 'Data Strength',    icon: BarChart3, description: 'Numeric density, financial amounts, confidence',       color: 'teal'   },
  { key: 'financial_impact',label: 'Financial Impact', icon: DollarSign,description: 'Cost savings, ROI, quantified benefits',               color: 'emerald'},
  { key: 'consistency',     label: 'Cross-Phase Logic',icon: Link,      description: 'Solutions map to causes, control tracks improvements', color: 'violet' },
]

const COLOR_MAP: Record<string, { bar: string; text: string; badge: string }> = {
  blue:   { bar: 'bg-blue-400',    text: 'text-blue-400',    badge: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  green:  { bar: 'bg-emerald-400', text: 'text-emerald-400', badge: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
  yellow: { bar: 'bg-yellow-400',  text: 'text-yellow-400',  badge: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  purple: { bar: 'bg-purple-400',  text: 'text-purple-400',  badge: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  cyan:   { bar: 'bg-cyan-400',    text: 'text-cyan-400',    badge: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
  teal:   { bar: 'bg-teal-400',    text: 'text-teal-400',    badge: 'bg-teal-500/20 text-teal-400 border-teal-500/30' },
  emerald:{ bar: 'bg-emerald-500', text: 'text-emerald-400', badge: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
  violet: { bar: 'bg-violet-400',  text: 'text-violet-400',  badge: 'bg-violet-500/20 text-violet-400 border-violet-500/30' },
}

const RATING_STYLE: Record<string, { ring: string; text: string; badge: string; bg: string }> = {
  'Black Belt':    { ring: 'ring-emerald-500/50', text: 'text-emerald-400', badge: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40', bg: 'bg-emerald-500/8' },
  'Green Belt':    { ring: 'ring-teal-500/50',    text: 'text-teal-400',    badge: 'bg-teal-500/20 text-teal-400 border-teal-500/40',         bg: 'bg-teal-500/8'    },
  'Acceptable':    { ring: 'ring-amber-500/50',   text: 'text-amber-400',   badge: 'bg-amber-500/20 text-amber-400 border-amber-500/40',       bg: 'bg-amber-500/8'   },
  'Weak Analysis': { ring: 'ring-red-500/50',     text: 'text-red-400',     badge: 'bg-red-500/20 text-red-400 border-red-500/40',             bg: 'bg-red-500/8'     },
}

function ScoreBar({ value, max = 5, color }: { value: number; max?: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100)
  const barStyle = COLOR_MAP[color]?.bar ?? 'bg-cyan-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-slate-700/60 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barStyle}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-white/60 w-8 text-right">
        {value.toFixed(1)}<span className="text-white/30">/5</span>
      </span>
    </div>
  )
}

// Circular progress ring for the overall score
function ScoreRing({ score, rating }: { score: number; rating: string }) {
  const style = RATING_STYLE[rating] ?? RATING_STYLE['Acceptable']
  const r = 44
  const circ = 2 * Math.PI * r
  const dash = (score / 100) * circ
  return (
    <div className="relative w-28 h-28 flex items-center justify-center">
      <svg className="absolute inset-0 rotate-[-90deg]" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="8" />
        <circle
          cx="50" cy="50" r={r} fill="none"
          strokeWidth="8" strokeLinecap="round"
          stroke={rating === 'Black Belt' ? '#34d399' : rating === 'Green Belt' ? '#2dd4bf' : rating === 'Acceptable' ? '#fbbf24' : '#f87171'}
          strokeDasharray={`${dash} ${circ - dash}`}
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      <div className="text-center">
        <div className={`text-2xl font-bold ${style.text}`}>{Math.round(score)}</div>
        <div className="text-[10px] text-white/40 uppercase tracking-widest">/ 100</div>
      </div>
    </div>
  )
}

const QualityScoreCard: React.FC<QualityScoreCardProps> = ({ qualityScore }) => {
  const [showBreakdown, setShowBreakdown] = useState(false)
  const style = RATING_STYLE[qualityScore.rating] ?? RATING_STYLE['Acceptable']

  const totalRaw = Object.values(qualityScore.breakdown).reduce((s, v) => s + v, 0)

  return (
    <Card className={`border-2 ${style.ring} bg-slate-900/60 backdrop-blur-sm ring-1`}>
      <CardHeader className={`pb-3 rounded-t-lg ${style.bg}`}>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-white text-base">
            <Shield className="h-5 w-5 text-cyan-400" />
            Six Sigma Quality Score
          </CardTitle>
          <Badge className={`${style.badge} text-xs font-bold`}>
            {qualityScore.rating}
          </Badge>
        </div>
        <p className="text-xs text-white/40 mt-1">
          Hybrid scoring: 70% rule-based + 30% LLM evaluator across 8 dimensions
        </p>
      </CardHeader>

      <CardContent className="pt-5 space-y-5">
        {/* Hero: ring + score summary */}
        <div className="flex items-center gap-6">
          <ScoreRing score={qualityScore.overall_score} rating={qualityScore.rating} />
          <div className="flex-1 space-y-2">
            <div className="flex items-baseline gap-2">
              <span className={`text-3xl font-bold ${style.text}`}>
                {qualityScore.overall_score.toFixed(1)}%
              </span>
              <span className="text-white/40 text-sm">overall quality</span>
            </div>
            <div className="text-xs text-white/40">
              Rule score: {qualityScore.rule_score.toFixed(1)}% &nbsp;·&nbsp;
              Raw: {totalRaw.toFixed(1)} / {qualityScore.max_score}
            </div>
            {qualityScore.llm_feedback && (
              <p className="text-xs text-white/60 italic leading-relaxed border-l-2 border-cyan-500/30 pl-3">
                {qualityScore.llm_feedback}
              </p>
            )}
          </div>
        </div>

        {/* Dimension breakdown */}
        <div>
          <button
            onClick={() => setShowBreakdown(v => !v)}
            className="flex items-center gap-2 text-xs font-semibold text-white/60 hover:text-white transition-colors mb-3"
          >
            {showBreakdown ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            {showBreakdown ? 'Hide' : 'Show'} dimension breakdown
          </button>

          {showBreakdown && (
            <div className="space-y-3">
              {DIMENSION_META.map(({ key, label, icon: Icon, description, color }) => {
                const val = qualityScore.breakdown[key] ?? 0
                const colors = COLOR_MAP[color]
                return (
                  <div key={key}>
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className={`h-3.5 w-3.5 ${colors.text}`} />
                      <span className="text-xs font-semibold text-white/80">{label}</span>
                      <span className="text-[10px] text-white/30 ml-auto">{description}</span>
                    </div>
                    <ScoreBar value={val} color={color} />
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Gaps */}
        {qualityScore.gaps.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-amber-400">
              <AlertTriangle className="h-3.5 w-3.5" />
              Quality Gaps Detected ({qualityScore.gaps.length})
            </div>
            <ul className="space-y-1.5">
              {qualityScore.gaps.map((gap, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-xs text-white/70 p-2
                             bg-amber-500/5 border-l-2 border-amber-500/30 rounded-r"
                >
                  <XCircle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                  {gap}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Reprocess suggestion */}
        {qualityScore.reprocess_phases.length > 0 && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/8 border border-red-500/20 text-xs">
            <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
            <span className="text-red-300">
              Weak phases detected — consider re-uploading for deeper analysis:{' '}
              <span className="font-bold uppercase">
                {qualityScore.reprocess_phases.join(', ')}
              </span>
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default QualityScoreCard
