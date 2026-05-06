import React from 'react';
import { motion } from 'framer-motion';
import { EmptyState } from './EmptyState';
import { Clock, AlertTriangle, BarChart3 } from 'lucide-react';

const fadeIn = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.4 } };

export const NPTIntelligence: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* NPT Hero Cards — empty */}
      <motion.div {...fadeIn} className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { title: 'Fleet NPT Today', icon: <Clock className="w-4 h-4" /> },
          { title: 'Top Cause', icon: <AlertTriangle className="w-4 h-4" /> },
          { title: 'Most Affected', icon: <BarChart3 className="w-4 h-4" /> },
          { title: 'Rigs with NPT' },
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

      {/* NPT Pareto — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.15 }}>
        <EmptyState
          title="NPT Pareto Analysis"
          message="Pareto chart requires GET /fleet/npt-pareto."
        />
      </motion.div>

      {/* NPT Events Table — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.3 }}>
        <EmptyState
          title="NPT Events Log"
          message="NPT events table requires GET /rigs/:rig_id/npt."
        />
      </motion.div>
    </div>
  );
};
