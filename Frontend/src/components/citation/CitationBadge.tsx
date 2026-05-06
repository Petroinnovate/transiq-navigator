// ============================================================================
// CitationBadge — Core DDR Authentication Layer
// Every KPI, chart point, and table cell wraps its value with this component.
// Provides full PDF provenance popover with rig identity and data quality.
// ============================================================================

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import type { KPIValue, RigIdentity } from '@/types/ddr.types';
import { DDR_TOKENS } from '@/styles/tokens';

interface CitationBadgeProps {
  kpiValue: KPIValue;
  identity: RigIdentity;
  serviceProviders?: string[];
  equipment?: string;
  compact?: boolean;
  children?: React.ReactNode;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({
  kpiValue, identity, serviceProviders, equipment, compact = false, children,
}) => {
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  const confLevel = kpiValue.confidence >= 0.95 ? 'high'
                  : kpiValue.confidence >= 0.80 ? 'medium' : 'low';

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node) &&
          btnRef.current && !btnRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Return focus to button on close
  const handleClose = useCallback(() => {
    setOpen(false);
    btnRef.current?.focus();
  }, []);

  return (
    <span className="inline-flex items-center gap-1">
      {children}

      {/* Derived value indicator */}
      {kpiValue.is_derived && (
        <span
          title={`Derived: ${kpiValue.formula || 'computed value'}`}
          className="text-[10px] cursor-help"
          style={{ color: DDR_TOKENS.status.derived }}
        >
          ⚡
        </span>
      )}

      {/* Under review indicator */}
      {kpiValue.under_review && (
        <span
          title="This value is under manual review"
          className="text-[10px]"
          style={{ color: DDR_TOKENS.status.warning }}
        >
          🔍
        </span>
      )}

      {/* Confidence dot */}
      <span
        className="inline-block w-1.5 h-1.5 rounded-full"
        title={`Confidence: ${(kpiValue.confidence * 100).toFixed(0)}%`}
        style={{
          background: confLevel === 'high' ? DDR_TOKENS.status.excellent
                    : confLevel === 'medium' ? DDR_TOKENS.status.warning
                    : DDR_TOKENS.status.critical,
          boxShadow: confLevel === 'high' ? `0 0 4px ${DDR_TOKENS.status.excellent}` : 'none',
        }}
      />

      {/* Citation trigger button */}
      <button
        ref={btnRef}
        onClick={() => setOpen(!open)}
        aria-label={`Source citation: ${kpiValue.source_citation}`}
        aria-expanded={open}
        aria-haspopup="dialog"
        className="inline-flex items-center gap-1 transition-all duration-150 hover:opacity-80"
        style={{
          background: DDR_TOKENS.citation.badge,
          border: `1px solid ${DDR_TOKENS.citation.badgeBorder}`,
          borderRadius: 4,
          padding: compact ? '1px 4px' : '1px 6px',
          cursor: 'pointer',
          fontSize: 10,
          color: DDR_TOKENS.citation.badgeText,
          fontFamily: DDR_TOKENS.font.mono,
          boxShadow: DDR_TOKENS.shadow.citation,
        }}
      >
        📋
        {!compact && kpiValue.source_citation && (
          <span className="max-w-[200px] overflow-hidden text-ellipsis whitespace-nowrap">
            [{kpiValue.source_citation.split('–').slice(0, 2).join('–').trim()}]
          </span>
        )}
      </button>

      {/* Popover (portal, outside parent stacking context) */}
      {open && createPortal(
        <div className="fixed inset-0 z-[9998]" onClick={handleClose}>
          <div
            ref={popoverRef}
            role="dialog"
            aria-modal="true"
            aria-label={`Source citation for ${kpiValue.source_field}`}
            onClick={(e) => e.stopPropagation()}
            className="overflow-y-auto"
            style={{
              position: 'fixed',
              top: Math.min(
                (btnRef.current?.getBoundingClientRect().bottom ?? 0) + 8,
                window.innerHeight - 500
              ),
              left: Math.min(
                btnRef.current?.getBoundingClientRect().left ?? 0,
                window.innerWidth - 440
              ),
              width: 420,
              maxHeight: '80vh',
              background: DDR_TOKENS.citation.popoverBg,
              border: `1px solid ${DDR_TOKENS.citation.popoverBorder}`,
              borderRadius: 12,
              padding: 20,
              zIndex: 9999,
              boxShadow: '0 8px 40px rgba(0,0,0,0.6)',
              fontSize: 13,
              color: DDR_TOKENS.text.primary,
            }}
          >
            {/* Close button */}
            <button
              onClick={handleClose}
              className="absolute top-3 right-3 bg-transparent border-none cursor-pointer text-base"
              style={{ color: DDR_TOKENS.text.muted }}
              aria-label="Close citation popover"
            >
              ✕
            </button>

            {/* Section 1: Source Reference */}
            <PopoverSection title="📍 Source Reference">
              <code
                className="block rounded-md p-2 text-xs break-all"
                style={{
                  background: DDR_TOKENS.bg.primary,
                  border: `1px solid ${DDR_TOKENS.citation.badgeBorder}`,
                  color: DDR_TOKENS.citation.badgeText,
                }}
              >
                {kpiValue.source_citation}
              </code>
              {kpiValue.source_snippet && (
                <div className="mt-2 text-[11px]" style={{ color: DDR_TOKENS.text.muted }}>
                  <strong>Raw text from PDF:</strong><br />
                  <code style={{ color: DDR_TOKENS.text.secondary }}>
                    &ldquo;{kpiValue.source_snippet}&rdquo;
                  </code>
                </div>
              )}
            </PopoverSection>

            {/* Section 2: Rig Identity */}
            <PopoverSection title="🏗️ Rig Identity">
              <IdentityTable rows={[
                ['Rig Number', identity.rig_id],
                ['Well ID', identity.well_id],
                ['Report Date', identity.report_date],
                ['Shift Period', identity.shift_period],
                ['Drillsite', identity.location],
                ['Objective', identity.objective],
                ['Programme', identity.programme_name],
                ['Prog. Dates', identity.programme_dates],
                ['Charge #', identity.charge_number],
              ]} />
            </PopoverSection>

            {/* Section 3: Operations Team */}
            <PopoverSection title="👥 Operations Team">
              <IdentityTable rows={[
                ['Foreman(s)', identity.foremen],
                ['Engineer', identity.engineer],
                ['Manager', identity.manager],
                ['THURAYA', identity.thuraya],
              ]} />
            </PopoverSection>

            {/* Section 4: PDF Source Details */}
            <PopoverSection title="📄 PDF Source Details">
              <IdentityTable rows={[
                ['Source Page', `Page ${kpiValue.source_page} of 3`],
                ['Section', kpiValue.source_section],
                ['Field Name', `"${kpiValue.source_field}"`],
                ['Method', kpiValue.extraction_method],
                ['Page SHA-256', kpiValue.page_hash.slice(0, 20) + '...'],
              ]} />
            </PopoverSection>

            {/* Section 5: Data Quality */}
            <PopoverSection title="📊 Data Quality">
              <QualityBar label="Confidence" value={kpiValue.confidence} />
              {kpiValue.is_derived && (
                <div
                  className="mt-2 p-2 rounded-md text-xs"
                  style={{
                    background: 'rgba(245,166,35,0.1)',
                    border: '1px solid rgba(245,166,35,0.3)',
                  }}
                >
                  <strong style={{ color: DDR_TOKENS.status.derived }}>⚡ Derived Value</strong>
                  <br />
                  <code style={{ color: DDR_TOKENS.text.secondary }}>{kpiValue.formula}</code>
                </div>
              )}
              {kpiValue.imputed && (
                <div
                  className="mt-2 p-2 rounded-md text-xs"
                  style={{ background: 'rgba(255,169,64,0.1)' }}
                >
                  <strong style={{ color: DDR_TOKENS.status.warning }}>⚠️ Imputed</strong>
                  {' — value estimated from available data'}
                </div>
              )}
              {kpiValue.under_review && (
                <div
                  className="mt-2 p-2 rounded-md text-xs"
                  style={{ background: 'rgba(255,77,79,0.1)' }}
                >
                  <strong style={{ color: DDR_TOKENS.status.critical }}>🔍 Under Review</strong>
                  {' — manual verification in progress'}
                </div>
              )}
            </PopoverSection>

            {/* Section 6: Service Providers */}
            {serviceProviders && serviceProviders.length > 0 && (
              <PopoverSection title="🔧 Service Providers">
                <ul className="m-0 pl-4 text-xs" style={{ color: DDR_TOKENS.text.secondary }}>
                  {serviceProviders.map(sp => <li key={sp}>{sp}</li>)}
                </ul>
              </PopoverSection>
            )}

            {/* Section 7: Equipment */}
            {equipment && (
              <PopoverSection title="⚙️ Equipment / Tool">
                <span className="text-xs" style={{ color: DDR_TOKENS.text.secondary }}>
                  {equipment}
                </span>
              </PopoverSection>
            )}

            {/* Classification footer */}
            <div
              className="mt-4 pt-3 text-center text-[10px]"
              style={{
                borderTop: `1px solid ${DDR_TOKENS.surface.border}`,
                color: DDR_TOKENS.text.muted,
              }}
            >
              {identity.classification}
            </div>
          </div>
        </div>,
        document.body
      )}
    </span>
  );
};

