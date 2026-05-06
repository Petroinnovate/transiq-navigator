import React from 'react';
import { motion } from 'framer-motion';
import { DatabaseZap } from 'lucide-react';

const fadeIn = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.4 } };

export const PlaceholderModule: React.FC<{ title: string; description: string }> = ({ title, description }) => (
  <motion.div {...fadeIn} className="card-surface p-8 text-center">
    <DatabaseZap className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
    <h2 className="text-xl font-bold text-foreground mb-2">{title}</h2>
    <p className="text-sm text-muted-foreground mb-4 max-w-md mx-auto">{description}</p>
    <div className="inline-block card-surface px-4 py-2 text-xs text-muted-foreground border border-border rounded">
      No Data Available — Connect backend API to activate
    </div>
  </motion.div>
);
