import React from 'react';

export const LoadingState: React.FC<{ message?: string }> = ({ message = 'Loading data...' }) => (
  <div className="card-surface p-8 flex flex-col items-center justify-center min-h-[200px]">
    <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
    <span className="text-xs text-muted-foreground">{message}</span>
  </div>
);
