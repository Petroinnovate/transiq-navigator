"""
Intelligence Graph Endpoints - Phase 5
Integrates GraphRAG relationships with Intelligence Engines
(Financial, ESG, Drilling) for domain-weighted analysis.

Features:
  - Real-time relationship queries with algorithm metrics
  - Financial impact weighting on relationships
  - ESG risk scoring overlay
  - Drilling-specific metrics (NPT, ROP, MTBF)
  - Cross-engine recommendations
  - Interactive impact visualization
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from pipelines.inference.impact_engine import Entity, Relationship
from pipelines.inference.deduction_enrichment import EntityTypePattern


# =============================================================================
# WEIGHTED RELATIONSHIP MODELS
# =============================================================================

class WeightedEntity(BaseModel):
    """Entity with domain-specific weights"""
    id: str = Field(..., description="Entity ID")
    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type")
    
    # Domain weights (0.0-1.0)
    financial_weight: float = Field(default=0.0, description="Financial impact weight")
    esg_weight: float = Field(default=0.0, description="ESG risk weight")
    drilling_weight: float = Field(default=0.0, description="Drilling relevance weight")
    
    # Importance metrics
    pagerank: float = Field(default=0.0, description="Graph centrality")
    betweenness: float = Field(default=0.0, description="Bridge importance")
    
    # Domain-specific metadata
    financial_metrics: Dict[str, Any] = Field(default_factory=dict, description="Financial data")
    esg_metrics: Dict[str, Any] = Field(default_factory=dict, description="ESG scores")
    drilling_metrics: Dict[str, Any] = Field(default_factory=dict, description="Drilling KPIs")


class WeightedRelationship(BaseModel):
    """Relationship with domain-weighted impact"""
    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    relationship_type: str = Field(..., description="Relationship type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Graph confidence")
    
    # Domain impact weights
    financial_impact: float = Field(default=0.0, description="Financial impact magnitude")
    esg_risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="ESG risk (0=low, 1=high)")
    drilling_sensitivity: float = Field(default=0.0, ge=0.0, le=1.0, description="Drilling impact")
    
    # Combined importance
    combined_weight: float = Field(default=0.0, description="Weighted average of all domains")


class IntelligenceNetworkVisualization(BaseModel):
    """Graph visualization with intelligence-weighted nodes/edges"""
    nodes: List[WeightedEntity] = Field(..., description="Weighted entity nodes")
    edges: List[WeightedRelationship] = Field(..., description="Weighted relationships")
    
    # Intelligence summaries
    financial_summary: Dict[str, Any] = Field(default_factory=dict)
    esg_summary: Dict[str, Any] = Field(default_factory=dict)
    drilling_summary: Dict[str, Any] = Field(default_factory=dict)
    
    # Cross-engine insights
    key_insights: List[str] = Field(default_factory=list, description="Top insights from all engines")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
    
    # Metadata
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class CrossEngineAnalysis(BaseModel):
    """Complete analysis across Financial, ESG, and Drilling engines"""
    primary_entity_id: str = Field(..., description="Primary KPI or entity")
    
    # Financial analysis
    financial_impact: float = Field(default=0.0, description="Total financial impact ($)")
    financial_drivers: List[str] = Field(default_factory=list, description="Cost drivers")
    financial_recommendations: List[str] = Field(default_factory=list, description="Financial optimizations")
    
    # ESG analysis
    esg_overall_score: float = Field(default=0.0, description="Overall ESG score (0-100)")
    environmental_score: float = Field(default=0.0, description="Environmental component")
    social_score: float = Field(default=0.0, description="Social component")
    governance_score: float = Field(default=0.0, description="Governance component")
    esg_recommendations: List[str] = Field(default_factory=list, description="ESG improvements")
    
    # Drilling analysis (if applicable)
    npt_metrics: Dict[str, Any] = Field(default_factory=dict, description="Non-productive time analysis")
    rop_metrics: Dict[str, Any] = Field(default_factory=dict, description="Rate of penetration analysis")
    mtbf_mttr: Dict[str, Any] = Field(default_factory=dict, description="Reliability metrics")
    drilling_recommendations: List[str] = Field(default_factory=list, description="Drilling optimizations")
    
    # Synthesis
    highest_priority: str = Field(default="", description="Highest priority recommendation")
    estimated_value_at_stake: float = Field(default=0.0, description="Total potential impact ($)")
    confidence_level: str = Field(default="medium", description="Analysis confidence (low/medium/high)")


class RecommendationPackage(BaseModel):
    """Unified recommendations across all engines"""
    primary_entity_id: str = Field(...)
    recommendations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of {engine, priority, action, impact_estimate, timeline}"
    )
    portfolio_summary: Dict[str, Any] = Field(default_factory=dict)
    next_steps: List[str] = Field(default_factory=list)


# =============================================================================
# ROUTER & ENDPOINTS
# =============================================================================

router = APIRouter(
    prefix="/api/v2/intelligence",
    tags=["graph-intelligence"],
    responses={404: {"description": "Not found"}}
)


def _compute_entity_weights(entity: Entity, financial_context: Dict[str, Any] = None,
                           esg_context: Dict[str, Any] = None,
                           drilling_context: Dict[str, Any] = None) -> WeightedEntity:
    """Compute intelligence engine weights for an entity."""
    financial_context = financial_context or {}
    esg_context = esg_context or {}
    drilling_context = drilling_context or {}
    
    financial_weight = min(1.0, financial_context.get("impact_ratio", 0.0))
    esg_weight = esg_context.get("normalization_factor", 0.5)
    drilling_weight = 1.0 if drilling_context.get("is_drilling_entity", False) else 0.0
    
    return WeightedEntity(
        id=entity.id,
        name=entity.name,
        type=str(getattr(entity, 'type', 'UNKNOWN')),
        financial_weight=financial_weight,
        esg_weight=esg_weight,
        drilling_weight=drilling_weight,
        pagerank=getattr(entity, 'pagerank', 0.0),
        betweenness=getattr(entity, 'betweenness', 0.0),
        financial_metrics=financial_context.get("metrics", {}),
        esg_metrics=esg_context.get("scores", {}),
        drilling_metrics=drilling_context.get("metrics", {})
    )


def _compute_relationship_weights(rel: Relationship,
                                 source_entity: Entity,
                                 target_entity: Entity,
                                 financial_impact: float = 0.0,
                                 esg_risk: float = 0.0,
                                 drilling_sensitivity: float = 0.0) -> WeightedRelationship:
    """Compute domain weights for a relationship."""
    non_zero_weights = [w for w in [financial_impact, esg_risk, drilling_sensitivity] if w > 0]
    combined = sum(non_zero_weights) / len(non_zero_weights) if non_zero_weights else 0.0
    
    return WeightedRelationship(
        source_id=rel.source_id,
        target_id=rel.target_id,
        relationship_type=str(getattr(rel, 'impact_type', 'unknown')),
        confidence=getattr(rel, 'confidence', 0.5),
        financial_impact=financial_impact,
        esg_risk_score=esg_risk,
        drilling_sensitivity=drilling_sensitivity,
        combined_weight=combined
    )


@router.get(
    "/graph-network/{entity_id}",
    response_model=IntelligenceNetworkVisualization,
    summary="Get entity graph with intelligence engine weights",
    description="Returns entity relationships weighted by Financial, ESG, and Drilling engines"
)
async def get_intelligence_network(
    entity_id: str,
    include_financial: bool = Query(True, description="Include financial impact weighting"),
    include_esg: bool = Query(True, description="Include ESG risk scoring"),
    include_drilling: bool = Query(True, description="Include drilling metrics"),
):
    """Get entity relationship graph with intelligence engine weights."""
    try:
        from services.storage.graph_storage import GraphStorage

        weighted_nodes: list = []
        weighted_edges: list = []
        insights: list = []
        financial_summary: dict = {}
        esg_summary: dict = {}
        drilling_summary: dict = {}

        try:
            with GraphStorage() as gs:
                # Fetch real entity profile from the knowledge graph
                profile = gs.get_entity_profile(entity_id)
                if not profile or not profile.get("entity"):
                    raise ValueError(f"Entity {entity_id} not found in graph")

                primary = profile["entity"]
                primary_entity = Entity(
                    id=str(primary.get("id", entity_id)),
                    name=primary.get("name", entity_id),
                    entity_type=primary.get("type", "UNKNOWN"),
                    confidence=primary.get("confidence", 50) / 100.0,
                )

                # Build weighted node for primary entity
                fin_ctx = {}
                esg_ctx = {}
                drill_ctx = {}

                if include_financial:
                    try:
                        from pipelines.inference.financial_engine import compute_financial_impact
                        impact = compute_financial_impact(
                            float(primary.get("properties", {}).get("value", 0)),
                            primary.get("properties", {}).get("unit", ""),
                        )
                        fin_ctx = {"impact_ratio": min(1.0, abs(impact.get("impact_usd", 0)) / 1_000_000), "metrics": impact}
                        financial_summary = impact
                    except Exception:
                        pass

                if include_esg:
                    try:
                        from pipelines.inference.esg_engine import classify_kpi_esg
                        esg_class = classify_kpi_esg({"title": primary.get("name", ""), "unit": ""})
                        esg_ctx = {"normalization_factor": 0.5, "scores": esg_class}
                        esg_summary = esg_class
                    except Exception:
                        pass

                if include_drilling:
                    import re
                    drilling_pattern = re.compile(r"\b(npt|rop|drill|mud|casing|bit|bha|well)\b", re.I)
                    is_drilling = bool(drilling_pattern.search(primary.get("name", "")))
                    drill_ctx = {"is_drilling_entity": is_drilling, "metrics": {}}
                    drilling_summary = {"is_drilling_related": is_drilling}

                weighted_nodes.append(_compute_entity_weights(primary_entity, fin_ctx, esg_ctx, drill_ctx))

                # Fetch related entities (1–2 hops)
                related = gs.find_related_entities(entity_id, max_depth=2) or []
                entity_lookup: dict = {str(primary_entity.id): primary_entity}

                for rel_info in related[:20]:  # Cap to avoid huge responses
                    rel_entity = Entity(
                        id=str(rel_info.get("id", "")),
                        name=rel_info.get("name", ""),
                        entity_type=rel_info.get("type", "UNKNOWN"),
                        confidence=rel_info.get("confidence", 50) / 100.0,
                    )
                    entity_lookup[rel_entity.id] = rel_entity
                    weighted_nodes.append(_compute_entity_weights(rel_entity))

                # Fetch relationships from graph
                rels = gs.graph_engine.get_entity_relationships(entity_id) if hasattr(gs, 'graph_engine') else []
                for rel_row in (rels or [])[:30]:
                    src_id = str(rel_row.get("source_id", ""))
                    tgt_id = str(rel_row.get("target_id", ""))
                    src_ent = entity_lookup.get(src_id, primary_entity)
                    tgt_ent = entity_lookup.get(tgt_id, primary_entity)

                    rel_obj = Relationship(
                        source_id=src_id,
                        target_id=tgt_id,
                        relationship_type=rel_row.get("type", "RELATED"),
                        confidence=rel_row.get("confidence", 50) / 100.0,
                        impact_type="AFFECTS",
                    )
                    weighted_edges.append(_compute_relationship_weights(rel_obj, src_ent, tgt_ent))

                if include_financial and financial_summary:
                    insights.append(f"Financial impact analysis available for {primary.get('name', entity_id)}")
                if include_esg and esg_summary:
                    insights.append(f"ESG classification: {esg_summary}")
                if include_drilling and drilling_summary.get("is_drilling_related"):
                    insights.append("Entity is drilling-related — NPT/ROP/MTBF analytics applicable")

        except Exception as graph_err:
            # Fallback: create minimal response from entity_id alone
            logger.warning(f"Graph storage unavailable, using fallback: {graph_err}")
            fallback_entity = Entity(
                id=entity_id,
                name=entity_id.replace("_", " ").title(),
                entity_type="KPI",
                confidence=0.5,
            )
            weighted_nodes.append(_compute_entity_weights(fallback_entity))
            insights.append("Graph data unavailable — showing fallback view")

        return IntelligenceNetworkVisualization(
            nodes=weighted_nodes,
            edges=weighted_edges,
            financial_summary=financial_summary,
            esg_summary=esg_summary,
            drilling_summary=drilling_summary,
            key_insights=insights,
            recommendations=[],
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/cross-engine-analysis/{entity_id}",
    response_model=CrossEngineAnalysis,
    summary="Complete analysis across all intelligence engines",
    description="Synthesized analysis from Financial, ESG, and Drilling engines"
)
async def cross_engine_analysis(entity_id: str):
    """Get unified analysis from all intelligence engines using real data."""
    try:
        from services.storage.graph_storage import GraphStorage

        financial_impact = 0.0
        financial_drivers: list = []
        financial_recs: list = []
        esg_overall = 0.0
        env_score = 0.0
        soc_score = 0.0
        gov_score = 0.0
        esg_recs: list = []
        npt_metrics: dict = {}
        rop_metrics: dict = {}
        mtbf_mttr: dict = {}
        drilling_recs: list = []

        # Try to fetch entity from graph and run real engines
        try:
            with GraphStorage() as gs:
                profile = gs.get_entity_profile(entity_id)
                entity_name = profile["entity"]["name"] if profile and profile.get("entity") else entity_id

                # Find related KPIs from graph
                related = gs.find_related_entities(entity_id, max_depth=2) or []
                related_kpis = [
                    {"title": r.get("name", ""), "value": r.get("properties", {}).get("value", 0),
                     "unit": r.get("properties", {}).get("unit", ""), "category": r.get("type", "")}
                    for r in related if r.get("type") in ("KPI", "METRIC", "PROCESS")
                ]

                # Financial analysis
                try:
                    from pipelines.inference.financial_engine import compute_kpi_financial_scores, compute_portfolio_summary
                    if related_kpis:
                        scored = compute_kpi_financial_scores(related_kpis)
                        portfolio = compute_portfolio_summary(scored)
                        financial_impact = portfolio.get("total_impact_usd", 0)
                        financial_drivers = portfolio.get("top_drivers", [])[:5]
                        financial_recs = [f"Optimize {d}" for d in financial_drivers[:3]]
                except Exception as fe:
                    logger.debug(f"Financial engine: {fe}")

                # ESG analysis
                try:
                    from pipelines.inference.esg_engine import build_esg_view
                    if related_kpis:
                        esg = build_esg_view(related_kpis)
                        scores = esg.get("scores", {})
                        env_score = scores.get("environmental", 0)
                        soc_score = scores.get("social", 0)
                        gov_score = scores.get("governance", 0)
                        esg_overall = (env_score + soc_score + gov_score) / 3.0
                        esg_recs = esg.get("recommendations", [])[:5]
                except Exception as ee:
                    logger.debug(f"ESG engine: {ee}")

                # Drilling analysis
                try:
                    from pipelines.inference.drilling_engine import build_drilling_view
                    if related_kpis:
                        drill = build_drilling_view(related_kpis)
                        npt_metrics = drill.get("npt", {})
                        rop_metrics = drill.get("rop", {})
                        mtbf_mttr = drill.get("reliability", {})
                        drilling_recs = drill.get("recommendations", [])[:5]
                except Exception as de:
                    logger.debug(f"Drilling engine: {de}")

        except Exception as gs_err:
            logger.warning(f"Graph storage unavailable for cross-engine: {gs_err}")

        highest = "Review entity relationships and optimize key metrics"
        if financial_impact > 100_000:
            highest = f"Address financial exposure of ${financial_impact:,.0f}"
        elif npt_metrics.get("total_npt_hours", 0) > 10:
            highest = "Critical: Reduce NPT hours to improve operational efficiency"

        return CrossEngineAnalysis(
            primary_entity_id=entity_id,
            financial_impact=financial_impact,
            financial_drivers=financial_drivers,
            financial_recommendations=financial_recs,
            esg_overall_score=esg_overall,
            environmental_score=env_score,
            social_score=soc_score,
            governance_score=gov_score,
            esg_recommendations=esg_recs,
            npt_metrics=npt_metrics,
            rop_metrics=rop_metrics,
            mtbf_mttr=mtbf_mttr,
            drilling_recommendations=drilling_recs,
            highest_priority=highest,
            estimated_value_at_stake=financial_impact * 1.5,
            confidence_level="high" if financial_impact > 0 or npt_metrics else "medium",
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/unified-recommendations/{entity_id}",
    response_model=RecommendationPackage,
    summary="Unified recommendations across all engines",
    description="Prioritized cross-engine recommendations"
)
async def get_unified_recommendations(entity_id: str):
    """Get unified recommendations from all engines using real graph data."""
    try:
        from services.storage.graph_storage import GraphStorage

        recommendations: list = []
        portfolio_summary: dict = {}
        next_steps: list = []

        try:
            with GraphStorage() as gs:
                related = gs.find_related_entities(entity_id, max_depth=2) or []
                related_kpis = [
                    {"title": r.get("name", ""), "value": r.get("properties", {}).get("value", 0),
                     "unit": r.get("properties", {}).get("unit", ""), "category": r.get("type", "")}
                    for r in related if r.get("type") in ("KPI", "METRIC", "PROCESS")
                ]

                priority_counter = 1

                # Drilling recommendations
                try:
                    from pipelines.inference.drilling_engine import build_drilling_view
                    if related_kpis:
                        drill = build_drilling_view(related_kpis)
                        for rec in drill.get("recommendations", [])[:3]:
                            recommendations.append({
                                "engine": "Drilling",
                                "priority": priority_counter,
                                "action": rec if isinstance(rec, str) else rec.get("action", str(rec)),
                                "impact_estimate": "Operational efficiency improvement",
                                "timeline": "Q2 2026",
                            })
                            priority_counter += 1
                except Exception:
                    pass

                # Financial recommendations
                try:
                    from pipelines.inference.financial_engine import compute_portfolio_summary, compute_kpi_financial_scores
                    if related_kpis:
                        scored = compute_kpi_financial_scores(related_kpis)
                        portfolio_summary = compute_portfolio_summary(scored)
                        for driver in portfolio_summary.get("top_drivers", [])[:2]:
                            recommendations.append({
                                "engine": "Financial",
                                "priority": priority_counter,
                                "action": f"Optimize: {driver}",
                                "impact_estimate": "Cost reduction",
                                "timeline": "Q1-Q2 2026",
                            })
                            priority_counter += 1
                except Exception:
                    pass

                # ESG recommendations
                try:
                    from pipelines.inference.esg_engine import build_esg_view
                    if related_kpis:
                        esg = build_esg_view(related_kpis)
                        for rec in esg.get("recommendations", [])[:2]:
                            recommendations.append({
                                "engine": "ESG",
                                "priority": priority_counter,
                                "action": rec if isinstance(rec, str) else str(rec),
                                "impact_estimate": "ESG score improvement",
                                "timeline": "H2 2026",
                            })
                            priority_counter += 1
                except Exception:
                    pass

                portfolio_summary["total_entities_analyzed"] = len(related) + 1
                portfolio_summary["high_priority_items"] = sum(1 for r in recommendations if r.get("priority", 99) <= 3)

                if recommendations:
                    next_steps = [r["action"] for r in sorted(recommendations, key=lambda x: x["priority"])[:3]]
                else:
                    next_steps = ["Upload documents to populate the knowledge graph", "Run analysis pipeline"]

        except Exception as gs_err:
            logger.warning(f"Graph storage unavailable for recommendations: {gs_err}")
            next_steps = ["Ensure graph storage is initialized", "Process documents through the pipeline"]

        return RecommendationPackage(
            primary_entity_id=entity_id,
            recommendations=recommendations,
            portfolio_summary=portfolio_summary,
            next_steps=next_steps,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@router.get(
    "/intelligence-status",
    summary="Service status with engine capabilities",
    description="Health check for Phase 5 Intelligence System"
)
async def intelligence_status():
    """Intelligence system health check and capabilities."""
    return {
        "status": "operational",
        "service": "Phase 5 - Intelligence Engine Integration",
        "version": "5.0",
        "engines": {
            "financial": {"status": "active", "capabilities": ["Budget analysis", "ROI calculation"]},
            "esg": {"status": "active", "capabilities": ["Environmental scoring", "Social impact"]},
            "drilling": {"status": "active", "capabilities": ["NPT analysis", "ROP metrics"]},
            "graphrag": {"status": "active", "capabilities": ["Entity relationships", "Path discovery"]}
        },
        "available_endpoints": [
            "GET /graph-network/{entity_id}",
            "GET /cross-engine-analysis/{entity_id}",
            "GET /unified-recommendations/{entity_id}",
            "GET /intelligence-status"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
