import React from 'react';
import { motion } from 'framer-motion';
import { EmptyState } from './EmptyState';
import { FlaskConical, Thermometer, Droplets } from 'lucide-react';

const fadeIn = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.4 } };

export const MudEngineering: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Mud Identity Banner — empty */}
      <motion.div {...fadeIn} className="card-surface p-4 border-l-2 border-border">
        <div className="text-sm font-bold text-muted-foreground">
          No Rig Selected — Mud data requires GET /rigs/:rig_id/mud
        </div>
      </motion.div>

      {/* Mud KPIs — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.1 }} className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { title: 'Weight', icon: <FlaskConical className="w-4 h-4" /> },
          { title: 'pH', icon: <Droplets className="w-4 h-4" /> },
          { title: 'CL (PPM)' },
          { title: 'FL Temp', icon: <Thermometer className="w-4 h-4" /> },
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

      {/* Comparison Table — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.2 }}>
        <EmptyState
          title="Mud Record Comparison"
          message="Mud comparison table requires GET /rigs/:rig_id/mud with current and previous records."
        />
      </motion.div>

      {/* Treatment — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.3 }}>
        <EmptyState
          title="Mud Treatment"
          message="Treatment data requires GET /rigs/:rig_id/mud."
        />
      </motion.div>
    </div>
  );
};
