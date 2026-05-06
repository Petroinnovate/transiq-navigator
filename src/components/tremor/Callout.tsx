// Callout – alert/notice banner
// Adapted from Tremor source for TransIQ dark dashboard

import React, { forwardRef } from "react"
import { cx } from "./utils/cx"

type CalloutVariant = "default" | "success" | "error" | "warning" | "neutral"

interface CalloutProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  icon?: React.ElementType
  variant?: CalloutVariant
  children?: React.ReactNode
}

const variantStyles: Record<CalloutVariant, string> = {
  default: "bg-cyan-500/10  border-cyan-500/30  text-cyan-300",
  success: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
  error:   "bg-rose-500/10  border-rose-500/30  text-rose-300",
  warning: "bg-amber-500/10 border-amber-500/30 text-amber-300",
  neutral: "bg-slate-700/40 border-slate-600/50 text-slate-300",
}

const Callout = forwardRef<HTMLDivElement, CalloutProps>(
  ({ title, icon: Icon, variant = "default", children, className, ...props }, forwardedRef) => {
    const styles = variantStyles[variant]
    return (
      <div
        ref={forwardedRef}
        className={cx(
          "flex w-full flex-col overflow-hidden rounded-xl border px-4 py-3 text-sm",
          styles,
          className,
        )}
        {...props}
      >
        <div className="flex items-start gap-2">
          {Icon && <Icon className="mt-0.5 h-4 w-4 shrink-0 opacity-90" aria-hidden />}
          <span className="font-semibold leading-snug">{title}</span>
        </div>
        {children && (
          <div className="mt-1 pl-6 text-xs opacity-80 leading-relaxed">
            {children}
          </div>
        )}
      </div>
    )
  },
)

Callout.displayName = "Callout"

export { Callout }
export type { CalloutProps, CalloutVariant }
