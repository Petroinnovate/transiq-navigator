// AlertCallouts – Tremor Callout widget for high/critical severity alerts
// Shown ABOVE the existing InsightsAlerts as a quick-glance banner strip

import React from 'react'
import { Callout } from '@/components/tremor'
import { AlertTriangle, AlertCircle, Info, CheckCircle2 } from 'lucide-react'

interface Alert {
  severity?: string
  type?: string
  message?: string
  action?: string
  actionRequired?: string
}

interface AlertCalloutsProps {
  alerts: Alert[]
}

const getCalloutVariant = (severity: string) => {
  const s = severity?.toLowerCase()
  if (s === 'critical' || s === 'high' || s === 'error') return 'error' as const
  if (s === 'medium' || s === 'warning') return 'warning' as const
  if (s === 'low' || s === 'info') return 'default' as const
  if (s === 'success') return 'success' as const
  return 'neutral' as const
}

const getIcon = (severity: string) => {
  const s = severity?.toLowerCase()
  if (s === 'critical' || s === 'high' || s === 'error') return AlertTriangle
  if (s === 'medium' || s === 'warning') return AlertCircle
  if (s === 'success') return CheckCircle2
  return Info
}

export const AlertCallouts: React.FC<AlertCalloutsProps> = ({ alerts }) => {
  // Only show high/critical alerts in this widget
  const urgentAlerts = alerts.filter((a) => {
    const s = (a.severity || a.type || '').toLowerCase()
    return s === 'critical' || s === 'high' || s === 'error'
  })

  if (urgentAlerts.length === 0) return null

  return (
    <div className="space-y-2">
      <h2 className="text-xl font-semibold text-red-700 dark:text-red-400">
        ⚠ Priority Alerts ({urgentAlerts.length})
      </h2>
      <div className="space-y-2">
        {urgentAlerts.map((alert, index) => {
          const severity = alert.severity || alert.type || 'high'
          const Icon = getIcon(severity)
          const action = alert.action || alert.actionRequired
          return (
            <Callout
              key={index}
              title={alert.message || 'Alert'}
              icon={Icon}
              variant={getCalloutVariant(severity)}
            >
              {action && (
                <p className="text-sm">
                  <span className="font-semibold">Action: </span>
                  {action}
                </p>
              )}
            </Callout>
          )
        })}
      </div>
    </div>
  )
}
