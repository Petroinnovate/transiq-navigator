// CategoryBar – segmented proportion bar
// Adapted from Tremor source for TransIQ dark dashboard

import React, { forwardRef } from "react"
import { cx } from "./utils/cx"
import type { AvailableChartColorsKeys } from "./utils/chartColors"
import { getColorHex } from "./utils/chartColors"

interface CategoryBarProps {
  values: number[]
  colors?: AvailableChartColorsKeys[]
  labels?: string[]
  showLabels?: boolean
  className?: string
}

const defaultColors: AvailableChartColorsKeys[] = [
  "cyan", "emerald", "violet", "amber", "rose", "teal", "blue", "orange",
]

const CategoryBar = forwardRef<HTMLDivElement, CategoryBarProps>(
  (
    {
      values = [],
      colors = defaultColors,
      labels = [],
      showLabels = false,
      className,
    },
    forwardedRef,
  ) => {
    const total = values.reduce((a, b) => a + b, 0)
    if (total === 0) return null

    const percents = values.map((v) => (v / total) * 100)

    return (
      <div ref={forwardedRef} className={cx("space-y-2", className)}>
        {/* Bar */}
        <div className="flex h-3 w-full overflow-hidden rounded-full">
          {percents.map((pct, i) => (
            <div
              key={i}
              className="transition-all duration-700"
              style={{
                width: `${pct}%`,
                backgroundColor: getColorHex((colors[i % colors.length]) as AvailableChartColorsKeys),
              }}
              title={labels[i] ? `${labels[i]}: ${pct.toFixed(1)}%` : `${pct.toFixed(1)}%`}
            />
          ))}
        </div>

        {/* Labels */}
        {showLabels && labels.length > 0 && (
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {labels.map((label, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
                  style={{
                    backgroundColor: getColorHex((colors[i % colors.length]) as AvailableChartColorsKeys),
                  }}
                />
                <span className="text-xs text-slate-400 truncate max-w-[12rem]"
                  title={label}
                >
                  {label} ({percents[i].toFixed(0)}%)
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  },
)

CategoryBar.displayName = "CategoryBar"

export { CategoryBar }
export type { CategoryBarProps }
