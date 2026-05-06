import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Database, BarChart2, AlertTriangle, TrendingUp, Shield, CheckCircle, Zap, GitBranch, Target, Activity, Cpu } from 'lucide-react';
import type { Optimization, DecisionConfidenceIndex, ActionManagement, ClosedLoopLearning, IntegrationMapping, DomainKPI, FailureMode } from '../types/dashboard';

// ─── DCI Gauge ───────────────────────────────────────────────────────────────

function DCIGauge({ score }: { score: number }) {
  const clamped = Math.min(100, Math.max(0, score));
  const color =
    clamped >= 75 ? '#10b981' :  // green
    clamped >= 50 ? '#f59e0b' :  // amber
    clamped >= 25 ? '#f97316' :  // orange
    '#ef4444';                   // red

  const label =
    clamped >= 75 ? 'High' :
    clamped >= 50 ? 'Moderate' :
    clamped >= 25 ? 'Low' : 'Very Low';

  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const dash = (clamped / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={radius} fill="none" stroke="#1e293b" strokeWidth="6" />
        <circle
          cx="36" cy="36" r={radius}
          fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
          transform="rotate(-90 36 36)"
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
        <text x="36" y="40" textAnchor="middle" fontSize="16" fontWeight="700" fill={color}>{clamped}</text>
      </svg>
      <span className="text-xs font-semibold" style={{ color }}>{label} Confidence</span>
    </div>
  );
}

// ─── DCI Pillar Bar ───────────────────────────────────────────────────────────

function DCIPillar({ label, text }: { label: string; text: string }) {
  const scoreMatch = text.match(/(\d+)\s*\/?\s*25/);
  const score = scoreMatch ? parseInt(scoreMatch[1]) : null;
  const pct = score !== null ? (score / 25) * 100 : 50;
  const color = pct >= 75 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        {score !== null && <span className="font-semibold" style={{ color }}>{score}/25</span>}
      </div>
      <div className="rounded-full overflow-hidden" style={{ height: 5, background: '#1e293b' }}>
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
      </div>
      <p className="text-xs text-slate-500 leading-relaxed">{text}</p>
    </div>
  );
}

// ─── Impact Badge ─────────────────────────────────────────────────────────────

function ImpactBadge({ impact }: { impact: string }) {
  const lower = impact.toLowerCase();
  const cfg =
    lower === 'high'   ? { bg: 'bg-red-500/15',    text: 'text-red-400',    label: 'High Impact' } :
    lower === 'medium' ? { bg: 'bg-amber-500/15',  text: 'text-amber-400',  label: 'Medium Impact' } :
                         { bg: 'bg-slate-500/15',  text: 'text-slate-400',  label: 'Low Impact' };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
      {cfg.label}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const lower = priority.toLowerCase();
  const cfg =
    lower === 'high'   ? { bg: 'bg-purple-500/15', text: 'text-purple-400', label: '↑ High Priority' } :
    lower === 'medium' ? { bg: 'bg-blue-500/15',   text: 'text-blue-400',   label: '→ Medium Priority' } :
                         { bg: 'bg-slate-500/15',  text: 'text-slate-400',  label: '↓ Low Priority' };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
      {cfg.label}
    </span>
  );
}

// ─── Main Card ────────────────────────────────────────────────────────────────

interface DCIRecommendationCardProps {
  recommendation: Optimization;
  index: number;
}

