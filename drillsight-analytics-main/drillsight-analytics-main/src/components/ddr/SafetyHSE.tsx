import React from 'react';
import { motion } from 'framer-motion';
import { EmptyState } from './EmptyState';
import { Shield, AlertTriangle, Activity } from 'lucide-react';

const fadeIn = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.4 } };

export const SafetyHSE: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* HSE Hero Cards — empty */}
      <motion.div {...fadeIn} className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { title: 'BOP Test', icon: <Shield className="w-4 h-4" /> },
          { title: 'BOP Drills' },
          { title: 'Near Misses', icon: <AlertTriangle className="w-4 h-4" /> },
          { title: 'Safety Drills', icon: <Activity className="w-4 h-4" /> },
        ].map(kpi => (
          <div key={kpi.title} className="card-surface p-4 border-l-2 border-border">
            <div className="flex items-center gap-2 mb-2">
              {kpi.icon && <span className="text-muted-foreground">{kpi.icon}</span>}
              <span className="text-xs uppercase tracking-wider text-muted-foreground font-medium">{kpi.title}</span>
            </div>
            <span className="text-kpi-sm text-muted-foreground">—</span>
            <div className="text-xs text-muted-foreground mt-1">No Data</div>
          </div>
        ))}
      </motion.div>

      {/* HSE Alerts — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.1 }}>
        <EmptyState
          title="HSE Alerts"
          message="HSE alerts require GET /rigs/:rig_id/hse."
        />
      </motion.div>

      {/* Safety Campaigns — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.2 }}>
        <EmptyState
          title="Active Safety Campaigns"
          message="Campaign data requires GET /rigs/:rig_id/hse."
        />
      </motion.div>

      {/* Aramco Personnel — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.3 }}>
        <EmptyState
          title="Aramco Personnel on Location"
          message="Personnel data requires GET /rigs/:rig_id/hse."
        />
      </motion.div>
    </div>
  );
};
