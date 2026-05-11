// ============================================================================
// DDR TopBar — Glass-panel header with health, search, alerts, avatar
// Embedded inside DDRDashboard (Option B)
// ============================================================================

import React, { useState, useRef, useEffect } from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { useAuth } from '@/contexts/AuthContext';
import { useHealthCheck } from '@/hooks/useHealthCheck';
import { useFleetSummary } from '@/api/hooks/useDDRHooks';
import ReportDateSelector from './ReportDateSelector';
import { DDR_TOKENS } from '@/styles/tokens';
import {
  Search, Bell, X, LogOut, User,
  AlertTriangle, Activity, Wifi, WifiOff,
} from 'lucide-react';

// ── Health Indicator ────────────────────────────────────────────────────────

const HealthIndicator: React.FC = () => {
  const { status, isHealthy, isCritical } = useHealthCheck();

  const color = isHealthy
    ? DDR_TOKENS.status.excellent
    : isCritical
      ? DDR_TOKENS.status.critical
      : DDR_TOKENS.status.warning;

  const Icon = isHealthy ? Wifi : isCritical ? WifiOff : Activity;
  const label = isHealthy ? 'Connected' : isCritical ? 'Disconnected' : 'Checking...';

  return (
    <div className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-medium"
      style={{ background: `${color}15`, color }}
      title={`Backend: ${status}`}
    >
      <Icon className="h-3 w-3" />
      <span className="hidden lg:inline">{label}</span>
    </div>
  );
};

// ── Alert Badge ─────────────────────────────────────────────────────────────

interface AlertBadgeProps {
  criticalCount: number;
}

const AlertBadge: React.FC<AlertBadgeProps> = ({ criticalCount }) => (
  <button
    className="relative p-2 rounded-md hover:bg-white/5 text-slate-400 hover:text-white transition-colors"
    aria-label={`${criticalCount} critical alerts`}
  >
    <AlertTriangle className="h-4 w-4" />
    {criticalCount > 0 && (
      <span
        className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 flex items-center justify-center rounded-full text-[9px] font-bold text-white px-1 animate-pulse"
        style={{ background: DDR_TOKENS.status.critical }}
      >
        {criticalCount}
      </span>
    )}
  </button>
);

// ── Notification Bell ───────────────────────────────────────────────────────

const NotificationBell: React.FC<{ hasNew?: boolean }> = ({ hasNew }) => (
  <button
    className="relative p-2 rounded-md hover:bg-white/5 text-slate-400 hover:text-white transition-colors"
    aria-label="Notifications"
  >
    <Bell className="h-4 w-4" />
    {hasNew && (
      <span
        className="absolute top-1 right-1 w-2 h-2 rounded-full"
        style={{ background: DDR_TOKENS.status.critical }}
      />
    )}
  </button>
);

// ── User Avatar ─────────────────────────────────────────────────────────────

const UserAvatar: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const initials = user?.user_metadata?.display_name
    ? (user.user_metadata?.display_name as string).split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() ?? 'U';

  const displayName = user?.user_metadata?.display_name || user?.email || 'User';

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-white/5 transition-colors"
        aria-label="User menu"
      >
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold text-white border border-cyan-500/30"
          style={{ background: 'rgba(6,182,212,0.15)' }}
        >
          {initials}
        </div>
        <span className="text-xs text-slate-300 hidden lg:inline max-w-[100px] truncate">
          {displayName}
        </span>
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-52 rounded-xl p-2 z-50 border"
          style={{
            background: DDR_TOKENS.bg.overlay,
            borderColor: DDR_TOKENS.surface.border,
          }}
        >
          <div className="px-3 py-2 border-b border-slate-700/40 mb-1">
            <div className="text-xs font-semibold text-white truncate">{displayName}</div>
            {user?.email && (
              <div className="text-[10px] text-slate-500 truncate">{user.email}</div>
            )}
          </div>
          {isAuthenticated && (
            <button
              onClick={() => { setOpen(false); logout(); }}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-xs text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </button>
          )}
        </div>
      )}
    </div>
  );
};

// ── Search Bar ──────────────────────────────────────────────────────────────

interface TopBarSearchProps {
  onSearch?: (query: string) => void;
}

const TopBarSearch: React.FC<TopBarSearchProps> = ({ onSearch }) => {
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) onSearch?.(query.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors ${
          focused
            ? 'border-cyan-500/40 bg-white/5'
            : 'border-slate-700/40 bg-white/[0.02]'
        }`}
      >
        <Search className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Search rig, well, event..."
          className="bg-transparent text-xs text-white placeholder:text-slate-600 outline-none w-32 lg:w-48"
          aria-label="Search rigs, wells, and events"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery('')}
            className="text-slate-500 hover:text-slate-300"
            aria-label="Clear search"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>
    </form>
  );
};

// ── Main TopBar ─────────────────────────────────────────────────────────────

interface DDRTopBarProps {
  selectedRigId: string | null;
  onClearRig: () => void;
}

const DDRTopBar: React.FC<DDRTopBarProps> = ({ selectedRigId, onClearRig }) => {
  const { reportDate } = useDDR();
  const { data: fleet } = useFleetSummary(reportDate);
  const criticalCount = fleet?.rigs_critical ?? 0;

  return (
    <header className="relative flex-shrink-0">
      {/* Glass panel header */}
      <div className="glass-panel h-14 flex items-center justify-between px-4 border-b border-white/[0.06]">
        {/* Left section — branding + date + rig context */}
        <div className="flex items-center gap-4">
          <span className="text-sm font-bold text-white flex items-center gap-1.5">
            🛢️ <span className="hidden sm:inline">DDR Intelligence</span>
          </span>

          <div className="h-5 w-px bg-slate-700/60" />

          <ReportDateSelector />

          {selectedRigId && (
            <>
              <div className="h-5 w-px bg-slate-700/60" />
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">Rig</span>
                <span className="text-xs font-mono text-cyan-400 px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20">
                  {selectedRigId}
                </span>
                <button
                  onClick={onClearRig}
                  className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
                  aria-label="Clear rig selection"
                >
                  ✕
                </button>
              </div>
            </>
          )}
        </div>

        {/* Center — search */}
        <div className="hidden md:block">
          <TopBarSearch />
        </div>

        {/* Right section — health, alerts, notifications, avatar */}
        <div className="flex items-center gap-1.5">
          <HealthIndicator />

          <div className="h-5 w-px bg-slate-700/60 mx-1" />

          <AlertBadge criticalCount={criticalCount} />
          <NotificationBell hasNew={criticalCount > 0} />

          <div className="h-5 w-px bg-slate-700/60 mx-1" />

          <div className="text-[9px] text-slate-600 uppercase tracking-wider px-2 py-1 rounded border border-slate-700/30 hidden xl:block">
            Saudi Aramco: Confidential
          </div>

          <UserAvatar />
        </div>
      </div>

      {/* Bottom gradient decorative line */}
      <div
        className="h-[1px]"
        style={{
          background: `linear-gradient(90deg, transparent 0%, ${DDR_TOKENS.brand.aramcoGreen}40 30%, ${DDR_TOKENS.status.normal}40 70%, transparent 100%)`,
        }}
      />
    </header>
  );
};

export default DDRTopBar;
