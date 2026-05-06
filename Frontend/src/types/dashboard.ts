// ============================================================================
// TypeScript Type Definitions - Universal AI Dashboard Schema
// Board-Grade Analytics - Schema-Driven, Confidence-Aware, Explainable
// ============================================================================

/**
 * Main Dashboard Response - Single Source of Truth
 */
export interface DashboardResponse {
  meta: MetaInfo
  autoClassification: AutoClassification
  sixSigma: SixSigma
  kpis: KPI[]
  charts: ChartBlock[]
  sections?: SectionAnalysis[]
  optimizationSuggestions: Optimization[]
  predictive?: PredictiveBlock
  explainability?: Explainability
  insights: Insights
  // Progressive Disclosure Layers
  ceo_view?: CeoView
  manager_view?: ManagerView
  engineer_view?: EngineerView
  boardroom_mode?: BoardroomMode
}

/**
 * Meta Information - Trust & Audit Trail
 */
export interface MetaInfo {
  reportId: string
  ingestedAt: string
  sourceType: string
  confidenceOverall: number
  decisionReadinessScore: number
  sectionsAnalyzed?: number
  totalPages?: number
  tiersUsed?: Record<string, number>
  estimatedCost?: CostEstimate
  crossPhaseInsights?: CrossPhaseInsight[]
  phaseSyntheses?: Record<string, any>
  modelUsage?: Record<string, number>
  reprocessed?: number
}

export interface CostEstimate {
  total_input_tokens: number
  total_output_tokens: number
  estimated_cost_usd: number
  tier_breakdown: Record<string, number>
  phase_calls: number
  executive_call: number
  pageindex_tokens: number
}

export interface CrossPhaseInsight {
  type: 'warning' | 'info'
  insight: string
}

/**
 * Auto-Classification - AI Understanding of Report
 */
export interface AutoClassification {
  reportType: string[]
  assetScope: string
  timeHorizon: string
  decisionLevel: string
  confidence: number
}

/**
 * Six Sigma Quality Framework
 */
export interface SixSigma {
  sigmaLevel: string
  defectRate: string
  processCapability: "Low" | "Medium" | "High"
  statisticalValidity: boolean
  dmaic: DMAIC
}

/**
 * DMAIC Framework - Complete Structure
 */
export interface DMAIC {
  define: DMAICDefine
  measure: DMAICMeasure
  analyze: DMAICAnalyze
  improve: DMAICImprove
  control: DMAICControl
}

export interface DMAICDefine {
  problemStatement: string
  goal: string
  scope: string
  stakeholders: string[]
  ctqCharacteristics: CTQCharacteristic[]
}

export interface CTQCharacteristic {
  name: string
  specification: string
  currentPerformance: string
  target: string
}

export interface DMAICMeasure {
  dataCollectionPlan: string
  measurementSystem: string
  baselineMetrics: BaselineMetric[]
  dataQuality: DataQuality
}

export interface BaselineMetric {
  metric: string
  value: number
  unit: string
  timestamp?: string
}

export interface DataQuality {
  completeness: number
  accuracy: number
  reliability: string
}

export interface DMAICAnalyze {
  rootCauseAnalysis: RootCause[]
  statisticalTests: StatisticalTest[]
  processMap: ProcessMap
  variationSources: VariationSource[]
}

export interface RootCause {
  cause: string
  impact: "High" | "Medium" | "Low"
  confidence: number
  evidence: string[]
}

export interface StatisticalTest {
  testName: string
  result: string
  pValue?: number
  significance: boolean
}

export interface ProcessMap {
  steps: ProcessStep[]
  bottlenecks: string[]
}

export interface ProcessStep {
  name: string
  duration: number
  valueAdded: boolean
}

export interface VariationSource {
  source: string
  contribution: number
  controllable: boolean
}

export interface DMAICImprove {
  solutions: Solution[]
  pilotResults: PilotResult[]
  implementationPlan: ImplementationPlan
}

export interface Solution {
  description: string
  expectedImpact: string
  cost: number
  timeline: string
  priority: "High" | "Medium" | "Low"
}

export interface PilotResult {
  solution: string
  outcome: string
  metrics: Record<string, number>
}

export interface ImplementationPlan {
  phases: Phase[]
  resources: string[]
  timeline: string
  risks: Risk[]
}

export interface Phase {
  name: string
  duration: string
  milestones: string[]
}

