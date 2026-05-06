// OptimizationCategoryBar – Tremor CategoryBar showing savings breakdown by impact level
// Placed below the existing OptimizationSuggestions section

import React from "react"
import { CategoryBar } from "@/components/tremor"
import type { AvailableChartColorsKeys } from "@/components/tremor"

interface OptimizationSuggestion {
  id: string
  title: string
  impact: "high" | "medium" | "low"
  savings: {
    value: number
    unit: string
    percentage: string
  }
}

interface OptimizationCategoryBarProps {
  suggestions: OptimizationSuggestion[]
}

const impactColor: Record<string, AvailableChartColorsKeys> = {
  high:   "emerald",
  medium: "amber",
  low:    "sky",
}

export const OptimizationCategoryBar: React.FC<OptimizationCategoryBarProps> = ({
  suggestions,
}) => {
  // Only include suggestions with a numeric savings value
  const withSavings = suggestions.filter((s) => s.savings?.value > 0)
  if (withSavings.length < 2) return null

  const values = withSavings.map((s) => s.savings.value)
  const colors = withSavings.map((s) => impactColor[s.impact] ?? "sky")
  const labels = withSavings.map(
    (s) => `${s.title.slice(0, 28)}${s.title.length > 28 ? "…" : ""} (${s.savings.unit}${s.savings.value.toLocaleString()})`,
  )
  const total = values.reduce((a, b) => a + b, 0)

  return (
    <div className="rounded-2xl border border-emerald-500/20 bg-slate-800/30 p-6">
      <div className="flex items-center gap-2 mb-1">
        <h3 className="text-base font-semibold text-slate-200">Savings Distribution</h3>
        <span className="text-xs px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          Total: {suggestions[0]?.savings.unit}{total.toLocaleString()}
        </span>
      </div>
      <p className="text-xs text-slate-500 mb-4">
        Share of total potential savings by each optimization opportunity
      </p>
      <CategoryBar
        values={values}
        colors={colors}
        labels={labels}
        showLabels
      />
    </div>
  )
}
