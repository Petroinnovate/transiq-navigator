// Tracker – timeline block strip for operational status
// Adapted from Tremor source for TransIQ dark dashboard

import React, { forwardRef } from "react"
import { cx } from "./utils/cx"

interface TrackerBlock {
  color?: string        // hex colour string e.g. "#34d399"
  tooltip?: string
  defaultColor?: string
}

interface TrackerProps {
  data: TrackerBlock[]
  className?: string
}

const Tracker = forwardRef<HTMLDivElement, TrackerProps>(
  ({ data = [], className }, forwardedRef) => {
    return (
      <div
        ref={forwardedRef}
        className={cx("flex items-center gap-0.5 h-10", className)}
        role="img"
      >
        {data.map((block, index) => (
          <div
            key={index}
            title={block.tooltip || ""}
            className="group relative h-full flex-1 rounded-sm transition-opacity hover:opacity-80 cursor-default"
            style={{
              backgroundColor: block.color ?? block.defaultColor ?? "#334155",
              minWidth: 4,
            }}
          >
            {block.tooltip && (
              <div
                className="absolute bottom-full left-1/2 z-10 mb-1 hidden -translate-x-1/2
                           whitespace-nowrap rounded bg-slate-800 border border-slate-600
                           px-2 py-1 text-xs text-slate-200 shadow-lg group-hover:block"
              >
                {block.tooltip}
              </div>
            )}
          </div>
        ))}
      </div>
    )
  },
)

Tracker.displayName = "Tracker"

export { Tracker }
export type { TrackerBlock, TrackerProps }
