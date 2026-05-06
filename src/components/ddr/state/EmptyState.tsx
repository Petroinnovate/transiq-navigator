import React from 'react';
import { DatabaseZap } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  message?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

const EmptyState: React.FC<EmptyStateProps> = ({ title, message, action }) => (
  <div className="card-surface p-8 flex flex-col items-center justify-center text-center">
    <DatabaseZap className="h-12 w-12 text-slate-500 mb-4" />
    <h3 className="text-lg font-semibold text-white mb-1">{title}</h3>
    {message && <p className="text-sm text-slate-400 mb-4 max-w-md">{message}</p>}
    {action && (
      <button
        onClick={action.onClick}
        className="px-4 py-2 rounded-md text-sm font-medium bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 transition-colors"
      >
        {action.label}
      </button>
    )}
  </div>
);

export default EmptyState;
