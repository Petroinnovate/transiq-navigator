import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { FLEET_TRENDS } from '@/data/mockData';

export const FleetTrendsChart: React.FC = () => {
  const [metric, setMetric] = useState<'avg_rop' | 'total_npt' | 'total_footage'>('avg_rop');
  
  const data = FLEET_TRENDS.dates.map((d, i) => ({
    date: d,
    avg_rop: FLEET_TRENDS.avg_rop[i],
    total_npt: FLEET_TRENDS.total_npt[i],
    total_footage: FLEET_TRENDS.total_footage[i],
  }));

  const configs = {
    avg_rop: { color: 'hsl(152, 100%, 33%)', label: 'Avg ROP (ft/hr)' },
    total_npt: { color: 'hsl(0, 100%, 62%)', label: 'Total NPT (hrs)' },
    total_footage: { color: 'hsl(204, 100%, 62%)', label: 'Total Footage (ft)' },
  };

  return (
    <div className="card-surface p-4 h-full">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">Fleet Trends — 7 Day</h3>
        <div className="flex gap-1 text-[10px]">
          {Object.entries(configs).map(([key, cfg]) => (
            <button
              key={key}
              onClick={() => setMetric(key as typeof metric)}
              className={`px-2 py-0.5 rounded ${metric === key ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}
            >
              {cfg.label.split(' (')[0]}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 25%, 16%)" />
          <XAxis dataKey="date" tick={{ fill: 'hsl(218, 20%, 55%)', fontSize: 11 }} stroke="hsl(220, 25%, 20%)" />
          <YAxis tick={{ fill: 'hsl(218, 20%, 55%)', fontSize: 11 }} stroke="hsl(220, 25%, 20%)" />
          <Tooltip
            contentStyle={{ background: 'hsl(222, 40%, 8%)', border: '1px solid hsl(220, 25%, 20%)', borderRadius: 6, fontSize: 12 }}
            labelStyle={{ color: 'hsl(210, 40%, 96%)' }}
          />
          <Line type="monotone" dataKey={metric} stroke={configs[metric].color} strokeWidth={2} dot={{ fill: configs[metric].color, r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
