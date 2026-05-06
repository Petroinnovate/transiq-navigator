// Mock data for DDR Intelligence Platform — based on Rig 088TE / QTIF-790 / 10/02/2024

export interface KPIValue {
  value: number | string | null;
  unit?: string;
  status: 'normal' | 'warning' | 'critical';
  is_derived: boolean;
  confidence: number;
  source_citation: string;
}

export interface RigSummary {
  rig_id: string;
  well_id: string;
  objective: string;
  status: 'normal' | 'warning' | 'critical' | 'standby';
  current_depth_ft: number;
  daily_footage_ft: number;
  rop_ft_hr: number;
  npt_pct: number;
  days_since_spud: number;
  mud_weight_pcf: number;
  total_personnel: number;
}

export interface TimelineRow {
  time_from: string;
  time_to: string;
  hours: number;
  phase: string;
  category: string;
  major_op: string;
  summary_text: string;
  is_npt: boolean;
}

export interface NPTEvent {
  rig_id: string;
  well_id: string;
  event_from: string;
  hours_lost: number;
  npt_type: string;
  cause_code: string;
  cause_desc: string;
  depth_ft: number;
  resp_co: string;
  lt_id: string;
}

export const FLEET_SUMMARY = {
  report_date: '10/02/2024',
  total_rigs: 267,
  active_rigs: 198,
  rigs_drilling: 198,
  rigs_standby: 42,
  rigs_completion: 27,
  rigs_critical: 6,
  rigs_warning: 23,
  avg_rop_ft_hr: { value: 12.4, unit: 'ft/hr', status: 'normal' as const, is_derived: true, confidence: 0.96, source_citation: 'Fleet–Computed–Avg ROP' },
  total_daily_footage_ft: { value: 24680, unit: 'ft', status: 'normal' as const, is_derived: true, confidence: 0.94, source_citation: 'Fleet–Computed–Total Footage' },
  avg_npt_pct: { value: 8.3, unit: '%', status: 'warning' as const, is_derived: true, confidence: 0.97, source_citation: 'Fleet–Computed–NPT%' },
  total_npt_hours: { value: 498.5, unit: 'hrs', status: 'warning' as const, is_derived: true, confidence: 0.95, source_citation: 'Fleet–Computed–Total NPT' },
  total_personnel: { value: 6842, unit: '', status: 'normal' as const, is_derived: true, confidence: 0.92, source_citation: 'Fleet–Computed–Personnel' },
  total_fuel_bbls: { value: 12450, unit: 'bbls', status: 'normal' as const, is_derived: true, confidence: 0.91, source_citation: 'Fleet–Computed–Fuel' },
};

const statuses: Array<'normal' | 'warning' | 'critical' | 'standby'> = ['normal', 'warning', 'critical', 'standby'];
const objectives = ['Development Drilling', 'Exploration', 'Workover', 'Completion', 'Horizontal Lateral'];
const wellPrefixes = ['QTIF', 'SDGM', 'ABQQ', 'KHRS', 'HRDH', 'SHYB', 'UTMN', 'BRRI'];

export const RIGS: RigSummary[] = Array.from({ length: 267 }, (_, i) => {
  const rigNum = String(i + 1).padStart(3, '0');
  const suffix = ['TE', 'SA', 'BD', 'XR', 'MK'][i % 5];
  const status = i < 198 ? (i < 6 ? 'critical' : i < 29 ? 'warning' : 'normal') : (i < 240 ? 'standby' : 'normal');
  return {
    rig_id: `${rigNum}${suffix}`,
    well_id: `${wellPrefixes[i % 8]}-${700 + i}`,
    objective: objectives[i % 5],
    status,
    current_depth_ft: Math.round(5000 + Math.random() * 20000),
    daily_footage_ft: status === 'standby' ? 0 : Math.round(Math.random() * 400),
    rop_ft_hr: status === 'standby' ? 0 : +(5 + Math.random() * 20).toFixed(1),
    npt_pct: status === 'critical' ? +(30 + Math.random() * 40).toFixed(1) : status === 'warning' ? +(10 + Math.random() * 20).toFixed(1) : +(Math.random() * 8).toFixed(1),
    days_since_spud: Math.round(10 + Math.random() * 200),
    mud_weight_pcf: Math.round(70 + Math.random() * 40),
    total_personnel: Math.round(15 + Math.random() * 30),
  };
});

