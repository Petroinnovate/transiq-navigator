// KPIProgressCircles – Tremor ProgressCircle showing each KPI's value vs target
// Shown as an additional visual grid below the existing KPICard grid

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ProgressCircle } from '@/components/tremor'
import { Target } from 'lucide-react'

interface KPI {
  title?: string
  name?: string
  value: number
  unit?: string
  target?: number
  trend?: string
  confidence?: number
}

interface KPIProgressCirclesProps {
  kpis: KPI[]
}

const getVariant = (pct: number, trend?: string) => {
  if (trend === 'deteriorating' || trend === 'down') return 'error' as const
  if (pct >= 100) return 'success' as const
  if (pct >= 75) return 'default' as const
  if (pct >= 50) return 'warning' as const
  return 'error' as const
}

export const KPIProgressCircles: React.FC<KPIProgressCirclesProps> = ({ kpis }) => {
  const kpisWithTarget = kpis.filter((k) => k.target && k.target > 0 && k.value >= 0)
  if (kpisWithTarget.length === 0) return null

  return (
    <div className="space-y-3">
      <h2 className="text-xl font-semibold">KPI Target Achievement</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-4">
        {kpisWithTarget.map((kpi, index) => {
          const label = kpi.title || kpi.name || `KPI ${index + 1}`
          const pct = Math.round((kpi.value / kpi.target!) * 100)
          const capped = Math.min(pct, 100)
          const variant = getVariant(pct, kpi.trend)
          return (
            <Card key={index} className="flex flex-col items-center justify-center p-4 gap-2">
              <CardHeader className="p-0 pb-1 text-center">
                <CardTitle className="text-xs font-medium text-muted-foreground line-clamp-2 text-center leading-tight">
                  {label}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0 flex flex-col items-center gap-1">
                <ProgressCircle value={capped} variant={variant} radius={36} strokeWidth={6}>
                  <span className="text-xs font-bold">{capped}%</span>
                </ProgressCircle>
                <p className="text-xs text-muted-foreground text-center">
                  {kpi.value} / {kpi.target} {kpi.unit}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
