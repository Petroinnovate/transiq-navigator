// RootCauseBarList – Tremor BarList showing ranked root causes from DMAIC Analyze
// Added alongside the existing SixSigmaDMAIC section

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BarList } from '@/components/tremor'
import { AlertCircle } from 'lucide-react'

interface RootCause {
  cause?: string
  confidence?: number | string
  description?: string
}

interface RootCauseBarListProps {
  rootCauses: (RootCause | string)[]
  title?: string
}

export const RootCauseBarList: React.FC<RootCauseBarListProps> = ({
  rootCauses,
  title = 'Root Cause Ranking',
}) => {
  if (!rootCauses || rootCauses.length === 0) return null

  const barData = rootCauses
    .map((rc) => {
      if (typeof rc === 'string') {
        return { name: rc, value: 50 }
      }
      const cause = rc.cause || rc.description || String(rc)
      const conf = typeof rc.confidence === 'number' ? rc.confidence : parseFloat(String(rc.confidence)) || 0.5
      return {
        name: cause.length > 60 ? cause.slice(0, 60) + '…' : cause,
        value: Math.round(conf * 100),
        key: cause,
      }
    })
    .filter((d) => d.name)

  if (barData.length === 0) return null

  return (
    <Card className="border-orange-200 dark:border-orange-800">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <AlertCircle className="h-5 w-5 text-orange-600" />
          {title}
        </CardTitle>
        <p className="text-xs text-muted-foreground">Bar width = confidence score (%)</p>
      </CardHeader>
      <CardContent>
        <BarList
          data={barData}
          valueFormatter={(v) => `${v}%`}
          showAnimation
        />
      </CardContent>
    </Card>
  )
}
