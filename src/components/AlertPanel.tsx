// ============================================================================
// AlertPanel — Critical KPI Alerts
// Displays high-urgency KPIs (priorityScore ≥ 85) surfaced by the AI engine.
// ============================================================================

import React from 'react';
import { AlertTriangle, TrendingDown, Zap, Target } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { KPIItemData } from './KPIWidget';

interface AlertPanelProps {
  alerts: KPIItemData[];
}

function formatValue(value: number | string, unit?: string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return String(value);
  if (unit === '$' || unit === 'USD') {
    if (num >= 1_000_000) return `$${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `$${(num / 1_000).toFixed(1)}K`;
    return `$${num.toLocaleString()}`;
  }
  if (unit === '%') return `${num.toFixed(1)}%`;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num % 1 === 0 ? num.toLocaleString() : num.toFixed(2);
}

const SEVERITY_STYLES = {
  critical: {
    border: 'border-red-500/40',
    dot: 'bg-red-500 animate-pulse',
    badge: 'bg-red-900/40 text-red-300 border-red-700/50',
    icon: 'text-red-400',
    bg: 'bg-red-950/20',
  },
  high: {
    border: 'border-amber-500/40',
    dot: 'bg-amber-400',
    badge: 'bg-amber-900/40 text-amber-300 border-amber-700/50',
    icon: 'text-amber-400',
    bg: 'bg-amber-950/20',
  },
};

export const AlertPanel: React.FC<AlertPanelProps> = ({ alerts }) => {
  if (!alerts || alerts.length === 0) return null;

  return (
    <Card className="bg-slate-900/80 border-red-500/30 backdrop-blur-sm">
      <CardHeader className="pb-3 flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-red-900/40 rounded-lg flex items-center justify-center border border-red-700/40">
            <AlertTriangle className="h-4 w-4 text-red-400" />
          </div>
          <CardTitle className="text-sm font-semibold text-red-300">Critical Drivers</CardTitle>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-cyan-400 bg-cyan-900/30 border border-cyan-700/40 px-1.5 py-0.5 rounded-full flex items-center gap-1">
            <Zap className="h-2.5 w-2.5" /> AI Scored ≥ 85
          </span>
          <span className="text-[10px] font-mono text-slate-500">{alerts.length} alerts</span>
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-2">
        {alerts.map((kpi, i) => {
          const score = kpi.priorityScore ?? 0;
          const sev = score >= 90 ? SEVERITY_STYLES.critical : SEVERITY_STYLES.high;
          const ct = kpi.changeType || (kpi.trend === 'down' ? 'negative' : 'neutral');

          const targetPct = kpi.target && kpi.target > 0 && typeof kpi.value === 'number'
            ? Math.round((kpi.value / kpi.target) * 100)
            : null;

          return (
            <div
              key={kpi.id || i}
              className={`flex items-start gap-3 p-3 rounded-lg border ${sev.border} ${sev.bg} transition-all hover:border-red-400/50`}
              title={kpi.selectionReason}
            >
              {/* Severity dot */}
              <div className="mt-0.5 flex-shrink-0">
                <span className={`inline-block w-2 h-2 rounded-full ${sev.dot}`} />
              </div>

              {/* KPI info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-semibold text-white truncate">
                    {kpi.title || kpi.name || 'KPI'}
                  </span>
                  {kpi.category && (
                    <span className="text-[10px] uppercase tracking-widest text-slate-500 shrink-0">
                      {kpi.category}
                    </span>
                  )}
                </div>
                {kpi.selectionReason && (
                  <p className="text-[11px] text-slate-400 leading-tight line-clamp-1">
                    {kpi.selectionReason}
                  </p>
                )}
              </div>

              {/* Value + score */}
              <div className="flex-shrink-0 text-right">
                <div className={`text-base font-bold tabular-nums ${ct === 'negative' ? 'text-red-300' : 'text-white'}`}>
                  {formatValue(kpi.value, kpi.unit)}
                  {kpi.unit && kpi.unit !== '$' && kpi.unit !== 'USD' && (
                    <span className="text-xs text-slate-400 ml-0.5">{kpi.unit}</span>
                  )}
                </div>
                {targetPct !== null && (
                  <div className="flex items-center gap-1 justify-end mt-0.5">
                    <Target className="h-2.5 w-2.5 text-slate-500" />
                    <span className={`text-[10px] font-bold ${targetPct >= 100 ? 'text-emerald-400' : targetPct >= 80 ? 'text-amber-400' : 'text-red-400'}`}>
                      {targetPct}% of target
                    </span>
                  </div>
                )}
                {ct === 'negative' && (
                  <div className="flex items-center gap-0.5 justify-end mt-0.5">
                    <TrendingDown className="h-3 w-3 text-red-400" />
                    {kpi.change && <span className="text-[10px] text-red-400 font-bold">{kpi.change}</span>}
                  </div>
                )}
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border mt-1 inline-block ${sev.badge}`}
                  title="AI Priority Score"
                >
                  {score.toFixed(0)}/100
                </span>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
};

export default AlertPanel;
