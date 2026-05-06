/**
 * ExplainabilityAuditTrail — PILLAR 3 of TransIQ's Industrial Decision OS
 *
 * Renders per-decision audit cards showing: Why · Data Used · Method · Assumptions · Limitations
 * Guarantees every AI recommendation can be traced, challenged, and justified by any stakeholder.
 */
import React, { useState } from 'react';
import { ShieldCheck, Database, FlaskConical, AlertTriangle, BookOpen, ChevronDown, ChevronUp } from 'lucide-react';

interface AuditEntry {
  decision_title: string;
  why: string;
  data_sources: string[];
  method: string;
  assumptions: string[];
  limitations: string[];
  confidence?: string;
}

interface ExplainabilityData {
  audit_trail?: AuditEntry[];
}

interface ExplainabilityAuditTrailProps {
  data: ExplainabilityData;
}

const FIELD_META = [
  { key: 'why',         label: 'Why This Decision',  icon: BookOpen,      color: 'text-cyan-400',    border: 'border-cyan-500/20',   bg: 'bg-cyan-500/5' },
  { key: 'data_sources',label: 'Data Used',           icon: Database,      color: 'text-violet-400',  border: 'border-violet-500/20', bg: 'bg-violet-500/5' },
  { key: 'method',      label: 'Method / Model',      icon: FlaskConical,  color: 'text-emerald-400', border: 'border-emerald-500/20',bg: 'bg-emerald-500/5' },
  { key: 'assumptions', label: 'Assumptions',         icon: ShieldCheck,   color: 'text-amber-400',   border: 'border-amber-500/20',  bg: 'bg-amber-500/5' },
  { key: 'limitations', label: 'Limitations',         icon: AlertTriangle, color: 'text-red-400',     border: 'border-red-500/20',    bg: 'bg-red-500/5' },
] as const;

type FieldKey = typeof FIELD_META[number]['key'];

const AuditCard: React.FC<{ entry: AuditEntry; index: number }> = ({ entry, index }) => {
  const [open, setOpen] = useState(index === 0);

  return (
    <div className="rounded-xl border border-slate-700/50 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setOpen(p => !p)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-slate-800/60 hover:bg-slate-800/90 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-bold text-slate-500 tabular-nums">
            #{String(index + 1).padStart(2, '0')}
          </span>
          <span className="text-sm font-semibold text-white">{entry.decision_title}</span>
          {entry.confidence && (
            <span className="ml-2 px-2 py-0.5 rounded-full text-[10px] font-medium border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
              Confidence: {entry.confidence}
            </span>
          )}
        </div>
        {open ? (
          <ChevronUp className="h-4 w-4 text-slate-400 flex-shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 text-slate-400 flex-shrink-0" />
        )}
      </button>

      {/* Body */}
      {open && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-slate-700/30">
          {FIELD_META.map(({ key, label, icon: Icon, color, border, bg }) => {
            const raw = entry[key as FieldKey];
            const items: string[] = Array.isArray(raw) ? raw : raw ? [raw as string] : [];
            if (!items.length) return null;

            return (
              <div key={key} className={`p-4 ${bg} border-b ${border}`}>
                <div className="flex items-center gap-2 mb-2.5">
                  <Icon className={`h-3.5 w-3.5 ${color}`} />
                  <span className={`text-[10px] font-bold uppercase tracking-widest ${color}`}>{label}</span>
                </div>
                {items.length === 1 ? (
                  <p className="text-xs text-slate-300 leading-relaxed">{items[0]}</p>
                ) : (
                  <ul className="space-y-1.5">
                    {items.map((item, i) => (
                      <li key={i} className="text-xs text-slate-300 flex gap-2">
                        <span className="text-slate-600 flex-shrink-0 mt-0.5">·</span>
                        <span className="leading-relaxed">{item}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const PLACEHOLDER_ENTRIES: AuditEntry[] = [
  {
    decision_title: 'Run multi-agent analysis to populate audit trail',
    why: 'Upload a document and run an analysis. Each decision produced by the Decision OS will appear here with full traceability — including the data used, statistical method, assumptions, and known limitations.',
    data_sources: ['Awaiting analysis output'],
    method: 'Six Sigma DMAIC + Gemini multi-agent orchestration',
    assumptions: ['Document is representative of the operational period described'],
    limitations: ['Accuracy depends on data completeness and quality score reported by the Data Interpreter agent'],
    confidence: 'N/A',
  },
];

const ExplainabilityAuditTrail: React.FC<ExplainabilityAuditTrailProps> = ({ data }) => {
  const entries = data?.audit_trail?.length ? data.audit_trail : PLACEHOLDER_ENTRIES;
  const isLive = !!(data?.audit_trail?.length);

  return (
    <div className="space-y-5">
      {/* ── Section banner ──────────────────────────────────────────── */}
      <div className="flex items-start gap-4 p-4 rounded-xl border border-violet-500/20 bg-violet-500/5">
        <div className="w-9 h-9 rounded-lg bg-violet-500/20 border border-violet-500/30 flex items-center justify-center flex-shrink-0">
          <ShieldCheck className="h-4.5 w-4.5 text-violet-400" />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">Fully Explainable &amp; Auditable AI</p>
          <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
            Every AI decision is traceable to its data source, statistical method, and key assumptions.
            Designed for regulatory review, board scrutiny, and safety-critical sign-off.
          </p>
        </div>
        <div className="ml-auto flex-shrink-0 flex items-center gap-1.5 rounded-full px-3 py-1 border border-violet-500/30 bg-violet-500/10">
          {isLive && <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />}
          <span className="text-[10px] text-violet-400 font-medium uppercase tracking-wider">
            {isLive ? `${entries.length} Decision${entries.length !== 1 ? 's' : ''} Traced` : 'Awaiting Data'}
          </span>
        </div>
      </div>

      {/* ── Audit cards ─────────────────────────────────────────────── */}
      <div className="space-y-3">
        {entries.map((entry, i) => (
          <AuditCard key={i} entry={entry} index={i} />
        ))}
      </div>
    </div>
  );
};

export default ExplainabilityAuditTrail;
