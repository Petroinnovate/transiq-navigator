"""
Multi-Report Trend Endpoints — Time-series comparison across DDR reports
=========================================================================

Provides:
  - Day-over-day deltas for key drilling metrics
  - Rolling window aggregations (7 / 14 / 30 day)
  - Multi-rig comparison time-series

All computations are deterministic (no LLM).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from services.db.session import get_db
from pipelines.inference.ddr.models import (
    DDRReport,
    DepthSummary,
    NPTEvent,
    MudData,
    HSEData,
    Timeline,
)

router = APIRouter(prefix="/api/ddr/trends", tags=["DDR Trends"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_date(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%Y-%m-%d") if dt else None


def _pct_change(prev: float, curr: float) -> Optional[float]:
    if prev == 0:
        return None
    return round((curr - prev) / abs(prev) * 100, 2)


def _rolling_avg(values: List[float], window: int) -> List[Optional[float]]:
    """Compute rolling average; returns None where window is incomplete."""
    result: List[Optional[float]] = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(None)
        else:
            subset = values[i - window + 1 : i + 1]
            result.append(round(sum(subset) / len(subset), 2) if subset else None)
    return result


# ---------------------------------------------------------------------------
# 1. Depth progress day-over-day
# ---------------------------------------------------------------------------

@router.get("/depth-progress")
async def depth_progress(
    rig_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """
    Day-over-day depth progress with deltas and rolling 7-day average.
    """
    since = datetime.utcnow() - timedelta(days=days)
    q = (
        db.query(
            DDRReport.report_date,
            DDRReport.rig_id,
            func.max(DepthSummary.hole_depth).label("depth"),
        )
        .join(DepthSummary, DepthSummary.report_id == DDRReport.id)
        .filter(DDRReport.report_date >= since)
    )
    if rig_id:
        q = q.filter(DDRReport.rig_id == rig_id)

    q = q.group_by(DDRReport.report_date, DDRReport.rig_id).order_by(DDRReport.report_date)
    rows = q.all()

    points: List[Dict[str, Any]] = []
    prev_depth: Optional[float] = None
    depths: List[float] = []

    for row in rows:
        depth = float(row.depth or 0)
        delta = round(depth - prev_depth, 2) if prev_depth is not None else None
        pct = _pct_change(prev_depth, depth) if prev_depth is not None else None
        depths.append(depth)
        points.append({
            "date": _to_date(row.report_date),
            "rig_id": row.rig_id,
            "depth_ft": depth,
            "daily_delta_ft": delta,
            "delta_pct": pct,
        })
        prev_depth = depth

    # Attach rolling averages
    roll7 = _rolling_avg(depths, 7)
    for i, p in enumerate(points):
        p["rolling_7d_avg"] = roll7[i]

    return {
        "metric": "depth_progress",
        "days": days,
        "rig_id": rig_id,
        "data": points,
    }


# ---------------------------------------------------------------------------
# 2. NPT trend
# ---------------------------------------------------------------------------

@router.get("/npt")
async def npt_trend(
    rig_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Daily NPT hours with day-over-day delta and rolling 7/14/30 day averages."""
    since = datetime.utcnow() - timedelta(days=days)
    q = (
        db.query(
            DDRReport.report_date,
            DDRReport.rig_id,
            func.sum(NPTEvent.duration_hours).label("npt_hours"),
            func.count(NPTEvent.id).label("event_count"),
        )
        .join(NPTEvent, NPTEvent.report_id == DDRReport.id)
        .filter(DDRReport.report_date >= since)
    )
    if rig_id:
        q = q.filter(DDRReport.rig_id == rig_id)

    q = q.group_by(DDRReport.report_date, DDRReport.rig_id).order_by(DDRReport.report_date)
    rows = q.all()

    points: List[Dict[str, Any]] = []
    prev_npt: Optional[float] = None
    npt_values: List[float] = []

    for row in rows:
        npt = float(row.npt_hours or 0)
        delta = round(npt - prev_npt, 2) if prev_npt is not None else None
        npt_values.append(npt)
        points.append({
            "date": _to_date(row.report_date),
            "rig_id": row.rig_id,
            "npt_hours": npt,
            "event_count": row.event_count,
            "daily_delta_hrs": delta,
        })
        prev_npt = npt

    # Rolling windows
    roll7 = _rolling_avg(npt_values, 7)
    roll14 = _rolling_avg(npt_values, 14)
    roll30 = _rolling_avg(npt_values, 30)
    for i, p in enumerate(points):
        p["rolling_7d"] = roll7[i]
        p["rolling_14d"] = roll14[i]
        p["rolling_30d"] = roll30[i]

    return {"metric": "npt_hours", "days": days, "rig_id": rig_id, "data": points}


# ---------------------------------------------------------------------------
# 3. ROP trend (from depth deltas / timeline hours)
# ---------------------------------------------------------------------------

