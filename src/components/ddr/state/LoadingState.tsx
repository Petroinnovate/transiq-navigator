import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
}

const LoadingState: React.FC<LoadingStateProps> = ({ message = 'Loading...' }) => (
  <div className="card-surface p-8 flex flex-col items-center justify-center text-center">
    <Loader2 className="h-8 w-8 text-cyan-400 animate-spin mb-4" />
    <p className="text-sm text-slate-400">{message}</p>
  </div>
);

export default LoadingState;
