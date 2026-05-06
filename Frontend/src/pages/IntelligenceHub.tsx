import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, Zap, Target, GitBranch, Lightbulb, Play,
  ChevronDown, ChevronRight, AlertTriangle, Clock, DollarSign,
  TrendingUp, Shield, Layers
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger
} from '@/components/ui/collapsible';
import {
  ResponsiveContainer, Sankey, Tooltip, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Cell
} from 'recharts';
import {
  getDMAIC, getRecommendations, getScenario,
  type DMAICResult, type RecommendationsResult, type ScenarioResult,
  type Recommendation
} from '@/api/intelligenceClient';

// ── DMAIC Panel ─────────────────────────────────────────────────────────────

const phaseIcons: Record<string, React.ReactNode> = {
  define_phase: <Target className="h-4 w-4 text-cyan-400" />,
  measure_phase: <TrendingUp className="h-4 w-4 text-blue-400" />,
  analyze_phase: <Zap className="h-4 w-4 text-violet-400" />,
  improve_phase: <Lightbulb className="h-4 w-4 text-emerald-400" />,
  control_phase: <Shield className="h-4 w-4 text-yellow-400" />,
};

const phaseLabels: Record<string, string> = {
  define_phase: 'Define',
  measure_phase: 'Measure',
  analyze_phase: 'Analyze',
  improve_phase: 'Improve',
  control_phase: 'Control',
};

const DMAICPanel: React.FC<{ data?: DMAICResult; isLoading: boolean }> = ({ data, isLoading }) => {
  const [openPhase, setOpenPhase] = useState<string>('define_phase');

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data) return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardContent className="py-12 text-center text-slate-400">
        <Layers className="h-12 w-12 mx-auto mb-3 opacity-40" />
        Enter a KPI ID to view DMAIC analysis
      </CardContent>
    </Card>
  );

  const phases = ['define_phase', 'measure_phase', 'analyze_phase', 'improve_phase', 'control_phase'] as const;

  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <GitBranch className="h-5 w-5 text-cyan-400" />
          DMAIC Analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {/* Phase progress bar */}
        <div className="flex gap-1 mb-4">
          {phases.map((phase, i) => (
            <button
              key={phase}
              onClick={() => setOpenPhase(phase)}
              className={`flex-1 h-2 rounded-full transition-colors ${
                phase === openPhase ? 'bg-cyan-400' : i <= phases.indexOf(openPhase as typeof phases[number]) ? 'bg-cyan-400/40' : 'bg-slate-700'
              }`}
            />
          ))}
        </div>
        {/* Accordion */}
        {phases.map(phase => {
          const phaseData = data[phase];
          if (!phaseData) return null;
          return (
            <Collapsible key={phase} open={openPhase === phase} onOpenChange={open => open && setOpenPhase(phase)}>
              <CollapsibleTrigger className="flex items-center gap-2 w-full p-3 rounded-lg bg-slate-700/30 hover:bg-slate-700/50 transition-colors">
                {phaseIcons[phase]}
                <span className="text-sm font-medium text-slate-200">{phaseLabels[phase]}</span>
                <span className="text-xs text-slate-500 ml-auto mr-2">{phaseData.title}</span>
                {openPhase === phase ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-1 p-3 bg-slate-700/20 rounded-lg">
                <p className="text-sm text-slate-300 mb-2">{phaseData.description}</p>
                {phaseData.findings.length > 0 && (
                  <ul className="space-y-1">
                    {phaseData.findings.map((f, i) => (
                      <li key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                        <span className="text-cyan-400 mt-0.5">•</span> {f}
                      </li>
                    ))}
                  </ul>
                )}
              </CollapsibleContent>
            </Collapsible>
          );
        })}
        {data.summary && (
          <p className="text-xs text-slate-500 mt-3 italic">{data.summary}</p>
        )}
      </CardContent>
    </Card>
  );
};

// ── Recommendations Panel ───────────────────────────────────────────────────

const priorityColor: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
};

