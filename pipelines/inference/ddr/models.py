"""
DDR Database Models — 15 normalized tables for Daily Drilling Report data

Includes citation tracking (ExtractedMetric) and append-only audit log (KPIAudit).
All tables use UUID primary keys, timestamps, and FK relationships.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from services.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ============================================================================
# 1. reports
# ============================================================================

class DDRReport(Base):
    """Master DDR report record — one row per uploaded DDR PDF."""
    __tablename__ = "ddr_reports"

    id = Column(String, primary_key=True, default=_uuid)
    doc_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    rig_id = Column(String, ForeignKey("ddr_rigs.id"), nullable=True, index=True)
    report_date = Column(DateTime(timezone=True), nullable=True)
    report_number = Column(String, nullable=True)
    field_name = Column(String, nullable=True)
    operator = Column(String, nullable=True)
    contractor = Column(String, nullable=True)
    well_name = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    total_pages = Column(Integer, default=0)
    ocr_pages = Column(Integer, default=0)
    parse_time_ms = Column(Float, default=0.0)
    status = Column(String, default="parsed", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    rig = relationship("DDRRig", back_populates="reports")
    depth_summaries = relationship("DepthSummary", back_populates="report", cascade="all, delete-orphan")
    timelines = relationship("Timeline", back_populates="report", cascade="all, delete-orphan")
    npt_events = relationship("NPTEvent", back_populates="report", cascade="all, delete-orphan")
    formation_tops = relationship("FormationTop", back_populates="report", cascade="all, delete-orphan")
    surveys = relationship("Survey", back_populates="report", cascade="all, delete-orphan")
    mud_data = relationship("MudData", back_populates="report", cascade="all, delete-orphan")
    mud_chemicals = relationship("MudChemical", back_populates="report", cascade="all, delete-orphan")
    drill_strings = relationship("DrillString", back_populates="report", cascade="all, delete-orphan")
    personnel = relationship("Personnel", back_populates="report", cascade="all, delete-orphan")
    bulk_logistics = relationship("BulkLogistics", back_populates="report", cascade="all, delete-orphan")
    hse_data = relationship("HSEData", back_populates="report", cascade="all, delete-orphan")
    foreman_remarks = relationship("ForemanRemark", back_populates="report", cascade="all, delete-orphan")
    extracted_metrics = relationship("ExtractedMetric", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ddr_reports_date", "report_date"),
        Index("idx_ddr_reports_rig_date", "rig_id", "report_date"),
    )


# ============================================================================
# 2. rigs
# ============================================================================

class DDRRig(Base):
    """Rig registry — one row per physical drilling rig."""
    __tablename__ = "ddr_rigs"

    id = Column(String, primary_key=True, default=_uuid)
    rig_name = Column(String, nullable=False, unique=True, index=True)
    rig_type = Column(String, nullable=True)
    contractor = Column(String, nullable=True)
    location = Column(String, nullable=True)
    status = Column(String, default="active", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reports = relationship("DDRReport", back_populates="rig")


# ============================================================================
# 3. depth_summary
# ============================================================================

class DepthSummary(Base):
    """Depth data per report — MD, TVD, hole depth, casing depth."""
    __tablename__ = "ddr_depth_summary"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    depth_md = Column(Float, nullable=True)
    depth_tvd = Column(Float, nullable=True)
    hole_depth = Column(Float, nullable=True)
    casing_depth = Column(Float, nullable=True)
    unit = Column(String, default="ft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="depth_summaries")


# ============================================================================
# 4. timeline
# ============================================================================

class Timeline(Base):
    """24-hour activity timeline entries for a report."""
    __tablename__ = "ddr_timeline"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(String, nullable=True)
    end_time = Column(String, nullable=True)
    duration_hours = Column(Float, nullable=True)
    activity_code = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    depth_from = Column(Float, nullable=True)
    depth_to = Column(Float, nullable=True)
    is_npt = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="timelines")


# ============================================================================
# 5. npt_events
# ============================================================================

class NPTEvent(Base):
    """Non-Productive Time events."""
    __tablename__ = "ddr_npt_events"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    npt_code = Column(String, nullable=True)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    duration_hours = Column(Float, nullable=True)
    cost_impact = Column(Float, nullable=True)
    root_cause = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="npt_events")

    __table_args__ = (
        Index("idx_npt_category", "category"),
    )


# ============================================================================
# 6. formation_tops
# ============================================================================

class FormationTop(Base):
    """Geological formation top markers."""
    __tablename__ = "ddr_formation_tops"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    formation_name = Column(String, nullable=False)
    depth_md = Column(Float, nullable=True)
    depth_tvd = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="formation_tops")


# ============================================================================
# 7. surveys
# ============================================================================

class Survey(Base):
    """Directional survey data points."""
    __tablename__ = "ddr_surveys"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    depth_md = Column(Float, nullable=True)
    inclination = Column(Float, nullable=True)
    azimuth = Column(Float, nullable=True)
    tvd = Column(Float, nullable=True)
    dog_leg_severity = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="surveys")


# ============================================================================
# 8. mud_data
# ============================================================================

class MudData(Base):
    """Drilling fluid properties per report."""
    __tablename__ = "ddr_mud_data"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    mud_type = Column(String, nullable=True)
    mud_weight = Column(Float, nullable=True)
    viscosity = Column(Float, nullable=True)
    plastic_viscosity = Column(Float, nullable=True)
    yield_point = Column(Float, nullable=True)
    gel_strength_10s = Column(Float, nullable=True)
    gel_strength_10m = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    fluid_loss = Column(Float, nullable=True)
    unit = Column(String, default="ppg")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="mud_data")


# ============================================================================
# 9. mud_chemicals
# ============================================================================

class MudChemical(Base):
    """Chemical additions to drilling fluid."""
    __tablename__ = "ddr_mud_chemicals"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    chemical_name = Column(String, nullable=False)
    quantity = Column(Float, nullable=True)
    unit = Column(String, default="sacks")
    purpose = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="mud_chemicals")


# ============================================================================
# 10. drill_string
# ============================================================================

class DrillString(Base):
    """Bottom Hole Assembly (BHA) / drill string components."""
    __tablename__ = "ddr_drill_string"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    component_name = Column(String, nullable=False)
    od = Column(Float, nullable=True)  # outer diameter
    id_val = Column(Float, nullable=True)  # inner diameter
    length = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    position = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="drill_strings")


# ============================================================================
# 11. personnel
# ============================================================================

class Personnel(Base):
    """Personnel on board for a report."""
    __tablename__ = "ddr_personnel"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=True)
    name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    count = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="personnel")


# ============================================================================
# 12. bulk_logistics
# ============================================================================

class BulkLogistics(Base):
    """Bulk material received / consumed / on-hand."""
    __tablename__ = "ddr_bulk_logistics"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    material = Column(String, nullable=False)
    received = Column(Float, default=0)
    consumed = Column(Float, default=0)
    on_hand = Column(Float, default=0)
    unit = Column(String, default="tons")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="bulk_logistics")


# ============================================================================
# 13. hse_data
# ============================================================================

class HSEData(Base):
    """Health, Safety, Environment data per report."""
    __tablename__ = "ddr_hse_data"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    lti = Column(Integer, default=0)  # Lost Time Injuries
    mto = Column(Integer, default=0)  # Medical Treatment Only
    first_aid = Column(Integer, default=0)
    near_miss = Column(Integer, default=0)
    safety_observations = Column(Integer, default=0)
    stop_cards = Column(Integer, default=0)
    drills_conducted = Column(String, nullable=True)
    permit_to_work = Column(Integer, default=0)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="hse_data")


# ============================================================================
# 14. foreman_remarks
# ============================================================================

class ForemanRemark(Base):
    """Foreman / supervisor daily remarks."""
    __tablename__ = "ddr_foreman_remarks"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    remark_text = Column(Text, nullable=False)
    author_role = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("DDRReport", back_populates="foreman_remarks")


# ============================================================================
# 15. kpi_audit  (append-only audit log — Citation System)
# ============================================================================

class KPIAudit(Base):
    """
    Append-only audit trail for every extracted/imputed metric value.

    Tracks value changes, source method, user/system origin.
    Rows are NEVER updated or deleted.
    """
    __tablename__ = "ddr_kpi_audit"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=True, index=True)
    metric_id = Column(String, ForeignKey("ddr_extracted_metrics.id", ondelete="SET NULL"), nullable=True, index=True)
    field_name = Column(String, nullable=False, index=True)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    change_reason = Column(String, nullable=True)
    source_method = Column(String, nullable=True)  # regex | ocr | llm | imputed | manual
    origin = Column(String, default="system")  # system | user:<email>
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_kpi_audit_report_field", "report_id", "field_name"),
    )


# ============================================================================
# Citation System — ExtractedMetric model
# ============================================================================

class ExtractedMetric(Base):
    """
    Every extracted DDR metric with full citation and provenance.

    Citation format: [RigID–Pg#–Section–Field]
    """
    __tablename__ = "ddr_extracted_metrics"

    id = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("ddr_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String, nullable=False, index=True)
    value = Column(String, nullable=True)
    numeric_value = Column(Float, nullable=True)

    # Citation & provenance
    citation = Column(String, nullable=True)  # [RIG-12–Pg3–MudData–MudWeight]
    extraction_method = Column(String, default="regex")  # regex | ocr | llm | imputed
    page_number = Column(Integer, nullable=True)
    page_hash = Column(String(64), nullable=True)  # SHA-256
    confidence_score = Column(Float, default=1.0)
    is_imputed = Column(Boolean, default=False)

    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    report = relationship("DDRReport", back_populates="extracted_metrics")

    __table_args__ = (
        Index("idx_extracted_metrics_report_field", "report_id", "field_name"),
        Index("idx_extracted_metrics_method", "extraction_method"),
    )
