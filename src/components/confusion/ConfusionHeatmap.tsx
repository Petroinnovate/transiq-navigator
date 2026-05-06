import React from 'react';

interface ConfusionHeatmapProps {
  matrix: number[][];
  labels: string[];
  normalized?: number[][] | null;
}

const ConfusionHeatmap: React.FC<ConfusionHeatmapProps> = ({ matrix, labels, normalized }) => {
  const n = labels.length;

  // Find max value for colour scaling
  const allValues = matrix.flat();
  const maxVal = Math.max(...allValues, 1);

  const cellBg = (row: number, col: number): string => {
    const val = matrix[row][col];
    const intensity = val / maxVal; // 0..1
    if (row === col) {
      // Correct predictions → green tones
      const g = Math.round(80 + intensity * 120);
      const opacity = 0.15 + intensity * 0.55;
      return `rgba(52, ${g}, 52, ${opacity})`;
    }
    // Errors → red tones
    const opacity = 0.1 + intensity * 0.65;
    return `rgba(220, 38, 38, ${opacity})`;
  };

  const pct = (row: number, col: number): string => {
    if (!normalized) return '';
    const v = normalized[row]?.[col];
    return v != null ? `(${(v * 100).toFixed(1)}%)` : '';
  };

  return (
    <div className="overflow-x-auto">
      <div className="inline-block min-w-full">
        {/* Y-axis label */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider rotate-90 origin-center w-4 mr-6 shrink-0">
            Actual
          </span>
          <div className="flex-1">
            {/* Column headers (Predicted) */}
            <div className="flex mb-1">
              <div className="w-20 shrink-0" />
              {labels.map((lbl, j) => (
                <div
                  key={j}
                  className="flex-1 text-center text-[10px] text-slate-400 font-medium px-1 truncate"
                  title={lbl}
                >
                  {lbl}
                </div>
              ))}
            </div>

            {/* Rows */}
            {matrix.map((row, i) => (
              <div key={i} className="flex items-center mb-1">
                {/* Row label */}
                <div
                  className="w-20 shrink-0 text-[11px] text-slate-300 font-medium pr-2 text-right truncate"
                  title={labels[i]}
                >
                  {labels[i]}
                </div>
                {row.map((val, j) => (
                  <div
                    key={j}
                    className="flex-1 aspect-square min-h-[44px] flex flex-col items-center justify-center rounded mx-0.5 border border-slate-700/30 transition-all hover:scale-105"
                    style={{ background: cellBg(i, j) }}
                    title={`Actual: ${labels[i]} → Predicted: ${labels[j]}: ${val}`}
                  >
                    <span className="text-sm font-bold text-white leading-none">{val}</span>
                    {normalized && (
                      <span className="text-[10px] text-slate-300 leading-none mt-0.5">
                        {pct(i, j)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ))}

            {/* X-axis label */}
            <div className="text-center text-[10px] text-slate-500 uppercase tracking-wider mt-2">
              Predicted
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 mt-3 justify-center">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm" style={{ background: 'rgba(52,160,52,0.6)' }} />
            <span className="text-[10px] text-slate-400">Correct</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm" style={{ background: 'rgba(220,38,38,0.55)' }} />
            <span className="text-[10px] text-slate-400">Misclassified</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm bg-slate-800 border border-slate-600" />
            <span className="text-[10px] text-slate-400">Zero</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfusionHeatmap;
