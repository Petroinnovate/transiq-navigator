// ProgressCircle – circular SVG progress gauge
// Adapted from Tremor source for TransIQ dark dashboard

import React, { forwardRef } from "react"
import { cx } from "./utils/cx"

type ProgressCircleVariant = "default" | "neutral" | "warning" | "error" | "success"

interface ProgressCircleProps {
  value?: number
  max?: number
  radius?: number
  strokeWidth?: number
  variant?: ProgressCircleVariant
  children?: React.ReactNode
  className?: string
}

const variantColors: Record<ProgressCircleVariant, { track: string; fill: string }> = {
  default: { track: "stroke-slate-700",   fill: "stroke-cyan-400"    },
  neutral: { track: "stroke-slate-700",   fill: "stroke-slate-400"   },
  warning: { track: "stroke-slate-700",   fill: "stroke-amber-400"   },
  error:   { track: "stroke-slate-700",   fill: "stroke-rose-500"    },
  success: { track: "stroke-slate-700",   fill: "stroke-emerald-400" },
}

const ProgressCircle = forwardRef<HTMLDivElement, ProgressCircleProps>(
  (
    {
      value = 0,
      max = 100,
      radius = 32,
      strokeWidth = 6,
      variant = "default",
      children,
      className,
    },
    forwardedRef,
  ) => {
    const safeValue = Math.min(Math.max(value, 0), max)
    const normalizedRadius = radius - strokeWidth / 2
    const circumference = 2 * Math.PI * normalizedRadius
    const offset = circumference - (safeValue / max) * circumference
    const size = radius * 2

    const colors = variantColors[variant]

    return (
      <div
        ref={forwardedRef}
        className={cx("relative inline-flex items-center justify-center", className)}
      >
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          fill="none"
          style={{ transform: "rotate(-90deg)" }}
        >
          {/* Track */}
          <circle
            cx={radius}
            cy={radius}
            r={normalizedRadius}
            strokeWidth={strokeWidth}
            className={colors.track}
          />
          {/* Fill */}
          <circle
            cx={radius}
            cy={radius}
            r={normalizedRadius}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={cx(colors.fill, "transition-all duration-700 ease-out")}
          />
        </svg>
        {children && (
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            {children}
          </div>
        )}
      </div>
    )
  },
)

ProgressCircle.displayName = "ProgressCircle"

export { ProgressCircle }
export type { ProgressCircleProps, ProgressCircleVariant }
