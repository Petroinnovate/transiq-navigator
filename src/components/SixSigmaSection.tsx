import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Target, TrendingUp, BarChart3, Lightbulb, Shield, AlertCircle } from 'lucide-react';

interface SixSigmaData {
  dmaic: {
    define: any;
    measure: any;
    analyze: any;
    improve: any;
    control: any;
  };
  sigmaLevel: any;
  defectRate: any;
  processCapability: any;
  rootCauses?: any[];
}

// Recursively renders any value (string, number, array, object) as React nodes
const renderContent = (value: any): React.ReactNode => {
  if (value === null || value === undefined) return null;
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    return (
      <ul className="list-disc list-inside space-y-1 mt-1">
        {value.map((item, i) => (
          <li key={i} className="text-slate-300 text-sm">
            {typeof item === 'object' && item !== null
              ? (item.cause || item.text || item.label || JSON.stringify(item))
              : String(item)}
          </li>
        ))}
      </ul>
    );
  }
  if (typeof value === 'object') {
    // {unit, value} financial pattern
    if ('value' in value && 'unit' in value) {
      return `${value.unit}${Number(value.value).toLocaleString()}`;
    }
    return (
      <div className="space-y-2 mt-1">
        {Object.entries(value).map(([k, v], i) => (
          <div key={i}>
            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wide">
              {k.replace(/([A-Z])/g, ' $1').trim()}:{' '}
            </span>
            <span className="text-slate-300 text-sm">{renderContent(v)}</span>
          </div>
        ))}
      </div>
    );
  }
  return String(value);
};

// Extracts 'High' | 'Medium' | 'Low' from any string or value
const extractCapabilityLevel = (capability: any): 'High' | 'Medium' | 'Low' => {
  const s = String(capability || '').toLowerCase();
  if (s.startsWith('high') || (s.includes('high') && !s.includes('medium') && !s.includes('low'))) return 'High';
  if (s.startsWith('low')) return 'Low';
  return 'Medium';
};

interface SixSigmaSectionProps {
  sixSigma: SixSigmaData;
}

