// ============================================================================
// DDR Data Provider — Global DDR state (report date, selected rig, mode)
// Wraps the app to provide DDR context to all components
// ============================================================================

import React, { createContext, useContext, useState, useCallback } from 'react';

export type DashboardMode = 'analytics' | 'drilling';

interface DDRState {
  /** Currently selected report date (YYYY-MM-DD) */
  reportDate: string;
  /** Currently selected rig ID (e.g., '088TE') */
  selectedRigId: string | null;
  /** Dashboard mode: analytics (generic BI) or drilling (DDR) */
  mode: DashboardMode;
  /** Whether DDR data is available for the current report */
  isDDRReport: boolean;
  /** Active DDR sidebar module */
  activeModule: string;
}

interface DDRContextValue extends DDRState {
  setReportDate: (date: string) => void;
  setSelectedRigId: (rigId: string | null) => void;
  setMode: (mode: DashboardMode) => void;
  setIsDDRReport: (isDDR: boolean) => void;
  setActiveModule: (module: string) => void;
  reset: () => void;
}

const initialState: DDRState = {
  reportDate: '',
  selectedRigId: null,
  mode: 'analytics',
  isDDRReport: false,
  activeModule: 'fleet-command',
};

const DDRContext = createContext<DDRContextValue | undefined>(undefined);

export const DDRDataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<DDRState>(initialState);

  const setReportDate = useCallback((date: string) => {
    setState(prev => ({ ...prev, reportDate: date }));
  }, []);

  const setSelectedRigId = useCallback((rigId: string | null) => {
    setState(prev => ({ ...prev, selectedRigId: rigId }));
  }, []);

  const setMode = useCallback((mode: DashboardMode) => {
    setState(prev => ({ ...prev, mode }));
  }, []);

  const setIsDDRReport = useCallback((isDDR: boolean) => {
    setState(prev => ({
      ...prev,
      isDDRReport: isDDR,
      mode: isDDR ? 'drilling' : 'analytics',
    }));
  }, []);

  const setActiveModule = useCallback((module: string) => {
    setState(prev => ({ ...prev, activeModule: module }));
  }, []);

  const reset = useCallback(() => {
    setState(initialState);
  }, []);

  return (
    <DDRContext.Provider value={{
      ...state,
      setReportDate,
      setSelectedRigId,
      setMode,
      setIsDDRReport,
      setActiveModule,
      reset,
    }}>
      {children}
    </DDRContext.Provider>
  );
};

export const useDDR = (): DDRContextValue => {
  const context = useContext(DDRContext);
  if (!context) {
    throw new Error('useDDR must be used within a DDRDataProvider');
  }
  return context;
};

export default DDRDataProvider;
