import React, { useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { TrendingUp, TrendingDown, DollarSign, Users, BarChart3, Activity, Target, Star, ShoppingCart, Package, Award, Percent, Clock, Repeat } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts';
import { CitationBadge } from '@/components/citation/CitationBadge';
import type { KPIValue, RigIdentity } from '@/types/ddr.types';
import { DDR_TOKENS } from '@/styles/tokens';

interface KPICardProps {
  kpi: {
    id: string;
    title: string;
    value: number;
    unit: string;
    change: string;
    changeType: 'positive' | 'negative' | 'neutral';
    icon: string;
    color: string;
    sparkData?: Array<{ v: number }>;
    category?: 'financial' | 'customer' | 'operational' | 'team' | string;
    status?: 'good' | 'warning' | 'critical';
    target?: number;
    targetLabel?: string;
    // AI scoring fields
    priorityScore?: number;
    visibility?: 'primary' | 'secondary' | 'hidden';
    selectionReason?: string;
  };
  // DDR props (optional — backward compatible)
  kpiValue?: KPIValue;
  identity?: RigIdentity;
  serviceProviders?: string[];
  equipment?: string;
  ddrStatus?: 'normal' | 'warning' | 'critical';
  showStatusRing?: boolean;
}

const KPICard = ({ kpi, kpiValue, identity, serviceProviders, equipment, ddrStatus, showStatusRing }: KPICardProps) => {
  const getIcon = (iconName: string) => {
    switch ((iconName || '').toLowerCase()) {
      case 'dollar': case 'dollarsign': case 'attach_money': return <DollarSign className="h-5 w-5" />;
      case 'users': case 'person': case 'people': return <Users className="h-5 w-5" />;
      case 'activity': return <Activity className="h-5 w-5" />;
      case 'barchart': case 'chart': case 'assessment': return <BarChart3 className="h-5 w-5" />;
      case 'target': return <Target className="h-5 w-5" />;
      case 'star': case 'nps': return <Star className="h-5 w-5" />;
      case 'shopping_cart': case 'cart': return <ShoppingCart className="h-5 w-5" />;
      case 'package': case 'inventory': return <Package className="h-5 w-5" />;
      case 'award': case 'efficiency': return <Award className="h-5 w-5" />;
      case 'percent': case 'percentage': return <Percent className="h-5 w-5" />;
      case 'clock': case 'lead_time': return <Clock className="h-5 w-5" />;
      case 'repeat': case 'retention': return <Repeat className="h-5 w-5" />;
      case 'trending_up': return <TrendingUp className="h-5 w-5" />;
      default: return <TrendingUp className="h-5 w-5" />;
    }
  };

  const statusConfig = {
    good:     { dot: 'bg-emerald-400', ring: 'border-emerald-500/30', label: 'On Track' },
    warning:  { dot: 'bg-amber-400',   ring: 'border-amber-500/30',   label: 'Watch'    },
    critical: { dot: 'bg-red-500',     ring: 'border-red-500/30',     label: 'Critical' },
  };
  const statusCfg = kpi.status ? statusConfig[kpi.status] : null;

  const getChangeIcon = () => {
    if (kpi.changeType === 'positive') return <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />;
    if (kpi.changeType === 'negative') return <TrendingDown className="h-3.5 w-3.5 text-red-400" />;
    return null;
  };

  const getChangeColor = () => {
    if (kpi.changeType === 'positive') return 'text-emerald-400';
    if (kpi.changeType === 'negative') return 'text-red-400';
    return 'text-slate-400';
  };

  const sparkColor = kpi.changeType === 'positive' ? '#34d399' : kpi.changeType === 'negative' ? '#f87171' : '#22d3ee';

  const formatValue = (value: number, unit: string) => {
    if (value === undefined || value === null) return 'N/A';
    if (unit === '%') return `${value}%`;
    if (unit === '$' || unit === 'USD') {
      if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
      if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`;
      return `$${value.toFixed(0)}`;
    }
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
    return value.toLocaleString();
  };

  // Generate synthetic sparkline if none provided
  const sparkData = useMemo(() => {
    if (kpi.sparkData && kpi.sparkData.length > 0) return kpi.sparkData;
    const base = kpi.value || 100;
    const trend = kpi.changeType === 'positive' ? 1 : kpi.changeType === 'negative' ? -1 : 0;
    return Array.from({ length: 8 }, (_, i) => ({
      v: Math.max(0, base * (0.7 + (i / 7) * 0.3 * (1 + trend * 0.3) + (Math.random() - 0.5) * 0.12))
    }));
  }, [kpi.value, kpi.changeType, kpi.sparkData]);

  // Target progress (value vs target, capped at 120%)
  const targetProgress = kpi.target && kpi.target > 0
    ? Math.min(Math.round((kpi.value / kpi.target) * 100), 120)
    : null;
  const targetProgressColor = targetProgress == null ? '' :
    targetProgress >= 100 ? 'bg-emerald-500' :
    targetProgress >= 75  ? 'bg-amber-400' : 'bg-red-500';

  const borderColor = kpi.status === 'critical' ? 'hover:border-red-500/50'
    : kpi.status === 'warning' ? 'hover:border-amber-500/40'
    : 'hover:border-cyan-500/40';

  // DDR status ring glow
  const ddrRingStyle = showStatusRing && ddrStatus ? {
    boxShadow: ddrStatus === 'critical' ? DDR_TOKENS.shadow.glowRed
             : ddrStatus === 'warning' ? DDR_TOKENS.shadow.glowAmber
             : DDR_TOKENS.shadow.glowGreen,
  } : {};

  // Glow CSS class based on kpi.status
  const glowClass = kpi.status === 'critical' ? 'glow-red'
    : kpi.status === 'warning' ? 'glow-amber'
    : kpi.status === 'good' ? 'glow-green'
    : '';

  return (
    <Card
      className={`card-surface ${glowClass} ${borderColor} transition-all duration-300 group overflow-hidden hover:shadow-lg hover:shadow-cyan-500/5`}
      style={ddrRingStyle}
    >
      <CardContent className="p-4">
        {/* Top row: icon + change badge + AI priority score */}
        <div className="flex items-start justify-between mb-2">
          <div className="w-8 h-8 bg-gradient-to-br from-cyan-400/20 to-teal-400/10 rounded-lg flex items-center justify-center border border-cyan-500/20 group-hover:border-cyan-500/40 transition-all">
            <div className="text-cyan-400">{getIcon(kpi.icon)}</div>
          </div>
          <div className="flex items-center gap-1.5">
            {kpi.priorityScore !== undefined && kpi.priorityScore !== null && (
              <span
                title={kpi.selectionReason ? `Why this KPI? ${kpi.selectionReason}` : `AI Priority Score: ${kpi.priorityScore}/100`}
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded cursor-help leading-none ${
                  kpi.priorityScore >= 80 ? 'bg-red-900/40 text-red-400 border border-red-500/30' :
                  kpi.priorityScore >= 60 ? 'bg-amber-900/40 text-amber-400 border border-amber-500/30' :
                                            'bg-slate-700/60 text-slate-400 border border-slate-600/30'
                }`}
              >
                {Math.round(kpi.priorityScore)}
              </span>
            )}
            <div className={`flex items-center gap-0.5 text-xs font-bold ${getChangeColor()}`}>
              {getChangeIcon()}
              {kpi.change && kpi.change !== '' && <span>{kpi.change}</span>}
            </div>
          </div>
        </div>

        {/* Value + DDR Citation */}
        <div className="text-2xl font-bold text-white leading-none mb-0.5 flex items-center gap-1">
          {formatValue(kpi.value, kpi.unit)}
          {kpiValue && identity && (
            <CitationBadge
              kpiValue={kpiValue}
              identity={identity}
              serviceProviders={serviceProviders}
              equipment={equipment}
              compact
            />
          )}
        </div>

        {/* Citation Confidence Bar */}
        {kpiValue && (
          <div className="flex items-center gap-1.5 mb-1" title={`Confidence: ${(kpiValue.confidence * 100).toFixed(0)}%`}>
            <span className="text-[9px] text-slate-500 w-14">Confidence</span>
            <div className="flex-1 h-1 rounded-full bg-slate-700/60 overflow-hidden">
              <div
                className="h-1 rounded-full transition-all duration-500"
                style={{
                  width: `${kpiValue.confidence * 100}%`,
                  background: kpiValue.confidence >= 0.95 ? DDR_TOKENS.status.excellent
                    : kpiValue.confidence >= 0.80 ? DDR_TOKENS.status.warning
                    : DDR_TOKENS.status.critical,
                }}
              />
            </div>
            <span className="text-[9px] text-slate-500 w-7 text-right">{(kpiValue.confidence * 100).toFixed(0)}%</span>
          </div>
        )}

        {/* Title + Derived Indicator */}
        <div
          className="text-[11px] text-slate-400 font-medium mb-2 uppercase tracking-wider leading-tight flex items-center gap-1"
          title={kpi.selectionReason ? `Why this KPI? ${kpi.selectionReason}` : undefined}
        >
          {kpi.title}
          {kpiValue?.is_derived && (
            <span title="Derived KPI" className="text-amber-400 cursor-help">⚡</span>
          )}
        </div>

        {/* Sparkline */}
        <div className="h-8 -mx-1">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
              <defs>
                <linearGradient id={`spark-${kpi.id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={sparkColor} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={sparkColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={sparkColor}
                strokeWidth={1.5}
                fill={`url(#spark-${kpi.id})`}
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Status + target footer */}
        <div className="flex items-center justify-between mt-1.5">
          {statusCfg ? (
            <span className={`text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded ${
              kpi.status === 'good'     ? 'text-emerald-400 bg-emerald-900/30' :
              kpi.status === 'warning'  ? 'text-amber-400 bg-amber-900/30' :
                                          'text-red-400 bg-red-900/30'
            }`}>
              <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1 ${statusCfg.dot} ${kpi.status === 'critical' ? 'animate-pulse' : ''}`} />
              {statusCfg.label}
            </span>
          ) : kpi.category ? (
            <span className="text-[10px] uppercase tracking-widest font-semibold text-slate-500">
              {kpi.category}
            </span>
          ) : <span />}
          {targetProgress !== null && (
            <span className={`text-[10px] font-bold ${
              targetProgress >= 100 ? 'text-emerald-400' : targetProgress >= 75 ? 'text-amber-400' : 'text-red-400'
            }`}>{targetProgress}% target</span>
          )}
        </div>

        {/* DDR Identity footer (only when DDR data is loaded) */}
        {identity && (
          <div className="mt-2 pt-2 border-t border-slate-700/40 flex flex-wrap gap-1">
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400 font-mono">
              {identity.rig_id}
            </span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400 font-mono">
              {identity.well_id}
            </span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400 font-mono">
              {identity.report_date}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default KPICard;