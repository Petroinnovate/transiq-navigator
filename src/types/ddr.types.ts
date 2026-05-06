// ============================================================================
// DDR Intelligence Platform — Core TypeScript Types
// All DDR data structures with full provenance tracking
// ============================================================================

// ── KPI Value with full provenance ──────────────────────────────────────────

export interface KPIValue {
  value: number | string | null;
  unit?: string;
  status: 'normal' | 'warning' | 'critical';
  is_derived: boolean;
  formula?: string;
  confidence: number;
  extraction_method: 'pdfplumber' | 'tesseract_ocr';
  source_page: number;
  source_section: string;
  source_field: string;
  source_citation: string;
  source_snippet?: string;
  page_hash: string;
  imputed: boolean;
  under_review: boolean;
}

// ── Rig Identity ────────────────────────────────────────────────────────────

export interface RigIdentity {
  rig_id: string;
  well_id: string;
  report_date: string;
  shift_period: string;
  objective: string;
  charge_number: string;
  location: string;
  programme_name: string;
  programme_dates: string;
  classification: string;
  foremen: string;
  engineer: string;
  manager: string;
  thuraya: string;
}

// ── Fleet Summary (GET /fleet/summary) ──────────────────────────────────────

export interface FleetSummary {
  report_date: string;
  total_rigs: number;
  active_rigs: number;
  rigs_drilling: number;
  rigs_standby: number;
  rigs_completion: number;
  rigs_critical: number;
  rigs_warning: number;
  avg_rop_ft_hr: KPIValue;
  total_daily_footage_ft: KPIValue;
  avg_npt_pct: KPIValue;
  total_npt_hours: KPIValue;
  total_personnel: KPIValue;
  total_fuel_bbls: KPIValue;
  avg_depth_ft: KPIValue;
}

// ── Rig Summary (GET /rigs) ─────────────────────────────────────────────────

export interface RigSummary {
  rig_id: string;
  well_id: string;
  report_date: string;
  objective: string;
  location: string;
  status: 'normal' | 'warning' | 'critical' | 'standby';
  current_depth_ft: KPIValue;
  daily_footage_ft: KPIValue;
  rop_ft_hr: KPIValue;
  npt_pct: KPIValue;
  days_since_spud: KPIValue;
  mud_weight_pcf: KPIValue;
  total_personnel: KPIValue;
  fuel_bbls: KPIValue;
  foremen: string;
  engineer: string;
  manager: string;
}

// ── Rig Detail (GET /rigs/:rigId) ───────────────────────────────────────────

export interface RigDetail extends RigSummary {
  identity: RigIdentity;
  depth_summary: DepthSummary;
  formation_tops: FormationTop[];
  well_design_milestones: WellMilestone[];
  current_operation: string;
  current_operation_citation: string;
  next_location: string;
}

export interface DepthSummary {
  current_md_ft: KPIValue;
  current_tvd_ft: KPIValue;
  daily_footage_ft: KPIValue;
  days_since_spud: KPIValue;
  circ_pct: KPIValue;
  target_td_ft: number;
  progress_pct: number;
}

export interface FormationTop {
  formation: string;
  top_depth_ft: number;
  comments: string;
  source_citation: string;
}

export interface WellMilestone {
  hole_size: string;
  casing_size: string;
  depth_ft: number;
  formation: string;
  completed: boolean;
  source_citation: string;
}

// ── Timeline (GET /rigs/:rigId/timeline) ────────────────────────────────────

export interface TimelineRow {
  time_from: string;
  time_to: string;
  hours: number;
  lateral: number;
  phase: string;
  category: string;
  major_op: string;
  action_code: string;
  object_code: string;
  resp_co: string;
  hole_depth_start: number;
  hole_depth_end: number;
  event_depth_start: number | null;
  event_depth_end: number | null;
  lt_type: string | null;
  lt_id: string | null;
  summary_text: string;
  source_citation: string;
}

// ── NPT/Lost Time (GET /rigs/:rigId/npt) ───────────────────────────────────

export interface NPTEvent {
  event_from: string;
  hours_lost: number;
  cum_hours: number;
  lt_id: string;
  parent_lt_id: string | null;
  npt_type: string;
  cause_code: string;
  cause_desc: string;
  object_code: string;
  resp_co: string;
  depth_ft: number;
  summary_text: string;
  source_citation: string;
}

// ── Survey (GET /rigs/:rigId/survey) ────────────────────────────────────────