export default function DCIRecommendationCard({ recommendation: rec, index }: DCIRecommendationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const dci = rec.decision_confidence_index;
  const traceability = rec.decision_traceability;
  const benchmarking = rec.industry_benchmarking;
  const limitations = rec.assumptions_limitations || [];
  const actionMgmt: ActionManagement | undefined = rec.action_management as ActionManagement | undefined;
  const execPlan: string[] = rec.execution_plan || [];
  const closedLoop: ClosedLoopLearning | undefined = rec.closed_loop_learning as ClosedLoopLearning | undefined;
  const integration: IntegrationMapping | undefined = rec.integration_mapping as IntegrationMapping | undefined;
  const domainKpis: DomainKPI[] = rec.domain_kpis || [];
  const failureModes: FailureMode[] = rec.failure_modes || [];
  const hasDCI = !!(dci || traceability || benchmarking || limitations.length > 0 ||
    actionMgmt || execPlan.length > 0 || closedLoop || integration || domainKpis.length > 0 || failureModes.length > 0);

  const categoryColors: Record<string, string> = {
    cost:        '#10b981',
    efficiency:  '#06b6d4',
    performance: '#8b5cf6',
    risk:        '#ef4444',
    quality:     '#f59e0b',
  };
  const catColor = categoryColors[rec.category?.toLowerCase() || ''] || '#64748b';

  return (
    <div className="rounded-xl border overflow-hidden" style={{ borderColor: '#1e293b', background: '#0f172a' }}>
      {/* Header */}
      <div className="px-5 py-4 flex items-start gap-4">
        {/* Index + Category accent */}
        <div className="flex-shrink-0 flex flex-col items-center gap-1">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-white"
               style={{ background: catColor }}>
            {index + 1}
          </div>
          <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: catColor }}>
            {rec.category || 'N/A'}
          </span>
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-white leading-snug mb-2">{rec.title}</h3>
          <p className="text-xs text-slate-400 leading-relaxed mb-3">{rec.description}</p>
          <div className="flex flex-wrap gap-2 items-center">
            <ImpactBadge impact={rec.impact || 'medium'} />
            <PriorityBadge priority={rec.priority || 'medium'} />
            {rec.use_case && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/15 text-indigo-400">
                <Cpu size={9} />{rec.use_case}
              </span>
            )}
            {rec.savings?.value !== undefined && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-green-500/15 text-green-400">
                {rec.savings.unit || '$'}{rec.savings.value.toLocaleString()} {rec.savings.timeframe || 'annually'}
              </span>
            )}
            {rec.roi !== undefined && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/15 text-cyan-400">
                ROI: {rec.roi}%
              </span>
            )}
          </div>
        </div>

        {/* DCI Score */}
        {dci && <DCIGauge score={typeof dci.score === 'number' ? dci.score : parseInt(String(dci.score) || '0')} />}
      </div>

      {/* DCI Expand Toggle */}
      {hasDCI && (
        <>
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between px-5 py-2 text-xs font-semibold text-slate-400 hover:text-cyan-400 transition-colors"
            style={{ borderTop: '1px solid #1e293b', background: '#0b1120' }}
          >
            <span className="flex items-center gap-1.5">
              <Shield size={12} />
              Decision Intelligence Audit Trail
            </span>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {expanded && (
            <div className="px-5 py-4 grid gap-5" style={{ borderTop: '1px solid #1e293b', background: '#080e1a' }}>

              {/* DCI Pillars */}
              {dci && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-3">
                    <BarChart2 size={12} className="text-cyan-400" />
                    Decision Confidence Index — {typeof dci.score === 'number' ? dci.score : dci.score}/100
                  </h4>
                  <div className="grid gap-3">
                    {dci.data_completeness && <DCIPillar label="Data Completeness" text={dci.data_completeness} />}
                    {dci.model_confidence   && <DCIPillar label="Model Confidence"   text={dci.model_confidence} />}
                    {dci.historical_accuracy&& <DCIPillar label="Historical Accuracy" text={dci.historical_accuracy} />}
                    {dci.variability        && <DCIPillar label="Data Variability"    text={dci.variability} />}
                  </div>
                  {dci.explanation && (
                    <p className="mt-3 text-xs text-slate-500 leading-relaxed italic">{dci.explanation}</p>
                  )}
                </div>
              )}

              {/* Decision Traceability */}
              {traceability && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-3">
                    <Database size={12} className="text-purple-400" />
                    Decision Traceability Layer
                  </h4>
                  {traceability.data_sources?.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Data Sources</p>
                      <ul className="space-y-1">
                        {traceability.data_sources.map((s, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
                            <span className="text-purple-400 mt-0.5 flex-shrink-0">•</span>{s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {traceability.analytical_methods?.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Analytical Methods</p>
                      <ul className="space-y-1">
                        {traceability.analytical_methods.map((m, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
                            <span className="text-cyan-400 mt-0.5 flex-shrink-0">≈</span>{m}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {traceability.supporting_evidence?.length > 0 && (
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Supporting Evidence</p>
                      <ul className="space-y-1">
                        {traceability.supporting_evidence.map((e, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-green-400">
                            <CheckCircle size={10} className="mt-0.5 flex-shrink-0" />{e}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Industry Benchmarking */}
              {benchmarking && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-3">
                    <TrendingUp size={12} className="text-amber-400" />
                    Industry Benchmarking
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    {benchmarking.median_comparison && (
                      <div className="rounded-lg p-3" style={{ background: '#1e293b' }}>
                        <p className="text-xs text-slate-500 mb-1">vs Industry Median</p>
                        <p className="text-xs text-slate-200">{benchmarking.median_comparison}</p>
                      </div>
                    )}
                    {benchmarking.top_quartile_comparison && (
                      <div className="rounded-lg p-3" style={{ background: '#1e293b' }}>
                        <p className="text-xs text-slate-500 mb-1">vs P75/P90 Quartile</p>
                        <p className="text-xs text-slate-200">{benchmarking.top_quartile_comparison}</p>
                      </div>
                    )}
                    {benchmarking.peer_comparison && (
                      <div className="rounded-lg p-3" style={{ background: '#1e293b' }}>
                        <p className="text-xs text-slate-500 mb-1">Peer Comparison</p>
                        <p className="text-xs text-slate-200">{benchmarking.peer_comparison}</p>
                      </div>
                    )}
                    {benchmarking.performance_gap && (
                      <div className="rounded-lg p-3" style={{ background: '#1e2940', borderLeft: '3px solid #f59e0b' }}>
                        <p className="text-xs text-slate-500 mb-1">Performance Gap</p>
                        <p className="text-xs text-amber-400 font-semibold">{benchmarking.performance_gap}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Assumptions & Limitations */}
              {limitations.length > 0 && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-3">
                    <AlertTriangle size={12} className="text-amber-400" />
                    Assumptions & Limitations
                  </h4>
                  <ul className="space-y-1.5">
                    {limitations.map((lim, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-amber-400/80">
                        <AlertTriangle size={10} className="mt-0.5 flex-shrink-0" />{lim}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* ── Action Management ───────────────────────────────── */}
              {actionMgmt && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-3">
                    <Target size={12} className="text-green-400" />
                    Action Management
                  </h4>
                  <div className="rounded-lg p-4 grid grid-cols-2 gap-3" style={{ background: '#1e293b' }}>
                    <div className="col-span-2">
                      <p className="text-xs text-slate-500 uppercase tracking-wider mb-0.5">Task</p>
                      <p className="text-xs text-white font-semibold">{actionMgmt.task_title}</p>
                      {actionMgmt.description && <p className="text-xs text-slate-400 mt-1">{actionMgmt.description}</p>}
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wider mb-0.5">Owner</p>
                      <p className="text-xs text-cyan-400">{actionMgmt.owner}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wider mb-0.5">Deadline</p>
                      <p className="text-xs text-orange-400 font-semibold">{actionMgmt.deadline}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wider mb-0.5">KPI</p>
                      <p className="text-xs text-slate-300">{actionMgmt.kpi}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wider mb-0.5">Target</p>
                      <p className="text-xs text-green-400 font-semibold">{actionMgmt.target_value}</p>
                    </div>
                    <div className="col-span-2 flex gap-2 items-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                        actionMgmt.priority === 'high' ? 'bg-red-500/20 text-red-400' :
                        actionMgmt.priority === 'medium' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-slate-500/20 text-slate-400'
                      }`}>{actionMgmt.priority?.toUpperCase()} PRIORITY</span>
                      <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-400">
                        {actionMgmt.status || 'Open'}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Execution Plan ──────────────────────────────────── */}
              {execPlan.length > 0 && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-3">
                    <GitBranch size={12} className="text-purple-400" />
                    Execution Plan ({execPlan.length} steps)
                  </h4>
                  <ol className="space-y-2">
                    {execPlan.map((step, i) => (
                      <li key={i} className="flex items-start gap-3">
                        <span className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-white"
                              style={{ background: '#7c3aed', fontSize: 10 }}>
                          {i + 1}
                        </span>
                        <p className="text-xs text-slate-400 leading-relaxed flex-1">{step}</p>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* ── Closed-Loop Learning ────────────────────────────── */}
              {closedLoop && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-3">
                    <Activity size={12} className="text-cyan-400" />
                    Closed-Loop Learning
                  </h4>
                  <div className="grid gap-2">
                    <div className="rounded-lg p-3" style={{ background: '#1e293b', borderLeft: '3px solid #06b6d4' }}>
                      <p className="text-xs text-slate-500 mb-1">Predicted Impact</p>
                      <p className="text-xs text-cyan-400 font-semibold">{closedLoop.predicted_impact}</p>
                    </div>
                    {closedLoop.actual_vs_predicted && (
                      <div className="rounded-lg p-3 grid grid-cols-2 gap-3" style={{ background: '#1e293b' }}>
                        <div>
                          <p className="text-xs text-slate-500 mb-1">Predicted</p>
                          <p className="text-xs text-slate-300">{closedLoop.actual_vs_predicted.predicted}</p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500 mb-1">Actual</p>
                          <p className="text-xs text-slate-400 italic">{closedLoop.actual_vs_predicted.actual}</p>
                        </div>
                      </div>
                    )}
                    {closedLoop.measurement_plan && (
                      <div className="rounded-lg p-3" style={{ background: '#1a2234' }}>
                        <p className="text-xs text-slate-500 mb-1">Measurement Plan</p>
                        <p className="text-xs text-slate-300">{closedLoop.measurement_plan}</p>
                      </div>
                    )}
                    {closedLoop.learning_loop && (
                      <div className="rounded-lg p-3" style={{ background: '#1a2234' }}>
                        <p className="text-xs text-slate-500 mb-1">Learning Loop</p>
                        <p className="text-xs text-slate-300">{closedLoop.learning_loop}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── System Integration Mapping ──────────────────────── */}
              {integration && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-3">
                    <Zap size={12} className="text-yellow-400" />
                    System Integration Mapping
                  </h4>
                  <div className="grid grid-cols-2 gap-2">
                    {integration.erp && (
                      <div className="rounded-lg p-3" style={{ background: '#1e293b' }}>
                        <p className="text-xs font-semibold text-blue-400 mb-1">ERP / SAP</p>
                        <p className="text-xs text-slate-400">{integration.erp}</p>
                      </div>
                    )}
                    {integration.scada && (
                      <div className="rounded-lg p-3" style={{ background: '#1e293b' }}>
                        <p className="text-xs font-semibold text-green-400 mb-1">SCADA / IoT</p>
                        <p className="text-xs text-slate-400">{integration.scada}</p>
                      </div>
                    )}
                    {integration.production_db && (
                      <div className="rounded-lg p-3 col-span-2" style={{ background: '#1a2234' }}>
                        <p className="text-xs font-semibold text-purple-400 mb-1">Production DB</p>
                        <p className="text-xs text-slate-400 font-mono leading-relaxed">{integration.production_db}</p>
                      </div>
                    )}
                    {integration.excel && (
                      <div className="rounded-lg p-3 col-span-2" style={{ background: '#1a2234' }}>
                        <p className="text-xs font-semibold text-emerald-400 mb-1">Excel / Reporting</p>
                        <p className="text-xs text-slate-400">{integration.excel}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── Domain KPI Targets ──────────────────────────────── */}
              {domainKpis.length > 0 && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-3">
                    <TrendingUp size={12} className="text-emerald-400" />
                    Domain KPI Targets
                  </h4>
                  <div className="rounded-lg overflow-hidden" style={{ border: '1px solid #1e293b' }}>
                    <div className="grid grid-cols-4 px-3 py-1.5 text-xs text-slate-500 uppercase tracking-wider"
                         style={{ background: '#0f172a' }}>
                      <span>KPI</span><span>Current</span><span>Target</span><span>Direction</span>
                    </div>
                    {domainKpis.map((kpi, i) => (
                      <div key={i} className="grid grid-cols-4 px-3 py-2 text-xs items-center"
                           style={{ background: i % 2 === 0 ? '#1a2234' : '#1e293b' }}>
                        <span className="text-slate-300 font-semibold truncate pr-2">{kpi.name}</span>
                        <span className="text-slate-400">{kpi.current}</span>
                        <span className="text-green-400 font-semibold">{kpi.target}</span>
                        <span className={kpi.direction === 'increase' ? 'text-green-400' : 'text-red-400'}>
                          {kpi.direction === 'increase' ? '↑ Increase' : '↓ Decrease'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── Failure Mode Intelligence ───────────────────────── */}
              {failureModes.length > 0 && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-3">
                    <AlertTriangle size={12} className="text-red-400" />
                    Failure Mode Intelligence (top {failureModes.length})
                  </h4>
                  <div className="space-y-2">
                    {failureModes.map((fm, i) => {
                      const pct = Math.round((fm.confidence || 0) * 100);
                      const color = pct >= 70 ? '#ef4444' : pct >= 40 ? '#f97316' : '#f59e0b';
                      return (
                        <div key={i}>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="text-slate-400 flex-1 pr-3">{fm.cause}</span>
                            <span className="font-semibold flex-shrink-0" style={{ color }}>{pct}%</span>
                          </div>
                          <div className="rounded-full overflow-hidden" style={{ height: 4, background: '#1e293b' }}>
                            <div className="h-full rounded-full transition-all duration-500"
                                 style={{ width: `${pct}%`, background: color }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

            </div>
          )}
        </>
      )}
    </div>
  );
}
