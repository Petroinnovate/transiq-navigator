// SparkCharts – minimalist inline sparklines using recharts
// Adapted from Tremor source for TransIQ dark dashboard

import React from "react"
import {
  ResponsiveContainer,
  AreaChart, Area,
  LineChart, Line,
  BarChart, Bar,
  Tooltip,
} from "recharts"
import { getColorHex } from "./utils/chartColors"
import type { AvailableChartColorsKeys } from "./utils/chartColors"

interface SparkChartProps {
  data: Record<string, any>[]
  index: string
  categories: string[]
  colors?: AvailableChartColorsKeys[]
  height?: number
  showTooltip?: boolean
}

export const SparkAreaChart = ({
  data,
  index,
  categories,
  colors = ["cyan"],
  height = 40,
  showTooltip = false,
}: SparkChartProps) => (
  <ResponsiveContainer width="100%" height={height}>
    <AreaChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
      <defs>
        {categories.map((cat, i) => (
          <linearGradient key={cat} id={`spark-area-${cat}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={getColorHex(colors[i % colors.length])} stopOpacity={0.3} />
            <stop offset="95%" stopColor={getColorHex(colors[i % colors.length])} stopOpacity={0}   />
          </linearGradient>
        ))}
      </defs>
      {showTooltip && <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", fontSize: 11 }} />}
      {categories.map((cat, i) => (
        <Area
          key={cat}
          type="monotone"
          dataKey={cat}
          stroke={getColorHex(colors[i % colors.length])}
          strokeWidth={1.5}
          fill={`url(#spark-area-${cat})`}
          dot={false}
          isAnimationActive={false}
        />
      ))}
    </AreaChart>
  </ResponsiveContainer>
)

export const SparkLineChart = ({
  data,
  index,
  categories,
  colors = ["cyan"],
  height = 40,
  showTooltip = false,
}: SparkChartProps) => (
  <ResponsiveContainer width="100%" height={height}>
    <LineChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
      {showTooltip && <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", fontSize: 11 }} />}
      {categories.map((cat, i) => (
        <Line
          key={cat}
          type="monotone"
          dataKey={cat}
          stroke={getColorHex(colors[i % colors.length])}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      ))}
    </LineChart>
  </ResponsiveContainer>
)

export const SparkBarChart = ({
  data,
  index,
  categories,
  colors = ["cyan"],
  height = 40,
  showTooltip = false,
}: SparkChartProps) => (
  <ResponsiveContainer width="100%" height={height}>
    <BarChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
      {showTooltip && <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", fontSize: 11 }} />}
      {categories.map((cat, i) => (
        <Bar
          key={cat}
          dataKey={cat}
          fill={getColorHex(colors[i % colors.length])}
          opacity={0.85}
          isAnimationActive={false}
          radius={[2, 2, 0, 0]}
        />
      ))}
    </BarChart>
  </ResponsiveContainer>
)