const RecommendationsPanel: React.FC<{ data?: RecommendationsResult; isLoading: boolean }> = ({ data, isLoading }) => {
  if (isLoading) return <Skeleton className="h-48 w-full" />;
  if (!data || data.recommendations.length === 0) return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardContent className="py-12 text-center text-slate-400">
        <Lightbulb className="h-12 w-12 mx-auto mb-3 opacity-40" />
        Enter an entity ID to view recommendations
      </CardContent>
    </Card>
  );

  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <Lightbulb className="h-5 w-5 text-cyan-400" />
          Recommendations
          <Badge variant="outline" className="ml-auto text-cyan-400 border-cyan-500/30">{data.recommendations.length}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 max-h-80 overflow-auto">
          {data.recommendations.map((rec, i) => (
            <div key={i} className="bg-slate-700/30 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Badge className={`text-xs ${priorityColor[rec.priority] || priorityColor.low}`}>{rec.priority}</Badge>
                <Badge variant="outline" className="text-xs text-slate-400">{rec.engine}</Badge>
                {rec.timeline && <span className="text-xs text-slate-500 ml-auto flex items-center gap-1"><Clock className="h-3 w-3" />{rec.timeline}</span>}
              </div>
              <p className="text-sm text-slate-200">{rec.action}</p>
              {rec.impact_estimate && (
                <p className="text-xs text-emerald-400 mt-1 flex items-center gap-1">
                  <DollarSign className="h-3 w-3" /> {rec.impact_estimate}
                </p>
              )}
            </div>
          ))}
        </div>
        {data.next_steps.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-700">
            <span className="text-xs font-medium text-slate-400">Next Steps:</span>
            <ul className="mt-1 space-y-0.5">
              {data.next_steps.map((s, i) => (
                <li key={i} className="text-xs text-slate-500 flex items-start gap-1.5">
                  <span className="text-cyan-400 mt-0.5">{i + 1}.</span> {s}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ── Scenario Panel ──────────────────────────────────────────────────────────

const ScenarioPanel: React.FC<{ data?: ScenarioResult; isLoading: boolean }> = ({ data, isLoading }) => {
  if (isLoading) return <Skeleton className="h-48 w-full" />;
  if (!data) return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardContent className="py-12 text-center text-slate-400">
        <Play className="h-12 w-12 mx-auto mb-3 opacity-40" />
        Enter an entity ID to run what-if scenarios
      </CardContent>
    </Card>
  );

  const changes = data.key_changes || [];
  const chartData = changes.map(c => ({
    metric: c.metric.length > 15 ? c.metric.slice(0, 15) + '…' : c.metric,
    before: typeof c.before === 'number' ? c.before : 0,
    after: typeof c.after === 'number' ? c.after : 0,
  }));

  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <Play className="h-5 w-5 text-cyan-400" />
          Scenario: {data.scenario}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length > 0 && (
          <div className="h-48 mb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis type="category" dataKey="metric" width={110} tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }} />
                <Bar dataKey="before" fill="#64748b" name="Baseline" barSize={10} radius={[0, 4, 4, 0]} />
                <Bar dataKey="after" fill="#06b6d4" name="Projected" barSize={10} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        {data.recommendations.length > 0 && (
          <div className="space-y-1">
            {data.recommendations.map((r, i) => (
              <p key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                <Lightbulb className="h-3 w-3 text-cyan-400 mt-0.5 flex-shrink-0" /> {r}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ── Main Intelligence Hub Page ──────────────────────────────────────────────

const IntelligenceHub: React.FC = () => {
  const [entityId, setEntityId] = useState('');
  const [kpiId, setKpiId] = useState('');
  const [activeEntityId, setActiveEntityId] = useState('');
  const [activeKpiId, setActiveKpiId] = useState('');

  const dmaicQ = useQuery({
    queryKey: ['dmaic', activeKpiId],
    queryFn: () => getDMAIC(activeKpiId),
    enabled: !!activeKpiId,
  });

  const recsQ = useQuery({
    queryKey: ['recommendations', activeEntityId],
    queryFn: () => getRecommendations(activeEntityId),
    enabled: !!activeEntityId,
  });

  const scenarioQ = useQuery({
    queryKey: ['scenario', activeEntityId],
    queryFn: () => getScenario(activeEntityId),
    enabled: !!activeEntityId,
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Link to="/">
            <Button variant="ghost" size="sm" className="text-cyan-400 hover:text-cyan-300">
              <ArrowLeft className="h-4 w-4 mr-1" /> Home
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <Zap className="h-6 w-6 text-cyan-400" />
            <h1 className="text-2xl font-bold text-white">Intelligence Hub</h1>
          </div>
        </div>

        {/* Input controls */}
        <Card className="bg-slate-800/60 border-slate-700">
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">Entity ID (for Recommendations + Scenarios)</label>
                <div className="flex gap-2">
                  <Input
                    value={entityId}
                    onChange={e => setEntityId(e.target.value)}
                    placeholder="e.g. well-alpha-1"
                    className="bg-slate-700/50 border-slate-600 text-slate-200"
                  />
                  <Button
                    onClick={() => setActiveEntityId(entityId)}
                    disabled={!entityId}
                    className="bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 border-cyan-500/30"
                    variant="outline"
                  >
                    <Play className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">KPI ID (for DMAIC Analysis)</label>
                <div className="flex gap-2">
                  <Input
                    value={kpiId}
                    onChange={e => setKpiId(e.target.value)}
                    placeholder="e.g. rop-efficiency"
                    className="bg-slate-700/50 border-slate-600 text-slate-200"
                  />
                  <Button
                    onClick={() => setActiveKpiId(kpiId)}
                    disabled={!kpiId}
                    className="bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 border-cyan-500/30"
                    variant="outline"
                  >
                    <Play className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Tabs defaultValue="dmaic" className="w-full">
          <TabsList className="bg-slate-800/80 border border-slate-700">
            <TabsTrigger value="dmaic" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">DMAIC</TabsTrigger>
            <TabsTrigger value="recommendations" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Recommendations</TabsTrigger>
            <TabsTrigger value="scenario" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Scenario Planner</TabsTrigger>
          </TabsList>

          <TabsContent value="dmaic" className="mt-4">
            <DMAICPanel data={dmaicQ.data} isLoading={dmaicQ.isLoading} />
          </TabsContent>

          <TabsContent value="recommendations" className="mt-4">
            <RecommendationsPanel data={recsQ.data} isLoading={recsQ.isLoading} />
          </TabsContent>

          <TabsContent value="scenario" className="mt-4">
            <ScenarioPanel data={scenarioQ.data} isLoading={scenarioQ.isLoading} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default IntelligenceHub;
