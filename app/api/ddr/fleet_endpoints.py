"""
Fleet-Level DDR Endpoints — fleet-wide KPIs, NPT Pareto, SPC control charts.

All endpoints query the DDR domain tables and return structured JSON with citations.
"""
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from services.db.session import get_db
from pipelines.inference.ddr.models import (
    DDRReport,
    DDRRig,
    DepthSummary,
    ExtractedMetric,
    MudData,
    NPTEvent,
    Timeline,
)
from core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v2/fleet", tags=["Fleet Analytics"])


# ============================================================================
# 1. GET /api/v2/fleet/summary
# ============================================================================

@router.get("/summary", summary="Fleet-wide daily KPI summary")
def fleet_summary(
    report_date: Optional[str] = Query(
        None, description="YYYY-MM-DD filter; defaults to latest available date"
    ),
    db: Session = Depends(get_db),
):
    """
    Aggregate KPIs across all active rigs for a given date.

    Returns total rigs, avg ROP, total footage, total NPT hours, avg mud weight,
    and per-rig KPI breakdown.
    """
    # Resolve target date
    if report_date:
        try:
            target = datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="report_date must be YYYY-MM-DD")
    else:
        latest = db.query(sa_func.max(DDRReport.report_date)).scalar()
        target = latest

    if target is None:
        return {
            "date": None,
            "total_rigs": 0,
            "avg_rop": 0,
            "total_footage": 0,
            "total_npt_hours": 0,
            "avg_mud_weight": 0,
            "kpis": [],
        }

    # Filter reports for the target date (same calendar day)
    target_date_start = target.replace(hour=0, minute=0, second=0) if isinstance(target, datetime) else datetime.combine(target, datetime.min.time())
    target_date_end = target_date_start + timedelta(days=1)

    reports = (
        db.query(DDRReport)
        .filter(DDRReport.report_date >= target_date_start)
        .filter(DDRReport.report_date < target_date_end)
        .all()
    )

    report_ids = [r.id for r in reports]
    rig_ids = list({r.rig_id for r in reports if r.rig_id})

    # Aggregate depth / footage
    depth_rows = (
        db.query(DepthSummary)
        .filter(DepthSummary.report_id.in_(report_ids))
        .all()
    ) if report_ids else []

    total_footage = sum(d.hole_depth or 0 for d in depth_rows)

    # Aggregate NPT
    npt_rows = (
        db.query(NPTEvent)
        .filter(NPTEvent.report_id.in_(report_ids))
        .all()
    ) if report_ids else []

    total_npt = sum(n.duration_hours or 0 for n in npt_rows)

    # Aggregate mud weight
    mud_rows = (
        db.query(MudData)
        .filter(MudData.report_id.in_(report_ids))
        .all()
    ) if report_ids else []

    mud_weights = [m.mud_weight for m in mud_rows if m.mud_weight is not None]
    avg_mud_weight = round(sum(mud_weights) / len(mud_weights), 2) if mud_weights else 0

    # ROP from extracted metrics
    rop_metrics = (
        db.query(ExtractedMetric)
        .filter(ExtractedMetric.report_id.in_(report_ids))
        .filter(ExtractedMetric.field_name == "rop")
        .all()
    ) if report_ids else []

    rop_values = [m.numeric_value for m in rop_metrics if m.numeric_value is not None]
    avg_rop = round(sum(rop_values) / len(rop_values), 2) if rop_values else 0

    # Per-rig KPI breakdown
    kpis: List[Dict[str, Any]] = []
    for report in reports:
        rig = db.query(DDRRig).filter(DDRRig.id == report.rig_id).first() if report.rig_id else None
        rig_depth = next((d for d in depth_rows if d.report_id == report.id), None)
        rig_npt = sum(n.duration_hours or 0 for n in npt_rows if n.report_id == report.id)
        rig_rop_m = next((m for m in rop_metrics if m.report_id == report.id), None)

        kpis.append({
            "rig_id": report.rig_id or report.id,
            "rig_name": rig.rig_name if rig else report.well_name or "Unknown",
            "footage": rig_depth.hole_depth if rig_depth else 0,
            "npt_hours": round(rig_npt, 2),
            "rop": rig_rop_m.numeric_value if rig_rop_m else None,
            "rop_citation": rig_rop_m.citation if rig_rop_m else None,
        })

    return {
        "date": target_date_start.strftime("%Y-%m-%d"),
        "total_rigs": len(rig_ids) or len(reports),
        "avg_rop": avg_rop,
        "total_footage": round(total_footage, 2),
        "total_npt_hours": round(total_npt, 2),
        "avg_mud_weight": avg_mud_weight,
        "kpis": kpis,
    }


# ============================================================================
# 2. GET /api/v2/fleet/npt-pareto
# ============================================================================

