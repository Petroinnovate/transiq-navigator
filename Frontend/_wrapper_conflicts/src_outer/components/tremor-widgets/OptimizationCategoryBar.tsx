// OptimizationCategoryBar – Tremor CategoryBar showing optimization savings breakdown
// Shown inside the OptimizationPanel section as an additional visualisation

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CategoryBar } from '@/components/tremor'
import { type AvailableChartColorsKeys } from '@/components/tremor/utils/chartColors'
import { Zap } from 'lucide-react'

interface Optimization {
  title?: string
  impact?: string
  savings?: {
    value?: number
    unit?: string
    percentage?: string
    timeframe?: string
  }
  confidence?: number
}

interface OptimizationCategoryBarProps {
  optimizations: Optimization[]
}

const impactColors: Record<string, AvailableChartColorsKeys> = {
  high: 'emerald',
  medium: 'amber',
  low: 'gray',
}

export const OptimizationCategoryBar: React.FC<OptimizationCategoryBarProps> = ({
  optimizations,
}) => {
  const withSavings = optimizations.filter((o) => o.savings?.value && o.savings.value > 0)
  if (withSavings.length === 0) return null

  const values = withSavings.map((o) => o.savings!.value!)
  const colors = withSavings.map((o) => impactColors[(o.impact || 'low').toLowerCase()] || 'gray')
  const labels = withSavings.map(
    (o) => `${o.title?.slice(0, 30) || 'Optimization'} (${o.savings?.unit || '$'}${(o.savings!.value!).toLocaleString()})`,
  )

  const total = values.reduce((a, b) => a + b, 0)

  return (
    <Card className="border-emerald-200 dark:border-emerald-800">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Zap className="h-5 w-5 text-emerald-600" />
          Savings Distribution
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Total potential: ${total.toLocaleString()} — green = high impact, amber = medium, gray = low
        </p>
      </CardHeader>
      <CardContent>
        <CategoryBar
          values={values}
          colors={colors}
          showLabels
          labels={labels}
        />
      </CardContent>
    </Card>
  )
}
