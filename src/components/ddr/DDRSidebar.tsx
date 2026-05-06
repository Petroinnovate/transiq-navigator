// ============================================================================
// DDR Sidebar Navigation — 11 modules + system links
// Structured with SECTIONS for grouped navigation
// ============================================================================

import React from 'react';
import { useDDR } from '@/contexts/DDRContext';
import { cn } from '@/lib/utils';
import {
  Factory, Pickaxe, Timer, FlaskConical, ShieldCheck, Users,
  BarChart3, Map, Bot, ClipboardList, FileText,
  ChevronLeft, ChevronRight,
} from 'lucide-react';

// ── Types ───────────────────────────────────────────────────────────────────

export type ModuleId =
  | 'fleet-command'
  | 'drilling-performance'
  | 'npt-intelligence'
  | 'mud-engineering'
  | 'safety-hse'
  | 'personnel-logistics'
  | 'six-sigma-spc'
  | 'survey-wellbore'
  | 'ai-qa'
  | 'audit-trail'
  | 'report-viewer';

export interface DDRNavItem {
  id: ModuleId;
  label: string;
  icon: React.ReactNode;
}

interface DDRSection {
  title: string;
  items: DDRNavItem[];
}

// ── Section Definitions ─────────────────────────────────────────────────────

const SECTIONS: DDRSection[] = [
  {
    title: 'FLEET OVERVIEW',
    items: [
      { id: 'fleet-command', label: 'Fleet Command', icon: <Factory className="h-4 w-4" /> },
    ],
  },
  {
    title: 'RIG ANALYSIS',
    items: [
      { id: 'drilling-performance', label: 'Drilling Perf.', icon: <Pickaxe className="h-4 w-4" /> },
      { id: 'npt-intelligence', label: 'NPT Intelligence', icon: <Timer className="h-4 w-4" /> },
      { id: 'mud-engineering', label: 'Mud Engineering', icon: <FlaskConical className="h-4 w-4" /> },
      { id: 'safety-hse', label: 'Safety & HSE', icon: <ShieldCheck className="h-4 w-4" /> },
      { id: 'personnel-logistics', label: 'Personnel', icon: <Users className="h-4 w-4" /> },
    ],
  },
  {
    title: 'AI & ANALYTICS',
    items: [
      { id: 'six-sigma-spc', label: 'Six Sigma/SPC', icon: <BarChart3 className="h-4 w-4" /> },
      { id: 'survey-wellbore', label: 'Survey & Wells', icon: <Map className="h-4 w-4" /> },
      { id: 'ai-qa', label: 'AI Q&A (RAG)', icon: <Bot className="h-4 w-4" /> },
    ],
  },
  {
    title: 'SYSTEM',
    items: [
      { id: 'audit-trail', label: 'Audit Trail', icon: <ClipboardList className="h-4 w-4" /> },
      { id: 'report-viewer', label: 'Report Viewer', icon: <FileText className="h-4 w-4" /> },
    ],
  },
];

// Flat list for backward compatibility
const DDR_NAV_ITEMS: (DDRNavItem & { group: string })[] = SECTIONS.flatMap(s =>
  s.items.map(item => ({ ...item, group: s.title }))
);

// ── Component ───────────────────────────────────────────────────────────────

interface DDRSidebarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

// Reusable nav link with forwardRef for sidebar items
const NavLink = React.forwardRef<
  HTMLButtonElement,
  { item: DDRNavItem; active: boolean; collapsed: boolean; onClick: () => void }
>(({ item, active, collapsed, onClick }, ref) => (
  <button
    ref={ref}
    onClick={onClick}
    className={cn(
      'w-full flex items-center gap-3 px-2.5 py-2 rounded-md text-sm transition-all duration-150',
      'hover:bg-slate-800/60 hover:text-white',
      active
        ? 'bg-cyan-500/10 text-cyan-400 border-l-2 border-l-cyan-400 border-y border-r border-y-cyan-500/20 border-r-cyan-500/20'
        : 'text-slate-400 border border-transparent'
    )}
    title={collapsed ? item.label : undefined}
    aria-current={active ? 'page' : undefined}
  >
    <span className={cn(
      'flex-shrink-0',
      active ? 'text-cyan-400' : 'text-slate-500'
    )}>
      {item.icon}
    </span>
    {!collapsed && <span className="truncate">{item.label}</span>}
  </button>
));
NavLink.displayName = 'NavLink';

const DDRSidebar: React.FC<DDRSidebarProps> = ({ collapsed = false, onToggleCollapse }) => {
  const { activeModule, setActiveModule } = useDDR();

  return (
    <aside
      className={cn(
        'h-full flex flex-col border-r border-slate-700/60 bg-slate-900/80 backdrop-blur-sm transition-all duration-300 ease-in-out',
        collapsed ? 'w-16' : 'w-60'
      )}
    >
      {/* Header */}
      <div className="px-3 py-4 border-b border-slate-700/40 flex items-center justify-center">
        {collapsed ? (
          <span className="text-lg" title="DDR Intel">🛢️</span>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white">🛢️ DDR Intel</span>
            <span className="text-[9px] text-slate-600 font-mono">v2</span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2 px-2" aria-label="DDR Navigation">
        {SECTIONS.map((section, sectionIdx) => (
          <div key={section.title} className={cn('mb-1', sectionIdx > 0 && 'mt-2 pt-2 border-t border-slate-700/20')}>
            {!collapsed && (
              <div className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                {section.title}
              </div>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.id}
                  item={item}
                  active={activeModule === item.id}
                  collapsed={collapsed}
                  onClick={() => setActiveModule(item.id)}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-slate-700/40 p-2">
        <button
          onClick={onToggleCollapse}
          className="w-full flex items-center justify-center gap-2 px-2.5 py-2 rounded-md text-xs text-slate-500 hover:text-slate-300 hover:bg-slate-800/60 transition-all"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : (
            <>
              <ChevronLeft className="h-4 w-4" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
};

export { DDR_NAV_ITEMS, SECTIONS };
export default DDRSidebar;