// ── Sub-components ──────────────────────────────────────────────────────────

const PopoverSection: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="mb-4">
    <div
      className="text-[11px] font-semibold uppercase tracking-wider mb-2"
      style={{ color: DDR_TOKENS.text.muted }}
    >
      {title}
    </div>
    {children}
  </div>
);

const IdentityTable: React.FC<{ rows: [string, string][] }> = ({ rows }) => (
  <table className="w-full border-collapse text-xs">
    <tbody>
      {rows.map(([label, value]) => (
        <tr key={label}>
          <td
            className="py-1 pr-2 whitespace-nowrap align-top"
            style={{ color: DDR_TOKENS.text.muted, width: '40%' }}
          >
            {label}
          </td>
          <td
            className="py-1 font-medium"
            style={{ color: DDR_TOKENS.text.primary }}
          >
            {value}
          </td>
        </tr>
      ))}
    </tbody>
  </table>
);

const QualityBar: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div className="flex items-center gap-2 mb-1.5">
    <span className="text-[11px] w-20" style={{ color: DDR_TOKENS.text.muted }}>{label}</span>
    <div
      className="flex-1 h-1.5 rounded-full overflow-hidden"
      style={{ background: DDR_TOKENS.surface.s1 }}
    >
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{
          width: `${value * 100}%`,
          background: value >= 0.95 ? DDR_TOKENS.status.excellent
                    : value >= 0.80 ? DDR_TOKENS.status.warning
                    : DDR_TOKENS.status.critical,
        }}
      />
    </div>
    <span className="text-[11px] w-9 text-right" style={{ color: DDR_TOKENS.text.secondary }}>
      {(value * 100).toFixed(0)}%
    </span>
  </div>
);

export default CitationBadge;
