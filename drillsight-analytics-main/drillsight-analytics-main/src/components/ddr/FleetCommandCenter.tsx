import React from 'react';
import { motion } from 'framer-motion';
import { EmptyState } from './EmptyState';
import { Factory, Pickaxe, Gauge, Clock, Ruler, Users } from 'lucide-react';

const fadeIn = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.4 } };

export const FleetCommandCenter: React.FC = () => {
  // No mock data — all sections show empty state until backend is connected
  return (
    <div className="space-y-6">
      {/* Priority Alerts — No Data */}
      <motion.div {...fadeIn}>
        <EmptyState
          title="No Active Alerts"
          message="Critical alerts will appear here when connected to the fleet API (GET /fleet/summary)."
          icon={<Clock className="w-10 h-10 mx-auto text-muted-foreground" />}
        />
      </motion.div>

      {/* Hero Header */}
      <motion.div {...fadeIn} transition={{ delay: 0.1 }}>
        <div className="flex items-baseline gap-3 mb-1">
          <h1 className="text-2xl font-bold text-foreground">Fleet Operations</h1>
          <span className="text-muted-foreground text-sm">—</span>
        </div>
        <p className="text-muted-foreground text-sm">No report loaded · Connect API to begin</p>
      </motion.div>

      {/* Hero KPI Row — Empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.2 }} className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {[
          { title: 'Total Rigs', icon: <Factory className="w-4 h-4" /> },
          { title: 'Drilling', icon: <Pickaxe className="w-4 h-4" /> },
          { title: 'Avg ROP', icon: <Gauge className="w-4 h-4" /> },
          { title: 'Total NPT', icon: <Clock className="w-4 h-4" /> },
          { title: 'Fleet Footage', icon: <Ruler className="w-4 h-4" /> },
          { title: 'Personnel', icon: <Users className="w-4 h-4" /> },
        ].map(kpi => (
          <div key={kpi.title} className="card-surface p-4 border-l-2 border-border">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-muted-foreground">{kpi.icon}</span>
              <span className="text-xs uppercase tracking-wider text-muted-foreground font-medium">{kpi.title}</span>
            </div>
            <span className="text-kpi-sm text-muted-foreground">—</span>
            <div className="text-xs text-muted-foreground mt-1">No Data</div>
          </div>
        ))}
      </motion.div>

      {/* Rig Status Heatmap — Empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.3 }}>
        <EmptyState
          title="Rig Status Heatmap"
          message="Heatmap will render 267 rig tiles when connected to GET /fleet/heatmap."
        />
      </motion.div>

      {/* Two-column: Performers + Trends — Empty */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <motion.div {...fadeIn} transition={{ delay: 0.4 }}>
          <EmptyState
            title="Fleet Performers"
            message="Top/Bottom performer tables require GET /fleet/top-performers."
          />
        </motion.div>
        <motion.div {...fadeIn} transition={{ delay: 0.5 }}>
          <EmptyState
            title="Fleet Trends"
            message="7/14/30-day trend charts require GET /fleet/trends."
          />
        </motion.div>
      </div>
    </div>
  );
};
