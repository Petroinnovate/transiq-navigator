import React from 'react';
import { TrendingUp, TrendingDown, Minus, Brain, Zap } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export interface KPIItemData {
  id?: string;
  title?: string;
  name?: string;
  value: number | string;
  unit?: string;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  trend?: 'up' | 'down' | 'stable';
  status?: 'good' | 'warning' | 'critical';
  target?: number;
  category?: string;
  sparkData?: Array<{ v: number }>;
  // AI scoring fields
  priorityScore?: number;
  visibility?: 'primary' | 'secondary' | 'hidden';
  selectionReason?: string;
}

interface KPIStatCardProps {
  kpi: KPIItemData;
  index: number;
}

// Resolve changeType from trend or changeType field
function resolveChangeType(kpi: KPIItemData): 'positive' | 'negative' | 'neutral' {
  if (kpi.changeType) return kpi.changeType;
  if (kpi.trend === 'up') return 'positive';
  if (kpi.trend === 'down') return 'negative';
  return 'neutral';
}

function formatValue(value: number | string, unit?: string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return String(value);
  if (unit === '%') return `${num.toFixed(num % 1 === 0 ? 0 : 1)}%`;
  if (unit === '$' || unit === 'USD') {
    if (num >= 1_000_000) return `$${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `$${(num / 1_000).toFixed(1)}K`;
    return `$${num.toLocaleString()}`;
  }
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num % 1 === 0 ? num.toLocaleString() : num.toFixed(2);
}

const STATUS_STYLES = {
  good:     { dot: 'bg-emerald-400', label: 'On Track',  text: 'text-emerald-400', bg: 'bg-emerald-900/30' },
  warning:  { dot: 'bg-amber-400',   label: 'Watch',     text: 'text-amber-400',   bg: 'bg-amber-900/30'   },
  critical: { dot: 'bg-red-500 animate-pulse', label: 'Critical', text: 'text-red-400', bg: 'bg-red-900/30' },
};

const CHANGE_STYLES = {
  positive: 'text-emerald-400',
  negative: 'text-red-400',
  neutral:  'text-slate-400',
};

const SPARK_COLORS = {
  positive: '#34d399',
  negative: '#f87171',
  neutral:  '#22d3ee',
};

const BORDER_HOVER = {
  positive: 'hover:border-emerald-500/40 hover:shadow-emerald-500/5',
  negative: 'hover:border-red-500/40 hover:shadow-red-500/5',
  neutral:  'hover:border-cyan-500/40 hover:shadow-cyan-500/5',
};

// ── Individual KPI stat card ─────────────────────────────────────────────
const KPIStatCard: React.FC<KPIStatCardProps> = ({ kpi, index }) => {
  const ct = resolveChangeType(kpi);
  const sparkColor = SPARK_COLORS[ct];
  const cardId = kpi.id || `kpi-widget-${index}`;

  // Generate a plausible synthetic sparkline when none is provided
  const sparkData = React.useMemo(() => {
    if (kpi.sparkData && kpi.sparkData.length > 0) return kpi.sparkData;
    const base = typeof kpi.value === 'number' ? Math.abs(kpi.value) || 100 : 100;
    const direction = ct === 'positive' ? 1 : ct === 'negative' ? -1 : 0;
    return Array.from({ length: 8 }, (_, i) => ({
      v: Math.max(0, base * (0.7 + (i / 7) * 0.3 * (1 + direction * 0.3) + (Math.random() - 0.5) * 0.12)),
    }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kpi.value, ct]);

  const targetProgress =
    kpi.target && kpi.target > 0 && typeof kpi.value === 'number'
      ? Math.min(Math.round((kpi.value / kpi.target) * 100), 120)
      : null;

  const targetBarColor =
    targetProgress == null ? '' :
    targetProgress >= 100 ? 'bg-emerald-500' :
    targetProgress >= 75  ? 'bg-amber-400' : 'bg-red-500';

  const statusCfg = kpi.status ? STATUS_STYLES[kpi.status] : null;

  return (
    <Card
      className={`bg-slate-800/60 border-slate-700/60 backdrop-blur-sm ${BORDER_HOVER[ct]} transition-all duration-300 group overflow-hidden hover:shadow-lg`}
      title={kpi.selectionReason ? `AI Selected: ${kpi.selectionReason}` : undefined}
    >
      <CardContent className="p-4">
        {/* Top row: trend icon + change badge + AI priority score */}
        <div className="flex items-start justify-between mb-2">
          <div className="w-8 h-8 bg-gradient-to-br from-cyan-400/20 to-teal-400/10 rounded-lg flex items-center justify-center border border-cyan-500/20 group-hover:border-cyan-500/40 transition-all">
            {ct === 'positive' && <TrendingUp className="h-4 w-4 text-emerald-400" />}
            {ct === 'negative' && <TrendingDown className="h-4 w-4 text-red-400" />}
            {ct === 'neutral'  && <Minus className="h-4 w-4 text-slate-400" />}
          </div>
          <div className="flex items-center gap-1">
            {kpi.priorityScore !== undefined && (
              <span
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border flex items-center gap-0.5 ${
                  kpi.priorityScore >= 80 ? 'text-emerald-300 bg-emerald-900/40 border-emerald-700/50' :
                  kpi.priorityScore >= 50 ? 'text-amber-300 bg-amber-900/40 border-amber-700/50' :
                  'text-slate-400 bg-slate-700/40 border-slate-600/50'
                }`}
                title={kpi.selectionReason}
              >
                <Brain className="h-2.5 w-2.5" />
                {kpi.priorityScore.toFixed(0)}
              </span>
            )}
            {kpi.change && (
              <span className={`text-xs font-bold ${CHANGE_STYLES[ct]} flex items-center gap-0.5`}>
                {ct === 'positive' && <TrendingUp className="h-3 w-3" />}
                {ct === 'negative' && <TrendingDown className="h-3 w-3" />}
                {kpi.change}
              </span>
            )}
          </div>
        </div>

        {/* Value */}
        <div className="text-2xl font-bold text-white leading-none mb-0.5 tabular-nums">
          {formatValue(kpi.value, kpi.unit)}
        </div>

        {/* Title */}
        <div className="text-[11px] text-slate-400 font-medium mb-2 uppercase tracking-wider leading-tight line-clamp-1">
          {kpi.title || kpi.name || 'Metric'}
        </div>

        {/* Sparkline */}
        <div className="h-8 -mx-1">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
              <defs>
                <linearGradient id={`spark-kw-${cardId}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={sparkColor} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={sparkColor} stopOpacity={0}    />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={sparkColor}
                strokeWidth={1.5}
                fill={`url(#spark-kw-${cardId})`}
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Target progress bar */}
        {targetProgress !== null && (
          <div className="mt-2">
            <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1">
              <span>Target</span>
              <span className={targetProgress >= 100 ? 'text-emerald-400' : targetProgress >= 75 ? 'text-amber-400' : 'text-red-400'}>
                {targetProgress}%
              </span>
            </div>
            <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${targetBarColor}`}
                style={{ width: `${Math.min(targetProgress, 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* Status / category footer */}
        <div className="flex items-center justify-between mt-1.5">
          {statusCfg ? (
            <span className={`text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded ${statusCfg.text} ${statusCfg.bg}`}>
              <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1 ${statusCfg.dot}`} />
              {statusCfg.label}
            </span>
          ) : kpi.category ? (
            <span className="text-[10px] uppercase tracking-widest font-semibold text-slate-500">
              {kpi.category}
            </span>
          ) : (
            <span />
          )}
        </div>
      </CardContent>
    </Card>
  );
};

// ── KPIWidget: grid of stat cards with optional insights ─────────────────
export interface KPIWidgetProps {
  kpis: KPIItemData[];
  title?: string;
  insights?: string[];
  poolSize?: number; // total KPIs in the AI pool (shown in header)
}

type FilterMode = 'top5' | 'top10' | 'all';

const KPIWidget: React.FC<KPIWidgetProps> = ({ kpis, title = 'Key Metrics', insights, poolSize }) => {
  const [filterMode, setFilterMode] = React.useState<FilterMode>('top10');

  if (!kpis || kpis.length === 0) return null;

  const filteredKpis =
    filterMode === 'top5'  ? kpis.slice(0, 5) :
    filterMode === 'top10' ? kpis.slice(0, 10) :
    kpis;

  // Choose an appropriate grid density based on count
  const gridClass =
    filteredKpis.length <= 2 ? 'grid-cols-1 sm:grid-cols-2' :
    filteredKpis.length <= 4 ? 'grid-cols-2 sm:grid-cols-2 lg:grid-cols-4' :
                               'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4';

  const hasScoring = kpis.some(k => k.priorityScore !== undefined);

  return (
    <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm hover:border-cyan-500/30 transition-all duration-300">
      <CardHeader className="pb-3 flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <CardTitle className="text-base font-semibold text-white">{title}</CardTitle>
          {hasScoring && (
            <span className="text-[10px] text-cyan-400 bg-cyan-900/30 border border-cyan-700/40 px-1.5 py-0.5 rounded-full flex items-center gap-1">
              <Zap className="h-2.5 w-2.5" /> AI Ranked
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* AI Filter Mode toggle */}
          <div className="flex items-center gap-0.5 bg-slate-700/60 rounded-lg p-0.5 border border-slate-600/40">
            {(['top5', 'top10', 'all'] as FilterMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setFilterMode(mode)}
                className={`text-[10px] px-2 py-1 rounded-md font-medium transition-all ${
                  filterMode === mode
                    ? 'bg-cyan-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {mode === 'top5' ? 'Top 5' : mode === 'top10' ? 'Top 10' : 'All'}
              </button>
            ))}
          </div>
          <span className="text-[10px] text-slate-500 font-mono">
            {filteredKpis.length}/{poolSize ?? kpis.length}
          </span>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className={`grid ${gridClass} gap-3`}>
          {filteredKpis.map((kpi, i) => (
            <KPIStatCard key={kpi.id || `kw-${i}`} kpi={kpi} index={i} />
          ))}
        </div>

        {insights && insights.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-700/50 space-y-1.5">
            {insights.map((ins, i) => (
              <p key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                <span className="text-cyan-500 shrink-0 mt-0.5">•</span>
                {ins}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default KPIWidget;
