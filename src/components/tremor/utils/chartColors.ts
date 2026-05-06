export type AvailableChartColorsKeys =
  | "blue"
  | "emerald"
  | "violet"
  | "amber"
  | "gray"
  | "cyan"
  | "pink"
  | "lime"
  | "fuchsia"
  | "rose"
  | "teal"
  | "indigo"
  | "orange"
  | "sky"

export const AvailableChartColors: AvailableChartColorsKeys[] = [
  "blue", "emerald", "violet", "amber", "gray", "cyan",
  "pink", "lime", "fuchsia", "rose", "teal", "indigo", "orange", "sky",
]

export const chartColors: Record<AvailableChartColorsKeys, { stroke: string; fill: string; hex: string }> = {
  blue:    { stroke: "stroke-blue-500",    fill: "fill-blue-500",    hex: "#3b82f6" },
  emerald: { stroke: "stroke-emerald-500", fill: "fill-emerald-500", hex: "#10b981" },
  violet:  { stroke: "stroke-violet-500",  fill: "fill-violet-500",  hex: "#8b5cf6" },
  amber:   { stroke: "stroke-amber-500",   fill: "fill-amber-500",   hex: "#f59e0b" },
  gray:    { stroke: "stroke-gray-500",    fill: "fill-gray-500",    hex: "#6b7280" },
  cyan:    { stroke: "stroke-cyan-500",    fill: "fill-cyan-500",    hex: "#06b6d4" },
  pink:    { stroke: "stroke-pink-500",    fill: "fill-pink-500",    hex: "#ec4899" },
  lime:    { stroke: "stroke-lime-500",    fill: "fill-lime-500",    hex: "#84cc16" },
  fuchsia: { stroke: "stroke-fuchsia-500", fill: "fill-fuchsia-500", hex: "#d946ef" },
  rose:    { stroke: "stroke-rose-500",    fill: "fill-rose-500",    hex: "#f43f5e" },
  teal:    { stroke: "stroke-teal-500",    fill: "fill-teal-500",    hex: "#14b8a6" },
  indigo:  { stroke: "stroke-indigo-500",  fill: "fill-indigo-500",  hex: "#6366f1" },
  orange:  { stroke: "stroke-orange-500",  fill: "fill-orange-500",  hex: "#f97316" },
  sky:     { stroke: "stroke-sky-500",     fill: "fill-sky-500",     hex: "#0ea5e9" },
}

export function getColorClassName(
  color: AvailableChartColorsKeys,
  type: "stroke" | "fill",
): string {
  return chartColors[color]?.[type] ?? ""
}

export function getColorHex(color: AvailableChartColorsKeys): string {
  return chartColors[color]?.hex ?? "#6b7280"
}
