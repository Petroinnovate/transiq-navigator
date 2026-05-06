import React, { useState } from 'react';
import { Database, Sigma, GitBranch, AlertOctagon, FlaskConical, ChevronDown, ChevronUp } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface FailureMode {
  cause: string;
  probability?: number;
  detection?: string;
  mitigation?: string;
  rpn?: number;
}

interface StatSummary {
  sigma_level?: string;
  cpk?: number;
  r_squared?: number;
  confidence_interval?: string;
}

interface EngineerViewData {
  data_references?: string[];
  models?: string[];
  root_cause_analysis?: string[];
  failure_modes?: FailureMode[];
  assumptions?: string[];
  statistical_summary?: StatSummary;
}

interface EngineerViewProps {
  data: EngineerViewData;
}

const SECTIONS = [
  { key: 'data_references',    label: 'Data References',       icon: Database,     color: 'text-cyan-400',   bg: 'bg-cyan-500/10',   border: 'border-cyan-500/30' },
  { key: 'models',             label: 'Statistical Models',    icon: Sigma,        color: 'text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/30' },
  { key: 'root_cause_analysis',label: 'Root Cause Analysis',   icon: GitBranch,    color: 'text-amber-400',  bg: 'bg-amber-500/10',  border: 'border-amber-500/30' },
  { key: 'failure_modes',      label: 'Failure Modes (FMEA)',  icon: AlertOctagon, color: 'text-red-400',    bg: 'bg-red-500/10',    border: 'border-red-500/30' },
  { key: 'assumptions',        label: 'Assumptions & Limits',  icon: FlaskConical, color: 'text-slate-400',  bg: 'bg-slate-700/30',  border: 'border-slate-600/40' },
] as const;

const probColor = (p: number) => {
  if (p >= 0.7) return 'bg-red-500/15 text-red-400 border-red-500/40';
  if (p >= 0.4) return 'bg-amber-500/15 text-amber-400 border-amber-500/40';
  return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40';
};

const EngineerView: React.FC<EngineerViewProps> = ({ data }) => {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const toggle = (key: string) => setCollapsed(p => ({ ...p, [key]: !p[key] }));

  const stats = data?.statistical_summary;

  return (
    <div className="space-y-6">

      {/* ── Statistical Header ────────────────────────────────────── */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Sigma Level',     value: stats.sigma_level      || '—' },
            { label: 'Cpk',             value: stats.cpk != null ? stats.cpk.toFixed(2) : '—' },
            { label: 'R²',              value: stats.r_squared != null ? stats.r_squared.toFixed(3) : '—' },
            { label: 'Conf. Interval',  value: stats.confidence_interval || '—' },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-xl border border-slate-700/60 bg-slate-800/60 px-4 py-3 text-center">
              <p className="text-xs text-slate-400 mb-1 uppercase tracking-wider">{label}</p>
              <p className="text-lg font-bold text-white font-mono">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Failure Modes table (FMEA) — always prominent ────────── */}
      {(data?.failure_modes?.length ?? 0) > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-red-500/15 border border-red-500/30 flex items-center justify-center">
              <AlertOctagon className="h-4 w-4 text-red-400" />
            </div>
            <h3 className="text-sm font-bold text-white uppercase tracking-widest">Failure Modes & Effects (FMEA)</h3>
          </div>
          <div className="rounded-xl border border-slate-700/60 overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-800/80">
                <tr>
                  {['Failure Mode', 'Probability', 'RPN', 'Detection', 'Mitigation'].map(h => (
                    <th key={h} className="px-3 py-2.5 text-left text-slate-400 font-semibold uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40">
                {data!.failure_modes!.map((fm, i) => (
                  <tr key={i} className="bg-slate-800/30 hover:bg-slate-800/60 transition-colors">
                    <td className="px-3 py-2.5 text-white font-medium max-w-[220px]">{fm.cause}</td>
                    <td className="px-3 py-2.5">
                      {fm.probability != null ? (
                        <Badge className={`text-[10px] px-1.5 py-0.5 border ${probColor(fm.probability)}`}>
                          {Math.round(fm.probability * 100)}%
                        </Badge>
                      ) : '—'}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-slate-300">{fm.rpn ?? '—'}</td>
                    <td className="px-3 py-2.5 text-slate-400 max-w-[180px]">{fm.detection || '—'}</td>
                    <td className="px-3 py-2.5 text-slate-300 max-w-[220px]">{fm.mitigation || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Collapsible detail sections ───────────────────────────── */}
      {SECTIONS.filter(s => s.key !== 'failure_modes').map(({ key, label, icon: Icon, color, bg, border }) => {
        const items: any[] = (data as any)?.[key] || [];
        if (items.length === 0) return null;
        const isCollapsed = collapsed[key];
        return (
          <div key={key}>
            <button
              className="w-full flex items-center justify-between mb-3"
              onClick={() => toggle(key)}
            >
              <div className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-lg ${bg} border ${border} flex items-center justify-center`}>
                  <Icon className={`h-4 w-4 ${color}`} />
                </div>
                <h3 className="text-sm font-bold text-white uppercase tracking-widest">{label}</h3>
                <Badge className="bg-slate-700/60 text-slate-400 border-slate-600/40 text-[10px] px-1.5">{items.length}</Badge>
              </div>
              {isCollapsed
                ? <ChevronDown className="h-4 w-4 text-slate-500" />
                : <ChevronUp className="h-4 w-4 text-slate-500" />
              }
            </button>
            {!isCollapsed && (
              <ul className="space-y-2">
                {items.map((item: string, i: number) => (
                  <li key={i} className="flex gap-3 rounded-lg border border-slate-700/50 bg-slate-800/40 px-4 py-3">
                    <span className={`text-[10px] font-bold mt-0.5 flex-shrink-0 ${color}`}>{String(i + 1).padStart(2, '0')}</span>
                    <p className="text-sm text-slate-300 leading-relaxed font-mono">{item}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}

    </div>
  );
};

export default EngineerView;