@router.get("/npt-pareto", summary="NPT Pareto distribution by cause code")
def fleet_npt_pareto(
    report_date: Optional[str] = Query(None, description="Optional YYYY-MM-DD filter"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Aggregate Non-Productive Time events across the fleet, grouped by cause/category.
    Sorted descending by total hours. Includes cumulative percentage for Pareto charting.
    """
    query = db.query(
        NPTEvent.category,
        sa_func.sum(NPTEvent.duration_hours).label("total_hours"),
        sa_func.count(NPTEvent.id).label("event_count"),
    ).group_by(NPTEvent.category)

    if report_date:
        try:
            target = datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="report_date must be YYYY-MM-DD")
        target_end = target + timedelta(days=1)
        # Join to reports for date filtering
        query = (
            db.query(
                NPTEvent.category,
                sa_func.sum(NPTEvent.duration_hours).label("total_hours"),
                sa_func.count(NPTEvent.id).label("event_count"),
            )
            .join(DDRReport, DDRReport.id == NPTEvent.report_id)
            .filter(DDRReport.report_date >= target)
            .filter(DDRReport.report_date < target_end)
            .group_by(NPTEvent.category)
        )

    rows = query.order_by(sa_func.sum(NPTEvent.duration_hours).desc()).limit(limit).all()

    grand_total = sum(r.total_hours or 0 for r in rows)
    pareto: List[Dict[str, Any]] = []
    cumulative = 0.0

    for row in rows:
        hours = round(row.total_hours or 0, 2)
        pct = round((hours / grand_total) * 100, 1) if grand_total > 0 else 0
        cumulative += pct
        pareto.append({
            "cause_code": row.category or "Uncategorized",
            "hours": hours,
            "event_count": row.event_count,
            "percentage": pct,
            "cumulative_pct": round(cumulative, 1),
        })

    return {
        "total_npt_hours": round(grand_total, 2),
        "categories": len(pareto),
        "pareto": pareto,
    }


# ============================================================================
# 3. GET /api/v2/fleet/spc/{metric}
# ============================================================================

METRIC_TO_FIELD: Dict[str, str] = {
    "rop": "rop",
    "mud_weight": "mud_weight",
    "pump_pressure": "pump_pressure",
    "wob": "wob",
    "rpm": "rpm",
    "torque": "torque",
    "flow_rate": "flow_rate",
    "depth_md": "depth_md",
    "npt_hours": "npt_hours",
}


@router.get("/spc/{metric}", summary="SPC control chart for a fleet metric")
def fleet_spc(
    metric: str,
    report_date: Optional[str] = Query(None, description="Optional YYYY-MM-DD filter"),
    usl: Optional[float] = Query(None, description="Upper specification limit"),
    lsl: Optional[float] = Query(None, description="Lower specification limit"),
    db: Session = Depends(get_db),
):
    """
    Compute Statistical Process Control analysis for a metric across the fleet.
    Pulls numeric values from ExtractedMetric, passes them to the SPC engine.
    """
    from pipelines.inference.ddr.spc_engine import compute_spc

    field_name = METRIC_TO_FIELD.get(metric.lower())
    if not field_name:
        available = ", ".join(METRIC_TO_FIELD.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown metric '{metric}'. Available: {available}",
        )

    query = (
        db.query(ExtractedMetric)
        .filter(ExtractedMetric.field_name == field_name)
        .filter(ExtractedMetric.numeric_value.isnot(None))
    )

    if report_date:
        try:
            target = datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="report_date must be YYYY-MM-DD")
        target_end = target + timedelta(days=1)
        query = (
            query.join(DDRReport, DDRReport.id == ExtractedMetric.report_id)
            .filter(DDRReport.report_date >= target)
            .filter(DDRReport.report_date < target_end)
        )

    metrics = query.order_by(ExtractedMetric.created_at).all()

    if len(metrics) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data for SPC on '{metric}' (need ≥2 points, found {len(metrics)})",
        )

    values = [m.numeric_value for m in metrics]
    rig_ids = []
    for m in metrics:
        report = db.query(DDRReport).filter(DDRReport.id == m.report_id).first()
        rig = db.query(DDRRig).filter(DDRRig.id == report.rig_id).first() if report and report.rig_id else None
        rig_ids.append(rig.rig_name if rig else (report.rig_id if report else ""))

    result = compute_spc(
        values=values,
        metric_name=metric,
        rig_ids=rig_ids,
        usl=usl,
        lsl=lsl,
    )

    return {
        "metric": metric,
        "data_points": len(values),
        "spc": result.model_dump(),
    }


# ============================================================================
# 4. GET /api/v2/fleet/top-performers
# ============================================================================

@router.get("/top-performers", summary="Top performing rigs by metric")
def fleet_top_performers(
    report_date: Optional[str] = Query(None, description="YYYY-MM-DD filter"),
    metric: Optional[str] = Query("rop", description="Metric to rank by: rop, footage, npt"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Return top-performing rigs ranked by a metric (ROP, footage, or inverse NPT).
    """
    if report_date:
        try:
            target = datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="report_date must be YYYY-MM-DD")
    else:
        latest = db.query(sa_func.max(DDRReport.report_date)).scalar()
        target = latest

    if target is None:
        return []

    target_start = target.replace(hour=0, minute=0, second=0) if isinstance(target, datetime) else datetime.combine(target, datetime.min.time())
    target_end = target_start + timedelta(days=1)

    reports = (
        db.query(DDRReport)
        .filter(DDRReport.report_date >= target_start)
        .filter(DDRReport.report_date < target_end)
        .all()
    )

    performers = []
    for report in reports:
        rig = db.query(DDRRig).filter(DDRRig.id == report.rig_id).first() if report.rig_id else None
        depth = db.query(DepthSummary).filter(DepthSummary.report_id == report.id).first()
        npt_total = sum(
            n.duration_hours or 0
            for n in db.query(NPTEvent).filter(NPTEvent.report_id == report.id).all()
        )
        rop_m = (
            db.query(ExtractedMetric)
            .filter(ExtractedMetric.report_id == report.id)
            .filter(ExtractedMetric.field_name == "rop")
            .first()
        )
        drilling_hours = sum(
            t.duration_hours or 0
            for t in db.query(Timeline).filter(Timeline.report_id == report.id).filter(Timeline.is_npt == False).all()  # noqa: E712
        )

        rop_val = rop_m.numeric_value if rop_m and rop_m.numeric_value else None
        footage = depth.hole_depth if depth else None

        performers.append({
            "rig_id": report.rig_id or report.id,
            "rig_name": rig.rig_name if rig else report.well_name or "Unknown",
            "rop": round(rop_val, 2) if rop_val else None,
            "footage": round(footage, 2) if footage else None,
            "npt_hours": round(npt_total, 2),
            "drilling_hours": round(drilling_hours, 2),
            "report_date": report.report_date.isoformat() if report.report_date else None,
        })

    # Sort by metric
    sort_key = metric or "rop"
    reverse = sort_key != "npt"  # lower NPT is better
    performers.sort(key=lambda x: x.get(sort_key) or 0, reverse=reverse)

    return performers[:limit]


# ============================================================================
# 5. GET /api/v2/fleet/heatmap
# ============================================================================

@router.get("/heatmap", summary="Fleet rig status heatmap tiles")
def fleet_heatmap(
    report_date: Optional[str] = Query(None, description="YYYY-MM-DD filter"),
    db: Session = Depends(get_db),
):
    """
    Return a heatmap tile for every rig showing status color based on performance.
    """
    if report_date:
        try:
            target = datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="report_date must be YYYY-MM-DD")
    else:
        latest = db.query(sa_func.max(DDRReport.report_date)).scalar()
        target = latest

    if target is None:
        return []

    target_start = target.replace(hour=0, minute=0, second=0) if isinstance(target, datetime) else datetime.combine(target, datetime.min.time())
    target_end = target_start + timedelta(days=1)

    # Get all rigs
    all_rigs = db.query(DDRRig).order_by(DDRRig.rig_name).all()

    # Get reports for target date
    date_reports = {
        r.rig_id: r
        for r in db.query(DDRReport)
        .filter(DDRReport.report_date >= target_start)
        .filter(DDRReport.report_date < target_end)
        .all()
        if r.rig_id
    }

    tiles = []
    for rig in all_rigs:
        report = date_reports.get(rig.id)
        if report:
            npt_total = sum(
                n.duration_hours or 0
                for n in db.query(NPTEvent).filter(NPTEvent.report_id == report.id).all()
            )
            depth = db.query(DepthSummary).filter(DepthSummary.report_id == report.id).first()
            rop_m = (
                db.query(ExtractedMetric)
                .filter(ExtractedMetric.report_id == report.id)
                .filter(ExtractedMetric.field_name == "rop")
                .first()
            )
            # Status based on NPT hours
            if npt_total > 8:
                status = "critical"
            elif npt_total > 4:
                status = "warning"
            elif npt_total > 0:
                status = "caution"
            else:
                status = "on_target"
        else:
            npt_total = 0
            depth = None
            rop_m = None
            status = "no_data"

        tiles.append({
            "rig_id": rig.id,
            "rig_name": rig.rig_name,
            "status": status,
            "npt_hours": round(npt_total, 2),
            "footage": depth.hole_depth if depth else None,
            "rop": rop_m.numeric_value if rop_m and rop_m.numeric_value else None,
            "has_report": report is not None,
        })

    return tiles


# ============================================================================
# 6. GET /api/v2/fleet/export
# ============================================================================

@router.get("/export", summary="Export fleet summary as JSON (PDF/Excel generation handled by frontend)")
def fleet_export(
    report_date: Optional[str] = Query(None),
    format: Optional[str] = Query("json", description="Export format: json"),
    db: Session = Depends(get_db),
):
    """
    Return fleet summary data suitable for export.
    """
    summary = fleet_summary(report_date=report_date, db=db)
    return {"format": format, "data": summary}
