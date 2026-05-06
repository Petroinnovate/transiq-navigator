import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  message = 'Failed to load data. Please try again.',
  onRetry,
}) => (
  <div className="card-surface p-8 flex flex-col items-center justify-center min-h-[200px] border-l-2 border-destructive">
    <AlertCircle className="w-10 h-10 text-destructive mb-3" />
    <h3 className="text-sm font-semibold text-foreground mb-1">Error</h3>
    <p className="text-xs text-muted-foreground mb-4 max-w-sm">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="flex items-center gap-2 px-3 py-1.5 text-xs rounded bg-secondary text-foreground hover:bg-accent transition-colors"
      >
        <RefreshCw className="w-3.5 h-3.5" /> Retry
      </button>
    )}
  </div>
);
