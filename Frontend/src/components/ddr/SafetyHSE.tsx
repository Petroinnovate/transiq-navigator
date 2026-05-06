// ============================================================================
// Safety HSE Module — Module 5
// ============================================================================

import React from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useRigDetail, useRigHSE } from '@/api/hooks/useDDRHooks';
import RigIdentityBanner from './RigIdentityBanner';
import { LoadingState, EmptyState } from '@/components/ddr/state';
import { DDR_TOKENS } from '@/styles/tokens';
import { AlertTriangle, ShieldCheck, Users } from 'lucide-react';

interface SafetyHSEProps {
  rigId: string;
}

const SafetyHSE: React.FC<SafetyHSEProps> = ({ rigId }) => {
  const { reportDate } = useDDR();
  const { data: rig } = useRigDetail(rigId, reportDate);
  const { data: hse, isLoading } = useRigHSE(rigId, reportDate);

  if (isLoading) return <LoadingState message="Loading safety & HSE data..." />;
  if (!rig || !hse) return <EmptyState title="No HSE Data" message="Select a rig to view safety & HSE data" />;

  const bopDaysClass = hse.bop_test_days_ago > 14 ? 'text-red-400' : hse.bop_test_days_ago > 7 ? 'text-amber-400' : 'text-emerald-400';

  return (
    <div className="space-y-6">
      <RigIdentityBanner identity={rig.identity} />

      {/* HSE Hero Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <HeroCard label="BOP Test" value={hse.bop_test_date} sub={`${hse.bop_test_days_ago} days ago`} subClass={bopDaysClass} icon={<ShieldCheck className="h-5 w-5" />} />
        <HeroCard label="BOP Drills" value={hse.bop_drills_date} sub="Last drill date" icon={<ShieldCheck className="h-5 w-5" />} />
        <HeroCard label="Near Misses" value={String(hse.near_miss_count)} sub="Today" subClass={hse.near_miss_count > 0 ? 'text-amber-400' : 'text-emerald-400'} icon={<AlertTriangle className="h-5 w-5" />} />
        <HeroCard label="Incident ID" value={hse.incident_id || 'None'} sub={hse.incident_id ? 'Active' : 'Clear'} subClass={hse.incident_id ? 'text-red-400' : 'text-emerald-400'} icon={<AlertTriangle className="h-5 w-5" />} />
      </div>

      {/* HSE Alerts */}
      {hse.hse_alerts.length > 0 && (
        <div className="rounded-xl p-4 space-y-2" style={{ background: DDR_TOKENS.bg.secondary }}>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-2">HSE Alerts</h3>
          {hse.hse_alerts.map((alert, i) => (
            <div key={i} className="flex items-start gap-2 text-xs p-2 rounded" style={{ background: 'rgba(255,77,79,0.06)', border: '1px solid rgba(255,77,79,0.2)' }}>
              <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
              <span className="text-red-300">{alert}</span>
            </div>
          ))}
        </div>
      )}

      {/* Safety Campaigns */}
      {hse.safety_campaigns.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary }}>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-2">Safety Campaigns</h3>
          <div className="space-y-1">
            {hse.safety_campaigns.map((c, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-slate-300">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                {c}
              </div>
            ))}
          </div>
          {hse.safety_drills && (
            <div className="mt-2 text-xs text-slate-400">
              Safety Drills: <span className="text-white">{hse.safety_drills}</span>
            </div>
          )}
        </div>
      )}

      {/* Aramco Personnel on Location */}
      {hse.aramco_personnel.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary }}>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
            <Users className="h-4 w-4" /> Aramco Personnel on Location
          </h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-700/40">
                <th scope="col" className="text-left py-1.5 px-2 text-slate-500 uppercase font-semibold">Name</th>
                <th scope="col" className="text-left py-1.5 px-2 text-slate-500 uppercase font-semibold">ID</th>
                <th scope="col" className="text-left py-1.5 px-2 text-slate-500 uppercase font-semibold">Role</th>
                <th scope="col" className="text-left py-1.5 px-2 text-slate-500 uppercase font-semibold">Since</th>
              </tr>
            </thead>
            <tbody>
              {hse.aramco_personnel.map((p) => (
                <tr key={p.id} className="border-b border-slate-700/20">
                  <td className="py-1.5 px-2 text-white">{p.name}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-400">{p.id}</td>
                  <td className="py-1.5 px-2 text-slate-300">{p.role}</td>
                  <td className="py-1.5 px-2 text-slate-400">{p.since}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Citation */}
      <div className="text-[10px] font-mono text-center" style={{ color: DDR_TOKENS.citation.badgeText }}>
        {hse.source_citation}
      </div>
    </div>
  );
};

// Mini card sub-component
const HeroCard: React.FC<{ label: string; value: string; sub: string; subClass?: string; icon: React.ReactNode }> = ({
  label, value, sub, subClass = 'text-slate-400', icon,
}) => (
  <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary, border: `1px solid ${DDR_TOKENS.surface.border}` }}>
    <div className="flex items-center gap-2 mb-2">
      <span className="text-slate-500">{icon}</span>
      <span className="text-[10px] uppercase tracking-wider text-slate-500">{label}</span>
    </div>
    <div className="text-lg font-bold text-white">{value}</div>
    <div className={`text-xs mt-0.5 ${subClass}`}>{sub}</div>
  </div>
);

export default SafetyHSE;
