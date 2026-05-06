// BarList – horizontal ranked bar list
// Adapted from Tremor source for TransIQ dark dashboard

import React, { forwardRef } from "react"
import { cx } from "./utils/cx"

interface BarListItem {
  name: string
  value: number
  href?: string
  icon?: React.ElementType
  color?: string
}

interface BarListProps {
  data: BarListItem[]
  valueFormatter?: (v: number) => string
  sortOrder?: "ascending" | "descending" | "none"
  showAnimation?: boolean
  onValueChange?: (item: BarListItem) => void
}

const BarList = forwardRef<HTMLDivElement, BarListProps>(
  (
    {
      data = [],
      valueFormatter = (v) => String(v),
      sortOrder = "descending",
      showAnimation = false,
      onValueChange,
    },
    forwardedRef,
  ) => {
    const sortedData = React.useMemo(() => {
      if (sortOrder === "none") return data
      return [...data].sort((a, b) =>
        sortOrder === "ascending" ? a.value - b.value : b.value - a.value,
      )
    }, [data, sortOrder])

    const maxValue = Math.max(...sortedData.map((item) => item.value), 0)

    const widths = sortedData.map((item) =>
      maxValue === 0 ? 0 : Math.max((item.value / maxValue) * 100, 2),
    )

    const rowClass = cx(
      "group flex w-full items-center gap-2",
      onValueChange ? "cursor-pointer" : "",
    )

    return (
      <div
        ref={forwardedRef}
        className="flex justify-between space-x-6"
        aria-sort={sortOrder}
      >
        {/* Bar column */}
        <div className="relative w-full space-y-1.5">
          {sortedData.map((item, index) => {
            const ItemIcon = item.icon
            return (
              <div
                key={`bar-${index}`}
                onClick={() => onValueChange?.(item)}
                className={rowClass}
              >
                <div
                  className="flex max-w-full items-center rounded"
                  style={{
                    width: `${widths[index]}%`,
                    backgroundColor: item.color ?? "rgba(6,182,212,0.25)",
                    transition: showAnimation ? "width 0.6s ease" : undefined,
                  }}
                >
                  <div className="flex items-center gap-2 overflow-hidden px-2 py-1.5">
                    {ItemIcon && <ItemIcon className="h-4 w-4 shrink-0 text-slate-300" />}
                    {item.href ? (
                      <a
                        href={item.href}
                        className="truncate text-sm text-slate-200 hover:text-cyan-300 hover:underline"
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {item.name}
                      </a>
                    ) : (
                      <span className="truncate text-sm text-slate-200">{item.name}</span>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Value column */}
        <div className="space-y-1.5">
          {sortedData.map((item, index) => (
            <div
              key={`value-${index}`}
              className="flex h-7 items-center justify-end"
              onClick={() => onValueChange?.(item)}
            >
              <span className="whitespace-nowrap text-sm font-medium text-slate-300">
                {valueFormatter(item.value)}
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  },
)

BarList.displayName = "BarList"

export { BarList }
export type { BarListItem, BarListProps }