@router.get("/rop")
async def rop_trend(
    rig_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Daily average ROP (ft/hr) computed from depth progress / drilling hours."""
    since = datetime.utcnow() - timedelta(days=days)
    q = (
        db.query(
            DDRReport.report_date,
            DDRReport.rig_id,
            func.max(DepthSummary.hole_depth).label("depth"),
            func.sum(Timeline.duration_hours).label("drill_hrs"),
        )
        .outerjoin(DepthSummary, DepthSummary.report_id == DDRReport.id)
        .outerjoin(Timeline, Timeline.report_id == DDRReport.id)
        .filter(DDRReport.report_date >= since)
    )
    if rig_id:
        q = q.filter(DDRReport.rig_id == rig_id)

    q = q.group_by(DDRReport.report_date, DDRReport.rig_id).order_by(DDRReport.report_date)
    rows = q.all()

    points: List[Dict[str, Any]] = []
    prev_depth: Optional[float] = None
    rop_values: List[float] = []

    for row in rows:
        depth = float(row.depth or 0)
        drill_hrs = float(row.drill_hrs or 0)
        footage = depth - prev_depth if prev_depth is not None else 0
        rop = round(footage / drill_hrs, 2) if drill_hrs > 0 and footage > 0 else 0
        rop_values.append(rop)
        points.append({
            "date": _to_date(row.report_date),
            "rig_id": row.rig_id,
            "rop_ft_hr": rop,
            "footage_ft": round(footage, 2),
            "drill_hours": round(drill_hrs, 2),
        })
        prev_depth = depth

    roll7 = _rolling_avg(rop_values, 7)
    for i, p in enumerate(points):
        p["rolling_7d_rop"] = roll7[i]

    return {"metric": "rop", "days": days, "rig_id": rig_id, "data": points}


# ---------------------------------------------------------------------------
# 4. Mud weight trend
# ---------------------------------------------------------------------------

@router.get("/mud-weight")
async def mud_weight_trend(
    rig_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Daily mud weight (ppg) with rolling averages and SPC-ready data."""
    since = datetime.utcnow() - timedelta(days=days)
    q = (
        db.query(
            DDRReport.report_date,
            DDRReport.rig_id,
            func.avg(MudData.mud_weight).label("avg_mw"),
            func.min(MudData.mud_weight).label("min_mw"),
            func.max(MudData.mud_weight).label("max_mw"),
        )
        .join(MudData, MudData.report_id == DDRReport.id)
        .filter(DDRReport.report_date >= since)
    )
    if rig_id:
        q = q.filter(DDRReport.rig_id == rig_id)

    q = q.group_by(DDRReport.report_date, DDRReport.rig_id).order_by(DDRReport.report_date)
    rows = q.all()

    points: List[Dict[str, Any]] = []
    mw_values: List[float] = []
    for row in rows:
        avg_mw = round(float(row.avg_mw or 0), 2)
        mw_values.append(avg_mw)
        points.append({
            "date": _to_date(row.report_date),
            "rig_id": row.rig_id,
            "avg_ppg": avg_mw,
            "min_ppg": round(float(row.min_mw or 0), 2),
            "max_ppg": round(float(row.max_mw or 0), 2),
        })

    roll7 = _rolling_avg(mw_values, 7)
    for i, p in enumerate(points):
        p["rolling_7d"] = roll7[i]

    return {"metric": "mud_weight", "days": days, "rig_id": rig_id, "data": points}


# ---------------------------------------------------------------------------
# 5. HSE trend (incidents + near-misses)
# ---------------------------------------------------------------------------

@router.get("/hse")
async def hse_trend(
    rig_id: Optional[str] = Query(None),
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Daily HSE incident counts with cumulative totals."""
    since = datetime.utcnow() - timedelta(days=days)
    q = (
        db.query(
            DDRReport.report_date,
            DDRReport.rig_id,
            func.count(HSEData.id).label("incidents"),
        )
        .join(HSEData, HSEData.report_id == DDRReport.id)
        .filter(DDRReport.report_date >= since)
    )
    if rig_id:
        q = q.filter(DDRReport.rig_id == rig_id)

    q = q.group_by(DDRReport.report_date, DDRReport.rig_id).order_by(DDRReport.report_date)
    rows = q.all()

    cumulative = 0
    points: List[Dict[str, Any]] = []
    for row in rows:
        count = int(row.incidents or 0)
        cumulative += count
        points.append({
            "date": _to_date(row.report_date),
            "rig_id": row.rig_id,
            "daily_incidents": count,
            "cumulative_incidents": cumulative,
        })

    return {"metric": "hse_incidents", "days": days, "rig_id": rig_id, "data": points}


# ---------------------------------------------------------------------------
# 6. Multi-rig comparison summary
# ---------------------------------------------------------------------------

@router.get("/compare")
async def multi_rig_compare(
    rig_ids: str = Query(..., description="Comma-separated rig IDs"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Compare key metrics across multiple rigs over a time window."""
    since = datetime.utcnow() - timedelta(days=days)
    rig_list = [r.strip() for r in rig_ids.split(",") if r.strip()]

    results: Dict[str, Any] = {}
    for rid in rig_list:
        # NPT total
        npt_row = (
            db.query(func.sum(NPTEvent.duration_hours))
            .join(DDRReport, DDRReport.id == NPTEvent.report_id)
            .filter(DDRReport.rig_id == rid, DDRReport.report_date >= since)
            .first()
        )
        npt_total = float(npt_row[0] or 0) if npt_row else 0
        # Depth progress
        depth_rows = (
            db.query(func.max(DepthSummary.hole_depth).label("d"))
            .join(DDRReport, DDRReport.id == DepthSummary.report_id)
            .filter(DDRReport.rig_id == rid, DDRReport.report_date >= since)
            .first()
        )
        max_depth = float(depth_rows[0] or 0) if depth_rows and depth_rows[0] else 0
        # Report count
        count_row = (
            db.query(func.count(DDRReport.id))
            .filter(DDRReport.rig_id == rid, DDRReport.report_date >= since)
            .first()
        )
        report_count = int(count_row[0] or 0) if count_row else 0
        results[rid] = {
            "npt_total_hrs": round(float(npt_total), 2),
            "max_depth_ft": round(max_depth, 2),
            "report_count": report_count,
        }

    return {"comparison": results, "days": days, "rig_ids": rig_list}
