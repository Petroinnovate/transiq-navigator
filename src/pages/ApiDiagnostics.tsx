import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, Loader2, PlayCircle, Copy } from 'lucide-react';
import { toast } from 'sonner';

type CheckStatus = 'idle' | 'running' | 'pass' | 'fail';

interface CheckResult {
  name: string;
  path: string;
  method: string;
  status: CheckStatus;
  httpStatus?: number;
  durationMs?: number;
  responsePreview?: string;
  error?: string;
  hint?: string;
}

const DEFAULT_API_URL =
  (import.meta.env.VITE_API_URL as string) || 'http://localhost:8001';

interface CheckSpec {
  name: string;
  path: string;
  method: 'GET' | 'POST' | 'OPTIONS';
  body?: any;
  expect: number[];
  hintOnFail: string;
}

const CHECKS: CheckSpec[] = [
  {
    name: 'Health endpoint',
    path: '/health',
    method: 'GET',
    expect: [200],
    hintOnFail:
      'Backend not reachable. Make sure FastAPI is running and VITE_API_URL points to a publicly reachable URL (not localhost when accessed from a browser on another machine).',
  },
  {
    name: 'CORS preflight',
    path: '/api/v2/health',
    method: 'OPTIONS',
    expect: [200, 204, 404],
    hintOnFail:
      'CORS preflight failed. Add this origin to your FastAPI CORSMiddleware allow_origins.',
  },
  {
    name: 'API v2 health',
    path: '/api/v2/health',
    method: 'GET',
    expect: [200],
    hintOnFail:
      'The /api/v2 prefix is not responding. Verify your FastAPI router includes /api/v2 routes.',
  },
  {
    name: 'Latest dashboard endpoint',
    path: '/api/v2/dashboard/latest',
    method: 'GET',
    expect: [200, 404],
    hintOnFail:
      '404 here is OK if no dashboards exist yet. Other errors mean the dashboard endpoint is broken or auth is rejecting the request.',
  },
];

async function runCheck(baseUrl: string, spec: CheckSpec): Promise<CheckResult> {
  const url = baseUrl.replace(/\/$/, '') + spec.path;
  const start = performance.now();
  try {
    const token = localStorage.getItem('auth_token');
    const res = await fetch(url, {
      method: spec.method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: spec.body ? JSON.stringify(spec.body) : undefined,
      signal: AbortSignal.timeout(8000),
    });
    const durationMs = Math.round(performance.now() - start);
    let preview = '';
    try {
      const text = await res.text();
      preview = text.slice(0, 240);
    } catch {
      /* ignore */
    }
    const ok = spec.expect.includes(res.status);
    return {
      name: spec.name,
      path: spec.path,
      method: spec.method,
      status: ok ? 'pass' : 'fail',
      httpStatus: res.status,
      durationMs,
      responsePreview: preview,
      hint: ok ? undefined : spec.hintOnFail,
    };
  } catch (err: any) {
    const durationMs = Math.round(performance.now() - start);
    const msg = err?.message ?? String(err);
    return {
      name: spec.name,
      path: spec.path,
      method: spec.method,
      status: 'fail',
      durationMs,
      error: msg,
      hint:
        /timeout|aborted/i.test(msg)
          ? 'Request timed out after 8s. Backend is unreachable from this browser.'
          : /failed to fetch|networkerror|load failed/i.test(msg)
          ? 'Network error. Likely causes: (1) VITE_API_URL points to localhost but you opened the app from another machine, (2) backend is down, (3) HTTPS page calling HTTP backend (mixed content), or (4) CORS blocked the request.'
          : spec.hintOnFail,
    };
  }
}

