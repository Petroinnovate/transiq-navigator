import React from 'react';
import { motion } from 'framer-motion';
import { EmptyState } from './EmptyState';
import { Users } from 'lucide-react';

const fadeIn = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.4 } };

export const PersonnelModule: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Summary — empty */}
      <motion.div {...fadeIn} className="card-surface p-4 border-l-2 border-border">
        <div className="flex items-center gap-3 mb-1">
          <Users className="w-5 h-5 text-muted-foreground" />
          <span className="text-lg font-bold text-muted-foreground">Personnel Matrix — No Data</span>
        </div>
        <p className="text-xs text-muted-foreground">Personnel data requires GET /rigs/:rig_id/personnel.</p>
      </motion.div>

      {/* Personnel Table — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.15 }}>
        <EmptyState
          title="Personnel by Company"
          message="Connect to GET /rigs/:rig_id/personnel to view crew distribution."
        />
      </motion.div>

      {/* Distribution — empty */}
      <motion.div {...fadeIn} transition={{ delay: 0.3 }}>
        <EmptyState
          title="Distribution Chart"
          message="Distribution visualization requires personnel API data."
        />
      </motion.div>
    </div>
  );
};
