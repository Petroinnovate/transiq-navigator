// ============================================================================
// DDR Dashboard — Master orchestrator for DDR Intelligence Platform
// Renders inside the existing /dashboard route when DDR mode is active
// ============================================================================

import React, { Suspense, useState, lazy } from 'react';
import { useDDR } from '@/contexts/DDRContext';
import DDRSidebar from './DDRSidebar';
import DDRTopBar from './DDRTopBar';
import ReportDateSelector from './ReportDateSelector';
import { DDR_TOKENS } from '@/styles/tokens';

// Lazy load modules for code splitting
const FleetCommandCenter = lazy(() => import('./FleetCommandCenter'));
const DrillingPerformance = lazy(() => import('./DrillingPerformance'));
const NPTIntelligence = lazy(() => import('./NPTIntelligence'));
const MudEngineering = lazy(() => import('./MudEngineering'));
const SafetyHSE = lazy(() => import('./SafetyHSE'));
const PersonnelLogistics = lazy(() => import('./PersonnelLogistics'));
const SurveyWellbore = lazy(() => import('./SurveyWellbore'));
const SixSigmaSPC = lazy(() => import('./SixSigmaSPC'));
const AIAssistant = lazy(() => import('./AIAssistant'));
const AuditTrail = lazy(() => import('./AuditTrail'));
const ReportViewer = lazy(() => import('./ReportViewer'));

// TODO: Replace ModuleSkeleton with <LoadingState /> from @/components/ddr/state
const ModuleSkeleton = () => (
  <div className="space-y-4">
    <div className="h-16 rounded-xl animate-pulse bg-slate-800/60" />
    <div className="grid grid-cols-3 gap-4">
      <div className="h-32 rounded-xl animate-pulse bg-slate-800/60" />
      <div className="h-32 rounded-xl animate-pulse bg-slate-800/60" />
      <div className="h-32 rounded-xl animate-pulse bg-slate-800/60" />
    </div>
    <div className="h-64 rounded-xl animate-pulse bg-slate-800/60" />
  </div>
);

const DDRDashboard: React.FC = () => {
  const { activeModule, selectedRigId, setSelectedRigId, reportDate } = useDDR();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleRigSelect = (rigId: string) => {
    setSelectedRigId(rigId);
  };

  const renderModule = () => {
    switch (activeModule) {
      case 'fleet-command':
        return <FleetCommandCenter onRigSelect={handleRigSelect} />;
      case 'drilling-performance':
        return selectedRigId ? (
          <DrillingPerformance rigId={selectedRigId} />
        ) : (
          <RigSelector onSelect={handleRigSelect} />
        );
      case 'npt-intelligence':
        return <NPTIntelligence rigId={selectedRigId} />;
      case 'mud-engineering':
        return selectedRigId ? (
          <MudEngineering rigId={selectedRigId} />
        ) : (
          <RigSelector onSelect={handleRigSelect} />
        );
      case 'safety-hse':
        return selectedRigId ? (
          <SafetyHSE rigId={selectedRigId} />
        ) : (
          <RigSelector onSelect={handleRigSelect} />
        );
      case 'personnel-logistics':
        return selectedRigId ? (
          <PersonnelLogistics rigId={selectedRigId} />
        ) : (
          <RigSelector onSelect={handleRigSelect} />
        );
      case 'survey-wellbore':
        return selectedRigId ? (
          <SurveyWellbore rigId={selectedRigId} />
        ) : (
          <RigSelector onSelect={handleRigSelect} />
        );
      case 'six-sigma-spc':
        return <SixSigmaSPC />;
      case 'ai-qa':
        return <AIAssistant />;
      case 'audit-trail':
        return <AuditTrail />;
      case 'report-viewer':
        return <ReportViewer />;
      default:
        return <FleetCommandCenter onRigSelect={handleRigSelect} />;
    }
  };

  return (
    <div className="flex h-screen" style={{ background: DDR_TOKENS.bg.primary, color: DDR_TOKENS.text.primary }}>
      {/* Sidebar */}
      <DDRSidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Glass TopBar */}
        <DDRTopBar
          selectedRigId={selectedRigId}
          onClearRig={() => setSelectedRigId(null)}
        />

        {/* Scrollable main content */}
        <main className="flex-1 overflow-y-auto p-6" id="main-content">
          {!reportDate ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-6xl mb-4">🛢️</div>
                <h2 className="text-xl font-bold text-white mb-2">DDR Intelligence Platform</h2>
                <p className="text-sm text-slate-400 mb-4">Select a report date to begin, or upload a new DDR report</p>
                <ReportDateSelector />
              </div>
            </div>
          ) : (
            <Suspense fallback={<ModuleSkeleton />}>
              {renderModule()}
            </Suspense>
          )}
        </main>
      </div>
    </div>
  );
};

// Rig selector prompt - shown when a module needs a rig but none is selected
const RigSelector: React.FC<{ onSelect: (rigId: string) => void }> = ({ onSelect }) => {
  const [search, setSearch] = useState('');

  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <div className="text-4xl mb-3">⛏️</div>
        <h3 className="text-lg font-bold text-white mb-2">Select a Rig</h3>
        <p className="text-sm text-slate-400 mb-4">Choose a rig from the Fleet Command heatmap, or type a rig ID:</p>
        <div className="flex items-center gap-2 justify-center">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="e.g. 088TE"
            className="px-3 py-2 rounded-md bg-slate-800 border border-slate-700 text-white text-sm w-40 focus:border-cyan-500 focus:outline-none"
            aria-label="Rig ID search"
          />
          <button
            onClick={() => search.trim() && onSelect(search.trim())}
            className="px-4 py-2 rounded-md text-sm font-medium transition-colors"
            style={{ background: DDR_TOKENS.brand.aramcoGreen, color: 'white' }}
            disabled={!search.trim()}
          >
            Go
          </button>
        </div>
      </div>
    </div>
  );
};

export default DDRDashboard;
