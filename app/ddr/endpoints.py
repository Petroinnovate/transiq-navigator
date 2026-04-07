"""
DDR API Endpoints — FastAPI router for DDR parsing, SPC analytics, and citations.

Integrates with the main TransIQ app via include_router().
"""
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v2/ddr", tags=["DDR Intelligence"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class SPCRequest(BaseModel):
    values: List[float]
    metric_name: str = "metric"
    rig_ids: Optional[List[str]] = None
    timestamps: Optional[List[str]] = None
    usl: Optional[float] = None
    lsl: Optional[float] = None
    sigma_multiplier: float = 3.0


class FleetSPCRequest(BaseModel):
    fleet_data: Dict[str, List[float]]
    metric_name: str = "metric"
    usl: Optional[float] = None
    lsl: Optional[float] = None


class DetectRequest(BaseModel):
    pdf_path: str


class MultiParseRequest(BaseModel):
    reports: List[Dict[str, str]]  # [{"pdf_path": "...", "rig_id": "..."}]
    max_workers: int = 4
    ocr_fallback: bool = True


class MetricUpdateRequest(BaseModel):
    new_value: str
    reason: str = "correction"
    source_method: str = "manual"
    origin: str = "system"


# ---------------------------------------------------------------------------
# DDR Parsing endpoints
# ---------------------------------------------------------------------------

@router.post("/parse", summary="Parse a single DDR PDF")
async def parse_ddr(
    pdf_path: str = Query(..., description="Server-side path to DDR PDF"),
    rig_id: str = Query("", description="Rig identifier for citations"),
    ocr_fallback: bool = Query(True, description="Use OCR on low-text pages"),
):
    """Parse a DDR PDF and return structured extraction results."""
    from app.ddr.ddr_parser import parse_ddr_pdf

    if not os.path.isfile(pdf_path):
        raise HTTPException(status_code=404, detail=f"PDF not found: {pdf_path}")

    result = parse_ddr_pdf(pdf_path, rig_id=rig_id, ocr_fallback=ocr_fallback)
    return result.model_dump()


@router.post("/parse-upload", summary="Upload & parse a DDR PDF")
async def parse_ddr_upload(
    file: UploadFile = File(...),
    rig_id: str = Query("", description="Rig identifier for citations"),
    ocr_fallback: bool = Query(True),
):
    """Upload a PDF, save to temp storage, parse it."""
    from app.ddr.ddr_parser import parse_ddr_pdf
    from app.config.settings import settings

    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    dest = os.path.join(upload_dir, file.filename or "upload.pdf")

    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)

    result = parse_ddr_pdf(dest, rig_id=rig_id, ocr_fallback=ocr_fallback)
    return result.model_dump()


@router.post("/parse-batch", summary="Parse multiple DDR PDFs concurrently")
async def parse_ddr_batch(request: MultiParseRequest):
    """Parse multiple DDR PDFs using multiprocessing."""
    from app.ddr.ddr_parser import parse_multiple_ddrs

    results = parse_multiple_ddrs(
        request.reports,
        max_workers=request.max_workers,
        ocr_fallback=request.ocr_fallback,
    )
    return {"count": len(results), "results": results}


# ---------------------------------------------------------------------------
# Report Detection endpoint
# ---------------------------------------------------------------------------

@router.post("/detect", summary="Detect if a PDF is a DDR or generic document")
async def detect_report(
    pdf_path: str = Query(..., description="Path to PDF for classification"),
):
    """Classify a PDF as DDR or GENERIC with confidence score."""
    from app.ddr.report_detector import detect_report_type

    if not os.path.isfile(pdf_path):
        raise HTTPException(status_code=404, detail=f"PDF not found: {pdf_path}")

    result = detect_report_type(pdf_path)
    return result.model_dump()


# ---------------------------------------------------------------------------
# SPC endpoints
# ---------------------------------------------------------------------------

@router.post("/spc", summary="Compute SPC analysis for a metric")
async def compute_spc_endpoint(request: SPCRequest):
    """Run Statistical Process Control analysis on a list of values."""
    from app.ddr.spc_engine import compute_spc

    if len(request.values) < 2:
        raise HTTPException(status_code=400, detail="At least 2 data points required")

    result = compute_spc(
        values=request.values,
        metric_name=request.metric_name,
        rig_ids=request.rig_ids,
        timestamps=request.timestamps,
        usl=request.usl,
        lsl=request.lsl,
        sigma_multiplier=request.sigma_multiplier,
    )
    return result.model_dump()


