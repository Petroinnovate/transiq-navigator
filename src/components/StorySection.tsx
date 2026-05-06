import React from 'react';
import { Activity, Target, BarChart3, Search, TrendingUp, Shield } from 'lucide-react';
import type { StoryBlock, StoryIcon } from '@/types/widget';
import ChartRenderer from './ChartRenderer';

interface StorySectionProps {
  block: StoryBlock;
}

const PHASE_STYLES: Record<string, { border: string; badge: string; icon: string; accent: string }> = {
  exec:    { border: 'border-cyan-500/30',    badge: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/25',    icon: 'text-cyan-400',    accent: 'from-cyan-500/10' },
  define:  { border: 'border-blue-500/30',    badge: 'bg-blue-500/15 text-blue-300 border-blue-500/25',    icon: 'text-blue-400',    accent: 'from-blue-500/10' },
  measure: { border: 'border-teal-500/30',    badge: 'bg-teal-500/15 text-teal-300 border-teal-500/25',    icon: 'text-teal-400',    accent: 'from-teal-500/10' },
  analyze: { border: 'border-violet-500/30',  badge: 'bg-violet-500/15 text-violet-300 border-violet-500/25', icon: 'text-violet-400', accent: 'from-violet-500/10' },
  improve: { border: 'border-emerald-500/30', badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25', icon: 'text-emerald-400', accent: 'from-emerald-500/10' },
  control: { border: 'border-amber-500/30',   badge: 'bg-amber-500/15 text-amber-300 border-amber-500/25',   icon: 'text-amber-400',   accent: 'from-amber-500/10' },
};

const PHASE_LABELS: Record<string, string> = {
  exec:    'EXECUTIVE',
  define:  'DEFINE',
  measure: 'MEASURE',
  analyze: 'ANALYZE',
  improve: 'IMPROVE',
  control: 'CONTROL',
};

const ICON_MAP: Record<StoryIcon, React.FC<{ className?: string }>> = {
  'activity':    Activity,
  'target':      Target,
  'bar-chart':   BarChart3,
  'search':      Search,
  'trending-up': TrendingUp,
  'shield':      Shield,
};

const SIZE_MAP: Record<string, string> = {
  large:  'col-span-12',
  medium: 'col-span-12 lg:col-span-6',
  small:  'col-span-12 lg:col-span-4',
};

const StorySection: React.FC<StorySectionProps> = ({ block }) => {
  const style = PHASE_STYLES[block.phase] ?? PHASE_STYLES.exec;
  const Icon = ICON_MAP[block.icon] ?? Activity;

  return (
    <div className={`rounded-2xl border ${style.border} bg-slate-800/40 backdrop-blur-sm overflow-hidden`}>
      {/* Phase accent strip */}
      <div className={`h-0.5 bg-gradient-to-r ${style.accent} to-transparent`} />

      <div className="p-6">
        {/* Header */}
        <div className="flex items-start gap-4 mb-4">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${style.badge} border`}
          >
            <Icon className={`h-5 w-5 ${style.icon}`} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[10px] font-bold tracking-widest uppercase ${style.icon} opacity-70`}>
                {PHASE_LABELS[block.phase] ?? block.phase.toUpperCase()}
              </span>
            </div>
            <h2 className="text-lg font-semibold text-white leading-tight">{block.title}</h2>
          </div>
        </div>

        {/* Narrative */}
        {block.narrative && (
          <div className={`rounded-xl border ${style.border} bg-slate-900/40 px-4 py-3 mb-5`}>
            <p className="text-sm text-slate-300 leading-relaxed">{block.narrative}</p>
          </div>
        )}

        {/* Widget grid */}
        {block.widgets.length > 0 && (
          <div className="grid grid-cols-12 gap-4">
            {block.widgets.map(widget => (
              <div key={`${block.id}__${widget.id}`} className={SIZE_MAP[widget.size] ?? 'col-span-12'}>
                <ChartRenderer widget={widget} />
              </div>
            ))}
          </div>
        )}

        {/* Empty state when no widgets but block exists for narrative only */}
        {block.widgets.length === 0 && (
          <div className={`rounded-xl border border-dashed ${style.border} px-4 py-6 text-center`}>
            <p className="text-sm text-slate-500">No chart data available for this phase yet.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default StorySection;
