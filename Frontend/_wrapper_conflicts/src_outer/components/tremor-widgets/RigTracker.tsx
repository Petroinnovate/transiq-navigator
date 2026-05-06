// RigTracker – Tremor Tracker showing operational status of each KPI metric
// Each KPI becomes a "block" whose color encodes its health / trend

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tracker } from '@/components/tremor'
import { Activity } from 'lucide-react'

interface KPI {
  name?: string
  value?: number | string
  trend?: string
  status?: string
  unit?: string
  target?: number
}

interface RigTrackerProps {
  kpis: KPI[]
}

function kpiColor(kpi: KPI): string {
  const trend = (kpi.trend || '').toLowerCase()
  const status = (kpi.status || '').toLowerCase()

  if (status === 'critical' || trend === 'down' || trend === 'deteriorating') return 'rose'
  if (status === 'warning' || trend === 'stable') return 'amber'
  if (trend === 'up' || trend === 'improving') return 'emerald'
  // check target vs value if available
  if (kpi.target && kpi.target > 0) {
    const val = typeof kpi.value === 'number' ? kpi.value : parseFloat(String(kpi.value))
    if (!isNaN(val)) {
      const pct = (val / kpi.target) * 100
      if (pct >= 100) return 'emerald'
      if (pct >= 75) return 'blue'
      if (pct >= 50) return 'amber'
      return 'rose'
    }
  }
  return 'gray'
}

function colorToHex(color: string): string {
  const map: Record<string, string> = {
    emerald: '#34d399',
    blue: '#60a5fa',
    amber: '#fbbf24',
    rose: '#fb7185',
    gray: '#9ca3af',
  }
  return map[color] || '#9ca3af'
}

export const RigTracker: React.FC<RigTrackerProps> = ({ kpis }) => {
  if (!kpis || kpis.length === 0) return null

  const trackerData = kpis.map((kpi) => {
    const color = kpiColor(kpi)
    return {
      color: colorToHex(color) as any,
      tooltip: `${kpi.name || 'KPI'}: ${kpi.value}${kpi.unit ? ' ' + kpi.unit : ''}${kpi.trend ? ' (' + kpi.trend + ')' : ''}`,
    }
  })

  // Add filler blocks to make the strip look fuller (padding to ~ 20 blocks)
  const padCount = Math.max(0, 20 - trackerData.length)
  const padded = [
    ...trackerData,
    ...Array.from({ length: padCount }, () => ({ color: '#e5e7eb' as any, tooltip: '' })),
  ]

  const healthy = trackerData.filter((d) => d.color === colorToHex('emerald')).length
  const total = trackerData.length

  return (
    <Card className="border-blue-200 dark:border-blue-800">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Activity className="h-5 w-5 text-blue-600" />
          KPI Health Tracker
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          {healthy}/{total} metrics on-target &nbsp;|&nbsp;
          <span className="text-emerald-500">■</span> On-target &nbsp;
          <span className="text-blue-400">■</span> Near-target &nbsp;
          <span className="text-amber-400">■</span> At-risk &nbsp;
          <span className="text-rose-400">■</span> Critical &nbsp;
          <span className="text-gray-300">■</span> No data
        </p>
      </CardHeader>
      <CardContent>
        <Tracker data={padded} />
      </CardContent>
    </Card>
  )
}
