// AlertCallouts – Tremor Callout banners for high/critical severity alerts
// Placed at the top of the dashboard so urgent items are never missed

import React from "react"
import { Callout } from "@/components/tremor"
import { AlertTriangle, XCircle, Info, CheckCircle } from "lucide-react"

interface Alert {
  type: "warning" | "error" | "info" | "success"
  message: string
  severity: "high" | "medium" | "low"
  action?: string
}

interface AlertCalloutsProps {
  alerts: Alert[]
}

const typeConfig = {
  error:   { variant: "error"   as const, Icon: XCircle,       label: "Critical" },
  warning: { variant: "warning" as const, Icon: AlertTriangle, label: "Warning"  },
  info:    { variant: "default" as const, Icon: Info,          label: "Info"     },
  success: { variant: "success" as const, Icon: CheckCircle,   label: "Success"  },
}

export const AlertCallouts: React.FC<AlertCalloutsProps> = ({ alerts }) => {
  const urgentAlerts = alerts.filter(
    (a) => a.severity === "high" || a.type === "error",
  )
  if (urgentAlerts.length === 0) return null

  return (
    <div className="space-y-2">
      {urgentAlerts.map((alert, i) => {
        const cfg = typeConfig[alert.type] ?? typeConfig.warning
        return (
          <Callout
            key={i}
            title={`${cfg.label}: ${alert.message}`}
            icon={cfg.Icon}
            variant={cfg.variant}
          >
            {alert.action}
          </Callout>
        )
      })}
    </div>
  )
}
