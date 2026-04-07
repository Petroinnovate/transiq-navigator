"""
Widget Mapper
=============

Takes the enriched + sorted KPI pool and returns a widget-assignment dict
so the frontend knows exactly which KPIs belong in each visualization widget.

Output schema (generic BI):
  kpi_summary, kpi_bar, kpi_status, kpi_cat, alerts

Output schema (DDR drilling):
  fleet_heatmap, npt_pareto, spc_chart, gantt_timeline, depth_sparkline,
  plus all generic widgets above.

Key principle: hidden KPIs still contribute to charts/distributions —
they just don't appear as individual cards.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# DDR keyword matchers for widget routing
# ---------------------------------------------------------------------------
_NPT_RE   = re.compile(r"\b(npt|non.?productive|wait|standby|breakdown|repair)\b", re.I)
_SPC_RE   = re.compile(r"\b(mud.?weight|rop|wob|rpm|torque|pressure|flow.?rate|ppg|ft/hr|psi|gpm)\b", re.I)
_DEPTH_RE = re.compile(r"\b(depth|footage|hole.?depth|tvd|md)\b", re.I)
_HSE_RE   = re.compile(r"\b(incident|near.?miss|safety|hse|hazard|spill|trir|ltir)\b", re.I)
_RIG_RE   = re.compile(r"\b(rig|well|contractor|field)\b", re.I)


def map_kpis_to_widgets(kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    kpis — already sorted by priorityScore descending, with visibility attached
           (output of kpi_engine.process_kpis).
    """
    primary   = [k for k in kpis if k.get("visibility") == "primary"]
    secondary = [k for k in kpis if k.get("visibility") == "secondary"]

    # ── KPI Summary cards — top 6 primary ─────────────────────────────────
    kpi_summary = primary[:6]

    # ── Bar chart — numeric-comparable KPIs (primary + secondary), top 10 ─
    kpi_bar = [
        k for k in kpis
        if isinstance(k.get("value"), (int, float))
        and k.get("visibility") in ("primary", "secondary")
    ][:10]

    # ── Status distribution — ALL KPIs (hidden ones still count here) ──────
    status_counts: Dict[str, int] = {
        "good": 0, "warning": 0, "critical": 0, "unknown": 0
    }
    for k in kpis:
        stat = (k.get("status") or "").lower()
        ct   = (k.get("changeType") or "").lower()
        if stat in status_counts:
            status_counts[stat] += 1
        elif ct == "positive":
            status_counts["good"] += 1
        elif ct == "negative":
            status_counts["warning"] += 1
        else:
            status_counts["unknown"] += 1

    kpi_status = {k: v for k, v in status_counts.items() if v > 0}

    # ── Category distribution — ALL KPIs ──────────────────────────────────
    cat_counts: Dict[str, int] = {}
    for k in kpis:
        cat = (k.get("category") or "Other").capitalize()
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # ── Alerts — KPIs with priorityScore ≥ 85 (top 5) ────────────────────
    alerts = [k for k in kpis if k.get("priorityScore", 0) >= 85][:5]

    # ── DDR-specific widgets ──────────────────────────────────────────────
    ddr_widgets = _map_ddr_widgets(kpis)

    result = {
        "kpi_summary": kpi_summary,
        "kpi_bar":     kpi_bar,
        "kpi_status":  kpi_status,
        "kpi_cat":     cat_counts,
        "alerts":      alerts,
        # Metadata for the frontend filter toggle
        "pool_size":   len(kpis),
        "primary_count":   len(primary),
        "secondary_count": len(secondary),
        "hidden_count":    len([k for k in kpis if k.get("visibility") == "hidden"]),
    }
    result.update(ddr_widgets)
    return result


# ---------------------------------------------------------------------------
# DDR-specific widget mapping
# ---------------------------------------------------------------------------

def _map_ddr_widgets(kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Route DDR-specific KPIs to drilling visualization widgets.
    Returns empty collections when no DDR data is present (no-op for generic BI).
    """
    # Classify KPIs by DDR widget type
    npt_kpis:   List[Dict[str, Any]] = []
    spc_kpis:   List[Dict[str, Any]] = []
    depth_kpis: List[Dict[str, Any]] = []
    hse_kpis:   List[Dict[str, Any]] = []
    rig_kpis:   List[Dict[str, Any]] = []

    for k in kpis:
        title = k.get("title", "")
        cat = (k.get("category") or "").lower()

        if _NPT_RE.search(title) or cat == "npt":
            npt_kpis.append(k)
        if _SPC_RE.search(title) or cat in ("drilling", "mud", "spc"):
            spc_kpis.append(k)
        if _DEPTH_RE.search(title) or cat == "depth":
            depth_kpis.append(k)
        if _HSE_RE.search(title) or cat in ("safety", "hse"):
            hse_kpis.append(k)
        if _RIG_RE.search(title) or cat in ("fleet", "rig"):
            rig_kpis.append(k)

    # ── Fleet Heatmap — rig-level KPIs for heat-map matrix ────────────────
    fleet_heatmap = _build_fleet_heatmap(rig_kpis)

    # ── NPT Pareto — top NPT causes sorted by impact ─────────────────────
    npt_pareto = sorted(npt_kpis, key=lambda k: abs(float(k.get("value") or 0)), reverse=True)[:10]

    # ── SPC Control Chart — numeric KPIs suitable for X-bar/R charts ──────
    spc_chart = [
        {
            "title": k.get("title"),
            "value": k.get("value"),
            "unit": k.get("unit", ""),
            "target": k.get("target"),
            "status": k.get("status"),
            "ucl": float(k.get("target") or 0) * 1.1 if k.get("target") else None,
            "lcl": float(k.get("target") or 0) * 0.9 if k.get("target") else None,
        }
        for k in spc_kpis
        if isinstance(k.get("value"), (int, float))
    ][:8]

    # ── Gantt Timeline — depth/time KPIs for drill-progress Gantt ─────────
    gantt_timeline = [
        {
            "title": k.get("title"),
            "value": k.get("value"),
            "unit": k.get("unit", ""),
            "category": k.get("category", ""),
        }
        for k in depth_kpis
    ][:12]

    # ── Depth Sparkline — compact depth progression data ──────────────────
    depth_sparkline = [
        float(k.get("value") or 0)
        for k in depth_kpis
        if isinstance(k.get("value"), (int, float))
    ]

    # ── HSE Scorecard — safety incidents aggregated ───────────────────────
    hse_scorecard = {
        "total_kpis": len(hse_kpis),
        "critical": len([k for k in hse_kpis if (k.get("status") or "").lower() == "critical"]),
        "items": hse_kpis[:5],
    }

    return {
        "fleet_heatmap":   fleet_heatmap,
        "npt_pareto":      npt_pareto,
        "spc_chart":       spc_chart,
        "gantt_timeline":  gantt_timeline,
        "depth_sparkline": depth_sparkline,
        "hse_scorecard":   hse_scorecard,
    }


def _build_fleet_heatmap(rig_kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a heatmap matrix: rows = rigs, columns = metric names, cells = status color.
    """
    rigs: Dict[str, Dict[str, str]] = {}
    for k in rig_kpis:
        rig = k.get("rig_id") or k.get("rig") or "all"
        metric = k.get("title", "unknown")
        status = (k.get("status") or "unknown").lower()
        if rig not in rigs:
            rigs[rig] = {}
        rigs[rig][metric] = status

    return {
        "rigs": rigs,
        "rig_count": len(rigs),
    }
