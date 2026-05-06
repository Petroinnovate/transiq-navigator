import React from 'react';
import { LayoutDashboard, GitCompare, FileText, Target } from 'lucide-react';

export type ViewMode = 'aggregate' | 'compare' | 'document' | 'benchmark';

interface ViewModeToggleProps {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
}

const MODES: { key: ViewMode; label: string; icon: React.FC<{ className?: string }>; desc: string }[] = [
  { key: 'aggregate',  label: 'Aggregate',      icon: LayoutDashboard, desc: 'Unified master dashboard' },
  { key: 'compare',   label: 'Compare',         icon: GitCompare,      desc: 'KPIs side-by-side per document' },
  { key: 'document',  label: 'Per Document',    icon: FileText,        desc: 'Drill into individual files' },
  { key: 'benchmark', label: 'Benchmark',       icon: Target,          desc: 'Six Sigma standard comparison' },
];

const ViewModeToggle: React.FC<ViewModeToggleProps> = ({ mode, onChange }) => {
  return (
    <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-800/60 border border-slate-700/50 w-fit flex-wrap">
      {MODES.map(m => {
        const Icon = m.icon;
        const active = mode === m.key;
        return (
          <button
            key={m.key}
            onClick={() => onChange(m.key)}
            title={m.desc}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 ${
              active
                ? 'bg-gradient-to-r from-cyan-500/20 to-teal-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/40'
            }`}
          >
            <Icon className={`h-3.5 w-3.5 ${active ? 'text-cyan-400' : ''}`} />
            {m.label}
          </button>
        );
      })}
    </div>
  );
};

export default ViewModeToggle;