export interface SurveyStation {
  lateral: number;
  survey_md_ft: number;
  angle_deg: number;
  azimuth_deg: number;
  tvd_ft: number;
  ns_coord: number;
  ew_coord: number;
  vertical_sec: number;
  dls_deg_100ft: number;
  source_citation: string;
}

// ── Mud Data (GET /rigs/:rigId/mud) ─────────────────────────────────────────

export interface MudRecord {
  record_no: number;
  weight_pcf: KPIValue;
  fl_temp_f: KPIValue;
  funnel_vis_sec: KPIValue;
  water_vol_pct: KPIValue;
  oil_vol_pct: KPIValue;
  solids_vol_pct: KPIValue;
  pv: KPIValue;
  yp: KPIValue;
  ph: KPIValue;
  mud_type: string;
  cl_ppm: KPIValue;
  ca_ppm: KPIValue;
  gels_10sec: KPIValue;
  gels_10min: KPIValue;
  source_citation: string;
}

export interface MudTreatment {
  chemical: string;
  quantity: number;
  unit: string;
  source_citation: string;
}

// ── Personnel (GET /rigs/:rigId/personnel) ──────────────────────────────────

export interface PersonnelRow {
  category_code: string;
  category_desc: string;
  num_persons: number;
  personnel_hrs: number;
  operating_hrs: number;
  source_citation: string;
}

// ── BHA (GET /rigs/:rigId/bha) ──────────────────────────────────────────────

export interface BHAComponent {
  order: number;
  component: string;
  provider: string;
  joints: number;
  od_in: number;
  id_in: number;
  length_ft: number;
  cum_length_ft: number;
  top_thread: string;
  bot_thread: string;
  weight_lb_ft: number;
  serial: string;
  grade: string;
  source_citation: string;
}

// ── HSE (GET /rigs/:rigId/hse) ──────────────────────────────────────────────

export interface HSEData {
  bop_test_date: string;
  bop_test_days_ago: number;
  bop_drills_date: string;
  safety_drills: string;
  near_miss_count: number;
  incident_id: string | null;
  hse_alerts: string[];
  safety_campaigns: string[];
  aramco_personnel: AramcoPersonnel[];
  source_citation: string;
}

export interface AramcoPersonnel {
  name: string;
  id: string;
  role: string;
  since: string;
}

// ── Bulk & Logistics (GET /rigs/:rigId/bulk) ────────────────────────────────

export interface BulkData {
  fuel_bbls: KPIValue;
  cement_sx: KPIValue;
  drill_water: KPIValue;
  pot_water: KPIValue;
  standby_vehicles: StandbyVehicle[];
  source_citation: string;
}

export interface StandbyVehicle {
  vehicle_id: string;
  status: string;
  notes: string;
  source_citation: string;
}

// ── Foreman Remarks (GET /rigs/:rigId/foreman-remarks) ──────────────────────

export interface ForemanRemarks {
  last_24hr_ops: string;
  next_24hr_plan: string;
  well_design: string;
  service_companies: ServiceProvider[];
  simops: SimopsInfo;
  erp_notes: string;
  mud_recycling: MudRecycling;
  source_citation: string;
}

export interface ServiceProvider {
  name: string;
  provider: string;
  since: string;
  source_citation: string;
}

export interface SimopsInfo {
  active: boolean;
  wells: string[];
  notes: string;
  source_citation: string;
}

export interface MudRecycling {
  total_received_wbm_bbl: number;
  total_received_obm_bbl: number;
  total_shipped_obm_bbl: number;
  sources: { location: string; volume_bbl: number }[];
  source_citation: string;
}

// ── Fleet Analytics ─────────────────────────────────────────────────────────

export interface FleetNPTPareto {
  cause_code: string;
  cause_desc: string;
  total_hours: number;
  cumulative_pct: number;
  rig_count: number;
  rigs: { rig_id: string; hours: number; citation: string }[];
}

export interface FleetSPCResult {
  metric: string;
  unit: string;
  mean: number;
  std_dev: number;
  ucl: number;
  lcl: number;
  cp?: number;
  cpk?: number;
  dpmo?: number;
  sigma_level?: number;
  out_of_control_count: number;
  data_points: SPCDataPoint[];
  violations: SPCViolation[];
}

export interface SPCDataPoint {
  rig_id: string;
  value: number;
  status: 'in_control' | 'warning' | 'out_of_control';
  source_citation: string;
}

