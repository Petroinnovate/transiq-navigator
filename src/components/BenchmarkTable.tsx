// ============================================================================
// BenchmarkTable.tsx — Six Sigma benchmark evaluation table
// ============================================================================

import React, { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Target } from 'lucide-react'
import { DocumentResult } from '@/contexts/DashboardContext'
import {
  normalizeKPI,
  evaluateKPI,
  parseKPIValue,
  SIX_SIGMA_BENCHMARKS,
  BenchmarkResult,
  statusColors,
} from '@/utils/benchmarkUtils'

interface Props {
  documents: DocumentResult[]
}

interface BenchmarkRow {
  kpiName: string
  canonical: string
  values: (string | number | null)[]
  results: (BenchmarkResult | null)[]
  benchmarkLabel: string
}

const StatusBadge: React.FC<{ result: BenchmarkResult | null; value: string | number | null }> = ({
  result,
  value,
}) => {
  if (value === null) return <span className="text-slate-600 italic text-xs">—</span>
  if (!result) {
    return <span className="text-slate-300 tabular-nums text-xs">{String(value)}</span>
  }
  const c = statusColors[result.status]
  const emoji = result.status === 'good' ? '🟢' : result.status === 'warning' ? '🟡' : '🔴'
  return (
    <div className="flex items-center justify-end gap-1.5" title={result.message}>
      <span className="text-slate-200 tabular-nums text-xs">{String(value)}</span>
      <span className="text-base leading-none" aria-label={result.status}>{emoji}</span>
    </div>
  )
}

const BenchmarkTable: React.FC<Props> = ({ documents }) => {
  if (!documents || documents.length === 0) return null

  const rows = useMemo((): BenchmarkRow[] => {
    // Gather all KPIs that have a recognized benchmark
    const seen = new Set<string>()
    const result: BenchmarkRow[] = []

    documents.forEach(doc => {
      ;(doc.kpis || []).forEach(kpi => {
        const canonical = normalizeKPI(kpi.title || '')
        if (!canonical) return
        if (!SIX_SIGMA_BENCHMARKS[canonical]) return
        if (seen.has(canonical)) return
        seen.add(canonical)

        const values: (string | number | null)[] = documents.map(d => {
          const found = (d.kpis || []).find(k => normalizeKPI(k.title || '') === canonical)
          return found ? found.value : null
        })

        const results: (BenchmarkResult | null)[] = values.map(v =>
          v !== null ? evaluateKPI(kpi.title, v) : null,
        )

        const spec = SIX_SIGMA_BENCHMARKS[canonical]
        result.push({
          kpiName: kpi.title,
          canonical,
          values,
          results,
          benchmarkLabel: spec.label,
        })
      })
    })

    return result
  }, [documents])

  // Summary stats
  const totalEvals = useMemo(() => {
    let good = 0, warning = 0, critical = 0
    rows.forEach(r => r.results.forEach(res => {
      if (!res) return
      if (res.status === 'good') good++
      else if (res.status === 'warning') warning++
      else critical++
    }))
    return { good, warning, critical }
  }, [rows])

  return (
    <Card className="bg-slate-800/40 border-slate-700/40">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <CardTitle className="flex items-center gap-3 text-white">
            <div className="w-8 h-8 rounded-lg bg-violet-500/15 border border-violet-500/30 flex items-center justify-center">
              <Target className="h-4 w-4 text-violet-400" />
            </div>
            Six Sigma Benchmark Evaluation
          </CardTitle>
          <div className="flex items-center gap-2 flex-wrap">
            {totalEvals.good > 0 && (
              <Badge className="bg-emerald-500/15 border-emerald-500/30 text-emerald-400 text-xs">
                🟢 {totalEvals.good} Good
              </Badge>
            )}
            {totalEvals.warning > 0 && (
              <Badge className="bg-amber-500/15 border-amber-500/30 text-amber-400 text-xs">
                🟡 {totalEvals.warning} Warning
              </Badge>
            )}
            {totalEvals.critical > 0 && (
              <Badge className="bg-red-500/15 border-red-500/30 text-red-400 text-xs">
                🔴 {totalEvals.critical} Critical
              </Badge>
            )}
          </div>
        </div>
        <p className="text-sm text-slate-400 mt-1">
          KPIs evaluated against Six Sigma world-class targets. Only metrics with recognized benchmarks are shown.
        </p>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <div className="text-center py-10 text-slate-500">
            <Target className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No KPIs matched Six Sigma benchmark definitions.</p>
            <p className="text-xs mt-1 text-slate-600">
              Recognized KPIs: Defect Rate, Cpk, DPMO, OEE, Yield, Sigma Level, CSAT, On-Time Delivery…
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/60 bg-slate-800/60">
                  <th className="text-left px-4 py-3 text-slate-400 font-medium min-w-[160px]">KPI</th>
                  {documents.map((doc, i) => (
                    <th
                      key={doc.id || i}
                      className="text-right px-4 py-3 text-slate-400 font-medium whitespace-nowrap"
                    >
                      <span className="block truncate max-w-[140px]" title={doc.name}>
                        {doc.name.length > 18 ? doc.name.slice(0, 16) + '…' : doc.name}
                      </span>
                    </th>
                  ))}
                  <th className="text-right px-4 py-3 text-violet-400 font-semibold whitespace-nowrap">
                    Target (6σ)
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => (
                  <tr
                    key={row.canonical}
                    className={[
                      'border-b border-slate-700/30 transition-colors',
                      idx % 2 === 0 ? 'bg-slate-800/20 hover:bg-slate-700/20' : 'hover:bg-slate-700/20',
                    ].join(' ')}
                  >
                    <td className="px-4 py-2.5 text-slate-200 font-medium">{row.kpiName}</td>
                    {row.values.map((val, vi) => (
                      <td key={vi} className="px-4 py-2.5 text-right">
                        <StatusBadge result={row.results[vi]} value={val} />
                      </td>
                    ))}
                    <td className="px-4 py-2.5 text-right">
                      <Badge className="bg-violet-500/10 border-violet-500/30 text-violet-300 text-[10px]">
                        {row.benchmarkLabel}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Legend */}
        <div className="flex items-center gap-4 mt-4 text-xs text-slate-500 flex-wrap">
          <span>🟢 At or above target</span>
          <span>🟡 Below target but within warning range</span>
          <span>🔴 Critical — far from target</span>
          <span className="text-slate-600 italic ml-auto">— not present in document</span>
        </div>
      </CardContent>
    </Card>
  )
}

export default BenchmarkTable