export default function ApiDiagnostics() {
  const [baseUrl, setBaseUrl] = useState(DEFAULT_API_URL);
  const [results, setResults] = useState<CheckResult[]>(
    CHECKS.map((c) => ({
      name: c.name,
      path: c.path,
      method: c.method,
      status: 'idle' as CheckStatus,
    })),
  );
  const [running, setRunning] = useState(false);

  const runAll = async () => {
    setRunning(true);
    setResults((prev) => prev.map((r) => ({ ...r, status: 'running' })));
    const out: CheckResult[] = [];
    for (const spec of CHECKS) {
      const r = await runCheck(baseUrl, spec);
      out.push(r);
      setResults([...out, ...CHECKS.slice(out.length).map((c) => ({
        name: c.name, path: c.path, method: c.method, status: 'running' as CheckStatus,
      }))]);
    }
    setResults(out);
    setRunning(false);
    const failed = out.filter((r) => r.status === 'fail').length;
    if (failed === 0) toast.success('All checks passed');
    else toast.error(`${failed} of ${out.length} checks failed`);
  };

  const copyReport = () => {
    const text = [
      `API Diagnostics — ${new Date().toISOString()}`,
      `Base URL: ${baseUrl}`,
      `Page origin: ${window.location.origin}`,
      '',
      ...results.map((r) =>
        [
          `[${r.status.toUpperCase()}] ${r.method} ${r.path}`,
          r.httpStatus !== undefined ? `  HTTP ${r.httpStatus} in ${r.durationMs}ms` : `  ${r.durationMs}ms`,
          r.error ? `  Error: ${r.error}` : '',
          r.responsePreview ? `  Body: ${r.responsePreview}` : '',
          r.hint ? `  Hint: ${r.hint}` : '',
        ]
          .filter(Boolean)
          .join('\n'),
      ),
    ].join('\n');
    navigator.clipboard.writeText(text);
    toast.success('Report copied to clipboard');
  };

  const passed = results.filter((r) => r.status === 'pass').length;
  const failed = results.filter((r) => r.status === 'fail').length;

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">API Diagnostics</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Test connectivity to your processing backend (<code className="text-xs">VITE_API_URL</code>).
            Useful before uploads or when the dashboard fails to load.
          </p>
        </div>

        <div className="rounded-lg border border-border bg-card p-4 space-y-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Base URL
            </label>
            <div className="flex gap-2 mt-1.5">
              <Input
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://your-api.example.com"
                disabled={running}
                className="font-mono text-sm"
              />
              <Button onClick={runAll} disabled={running || !baseUrl.trim()}>
                {running ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Running…</>
                ) : (
                  <><PlayCircle className="h-4 w-4 mr-2" />Run all checks</>
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Page origin: <code className="text-xs">{window.location.origin}</code>
              {baseUrl.startsWith('http://localhost') && window.location.protocol === 'https:' && (
                <span className="block mt-1 text-amber-400">
                  ⚠ This is an HTTPS page calling an HTTP localhost URL — browsers block this.
                  Use a public HTTPS URL or an ngrok tunnel.
                </span>
              )}
            </p>
          </div>

          {(passed > 0 || failed > 0) && !running && (
            <div className="flex items-center gap-3 pt-2 border-t border-border">
              <Badge variant={failed === 0 ? 'default' : 'destructive'}>
                {passed} passed · {failed} failed
              </Badge>
              <Button variant="ghost" size="sm" onClick={copyReport}>
                <Copy className="h-3.5 w-3.5 mr-1.5" />
                Copy report
              </Button>
            </div>
          )}
        </div>

        <div className="space-y-3">
          {results.map((r, i) => (
            <div
              key={i}
              className={`rounded-lg border p-4 transition-colors ${
                r.status === 'pass'
                  ? 'border-emerald-500/40 bg-emerald-500/5'
                  : r.status === 'fail'
                  ? 'border-red-500/40 bg-red-500/5'
                  : r.status === 'running'
                  ? 'border-slate-500/40 bg-slate-500/5'
                  : 'border-border bg-card'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  {r.status === 'pass' && <CheckCircle2 className="h-5 w-5 text-emerald-400" />}
                  {r.status === 'fail' && <XCircle className="h-5 w-5 text-red-400" />}
                  {r.status === 'running' && <Loader2 className="h-5 w-5 animate-spin text-slate-400" />}
                  {r.status === 'idle' && <div className="h-5 w-5 rounded-full border border-border" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-sm">{r.name}</span>
                    <code className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                      {r.method} {r.path}
                    </code>
                    {r.httpStatus !== undefined && (
                      <Badge variant="outline" className="text-xs">
                        HTTP {r.httpStatus}
                      </Badge>
                    )}
                    {r.durationMs !== undefined && (
                      <span className="text-xs text-muted-foreground">{r.durationMs}ms</span>
                    )}
                  </div>
                  {r.error && (
                    <div className="mt-2 text-sm font-mono text-red-300 bg-black/30 px-2 py-1 rounded">
                      {r.error}
                    </div>
                  )}
                  {r.responsePreview && (
                    <details className="mt-2 text-xs text-muted-foreground">
                      <summary className="cursor-pointer hover:text-foreground">
                        Response preview
                      </summary>
                      <pre className="mt-1.5 p-2 rounded bg-black/30 overflow-x-auto whitespace-pre-wrap break-all">
                        {r.responsePreview}
                      </pre>
                    </details>
                  )}
                  {r.hint && (
                    <div className="mt-2 text-xs text-amber-300/90 bg-amber-500/5 border border-amber-500/20 px-2.5 py-1.5 rounded">
                      💡 {r.hint}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
