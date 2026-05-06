// KPIProgressCircles – Tremor ProgressCircle gauges for KPI target achievement
// Shows how far each KPI is toward its target

import React from "react"
import { ProgressCircle } from "@/components/tremor"
import type { ProgressCircleVariant } from "@/components/tremor"

interface KPI {
  id: string
  title: string
  value: number
  unit: string
  target?: number
  changeType?: "positive" | "negative" | "neutral"
  status?: "good" | "warning" | "critical"
}

interface KPIProgressCirclesProps {
  kpis: KPI[]
}

function pickVariant(pct: number, changeType?: string, status?: string): ProgressCircleVariant {
  if (status === "critical") return "error"
  if (status === "warning")  return "warning"
  if (status === "good")     return "success"
  if (changeType === "negative") return "error"
  if (pct >= 100) return "success"
  if (pct >= 75)  return "default"
  if (pct >= 50)  return "warning"
  return "error"
}

const formatVal = (v: number, unit: string) => {
  if (unit === "%") return `${v}%`
  if (unit === "$" || unit === "USD") {
    if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
    if (v >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`
    return `$${v}`
  }
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000)     return `${(v / 1_000).toFixed(0)}K`
  return String(v)
}

export const KPIProgressCircles: React.FC<KPIProgressCirclesProps> = ({ kpis }) => {
  const kpisWithTarget = kpis.filter((k) => k.target && k.target > 0)
  if (kpisWithTarget.length === 0) return null

  return (
    <div className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-6">
      <h3 className="text-base font-semibold text-slate-200 mb-5">KPI Target Achievement</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-6">
        {kpisWithTarget.map((kpi) => {
          const pct = Math.round((kpi.value / kpi.target!) * 100)
          const variant = pickVariant(pct, kpi.changeType, kpi.status)
          return (
            <div key={kpi.id} className="flex flex-col items-center gap-2 text-center">
              <ProgressCircle value={Math.min(pct, 100)} max={100} radius={36} strokeWidth={5} variant={variant}>
                <span className="text-xs font-bold text-slate-100">{pct}%</span>
              </ProgressCircle>
              <div>
                <div className="text-xs font-semibold text-slate-200 truncate max-w-[80px]" title={kpi.title}>
                  {kpi.title.length > 14 ? kpi.title.slice(0, 13) + "…" : kpi.title}
                </div>
                <div className="text-[10px] text-slate-500">
                  {formatVal(kpi.value, kpi.unit)} / {formatVal(kpi.target!, kpi.unit)}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
