import React, { useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Clock, DollarSign, Brain } from 'lucide-react';

interface ForecastEntry {
  metric: string;
  unit: string;
  currentValue?: number;
  forecastValue?: number;
  trend: 'up' | 'down' | 'stable';
  confidence: number;
  forecast: number[];
  models: {
    linear?: number[] | null;
    arima?: number[] | null;
    prophet?: number[] | null;
    xgboost?: number[] | null;
    ensemble?: number[] | null;
  };
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  breachPredicted: boolean;
  timeToBreach?: number | null;
  financialRisk?: number | null;
  decision: string;
  slope: number;
}

interface PredictiveDashboardProps {
  predictive: {
    forecast?: ForecastEntry[];
    whatIfScenarios?: any[];
    forecastSteps?: number;
    modelsUsed?: string[];
  };
}

const RISK_CONFIG: Record<string, { label: string; badge: string; border: string; icon: string }> = {
  critical: { label: 'Critical',  badge: 'bg-red-900/50 text-red-400 border-red-500/40',    border: 'border-red-500/30',    icon: 'text-red-400' },
  high:     { label: 'High Risk', badge: 'bg-orange-900/50 text-orange-400 border-orange-500/40', border: 'border-orange-500/30', icon: 'text-orange-400' },
  medium:   { label: 'Watch',     badge: 'bg-amber-900/50 text-amber-400 border-amber-500/40',  border: 'border-amber-500/30',  icon: 'text-amber-400' },
  low:      { label: 'Stable',    badge: 'bg-emerald-900/50 text-emerald-400 border-emerald-500/40', border: 'border-emerald-500/30', icon: 'text-emerald-400' },
};

const PALETTE = {
  ensemble: '#06b6d4',
  linear:   '#8b5cf6',
  arima:    '#10b981',
  prophet:  '#f59e0b',
  xgboost:  '#ec4899',
};

function buildChartData(entry: ForecastEntry) {
  const steps = entry.forecast?.length || 5;
  return Array.from({ length: steps }, (_, i) => {
    const period = `+${i + 1}`;
    const row: Record<string, any> = { period };
    if (entry.models?.ensemble?.[i] != null) row.ensemble = +entry.models.ensemble[i].toFixed(2);
    if (entry.models?.linear?.[i] != null)   row.linear   = +entry.models.linear[i].toFixed(2);
    if (entry.models?.arima?.[i] != null)     row.arima    = +entry.models.arima[i].toFixed(2);
    if (entry.models?.prophet?.[i] != null)   row.prophet  = +entry.models.prophet[i].toFixed(2);
    if (entry.models?.xgboost?.[i] != null)   row.xgboost  = +entry.models.xgboost[i].toFixed(2);
    return row;
  });
}

