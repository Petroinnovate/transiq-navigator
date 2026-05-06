import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';
import { updateDDRMetric, type MetricUpdateResponse } from '@/api/ddrClient';

const DDRMetricEditPage: React.FC = () => {
  const [metricId, setMetricId] = useState('');
  const [newValue, setNewValue] = useState('');
  const [reason, setReason] = useState('correction');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MetricUpdateResponse | null>(null);
  const { toast } = useToast();

  const handleUpdate = async () => {
    if (!metricId.trim()) {
      toast({ title: 'Missing ID', description: 'Enter a metric ID.', variant: 'destructive' });
      return;
    }
    if (!newValue.trim()) {
      toast({ title: 'Missing value', description: 'Enter the new metric value.', variant: 'destructive' });
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const res = await updateDDRMetric(metricId.trim(), {
        new_value: newValue.trim(),
        reason: reason.trim() || 'correction',
        source_method: 'manual',
        origin: 'system',
      });
      setResult(res);
      toast({ title: 'Metric updated', description: `${res.field_name} → ${res.value}` });
    } catch (err: any) {
      toast({ title: 'Update failed', description: err.message ?? 'Unknown error', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6 space-y-6 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold tracking-tight">DDR Metric Edit</h1>

      <Card>
        <CardHeader><CardTitle>Update Metric</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm text-muted-foreground mb-1 block">Metric ID</label>
            <Input placeholder="e.g. metric_123" value={metricId} onChange={(e) => setMetricId(e.target.value)} />
          </div>
          <div>
            <label className="text-sm text-muted-foreground mb-1 block">New Value</label>
            <Input placeholder="e.g. 24.5" value={newValue} onChange={(e) => setNewValue(e.target.value)} />
          </div>
          <div>
            <label className="text-sm text-muted-foreground mb-1 block">Reason</label>
            <Input placeholder="correction" value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
          <Button onClick={handleUpdate} disabled={loading}>
            {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Update Metric
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader><CardTitle>Update Result</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="border rounded-md p-3">
                <p className="text-xs text-muted-foreground uppercase">ID</p>
                <p className="text-sm font-semibold">{result.id}</p>
              </div>
              <div className="border rounded-md p-3">
                <p className="text-xs text-muted-foreground uppercase">Field</p>
                <p className="text-sm font-semibold">{result.field_name}</p>
              </div>
              <div className="border rounded-md p-3">
                <p className="text-xs text-muted-foreground uppercase">Value</p>
                <p className="text-sm font-semibold">{result.value}</p>
              </div>
              <div className="border rounded-md p-3">
                <p className="text-xs text-muted-foreground uppercase">Citation</p>
                <p className="text-sm font-semibold">{result.citation}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default DDRMetricEditPage;