@router.post("/spc/fleet", summary="Fleet-wide SPC analysis across rigs")
async def fleet_spc_endpoint(request: FleetSPCRequest):
    """Compute SPC across an entire fleet of rigs."""
    from app.ddr.spc_engine import compute_fleet_spc

    if not request.fleet_data:
        raise HTTPException(status_code=400, detail="fleet_data must not be empty")

    result = compute_fleet_spc(
        fleet_data=request.fleet_data,
        metric_name=request.metric_name,
        usl=request.usl,
        lsl=request.lsl,
    )
    return result


# ---------------------------------------------------------------------------
# Citation / Metrics endpoints
# ---------------------------------------------------------------------------

@router.get("/metrics/{report_id}", summary="Get all extracted metrics for a DDR report")
async def get_report_metrics(report_id: str):
    """Return all extracted metrics with citations for a report."""
    try:
        from app.db.session import get_db_session
        from app.ddr.citation_service import get_report_metrics as _get

        with get_db_session() as db:
            metrics = _get(db, report_id)
            return {
                "report_id": report_id,
                "count": len(metrics),
                "metrics": [
                    {
                        "id": m.id,
                        "field_name": m.field_name,
                        "value": m.value,
                        "numeric_value": m.numeric_value,
                        "citation": m.citation,
                        "extraction_method": m.extraction_method,
                        "page_number": m.page_number,
                        "confidence_score": m.confidence_score,
                        "is_imputed": m.is_imputed,
                    }
                    for m in metrics
                ],
            }
    except Exception as e:
        logger.error(f"Failed to fetch metrics for report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/{metric_id}", summary="Get audit trail for a metric")
async def get_metric_audit(metric_id: str):
    """Return the full change history (audit trail) for a single metric."""
    try:
        from app.db.session import get_db_session
        from app.ddr.citation_service import get_metric_audit_trail

        with get_db_session() as db:
            trail = get_metric_audit_trail(db, metric_id)
            return {
                "metric_id": metric_id,
                "count": len(trail),
                "audit_trail": [
                    {
                        "id": a.id,
                        "field_name": a.field_name,
                        "old_value": a.old_value,
                        "new_value": a.new_value,
                        "change_reason": a.change_reason,
                        "source_method": a.source_method,
                        "origin": a.origin,
                        "timestamp": str(a.timestamp) if a.timestamp else None,
                    }
                    for a in trail
                ],
            }
    except Exception as e:
        logger.error(f"Failed to fetch audit trail for metric {metric_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/metrics/{metric_id}", summary="Update a metric value with audit logging")
async def update_metric_endpoint(metric_id: str, request: MetricUpdateRequest):
    """Update an extracted metric — old value is preserved in audit trail."""
    try:
        from app.db.session import get_db_session
        from app.ddr.citation_service import update_metric
        from app.ddr.models import ExtractedMetric

        with get_db_session() as db:
            metric = db.query(ExtractedMetric).filter(ExtractedMetric.id == metric_id).first()
            if not metric:
                raise HTTPException(status_code=404, detail=f"Metric {metric_id} not found")

            updated = update_metric(
                db, metric,
                new_value=request.new_value,
                reason=request.reason,
                source_method=request.source_method,
                origin=request.origin,
            )
            return {
                "id": updated.id,
                "field_name": updated.field_name,
                "value": updated.value,
                "citation": updated.citation,
                "updated": True,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update metric {metric_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Reports list — all DDR reports for date selector
# ============================================================================

@router.get("/reports", summary="List all DDR reports with dates")
def list_ddr_reports(db: Session = Depends(get_db)):
    """
    Return a list of all DDR reports with dates, rig info, and basic metadata.
    Used by the frontend ReportDateSelector.
    """
    from app.ddr.models import DDRReport, DDRRig

    reports = (
        db.query(DDRReport)
        .order_by(DDRReport.report_date.desc())
        .limit(500)
        .all()
    )

    result = []
    for r in reports:
        rig = db.query(DDRRig).filter(DDRRig.id == r.rig_id).first() if r.rig_id else None
        result.append({
            "id": r.id,
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "rig_id": r.rig_id,
            "rig_name": rig.rig_name if rig else None,
            "well_name": r.well_name,
            "field_name": r.field_name,
            "operator": r.operator,
            "report_number": r.report_number,
            "status": r.status,
        })

    return result
