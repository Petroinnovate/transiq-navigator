// KPITracker – Tremor Tracker strip showing health status of each KPI
// Each KPI becomes a colored block; color encodes its status/changeType

import React from "react"
import { Tracker } from "@/components/tremor"

interface KPI {
  id: string
  title: string
  value: number
  unit: string
  changeType?: "positive" | "negative" | "neutral"
  status?: "good" | "warning" | "critical"
  target?: number
}

interface KPITrackerProps {
  kpis: KPI[]
}

function blockColor(kpi: KPI): string {
  if (kpi.status === "critical" || kpi.changeType === "negative") return "#f43f5e"
  if (kpi.status === "warning")  return "#f59e0b"
  if (kpi.status === "good" || kpi.changeType === "positive") {
    if (kpi.target && kpi.target > 0) {
      const pct = (kpi.value / kpi.target) * 100
      if (pct >= 100) return "#34d399"
      if (pct >= 75)  return "#22d3ee"
      if (pct >= 50)  return "#f59e0b"
      return "#f43f5e"
    }
    return "#34d399"
  }
  return "#64748b"
}

export const KPITracker: React.FC<KPITrackerProps> = ({ kpis }) => {
  if (!kpis || kpis.length === 0) return null

  const blocks = kpis.map((kpi) => ({
    color: blockColor(kpi),
    tooltip: `${kpi.title}: ${kpi.value}${kpi.unit ? " " + kpi.unit : ""}${kpi.status ? " [" + kpi.status + "]" : ""}`,
  }))

  // Pad to 24 blocks for a fuller visual
  const padCount = Math.max(0, 24 - blocks.length)
  const padded = [...blocks, ...Array.from({ length: padCount }, () => ({ color: "#1e293b", tooltip: "" }))]

  const onTarget  = blocks.filter((b) => b.color === "#34d399" || b.color === "#22d3ee").length
  const atRisk    = blocks.filter((b) => b.color === "#f59e0b").length
  const critical  = blocks.filter((b) => b.color === "#f43f5e").length

  return (
    <div className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-6">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-base font-semibold text-slate-200">KPI Health Tracker</h3>
        <div className="flex items-center gap-3 text-[10px] text-slate-400">
          <span><span className="inline-block w-2 h-2 rounded-sm bg-emerald-400 mr-1" />On-target ({onTarget})</span>
          <span><span className="inline-block w-2 h-2 rounded-sm bg-amber-400 mr-1" />At-risk ({atRisk})</span>
          <span><span className="inline-block w-2 h-2 rounded-sm bg-rose-500 mr-1" />Critical ({critical})</span>
        </div>
      </div>
      <Tracker data={padded} />
    </div>
  )
}
