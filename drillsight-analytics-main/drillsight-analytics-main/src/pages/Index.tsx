import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TopBar } from '@/components/ddr/TopBar';
import { DDRSidebar, type ModuleId } from '@/components/ddr/Sidebar';
import { FleetCommandCenter } from '@/components/ddr/FleetCommandCenter';
import { DrillingPerformance } from '@/components/ddr/DrillingPerformance';
import { NPTIntelligence } from '@/components/ddr/NPTIntelligence';
import { MudEngineering } from '@/components/ddr/MudEngineering';
import { SafetyHSE } from '@/components/ddr/SafetyHSE';
import { PersonnelModule } from '@/components/ddr/PersonnelModule';
import { PlaceholderModule } from '@/components/ddr/PlaceholderModule';
import { useAuth } from '@/hooks/useAuth';

const MODULE_TITLES: Record<ModuleId, string> = {
  'fleet-command': 'Fleet Command Center',
  'drilling-performance': 'Drilling Performance',
  'npt-intelligence': 'NPT & Lost-Time Intelligence',
  'mud-engineering': 'Mud & Fluid Engineering',
  'safety-hse': 'Safety, HSE & Compliance',
  'personnel': 'Personnel & Logistics',
  'six-sigma': 'Six Sigma / SPC Analysis',
  'survey-wells': 'Survey & Wells',
  'ai-qa': 'AI Q&A (RAG)',
  'audit-trail': 'Explainability & Audit Trail',
  'report-viewer': 'Report Viewer',
  'agent-lab': 'Agent Lab',
  'search': 'Search',
  'upload': 'Upload Report',
};

const Index: React.FC = () => {
  const [activeModule, setActiveModule] = useState<ModuleId>('fleet-command');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/auth');
    }
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated) return null;

  const renderModule = () => {
    switch (activeModule) {
      case 'fleet-command': return <FleetCommandCenter />;
      case 'drilling-performance': return <DrillingPerformance />;
      case 'npt-intelligence': return <NPTIntelligence />;
      case 'mud-engineering': return <MudEngineering />;
      case 'safety-hse': return <SafetyHSE />;
      case 'personnel': return <PersonnelModule />;
      case 'six-sigma': return <PlaceholderModule title="Six Sigma / SPC" description="Statistical process control charts, control limits, and capability analysis across the fleet. Requires GET /fleet/spc endpoint." />;
      case 'survey-wells': return <PlaceholderModule title="Survey & Wells" description="Directional survey data, well trajectory visualization, and formation tops. Requires GET /rigs/:rig_id/survey." />;
      case 'ai-qa': return <PlaceholderModule title="AI Q&A (RAG)" description="Natural language queries against the DDR corpus with source-cited answers. Requires POST /search." />;
      case 'audit-trail': return <PlaceholderModule title="Audit Trail" description="Full PDF provenance audit with extraction confidence and page-level verification. Requires GET /audit." />;
      case 'report-viewer': return <PlaceholderModule title="Report Viewer" description="Browse original PDF pages with highlighted extraction regions. Requires report data." />;
      default: return <PlaceholderModule title={MODULE_TITLES[activeModule] || 'Module'} description="This module requires backend API connection. No data available." />;
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/auth');
  };

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <TopBar
        onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
        userName={user?.name}
        onLogout={handleLogout}
      />
      <div className="flex flex-1 overflow-hidden">
        <DDRSidebar
          activeModule={activeModule}
          onModuleChange={setActiveModule}
          collapsed={sidebarCollapsed}
          onCollapse={setSidebarCollapsed}
        />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto p-6">
            {/* Module Header */}
            <div className="mb-6">
              <h2 className="text-xl font-bold text-foreground">{MODULE_TITLES[activeModule]}</h2>
              <div className="h-0.5 w-16 bg-primary mt-1 rounded" />
            </div>
            {renderModule()}
          </div>
          {/* Classification Footer */}
          <div className="text-center py-4 text-[10px] text-muted-foreground border-t border-border mt-8">
            SAUDI ARAMCO: CONFIDENTIAL — OPERLMTDMRREP — DDR Intelligence Platform v3.0
          </div>
        </main>
      </div>
    </div>
  );
};

export default Index;
