// ============================================================================
// benchmarkUtils.ts — Six Sigma KPI normalization + benchmark evaluation
// ============================================================================

export type BenchmarkStatus = 'good' | 'warning' | 'critical'

export interface BenchmarkResult {
  status: BenchmarkStatus
  delta?: number
  message: string
}

// Canonical KPI key mapped from common display names
export const KPI_MAP: Record<string, string> = {
  'defect rate': 'defect_rate',
  'defects %': 'defect_rate',
  'defect %': 'defect_rate',
  'defects rate': 'defect_rate',
  'defect percentage': 'defect_rate',
  'cpk': 'cpk',
  'cp': 'cpk',
  'process capability index': 'cpk',
  'process capability': 'cpk',
  'dpmo': 'dpmo',
  'defects per million opportunities': 'dpmo',
  'cycle time': 'cycle_time',
  'lead time': 'cycle_time',
  'throughput time': 'cycle_time',
  'oee': 'oee',
  'overall equipment effectiveness': 'oee',
  'yield': 'yield',
  'first pass yield': 'yield',
  'fpy': 'yield',
  'first time yield': 'yield',
  'rework rate': 'rework_rate',
  'rework %': 'rework_rate',
  'scrap rate': 'scrap_rate',
  'scrap %': 'scrap_rate',
  'sigma level': 'sigma_level',
  'sigma': 'sigma_level',
  'process sigma': 'sigma_level',
  'customer satisfaction': 'csat',
  'csat': 'csat',
  'nps': 'nps',
  'net promoter score': 'nps',
  'on time delivery': 'otd',
  'otd': 'otd',
  'on-time delivery': 'otd',
  'uptime': 'uptime',
  'availability': 'uptime',
  'mtbf': 'mtbf',
  'mean time between failures': 'mtbf',
  'mttr': 'mttr',
  'mean time to repair': 'mttr',
}

interface BenchmarkSpec {
  target: number
  warnAt?: number      // threshold below which warning triggers (lower_better) or above (higher_better)
  type: 'lower_better' | 'higher_better'
  label: string
  unit?: string
}

export const SIX_SIGMA_BENCHMARKS: Record<string, BenchmarkSpec> = {
  defect_rate: { target: 0.01, warnAt: 1, type: 'lower_better', label: '<0.01%', unit: '%' },
  cpk: { target: 1.33, warnAt: 1.0, type: 'higher_better', label: '≥1.33' },
  dpmo: { target: 3.4, warnAt: 6210, type: 'lower_better', label: '3.4 DPMO', unit: 'DPMO' },
  oee: { target: 85, warnAt: 70, type: 'higher_better', label: '≥85%', unit: '%' },
  yield: { target: 99.99, warnAt: 95, type: 'higher_better', label: '≥99.99%', unit: '%' },
  rework_rate: { target: 0.5, warnAt: 2, type: 'lower_better', label: '<0.5%', unit: '%' },
  scrap_rate: { target: 0.1, warnAt: 1, type: 'lower_better', label: '<0.1%', unit: '%' },
  sigma_level: { target: 6, warnAt: 3, type: 'higher_better', label: '6σ', unit: 'σ' },
  csat: { target: 90, warnAt: 75, type: 'higher_better', label: '≥90%', unit: '%' },
  nps: { target: 50, warnAt: 20, type: 'higher_better', label: '≥50' },
  otd: { target: 95, warnAt: 80, type: 'higher_better', label: '≥95%', unit: '%' },
  uptime: { target: 99, warnAt: 95, type: 'higher_better', label: '≥99%', unit: '%' },
}

/**
 * Normalize a KPI display name to its canonical key.
 * Returns null if no match found.
 */
export function normalizeKPI(name: string): string | null {
  const lower = name.toLowerCase().trim()
  // Direct map hit
  if (KPI_MAP[lower]) return KPI_MAP[lower]
  // Partial match — check if any map key is a substring of the name or vice versa
  for (const [key, canonical] of Object.entries(KPI_MAP)) {
    if (lower.includes(key) || key.includes(lower)) return canonical
  }
  return null
}

/**
 * Parse a KPI value string/number to a float. Returns null if not parseable.
 */
export function parseKPIValue(value: string | number | undefined): number | null {
  if (value === undefined || value === null || value === '') return null
  if (typeof value === 'number') return isNaN(value) ? null : value
  // Strip common units: %, σ, $, K, M
  const cleaned = String(value).replace(/[%σ$,\s]/g, '').replace(/k$/i, '000').replace(/m$/i, '000000')
  const parsed = parseFloat(cleaned)
  return isNaN(parsed) ? null : parsed
}

/**
 * Evaluate a KPI value against Six Sigma benchmarks.
 * Returns null if no benchmark exists for this KPI.
 */
export function evaluateKPI(kpiName: string, value: string | number): BenchmarkResult | null {
  const canonical = normalizeKPI(String(kpiName))
  if (!canonical) return null
  const spec = SIX_SIGMA_BENCHMARKS[canonical]
  if (!spec) return null

  const numeric = parseKPIValue(value)
  if (numeric === null) return null

  const unit = spec.unit ?? ''

  if (spec.type === 'lower_better') {
    if (numeric <= spec.target) {
      return { status: 'good', delta: spec.target - numeric, message: `${numeric}${unit} ≤ target ${spec.label}` }
    }
    if (spec.warnAt !== undefined && numeric <= spec.warnAt) {
      return { status: 'warning', delta: numeric - spec.target, message: `${numeric}${unit} above target ${spec.label}` }
    }
    return { status: 'critical', delta: numeric - spec.target, message: `${numeric}${unit} far exceeds target ${spec.label}` }
  } else {
    // higher_better
    if (numeric >= spec.target) {
      return { status: 'good', delta: numeric - spec.target, message: `${numeric}${unit} ≥ target ${spec.label}` }
    }
    if (spec.warnAt !== undefined && numeric >= spec.warnAt) {
      return { status: 'warning', delta: spec.target - numeric, message: `${numeric}${unit} below target ${spec.label}` }
    }
    return { status: 'critical', delta: spec.target - numeric, message: `${numeric}${unit} far below target ${spec.label}` }
  }
}

/**
 * Detect if a set of numeric values has high variance.
 * Returns true if (max - min) / max > 30%.
 */
export function detectVariance(values: number[]): boolean {
  const nums = values.filter(v => typeof v === 'number' && !isNaN(v))
  if (nums.length < 2) return false
  const max = Math.max(...nums)
  const min = Math.min(...nums)
  if (max === 0) return false
  return (max - min) / max > 0.3
}

/** Status badge color classes */
export const statusColors: Record<BenchmarkStatus, { badge: string; text: string; dot: string }> = {
  good:     { badge: 'bg-emerald-500/15 border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  warning:  { badge: 'bg-amber-500/15 border-amber-500/30',   text: 'text-amber-400',   dot: 'bg-amber-400'   },
  critical: { badge: 'bg-red-500/15 border-red-500/30',       text: 'text-red-400',      dot: 'bg-red-400'     },
}
