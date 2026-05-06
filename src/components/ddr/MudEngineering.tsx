// ============================================================================
// Mud Engineering Module — Module 4
// ============================================================================

import React from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useRigDetail, useRigMud } from '@/api/hooks/useDDRHooks';
import MudComparisonTable from './MudComparisonTable';
import RigIdentityBanner from './RigIdentityBanner';
import { LoadingState, EmptyState } from '@/components/ddr/state';
import { DDR_TOKENS } from '@/styles/tokens';

interface MudEngineeringProps {
  rigId: string;
}

const MudEngineering: React.FC<MudEngineeringProps> = ({ rigId }) => {
  const { reportDate } = useDDR();
  const { data: rig } = useRigDetail(rigId, reportDate);
  const { data: mudRecords, isLoading } = useRigMud(rigId, reportDate);

  if (isLoading) {
    return <LoadingState message="Loading mud engineering data..." />;
  }

  if (!rig || !mudRecords) {
    return <EmptyState title="No Mud Data" message="Select a rig to view mud engineering data" />;
  }

  const rec1 = mudRecords.find(r => r.record_no === 1);

  return (
    <div className="space-y-6">
      <RigIdentityBanner identity={rig.identity} />

      {/* Mud Identity */}
      {rec1 && (
        <div className="rounded-xl p-4" style={{ background: DDR_TOKENS.bg.secondary, border: `1px solid ${DDR_TOKENS.surface.border}` }}>
          <div className="text-xs text-slate-400">
            Mud Type: <span className="text-cyan-400 font-bold">{rec1.mud_type}</span>
          </div>
        </div>
      )}

      {/* Mud Comparison Table */}
      <MudComparisonTable records={mudRecords} identity={rig.identity} />
    </div>
  );
};

export default MudEngineering;
