"""
Rig-Level DDR Endpoints — per-rig drilldown for all DDR data domains.

Covers: rig list, rig detail, timeline, NPT, survey, mud, personnel,
BHA/drill-string, HSE, and foreman remarks. All include citations where applicable.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func as sa_func
from sqlalchemy.orm import Session

from services.db.session import get_db
from pipelines.inference.ddr.models import (
    BulkLogistics,
    DDRReport,
    DDRRig,
    DepthSummary,
    DrillString,
    ExtractedMetric,
    ForemanRemark,
    FormationTop,
    HSEData,
    MudChemical,
    MudData,
    NPTEvent,
    Personnel,
    Survey,
    Timeline,
)
from core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v2/rigs", tags=["Rig Analytics"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_rig_or_404(db: Session, rig_id: str) -> DDRRig:
    rig = db.query(DDRRig).filter(DDRRig.id == rig_id).first()
    if not rig:
        # Try by name as well
        rig = db.query(DDRRig).filter(DDRRig.rig_name == rig_id).first()
    if not rig:
        raise HTTPException(status_code=404, detail=f"Rig '{rig_id}' not found")
    return rig


def _latest_report(db: Session, rig: DDRRig) -> Optional[DDRReport]:
    return (
        db.query(DDRReport)
        .filter(DDRReport.rig_id == rig.id)
        .order_by(desc(DDRReport.report_date))
        .first()
    )


def _report_for_rig(
    db: Session,
    rig: DDRRig,
    report_date: Optional[str],
) -> Optional[DDRReport]:
    """Get a specific report by date or latest."""
    if report_date:
        try:
            target = datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="report_date must be YYYY-MM-DD")
        target_end = target + timedelta(days=1)
        return (
            db.query(DDRReport)
            .filter(DDRReport.rig_id == rig.id)
            .filter(DDRReport.report_date >= target)
            .filter(DDRReport.report_date < target_end)
            .first()
        )
    return _latest_report(db, rig)


def _citations_for_report(db: Session, report_id: str) -> Dict[str, str]:
    """Return {field_name: citation} map for a report."""
    rows = (
        db.query(ExtractedMetric.field_name, ExtractedMetric.citation)
        .filter(ExtractedMetric.report_id == report_id)
        .all()
    )
    return {r.field_name: r.citation for r in rows if r.citation}


# ============================================================================
# 4. GET /api/v2/rigs — list all rigs with summary KPIs
# ============================================================================

@router.get("", summary="List all rigs with summary KPIs")
def list_rigs(
    status: Optional[str] = Query(None, description="Filter by status (active/inactive)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(DDRRig)
    if status:
        query = query.filter(DDRRig.status == status)

    total = query.count()
    rigs = query.order_by(DDRRig.rig_name).offset((page - 1) * page_size).limit(page_size).all()

    result: List[Dict[str, Any]] = []
    for rig in rigs:
        # Latest report
        latest = _latest_report(db, rig)

        # Aggregate NPT
        total_npt = (
            db.query(sa_func.sum(NPTEvent.duration_hours))
            .join(DDRReport, DDRReport.id == NPTEvent.report_id)
            .filter(DDRReport.rig_id == rig.id)
            .scalar()
        ) or 0

        # Avg ROP
        avg_rop_val = (
            db.query(sa_func.avg(ExtractedMetric.numeric_value))
            .join(DDRReport, DDRReport.id == ExtractedMetric.report_id)
            .filter(DDRReport.rig_id == rig.id)
            .filter(ExtractedMetric.field_name == "rop")
            .scalar()
        )

        result.append({
            "rig_id": rig.id,
            "name": rig.rig_name,
            "rig_type": rig.rig_type,
            "contractor": rig.contractor,
            "status": rig.status,
            "avg_rop": round(avg_rop_val, 2) if avg_rop_val else None,
            "total_npt": round(total_npt, 2),
            "last_report_date": latest.report_date.isoformat() if latest and latest.report_date else None,
        })

    return {"total": total, "page": page, "page_size": page_size, "rigs": result}


# ============================================================================
# 5. GET /api/v2/rigs/{rig_id} — full rig details with citations
# ============================================================================

@router.get("/{rig_id}", summary="Full rig details including KPIs and citations")
def rig_detail(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {
            "rig": {"id": rig.id, "name": rig.rig_name, "status": rig.status},
            "report": None,
            "message": "No report found for the specified date",
        }

    citations = _citations_for_report(db, report.id)

    # Depth
    depth = db.query(DepthSummary).filter(DepthSummary.report_id == report.id).first()

    # Extracted metrics
    metrics = (
        db.query(ExtractedMetric)
        .filter(ExtractedMetric.report_id == report.id)
        .all()
    )
    kpis = {}
    for m in metrics:
        kpis[m.field_name] = {
            "value": m.value,
            "numeric_value": m.numeric_value,
            "confidence": m.confidence_score,
            "extraction_method": m.extraction_method,
            "citation": m.citation,
            "is_imputed": m.is_imputed,
        }

    return {
        "rig": {
            "id": rig.id,
            "name": rig.rig_name,
            "rig_type": rig.rig_type,
            "contractor": rig.contractor,
            "location": rig.location,
            "status": rig.status,
        },
        "report": {
            "id": report.id,
            "report_date": report.report_date.isoformat() if report.report_date else None,
            "report_number": report.report_number,
            "well_name": report.well_name,
            "field_name": report.field_name,
            "operator": report.operator,
            "total_pages": report.total_pages,
        },
        "depth": {
            "md": depth.depth_md if depth else None,
            "tvd": depth.depth_tvd if depth else None,
            "hole_depth": depth.hole_depth if depth else None,
            "casing_depth": depth.casing_depth if depth else None,
            "unit": depth.unit if depth else "ft",
        },
        "kpis": kpis,
        "citations": citations,
    }


# ============================================================================
# 6. GET /api/v2/rigs/{rig_id}/timeline — 24-hour operations timeline
# ============================================================================

@router.get("/{rig_id}/timeline", summary="24-hour operations timeline")
def rig_timeline(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {"rig_id": rig.id, "timeline": [], "message": "No report found"}

    entries = (
        db.query(Timeline)
        .filter(Timeline.report_id == report.id)
        .order_by(Timeline.start_time)
        .all()
    )

    return {
        "rig_id": rig.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "count": len(entries),
        "timeline": [
            {
                "start_time": e.start_time,
                "end_time": e.end_time,
                "duration_hours": e.duration_hours,
                "activity_code": e.activity_code,
                "description": e.description,
                "depth_from": e.depth_from,
                "depth_to": e.depth_to,
                "is_npt": e.is_npt,
            }
            for e in entries
        ],
    }


# ============================================================================
# 7. GET /api/v2/rigs/{rig_id}/npt — NPT events
# ============================================================================

@router.get("/{rig_id}/npt", summary="Non-Productive Time events for a rig")
def rig_npt(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {"rig_id": rig.id, "npt_events": [], "total_hours": 0}

    events = (
        db.query(NPTEvent)
        .filter(NPTEvent.report_id == report.id)
        .order_by(NPTEvent.duration_hours.desc())
        .all()
    )

    total = sum(e.duration_hours or 0 for e in events)

    return {
        "rig_id": rig.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "total_npt_hours": round(total, 2),
        "count": len(events),
        "npt_events": [
            {
                "id": e.id,
                "npt_code": e.npt_code,
                "category": e.category,
                "description": e.description,
                "duration_hours": e.duration_hours,
                "cost_impact": e.cost_impact,
                "root_cause": e.root_cause,
            }
            for e in events
        ],
    }


# ============================================================================
# 8. GET /api/v2/rigs/{rig_id}/survey — directional survey
# ============================================================================

@router.get("/{rig_id}/survey", summary="Directional survey data")
def rig_survey(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {"rig_id": rig.id, "surveys": []}

    rows = (
        db.query(Survey)
        .filter(Survey.report_id == report.id)
        .order_by(Survey.depth_md)
        .all()
    )

    return {
        "rig_id": rig.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "count": len(rows),
        "surveys": [
            {
                "depth_md": s.depth_md,
                "inclination": s.inclination,
                "azimuth": s.azimuth,
                "tvd": s.tvd,
                "dog_leg_severity": s.dog_leg_severity,
            }
            for s in rows
        ],
    }


# ============================================================================
# 9. GET /api/v2/rigs/{rig_id}/mud — mud data + chemicals
# ============================================================================

@router.get("/{rig_id}/mud", summary="Mud data and treatment chemicals")
def rig_mud(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {"rig_id": rig.id, "mud_data": None, "chemicals": []}

    mud = db.query(MudData).filter(MudData.report_id == report.id).first()
    chemicals = (
        db.query(MudChemical)
        .filter(MudChemical.report_id == report.id)
        .order_by(MudChemical.chemical_name)
        .all()
    )

    citations = _citations_for_report(db, report.id)

    return {
        "rig_id": rig.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "mud_data": {
            "mud_type": mud.mud_type,
            "mud_weight": mud.mud_weight,
            "viscosity": mud.viscosity,
            "plastic_viscosity": mud.plastic_viscosity,
            "yield_point": mud.yield_point,
            "gel_strength_10s": mud.gel_strength_10s,
            "gel_strength_10m": mud.gel_strength_10m,
            "ph": mud.ph,
            "fluid_loss": mud.fluid_loss,
            "unit": mud.unit,
            "mud_weight_citation": citations.get("mud_weight"),
        } if mud else None,
        "chemicals": [
            {
                "chemical_name": c.chemical_name,
                "quantity": c.quantity,
                "unit": c.unit,
                "purpose": c.purpose,
            }
            for c in chemicals
        ],
    }


# ============================================================================
# 10. GET /api/v2/rigs/{rig_id}/personnel — personnel matrix
# ============================================================================

@router.get("/{rig_id}/personnel", summary="Personnel on-board matrix")
def rig_personnel(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {"rig_id": rig.id, "personnel": [], "total_pob": 0}

    rows = (
        db.query(Personnel)
        .filter(Personnel.report_id == report.id)
        .order_by(Personnel.role)
        .all()
    )

    total_pob = sum(p.count for p in rows)

    return {
        "rig_id": rig.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "total_pob": total_pob,
        "count": len(rows),
        "personnel": [
            {
                "name": p.name,
                "role": p.role,
                "company": p.company,
                "count": p.count,
            }
            for p in rows
        ],
    }


# ============================================================================
# 11. GET /api/v2/rigs/{rig_id}/bha — BHA / drill string
# ============================================================================

@router.get("/{rig_id}/bha", summary="BHA / drill string composition")
def rig_bha(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {"rig_id": rig.id, "drill_string": []}

    rows = (
        db.query(DrillString)
        .filter(DrillString.report_id == report.id)
        .order_by(DrillString.position)
        .all()
    )

    total_length = sum(c.length or 0 for c in rows)

    return {
        "rig_id": rig.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "total_length": round(total_length, 2),
        "component_count": len(rows),
        "drill_string": [
            {
                "position": c.position,
                "component_name": c.component_name,
                "od": c.od,
                "id": c.id_val,
                "length": c.length,
                "weight": c.weight,
                "description": c.description,
            }
            for c in rows
        ],
    }


# ============================================================================
# 12. GET /api/v2/rigs/{rig_id}/hse — HSE safety data
# ============================================================================

@router.get("/{rig_id}/hse", summary="HSE and safety data")
def rig_hse(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {"rig_id": rig.id, "hse": None}

    hse = db.query(HSEData).filter(HSEData.report_id == report.id).first()

    return {
        "rig_id": rig.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "hse": {
            "lti": hse.lti,
            "mto": hse.mto,
            "first_aid": hse.first_aid,
            "near_miss": hse.near_miss,
            "safety_observations": hse.safety_observations,
            "stop_cards": hse.stop_cards,
            "drills_conducted": hse.drills_conducted,
            "permit_to_work": hse.permit_to_work,
            "remarks": hse.remarks,
        } if hse else None,
    }


# ============================================================================
# 13. GET /api/v2/rigs/{rig_id}/foreman-remarks — parsed foreman remarks
# ============================================================================

@router.get("/{rig_id}/foreman-remarks", summary="Parsed foreman remarks & observations")
def rig_foreman_remarks(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {"rig_id": rig.id, "remarks": []}

    rows = (
        db.query(ForemanRemark)
        .filter(ForemanRemark.report_id == report.id)
        .order_by(ForemanRemark.created_at)
        .all()
    )

    return {
        "rig_id": rig.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "count": len(rows),
        "remarks": [
            {
                "id": r.id,
                "text": r.remark_text,
                "author_role": r.author_role,
            }
            for r in rows
        ],
    }


# ============================================================================
# 14. GET /api/v2/rigs/{rig_id}/kpis — extracted KPIs with citations
# ============================================================================

@router.get("/{rig_id}/kpis", summary="All extracted KPIs with citations")
def rig_kpis(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {"rig_id": rig.id, "kpis": {}}

    metrics = (
        db.query(ExtractedMetric)
        .filter(ExtractedMetric.report_id == report.id)
        .all()
    )

    kpis = {}
    for m in metrics:
        kpis[m.field_name] = {
            "value": m.value,
            "numeric_value": m.numeric_value,
            "confidence": m.confidence_score,
            "extraction_method": m.extraction_method,
            "citation": m.citation,
            "is_imputed": m.is_imputed,
            "page_number": m.page_number,
        }

    return {
        "rig_id": rig.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "kpis": kpis,
    }


# ============================================================================
# 15. GET /api/v2/rigs/{rig_id}/bulk — bulk logistics / materials
# ============================================================================

@router.get("/{rig_id}/bulk", summary="Bulk material logistics")
def rig_bulk(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {"rig_id": rig.id, "bulk": []}

    rows = (
        db.query(BulkLogistics)
        .filter(BulkLogistics.report_id == report.id)
        .order_by(BulkLogistics.material)
        .all()
    )

    return {
        "rig_id": rig.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "count": len(rows),
        "bulk": [
            {
                "material": b.material,
                "received": b.received,
                "consumed": b.consumed,
                "on_hand": b.on_hand,
                "unit": b.unit,
            }
            for b in rows
        ],
    }


# ============================================================================
# 16. GET /api/v2/rigs/{rig_id}/well-design — formation tops + depth profile
# ============================================================================

@router.get("/{rig_id}/well-design", summary="Well design with formation tops")
def rig_well_design(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rig = _get_rig_or_404(db, rig_id)
    report = _report_for_rig(db, rig, report_date)

    if not report:
        return {"rig_id": rig.id, "formation_tops": [], "depth": None}

    depth = db.query(DepthSummary).filter(DepthSummary.report_id == report.id).first()
    tops = (
        db.query(FormationTop)
        .filter(FormationTop.report_id == report.id)
        .order_by(FormationTop.depth_md)
        .all()
    )

    return {
        "rig_id": rig.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "well_name": report.well_name,
        "depth": {
            "md": depth.depth_md if depth else None,
            "tvd": depth.depth_tvd if depth else None,
            "hole_depth": depth.hole_depth if depth else None,
            "casing_depth": depth.casing_depth if depth else None,
            "unit": depth.unit if depth else "ft",
        },
        "formation_tops": [
            {
                "formation_name": f.formation_name,
                "depth_md": f.depth_md,
                "depth_tvd": f.depth_tvd,
                "description": f.description,
            }
            for f in tops
        ],
    }


# ============================================================================
# 17. GET /api/v2/rigs/{rig_id}/export — export rig data
# ============================================================================

@router.get("/{rig_id}/export", summary="Export rig report data as JSON")
def rig_export(
    rig_id: str,
    report_date: Optional[str] = Query(None),
    format: Optional[str] = Query("json"),
    db: Session = Depends(get_db),
):
    detail = rig_detail(rig_id=rig_id, report_date=report_date, db=db)
    return {"format": format, "data": detail}
