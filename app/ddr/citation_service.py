"""
Citation Service — Tracks provenance for every extracted DDR metric.

Provides helpers to:
 - Create citations in [RigID–Pg#–Section–Field] format
 - Persist ExtractedMetric rows with confidence & method
 - Append audit-log entries (KPIAudit) on every value change
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.ddr.models import ExtractedMetric, KPIAudit
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Citation formatting
# ---------------------------------------------------------------------------

def build_citation(
    rig_id: str,
    page_number: int,
    section: str,
    field_name: str,
) -> str:
    """
    Produce citation string in standard DDR format.

    Example: [RIG-12–Pg3–MudData–MudWeight]
    """
    return f"[{rig_id}–Pg{page_number}–{section}–{field_name}]"


# ---------------------------------------------------------------------------
# Persist extracted metrics
# ---------------------------------------------------------------------------

def save_extracted_metrics(
    db: Session,
    report_id: str,
    extractions: List[Dict[str, Any]],
    page_hashes: Optional[Dict[int, str]] = None,
) -> List[ExtractedMetric]:
    """
    Bulk-save extracted metrics with citations.

    Args:
        db: SQLAlchemy session.
        report_id: FK to ddr_reports.id.
        extractions: List of dicts with keys:
            name, value, page_number, confidence, extraction_method,
            citation, raw_text, is_imputed (optional).
        page_hashes: {page_number: sha256_hex} for traceability.

    Returns:
        List of persisted ExtractedMetric objects.
    """
    page_hashes = page_hashes or {}
    metrics: List[ExtractedMetric] = []

    for ext in extractions:
        pg = ext.get("page_number", 0)
        numeric = None
        try:
            numeric = float(ext["value"])
        except (ValueError, TypeError):
            pass

        m = ExtractedMetric(
            report_id=report_id,
            field_name=ext["name"],
            value=str(ext.get("value", "")),
            numeric_value=numeric,
            citation=ext.get("citation", ""),
            extraction_method=ext.get("extraction_method", "regex"),
            page_number=pg,
            page_hash=page_hashes.get(pg, ""),
            confidence_score=ext.get("confidence", 1.0),
            is_imputed=ext.get("is_imputed", False),
            raw_text=ext.get("raw_text", ""),
        )
        db.add(m)
        metrics.append(m)

        # Audit log entry — initial extraction
        audit = KPIAudit(
            report_id=report_id,
            field_name=ext["name"],
            old_value=None,
            new_value=str(ext.get("value", "")),
            change_reason="initial_extraction",
            source_method=ext.get("extraction_method", "regex"),
            origin="system",
        )
        db.add(audit)

    db.commit()
    logger.info(f"Saved {len(metrics)} extracted metrics for report {report_id}")
    return metrics


# ---------------------------------------------------------------------------
# Update metric with audit trail
# ---------------------------------------------------------------------------

def update_metric(
    db: Session,
    metric: ExtractedMetric,
    new_value: str,
    reason: str = "correction",
    source_method: str = "manual",
    origin: str = "system",
) -> ExtractedMetric:
    """
    Update an extracted metric and append an audit log entry.

    The old value is preserved in the audit trail — metrics table shows current value.
    """
    old_value = metric.value

    # Update metric
    metric.value = new_value
    try:
        metric.numeric_value = float(new_value)
    except (ValueError, TypeError):
        metric.numeric_value = None

    # Append audit log (immutable)
    audit = KPIAudit(
        report_id=metric.report_id,
        metric_id=metric.id,
        field_name=metric.field_name,
        old_value=old_value,
        new_value=new_value,
        change_reason=reason,
        source_method=source_method,
        origin=origin,
    )
    db.add(audit)
    db.commit()

    logger.info(
        f"Updated metric {metric.field_name}: {old_value} → {new_value} "
        f"(reason={reason}, origin={origin})"
    )
    return metric


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_metric_audit_trail(
    db: Session,
    metric_id: str,
) -> List[KPIAudit]:
    """Return full audit trail for a single metric, oldest first."""
    return (
        db.query(KPIAudit)
        .filter(KPIAudit.metric_id == metric_id)
        .order_by(KPIAudit.timestamp.asc())
        .all()
    )


def get_report_metrics(
    db: Session,
    report_id: str,
) -> List[ExtractedMetric]:
    """Return all extracted metrics for a report."""
    return (
        db.query(ExtractedMetric)
        .filter(ExtractedMetric.report_id == report_id)
        .order_by(ExtractedMetric.field_name)
        .all()
    )
