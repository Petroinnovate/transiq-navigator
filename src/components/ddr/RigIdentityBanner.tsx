// ============================================================================
// Rig Identity Banner — Shown at top of every rig-level module
// ============================================================================

import React from 'react';
import type { RigIdentity } from '@/types/ddr.types';
import { DDR_TOKENS } from '@/styles/tokens';

interface RigIdentityBannerProps {
  identity: RigIdentity;
  daysOnWell?: number;
}

const RigIdentityBanner: React.FC<RigIdentityBannerProps> = ({ identity, daysOnWell }) => {
  return (
    <div
      className="rounded-xl p-4 font-mono text-xs leading-relaxed"
      style={{
        background: DDR_TOKENS.bg.secondary,
        border: `1px solid ${DDR_TOKENS.surface.border}`,
      }}
    >
      <div className="flex items-center gap-3 mb-2">
        <span className="text-lg font-bold text-white" style={{ fontFamily: DDR_TOKENS.font.display }}>
          RIG {identity.rig_id}
        </span>
        <span className="text-sm text-cyan-400 font-semibold">{identity.well_id}</span>
        <span className="text-sm text-slate-400">{identity.report_date}</span>
        <span className="text-sm text-slate-500">{identity.shift_period} Shift</span>
        {daysOnWell !== undefined && (
          <span className="text-xs px-2 py-0.5 rounded bg-slate-700/50 text-amber-400">
            {daysOnWell} days on well
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-x-8 gap-y-1">
        <Row label="Foreman(s)" value={identity.foremen} />
        <Row label="Objective" value={identity.objective} />
        <Row label="Engineer" value={identity.engineer} />
        <Row label="Location" value={identity.location} />
        <Row label="Manager" value={identity.manager} />
        <Row label="Programme" value={`${identity.programme_name} (${identity.programme_dates})`} />
        <Row label="THURAYA" value={identity.thuraya} />
        <Row label="Charge #" value={identity.charge_number} />
      </div>
      <div className="mt-2 pt-2 border-t border-slate-700/30 text-[10px] text-slate-500 text-center">
        {identity.classification}
      </div>
    </div>
  );
};

const Row: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="flex gap-2">
    <span className="text-slate-500 w-20 flex-shrink-0">{label}:</span>
    <span className="text-slate-300 truncate" title={value}>{value || '—'}</span>
  </div>
);

export default RigIdentityBanner;
