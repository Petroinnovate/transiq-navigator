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
  optimizationSuggestions: Optimization[]
  predictive?: PredictiveBlock
  explainability?: Explainability
  insights: Insights
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
  methodology?: "DMAIC" | "DMADV"
  dmaic: DMAIC
  dmadv?: DMADV
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
 * DMADV Framework - Design for New Processes/Products
 */
export interface DMADV {
  define: DMADVDefine
  measure: DMADVMeasure
  analyze: DMADVAnalyze
  design: DMADVDesign
  verify: DMADVVerify
}

export interface DMADVDefine {
  projectGoal: string
  customerNeeds: string[]
  businessCase: string
  scope: string
}

export interface DMADVMeasure {
  voiceOfCustomer: string[]
  criticalToQuality: CTQRequirement[]
  benchmarks: string[]
}

export interface CTQRequirement {
  ctq: string
  target: string
  weight: string
}

export interface DMADVAnalyze {
  gapAnalysis: string
  designOptions: DesignOption[]
  riskAssessment: DMADVRisk[]
}

export interface DesignOption {
  option: string
  pros: string[]
  cons: string[]
}

export interface DMADVRisk {
  risk: string
  severity: string
  mitigation: string
}

export interface DMADVDesign {
  selectedApproach: string
  detailedDesign: string[]
  designFMEA: DesignFMEA[]
  targetSpecifications: TargetSpec[]
}

export interface DesignFMEA {
  failureMode: string
  effect: string
  rpn: number
}

export interface TargetSpec {
  parameter: string
  target: string
  tolerance: string
}

export interface DMADVVerify {
  verificationPlan: string
  testResults: TestResult[]
  pilotOutcome: string
  deploymentReadiness: string
}

export interface TestResult {
  test: string
  result: string
  notes: string
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
  type: "line" | "bar" | "pie" | "scatter" | "area" | "sankey" | "heatmap" | "radar" | "boxplot" | "histogram" | "funnel" | "radialbar"
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
 * Optimization Suggestion - Decision-First
 */
export interface Optimization {
  title: string
  category: string
  description: string
  impact: string
  roi?: number
  paybackPeriod?: string
  riskIfIgnored: "High" | "Medium" | "Low"
  priority: "High" | "Medium" | "Low"
  approvalStatus?: "Pending" | "Approved" | "Rejected" | "Under Review"
  estimatedCost?: number
  timeline?: string
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
