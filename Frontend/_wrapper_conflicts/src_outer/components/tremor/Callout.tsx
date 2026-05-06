// Tremor Callout [v0.0.1]

import React from "react"
import { tv, type VariantProps } from "tailwind-variants"
import { cx } from "./utils/cx"

const calloutVariants = tv({
  base: "flex flex-col overflow-hidden rounded-md p-4 text-sm",
  variants: {
    variant: {
      default: [
        "text-blue-900 dark:text-blue-400",
        "bg-blue-50 dark:bg-blue-950/70",
      ],
      success: [
        "text-emerald-900 dark:text-emerald-500",
        "bg-emerald-50 dark:bg-emerald-950/70",
      ],
      error: [
        "text-red-900 dark:text-red-500",
        "bg-red-50 dark:bg-red-950/70",
      ],
      warning: [
        "text-yellow-900 dark:text-yellow-500",
        "bg-yellow-50 dark:bg-yellow-950/70",
      ],
      neutral: [
        "text-gray-900 dark:text-gray-400",
        "bg-gray-100 dark:bg-gray-800/70",
      ],
    },
  },
  defaultVariants: {
    variant: "default",
  },
})

interface CalloutProps
  extends React.ComponentPropsWithoutRef<"div">,
    VariantProps<typeof calloutVariants> {
  title: string
  icon?: React.ElementType | React.ReactElement
}

const Callout = React.forwardRef<HTMLDivElement, CalloutProps>(
  (
    { title, icon: Icon, className, variant, children, ...props },
    forwardedRef,
  ) => {
    return (
      <div
        ref={forwardedRef}
        className={cx(calloutVariants({ variant }), className)}
        {...props}
      >
        <div className="flex items-start">
          {Icon && typeof Icon === "function" ? (
            <Icon className="mr-1.5 h-5 w-5 shrink-0" aria-hidden="true" />
          ) : (
            Icon
          )}
          <span className="font-semibold">{title}</span>
        </div>
        <div className={cx("overflow-y-auto", children ? "mt-2" : "")}>
          {children}
        </div>
      </div>
    )
  },
)

Callout.displayName = "Callout"

export { Callout, calloutVariants, type CalloutProps }
