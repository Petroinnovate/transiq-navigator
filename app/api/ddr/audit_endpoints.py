"""
Audit Endpoint — field-level audit trail for any rig/field combination.

Exposes the append-only KPIAudit log with full change history,
source methods, and citations.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from services.db.session import get_db
from pipelines.inference.ddr.models import DDRReport, DDRRig, ExtractedMetric, KPIAudit
from core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v2/audit", tags=["DDR Audit"])


# ============================================================================
# 13b. GET /api/v2/audit/{rig_id}/all — All fields audit for a rig
# ============================================================================

@router.get(
    "/{rig_id}/all",
    summary="All-fields audit trail for a rig",
)
def all_fields_audit_trail(
    rig_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Return the full change history across ALL fields for a specific rig.
    """
    rig = db.query(DDRRig).filter(DDRRig.id == rig_id).first()
    if not rig:
        rig = db.query(DDRRig).filter(DDRRig.rig_name == rig_id).first()
    if not rig:
        raise HTTPException(status_code=404, detail=f"Rig '{rig_id}' not found")

    report_ids = [
        r.id
        for r in db.query(DDRReport.id).filter(DDRReport.rig_id == rig.id).all()
    ]

    if not report_ids:
        return {
            "rig_id": rig.id,
            "rig_name": rig.rig_name,
            "total": 0,
            "history": [],
        }

    query = (
        db.query(KPIAudit)
        .filter(KPIAudit.report_id.in_(report_ids))
    )

    total = query.count()
    rows = (
        query.order_by(desc(KPIAudit.timestamp))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    history: List[Dict[str, Any]] = []
    for row in rows:
        history.append({
            "id": row.id,
            "field": row.field_name,
            "value": row.new_value,
            "old_value": row.old_value,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "source": row.source_method,
            "origin": row.origin,
            "change_reason": row.change_reason,
            "report_id": row.report_id,
        })

    return {
        "rig_id": rig.id,
        "rig_name": rig.rig_name,
        "total": total,
        "page": page,
        "page_size": page_size,
        "history": history,
    }


# ============================================================================
# 14. GET /api/v2/audit/{rig_id}/{field_name}
# ============================================================================

@router.get(
    "/{rig_id}/{field_name}",
    summary="Field-level audit trail for a rig",
)
def field_audit_trail(
    rig_id: str,
    field_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Return the full change history for a specific field on a specific rig.

    Includes: value, timestamp, source method (regex/OCR/LLM/imputed),
    citation, and change reason.
    """
    # Resolve rig
    rig = db.query(DDRRig).filter(DDRRig.id == rig_id).first()
    if not rig:
        rig = db.query(DDRRig).filter(DDRRig.rig_name == rig_id).first()
    if not rig:
        raise HTTPException(status_code=404, detail=f"Rig '{rig_id}' not found")

    # Find all report IDs for this rig
    report_ids = [
        r.id
        for r in db.query(DDRReport.id).filter(DDRReport.rig_id == rig.id).all()
    ]

    if not report_ids:
        return {
            "rig_id": rig.id,
            "rig_name": rig.rig_name,
            "field": field_name,
            "total": 0,
            "history": [],
        }

    # Query audit trail for this field across all rig reports
    query = (
        db.query(KPIAudit)
        .filter(KPIAudit.report_id.in_(report_ids))
        .filter(KPIAudit.field_name == field_name)
    )

    total = query.count()
    rows = (
        query.order_by(desc(KPIAudit.timestamp))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Enrich with citation from ExtractedMetric if available
    history: List[Dict[str, Any]] = []
    for row in rows:
        citation = None
        if row.metric_id:
            metric = db.query(ExtractedMetric).filter(ExtractedMetric.id == row.metric_id).first()
            if metric:
                citation = metric.citation
        elif row.report_id:
            # Fallback: look up by report_id + field_name
            metric = (
                db.query(ExtractedMetric)
                .filter(ExtractedMetric.report_id == row.report_id)
                .filter(ExtractedMetric.field_name == field_name)
                .first()
            )
            if metric:
                citation = metric.citation

        history.append({
            "id": row.id,
            "value": row.new_value,
            "old_value": row.old_value,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "source": row.source_method,
            "origin": row.origin,
            "change_reason": row.change_reason,
            "citation": citation,
            "report_id": row.report_id,
        })

    return {
        "rig_id": rig.id,
        "rig_name": rig.rig_name,
        "field": field_name,
        "total": total,
        "page": page,
        "page_size": page_size,
        "history": history,
    }


# ============================================================================
# 15. GET /api/v2/audit/changelog — Recent changes across all rigs
# ============================================================================

@router.get(
    "/changelog",
    summary="Recent audit changes across all rigs and fields",
)
def audit_changelog(
    report_date: Optional[str] = Query(None, description="Optional YYYY-MM-DD filter"),
    rig_id: Optional[str] = Query(None, description="Optional rig ID filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Return recent audit changelog entries across all rigs/fields.
    Useful for the Audit Trail dashboard module.
    """
    query = db.query(KPIAudit)

    if rig_id:
        rig = db.query(DDRRig).filter(DDRRig.id == rig_id).first()
        if not rig:
            rig = db.query(DDRRig).filter(DDRRig.rig_name == rig_id).first()
        if rig:
            report_ids = [
                r.id for r in db.query(DDRReport.id).filter(DDRReport.rig_id == rig.id).all()
            ]
            if report_ids:
                query = query.filter(KPIAudit.report_id.in_(report_ids))
            else:
                return {"total": 0, "page": page, "page_size": page_size, "entries": []}

    total = query.count()
    rows = (
        query.order_by(desc(KPIAudit.timestamp))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    entries = []
    for row in rows:
        # Resolve rig name from report
        rig_name = None
        if row.report_id:
            report = db.query(DDRReport).filter(DDRReport.id == row.report_id).first()
            if report and report.rig_id:
                rig_obj = db.query(DDRRig).filter(DDRRig.id == report.rig_id).first()
                rig_name = rig_obj.rig_name if rig_obj else None

        entries.append({
            "id": row.id,
            "field_name": row.field_name,
            "old_value": row.old_value,
            "new_value": row.new_value,
            "change_reason": row.change_reason,
            "source_method": row.source_method,
            "origin": row.origin,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "report_id": row.report_id,
            "rig_name": rig_name,
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "entries": entries,
    }
