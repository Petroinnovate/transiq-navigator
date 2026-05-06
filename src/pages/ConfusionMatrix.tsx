import React, { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Upload, Loader2, BarChart3, AlertTriangle, FileSpreadsheet } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import axiosInstance from '@/lib/axios';
import ConfusionHeatmap from '@/components/confusion/ConfusionHeatmap';
import MetricsPanel from '@/components/confusion/MetricsPanel';

// ── Types ────────────────────────────────────────────────────────────────────

interface AnalysisResult {
  confusion_matrix: number[][];
  confusion_matrix_norm: number[][] | null;
  labels: string[];
  n_classes: number;
  total_samples: number;
  metrics: {
    accuracy: number;
    precision_macro: number;
    recall_macro: number;
    f1_macro: number;
    precision_weighted: number;
    recall_weighted: number;
    f1_weighted: number;
  };
  per_class_metrics: {
    class: string;
    precision: number;
    recall: number;
    f1_score: number;
    support: number;
  }[];
  top_errors: {
    actual: string;
    predicted: string;
    count: number;
    pct_of_actual: number;
  }[];
  risk_flags: { type: string; severity: string; message: string }[];
  insights: string[];
  threshold_analysis: {
    optimal_threshold: number;
    best_f1: number;
    best_precision: number;
    best_recall: number;
    note: string;
  } | null;
  domain: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

const ConfusionMatrixPage: React.FC = () => {
  const { toast } = useToast();
  const fileRef = useRef<HTMLInputElement>(null);

  const [file, setFile]         = useState<File | null>(null);
  const [normalize, setNormalize] = useState(false);
  const [useCase, setUseCase]   = useState('oil_gas');
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState<AnalysisResult | null>(null);
  const [error, setError]       = useState<string | null>(null);

  // ── Manual JSON input (quick test) ───────────────────────────────────────
  const [jsonMode, setJsonMode] = useState(false);
  const [yTrue, setYTrue]       = useState('[0,1,1,0,1,0,1]');
  const [yPred, setYPred]       = useState('[0,1,0,0,1,1,1]');

  // ── File handling ─────────────────────────────────────────────────────────
  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped?.name.endsWith('.csv')) setFile(dropped);
    else toast({ title: 'Only CSV files accepted', variant: 'destructive' });
  };

  // ── Submit CSV ─────────────────────────────────────────────────────────────
  const submitCsv = async () => {
    if (!file) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      // Pass params as query string — same pattern as all other endpoints in this app
      const params = new URLSearchParams({
        normalize: String(normalize),
        use_case: useCase,
      });
      const res = await axiosInstance.post(
        `/api/v2/confusion-matrix/upload?${params.toString()}`,
        fd,
      );
      setResult(res.data.data);
      toast({ title: 'Analysis complete', description: `${res.data.filename}` });
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Analysis failed';
      setError(msg);
      toast({ title: 'Error', description: msg, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  // ── Submit JSON ─────────────────────────────────────────────────────────────
  const submitJson = async () => {
    let parsedTrue: unknown[], parsedPred: unknown[];
    try {
      parsedTrue = JSON.parse(yTrue);
      parsedPred = JSON.parse(yPred);
    } catch {
      toast({ title: 'Invalid JSON', description: 'Check y_true / y_pred arrays', variant: 'destructive' });
      return;
    }
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await axiosInstance.post('/api/v2/confusion-matrix', {
        y_true: parsedTrue,
        y_pred: parsedPred,
        normalize,
        use_case: useCase,
      });
      setResult(res.data.data);
      toast({ title: 'Analysis complete' });
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Analysis failed';
      setError(msg);
      toast({ title: 'Error', description: msg, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  // ── Download JSON report ──────────────────────────────────────────────────
  const downloadReport = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'confusion_matrix_report.json'; a.click();
    URL.revokeObjectURL(url);
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/upload">
              <Button variant="ghost" size="sm" className="gap-1.5 text-slate-400 hover:text-slate-100">
                <ArrowLeft className="h-4 w-4" /> Back
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                <BarChart3 className="h-6 w-6 text-violet-400" />
                Confusion Matrix Analysis
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                Upload a CSV or enter arrays — get full model performance + domain risk insights
              </p>
            </div>
          </div>
          {result && (
            <Button variant="outline" size="sm" onClick={downloadReport} className="border-slate-600 text-slate-300">
              Download JSON
            </Button>
          )}
        </div>

        {/* Input Card */}
        <Card className="bg-slate-900/60 border-slate-700/40">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base text-slate-200">Input Data</CardTitle>
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <span>CSV Upload</span>
                <Switch checked={jsonMode} onCheckedChange={setJsonMode} />
                <span>JSON Arrays</span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Options row */}
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex items-center gap-2">
                <Switch id="norm" checked={normalize} onCheckedChange={setNormalize} />
                <Label htmlFor="norm" className="text-sm text-slate-300">Show percentages</Label>
              </div>
              <div className="flex items-center gap-2">
                <Label className="text-sm text-slate-300">Domain</Label>
                <Select value={useCase} onValueChange={setUseCase}>
                  <SelectTrigger className="w-40 bg-slate-800 border-slate-600 text-slate-200 h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-600">
                    <SelectItem value="oil_gas">Oil &amp; Gas</SelectItem>
                    <SelectItem value="manufacturing">Manufacturing</SelectItem>
                    <SelectItem value="general">General</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* CSV Upload mode */}
            {!jsonMode && (
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer
                  ${file ? 'border-emerald-500/50 bg-emerald-900/10' : 'border-slate-600/50 hover:border-slate-500/60 bg-slate-800/20'}`}
                onDragOver={e => e.preventDefault()}
                onDrop={handleFileDrop}
                onClick={() => fileRef.current?.click()}
              >
                <input
                  ref={fileRef}
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={e => e.target.files?.[0] && setFile(e.target.files[0])}
                />
                <FileSpreadsheet className={`h-10 w-10 mx-auto mb-3 ${file ? 'text-emerald-400' : 'text-slate-600'}`} />
                {file ? (
                  <p className="text-emerald-300 font-medium">{file.name}</p>
                ) : (
                  <>
                    <p className="text-slate-300 font-medium">Drag &amp; drop a CSV file</p>
                    <p className="text-slate-500 text-sm mt-1">
                      Required columns: <code className="text-slate-400">actual</code>, <code className="text-slate-400">predicted</code>
                      &nbsp;— optional: <code className="text-slate-400">probability</code>
                    </p>
                  </>
                )}
              </div>
            )}

            {/* JSON Input mode */}
            {jsonMode && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs text-slate-400">y_true (actual labels)</Label>
                  <textarea
                    className="w-full rounded-lg border border-slate-600 bg-slate-800 text-slate-200 text-sm p-3 font-mono resize-none focus:outline-none focus:border-violet-500"
                    rows={3}
                    value={yTrue}
                    onChange={e => setYTrue(e.target.value)}
                    placeholder="[0,1,1,0,1,0,1]"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-slate-400">y_pred (predicted labels)</Label>
                  <textarea
                    className="w-full rounded-lg border border-slate-600 bg-slate-800 text-slate-200 text-sm p-3 font-mono resize-none focus:outline-none focus:border-violet-500"
                    rows={3}
                    value={yPred}
                    onChange={e => setYPred(e.target.value)}
                    placeholder="[0,1,0,0,1,1,1]"
                  />
                </div>
              </div>
            )}

            <Button
              className="w-full bg-violet-600 hover:bg-violet-700 text-white"
              disabled={loading || (!jsonMode && !file)}
              onClick={jsonMode ? submitJson : submitCsv}
            >
              {loading ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Analysing...</>
              ) : (
                <><BarChart3 className="h-4 w-4 mr-2" /> Run Analysis</>
              )}
            </Button>

            {error && (
              <div className="flex items-center gap-2 rounded-lg border border-red-500/40 bg-red-900/20 px-3 py-2 text-sm text-red-300">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                {error}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results */}
        {result && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Heatmap */}
            <Card className="bg-slate-900/60 border-slate-700/40">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base text-slate-200">Confusion Matrix</CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] border-slate-600 text-slate-400">
                      {result.n_classes}-class
                    </Badge>
                    <Badge variant="outline" className="text-[10px] border-slate-600 text-slate-400 capitalize">
                      {result.domain.replace('_', ' ')}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ConfusionHeatmap
                  matrix={result.confusion_matrix}
                  labels={result.labels}
                  normalized={normalize ? result.confusion_matrix_norm : null}
                />
              </CardContent>
            </Card>

            {/* Metrics */}
            <Card className="bg-slate-900/60 border-slate-700/40">
              <CardHeader className="pb-2">
                <CardTitle className="text-base text-slate-200">Performance &amp; Risk Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <MetricsPanel
                  metrics={result.metrics}
                  perClassMetrics={result.per_class_metrics}
                  riskFlags={result.risk_flags}
                  insights={result.insights}
                  topErrors={result.top_errors}
                  thresholdAnalysis={result.threshold_analysis}
                  totalSamples={result.total_samples}
                />
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConfusionMatrixPage;