// Override first rig with 088TE exact data
RIGS[0] = {
  rig_id: '088TE',
  well_id: 'QTIF-790',
  objective: 'Single Lateral Disposal Targeting Arab-C',
  status: 'warning',
  current_depth_ft: 23695,
  daily_footage_ft: 0,
  rop_ft_hr: 0,
  npt_pct: 23.0,
  days_since_spud: 115,
  mud_weight_pcf: 92,
  total_personnel: 28,
};

export const RIG_088TE_TIMELINE: TimelineRow[] = [
  { time_from: '05:00', time_to: '06:00', hours: 1, phase: 'MAINT', category: 'PA', major_op: 'SDR1', summary_text: 'Safety meeting and pre-job planning session.', is_npt: false },
  { time_from: '06:00', time_to: '09:00', hours: 3, phase: 'DRILL', category: 'PA', major_op: 'CIRC', summary_text: 'Circulating and conditioning hole. MW 92 PCF CaCl brine.', is_npt: false },
  { time_from: '09:00', time_to: '12:00', hours: 3, phase: 'DRILL', category: 'PA', major_op: 'CIRC', summary_text: 'Cont. circulating. Preparing to run 4-1/2" completion string.', is_npt: false },
  { time_from: '12:00', time_to: '14:00', hours: 2, phase: 'COMP', category: 'PA', major_op: 'RIH', summary_text: 'Running in hole with completion string. Reached 18,500 ft MD.', is_npt: false },
  { time_from: '14:00', time_to: '16:00', hours: 2, phase: 'COMP', category: 'PA', major_op: 'RIH', summary_text: 'Continue RIH completion string. Tag at 20,200 ft MD.', is_npt: false },
  { time_from: '16:00', time_to: '19:00', hours: 3, phase: 'NPT', category: 'LT', major_op: 'STUK', summary_text: 'Stuck pipe — differential pressure. Attempting jarring operations.', is_npt: true },
  { time_from: '19:00', time_to: '22:00', hours: 3, phase: 'NPT', category: 'LT', major_op: 'STUK', summary_text: 'Cont. jarring. Pump spotting fluid — diesel pill. No movement.', is_npt: true },
  { time_from: '22:00', time_to: '01:00', hours: 3, phase: 'DRILL', category: 'PA', major_op: 'CIRC', summary_text: 'Freed pipe. Circulating bottoms up. MW checks normal.', is_npt: false },
  { time_from: '01:00', time_to: '03:00', hours: 2, phase: 'COMP', category: 'PA', major_op: 'POOH', summary_text: 'Pulling out of hole with completion string to surface.', is_npt: false },
  { time_from: '03:00', time_to: '05:00', hours: 2, phase: 'MAINT', category: 'PA', major_op: 'MNTC', summary_text: 'Equipment maintenance. Rig floor cleanup. Tool inspection.', is_npt: false },
];

export const NPT_EVENTS: NPTEvent[] = [
  { rig_id: '088TE', well_id: 'QTIF-790', event_from: '08 Sep 1600', hours_lost: 11.25, npt_type: 'STUK', cause_code: 'STDP', cause_desc: 'Stuck Differential Pressure', depth_ft: 23506, resp_co: 'RIG', lt_id: '940449' },
  { rig_id: '088TE', well_id: 'QTIF-790', event_from: '13 Sep 0500', hours_lost: 11.75, npt_type: 'STUK', cause_code: 'IPDF', cause_desc: 'Stuck Insufficient Pipe Dope/Friction', depth_ft: 23506, resp_co: 'BDF', lt_id: '940868' },
  { rig_id: '002SA', well_id: 'SDGM-702', event_from: '01 Oct 0800', hours_lost: 8.5, npt_type: 'WAIT', cause_code: 'WMAT', cause_desc: 'Waiting on Materials', depth_ft: 15200, resp_co: 'ARM', lt_id: '941002' },
  { rig_id: '003BD', well_id: 'ABQQ-703', event_from: '30 Sep 1200', hours_lost: 14.0, npt_type: 'MECH', cause_code: 'MPMP', cause_desc: 'Mechanical — Mud Pump Failure', depth_ft: 18300, resp_co: 'RIG', lt_id: '941120' },
  { rig_id: '004XR', well_id: 'KHRS-704', event_from: '02 Oct 0200', hours_lost: 6.25, npt_type: 'FISH', cause_code: 'FISH', cause_desc: 'Fishing Operations', depth_ft: 12800, resp_co: 'BDF', lt_id: '941234' },
  { rig_id: '005MK', well_id: 'HRDH-705', event_from: '01 Oct 1800', hours_lost: 4.0, npt_type: 'CSG', cause_code: 'CSGL', cause_desc: 'Casing Leak', depth_ft: 9200, resp_co: 'RIG', lt_id: '941345' },
  { rig_id: '006TE', well_id: 'SHYB-706', event_from: '02 Oct 0500', hours_lost: 9.75, npt_type: 'STUK', cause_code: 'STDP', cause_desc: 'Stuck Differential Pressure', depth_ft: 21000, resp_co: 'RIG', lt_id: '941456' },
  { rig_id: '007SA', well_id: 'UTMN-707', event_from: '01 Oct 2200', hours_lost: 5.5, npt_type: 'CEMG', cause_code: 'CEMF', cause_desc: 'Cementing Failure', depth_ft: 7500, resp_co: 'SLB', lt_id: '941567' },
  { rig_id: '008BD', well_id: 'BRRI-708', event_from: '02 Oct 0100', hours_lost: 7.0, npt_type: 'WTH', cause_code: 'WTHS', cause_desc: 'Weather — Sandstorm', depth_ft: 16800, resp_co: 'N/A', lt_id: '941678' },
];

