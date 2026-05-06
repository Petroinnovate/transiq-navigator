import React from 'react';
import { AlertTriangle, CheckCircle, Zap, TrendingUp, TrendingDown, Clock, ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface CEODecision {
  title: string;
  impact: string;
  urgency: 'High' | 'Medium' | 'Low';
}

interface CEORisk {
  title: string;
  severity: 'High' | 'Medium' | 'Low';
  financial_impact: string;
}

interface CEOAction {
  title: string;
  owner: string;
  timeline: string;
}

interface CEOViewData {
  decisions?: CEODecision[];
  risks?: CEORisk[];
  actions?: CEOAction[];
}

interface CEOViewProps {
  data: CEOViewData;
}

const urgencyColors: Record<string, string> = {
  High: 'bg-red-500/15 text-red-400 border-red-500/40',
  Medium: 'bg-amber-500/15 text-amber-400 border-amber-500/40',
  Low: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40',
};

const severityDot: Record<string, string> = {
  High: 'bg-red-400',
  Medium: 'bg-amber-400',
  Low: 'bg-emerald-400',
};

const CEOView: React.FC<CEOViewProps> = ({ data }) => {
  const decisions: CEODecision[] = (data?.decisions || []).slice(0, 3);
  const risks: CEORisk[] = (data?.risks || []).slice(0, 3);
  const actions: CEOAction[] = (data?.actions || []).slice(0, 3);

  const isEmpty = decisions.length === 0 && risks.length === 0 && actions.length === 0;

  if (isEmpty) {
    return (
      <div className="flex items-center justify-center py-16 text-slate-500 text-sm">
        CEO View is being generated — no data yet.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Readable-in-30s tagline ─────────────────────────────────── */}
      <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-4 py-3 flex items-center gap-2">
        <Clock className="h-4 w-4 text-cyan-400 flex-shrink-0" />
        <span className="text-xs text-cyan-300 font-medium">Board-ready summary — readable in under 30 seconds</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* ── DECISIONS ─────────────────────────────────────────────── */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center">
              <TrendingUp className="h-4 w-4 text-cyan-400" />
            </div>
            <h3 className="text-sm font-bold text-white uppercase tracking-widest">Top Decisions</h3>
          </div>
          {decisions.map((d, i) => (
            <div key={i} className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4 hover:border-cyan-500/40 transition-all group">
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className="text-[11px] font-bold text-cyan-400/70 uppercase tracking-widest">D{i + 1}</span>
                <Badge className={`text-[10px] px-1.5 py-0.5 border ${urgencyColors[d.urgency] || urgencyColors.Medium}`}>
                  {d.urgency}
                </Badge>
              </div>
              <p className="text-sm font-semibold text-white leading-snug mb-2">{d.title}</p>
              <div className="flex items-center gap-1.5">
                <ArrowRight className="h-3 w-3 text-cyan-400/60 flex-shrink-0" />
                <p className="text-xs text-slate-400 leading-snug">{d.impact}</p>
              </div>
            </div>
          ))}
        </div>

        {/* ── RISKS ─────────────────────────────────────────────────── */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-red-500/15 border border-red-500/30 flex items-center justify-center">
              <AlertTriangle className="h-4 w-4 text-red-400" />
            </div>
            <h3 className="text-sm font-bold text-white uppercase tracking-widest">Top Risks</h3>
          </div>
          {risks.map((r, i) => (
            <div key={i} className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4 hover:border-red-500/40 transition-all">
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className="text-[11px] font-bold text-red-400/70 uppercase tracking-widest">R{i + 1}</span>
                <div className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${severityDot[r.severity] || severityDot.Medium}`} />
                  <span className="text-[10px] text-slate-400">{r.severity}</span>
                </div>
              </div>
              <p className="text-sm font-semibold text-white leading-snug mb-2">{r.title}</p>
              <div className="flex items-center gap-1.5">
                <TrendingDown className="h-3 w-3 text-red-400/60 flex-shrink-0" />
                <p className="text-xs text-slate-400 leading-snug">{r.financial_impact}</p>
              </div>
            </div>
          ))}
        </div>

        {/* ── ACTIONS ───────────────────────────────────────────────── */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
              <Zap className="h-4 w-4 text-emerald-400" />
            </div>
            <h3 className="text-sm font-bold text-white uppercase tracking-widest">Top Actions</h3>
          </div>
          {actions.map((a, i) => (
            <div key={i} className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4 hover:border-emerald-500/40 transition-all">
              <div className="flex items-start gap-2 mb-2">
                <span className="text-[11px] font-bold text-emerald-400/70 uppercase tracking-widest">A{i + 1}</span>
              </div>
              <p className="text-sm font-semibold text-white leading-snug mb-2">{a.title}</p>
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-1.5">
                  <CheckCircle className="h-3 w-3 text-emerald-400/60 flex-shrink-0" />
                  <span className="text-xs text-slate-400">{a.owner}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Clock className="h-3 w-3 text-slate-500 flex-shrink-0" />
                  <span className="text-xs text-slate-500">{a.timeline}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
};

export default CEOView;
