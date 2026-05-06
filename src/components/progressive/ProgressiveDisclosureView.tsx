/**
 * ProgressiveDisclosureView
 * =========================
 * The "Decision OS" layer on top of the TransIQ dashboard.
 *
 * Three audience-specific views toggled by a tab bar:
 *   CEO VIEW      — 3 decisions · 3 risks · 3 actions (30-second read)
 *   MANAGER VIEW  — DMAIC breakdown · recommendations · KPI tracking
 *   ENGINEER VIEW — full technical depth (models, FMEA, root causes)
 *   BOARDROOM     — slide-ready executive narrative + export
 */
import React, { useState } from 'react';
import { Users, BarChart2, Cpu, Presentation, Layers, ShieldCheck, Target } from 'lucide-react';
import CEOView                  from './CEOView';
import ManagerView              from './ManagerView';
import EngineerView             from './EngineerView';
import BoardroomMode            from './BoardroomMode';
import ExplainabilityAuditTrail from './ExplainabilityAuditTrail';
import OutcomeDrivenView        from './OutcomeDrivenView';

interface ProgressiveDisclosureProps {
  /** Full raw dashboard object from the backend */
  dashboardData: Record<string, any>;
}

const TABS = [
  {
    id:      'ceo',
    label:   'CEO View',
    sublabel:'30-sec snapshot',
    icon:    Users,
    color:   'text-cyan-400',
    active:  'border-cyan-500 bg-cyan-500/10 text-cyan-300',
    inactive:'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-600',
  },
  {
    id:      'manager',
    label:   'Manager View',
    sublabel:'DMAIC + KPIs',
    icon:    BarChart2,
    color:   'text-violet-400',
    active:  'border-violet-500 bg-violet-500/10 text-violet-300',
    inactive:'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-600',
  },
  {
    id:      'engineer',
    label:   'Engineer View',
    sublabel:'Full technical depth',
    icon:    Cpu,
    color:   'text-amber-400',
    active:  'border-amber-500 bg-amber-500/10 text-amber-300',
    inactive:'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-600',
  },
  {
    id:      'boardroom',
    label:   'Boardroom',
    sublabel:'Slide-ready narrative',
    icon:    Presentation,
    color:   'text-emerald-400',
    active:  'border-emerald-500 bg-emerald-500/10 text-emerald-300',
    inactive:'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-600',
  },
  {
    id:      'audit',
    label:   'Audit Trail',
    sublabel:'Explainable AI',
    icon:    ShieldCheck,
    color:   'text-violet-400',
    active:  'border-violet-500 bg-violet-500/10 text-violet-300',
    inactive:'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-600',
  },
  {
    id:      'outcomes',
    label:   'Outcomes',
    sublabel:'Decision → $ Impact',
    icon:    Target,
    color:   'text-emerald-400',
    active:  'border-emerald-500 bg-emerald-500/10 text-emerald-300',
    inactive:'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-600',
  },
] as const;

type TabId = 'ceo' | 'manager' | 'engineer' | 'boardroom' | 'audit' | 'outcomes';

const ProgressiveDisclosureView: React.FC<ProgressiveDisclosureProps> = ({ dashboardData }) => {
  const [activeTab, setActiveTab] = useState<TabId>('ceo');

  // Extract progressive disclosure data from dashboard
  const ceoData        = dashboardData?.ceo_view                  || {};
  const managerData    = dashboardData?.manager_view              || {};
  const engineerData   = dashboardData?.engineer_view             || {};
  const boardroomData  = dashboardData?.boardroom_mode            || {};
  const auditData      = dashboardData?.audit_trail               || {};
  const outcomeDecisions = dashboardData?.outcome_driven_decisions || [];
  const portfolioSummary = dashboardData?.portfolio_summary       || {};
  const reportTitle    = dashboardData?.dashboard?.title || dashboardData?.title || 'TransIQ Analysis';

  // Check if any agent data is available
  const hasAgentData =
    Object.keys(ceoData).length > 0 ||
    Object.keys(managerData).length > 0 ||
    Object.keys(engineerData).length > 0 ||
    Object.keys(boardroomData).length > 0;

  if (!hasAgentData) {
    return null; // Don't render if there's no multi-agent output yet
  }

  return (
    <section className="rounded-2xl border border-slate-700/50 bg-gradient-to-br from-slate-900/80 via-slate-900/60 to-slate-900/80 overflow-hidden">

      {/* ── Section header ─────────────────────────────────────────── */}
      <div className="px-6 py-4 border-b border-slate-700/50 bg-slate-800/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500/20 to-violet-500/20 border border-cyan-500/30 flex items-center justify-center">
            <Layers className="h-5 w-5 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white leading-tight">Industrial Decision OS</h2>
            <p className="text-xs text-slate-500 mt-0.5">Decide · Execute · Justify · Learn</p>
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-2">
          {dashboardData._orchestrated && (
            <div className="flex items-center gap-1.5 rounded-full px-3 py-1 border border-cyan-500/30 bg-cyan-500/10">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-[10px] text-cyan-400 font-medium uppercase tracking-wider">Multi-Agent</span>
            </div>
          )}
          <div className="flex items-center gap-1.5 rounded-full px-3 py-1 border border-emerald-500/30 bg-emerald-500/10">
            <span className="text-[10px] text-emerald-400 font-medium uppercase tracking-wider">Six Sigma</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-full px-3 py-1 border border-violet-500/30 bg-violet-500/10">
            <span className="text-[10px] text-violet-400 font-medium uppercase tracking-wider">Explainable AI</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-full px-3 py-1 border border-amber-500/30 bg-amber-500/10">
            <span className="text-[10px] text-amber-400 font-medium uppercase tracking-wider">Auditable</span>
          </div>
        </div>
      </div>

      {/* ── Tab bar ────────────────────────────────────────────────── */}
      <div className="flex border-b border-slate-700/50 overflow-x-auto">
        {TABS.map(({ id, label, sublabel, icon: Icon, active, inactive }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as TabId)}
            className={`flex items-center gap-2.5 px-5 py-3.5 border-b-2 transition-all flex-shrink-0
              ${activeTab === id ? active : inactive}`}
          >
            <Icon className={`h-4 w-4 flex-shrink-0 ${activeTab === id ? '' : 'opacity-50'}`} />
            <div className="text-left">
              <p className="text-xs font-semibold leading-tight whitespace-nowrap">{label}</p>
              <p className={`text-[10px] leading-tight whitespace-nowrap ${activeTab === id ? 'opacity-70' : 'text-slate-600'}`}>
                {sublabel}
              </p>
            </div>
          </button>
        ))}
      </div>

      {/* ── Active view ────────────────────────────────────────────── */}
      <div className="p-6">
        {activeTab === 'ceo'       && <CEOView                  data={ceoData} />}
        {activeTab === 'manager'   && <ManagerView              data={managerData} />}
        {activeTab === 'engineer'  && <EngineerView             data={engineerData} />}
        {activeTab === 'boardroom' && <BoardroomMode            data={boardroomData} reportTitle={reportTitle} />}
        {activeTab === 'audit'     && <ExplainabilityAuditTrail data={auditData} />}
        {activeTab === 'outcomes'  && <OutcomeDrivenView        decisions={outcomeDecisions} portfolio={portfolioSummary} />}
      </div>

    </section>
  );
};

export default ProgressiveDisclosureView;
