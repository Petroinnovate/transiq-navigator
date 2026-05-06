import React from 'react';
import { Bell, Search, Settings } from 'lucide-react';
import { useHealthCheck } from '@/hooks/useHealthCheck';

interface TopBarProps {
  reportDate?: string;
  criticalAlerts?: number;
  onToggleSidebar: () => void;
  userName?: string;
  onLogout?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ reportDate, criticalAlerts = 0, onToggleSidebar, userName, onLogout }) => {
  const { data: health } = useHealthCheck();
  const isHealthy = health?.status === 'ok' || health?.status === 'healthy';

  return (
    <header className="h-14 glass-panel border-b flex items-center justify-between px-4 sticky top-0 z-40">
      <div className="flex items-center gap-4">
        <button onClick={onToggleSidebar} className="text-primary font-bold text-lg tracking-tight flex items-center gap-2">
          <span className="text-xl">🛢️</span>
          <span className="hidden md:inline">DDR Intelligence</span>
        </button>
        <div className="hidden md:flex items-center gap-3 text-xs">
          {/* Backend health indicator */}
          <span className="card-surface px-2 py-1 flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-ddr-excellent' : health === null ? 'bg-ddr-standby animate-pulse' : 'bg-ddr-critical'}`} />
            <span className="text-muted-foreground">{isHealthy ? 'API Connected' : 'API Offline'}</span>
          </span>
          <span className="card-surface px-2 py-1 text-muted-foreground">
            Report: <span className="text-foreground font-medium">{reportDate || '—'}</span>
          </span>
          {criticalAlerts > 0 && (
            <span className="card-surface px-2 py-1 text-ddr-critical animate-pulse">
              ⚠️ {criticalAlerts} Critical
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden lg:flex items-center card-surface rounded-md px-3 py-1.5 gap-2 w-64">
          <Search className="w-3.5 h-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder='Search rigs, wells, events...'
            className="bg-transparent text-xs text-foreground outline-none flex-1 placeholder:text-muted-foreground"
          />
        </div>
        <button className="relative p-1.5 rounded text-muted-foreground hover:text-foreground transition-colors">
          <Bell className="w-4 h-4" />
          {criticalAlerts > 0 && <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-ddr-critical rounded-full" />}
        </button>
        <button className="p-1.5 rounded text-muted-foreground hover:text-foreground transition-colors">
          <Settings className="w-4 h-4" />
        </button>
        <div className="flex items-center gap-2 card-surface px-2 py-1 rounded">
          <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-primary-foreground">
            {userName ? userName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : '??'}
          </div>
          <span className="text-xs hidden md:inline">{userName || 'Not Signed In'}</span>
          {onLogout && (
            <button onClick={onLogout} className="text-[10px] text-muted-foreground hover:text-destructive transition-colors ml-1">
              ✕
            </button>
          )}
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
    </header>
  );
};
