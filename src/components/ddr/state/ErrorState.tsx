import React from 'react';
import { AlertCircle } from 'lucide-react';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

const ErrorState: React.FC<ErrorStateProps> = ({
  message = 'Something went wrong. Please try again.',
  onRetry,
}) => (
  <div className="card-surface p-6 border-l-2 border-destructive flex items-start gap-4">
    <AlertCircle className="h-6 w-6 text-red-400 flex-shrink-0 mt-0.5" />
    <div className="flex-1">
      <h3 className="text-sm font-semibold text-white mb-1">Error</h3>
      <p className="text-sm text-slate-400">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 px-4 py-1.5 rounded-md text-xs font-medium bg-red-500/10 text-red-300 border border-red-500/30 hover:bg-red-500/20 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  </div>
);

export default ErrorState;