const ForecastCard: React.FC<{ entry: ForecastEntry }> = ({ entry }) => {
  const risk = RISK_CONFIG[entry.riskLevel] ?? RISK_CONFIG.low;
  const chartData = useMemo(() => buildChartData(entry), [entry]);
  const hasEnsemble = entry.models?.ensemble != null;
  const hasMultiModel = [entry.models?.linear, entry.models?.arima, entry.models?.prophet, entry.models?.xgboost].filter(Boolean).length > 1;
  const TrendIcon = entry.trend === 'up' ? TrendingUp : entry.trend === 'down' ? TrendingDown : Minus;
  const trendColor = entry.trend === 'up' ? 'text-emerald-400' : entry.trend === 'down' ? 'text-red-400' : 'text-slate-400';

  return (
    <Card className={`bg-slate-800/50 border backdrop-blur-sm ${risk.border} transition-all hover:shadow-lg`}>
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-white truncate">{entry.metric}</h3>
            {entry.decision && (
              <p className="text-[11px] text-slate-400 mt-0.5 leading-snug line-clamp-2">{entry.decision}</p>
            )}
          </div>
          <Badge className={`text-[10px] px-1.5 py-0.5 border shrink-0 ${risk.badge}`}>
            {risk.label}
          </Badge>
        </div>

        {/* Values row */}
        <div className="flex items-center gap-4">
          {entry.currentValue != null && (
            <div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">Current</div>
              <div className="text-lg font-bold text-slate-300">
                {entry.currentValue.toLocaleString()}{entry.unit}
              </div>
            </div>
          )}
          <div className="text-slate-600">→</div>
          {entry.forecastValue != null && (
            <div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">Forecast</div>
              <div className={`text-lg font-bold flex items-center gap-1 ${trendColor}`}>
                <TrendIcon className="h-4 w-4" />
                {entry.forecastValue.toLocaleString()}{entry.unit}
              </div>
            </div>
          )}
          <div className="ml-auto text-right">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Confidence</div>
            <div className="text-sm font-semibold text-teal-400">{Math.round(entry.confidence * 100)}%</div>
          </div>
        </div>

        {/* Confidence bar */}
        <div className="h-1 bg-slate-700 rounded-full">
          <div
            className="h-full rounded-full bg-gradient-to-r from-teal-500 to-cyan-400"
            style={{ width: `${Math.min(entry.confidence * 100, 100)}%` }}
          />
        </div>

        {/* Forecast chart */}
        {chartData.length > 0 && (
          <div className="h-28">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="2 2" stroke="#334155" />
                <XAxis dataKey="period" tick={{ fill: '#64748b', fontSize: 9 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 9 }} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 11 }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                {hasEnsemble && (
                  <Line dataKey="ensemble" name="Ensemble" stroke={PALETTE.ensemble} strokeWidth={2.5} dot={false} />
                )}
                {hasMultiModel && (<>
                  {entry.models?.linear  && <Line dataKey="linear"  name="Linear"  stroke={PALETTE.linear}  strokeWidth={1} strokeDasharray="3 3" dot={false} />}
                  {entry.models?.arima   && <Line dataKey="arima"   name="ARIMA"   stroke={PALETTE.arima}   strokeWidth={1} strokeDasharray="3 3" dot={false} />}
                  {entry.models?.prophet && <Line dataKey="prophet" name="Prophet" stroke={PALETTE.prophet} strokeWidth={1} strokeDasharray="3 3" dot={false} />}
                  {entry.models?.xgboost && <Line dataKey="xgboost" name="XGBoost" stroke={PALETTE.xgboost} strokeWidth={1} strokeDasharray="3 3" dot={false} />}
                </>)}
                {hasMultiModel && <Legend wrapperStyle={{ fontSize: 9, color: '#64748b' }} />}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Risk details */}
        <div className="flex flex-wrap gap-2 pt-1">
          {entry.breachPredicted && (
            <span className="flex items-center gap-1 text-[10px] text-red-400 bg-red-900/20 border border-red-500/20 rounded px-1.5 py-0.5">
              <AlertTriangle className="h-2.5 w-2.5" />
              Target breach predicted
            </span>
          )}
          {entry.timeToBreach != null && (
            <span className="flex items-center gap-1 text-[10px] text-orange-400 bg-orange-900/20 border border-orange-500/20 rounded px-1.5 py-0.5">
              <Clock className="h-2.5 w-2.5" />
              Breach in {entry.timeToBreach} period{entry.timeToBreach !== 1 ? 's' : ''}
            </span>
          )}
          {entry.financialRisk != null && entry.financialRisk > 0 && (
            <span className="flex items-center gap-1 text-[10px] text-amber-400 bg-amber-900/20 border border-amber-500/20 rounded px-1.5 py-0.5">
              <DollarSign className="h-2.5 w-2.5" />
              ~${entry.financialRisk.toLocaleString()} at risk
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

const PredictiveDashboard: React.FC<PredictiveDashboardProps> = ({ predictive }) => {
  const forecasts: ForecastEntry[] = predictive?.forecast || [];
  const modelsUsed: string[] = predictive?.modelsUsed || [];

  if (forecasts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Brain className="h-12 w-12 text-slate-600 mb-4" />
        <h3 className="text-lg font-semibold text-slate-400 mb-2">No Forecast Data Available</h3>
        <p className="text-sm text-slate-500 max-w-md">
          KPIs need a <code className="text-cyan-400">history</code> array (min 5 values) to enable forecasting.
          Upload time-series data to unlock predictive analytics.
        </p>
      </div>
    );
  }

  const criticalCount = forecasts.filter(f => f.riskLevel === 'critical' || f.riskLevel === 'high').length;

  return (
    <div className="space-y-5">
      {/* Summary bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700/40 rounded-lg px-3 py-2">
          <Brain className="h-4 w-4 text-cyan-400" />
          <span className="text-sm text-slate-300 font-medium">{forecasts.length} KPIs forecasted</span>
        </div>
        {criticalCount > 0 && (
          <div className="flex items-center gap-2 bg-red-900/20 border border-red-500/30 rounded-lg px-3 py-2">
            <AlertTriangle className="h-4 w-4 text-red-400" />
            <span className="text-sm text-red-400 font-medium">{criticalCount} high-risk KPI{criticalCount !== 1 ? 's' : ''}</span>
          </div>
        )}
        {modelsUsed.length > 0 && (
          <div className="flex items-center gap-2 bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">Models:</span>
            <div className="flex gap-1.5">
              {modelsUsed.map(m => (
                <span key={m} className="text-[10px] font-semibold text-slate-400 bg-slate-700/60 rounded px-1.5 py-0.5">{m}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Forecast cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {forecasts.map((entry, i) => (
          <ForecastCard key={i} entry={entry} />
        ))}
      </div>
    </div>
  );
};

export default PredictiveDashboard;