export interface SPCViolation {
  rig_id: string;
  rule: string;
  description: string;
  value: number;
  source_citation: string;
}

export interface FleetTopPerformer {
  rig_id: string;
  well_id: string;
  metric_value: number;
  metric_unit: string;
  rank: number;
  source_citation: string;
}

export interface FleetHeatmapTile {
  rig_id: string;
  well_id: string;
  status: 'drilling' | 'standby' | 'completion' | 'critical' | 'normal';
  current_md_ft: number;
  /** Optional — backend may not yet provide this field */
  rop_ft_hr?: number;
  npt_pct: number;
  last_operation: string;
  source_citation: string;
}

export interface FleetTrendPoint {
  date: string;
  avg_rop: number;
  total_npt_hours: number;
  total_footage: number;
}

// ── Search / RAG ────────────────────────────────────────────────────────────

export interface DDRSearchResult {
  answer: string;
  confidence: number;
  citations: DDRCitation[];
  data_not_found: string[];
}

export interface DDRCitation {
  rig_id: string;
  page: number;
  section: string;
  field: string;
  raw_text: string;
  citation_string: string;
}

// ── ETL / Ingestion ─────────────────────────────────────────────────────────

export interface ETLProgress {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  pages_processed: number;
  total_pages: number;
  rigs_extracted: number;
  estimated_rigs: number;
  current_rig: string;
  validation_errors: number;
  ocr_fallbacks: number;
  elapsed_seconds: number;
  estimated_remaining: number;
}

export interface ReportListItem {
  report_date: string;
  rigs: number;
  status: 'processed' | 'processing' | 'failed';
  uploaded_at: string;
  pages: number;
}

// ── Audit ───────────────────────────────────────────────────────────────────

export interface FieldAuditRecord {
  rig_id: string;
  field_name: string;
  value: string;
  source_page: number;
  source_section: string;
  extraction_method: string;
  confidence: number;
  page_hash: string;
  raw_text: string;
  validation_checks: ValidationCheck[];
  imputed: boolean;
  manual_overrides: ManualOverride[];
}

export interface ValidationCheck {
  check_name: string;
  passed: boolean;
  details: string;
}

export interface ManualOverride {
  timestamp: string;
  changed_by: string;
  old_value: string;
  new_value: string;
  reason: string;
}

export interface AuditChangeLogEntry {
  timestamp: string;
  rig_id: string;
  field: string;
  old_value: string;
  new_value: string;
  changed_by: string;
  reason: string;
  source_citation: string;
}

// ── Rig KPIs (GET /rigs/:rigId/kpis) ───────────────────────────────────────

export interface RigKPIs {
  rig_id: string;
  report_date: string;
  identity: RigIdentity;
  depth: KPIValue;
  tvd: KPIValue;
  daily_footage: KPIValue;
  rop: KPIValue;
  days_since_spud: KPIValue;
  npt_hours: KPIValue;
  npt_pct: KPIValue;
  mud_weight: KPIValue;
  total_personnel: KPIValue;
  fuel_bbls: KPIValue;
  circ_pct: KPIValue;
}

// ── Well Design (GET /rigs/:rigId/well-design) ──────────────────────────────

export interface WellDesign {
  rig_id: string;
  well_id: string;
  target_td_ft: number;
  milestones: WellMilestone[];
  directional_plan: string;
  deviation_notes: string;
  source_citation: string;
}

// ── Export Types ─────────────────────────────────────────────────────────────

export interface ExportOptions {
  format: 'pdf' | 'excel' | 'pptx';
  scope: 'rig' | 'fleet';
  rig_id?: string;
  report_date: string;
  include_citations: boolean;
}

// ── Multi-Tenant Branding ───────────────────────────────────────────────────

export type Tenant = 'aramco' | 'adnoc' | 'ongc' | 'bp' | 'shell' | 'total' | 'chevron';

export interface TenantConfig {
  name: string;
  primaryColor: string;
  logoPath: string;
  reportFormat: string;
  classificationLabel: string;
  dateFormat: string;
  depthUnit: 'ft' | 'm';
  pressureUnit: 'psi' | 'bar';
}

// ── API Request Params ──────────────────────────────────────────────────────

export interface RigListParams {
  report_date?: string;
  status?: string;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface FleetTrendParams {
  report_date: string;
  days?: 7 | 14 | 30;
}

export interface DDRSearchParams {
  query: string;
  report_date?: string;
  rig_id?: string;
  top_k?: number;
}
