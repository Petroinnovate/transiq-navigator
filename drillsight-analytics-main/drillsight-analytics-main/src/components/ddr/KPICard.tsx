import React from 'react';
import { CitationBadge } from './CitationBadge';
import type { KPIValue } from '@/data/mockData';

interface KPICardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: React.ReactNode;
  kpiValue?: KPIValue;
  trend?: string;
  className?: string;
}

export const KPICard: React.FC<KPICardProps> = ({
  title, value, unit, icon, kpiValue, trend, className = '',
}) => {
  const statusColor = kpiValue?.status === 'critical'
    ? 'border-ddr-critical glow-red'
    : kpiValue?.status === 'warning'
    ? 'border-ddr-warning glow-amber'
    : 'border-primary/30 glow-green';

  return (
    <div className={`card-surface p-4 border-l-2 ${statusColor} ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {icon && <span className="text-muted-foreground">{icon}</span>}
          <span className="text-xs uppercase tracking-wider text-muted-foreground font-medium">{title}</span>
        </div>
        {kpiValue && (
          <CitationBadge
            citation={kpiValue.source_citation}
            confidence={kpiValue.confidence}
            isDerived={kpiValue.is_derived}
            compact
          />
        )}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-kpi-sm text-foreground">{typeof value === 'number' ? value.toLocaleString() : value}</span>
        {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
      </div>
      {trend && <div className="text-xs text-muted-foreground mt-1">{trend}</div>}
    </div>
  );
};