const SixSigmaSection = ({ sixSigma }: SixSigmaSectionProps) => {

  const getProcessCapabilityColor = (capability: any) => {
    const level = extractCapabilityLevel(capability);
    switch (level) {
      case 'High':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'Medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'Low':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const dmaicPhases = [
    { key: 'define',  label: 'Define',   icon: Target,    color: 'text-blue-400',   bg: 'bg-blue-500/15'   },
    { key: 'measure', label: 'Measure',  icon: BarChart3, color: 'text-green-400',  bg: 'bg-green-500/15'  },
    { key: 'analyze', label: 'Analyze',  icon: TrendingUp,color: 'text-yellow-400', bg: 'bg-yellow-500/15' },
    { key: 'improve', label: 'Improve',  icon: Lightbulb, color: 'text-purple-400', bg: 'bg-purple-500/15' },
    { key: 'control', label: 'Control',  icon: Shield,    color: 'text-cyan-400',   bg: 'bg-cyan-500/15'   },
  ];

  const sigmaIsNA = !sixSigma.sigmaLevel || String(sixSigma.sigmaLevel).toUpperCase() === 'N/A';
  const defectIsNA = !sixSigma.defectRate || String(sixSigma.defectRate).toUpperCase() === 'N/A';
  const capabilityLevel = extractCapabilityLevel(sixSigma.processCapability);
  const capabilityColor = capabilityLevel === 'High' ? 'text-emerald-400' : capabilityLevel === 'Medium' ? 'text-amber-400' : 'text-red-400';
  const capabilityBg = capabilityLevel === 'High' ? 'bg-emerald-500/10 border-emerald-500/30' : capabilityLevel === 'Medium' ? 'bg-amber-500/10 border-amber-500/30' : 'bg-red-500/10 border-red-500/30';
  const capabilityWidth = capabilityLevel === 'High' ? '85%' : capabilityLevel === 'Medium' ? '55%' : '25%';
  const capabilityBarColor = capabilityLevel === 'High' ? 'bg-emerald-500' : capabilityLevel === 'Medium' ? 'bg-amber-400' : 'bg-red-500';

  return (
    <div className="space-y-5">
      {/* Key Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Sigma Level */}
        <Card className="bg-slate-800/50 border-slate-700/60 backdrop-blur-sm">
          <CardContent className="p-4">
            <div className="text-xs text-slate-500 uppercase tracking-widest font-semibold mb-2">Sigma Level</div>
            {sigmaIsNA ? (
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  {[1,2,3,4,5,6].map(i => (
                    <div key={i} className="w-3 h-3 rounded-full bg-slate-700 border border-slate-600" />
                  ))}
                </div>
                <span className="text-slate-500 text-xs">Pending analysis</span>
              </div>
            ) : (
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold text-cyan-400">{sixSigma.sigmaLevel}</span>
              </div>
            )}
            <div className="text-[11px] text-slate-500 mt-1">Process performance σ</div>
          </CardContent>
        </Card>

        {/* Defect Rate */}
        <Card className="bg-slate-800/50 border-slate-700/60 backdrop-blur-sm">
          <CardContent className="p-4">
            <div className="text-xs text-slate-500 uppercase tracking-widest font-semibold mb-2">Defect Rate</div>
            {defectIsNA ? (
              <div className="text-slate-500 text-xs italic">Requires baseline data</div>
            ) : (
              <span className="text-3xl font-bold text-amber-400">{sixSigma.defectRate}</span>
            )}
            <div className="text-[11px] text-slate-500 mt-1">Defects per million opp.</div>
          </CardContent>
        </Card>

        {/* Process Capability */}
        <Card className={`border backdrop-blur-sm ${capabilityBg}`}>
          <CardContent className="p-4">
            <div className="text-xs text-slate-500 uppercase tracking-widest font-semibold mb-2">Process Capability</div>
            <div className={`text-2xl font-bold ${capabilityColor} mb-2`}>{capabilityLevel}</div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all duration-700 ${capabilityBarColor}`} style={{ width: capabilityWidth }} />
            </div>
            <div className="text-[11px] text-slate-500 mt-1">Overall capability rating</div>
          </CardContent>
        </Card>
      </div>

      {/* DMAIC Phases - 2 column grid */}
      {sixSigma.dmaic ? (
        <Card className="bg-slate-800/50 border-slate-700/60 backdrop-blur-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-white flex items-center gap-2">
              <Target className="h-4 w-4 text-cyan-400" />
              DMAIC Methodology
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {dmaicPhases.map((phase) => {
                const Icon = phase.icon;
                const content = (sixSigma.dmaic as any)?.[phase.key];
                const hasContent = content !== null && content !== undefined && content !== '';
                return (
                  <div key={phase.key} className="bg-slate-900/40 rounded-lg p-3 border border-slate-700/40 hover:border-slate-600/60 transition-colors">
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className={`w-6 h-6 rounded flex items-center justify-center ${phase.bg}`}>
                        <Icon className={`h-3.5 w-3.5 ${phase.color}`} />
                      </div>
                      <span className={`text-xs font-bold uppercase tracking-widest ${phase.color}`}>{phase.label}</span>
                    </div>
                    <div className="text-slate-300 text-xs leading-relaxed pl-8">
                      {hasContent ? renderContent(content) : <span className="text-slate-600 italic">No data available</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="bg-slate-800/50 border-slate-700/60 backdrop-blur-sm">
          <CardContent className="p-6 text-center">
            <p className="text-slate-500 text-sm italic">DMAIC data not available — DMADV methodology may have been applied.</p>
          </CardContent>
        </Card>
      )}

      {/* Root Causes */}
      {(() => {
        const rawCauses = sixSigma.rootCauses || (sixSigma.dmaic as any)?.analyze?.rootCauses || [];
        const causes: string[] = Array.isArray(rawCauses)
          ? rawCauses.map((c: any) => typeof c === 'object' && c !== null ? (c.cause || JSON.stringify(c)) : String(c))
          : [];
        if (causes.length === 0) return null;
        return (
          <Card className="bg-slate-800/50 border-slate-700/60 backdrop-blur-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-white flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-400" />
                Root Causes Identified
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {causes.map((cause, index) => (
                  <div key={index} className="flex items-start gap-2 p-3 bg-red-500/8 rounded-lg border border-red-500/20">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-red-500/20 text-red-400 text-[10px] font-bold flex items-center justify-center mt-0.5">
                      {index + 1}
                    </span>
                    <p className="text-slate-300 text-xs leading-relaxed">{cause}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        );
      })()}
    </div>
  );
};

export default SixSigmaSection;

