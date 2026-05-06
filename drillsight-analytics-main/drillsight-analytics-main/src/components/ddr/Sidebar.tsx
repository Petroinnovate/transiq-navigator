import React from 'react';
import { 
  Factory, Pickaxe, Clock, FlaskConical, HardHat, Users,
  BarChart3, Map, Bot, FileSearch, FileText, Beaker, Search, Upload, ChevronLeft, ChevronRight
} from 'lucide-react';

export type ModuleId = 
  | 'fleet-command' | 'drilling-performance' | 'npt-intelligence'
  | 'mud-engineering' | 'safety-hse' | 'personnel'
  | 'six-sigma' | 'survey-wells' | 'ai-qa'
  | 'audit-trail' | 'report-viewer' | 'agent-lab' | 'search' | 'upload';

interface SidebarProps {
  activeModule: ModuleId;
  onModuleChange: (module: ModuleId) => void;
  collapsed: boolean;
  onCollapse: (c: boolean) => void;
}

const SECTIONS = [
  {
    label: 'FLEET OVERVIEW',
    items: [
      { id: 'fleet-command' as ModuleId, icon: Factory, label: 'Fleet Command' },
    ],
  },
  {
    label: 'RIG ANALYSIS',
    items: [
      { id: 'drilling-performance' as ModuleId, icon: Pickaxe, label: 'Drilling Perf.' },
      { id: 'npt-intelligence' as ModuleId, icon: Clock, label: 'NPT Intelligence' },
      { id: 'mud-engineering' as ModuleId, icon: FlaskConical, label: 'Mud Engineering' },
      { id: 'safety-hse' as ModuleId, icon: HardHat, label: 'Safety & HSE' },
      { id: 'personnel' as ModuleId, icon: Users, label: 'Personnel' },
    ],
  },
  {
    label: 'AI & ANALYTICS',
    items: [
      { id: 'six-sigma' as ModuleId, icon: BarChart3, label: 'Six Sigma / SPC' },
      { id: 'survey-wells' as ModuleId, icon: Map, label: 'Survey & Wells' },
      { id: 'ai-qa' as ModuleId, icon: Bot, label: 'AI Q&A (RAG)' },
    ],
  },
  {
    label: 'SYSTEM',
    items: [
      { id: 'audit-trail' as ModuleId, icon: FileSearch, label: 'Audit Trail' },
      { id: 'report-viewer' as ModuleId, icon: FileText, label: 'Report Viewer' },
    ],
  },
];

export const DDRSidebar: React.FC<SidebarProps> = ({ activeModule, onModuleChange, collapsed, onCollapse }) => {
  return (
    <aside className={`${collapsed ? 'w-16' : 'w-60'} transition-all duration-300 bg-sidebar border-r border-sidebar-border flex flex-col h-full`}>
      <div className="flex-1 overflow-y-auto py-3">
        {SECTIONS.map(section => (
          <div key={section.label} className="mb-4">
            {!collapsed && (
              <div className="px-4 mb-1 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
                {section.label}
              </div>
            )}
            {section.items.map(item => {
              const isActive = activeModule === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onModuleChange(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors ${
                    isActive
                      ? 'bg-sidebar-accent text-sidebar-primary font-medium border-r-2 border-sidebar-primary'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-foreground'
                  }`}
                  title={collapsed ? item.label : undefined}
                >
                  <item.icon className="w-4 h-4 flex-shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </button>
              );
            })}
          </div>
        ))}
      </div>
      <button
        onClick={() => onCollapse(!collapsed)}
        className="p-3 border-t border-sidebar-border text-muted-foreground hover:text-foreground transition-colors flex items-center justify-center"
      >
        {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </aside>
  );
};
