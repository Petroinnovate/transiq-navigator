import React, { useState } from 'react';
import { Presentation, FileText, ShieldAlert, Zap, TrendingUp, ChevronRight, Download } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Slides {
  summary?: string[];
  decisions?: string[];
  risks?: string[];
  actions?: string[];
  kpi_impact?: string[];
}

interface BoardroomData {
  executive_summary?: string;
  slides?: Slides;
}

interface BoardroomModeProps {
  data: BoardroomData;
  reportTitle?: string;
}

const SLIDE_CONFIG = [
  { key: 'summary',   label: 'Executive Summary',  icon: FileText,    color: 'text-cyan-400',    ring: 'ring-cyan-500/30',    bg: 'from-cyan-950/60',   num: '01' },
  { key: 'decisions', label: 'Key Decisions',       icon: TrendingUp,  color: 'text-violet-400',  ring: 'ring-violet-500/30',  bg: 'from-violet-950/60', num: '02' },
  { key: 'risks',     label: 'Risk Register',       icon: ShieldAlert, color: 'text-red-400',     ring: 'ring-red-500/30',     bg: 'from-red-950/60',    num: '03' },
  { key: 'actions',   label: 'Action Plan',         icon: Zap,         color: 'text-amber-400',   ring: 'ring-amber-500/30',   bg: 'from-amber-950/60',  num: '04' },
  { key: 'kpi_impact',label: 'KPI Impact',          icon: TrendingUp,  color: 'text-emerald-400', ring: 'ring-emerald-500/30', bg: 'from-emerald-950/60',num: '05' },
] as const;

const BoardroomMode: React.FC<BoardroomModeProps> = ({ data, reportTitle }) => {
  const [activeSlide, setActiveSlide] = useState<string>('summary');
  const slides = data?.slides || {};
  const summary = data?.executive_summary || '';

  const handleExport = () => {
    // Build a plain-text PowerPoint-ready export
    const lines: string[] = [
      `TRANSIQ — BOARDROOM REPORT`,
      `${reportTitle || 'Executive Report'}`,
      '',
      '─'.repeat(60),
      'SLIDE 1: EXECUTIVE SUMMARY',
      '─'.repeat(60),
      summary,
      '',
    ];
    SLIDE_CONFIG.slice(1).forEach(({ key, label, num }) => {
      const items: string[] = (slides as any)[key] || [];
      lines.push('─'.repeat(60));
      lines.push(`SLIDE ${num}: ${label.toUpperCase()}`);
      lines.push('─'.repeat(60));
      items.forEach(b => lines.push(`• ${b}`));
      lines.push('');
    });

    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'TransIQ_Boardroom_Export.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">

      {/* ── Header bar ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-violet-500/15 border border-violet-500/30 flex items-center justify-center">
            <Presentation className="h-4 w-4 text-violet-400" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Boardroom Mode</h3>
            <p className="text-xs text-slate-500">Slide-ready executive narrative</p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleExport}
          className="text-slate-300 hover:text-white border border-slate-700/60 hover:bg-slate-700/60 h-8 text-xs"
        >
          <Download className="h-3.5 w-3.5 mr-1.5" />
          Export for PowerPoint
        </Button>
      </div>

      {/* ── Executive Summary (always visible) ────────────────────── */}
      {summary && (
        <div className="rounded-xl border border-cyan-500/20 bg-gradient-to-br from-cyan-950/40 to-slate-800/60 p-5">
          <p className="text-xs font-bold text-cyan-400/70 uppercase tracking-widest mb-3">Executive Summary</p>
          <p className="text-sm text-slate-200 leading-relaxed">{summary}</p>
        </div>
      )}

      {/* ── Slide navigation ──────────────────────────────────────── */}
      <div className="flex gap-2 flex-wrap">
        {SLIDE_CONFIG.map(({ key, label, num }) => (
          <button
            key={key}
            onClick={() => setActiveSlide(key)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-all font-medium
              ${activeSlide === key
                ? 'bg-white/10 border-white/20 text-white'
                : 'border-slate-700/60 text-slate-500 hover:text-slate-300 hover:border-slate-600'}`}
          >
            {num} · {label}
          </button>
        ))}
      </div>

      {/* ── Active slide ──────────────────────────────────────────── */}
      {SLIDE_CONFIG.map(({ key, label, icon: Icon, color, ring, bg, num }) => {
        if (activeSlide !== key) return null;
        const bullets: string[] = (slides as any)[key] || [];
        return (
          <div
            key={key}
            className={`rounded-2xl border border-slate-700/60 ring-1 ${ring} bg-gradient-to-br ${bg} to-slate-900/80 overflow-hidden`}
          >
            {/* Slide header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/40">
              <div className="flex items-center gap-3">
                <span className={`text-4xl font-black ${color} opacity-20 leading-none select-none`}>{num}</span>
                <div>
                  <p className={`text-xs font-bold uppercase tracking-widest ${color}`}>{label}</p>
                  <p className="text-xs text-slate-500 mt-0.5">TransIQ Decision Intelligence</p>
                </div>
              </div>
              <Icon className={`h-6 w-6 ${color} opacity-40`} />
            </div>

            {/* Slide body */}
            <div className="px-6 py-5">
              {bullets.length > 0 ? (
                <ul className="space-y-3">
                  {bullets.map((bullet, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <ChevronRight className={`h-4 w-4 mt-0.5 flex-shrink-0 ${color}`} />
                      <p className="text-sm text-slate-200 leading-relaxed">{bullet}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-600 italic">No content for this slide.</p>
              )}
            </div>

            {/* Slide footer */}
            <div className="px-6 py-3 border-t border-slate-700/30 flex items-center justify-between">
              <span className="text-xs text-slate-600">TransIQ · AI Decision OS</span>
              <span className={`text-xs ${color} opacity-60`}>Slide {num} of {SLIDE_CONFIG.length}</span>
            </div>
          </div>
        );
      })}

    </div>
  );
};

export default BoardroomMode;
