import React, { useState, useRef } from 'react';
import axios from '@/lib/axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BarChart3, AlertCircle, Loader2, Download, CheckCircle2, AlertTriangle, Info } from 'lucide-react';

// ── Types matching locked API contract ──────────────────────────────────

interface RuleViolation {
  rule: string;
  description: string;
  indices: number[];
  severity: string;
}

interface MetricsBlock {
  n: number;
  mean: number;
  std_dev: number;
  cp: number;
  cpk: number;
  cpu: number;
  cpl: number;
  sigma_short_term: number;
  sigma_long_term: number;
  dpmo: number;
  yield_pct: number;
  fraction_defective: number;
  sigma_level: number | null;
}

interface ChartDataBlock {
  values: number[];
  cl: number;
  ucl: number;
  lcl: number;
  mr_cl: number;
  mr_ucl: number;
  usl: number;
  lsl: number;
}

interface AnalyzeResult {
  analysis_type: string;
  inputs: Record<string, unknown>;
  metrics: MetricsBlock;
  chart_data: ChartDataBlock;
  warnings: RuleViolation[];
  recommendations: string[];
}

// ── Helpers ──────────────────────────────────────────────────────────────

const getSigmaColor = (level: number) =>
  level >= 6 ? 'text-emerald-400' :
  level >= 4 ? 'text-cyan-400' :
  level >= 3 ? 'text-yellow-400' :
              'text-red-400';

const getSigmaBg = (level: number) =>
  level >= 6 ? 'bg-emerald-500/20 border-emerald-500/30' :
  level >= 4 ? 'bg-cyan-500/20 border-cyan-500/30' :
  level >= 3 ? 'bg-yellow-500/20 border-yellow-500/30' :
              'bg-red-500/20 border-red-500/30';

const getCpkRating = (cpk: number) => {
  if (cpk >= 2.0) return { label: 'World Class', color: 'text-emerald-400', bg: 'bg-emerald-500/10' };
  if (cpk >= 1.33) return { label: 'Capable', color: 'text-cyan-400', bg: 'bg-cyan-500/10' };
  if (cpk >= 1.0) return { label: 'Marginal', color: 'text-yellow-400', bg: 'bg-yellow-500/10' };
  return { label: 'Incapable', color: 'text-red-400', bg: 'bg-red-500/10' };
};

// ── Component ────────────────────────────────────────────────────────────

