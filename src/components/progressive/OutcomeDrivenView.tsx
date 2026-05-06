/**
 * OutcomeDrivenView — Outcome Intelligence Layer
 * ================================================
 * Renders Agent 7 (OutcomeIntelligenceAgent) output.
 * Closes the loop: Decision → KPI → Financial Impact → Tracking → Actual vs Expected
 *
 * Designed for: Executives ($ impact), Ops (tracking), Auditors (traceability)
 */
import React, { useState } from 'react';
import {
  TrendingUp, AlertTriangle, Target, ChevronDown, ChevronUp,
  BarChart2, Clock, Users, Database, CheckCircle2, Circle,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

// ── Types matching OutcomeIntelligenceAgent JSON schema ─────────────────────

interface ExpectedOutcome {
  kpi: string;
  current: string;
  target: string;
  timeline: string;
}

interface BusinessImpact {
  type: 'revenue_gain' | 'cost_saving' | 'loss_avoidance' | string;
  value: string;
  confidence: 'High' | 'Medium' | 'Low';
}

interface OutcomeAction {
  task: string;
  owner: string;
  kpi_link: string;
  deadline: string;
}

interface TrackingFramework {
  metrics: string[];
  data_source: string[];
  frequency: string;
  owner: string;
}

interface ActualVsExpected {
  expected: string;
  actual: string;
  variance: string;
}

interface OutcomeConfidenceScore {
  score: number;
  explanation: string;
}

interface BenchmarkImpact {
  current_position: string;
  target_position: string;
  improvement: string;
}

interface OutcomeDecision {
  decision: string;
  expected_outcome: ExpectedOutcome;
  business_impact: BusinessImpact;
  actions: OutcomeAction[];
  tracking_framework: TrackingFramework;
  cost_of_inaction: string;
  actual_vs_expected: ActualVsExpected;
  outcome_confidence_score: OutcomeConfidenceScore;
  benchmark_impact: BenchmarkImpact;
}

interface PortfolioSummary {
  total_value_at_stake: string;
  decisions_count: number;
  highest_confidence_decision: string;
  fastest_win: string;
}

interface OutcomeDrivenViewProps {
  decisions: OutcomeDecision[];
  portfolio: PortfolioSummary;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const IMPACT_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  revenue_gain:   { label: 'Revenue Gain',   color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  cost_saving:    { label: 'Cost Saving',    color: 'text-cyan-400',    bg: 'bg-cyan-500/10',    border: 'border-cyan-500/30'    },
  loss_avoidance: { label: 'Loss Avoidance', color: 'text-amber-400',   bg: 'bg-amber-500/10',   border: 'border-amber-500/30'   },
};

const confidenceBadge = (c: string) => {
  if (c === 'High')   return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
  if (c === 'Medium') return 'bg-amber-500/10   text-amber-400   border-amber-500/30';
  return                     'bg-red-500/10     text-red-400     border-red-500/30';
};

const confidenceBarColor = (score: number) => {
  if (score >= 70) return 'bg-emerald-500';
  if (score >= 40) return 'bg-amber-500';
  return 'bg-red-500';
};

// ── Sub-components ───────────────────────────────────────────────────────────

const KpiDelta: React.FC<{ outcome: ExpectedOutcome }> = ({ outcome }) => (
  <div className="flex flex-wrap items-center gap-2 text-sm">
    <span className="font-medium text-slate-300">{outcome.kpi}</span>
    <span className="px-2 py-0.5 rounded bg-slate-700/60 text-slate-400 font-mono">{outcome.current}</span>
    <TrendingUp className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
    <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-mono font-semibold">{outcome.target}</span>
    <span className="flex items-center gap-1 text-slate-500 text-xs">
      <Clock className="h-3 w-3" /> {outcome.timeline}
    </span>
  </div>
);

const ActualVsExpectedRow: React.FC<{ avs: ActualVsExpected }> = ({ avs }) => {
  const isPending = !avs.actual || avs.actual === 'Pending';
  return (
    <div className="flex items-start gap-3 text-xs">
      {isPending ? (
        <Circle className="h-3.5 w-3.5 text-slate-500 mt-0.5 flex-shrink-0" />
      ) : (
        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
      )}
      <div>
        <span className="text-slate-400">Expected: </span>
        <span className="text-slate-300">{avs.expected}</span>
        <span className="mx-2 text-slate-600">·</span>
        <span className="text-slate-400">Actual: </span>
        <span className={isPending ? 'text-slate-500 italic' : 'text-emerald-400 font-medium'}>{avs.actual}</span>
        {avs.variance && avs.variance !== 'TBD' && (
          <>
            <span className="mx-2 text-slate-600">·</span>
            <span className="text-slate-400">Variance: </span>
            <span className="text-amber-400">{avs.variance}</span>
          </>
        )}
      </div>
    </div>
  );
};

// ── Decision Card ─────────────────────────────────────────────────────────────

const OutcomeCard: React.FC<{ item: OutcomeDecision; index: number }> = ({ item, index }) => {
  const [open, setOpen] = useState(index === 0);
  const impactMeta = IMPACT_META[item.business_impact?.type] ?? IMPACT_META['cost_saving'];
  const score = item.outcome_confidence_score?.score ?? 0;

  return (
    <div className="rounded-xl border border-slate-700/50 overflow-hidden">

      {/* ── Card header ── */}
      <button
        onClick={() => setOpen(p => !p)}
        className="w-full flex items-start justify-between gap-3 px-5 py-4 bg-slate-800/60 hover:bg-slate-800/90 transition-colors text-left"
      >
        <div className="flex items-start gap-3 min-w-0">
          <span className="text-[10px] font-bold text-slate-500 tabular-nums mt-0.5 flex-shrink-0">
            #{String(index + 1).padStart(2, '0')}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white leading-snug">{item.decision}</p>
            {item.expected_outcome && (
              <div className="mt-1.5">
                <KpiDelta outcome={item.expected_outcome} />
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {item.business_impact && (
            <div className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-semibold ${impactMeta.bg} ${impactMeta.border} ${impactMeta.color}`}>
              {impactMeta.label} · {item.business_impact.value}
            </div>
          )}
          {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
        </div>
      </button>

      {/* ── Card body ── */}
      {open && (
        <div className="divide-y divide-slate-700/40">

          {/* Business Impact (mobile fallback + confidence) */}
          <div className="px-5 py-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">Business Impact</p>
              {item.business_impact && (
                <div className="space-y-1.5">
                  <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold ${impactMeta.bg} ${impactMeta.border} ${impactMeta.color}`}>
                    {impactMeta.label} · {item.business_impact.value}
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">Confidence: </span>
                    <span className={`text-xs font-medium px-1.5 py-0.5 rounded border ${confidenceBadge(item.business_impact.confidence)}`}>
                      {item.business_impact.confidence}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Outcome Confidence Score */}
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">
                Outcome Confidence Score
              </p>
              <div className="flex items-center gap-3">
                <div className="text-2xl font-bold text-white tabular-nums">{score}</div>
                <div className="flex-1">
                  <div className="w-full bg-slate-700/50 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-2 rounded-full transition-all ${confidenceBarColor(score)}`}
                      style={{ width: `${score}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-slate-500 mt-1 leading-relaxed">
                    {item.outcome_confidence_score?.explanation}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Execution Actions */}
          {item.actions?.length > 0 && (
            <div className="px-5 py-4">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-3">Execution Plan</p>
              <div className="space-y-2">
                {item.actions.map((a, i) => (
                  <div key={i} className="flex items-start justify-between gap-3 text-xs py-1.5 border-b border-slate-700/30 last:border-0">
                    <span className="text-slate-300 leading-relaxed">{a.task}</span>
                    <div className="flex items-center gap-2 flex-shrink-0 text-slate-500">
                      <span className="flex items-center gap-1"><Users className="h-3 w-3" />{a.owner}</span>
                      <span>·</span>
                      <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{a.deadline}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tracking Framework */}
          {item.tracking_framework && (
            <div className="px-5 py-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">
                  <Database className="h-3 w-3 inline mr-1" />Data Source
                </p>
                <p className="text-xs text-slate-300">{item.tracking_framework.data_source?.join(' · ')}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">
                  <BarChart2 className="h-3 w-3 inline mr-1" />Frequency
                </p>
                <p className="text-xs text-slate-300">{item.tracking_framework.frequency}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">
                  <Users className="h-3 w-3 inline mr-1" />Owner
                </p>
                <p className="text-xs text-slate-300">{item.tracking_framework.owner}</p>
              </div>
            </div>
          )}

          {/* Cost of Inaction */}
          {item.cost_of_inaction && (
            <div className="px-5 py-3.5 flex items-start gap-2.5 bg-red-500/5 border-t border-red-500/20">
              <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-red-400 mb-0.5">Cost of Inaction</p>
                <p className="text-xs text-red-300/80 leading-relaxed">{item.cost_of_inaction}</p>
              </div>
            </div>
          )}

          {/* Actual vs Expected + Benchmark */}
          <div className="px-5 py-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {item.actual_vs_expected && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">Actual vs Expected</p>
                <ActualVsExpectedRow avs={item.actual_vs_expected} />
              </div>
            )}
            {item.benchmark_impact && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">
                  <TrendingUp className="h-3 w-3 inline mr-1" />Benchmark Movement
                </p>
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-2 py-0.5 rounded bg-slate-700/60 text-slate-400">{item.benchmark_impact.current_position}</span>
                  <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-semibold">{item.benchmark_impact.target_position}</span>
                </div>
                <p className="text-[10px] text-slate-500 mt-1.5 leading-relaxed">{item.benchmark_impact.improvement}</p>
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
};

// ── PLACEHOLDER_DECISIONS (shown before first analysis run) ─────────────────

const PLACEHOLDER: OutcomeDecision[] = [
  {
    decision: 'Upload a document and run analysis to generate outcome-driven decisions',
    expected_outcome: { kpi: 'Your KPI', current: '—', target: '—', timeline: '—' },
    business_impact:  { type: 'cost_saving', value: '$X', confidence: 'High' },
    actions: [{ task: 'Run the multi-agent pipeline to populate this view', owner: 'You', kpi_link: '—', deadline: 'Now' }],
    tracking_framework: { metrics: [], data_source: ['SCADA / ERP'], frequency: 'Weekly', owner: 'Ops Manager' },
    cost_of_inaction: 'No data yet — upload a document to quantify inaction cost.',
    actual_vs_expected: { expected: '—', actual: 'Pending', variance: 'TBD' },
    outcome_confidence_score: { score: 0, explanation: 'Awaiting analysis.' },
    benchmark_impact: { current_position: '—', target_position: '—', improvement: 'Run analysis to compare vs P50/P75 benchmarks.' },
  },
];

// ── Main Export ───────────────────────────────────────────────────────────────

const OutcomeDrivenView: React.FC<OutcomeDrivenViewProps> = ({ decisions, portfolio }) => {
  const items = decisions?.length ? decisions : PLACEHOLDER;
  const isLive = !!decisions?.length;

  return (
    <div className="space-y-5">

      {/* ── Portfolio Summary banner ─────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          {
            label: 'Total Value at Stake',
            value: portfolio?.total_value_at_stake || (isLive ? '$0' : '—'),
            color: 'text-emerald-400',
            icon: Target,
          },
          {
            label: 'Decisions Tracked',
            value: String(portfolio?.decisions_count || items.length),
            color: 'text-cyan-400',
            icon: BarChart2,
          },
          {
            label: 'Fastest Win',
            value: portfolio?.fastest_win || '—',
            color: 'text-amber-400',
            icon: Clock,
          },
          {
            label: 'Highest Confidence',
            value: portfolio?.highest_confidence_decision || '—',
            color: 'text-violet-400',
            icon: TrendingUp,
          },
        ].map(({ label, value, color, icon: Icon }) => (
          <div key={label} className="rounded-xl border border-slate-700/40 bg-slate-800/40 p-4">
            <div className="flex items-center gap-2 mb-1.5">
              <Icon className={`h-3.5 w-3.5 ${color}`} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{label}</span>
            </div>
            <p className={`text-sm font-bold leading-tight ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* ── Outcome cards ────────────────────────────────────────────── */}
      <div className="space-y-3">
        {items.map((item, i) => (
          <OutcomeCard key={i} item={item} index={i} />
        ))}
      </div>

    </div>
  );
};

export default OutcomeDrivenView;
