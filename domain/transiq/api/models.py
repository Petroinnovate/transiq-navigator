"""
SQLAlchemy model for persisting Six Sigma analysis results.

NOTE: The actual ORM model lives in services.db.models (domain purity).
This module re-exports it for backward compatibility.
"""
from services.db.models import SavedAnalysis

__all__ = ["SavedAnalysis"]
