import React from 'react';
import { motion } from 'framer-motion';
import { EmptyState } from './EmptyState';
import { Ruler, Clock, Gauge, MapPin } from 'lucide-react';

const fadeIn = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.4 } };

export const DrillingPerformance: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Rig Selector — empty */}
      <motion.div {...fadeIn} className="flex items-center gap-3">
        <select
          disabled
          className="card-surface px-3 py-2 text-sm text-muted-foreground bg-card border border-border rounded outline-none cursor-not-allowed"
        >
          <option>No rigs available — connect API</option>
        </select>
      </motion.div>

      {/* Rig Identity Banner — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.1 }} className="card-surface p-4 border-l-2 border-border">
        <div className="text-lg font-bold text-muted-foreground mb-1">
          No Rig Selected
        </div>
        <p className="text-xs text-muted-foreground">
          Rig identity data requires GET /rigs/:rig_id
        </p>
      </motion.div>

      {/* Depth KPIs — empty placeholders */}
      <motion.div {...fadeIn} transition={{ delay: 0.2 }} className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {[
          { title: 'Current MD', icon: <Ruler className="w-4 h-4" /> },
          { title: 'Daily Footage', icon: <Gauge className="w-4 h-4" /> },
          { title: 'ROP', icon: <Gauge className="w-4 h-4" /> },
          { title: 'Days Spud', icon: <Clock className="w-4 h-4" /> },
          { title: 'Circ%' },
          { title: 'Next Location', icon: <MapPin className="w-4 h-4" /> },
        ].map(kpi => (
          <div key={kpi.title} className="card-surface p-4 border-l-2 border-border">
            <div className="flex items-center gap-2 mb-2">
              {kpi.icon && <span className="text-muted-foreground">{kpi.icon}</span>}
              <span className="text-xs uppercase tracking-wider text-muted-foreground font-medium">{kpi.title}</span>
            </div>
            <span className="text-kpi-sm text-muted-foreground">—</span>
          </div>
        ))}
      </motion.div>

      {/* Depth Progress — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.25 }} className="card-surface p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-foreground">Depth Progress</h3>
          <span className="text-xs text-muted-foreground">No Data</span>
        </div>
        <div className="w-full h-3 bg-muted rounded-full overflow-hidden" />
      </motion.div>

      {/* 24-Hour Timeline — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.3 }}>
        <EmptyState
          title="24-Hour Timeline"
          message="Timeline data requires GET /rigs/:rig_id/timeline."
        />
      </motion.div>

      {/* Well Design Milestones — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.4 }}>
        <EmptyState
          title="Well Design Milestones"
          message="Well design data requires GET /rigs/:rig_id/well-design."
        />
      </motion.div>
    </div>
  );
};
