import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Bot, Loader2, Play, Sparkles } from 'lucide-react';

import { api, type AgentRunResponse } from '@/services/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';

const defaultGoal = 'Decide how to reduce the defect rate fastest for the assembly line';
const defaultContext = JSON.stringify(
  {
    kpis: [
      { name: 'Defect Rate', value: 8.2, target: 2.0, unit: '%' },
      { name: 'First Pass Yield', value: 91.8, target: 98.0, unit: '%' },
    ],
    constraints: {
      deadline_days: 30,
      budget_usd: 50000,
    },
    notes: 'Pilot line data from the last four weeks.',
  },
  null,
  2,
);

const prettyJson = (value: unknown) => JSON.stringify(value ?? {}, null, 2);

const AgentLab = () => {
  const { toast } = useToast();
  const [goal, setGoal] = useState(defaultGoal);
  const [contextText, setContextText] = useState(defaultContext);
  const [isRunning, setIsRunning] = useState(false);
  const [response, setResponse] = useState<AgentRunResponse | null>(null);

  const runAgent = async () => {
    let parsedContext: Record<string, unknown>;

    try {
      const maybeContext = JSON.parse(contextText);
      if (!maybeContext || typeof maybeContext !== 'object' || Array.isArray(maybeContext)) {
        throw new Error('Context must be a JSON object.');
      }
      parsedContext = maybeContext as Record<string, unknown>;
    } catch (error) {
      toast({
        title: 'Invalid context JSON',
        description: error instanceof Error ? error.message : 'Provide a valid JSON object before running the agent.',
        variant: 'destructive',
      });
      return;
    }

    setIsRunning(true);
    try {
      const result = await api.runAgent(goal, parsedContext);
      setResponse(result);
      toast({
        title: result.status === 'success' ? 'Agent run completed' : 'Agent run failed',
        description: result.status === 'success'
          ? `Captured ${result.steps.length} step${result.steps.length === 1 ? '' : 's'}.`
          : String(result.final_result?.error ?? 'The agent returned a failure status.'),
        variant: result.status === 'success' ? 'default' : 'destructive',
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown request failure';
      toast({
        title: 'Agent request failed',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.16),_transparent_35%),radial-gradient(circle_at_top_right,_rgba(45,212,191,0.14),_transparent_30%),linear-gradient(180deg,_#020617_0%,_#0f172a_52%,_#111827_100%)] px-6 py-8 text-white">
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-3">
            <Link to="/" className="inline-flex items-center gap-2 text-sm text-cyan-200 hover:text-cyan-100">
              <ArrowLeft className="h-4 w-4" />
              Back to Home
            </Link>
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-sm text-cyan-100">
              <Sparkles className="h-4 w-4" />
              Agent Lab
            </div>
            <div>
              <h1 className="text-4xl font-bold tracking-tight">GodMode Agent Console</h1>
              <p className="mt-2 max-w-3xl text-slate-300">
                Run the backend planner against a real goal, inspect each tool step, and review the final structured output.
              </p>
            </div>
          </div>

          <Card className="border-cyan-500/20 bg-slate-900/70 shadow-2xl shadow-cyan-950/20">
            <CardContent className="flex items-center gap-3 p-4">
              <div className="rounded-xl bg-cyan-400/15 p-3 text-cyan-200">
                <Bot className="h-6 w-6" />
              </div>
              <div>
                <div className="text-sm text-slate-400">Endpoint</div>
                <div className="font-mono text-sm text-cyan-100">POST /api/v2/agent/run</div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <Card className="border-slate-700/80 bg-slate-900/70 shadow-xl shadow-slate-950/30">
            <CardHeader>
              <CardTitle>Run Configuration</CardTitle>
              <CardDescription className="text-slate-400">
                Provide a high-level goal and a JSON object for the planner context.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="goal">Goal</Label>
                <Input
                  id="goal"
                  value={goal}
                  onChange={(event) => setGoal(event.target.value)}
                  className="border-slate-700 bg-slate-950/70 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="context">Context JSON</Label>
                <Textarea
                  id="context"
                  value={contextText}
                  onChange={(event) => setContextText(event.target.value)}
                  className="min-h-[320px] border-slate-700 bg-slate-950/70 font-mono text-sm text-cyan-50"
                />
              </div>

              <div className="flex flex-wrap gap-3">
                <Button
                  onClick={runAgent}
                  disabled={isRunning || !goal.trim()}
                  className="bg-gradient-to-r from-cyan-500 to-teal-500 text-white hover:from-cyan-600 hover:to-teal-600"
                >
                  {isRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                  Run Agent
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setGoal(defaultGoal);
                    setContextText(defaultContext);
                  }}
                  className="border-slate-700 bg-transparent text-slate-100 hover:bg-slate-800"
                >
                  Reset Example
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className="border-slate-700/80 bg-slate-900/70 shadow-xl shadow-slate-950/30">
              <CardHeader>
                <CardTitle>Execution Summary</CardTitle>
                <CardDescription className="text-slate-400">
                  Step-by-step planner activity from the latest agent run.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!response ? (
                  <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-6 text-sm text-slate-400">
                    No run yet. Use the default sample or paste your own goal and context.
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950/50 px-4 py-3">
                      <div>
                        <div className="text-sm text-slate-400">Status</div>
                        <div className="text-lg font-semibold text-white">{response.status}</div>
                      </div>
                      <Badge variant={response.status === 'success' ? 'default' : 'destructive'}>
                        {response.steps.length} step{response.steps.length === 1 ? '' : 's'}
                      </Badge>
                    </div>

                    <div className="space-y-3">
                      {response.steps.map((step) => (
                        <div key={step.step} className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                          <div className="mb-2 flex items-center justify-between gap-3">
                            <div className="text-sm font-semibold text-cyan-100">Step {step.step}</div>
                            <Badge variant="outline" className="border-cyan-500/40 text-cyan-100">
                              {step.action || 'final'}
                            </Badge>
                          </div>
                          {step.thought && <p className="mb-3 text-sm text-slate-300">{step.thought}</p>}
                          <div className="grid gap-3 xl:grid-cols-2">
                            <div>
                              <div className="mb-1 text-xs uppercase tracking-wide text-slate-500">Input</div>
                              <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-200">{prettyJson(step.input)}</pre>
                            </div>
                            <div>
                              <div className="mb-1 text-xs uppercase tracking-wide text-slate-500">Result</div>
                              <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-200">{prettyJson(step.result || step.error)}</pre>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-slate-700/80 bg-slate-900/70 shadow-xl shadow-slate-950/30">
              <CardHeader>
                <CardTitle>Final Result</CardTitle>
                <CardDescription className="text-slate-400">
                  Structured response returned by the backend after the planner stops.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="min-h-[220px] overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs text-cyan-50">
                  {prettyJson(response?.final_result ?? { message: 'Run the agent to inspect the final_result payload.' })}
                </pre>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentLab;