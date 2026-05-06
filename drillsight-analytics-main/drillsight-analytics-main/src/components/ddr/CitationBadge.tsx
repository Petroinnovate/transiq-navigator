import React, { useState } from 'react';

interface CitationBadgeProps {
  citation: string;
  confidence?: number;
  isDerived?: boolean;
  compact?: boolean;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({
  citation, confidence = 0.95, isDerived = false, compact = false,
}) => {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-flex items-center gap-1">
      {isDerived && (
        <span className="text-ddr-derived text-[10px]" title="Derived value">⚡</span>
      )}
      <button
        onClick={() => setOpen(!open)}
        className="citation-badge inline-flex items-center gap-1"
        title={citation}
      >
        📋
        {!compact && <span>[{citation.split('–').slice(0, 2).join('–')}]</span>}
      </button>
      {open && (
        <div className="absolute top-full right-0 z-50 mt-1 w-80 card-surface p-3 shadow-lg text-xs">
          <div className="flex justify-between items-start mb-2">
            <span className="font-mono-citation break-all">{citation}</span>
            <button onClick={() => setOpen(false)} className="text-muted-foreground ml-2">✕</button>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-muted-foreground">Confidence:</span>
            <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${confidence * 100}%`,
                  background: confidence >= 0.95 ? 'hsl(var(--ddr-status-excellent))' : confidence >= 0.8 ? 'hsl(var(--ddr-status-warning))' : 'hsl(var(--ddr-status-critical))',
                }}
              />
            </div>
            <span className="font-mono-citation">{(confidence * 100).toFixed(0)}%</span>
          </div>
          {isDerived && (
            <div className="mt-2 text-ddr-derived">⚡ Derived/Computed Value</div>
          )}
        </div>
      )}
    </span>
  );
};
