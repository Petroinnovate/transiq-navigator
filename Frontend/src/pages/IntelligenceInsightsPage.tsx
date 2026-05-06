import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';
import {
  getIntelligenceDashboard,
  getImpactNetwork,
  type DashboardSummary,
  type ImpactNetworkResult,
} from '@/api/intelligenceClient';

const IntelligenceInsightsPage: React.FC = () => {
  const [kpiId, setKpiId] = useState('');
  const [dashLoading, setDashLoading] = useState(false);
  const [netLoading, setNetLoading] = useState(false);
  const [dashData, setDashData] = useState<DashboardSummary | null>(null);
  const [netData, setNetData] = useState<ImpactNetworkResult | null>(null);
  const { toast } = useToast();

  const handleLoadDashboard = async () => {
    if (!kpiId.trim()) {
      toast({ title: 'Missing KPI ID', description: 'Enter a KPI ID first.', variant: 'destructive' });
      return;
    }
    setDashLoading(true);
    setDashData(null);
    try {
      const data = await getIntelligenceDashboard(kpiId.trim());
      setDashData(data);
    } catch (err: any) {
      toast({ title: 'Failed to load dashboard', description: err.message ?? 'Unknown error', variant: 'destructive' });
    } finally {
      setDashLoading(false);
    }
  };

  const handleLoadNetwork = async () => {
    if (!kpiId.trim()) {
      toast({ title: 'Missing KPI ID', description: 'Enter a KPI ID first.', variant: 'destructive' });
      return;
    }
    setNetLoading(true);
    setNetData(null);
    try {
      const data = await getImpactNetwork(kpiId.trim());
      setNetData(data);
    } catch (err: any) {
      toast({ title: 'Failed to load network', description: err.message ?? 'Unknown error', variant: 'destructive' });
    } finally {
      setNetLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6 space-y-6 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold tracking-tight">Intelligence Insights</h1>

      <Card>
        <CardHeader><CardTitle>KPI Lookup</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm text-muted-foreground mb-1 block">KPI ID</label>
            <Input placeholder="e.g. kpi_001" value={kpiId} onChange={(e) => setKpiId(e.target.value)} />
          </div>
          <div className="flex gap-3">
            <Button onClick={handleLoadDashboard} disabled={dashLoading}>
              {dashLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Load Dashboard
            </Button>
            <Button variant="outline" onClick={handleLoadNetwork} disabled={netLoading}>
              {netLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Load Impact Network
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Dashboard Summary */}
      {dashData && (
        <Card>
          <CardHeader><CardTitle>Dashboard — {dashData.kpi_name}</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-4">
              <Metric label="Total Impact" value={`$${dashData.total_impact.toLocaleString()}`} />
              <Metric label="Direct Impact" value={`$${dashData.direct_impact.toLocaleString()}`} />
              <Metric label="Cascading Impact" value={`$${dashData.cascading_impact.toLocaleString()}`} />
              <Metric label="Affected Entities" value={String(dashData.affected_entities_count)} />
              <Metric label="Confidence" value={`${(dashData.confidence_score * 100).toFixed(1)}%`} />
              <Metric label="Timestamp" value={dashData.timestamp} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground uppercase mb-1">Primary Drivers</p>
                <ul className="list-disc pl-5 text-sm space-y-0.5">
                  {dashData.primary_drivers.map((d, i) => <li key={i}>{d}</li>)}
                </ul>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase mb-1">Affected Departments</p>
                <ul className="list-disc pl-5 text-sm space-y-0.5">
                  {dashData.affected_departments.map((d, i) => <li key={i}>{d}</li>)}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Impact Network */}
      {netData && (
        <Card>
          <CardHeader><CardTitle>Impact Network</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {/* Stats row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {Object.entries(netData.stats).map(([key, val]) => (
                <div key={key} className="border rounded-md p-2">
                  <p className="text-xs text-muted-foreground uppercase">{key.replace(/_/g, ' ')}</p>
                  <p className="text-sm font-semibold">{typeof val === 'number' ? val.toLocaleString() : String(val)}</p>
                </div>
              ))}
            </div>

            {/* Nodes table */}
            <div>
              <p className="text-sm font-medium mb-2">Nodes ({netData.nodes.length})</p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="py-2 pr-4">Label</th>
                    <th className="py-2 pr-4">Type</th>
                    <th className="py-2 pr-4">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {netData.nodes.map((n) => (
                    <tr key={n.id} className="border-b">
                      <td className="py-1.5 pr-4">{n.label}</td>
                      <td className="py-1.5 pr-4">{n.type}</td>
                      <td className="py-1.5 pr-4">{n.value.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Edges table */}
            <div>
              <p className="text-sm font-medium mb-2">Edges ({netData.edges.length})</p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="py-2 pr-4">Source</th>
                    <th className="py-2 pr-4">→</th>
                    <th className="py-2 pr-4">Target</th>
                    <th className="py-2 pr-4">Type</th>
                    <th className="py-2">Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {netData.edges.map((e, i) => (
                    <tr key={i} className="border-b">
                      <td className="py-1.5 pr-4">{e.source}</td>
                      <td className="py-1.5 pr-4">→</td>
                      <td className="py-1.5 pr-4">{e.target}</td>
                      <td className="py-1.5 pr-4">{e.label}</td>
                      <td className="py-1.5">{e.weight.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

const Metric: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="border rounded-md p-3">
    <p className="text-xs text-muted-foreground uppercase">{label}</p>
    <p className="text-lg font-semibold">{value}</p>
  </div>
);

export default IntelligenceInsightsPage;
