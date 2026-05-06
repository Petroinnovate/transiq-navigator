import React from 'react'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  FileText,
  ChevronRight,
  AlertTriangle,
  TrendingUp,
  Shield,
} from 'lucide-react'
import type { SectionAnalysis } from '@/types/dashboard'

interface SectionNavProps {
  sections: SectionAnalysis[]
  activeSectionId: string | null
  onSectionClick: (sectionId: string) => void
}

const severityColor: Record<string, string> = {
  high: 'bg-red-500/20 text-red-400 border-red-500/30',
  medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  low: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
}

const confidenceColor = (c: number) =>
  c >= 0.8 ? 'text-emerald-400' : c >= 0.5 ? 'text-amber-400' : 'text-red-400'

const SectionNav: React.FC<SectionNavProps> = ({
  sections,
  activeSectionId,
  onSectionClick,
}) => {
  if (!sections || sections.length === 0) return null

  return (
    <div className="rounded-xl border border-white/10 bg-gradient-to-b from-slate-900/80 to-slate-950/80 backdrop-blur-xl">
      <div className="p-4 border-b border-white/10">
        <h3 className="text-sm font-semibold text-white/90 flex items-center gap-2">
          <FileText className="h-4 w-4 text-cyan-400" />
          Report Sections ({sections.length})
        </h3>
      </div>
      <ScrollArea className="max-h-[70vh]">
        <div className="p-2 space-y-1">
          {sections.map((section, idx) => {
            const isActive = section.sectionId === activeSectionId
            const highRisks = (section.risks || []).filter(
              (r) => r.severity === 'high'
            ).length
            const kpiCount = (section.kpis || []).length
            const findingCount = (section.keyFindings || []).length

            return (
              <button
                key={section.sectionId}
                onClick={() => onSectionClick(section.sectionId)}
                className={`w-full text-left px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                  isActive
                    ? 'bg-cyan-500/20 border border-cyan-500/40 text-white'
                    : 'hover:bg-white/5 border border-transparent text-white/70 hover:text-white'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-white/40">
                        {String(idx + 1).padStart(2, '0')}
                      </span>
                      <span className="text-sm font-medium truncate">
                        {section.title}
                      </span>
                    </div>
                    {section.pageRange && (
                      <span className="text-xs text-white/40 ml-6">
                        {section.pageRange}
                      </span>
                    )}
                  </div>
                  <ChevronRight
                    className={`h-4 w-4 flex-shrink-0 transition-transform ${
                      isActive ? 'rotate-90 text-cyan-400' : 'text-white/30'
                    }`}
                  />
                </div>
                {/* Mini stats row */}
                <div className="flex items-center gap-2 ml-6 mt-1">
                  {(section as any).tier && (
                    <Badge
                      variant="outline"
                      className={`text-[10px] px-1.5 py-0 ${
                        (section as any).tier === 1 ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
                          : (section as any).tier === 2 ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                          : 'bg-slate-600/20 text-slate-400 border-slate-600/40'
                      }`}
                    >
                      T{(section as any).tier}
                    </Badge>
                  )}
                  {(section as any).dmaicPhase && (section as any).dmaicPhase !== 'unassigned' && (section as any).dmaicPhase !== 'none' && (
                    <span className="text-[10px] font-medium uppercase text-violet-400">
                      {(section as any).dmaicPhase}
                    </span>
                  )}
                  {kpiCount > 0 && (
                    <span className="flex items-center gap-1 text-xs text-white/40">
                      <TrendingUp className="h-3 w-3" />
                      {kpiCount}
                    </span>
                  )}
                  {findingCount > 0 && (
                    <span className="flex items-center gap-1 text-xs text-white/40">
                      <FileText className="h-3 w-3" />
                      {findingCount}
                    </span>
                  )}
                  {highRisks > 0 && (
                    <Badge
                      variant="outline"
                      className={`text-[10px] px-1.5 py-0 ${severityColor.high}`}
                    >
                      <AlertTriangle className="h-2.5 w-2.5 mr-0.5" />
                      {highRisks}
                    </Badge>
                  )}
                  <span
                    className={`text-[10px] ml-auto ${confidenceColor(
                      section.confidence ?? 0
                    )}`}
                  >
                    {Math.round((section.confidence ?? 0) * 100)}%
                  </span>
                </div>
              </button>
            )
          })}
        </div>
      </ScrollArea>
    </div>
  )
}

export default SectionNav
