import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';
import { analyzeSixSigma, type SixSigmaAnalyzeResponse } from '@/api/sixSigmaClient';

const PLACEHOLDER_DATA = '5.1, 5.3, 4.9, 5.0, 5.2, 4.8, 5.4, 5.1, 5.0, 5.3, 4.7, 5.2, 5.1, 4.9, 5.0';

const SixSigmaPage: React.FC = () => {
  const [dataInput, setDataInput] = useState('');
  const [usl, setUsl] = useState('10');
  const [lsl, setLsl] = useState('0');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SixSigmaAnalyzeResponse | null>(null);
  const { toast } = useToast();

  const handleAnalyze = async () => {
    const raw = dataInput.trim();
    if (!raw) {
      toast({ title: 'Missing data', description: 'Enter comma-separated process measurements.', variant: 'destructive' });
      return;
    }

    const values = raw.split(',').map((s) => parseFloat(s.trim())).filter((n) => !isNaN(n));
    if (values.length === 0) {
      toast({ title: 'Invalid data', description: 'Could not parse any numeric values.', variant: 'destructive' });
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const res = await analyzeSixSigma({
        data: values,
        usl: parseFloat(usl) || 10,
        lsl: parseFloat(lsl) || 0,
      });
      setResult(res);
    } catch (err: any) {
      toast({ title: 'Analysis failed', description: err.message ?? 'Unknown error', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6 space-y-6 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold tracking-tight">Six Sigma Analysis</h1>

      <Card>
        <CardHeader><CardTitle>Process Capability Input</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm text-muted-foreground mb-1 block">Process Measurements (comma-separated)</label>
            <textarea
              className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder={PLACEHOLDER_DATA}
              value={dataInput}
              onChange={(e) => setDataInput(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Upper Spec Limit (USL)</label>
              <Input type="number" value={usl} onChange={(e) => setUsl(e.target.value)} />
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Lower Spec Limit (LSL)</label>
              <Input type="number" value={lsl} onChange={(e) => setLsl(e.target.value)} />
            </div>
          </div>
          <Button onClick={handleAnalyze} disabled={loading}>
            {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Analyze
          </Button>
        </CardContent>
      </Card>

      {result && (
        <>
          {/* Metrics summary */}
          <Card>
            <CardHeader><CardTitle>Process Capability Metrics</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                {Object.entries(result.metrics).map(([key, val]) => (
                  <div key={key} className="border rounded-md p-3">
                    <p className="text-xs text-muted-foreground uppercase">{key.replace(/_/g, ' ')}</p>
                    <p className="text-lg font-semibold">{val != null ? (typeof val === 'number' ? val.toFixed(4) : String(val)) : 'N/A'}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Warnings */}
          {result.warnings.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Rule Violations</CardTitle></CardHeader>
              <CardContent>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="py-2 pr-4">Rule</th>
                      <th className="py-2 pr-4">Description</th>
                      <th className="py-2 pr-4">Severity</th>
                      <th className="py-2">Indices</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.warnings.map((w, i) => (
                      <tr key={i} className="border-b">
                        <td className="py-2 pr-4 font-medium">{w.rule}</td>
                        <td className="py-2 pr-4">{w.description}</td>
                        <td className="py-2 pr-4">{w.severity}</td>
                        <td className="py-2">{w.indices.join(', ')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}

          {/* Recommendations */}
          {result.recommendations.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Recommendations</CardTitle></CardHeader>
              <CardContent>
                <ul className="list-disc pl-5 space-y-1 text-sm">
                  {result.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default SixSigmaPage;
