"""
TransIQ Intelligence Layer
===========================
Multi-stage AI pipeline with validation, financial modeling, ESG, domain analytics, and impact analysis.

Modules:
  pipeline         - Multi-stage LLM pipeline (extraction → reasoning → decisions → assembly)
  financial_engine - Deterministic financial impact calculations (not LLM-dependent)
  validation       - KPI/recommendation validation and deduplication
  esg_engine       - ESG / sustainability scoring engine
  drilling_engine  - Drilling domain analytics (NPT, ROP, MTBF)
  impact_engine    - GraphRAG-integrated impact analysis & DMAIC support
"""

from app.intelligence.financial_engine import (
    compute_kpi_financial_scores,
    compute_financial_impact,
    compute_portfolio_summary,
    compute_recommendation_roi,
)
from app.intelligence.validation import (
    validate_kpis,
    validate_recommendations,
    validate_findings,
)
from app.intelligence.esg_engine import build_esg_view, compute_esg_scores
from app.intelligence.drilling_engine import build_drilling_view
from app.intelligence.impact_engine import (
    ImpactEngine,
    create_impact_engine,
    ImpactType,
    Entity,
    Relationship,
    ImpactPath,
    KPIImpactAnalysis,
)
from app.intelligence.deduction_enrichment import (
    BusinessEntityExtractor,
    create_extractor,
    EntityTypePattern,
)
from app.intelligence.pipeline import run_pipeline

# Phase 4: GraphRAG Deep Integration
from app.intelligence.graphrag_connector import (
    GraphRAGConnector,
    GraphAlgorithms,
    EntityDeduplicator,
    CacheManager,
    create_graphrag_connector,
)
from app.intelligence.real_data_provider import (
    RealDataProvider,
    AdvancedVisualization,
    create_real_data_provider,
)

__all__ = [
    "run_pipeline",
    "validate_kpis",
    "validate_recommendations",
    "validate_findings",
    "compute_kpi_financial_scores",
    "compute_financial_impact",
    "compute_portfolio_summary",
    "compute_recommendation_roi",
    "build_esg_view",
    "compute_esg_scores",
    "build_drilling_view",
    "ImpactEngine",
    "create_impact_engine",
    "ImpactType",
    "Entity",
    "Relationship",
    "ImpactPath",
    "KPIImpactAnalysis",
    "BusinessEntityExtractor",
    "create_extractor",
    "EntityTypePattern",
    # Phase 4: GraphRAG Deep Integration
    "GraphRAGConnector",
    "GraphAlgorithms",
    "EntityDeduplicator",
    "CacheManager",
    "create_graphrag_connector",
    "RealDataProvider",
    "AdvancedVisualization",
    "create_real_data_provider",
]


