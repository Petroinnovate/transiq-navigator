import React from 'react';
import { DatabaseZap } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  message?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Data Available',
  message = 'Connect to a backend API to populate this module with real data.',
  icon,
  action,
}) => (
  <div className="card-surface p-8 flex flex-col items-center justify-center text-center min-h-[200px]">
    <div className="text-muted-foreground mb-3">
      {icon || <DatabaseZap className="w-10 h-10 mx-auto" />}
    </div>
    <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
    <p className="text-xs text-muted-foreground max-w-sm">{message}</p>
    {action && <div className="mt-4">{action}</div>}
  </div>
);
