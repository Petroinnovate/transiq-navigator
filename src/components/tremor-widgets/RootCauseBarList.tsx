// RootCauseBarList – Tremor BarList ranked view of root causes
// Reads from sixSigmaData.rootCauses (string[] in the inner project schema)

import React from "react"
import { BarList } from "@/components/tremor"

interface RootCauseBarListProps {
  rootCauses: string[]
}

// Assigns a synthetic "weight" to each cause based on its order
// (first = most impactful = 100, last = least)
function buildBarData(causes: string[]) {
  return causes.map((cause, i) => ({
    name: cause.length > 70 ? cause.slice(0, 68) + "…" : cause,
    value: Math.max(100 - i * Math.floor(80 / Math.max(causes.length - 1, 1)), 10),
    color: i === 0 ? "rgba(244,63,94,0.3)" : i === 1 ? "rgba(251,146,60,0.25)" : "rgba(6,182,212,0.2)",
  }))
}

export const RootCauseBarList: React.FC<RootCauseBarListProps> = ({ rootCauses }) => {
  if (!rootCauses || rootCauses.length === 0) return null

  const data = buildBarData(rootCauses)

  return (
    <div className="rounded-2xl border border-violet-500/20 bg-slate-800/30 p-6">
      <div className="flex items-center gap-2 mb-1">
        <h3 className="text-base font-semibold text-slate-200">Root Cause Ranking</h3>
        <span className="text-xs px-1.5 py-0.5 rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/30">
          Six Sigma · Analyze
        </span>
      </div>
      <p className="text-xs text-slate-500 mb-5">
        Pareto ranking — top drivers ordered by estimated impact
      </p>
      <BarList
        data={data}
        valueFormatter={(v) => `${v}% impact`}
        sortOrder="none"
        showAnimation
      />
    </div>
  )
}
