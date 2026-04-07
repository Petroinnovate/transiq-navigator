"""SQLAlchemy model for persisting Six Sigma analysis results."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String

from services.db.session import Base


class SavedAnalysis(Base):
    """Persisted Six Sigma analysis."""

    __tablename__ = "saved_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    api_key_hash = Column(String(16), nullable=True, index=True)
    analysis_type = Column(String(50), default="process_capability", nullable=False)
    inputs = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=False)
    chart_data = Column(JSON, nullable=False)
    warnings = Column(JSON, nullable=False, default=list)
    recommendations = Column(JSON, nullable=False, default=list)
