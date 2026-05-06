import React, { useState } from 'react';
import { BarChart3, Target, TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp, CheckCircle2, AlertCircle, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface DmiacPhases {
  define?: string;
  measure?: string;
  analyze?: string;
  improve?: string;
  control?: string;
}

interface Recommendation {
  title: string;
  impact?: string;
  timeline?: string;
  priority?: 'high' | 'medium' | 'low';
  owner?: string;
}

interface KPITrack {
  name: string;
  current?: string;
  target?: string;
  gap?: string;
  status?: 'on-track' | 'at-risk' | 'off-track';
  trend?: 'improving' | 'deteriorating' | 'stable';
}

interface ManagerViewData {
  dmaic?: DmiacPhases;
  recommendations?: Recommendation[];
  kpi_tracking?: KPITrack[];
}

interface ManagerViewProps {
  data: ManagerViewData;
}

const DMAIC_META = [
  { key: 'define',  label: 'Define',  color: 'cyan',    ring: 'ring-cyan-500/40',   bg: 'bg-cyan-500/10',   text: 'text-cyan-400' },
  { key: 'measure', label: 'Measure', color: 'blue',    ring: 'ring-blue-500/40',   bg: 'bg-blue-500/10',   text: 'text-blue-400' },
  { key: 'analyze', label: 'Analyze', color: 'violet',  ring: 'ring-violet-500/40', bg: 'bg-violet-500/10', text: 'text-violet-400' },
  { key: 'improve', label: 'Improve', color: 'amber',   ring: 'ring-amber-500/40',  bg: 'bg-amber-500/10',  text: 'text-amber-400' },
  { key: 'control', label: 'Control', color: 'emerald', ring: 'ring-emerald-500/40',bg: 'bg-emerald-500/10',text: 'text-emerald-400' },
] as const;

const priorityColors: Record<string, string> = {
  high:   'bg-red-500/15 text-red-400 border-red-500/40',
  medium: 'bg-amber-500/15 text-amber-400 border-amber-500/40',
  low:    'bg-slate-600/40 text-slate-400 border-slate-500/40',
};

const statusIcon = (status?: string) => {
  if (status === 'on-track')  return <CheckCircle2  className="h-4 w-4 text-emerald-400" />;
  if (status === 'at-risk')   return <AlertCircle   className="h-4 w-4 text-amber-400" />;
  if (status === 'off-track') return <XCircle       className="h-4 w-4 text-red-400" />;
  return <Minus className="h-4 w-4 text-slate-500" />;
};

const statusBadge: Record<string, string> = {
  'on-track':  'bg-emerald-500/15 text-emerald-400 border-emerald-500/40',
  'at-risk':   'bg-amber-500/15 text-amber-400 border-amber-500/40',
  'off-track': 'bg-red-500/15 text-red-400 border-red-500/40',
};

const trendIcon = (trend?: string) => {
  if (trend === 'improving')    return <TrendingUp   className="h-3.5 w-3.5 text-emerald-400" />;
  if (trend === 'deteriorating') return <TrendingDown className="h-3.5 w-3.5 text-red-400" />;
  return <Minus className="h-3.5 w-3.5 text-slate-500" />;
};

const ManagerView: React.FC<ManagerViewProps> = ({ data }) => {
  const dmaic     = data?.dmaic || {};
  const recs      = data?.recommendations || [];
  const kpis      = data?.kpi_tracking || [];
  const [openPhase, setOpenPhase] = useState<string | null>('define');

  return (
    <div className="space-y-8">

      {/* ── DMAIC Breakdown ─────────────────────────────────────────── */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-violet-500/15 border border-violet-500/30 flex items-center justify-center">
            <BarChart3 className="h-4 w-4 text-violet-400" />
          </div>
          <h3 className="text-sm font-bold text-white uppercase tracking-widest">DMAIC Breakdown</h3>
        </div>

        <div className="space-y-2">
          {DMAIC_META.map(({ key, label, ring, bg, text }) => {
            const content = (dmaic as any)[key] || '';
            const isOpen = openPhase === key;
            return (
              <div key={key} className={`rounded-xl border border-slate-700/60 overflow-hidden transition-all ${isOpen ? ring + ' ring-1' : ''}`}>
                <button
                  className={`w-full flex items-center justify-between px-4 py-3 ${isOpen ? bg : 'bg-slate-800/50 hover:bg-slate-800/80'} transition-colors`}
                  onClick={() => setOpenPhase(isOpen ? null : key)}
                >
                  <div className="flex items-center gap-3">
                    <span className={`text-xs font-bold uppercase tracking-widest ${isOpen ? text : 'text-slate-500'}`}>{label}</span>
                    {!isOpen && content && (
                      <span className="text-xs text-slate-500 truncate max-w-xs hidden sm:block">{content.split('.')[0]}.</span>
                    )}
                  </div>
                  {isOpen ? <ChevronUp className={`h-4 w-4 ${text}`} /> : <ChevronDown className="h-4 w-4 text-slate-500" />}
                </button>
                {isOpen && (
                  <div className="px-4 pb-4 pt-2 bg-slate-800/30">
                    {content
                      ? <p className="text-sm text-slate-300 leading-relaxed">{content}</p>
                      : <p className="text-xs text-slate-600 italic">No data for this phase.</p>
                    }
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

        {/* ── Recommendations ───────────────────────────────────────── */}
        {recs.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center">
                <TrendingUp className="h-4 w-4 text-amber-400" />
              </div>
              <h3 className="text-sm font-bold text-white uppercase tracking-widest">Recommendations</h3>
            </div>
            <div className="space-y-3">
              {recs.slice(0, 6).map((rec, i) => (
                <div key={i} className="rounded-xl border border-slate-700/60 bg-slate-800/50 p-4">
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <p className="text-sm font-semibold text-white leading-snug flex-1">{rec.title}</p>
                    {rec.priority && (
                      <Badge className={`text-[10px] px-1.5 py-0.5 border flex-shrink-0 ${priorityColors[rec.priority] || priorityColors.medium}`}>
                        {rec.priority}
                      </Badge>
                    )}
                  </div>
                  {rec.impact && <p className="text-xs text-emerald-400/80 mb-1">{rec.impact}</p>}
                  <div className="flex items-center gap-3 mt-2">
                    {rec.owner    && <span className="text-xs text-slate-500">{rec.owner}</span>}
                    {rec.timeline && <span className="text-xs text-slate-600">· {rec.timeline}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── KPI Tracking ──────────────────────────────────────────── */}
        {kpis.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center">
                <Target className="h-4 w-4 text-cyan-400" />
              </div>
              <h3 className="text-sm font-bold text-white uppercase tracking-widest">KPI Tracking</h3>
            </div>
            <div className="rounded-xl border border-slate-700/60 overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-slate-800/80">
                  <tr>
                    {['KPI', 'Current', 'Target', 'Status', 'Trend'].map(h => (
                      <th key={h} className="px-3 py-2.5 text-left text-slate-400 font-semibold uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/40">
                  {kpis.slice(0, 8).map((kpi, i) => (
                    <tr key={i} className="bg-slate-800/30 hover:bg-slate-800/60 transition-colors">
                      <td className="px-3 py-2.5 text-white font-medium">{kpi.name}</td>
                      <td className="px-3 py-2.5 text-slate-300">{kpi.current ?? '—'}</td>
                      <td className="px-3 py-2.5 text-slate-400">{kpi.target ?? '—'}</td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-1.5">
                          {statusIcon(kpi.status)}
                          {kpi.status && (
                            <Badge className={`text-[10px] px-1.5 py-0.5 border ${statusBadge[kpi.status] || ''}`}>
                              {kpi.status.replace('-', ' ')}
                            </Badge>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2.5">{trendIcon(kpi.trend)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default ManagerView;
