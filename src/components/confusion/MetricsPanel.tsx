import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle2, Info, TrendingUp, TrendingDown } from 'lucide-react';

interface PerClassMetric {
  class: string;
  precision: number;
  recall: number;
  f1_score: number;
  support: number;
}

interface RiskFlag {
  type: string;
  severity: string;
  message: string;
}

interface TopError {
  actual: string;
  predicted: string;
  count: number;
  pct_of_actual: number;
}

interface ThresholdAnalysis {
  optimal_threshold: number;
  best_f1: number;
  best_precision: number;
  best_recall: number;
  note: string;
}

interface MetricsPanelProps {
  metrics: {
    accuracy: number;
    precision_macro: number;
    recall_macro: number;
    f1_macro: number;
    precision_weighted: number;
    recall_weighted: number;
    f1_weighted: number;
  };
  perClassMetrics: PerClassMetric[];
  riskFlags: RiskFlag[];
  insights: string[];
  topErrors: TopError[];
  thresholdAnalysis?: ThresholdAnalysis | null;
  totalSamples: number;
}

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

const severityColor = (s: string) => {
  if (s === 'HIGH') return 'border-red-500/50 bg-red-900/20 text-red-300';
  if (s === 'MEDIUM') return 'border-amber-500/50 bg-amber-900/20 text-amber-300';
  return 'border-blue-500/50 bg-blue-900/20 text-blue-300';
};

const SummaryKPI = ({ label, value, color }: { label: string; value: string; color: string }) => (
  <div className="flex flex-col items-center justify-center rounded-xl border border-slate-700/40 bg-slate-800/50 p-4 text-center">
    <span className={`text-2xl font-bold ${color}`}>{value}</span>
    <span className="text-[11px] text-slate-400 mt-1 uppercase tracking-wider">{label}</span>
  </div>
);

const MetricsPanel: React.FC<MetricsPanelProps> = ({
  metrics,
  perClassMetrics,
  riskFlags,
  insights,
  topErrors,
  thresholdAnalysis,
  totalSamples,
}) => {
  const accColor =
    metrics.accuracy >= 0.9
      ? 'text-emerald-400'
      : metrics.accuracy >= 0.75
      ? 'text-amber-400'
      : 'text-red-400';

  const f1Color =
    metrics.f1_weighted >= 0.85
      ? 'text-emerald-400'
      : metrics.f1_weighted >= 0.70
      ? 'text-amber-400'
      : 'text-red-400';

  return (
    <div className="space-y-5">
      {/* ── KPI summary row ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryKPI label="Accuracy"   value={pct(metrics.accuracy)}       color={accColor} />
        <SummaryKPI label="F1 Weighted" value={pct(metrics.f1_weighted)}   color={f1Color} />
        <SummaryKPI label="Precision"  value={pct(metrics.precision_weighted)} color="text-sky-400" />
        <SummaryKPI label="Recall"     value={pct(metrics.recall_weighted)} color="text-violet-400" />
      </div>

      {/* ── Risk flags ── */}
      {riskFlags.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[11px] uppercase tracking-widest text-slate-500">Risk Alerts</h4>
          {riskFlags.map((flag, i) => (
            <div
              key={i}
              className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm ${severityColor(flag.severity)}`}
            >
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <span className="leading-snug">{flag.message}</span>
              <Badge variant="outline" className="ml-auto shrink-0 text-[10px] border-current">
                {flag.severity}
              </Badge>
            </div>
          ))}
        </div>
      )}

      {/* ── AI Insights ── */}
      {insights.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[11px] uppercase tracking-widest text-slate-500">Insights</h4>
          {insights.map((ins, i) => (
            <div key={i} className="flex items-start gap-2 rounded-lg border border-slate-700/40 bg-slate-800/40 px-3 py-2.5 text-sm text-slate-300">
              <Info className="h-4 w-4 mt-0.5 text-slate-500 shrink-0" />
              <span className="leading-snug">{ins}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Per-class metrics table ── */}
      {perClassMetrics.length > 0 && (
        <div>
          <h4 className="text-[11px] uppercase tracking-widest text-slate-500 mb-2">Per-Class Metrics</h4>
          <div className="rounded-lg border border-slate-700/40 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-800/70 text-slate-400 text-[11px] uppercase tracking-wider">
                  <th className="text-left px-3 py-2">Class</th>
                  <th className="text-right px-3 py-2">Precision</th>
                  <th className="text-right px-3 py-2">Recall</th>
                  <th className="text-right px-3 py-2">F1</th>
                  <th className="text-right px-3 py-2">Support</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40">
                {perClassMetrics.map((row, i) => (
                  <tr key={i} className="bg-slate-900/20 hover:bg-slate-800/40 transition-colors">
                    <td className="px-3 py-2 font-medium text-slate-200">{row.class}</td>
                    <td className="px-3 py-2 text-right text-slate-300">{pct(row.precision)}</td>
                    <td className={`px-3 py-2 text-right font-semibold ${row.recall < 0.70 ? 'text-red-400' : 'text-emerald-400'}`}>
                      {pct(row.recall)}
                    </td>
                    <td className="px-3 py-2 text-right text-slate-300">{pct(row.f1_score)}</td>
                    <td className="px-3 py-2 text-right text-slate-500">{row.support}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Top confusion pairs ── */}
      {topErrors.length > 0 && (
        <div>
          <h4 className="text-[11px] uppercase tracking-widest text-slate-500 mb-2">Top Confusion Pairs</h4>
          <div className="space-y-1.5">
            {topErrors.map((err, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg border border-red-500/20 bg-red-900/10 px-3 py-2 text-sm">
                <span className="text-slate-300">
                  <span className="font-medium text-slate-100">{err.actual}</span>
                  <span className="text-slate-500 mx-2">→</span>
                  <span className="font-medium text-red-300">{err.predicted}</span>
                </span>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge variant="outline" className="text-[10px] border-red-500/40 text-red-300">
                    {err.count} cases
                  </Badge>
                  <span className="text-[11px] text-red-400">{pct(err.pct_of_actual)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Threshold analysis ── */}
      {thresholdAnalysis && (
        <div className="rounded-xl border border-violet-500/30 bg-violet-900/10 p-4 space-y-2">
          <h4 className="text-[11px] uppercase tracking-widest text-violet-400">Threshold Optimisation</h4>
          <p className="text-sm text-slate-300 leading-snug">{thresholdAnalysis.note}</p>
          <div className="grid grid-cols-3 gap-2 pt-1">
            {[
              { label: 'Optimal Threshold', value: thresholdAnalysis.optimal_threshold.toFixed(3) },
              { label: 'Best F1',           value: pct(thresholdAnalysis.best_f1) },
              { label: 'Best Recall',       value: pct(thresholdAnalysis.best_recall) },
            ].map((item, i) => (
              <div key={i} className="text-center">
                <div className="text-base font-bold text-violet-300">{item.value}</div>
                <div className="text-[10px] text-slate-500">{item.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-[10px] text-slate-600 text-right">Total samples: {totalSamples}</p>
    </div>
  );
};

export default MetricsPanel;
