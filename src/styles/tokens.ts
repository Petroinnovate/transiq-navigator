// ============================================================================
// DDR Intelligence Platform — Design Tokens
// Extends the existing TransIQ design system for DDR (Daily Drilling Report)
// ============================================================================

export const DDR_TOKENS = {
  // ── Brand ─────────────────────────────────────────────────────
  brand: {
    aramcoGreen:    '#00A651',
    aramcoDark:     '#003366',
    adnocBlue:      '#0066B3',
    shellYellow:    '#FBB731',
    bpGreen:        '#009B4E',
    totalRed:       '#E2231A',
    ongcRed:        '#CC0000',
  },

  // ── Backgrounds ───────────────────────────────────────────────
  bg: {
    primary:        '#0A0E1A',
    secondary:      '#0F1629',
    tertiary:       '#141E35',
    glass:          'rgba(15,22,41,0.85)',
    overlay:        'rgba(10,14,26,0.95)',
  },

  // ── Surfaces ──────────────────────────────────────────────────
  surface: {
    s1:             '#1A2540',
    s2:             '#1F2D4A',
    border:         '#2A3A5C',
    hover:          '#243050',
    active:         '#2D3D65',
    glow:           'rgba(0,166,81,0.08)',
  },

  // ── Text ──────────────────────────────────────────────────────
  text: {
    primary:        '#FFFFFF',
    secondary:      '#A0AABE',
    muted:          '#5A6B8A',
    emphasis:       '#E8F4FD',
    link:           '#40B4FF',
    citation:       '#4BC6FF',
    onDark:         '#FFFFFF',
  },

  // ── Status (colorblind-safe) ──────────────────────────────────
  status: {
    excellent:      '#00D084',
    normal:         '#40B4FF',
    warning:        '#FFA940',
    critical:       '#FF4D4F',
    standby:        '#8C8C8C',
    drilling:       '#52C41A',
    completion:     '#9254DE',
    derived:        '#F5A623',
  },

  // ── KPI Status ring colors ────────────────────────────────────
  kpiRing: {
    excellent:      'rgba(0,208,132,0.3)',
    normal:         'rgba(64,180,255,0.3)',
    warning:        'rgba(255,169,64,0.3)',
    critical:       'rgba(255,77,79,0.3)',
  },

  // ── Charts (categorical, colorblind-safe) ─────────────────────
  chart: {
    c1: '#00A651', c2: '#1890FF', c3: '#FFA940', c4: '#9254DE',
    c5: '#00BCD4', c6: '#FF7A45', c7: '#52C41A', c8: '#EB2F96',
  },

  // ── Heatmap (fleet status gradient) ──────────────────────────
  heatmap: {
    cold:  '#003A70',
    cool:  '#006BB8',
    mid:   '#00A651',
    warm:  '#FFA940',
    hot:   '#FF4D4F',
  },

  // ── Citation ──────────────────────────────────────────────────
  citation: {
    badge:          '#1A2D4A',
    badgeBorder:    '#4BC6FF',
    badgeText:      '#4BC6FF',
    popoverBg:      '#0F1629',
    popoverBorder:  '#2A3A5C',
    highConf:       '#00D084',
    medConf:        '#FFA940',
    lowConf:        '#FF4D4F',
  },

  // ── Typography ────────────────────────────────────────────────
  font: {
    display:  '"Inter", "SF Pro Display", -apple-system, sans-serif',
    mono:     '"JetBrains Mono", "Fira Code", "Consolas", monospace',
    data:     '"Roboto Mono", monospace',
  },

  // ── Shadows ───────────────────────────────────────────────────
  shadow: {
    card:           '0 4px 24px rgba(0,0,0,0.4)',
    cardHover:      '0 8px 40px rgba(0,0,0,0.6)',
    glowGreen:      '0 0 20px rgba(0,166,81,0.3)',
    glowRed:        '0 0 20px rgba(255,77,79,0.3)',
    glowAmber:      '0 0 20px rgba(255,169,64,0.3)',
    glowBlue:       '0 0 20px rgba(24,144,255,0.3)',
    citation:       '0 0 12px rgba(75,198,255,0.2)',
  },
} as const;

export type DDRTokens = typeof DDR_TOKENS;
