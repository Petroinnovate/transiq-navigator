import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Activity, Database, Brain, AlertTriangle, Clock, Server,
  CheckCircle2, XCircle, ArrowLeft, RefreshCcw, BarChart3,
  Gauge, Layers, TrendingUp, Shield
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend,
} from 'recharts';
import {
  fetchSystemHealth, fetchModelRegistry, fetchFeatureStore,
  fetchPredictions, fetchDriftStatus,
  type SystemHealth, type ModelRegistry, type FeatureStore,
  type PredictionStats, type DriftStatus,
} from '@/api/observabilityClient';

// ── Health Status Icon ──────────────────────────────────────────────────────

const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  if (status === 'healthy' || status === 'ok' || status === 'connected')
    return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
  if (status === 'degraded' || status === 'warning')
    return <AlertTriangle className="h-4 w-4 text-yellow-400" />;
  return <XCircle className="h-4 w-4 text-red-400" />;
};

const statusColor = (status: string) => {
  if (status === 'healthy' || status === 'ok' || status === 'connected') return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
  if (status === 'degraded' || status === 'warning') return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
  return 'bg-red-500/20 text-red-400 border-red-500/30';
};

// ── System Health Panel ─────────────────────────────────────────────────────

const SystemHealthPanel: React.FC<{ data?: SystemHealth; isLoading: boolean }> = ({ data, isLoading }) => {
  if (isLoading) return <Skeleton className="h-48 w-full" />;
  if (!data) return <div className="text-slate-400 text-center py-8">No health data available</div>;

  const checks = Object.entries(data.checks);
  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <Server className="h-5 w-5 text-cyan-400" />
          System Health
          <Badge className={`ml-auto ${statusColor(data.status)}`}>{data.status.toUpperCase()}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {checks.map(([name, check]) => (
            <div key={name} className="bg-slate-700/40 rounded-lg p-3 flex flex-col items-center gap-1">
              <StatusIcon status={check.status} />
              <span className="text-xs font-medium text-slate-300 capitalize">{name.replace('_', ' ')}</span>
              <Badge variant="outline" className={`text-xs ${statusColor(check.status)}`}>
                {check.status}
              </Badge>
              {check.latency_ms !== undefined && (
                <span className="text-xs text-slate-500">{check.latency_ms}ms</span>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

// ── Model Registry Panel ────────────────────────────────────────────────────

const ModelRegistryPanel: React.FC<{ data?: ModelRegistry; isLoading: boolean }> = ({ data, isLoading }) => {
  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data || data.models.length === 0) return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardContent className="py-12 text-center text-slate-400">
        <Brain className="h-12 w-12 mx-auto mb-3 opacity-40" />
        No models registered yet
      </CardContent>
    </Card>
  );

  const stageCounts = data.models.reduce<Record<string, number>>((acc, m) => {
    acc[m.stage] = (acc[m.stage] || 0) + 1;
    return acc;
  }, {});
  const pieData = Object.entries(stageCounts).map(([name, value]) => ({ name, value }));
  const COLORS = ['#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <Brain className="h-5 w-5 text-cyan-400" />
          Model Registry
          <Badge variant="outline" className="ml-auto text-cyan-400 border-cyan-500/30">{data.total} models</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Stage distribution pie */}
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          {/* Model table */}
          <div className="lg:col-span-2 overflow-auto max-h-48">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-1 px-2">Name</th>
                  <th className="text-left py-1 px-2">Version</th>
                  <th className="text-left py-1 px-2">Stage</th>
                  <th className="text-left py-1 px-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.models.map(m => (
                  <tr key={m.model_id} className="border-b border-slate-700/50 text-slate-300 hover:bg-slate-700/30">
                    <td className="py-1.5 px-2 font-medium">{m.name}</td>
                    <td className="py-1.5 px-2"><Badge variant="outline" className="text-xs">{m.version}</Badge></td>
                    <td className="py-1.5 px-2">
                      <Badge className={`text-xs ${m.stage === 'production' ? 'bg-emerald-500/20 text-emerald-400' : m.stage === 'staging' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-slate-500/20 text-slate-400'}`}>
                        {m.stage}
                      </Badge>
                    </td>
                    <td className="py-1.5 px-2 text-xs text-slate-500">{new Date(m.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// ── Feature Store Panel ─────────────────────────────────────────────────────

const FeatureStorePanel: React.FC<{ data?: FeatureStore; isLoading: boolean }> = ({ data, isLoading }) => {
  if (isLoading) return <Skeleton className="h-48 w-full" />;
  if (!data || data.features.length === 0) return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardContent className="py-12 text-center text-slate-400">
        <Layers className="h-12 w-12 mx-auto mb-3 opacity-40" />
        No features registered
      </CardContent>
    </Card>
  );

  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <Layers className="h-5 w-5 text-cyan-400" />
          Feature Store
          <div className="ml-auto flex gap-2">
            <Badge variant="outline" className="text-cyan-400 border-cyan-500/30">{data.total} features</Badge>
            {data.stale_count > 0 && (
              <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">{data.stale_count} stale</Badge>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 max-h-48 overflow-auto">
          {data.features.map(f => (
            <div key={f.name} className="flex items-center justify-between bg-slate-700/30 rounded-lg p-2.5">
              <div>
                <span className="text-sm font-medium text-slate-200">{f.name}</span>
                <span className="text-xs text-slate-500 ml-2">v{f.version} &middot; {f.row_count.toLocaleString()} rows</span>
              </div>
              <div className="flex items-center gap-2">
                {f.stale ? (
                  <Badge className="text-xs bg-yellow-500/20 text-yellow-400">Stale ({Math.round(f.staleness_hours)}h)</Badge>
                ) : (
                  <Badge className="text-xs bg-emerald-500/20 text-emerald-400">Fresh</Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

// ── Predictions Panel ───────────────────────────────────────────────────────

const PredictionsPanel: React.FC<{ data?: PredictionStats; isLoading: boolean }> = ({ data, isLoading }) => {
  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data || data.count === 0) return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardContent className="py-12 text-center text-slate-400">
        <Gauge className="h-12 w-12 mx-auto mb-3 opacity-40" />
        No prediction logs available
      </CardContent>
    </Card>
  );

  // Build latency chart from recent predictions
  const latencyData = data.recent.slice(-30).map((p, i) => ({
    idx: i + 1,
    latency: p.latency_ms,
    confidence: Math.round(p.confidence * 100),
  }));

  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <Gauge className="h-5 w-5 text-cyan-400" />
          Prediction Logs
          <Badge variant="outline" className="ml-auto text-cyan-400 border-cyan-500/30">{data.count} total</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* KPI row */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          {[
            { label: 'Avg Latency', value: `${data.stats.avg_latency_ms.toFixed(0)}ms`, color: 'text-cyan-400' },
            { label: 'P95 Latency', value: `${data.stats.p95_latency_ms.toFixed(0)}ms`, color: 'text-yellow-400' },
            { label: 'Max Latency', value: `${data.stats.max_latency_ms.toFixed(0)}ms`, color: 'text-red-400' },
            { label: 'Avg Confidence', value: `${(data.stats.avg_confidence * 100).toFixed(1)}%`, color: 'text-emerald-400' },
            { label: 'Low Confidence', value: `${(data.stats.low_confidence_pct * 100).toFixed(1)}%`, color: 'text-orange-400' },
          ].map(kpi => (
            <div key={kpi.label} className="bg-slate-700/30 rounded-lg p-2 text-center">
              <div className={`text-lg font-bold ${kpi.color}`}>{kpi.value}</div>
              <div className="text-xs text-slate-500">{kpi.label}</div>
            </div>
          ))}
        </div>
        {/* Latency chart */}
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={latencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="idx" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }} />
              <Area type="monotone" dataKey="latency" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.15} name="Latency (ms)" />
              <Area type="monotone" dataKey="confidence" stroke="#10b981" fill="#10b981" fillOpacity={0.1} name="Confidence %" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

// ── Drift Monitor Panel ─────────────────────────────────────────────────────

const DriftMonitorPanel: React.FC<{ data?: DriftStatus; isLoading: boolean }> = ({ data, isLoading }) => {
  if (isLoading) return <Skeleton className="h-48 w-full" />;
  if (!data) return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardContent className="py-12 text-center text-slate-400">
        <TrendingUp className="h-12 w-12 mx-auto mb-3 opacity-40" />
        No drift data available
      </CardContent>
    </Card>
  );

  const alerts = data.alerts || [];
  const severityColor: Record<string, string> = {
    critical: 'bg-red-500/20 text-red-400 border-red-500/30',
    high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  };

  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <Shield className="h-5 w-5 text-cyan-400" />
          Drift Monitor
          {alerts.length > 0 && (
            <Badge className="ml-auto bg-red-500/20 text-red-400">{alerts.length} alerts</Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <div className="text-center py-6 text-emerald-400 flex flex-col items-center gap-2">
            <CheckCircle2 className="h-8 w-8" />
            <span>No drift detected — models are stable</span>
          </div>
        ) : (
          <div className="space-y-2 max-h-48 overflow-auto">
            {alerts.map((alert, i) => (
              <div key={i} className="flex items-start gap-3 bg-slate-700/30 rounded-lg p-3">
                <AlertTriangle className={`h-4 w-4 mt-0.5 ${alert.severity === 'critical' || alert.severity === 'high' ? 'text-red-400' : 'text-yellow-400'}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-200">{alert.metric}</span>
                    <Badge className={`text-xs ${severityColor[alert.severity] || severityColor.low}`}>{alert.severity}</Badge>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">{alert.message}</p>
                </div>
                <span className="text-xs text-slate-500 whitespace-nowrap">{new Date(alert.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ── Main Observability Page ─────────────────────────────────────────────────

const Observability: React.FC = () => {
  const healthQ = useQuery({ queryKey: ['obs-health'], queryFn: fetchSystemHealth, refetchInterval: 30_000 });
  const modelsQ = useQuery({ queryKey: ['obs-models'], queryFn: fetchModelRegistry, refetchInterval: 60_000 });
  const featuresQ = useQuery({ queryKey: ['obs-features'], queryFn: fetchFeatureStore, refetchInterval: 60_000 });
  const predsQ = useQuery({ queryKey: ['obs-predictions'], queryFn: () => fetchPredictions(100), refetchInterval: 30_000 });
  const driftQ = useQuery({ queryKey: ['obs-drift'], queryFn: fetchDriftStatus, refetchInterval: 30_000 });

  const refetchAll = () => {
    healthQ.refetch();
    modelsQ.refetch();
    featuresQ.refetch();
    predsQ.refetch();
    driftQ.refetch();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/">
              <Button variant="ghost" size="sm" className="text-cyan-400 hover:text-cyan-300">
                <ArrowLeft className="h-4 w-4 mr-1" /> Home
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Activity className="h-6 w-6 text-cyan-400" />
              <h1 className="text-2xl font-bold text-white">Observability</h1>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={refetchAll} className="text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/10">
            <RefreshCcw className="h-4 w-4 mr-1" /> Refresh
          </Button>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="bg-slate-800/80 border border-slate-700">
            <TabsTrigger value="overview" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Overview</TabsTrigger>
            <TabsTrigger value="models" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Models</TabsTrigger>
            <TabsTrigger value="features" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Features</TabsTrigger>
            <TabsTrigger value="predictions" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Predictions</TabsTrigger>
            <TabsTrigger value="drift" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Drift</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4 mt-4">
            <SystemHealthPanel data={healthQ.data} isLoading={healthQ.isLoading} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <ModelRegistryPanel data={modelsQ.data} isLoading={modelsQ.isLoading} />
              <DriftMonitorPanel data={driftQ.data} isLoading={driftQ.isLoading} />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <FeatureStorePanel data={featuresQ.data} isLoading={featuresQ.isLoading} />
              <PredictionsPanel data={predsQ.data} isLoading={predsQ.isLoading} />
            </div>
          </TabsContent>

          <TabsContent value="models" className="mt-4">
            <ModelRegistryPanel data={modelsQ.data} isLoading={modelsQ.isLoading} />
          </TabsContent>

          <TabsContent value="features" className="mt-4">
            <FeatureStorePanel data={featuresQ.data} isLoading={featuresQ.isLoading} />
          </TabsContent>

          <TabsContent value="predictions" className="mt-4">
            <PredictionsPanel data={predsQ.data} isLoading={predsQ.isLoading} />
          </TabsContent>

          <TabsContent value="drift" className="mt-4">
            <DriftMonitorPanel data={driftQ.data} isLoading={driftQ.isLoading} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Observability;