export const NPT_PARETO = [
  { cause: 'STUK', hours: 168.5, pct: 33.8 },
  { cause: 'WAIT', hours: 89.2, pct: 17.9 },
  { cause: 'MECH', hours: 72.0, pct: 14.4 },
  { cause: 'CSG', hours: 52.3, pct: 10.5 },
  { cause: 'WTH', hours: 41.0, pct: 8.2 },
  { cause: 'CEMG', hours: 32.5, pct: 6.5 },
  { cause: 'FISH', hours: 25.0, pct: 5.0 },
  { cause: 'OTHER', hours: 18.0, pct: 3.6 },
];

export const FLEET_TRENDS = {
  dates: ['09/25', '09/26', '09/27', '09/28', '09/29', '09/30', '10/01', '10/02'],
  avg_rop: [11.8, 12.1, 11.5, 12.8, 13.1, 12.0, 11.9, 12.4],
  total_npt: [420, 510, 385, 440, 395, 480, 520, 498],
  total_footage: [22100, 23400, 21800, 25200, 26100, 24000, 23500, 24680],
};

export const MUD_DATA_088TE = {
  current: {
    weight_pcf: 92, fl_temp_f: 110, funnel_vis_sec: 30,
    water_vol_pct: 90, oil_vol_pct: 0, solids_vol_pct: 10,
    pv: 12, yp: 8, ph: 9.5, mud_type: 'CACLBR',
    cl_ppm: 280000, ca_ppm: 450, gels_10sec: 3, gels_10min: 5,
  },
  previous: {
    weight_pcf: 92, fl_temp_f: 108, funnel_vis_sec: 28,
    water_vol_pct: 90, oil_vol_pct: 0, solids_vol_pct: 10,
    pv: 11, yp: 7, ph: 9.0, mud_type: 'CACLBR',
    cl_ppm: 280000, ca_ppm: 440, gels_10sec: 3, gels_10min: 5,
  },
};

export const WELL_DESIGN_088TE = [
  { hole: '42"', casing: '36" conductor', depth: 125, complete: true },
  { hole: '34"', casing: '30" conductor', depth: 333, complete: true },
  { hole: '28"', casing: '24" CSG', depth: 863, complete: true },
  { hole: '22"', casing: '18-5/8" CSG', depth: 3076, complete: true },
  { hole: '17"', casing: '13-3/8" CSG', depth: 4950, complete: true },
  { hole: '12-1/4"', casing: '9-5/8" CSG', depth: 5574, complete: true },
  { hole: '8-1/2"', casing: '7" liner', depth: 19193, complete: true },
  { hole: '6-1/8"', casing: 'Open hole', depth: 23695, complete: true },
];

export const HSE_DATA = {
  bop_test_date: '09/23/2024',
  bop_days_ago: 9,
  near_miss_count: 0,
  alerts: [
    'HSE Alert 118-24: Leg Injury During Forklift Operation',
    'HSE Alert 120-24: Incident with Fatal Injury — Industry Alert',
  ],
  campaigns: [
    'Hand & Finger Injury Prevention Campaign',
    'Fall Protection Safety Campaign',
  ],
  safety_drills: '2EA × TRIP',
  aramco_personnel: [
    { name: 'ABDULMOHSEN ALOTAIBI', id: '8494366', role: 'Material Expeditor', since: '09/30/2024' },
    { name: 'KHALID S. ALSHAMRANI', id: '812868', role: 'Foreman Trainee', since: '09/30/2024' },
  ],
};
