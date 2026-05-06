// ============================================================================
// DocumentTabs.tsx — Per-document drill-down tab view
// ============================================================================

import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { FileText, ChevronRight, Activity, Layers, TrendingUp } from 'lucide-react'
import { DocumentResult } from '@/contexts/DashboardContext'

interface Props {
  documents: DocumentResult[]
}

const DMAIC_PHASES = ['define', 'measure', 'analyze', 'improve', 'control'] as const
const PHASE_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  define:   { text: 'text-blue-400',    bg: 'bg-blue-500/10',    border: 'border-blue-500/30'    },
  measure:  { text: 'text-teal-400',    bg: 'bg-teal-500/10',    border: 'border-teal-500/30'    },
  analyze:  { text: 'text-violet-400',  bg: 'bg-violet-500/10',  border: 'border-violet-500/30'  },
  improve:  { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  control:  { text: 'text-amber-400',   bg: 'bg-amber-500/10',   border: 'border-amber-500/30'   },
}

const DocumentTabs: React.FC<Props> = ({ documents }) => {
  const [activeIdx, setActiveIdx] = useState(0)

  if (!documents || documents.length === 0) return null

  const activeDoc = documents[activeIdx]

  return (
    <div className="space-y-4">
      {/* Tab bar */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {documents.map((doc, i) => (
          <button
            key={doc.id || i}
            onClick={() => setActiveIdx(i)}
            className={[
              'flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium whitespace-nowrap transition-all duration-150 flex-shrink-0',
              i === activeIdx
                ? 'bg-gradient-to-r from-cyan-500/20 to-teal-500/20 border-cyan-500/50 text-cyan-300 shadow-lg shadow-cyan-500/10'
                : 'bg-slate-800/40 border-slate-700/40 text-slate-400 hover:text-slate-200 hover:border-slate-600/60',
            ].join(' ')}
          >
            <FileText className="h-3.5 w-3.5 flex-shrink-0" />
            <span className="max-w-[160px] truncate" title={doc.name}>{doc.name}</span>
            {i === activeIdx && <ChevronRight className="h-3 w-3 text-cyan-400" />}
          </button>
        ))}
      </div>

      {/* Document content */}
      {activeDoc && (
        <div className="space-y-5">
          {/* KPIs */}
          {activeDoc.kpis && activeDoc.kpis.length > 0 && (
            <Card className="bg-slate-800/40 border-slate-700/40">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-white text-base">
                  <Activity className="h-4 w-4 text-cyan-400" />
                  Key Performance Indicators
                  <Badge className="ml-auto text-[10px] bg-cyan-500/10 border-cyan-500/30 text-cyan-400">
                    {activeDoc.kpis.length} KPIs
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                  {activeDoc.kpis.map((kpi, i) => (
                    <div
                      key={i}
                      className="bg-slate-900/50 border border-slate-700/50 rounded-lg p-3 hover:border-cyan-500/30 transition-colors"
                    >
                      <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 truncate" title={kpi.title}>
                        {kpi.title}
                      </p>
                      <p className="text-lg font-bold text-white leading-tight">
                        {kpi.value !== null && kpi.value !== undefined
                          ? typeof kpi.value === 'object'
                            ? JSON.stringify(kpi.value)
                            : String(kpi.value)
                          : '—'}
                        {kpi.unit ? <span className="text-xs text-slate-400 ml-0.5">{kpi.unit}</span> : null}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* DMAIC Phases */}
          {activeDoc.dmaic && Object.values(activeDoc.dmaic).some(Boolean) && (
            <Card className="bg-slate-800/40 border-slate-700/40">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-white text-base">
                  <Layers className="h-4 w-4 text-violet-400" />
                  DMAIC Analysis
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {DMAIC_PHASES.map(phase => {
                    const rawText = activeDoc.dmaic?.[phase]
                    // Coerce to string — guard against object values stored from old data
                    const text: string = typeof rawText === 'string'
                      ? rawText
                      : rawText && typeof rawText === 'object'
                      ? Object.values(rawText as Record<string, unknown>)
                          .filter((v): v is string => typeof v === 'string' && Boolean(v))
                          .slice(0, 3)
                          .join(' — ')
                      : ''
                    if (!text) return null
                    const colors = PHASE_COLORS[phase]
                    return (
                      <div
                        key={phase}
                        className={`rounded-lg border p-3 ${colors.bg} ${colors.border}`}
                      >
                        <p className={`text-[10px] font-bold uppercase tracking-widest mb-1 ${colors.text}`}>
                          {phase}
                        </p>
                        <p className="text-sm text-slate-300 leading-relaxed">{text}</p>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Sections */}
          {activeDoc.sections && activeDoc.sections.length > 0 && (
            <Card className="bg-slate-800/40 border-slate-700/40">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-white text-base">
                  <TrendingUp className="h-4 w-4 text-teal-400" />
                  Report Sections
                  <Badge className="ml-auto text-[10px] bg-teal-500/10 border-teal-500/30 text-teal-400">
                    {activeDoc.sections.length} sections
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {activeDoc.sections.map((sec, i) => {
                    const conf = typeof sec.confidence === 'number' ? sec.confidence : 0
                    const confPct = conf <= 1 ? Math.round(conf * 100) : Math.round(conf)
                    const confColor =
                      confPct >= 70 ? 'text-emerald-400' : confPct >= 40 ? 'text-amber-400' : 'text-red-400'
                    return (
                      <div
                        key={i}
                        className="bg-slate-900/40 border border-slate-700/40 rounded-lg p-3 hover:border-teal-500/30 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-3 mb-1">
                          <p className="text-sm font-semibold text-white leading-snug">{sec.title}</p>
                          <span className={`text-[11px] font-semibold flex-shrink-0 ${confColor}`}>
                            {confPct}%
                          </span>
                        </div>
                        {sec.summary && (
                          <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">{sec.summary}</p>
                        )}
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Empty state */}
          {(!activeDoc.kpis || activeDoc.kpis.length === 0) &&
            (!activeDoc.dmaic || !Object.values(activeDoc.dmaic).some(Boolean)) &&
            (!activeDoc.sections || activeDoc.sections.length === 0) && (
              <div className="text-center py-12 text-slate-500">
                <FileText className="h-10 w-10 mx-auto mb-3 opacity-40" />
                <p className="text-sm">No detailed data available for this document.</p>
              </div>
            )}
        </div>
      )}
    </div>
  )
}

export default DocumentTabs
