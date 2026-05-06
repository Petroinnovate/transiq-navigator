// Tremor CategoryBar [v0.0.3]

import React from "react"
import {
  AvailableChartColors,
  type AvailableChartColorsKeys,
  getColorClassName,
} from "./utils/chartColors"
import { cx } from "./utils/cx"

const sumNumericArray = (arr: number[]) =>
  arr.reduce((prefixSum, num) => prefixSum + num, 0)

const formatNumber = (num: number): string => {
  if (Number.isInteger(num)) return num.toString()
  return num.toFixed(1)
}

const getPositionLeft = (value: number | undefined, maxValue: number): number =>
  value ? (value / maxValue) * 100 : 0

const BarLabels = ({ values }: { values: number[] }) => {
  const sumValues = React.useMemo(() => sumNumericArray(values), [values])
  let prefixSum = 0
  let sumConsecutiveHiddenLabels = 0

  return (
    <div className={cx("relative mb-2 flex h-5 w-full text-sm font-medium", "text-gray-700 dark:text-gray-300")}>
      <div className="absolute bottom-0 left-0 flex items-center">0</div>
      {values.map((widthPercentage, index) => {
        prefixSum += widthPercentage
        const showLabel =
          (widthPercentage >= 0.1 * sumValues ||
            sumConsecutiveHiddenLabels >= 0.09 * sumValues) &&
          sumValues - prefixSum >= 0.1 * sumValues &&
          prefixSum >= 0.1 * sumValues &&
          prefixSum < 0.9 * sumValues
        sumConsecutiveHiddenLabels = showLabel
          ? 0
          : (sumConsecutiveHiddenLabels += widthPercentage)
        const widthPositionLeft = getPositionLeft(widthPercentage, sumValues)
        return (
          <div
            key={`item-${index}`}
            className="flex items-center justify-end pr-0.5"
            style={{ width: `${widthPositionLeft}%` }}
          >
            {showLabel ? (
              <span className="block translate-x-1/2 text-sm tabular-nums">
                {formatNumber(prefixSum)}
              </span>
            ) : null}
          </div>
        )
      })}
      <div className="absolute bottom-0 right-0 flex items-center">
        {formatNumber(sumValues)}
      </div>
    </div>
  )
}

interface CategoryBarProps extends React.HTMLAttributes<HTMLDivElement> {
  values: number[]
  colors?: AvailableChartColorsKeys[]
  showLabels?: boolean
  /** Optional legend labels matching the values array */
  labels?: string[]
}

const CategoryBar = React.forwardRef<HTMLDivElement, CategoryBarProps>(
  (
    {
      values = [],
      colors = AvailableChartColors,
      showLabels = true,
      labels,
      className,
      ...props
    },
    forwardedRef,
  ) => {
    const maxValue = React.useMemo(() => sumNumericArray(values), [values])

    return (
      <div ref={forwardedRef} className={cx(className)} aria-label="Category bar" {...props}>
        {showLabels ? <BarLabels values={values} /> : null}
        <div className="relative flex h-2 w-full items-center">
          <div className="flex h-full flex-1 items-center gap-0.5 overflow-hidden rounded-full">
            {values.map((value, index) => {
              const barColor = colors[index] ?? "gray"
              const percentage = (value / maxValue) * 100
              return (
                <div
                  key={`item-${index}`}
                  className={cx(
                    "h-full",
                    getColorClassName(barColor as AvailableChartColorsKeys, "bg"),
                    percentage === 0 && "hidden",
                  )}
                  style={{ width: `${percentage}%` }}
                />
              )
            })}
          </div>
        </div>
        {labels && labels.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {labels.map((label, index) => {
              const barColor = colors[index] ?? "gray"
              return (
                <div key={label} className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                  <span
                    className={cx(
                      "inline-block h-2 w-2 rounded-full",
                      getColorClassName(barColor as AvailableChartColorsKeys, "bg"),
                    )}
                  />
                  {label}
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  },
)

CategoryBar.displayName = "CategoryBar"

export { CategoryBar, type CategoryBarProps }
