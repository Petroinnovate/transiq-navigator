import React, { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DollarSign, Layers, ChevronRight, BarChart3 } from 'lucide-react';

interface SimulatedKpi {
  metric: string;
  original: number;
  simulated: number;
  change: number;
}

interface Scenario {
  name: string;
  inputs: Record<string, number>;
  simulatedKpis: SimulatedKpi[];
  financialImpact: number;
  narrative: string;
}

interface WhatIfSimulatorProps {
  scenarios?: Scenario[];
}

const impactColor = (impact: number) =>
  impact > 0 ? 'text-emerald-400' : impact < 0 ? 'text-red-400' : 'text-slate-400';
const impactBg = (impact: number) =>
  impact > 0 ? 'border-emerald-500/30 bg-emerald-900/10' : impact < 0 ? 'border-red-500/30 bg-red-900/10' : 'border-slate-600/30';

const WhatIfSimulator: React.FC<WhatIfSimulatorProps> = ({ scenarios = [] }) => {
  const [selected, setSelected] = useState<number | null>(0);

  if (scenarios.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Layers className="h-10 w-10 text-slate-600 mb-3" />
        <h3 className="text-base font-semibold text-slate-400 mb-1">No Scenarios Available</h3>
        <p className="text-sm text-slate-500 max-w-md">
          Scenario simulation requires KPI causal relationships and historical data.
        </p>
      </div>
    );
  }

  const sorted = [...scenarios].sort((a, b) => (b.financialImpact ?? 0) - (a.financialImpact ?? 0));
  const active = selected != null ? sorted[selected] : null;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700/40 rounded-lg px-3 py-2">
          <Layers className="h-4 w-4 text-violet-400" />
          <span className="text-sm text-slate-300 font-medium">{scenarios.length} preset scenarios</span>
        </div>
        <div className="text-xs text-slate-500">Click a scenario to explore its impact</div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Scenario list */}
        <div className="space-y-2">
          {sorted.map((s, i) => (
            <button
              key={i}
              className={`w-full text-left rounded-lg border p-3 transition-all ${
                selected === i
                  ? 'border-violet-500/50 bg-violet-900/20 shadow-lg shadow-violet-900/20'
                  : 'border-slate-700/40 bg-slate-800/40 hover:border-slate-600/60 hover:bg-slate-800/60'
              }`}
              onClick={() => setSelected(i)}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-slate-200 leading-snug truncate">{s.name}</span>
                <ChevronRight className={`h-3.5 w-3.5 shrink-0 transition-colors ${selected === i ? 'text-violet-400' : 'text-slate-600'}`} />
              </div>
              <div className={`text-xs font-semibold mt-1 ${impactColor(s.financialImpact ?? 0)}`}>
                {(s.financialImpact ?? 0) > 0 ? '+' : ''}${(s.financialImpact ?? 0).toLocaleString()} impact
              </div>
            </button>
          ))}
        </div>

        {/* Scenario detail */}
        {active && (
          <Card className="lg:col-span-2 bg-slate-800/50 border border-slate-700/40">
            <CardContent className="p-4 space-y-4">
              {/* Title + impact */}
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-white">{active.name}</h3>
                  <p className="text-sm text-slate-400 mt-1 leading-snug">{active.narrative}</p>
                </div>
                <div className={`flex items-center gap-1.5 border rounded-lg px-3 py-2 shrink-0 ${impactBg(active.financialImpact ?? 0)}`}>
                  <DollarSign className={`h-4 w-4 ${impactColor(active.financialImpact ?? 0)}`} />
                  <div className="text-right">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider">Est. Impact</div>
                    <div className={`text-sm font-bold ${impactColor(active.financialImpact ?? 0)}`}>
                      {(active.financialImpact ?? 0) > 0 ? '+' : ''}${(active.financialImpact ?? 0).toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>

              {/* Inputs */}
              {Object.keys(active.inputs).length > 0 && (
                <div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Levers Applied</div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(active.inputs).map(([k, v]) => (
                      <Badge key={k} variant="outline" className="text-[10px] border-violet-500/30 text-violet-300 bg-violet-900/20">
                        {k}: {v > 0 ? '+' : ''}{v}%
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* KPI impact table */}
              {active.simulatedKpis?.length > 0 && (
                <div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">
                    <BarChart3 className="inline h-3 w-3 mr-1" />
                    Simulated KPI Changes
                  </div>
                  <div className="divide-y divide-slate-700/40 rounded-lg border border-slate-700/40 overflow-hidden">
                    {active.simulatedKpis.map((kpi, ki) => (
                      <div key={ki} className="flex items-center justify-between px-3 py-2 bg-slate-900/20 hover:bg-slate-900/40 transition-colors text-sm">
                        <span className="text-slate-300 truncate">{kpi.metric}</span>
                        <div className="flex items-center gap-4 shrink-0">
                          <span className="text-slate-500 text-xs">{(kpi.original ?? 0).toFixed(1)}</span>
                          <span className="text-slate-600 text-xs">→</span>
                          <span className="text-slate-200 font-medium text-xs">{(kpi.simulated ?? 0).toFixed(1)}</span>
                          <span className={`text-xs font-bold w-14 text-right ${impactColor(kpi.change ?? 0)}`}>
                            {(kpi.change ?? 0) > 0 ? '+' : ''}{(kpi.change ?? 0).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default WhatIfSimulator;
