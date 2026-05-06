// ============================================================================
// KPIComparisonTable.tsx — Cross-document KPI comparison table
// ============================================================================

import React, { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { GitCompare, AlertTriangle } from 'lucide-react'
import { DocumentResult } from '@/contexts/DashboardContext'
import { parseKPIValue, detectVariance } from '@/utils/benchmarkUtils'

interface Props {
  documents: DocumentResult[]
}

interface KPIRow {
  name: string
  values: (string | number | null)[]
  numericValues: (number | null)[]
  average: number | null
  hasVariance: boolean
}

const KPIComparisonTable: React.FC<Props> = ({ documents }) => {
  if (!documents || documents.length === 0) return null

  const rows = useMemo((): KPIRow[] => {
    // Collect all unique KPI names across all documents (order: by first document)
    const allNames: string[] = []
    const seen = new Set<string>()
    documents.forEach(doc => {
      ;(doc.kpis || []).forEach(kpi => {
        const key = (kpi.title || '').toLowerCase().trim()
        if (!seen.has(key)) {
          seen.add(key)
          allNames.push(kpi.title)
        }
      })
    })

    return allNames.map(name => {
      const key = name.toLowerCase().trim()
      const values: (string | number | null)[] = documents.map(doc => {
        const found = (doc.kpis || []).find(k => (k.title || '').toLowerCase().trim() === key)
        return found ? found.value : null
      })
      const numericValues = values.map(v => (v !== null ? parseKPIValue(v) : null))
      const validNums = numericValues.filter((n): n is number => n !== null)
      const average = validNums.length > 0 ? validNums.reduce((a, b) => a + b, 0) / validNums.length : null
      const hasVariance = detectVariance(validNums)
      return { name, values, numericValues, average, hasVariance }
    })
  }, [documents])

  const formatValue = (val: string | number | null): string => {
    if (val === null || val === undefined) return '—'
    return String(val)
  }

  const formatAvg = (avg: number | null): string => {
    if (avg === null) return '—'
    if (Math.abs(avg) >= 1000000) return `${(avg / 1000000).toFixed(2)}M`
    if (Math.abs(avg) >= 1000) return `${(avg / 1000).toFixed(1)}K`
    return avg % 1 === 0 ? String(avg) : avg.toFixed(2)
  }

  return (
    <Card className="bg-slate-800/40 border-slate-700/40">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-3 text-white">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center">
            <GitCompare className="h-4 w-4 text-cyan-400" />
          </div>
          KPI Comparison — {documents.length} Documents
        </CardTitle>
        <p className="text-sm text-slate-400 mt-1">
          Compare metrics across all analysed documents. Highlighted rows indicate &gt;30% variance.
        </p>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">No KPI data available for comparison.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/60 bg-slate-800/60">
                  <th className="text-left px-4 py-3 text-slate-400 font-medium min-w-[180px]">KPI</th>
                  {documents.map((doc, i) => (
                    <th
                      key={doc.id || i}
                      className="text-right px-4 py-3 text-slate-400 font-medium whitespace-nowrap max-w-[160px]"
                    >
                      <span className="block truncate" title={doc.name}>
                        {doc.name.length > 20 ? doc.name.slice(0, 18) + '…' : doc.name}
                      </span>
                    </th>
                  ))}
                  <th className="text-right px-4 py-3 text-cyan-400 font-semibold whitespace-nowrap">
                    Average
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => (
                  <tr
                    key={row.name}
                    className={[
                      'border-b border-slate-700/30 transition-colors',
                      row.hasVariance
                        ? 'bg-amber-500/5 hover:bg-amber-500/10'
                        : idx % 2 === 0
                        ? 'bg-slate-800/20 hover:bg-slate-700/20'
                        : 'hover:bg-slate-700/20',
                    ].join(' ')}
                  >
                    <td className="px-4 py-2.5 text-slate-200 font-medium">
                      <div className="flex items-center gap-2">
                        {row.hasVariance && (
                          <span title="High variance across documents (>30%)">
                            <AlertTriangle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" />
                          </span>
                        )}
                        {row.name}
                      </div>
                    </td>
                    {row.values.map((val, vi) => (
                      <td
                        key={vi}
                        className={`px-4 py-2.5 text-right tabular-nums ${
                          val === null ? 'text-slate-600 italic' : 'text-slate-100'
                        }`}
                      >
                        {formatValue(val)}
                      </td>
                    ))}
                    <td className="px-4 py-2.5 text-right tabular-nums font-semibold text-cyan-400">
                      {formatAvg(row.average)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Legend */}
        <div className="flex items-center gap-4 mt-4 text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <AlertTriangle className="h-3 w-3 text-amber-400" />
            <span>High variance (&gt;30% spread)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-600 italic">—</span>
            <span>Not present in this document</span>
          </div>
          <Badge className="ml-auto text-[10px] bg-cyan-500/10 border-cyan-500/30 text-cyan-400">
            {rows.length} KPIs · {documents.length} docs
          </Badge>
        </div>
      </CardContent>
    </Card>
  )
}

export default KPIComparisonTable