export interface Risk {
  description: string
  probability: "High" | "Medium" | "Low"
  impact: "High" | "Medium" | "Low"
  mitigation: string
}

export interface DMAICControl {
  controlPlan: ControlPlan
  monitoring: Monitoring
  documentation: Documentation
  sustainability: Sustainability
}

export interface ControlPlan {
  metrics: ControlMetric[]
  responsibilities: string[]
  frequency: string
}

export interface ControlMetric {
  name: string
  target: number
  alertThreshold: number
  method: string
}

export interface Monitoring {
  tools: string[]
  frequency: string
  dashboards: string[]
}

export interface Documentation {
  procedures: string[]
  training: string[]
  auditTrail: boolean
}

export interface Sustainability {
  reviewSchedule: string
  continuousImprovement: string[]
  ownership: string
}

/**
 * KPI - Key Performance Indicator
 */
export interface KPI {
  name: string
  value: number
  unit: string
  target?: number
  trend?: "up" | "down" | "stable"
  confidence: number
  linkedCTQ?: string
  context?: string
}

/**
 * Chart Block - Visualization Definition
 */
export interface ChartBlock {
  chartId: string
  title: string
  type: "line" | "bar" | "pie" | "scatter" | "area" | "sankey" | "heatmap"
  data: ChartDataPoint[]
  xAxis?: string
  yAxis?: string
  annotations?: Annotation[]
  compareMode?: boolean
}

export interface ChartDataPoint {
  [key: string]: string | number
}

export interface Annotation {
  position: number | string
  label: string
  type: "threshold" | "event" | "target"
}

/**
 * Decision Traceability Layer - Audit trail for every recommendation
 */
export interface DecisionTraceability {
  data_sources: string[]
  analytical_methods: string[]
  supporting_evidence: string[]
}

/**
 * Industry Benchmarking - Peer & quartile comparison
 */
export interface IndustryBenchmarking {
  median_comparison: string
  top_quartile_comparison: string
  peer_comparison: string
  performance_gap: string
}

/**
 * Decision Confidence Index (DCI) - Composite trust score 0-100
 */
export interface DecisionConfidenceIndex {
  score: number                 // 0-100 composite
  data_completeness: string     // rationale for 0-25 sub-score
  model_confidence: string      // rationale for 0-25 sub-score
  historical_accuracy: string   // rationale for 0-25 sub-score
  variability: string           // rationale for 0-25 sub-score
  explanation: string           // why this score; what would raise it
}

/**
 * Optimization Suggestion - Decision-First with full DCI Framework
 */
export interface Optimization {
  id?: string
  title: string
  category: string
  description: string
  impact: string
  roi?: number
  paybackPeriod?: string
  riskIfIgnored?: string
  savings?: { value?: number; unit?: string; timeframe?: string; percentage?: string }
  priority: string
  confidence?: number
  approvalStatus?: string
  sourceSection?: string
  implementation?: string
  metrics?: string[]
  tags?: string[]
  actionable?: boolean
  // DCI Framework (populated by AI for new analyses)
  decision_traceability?: DecisionTraceability
  industry_benchmarking?: IndustryBenchmarking
  decision_confidence_index?: DecisionConfidenceIndex
  assumptions_limitations?: string[]
  // Operational Intelligence Layer
  use_case?: string
  action_management?: ActionManagement
  execution_plan?: string[]
  closed_loop_learning?: ClosedLoopLearning
  integration_mapping?: IntegrationMapping
  domain_kpis?: DomainKPI[]
  failure_modes?: FailureMode[]
}

export interface ActionManagement {
  task_title: string
  description?: string
  owner: string
  kpi: string
  target_value: string
  deadline: string
  priority: string
  status: string
}

export interface ClosedLoopLearning {
  predicted_impact: string
  measurement_plan: string
  feedback_capture: string
  learning_loop: string
  actual_vs_predicted?: {
    predicted: string
    actual: string
  }
}

export interface IntegrationMapping {
  erp?: string
  scada?: string
  production_db?: string
  excel?: string
}

export interface DomainKPI {
  name: string
  current: string
  target: string
  direction: 'increase' | 'decrease'
}

export interface FailureMode {
  cause: string
  confidence: number
}


/**
 * Predictive Block - Forecasting & What-If
 */
