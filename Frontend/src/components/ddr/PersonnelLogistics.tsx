// ============================================================================
// Personnel & Logistics Module — Module 6
// ============================================================================

import React from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useRigDetail, useRigPersonnel, useRigBHA, useRigBulk } from '@/api/hooks/useDDRHooks';
import RigIdentityBanner from './RigIdentityBanner';
import PersonnelMatrix from './PersonnelMatrix';
import DrillStringDiagram from './DrillStringDiagram';
import { LoadingState, EmptyState } from '@/components/ddr/state';
import { DDR_TOKENS } from '@/styles/tokens';
import { CitationBadge } from '@/components/citation/CitationBadge';

interface PersonnelLogisticsProps {
  rigId: string;
}

const PersonnelLogistics: React.FC<PersonnelLogisticsProps> = ({ rigId }) => {
  const { reportDate } = useDDR();
  const { data: rig } = useRigDetail(rigId, reportDate);
  const { data: personnel, isLoading } = useRigPersonnel(rigId, reportDate);
  const { data: bha } = useRigBHA(rigId, reportDate);
  const { data: bulk } = useRigBulk(rigId, reportDate);

  if (isLoading) return <LoadingState message="Loading personnel & logistics data..." />;
  if (!rig) return <EmptyState title="No Personnel Data" message="Select a rig to view personnel & logistics data" />;

  return (
    <div className="space-y-6">
      <RigIdentityBanner identity={rig.identity} />

      {/* Personnel Matrix */}
      {personnel && <PersonnelMatrix rows={personnel} identity={rig.identity} />}

      {/* Bulk & Logistics Cards */}
      {bulk && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <BulkCard label="Fuel" value={bulk.fuel_bbls} unit="BBLS" identity={rig.identity} />
          <BulkCard label="Cement" value={bulk.cement_sx} unit="SX" identity={rig.identity} />
          <BulkCard label="Drill Water" value={bulk.drill_water} unit="" identity={rig.identity} />
          <BulkCard label="Pot Water" value={bulk.pot_water} unit="" identity={rig.identity} />
        </div>
      )}

      {/* Standby Vehicles */}
      {bulk?.standby_vehicles && bulk.standby_vehicles.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary }}>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-3">Standby Vehicles</h3>
          {bulk.standby_vehicles.map((v, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-slate-300 py-1">
              <span className="text-white font-mono">{v.vehicle_id}</span>
              <span className={v.status.includes('REPAIR') ? 'text-amber-400' : 'text-slate-400'}>— {v.status}</span>
              {v.notes && <span className="text-slate-500">{v.notes}</span>}
            </div>
          ))}
        </div>
      )}

      {/* Drill String / BHA */}
      {bha && bha.length > 0 && <DrillStringDiagram components={bha} />}
    </div>
  );
};

// Bulk card sub-component
const BulkCard: React.FC<{ label: string; value: any; unit: string; identity: any }> = ({
  label, value, unit, identity,
}) => {
  const displayVal = value && typeof value.value === 'number' ? value.value.toLocaleString() : 'N/A';
  return (
    <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary, border: `1px solid ${DDR_TOKENS.surface.border}` }}>
      <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">{label}</div>
      <div className="flex items-center gap-2">
        <span className="text-xl font-bold text-white font-mono">{displayVal}</span>
        {unit && <span className="text-xs text-slate-400">{unit}</span>}
        {value && value.source_citation && (
          <CitationBadge kpiValue={value} identity={identity} compact />
        )}
      </div>
    </div>
  );
};

export default PersonnelLogistics;