const SixSigmaAnalyzer: React.FC = () => {
  const [dataInput, setDataInput] = useState('');
  const [usl, setUsl] = useState('10');
  const [lsl, setLsl] = useState('0');
  const [sigma, setSigma] = useState('');
  const [ppm, setPpm] = useState('');

  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const resultRef = useRef<HTMLDivElement>(null);

  // ── Client-side validation ──────────────────────────────────────────

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    const nums = dataInput.split(',').map(s => s.trim()).filter(s => s !== '').map(Number);
    if (nums.length === 0) errors.data = 'Enter at least one measurement.';
    else if (nums.some(isNaN)) errors.data = 'All values must be valid numbers.';

    const u = parseFloat(usl), l = parseFloat(lsl);
    if (isNaN(u)) errors.usl = 'Required.';
    if (isNaN(l)) errors.lsl = 'Required.';
    if (!isNaN(u) && !isNaN(l) && u <= l) errors.usl = 'USL must exceed LSL.';

    if (sigma.trim() && (isNaN(parseFloat(sigma)) || parseFloat(sigma) <= 0))
      errors.sigma = 'Must be > 0.';
    if (ppm.trim() && (isNaN(parseFloat(ppm)) || parseFloat(ppm) <= 0))
      errors.ppm = 'Must be > 0.';

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // ── Submit ──────────────────────────────────────────────────────────

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!validate()) return;

    const data = dataInput.split(',').map(s => Number(s.trim())).filter(v => !isNaN(v));
    const payload: Record<string, unknown> = { data, usl: parseFloat(usl), lsl: parseFloat(lsl) };
    if (sigma.trim()) payload.sigma = parseFloat(sigma);
    if (ppm.trim()) payload.ppm = parseFloat(ppm);

    setLoading(true);
    try {
      const resp = await axios.post<AnalyzeResult>('/api/v2/six-sigma/analyze', payload);
      setResult(resp.data);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Analysis failed. Check inputs and try again.');
    } finally {
      setLoading(false);
    }
  };

  // ── Export ──────────────────────────────────────────────────────────

  const handleExport = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `six-sigma-analysis-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const m = result?.metrics;
  const cd = result?.chart_data;
  const cpkR = m ? getCpkRating(m.cpk) : null;

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <Card className="bg-slate-800/50 border-slate-700/60 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-base text-white flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-cyan-400" />
          Six Sigma Analyzer
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* ── Form ─────────────────────────────────────────────────── */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-slate-400 font-semibold uppercase tracking-wide mb-1 block">
              Process Data (comma-separated)
            </label>
            <Input
              value={dataInput}
              onChange={(e) => { setDataInput(e.target.value); setValidationErrors(v => ({ ...v, data: '' })); }}
              placeholder="e.g. 2.1, 4.3, 4.0, 5.1, 5.0, 7.2, 9.0"
              className={`bg-slate-900/60 border-slate-700 text-slate-200 ${validationErrors.data ? 'border-red-500/60' : ''}`}
            />
            {validationErrors.data && <p className="text-red-400 text-xs mt-1">{validationErrors.data}</p>}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 font-semibold uppercase tracking-wide mb-1 block">LSL</label>
              <Input type="number" step="any" value={lsl} onChange={(e) => setLsl(e.target.value)}
                className={`bg-slate-900/60 border-slate-700 text-slate-200 ${validationErrors.lsl ? 'border-red-500/60' : ''}`} />
              {validationErrors.lsl && <p className="text-red-400 text-xs mt-1">{validationErrors.lsl}</p>}
            </div>
            <div>
              <label className="text-xs text-slate-400 font-semibold uppercase tracking-wide mb-1 block">USL</label>
              <Input type="number" step="any" value={usl} onChange={(e) => setUsl(e.target.value)}
                className={`bg-slate-900/60 border-slate-700 text-slate-200 ${validationErrors.usl ? 'border-red-500/60' : ''}`} />
              {validationErrors.usl && <p className="text-red-400 text-xs mt-1">{validationErrors.usl}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 font-semibold uppercase tracking-wide mb-1 block">
                Known σ <span className="text-slate-600">(optional)</span>
              </label>
              <Input type="number" step="any" min="0" value={sigma} onChange={(e) => setSigma(e.target.value)}
                placeholder="auto-compute" className={`bg-slate-900/60 border-slate-700 text-slate-200 ${validationErrors.sigma ? 'border-red-500/60' : ''}`} />
              {validationErrors.sigma && <p className="text-red-400 text-xs mt-1">{validationErrors.sigma}</p>}
            </div>
            <div>
              <label className="text-xs text-slate-400 font-semibold uppercase tracking-wide mb-1 block">
                PPM <span className="text-slate-600">(optional)</span>
              </label>
              <Input type="number" step="any" min="0" value={ppm} onChange={(e) => setPpm(e.target.value)}
                placeholder="defects per million" className={`bg-slate-900/60 border-slate-700 text-slate-200 ${validationErrors.ppm ? 'border-red-500/60' : ''}`} />
              {validationErrors.ppm && <p className="text-red-400 text-xs mt-1">{validationErrors.ppm}</p>}
            </div>
          </div>

          <Button type="submit" disabled={loading} className="w-full bg-cyan-600 hover:bg-cyan-700 text-white">
            {loading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Analyzing…</> : 'Analyze'}
          </Button>
        </form>

        {/* ── Error ────────────────────────────────────────────────── */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* ── Results ──────────────────────────────────────────────── */}
        {result && m && cd && cpkR && (
          <div ref={resultRef} className="space-y-4">
            {/* Header with export */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge className="bg-slate-700/50 text-slate-300 text-[10px]">{m.n} samples</Badge>
                <Badge className={`${cpkR.bg} ${cpkR.color} text-[10px] border-0`}>{cpkR.label}</Badge>
              </div>
              <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white h-7 px-2" onClick={handleExport}>
                <Download className="h-3.5 w-3.5 mr-1" /> Export
              </Button>
            </div>

            {/* ── Key Metrics Row ──────────────────────────────────── */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {/* Mean */}
              <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/40">
                <div className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Mean (x̄)</div>
                <div className="text-xl font-bold text-slate-100 mt-1">{m.mean.toFixed(4)}</div>
                <div className="text-[10px] text-slate-600 mt-0.5">σ = {m.std_dev.toFixed(4)}</div>
              </div>
              {/* Cp */}
              <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/40">
                <div className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Cp</div>
                <div className="text-xl font-bold text-slate-100 mt-1">{m.cp.toFixed(4)}</div>
                <div className="text-[10px] text-slate-600 mt-0.5">Potential capability</div>
              </div>
              {/* Cpk */}
              <div className={`rounded-lg p-3 border border-slate-700/40 ${cpkR.bg}`}>
                <div className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Cpk</div>
                <div className={`text-xl font-bold mt-1 ${cpkR.color}`}>{m.cpk.toFixed(4)}</div>
                <div className={`text-[10px] mt-0.5 ${cpkR.color}`}>{cpkR.label}</div>
              </div>
              {/* Sigma Level */}
              <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/40">
                <div className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Sigma Level</div>
                <div className="mt-1">
                  {m.sigma_level !== null ? (
                    <Badge className={`${getSigmaBg(m.sigma_level)} ${getSigmaColor(m.sigma_level)} text-sm px-3 py-1`}>
                      {m.sigma_level.toFixed(2)}σ
                    </Badge>
                  ) : (
                    <span className="text-lg font-bold text-slate-300">{m.sigma_short_term.toFixed(2)}σ</span>
                  )}
                </div>
                <div className="text-[10px] text-slate-600 mt-0.5">
                  {m.sigma_level !== null ? 'From PPM' : 'Short-term (from Cpk)'}
                </div>
              </div>
            </div>

            {/* ── Extended Metrics ─────────────────────────────────── */}
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
              {[
                { label: 'DPMO', value: m.dpmo.toFixed(1) },
                { label: 'Yield %', value: m.yield_pct.toFixed(2) + '%' },
                { label: 'Cpu', value: m.cpu.toFixed(4) },
                { label: 'Cpl', value: m.cpl.toFixed(4) },
                { label: 'σ short', value: m.sigma_short_term.toFixed(2) },
                { label: 'σ long', value: m.sigma_long_term.toFixed(2) },
              ].map(({ label, value }) => (
                <div key={label} className="bg-slate-900/30 rounded-md p-2 border border-slate-700/30 text-center">
                  <div className="text-[9px] text-slate-500 uppercase tracking-widest font-semibold">{label}</div>
                  <div className="text-sm font-semibold text-slate-200 mt-0.5">{value}</div>
                </div>
              ))}
            </div>

            {/* ── IMR Chart Legend ──────────────────────────────────── */}
            <div className="bg-slate-900/40 rounded-lg p-3 border border-slate-700/40">
              <div className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold mb-2">
                I-MR Chart Control Limits
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div><span className="text-slate-500">CL:</span> <span className="text-slate-200 font-mono">{cd.cl.toFixed(4)}</span></div>
                <div><span className="text-red-400">UCL:</span> <span className="text-slate-200 font-mono">{cd.ucl.toFixed(4)}</span></div>
                <div><span className="text-red-400">LCL:</span> <span className="text-slate-200 font-mono">{cd.lcl.toFixed(4)}</span></div>
                <div><span className="text-amber-400">MR̄:</span> <span className="text-slate-200 font-mono">{cd.mr_cl.toFixed(4)}</span></div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs mt-1">
                <div><span className="text-blue-400">USL:</span> <span className="text-slate-200 font-mono">{cd.usl}</span></div>
                <div><span className="text-blue-400">LSL:</span> <span className="text-slate-200 font-mono">{cd.lsl}</span></div>
              </div>
            </div>

            {/* ── SPC Rule Violations ──────────────────────────────── */}
            {result.warnings.length > 0 && (
              <div className="bg-red-500/5 rounded-lg p-3 border border-red-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-red-400" />
                  <span className="text-xs text-red-400 font-semibold uppercase tracking-wide">
                    SPC Rule Violations ({result.warnings.length})
                  </span>
                </div>
                <div className="space-y-1.5">
                  {result.warnings.map((w, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs">
                      <Badge className={`flex-shrink-0 text-[9px] px-1.5 py-0.5 ${
                        w.severity === 'critical' ? 'bg-red-500/20 text-red-400 border-red-500/30' : 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                      }`}>{w.rule}</Badge>
                      <span className="text-slate-400">
                        {w.description}
                        <span className="text-slate-600 ml-1">(pts {w.indices.join(', ')})</span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Recommendations ──────────────────────────────────── */}
            {result.recommendations.length > 0 && (
              <div className="bg-cyan-500/5 rounded-lg p-3 border border-cyan-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <Info className="h-4 w-4 text-cyan-400" />
                  <span className="text-xs text-cyan-400 font-semibold uppercase tracking-wide">Recommendations</span>
                </div>
                <ul className="space-y-1">
                  {result.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                      <CheckCircle2 className="h-3.5 w-3.5 text-cyan-500 flex-shrink-0 mt-0.5" />
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* ── No Issues ────────────────────────────────────────── */}
            {result.warnings.length === 0 && result.recommendations.length === 0 && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
                <CheckCircle2 className="h-4 w-4" />
                Process is in control with no actionable findings.
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default SixSigmaAnalyzer;