export interface PredictiveBlock {
  forecastHorizon: string
  predictions: Prediction[]
  whatIfScenarios: Scenario[]
  confidence: number
}

export interface Prediction {
  metric: string
  forecastedValue: number
  timeframe: string
  risk: "High" | "Medium" | "Low"
  confidenceInterval?: ConfidenceInterval
}

export interface ConfidenceInterval {
  lower: number
  upper: number
  confidenceLevel: number
}

export interface Scenario {
  name: string
  assumptions: string[]
  outcome: string
  probability: number
}

/**
 * Explainability - CRITICAL for PSU/Board/Audit
 */
export interface Explainability {
  reasoning: string
  dataSourcesUsed: string[]
  assumptions: string[]
  limitations: string[]
  modelInfo?: ModelInfo
  auditTrail: AuditTrailEntry[]
}

export interface ModelInfo {
  name: string
  version: string
  accuracy?: number
  lastTrained?: string
}

export interface AuditTrailEntry {
  timestamp: string
  action: string
  user?: string
  details: string
}

/**
 * Insights - Alerts and Recommendations
 */
export interface Insights {
  alerts: Alert[]
  recommendations: Recommendation[]
  summary: string
}

export interface Alert {
  severity: "Critical" | "High" | "Medium" | "Low"
  message: string
  timestamp: string
  category: string
  actionRequired?: string
}

export interface Recommendation {
  title: string
  description: string
  priority: "High" | "Medium" | "Low"
  estimatedImpact: string
  confidence: number
}

/**
 * Section-Level Analysis — per-section deep dive from full-report analysis
 */
export interface SectionAnalysis {
  sectionId: string
  title: string
  pageRange?: string
  summary: string
  keyFindings: SectionFinding[]
  kpis: KPI[]
  risks: SectionRisk[]
  recommendations: string[]
  financialImpact?: {
    identified?: boolean
    items?: { description: string; amount?: number; unit?: string; type?: string }[]
  }
  charts: ChartBlock[]
  confidence: number
  tier?: 1 | 2 | 3
  dmaicPhase?: 'define' | 'measure' | 'analyze' | 'improve' | 'control' | 'unassigned' | 'none'
  modelUsed?: 'cheap' | 'balanced' | 'powerful'
  score?: {
    composite: number
    kpi_density: number
    financial_signal: number
    dmaic_relevance: number
    data_table: number
    risk_defect: number
    boilerplate: number
    pageindex_boost: number
  }
}

export interface SectionFinding {
  finding: string
  impact: "high" | "medium" | "low"
  confidence: number
}

export interface SectionRisk {
  risk: string
  severity: "high" | "medium" | "low"
  probability?: "high" | "medium" | "low"
}

// ═══════════════════════════════════════════════════════════════
// Progressive Disclosure Layers — CEO / Manager / Engineer / Boardroom
// ═══════════════════════════════════════════════════════════════

export interface CeoDecision {
  title: string
  impact: string
  urgency: 'high' | 'medium' | 'low'
}

export interface CeoRisk {
  title: string
  severity: 'High' | 'Medium' | 'Low'
  financial_impact: string
}

export interface CeoAction {
  title: string
  owner: string
  timeline: string
}

export interface CeoView {
  decisions: CeoDecision[]
  risks: CeoRisk[]
  actions: CeoAction[]
}

export interface ManagerDmaic {
  define: string
  measure: string
  analyze: string
  improve: string
  control: string
}

export interface ManagerRecommendation {
  title: string
  impact: string
  timeline: string
  priority: 'high' | 'medium' | 'low'
}

export interface ManagerKpiTracking {
  name: string
  current: string
  target: string
  status: 'on-track' | 'at-risk' | 'off-track'
}

export interface ManagerView {
  dmaic: ManagerDmaic
  recommendations: ManagerRecommendation[]
  kpi_tracking: ManagerKpiTracking[]
}

export interface EngineerFailureMode {
  cause: string
  probability: number
  detection: string
  mitigation: string
}

export interface EngineerView {
  data_references: string[]
  models: string[]
  root_cause_analysis: string[]
  failure_modes: EngineerFailureMode[]
  assumptions: string[]
}

export interface BoardroomSlides {
  summary: string[]
  decisions: string[]
  risks: string[]
  actions: string[]
  kpi_impact: string[]
}

export interface BoardroomMode {
  executive_summary: string
  slides: BoardroomSlides
}
