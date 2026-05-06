import React, { useState } from 'react';
import { FolderOpen, X, ChevronDown, ChevronUp, CheckCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { ProjectMeta } from '@/contexts/DashboardContext';

interface ProjectBannerProps {
  meta: ProjectMeta;
}

const ProjectBanner: React.FC<ProjectBannerProps> = ({ meta }) => {
  const [dismissed, setDismissed] = useState(false);
  const [expanded, setExpanded] = useState(false);

  if (dismissed) return null;
  if (meta.filesProcessed <= 1 && meta.batchesProcessed <= 1) return null;

  const subtitle =
    meta.message ||
    `Unified master dashboard synthesised across ${meta.filesProcessed} documents`;

  const batches = Array.from({ length: meta.batchesProcessed }, (_, i) => i + 1);

  return (
    <div className="relative rounded-xl border border-purple-500/30 bg-gradient-to-r from-purple-900/30 via-slate-800/60 to-purple-900/20 px-5 py-4 overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 via-transparent to-violet-500/5 pointer-events-none" />

      {/* Dismiss button */}
      <button
        onClick={() => setDismissed(true)}
        className="absolute top-3 right-3 text-slate-500 hover:text-slate-300 transition-colors"
        aria-label="Dismiss project banner"
      >
        <X className="h-4 w-4" />
      </button>

      {/* Top row */}
      <div className="flex items-center gap-3 flex-wrap pr-6">
        <div className="w-8 h-8 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center flex-shrink-0">
          <FolderOpen className="h-4 w-4 text-purple-400" />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-white font-semibold text-sm">Project Analysis</span>
          <Badge className="bg-purple-500/20 text-purple-300 border-purple-500/40 text-xs">
            {meta.filesProcessed} Documents
          </Badge>
          <Badge className="bg-violet-500/20 text-violet-300 border-violet-500/40 text-xs">
            {meta.batchesProcessed} {meta.batchesProcessed === 1 ? 'Batch' : 'Batches'}
          </Badge>
        </div>
      </div>

      {/* Subtitle */}
      <p className="text-slate-400 text-xs mt-2 ml-11">{subtitle}</p>

      {/* Batch pills */}
      {meta.batchesProcessed > 1 && (
        <div className="mt-3 ml-11 flex flex-wrap gap-2">
          {batches.map(b => (
            <span
              key={b}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/25"
            >
              <CheckCircle className="h-3 w-3" />
              Batch {b}
            </span>
          ))}
        </div>
      )}

      {/* Expandable file list */}
      {meta.fileNames && meta.fileNames.length > 0 && (
        <div className="mt-3 ml-11">
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            {expanded ? 'Hide' : 'Show'} {meta.fileNames.length} file{meta.fileNames.length !== 1 ? 's' : ''}
          </button>
          {expanded && (
            <ul className="mt-2 space-y-1">
              {meta.fileNames.map((name, i) => (
                <li key={i} className="text-[11px] text-slate-400 flex items-center gap-2">
                  <span className="w-4 h-4 rounded bg-purple-500/15 flex items-center justify-center text-purple-400 font-mono text-[9px]">
                    {i + 1}
                  </span>
                  {name}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

export default ProjectBanner;
