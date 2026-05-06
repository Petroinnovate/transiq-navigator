// ============================================================================
// Multi-Tenant Branding Configuration
// ============================================================================

import type { Tenant, TenantConfig } from '@/types/ddr.types';

export const TENANT_CONFIGS: Record<Tenant, TenantConfig> = {
  aramco: {
    name: 'Saudi Aramco',
    primaryColor: '#00A651',
    logoPath: '/logos/aramco.svg',
    reportFormat: 'OPERLMTDMRREP',
    classificationLabel: 'Saudi Aramco: Confidential',
    dateFormat: 'MM/dd/yyyy',
    depthUnit: 'ft',
    pressureUnit: 'psi',
  },
  adnoc: {
    name: 'ADNOC',
    primaryColor: '#0066B3',
    logoPath: '/logos/adnoc.svg',
    reportFormat: 'ADNOC-DDR',
    classificationLabel: 'ADNOC: Restricted',
    dateFormat: 'dd/MM/yyyy',
    depthUnit: 'm',
    pressureUnit: 'bar',
  },
  ongc: {
    name: 'ONGC',
    primaryColor: '#CC0000',
    logoPath: '/logos/ongc.svg',
    reportFormat: 'ONGC-DDR',
    classificationLabel: 'ONGC: Confidential',
    dateFormat: 'dd/MM/yyyy',
    depthUnit: 'm',
    pressureUnit: 'bar',
  },
  bp: {
    name: 'BP',
    primaryColor: '#009B4E',
    logoPath: '/logos/bp.svg',
    reportFormat: 'BP-DDR',
    classificationLabel: 'BP: Internal',
    dateFormat: 'dd/MM/yyyy',
    depthUnit: 'm',
    pressureUnit: 'bar',
  },
  shell: {
    name: 'Shell',
    primaryColor: '#FBB731',
    logoPath: '/logos/shell.svg',
    reportFormat: 'SHELL-DDR',
    classificationLabel: 'Shell: Confidential',
    dateFormat: 'dd/MM/yyyy',
    depthUnit: 'm',
    pressureUnit: 'bar',
  },
  total: {
    name: 'TotalEnergies',
    primaryColor: '#E2231A',
    logoPath: '/logos/total.svg',
    reportFormat: 'TOTAL-DDR',
    classificationLabel: 'TotalEnergies: Internal',
    dateFormat: 'dd/MM/yyyy',
    depthUnit: 'm',
    pressureUnit: 'bar',
  },
  chevron: {
    name: 'Chevron',
    primaryColor: '#004A97',
    logoPath: '/logos/chevron.svg',
    reportFormat: 'CHEVRON-DDR',
    classificationLabel: 'Chevron: Proprietary',
    dateFormat: 'MM/dd/yyyy',
    depthUnit: 'ft',
    pressureUnit: 'psi',
  },
};

export const DEFAULT_TENANT: Tenant = 'aramco';

export const getTenantConfig = (tenant?: Tenant): TenantConfig => {
  return TENANT_CONFIGS[tenant || DEFAULT_TENANT];
};
