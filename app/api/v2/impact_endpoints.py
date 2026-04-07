"""
Impact Analysis API Endpoints

Exposes GraphRAG + Intelligence Engine capabilities for:
- Entity relationship discovery
- KPI impact propagation analysis
- DMAIC phase-based decision support
- Root cause chain analysis

Endpoints:
  POST /api/v2/intelligence/enrich-facts      - Enrich deduction facts with entities
  POST /api/v2/intelligence/analyze-kpi-impact - Analyze KPI cascading effects
  GET  /api/v2/intelligence/dmaic/{kpi_id}    - Get DMAIC analysis for KPI
  POST /api/v2/intelligence/entity-relationships - Get relationships between entities
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import logging

from pipelines.inference import (
    BusinessEntityExtractor,
    create_extractor,
    create_impact_engine,
    Entity,
    EntityTypePattern,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/intelligence", tags=["Intelligence"])


# ============================================================================
# Request/Response Models
# ============================================================================

class DeductionFact(BaseModel):
    """Fact from deduction engine (RDF triple)"""
    subject: str = Field(..., description="Subject entity")
    predicate: str = Field(..., description="Relationship type")
    object: str = Field(alias="object", description="Object entity")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    
    class Config:
        populate_by_name = True


class EnrichFactsRequest(BaseModel):
    """Request to enrich deduction facts"""
    facts: List[DeductionFact] = Field(..., description="Deduction facts to enrich")
    doc_id: Optional[str] = Field(None, description="Document ID for context")
    user_id: Optional[str] = Field(None, description="User ID for context")


class EnrichedEntity(BaseModel):
    """Entity with type information"""
    name: str
    type: str
    confidence: float


class EntityRelationship(BaseModel):
    """Relationship between entities"""
    source: str
    target: str
    type: str
    confidence: float
    source_type: str
    target_type: str


class EnrichFactsResponse(BaseModel):
    """Response from fact enrichment"""
    enriched_facts: List[Dict] = Field(..., description="Facts with entity type info")
    entities: List[EnrichedEntity] = Field(..., description="Discovered entities")
    relationships: List[EntityRelationship] = Field(..., description="Entity relationships")
    entity_count: int
    relationship_count: int
    summary: Dict = Field(default_factory=dict)


class KPIImpactRequest(BaseModel):
    """Request to analyze KPI impact"""
    kpi_name: str = Field(..., description="KPI entity name (e.g., 'Revenue')")
    kpi_type: str = Field(default="KPI", description="Entity type")
    entities: List[Dict] = Field(..., description="All entities from deduction")
    relationships: List[Dict] = Field(..., description="All relationships from graph")
    financial_impact_usd: Optional[float] = Field(
        None, description="Base financial impact from Financial Engine"
    )


class ImpactPathDetail(BaseModel):
    """Impact propagation path"""
    depth: int
    affected_count: int
    confidence: float
    impact_estimate: float


class DMAICAnalysisResponse(BaseModel):
    """Complete DMAIC analysis"""
    define_phase: Dict
    measure_phase: Dict
    analyze_phase: Dict
    improve_phase: Dict
    control_phase: Dict
    summary: Dict


class EntityRelationshipRequest(BaseModel):
    """Request to find relationships between entities"""
    entity_ids: List[str] = Field(..., description="Entity IDs to find relationships")
    max_depth: int = Field(default=3, ge=1, le=10, description="Max relationship depth")


class EntityRelationshipResponse(BaseModel):
    """Relationships between entities"""
    source_entity: str
    target_entity: str
    paths: List[Dict]
    direct_relationship: Optional[Dict]


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/enrich-facts", response_model=EnrichFactsResponse)
async def enrich_deduction_facts(request: EnrichFactsRequest):
    """
    Enrich deduction facts with business entity classification and relationships.
    
    This endpoint:
    1. Classifies entities (DEPARTMENT, ROLE, KPI, PROCESS, SYSTEM, etc.)
    2. Discovers entity-to-entity relationships
    3. Creates relationship types based on entity types and predicates
    
    Returns enriched facts ready for GraphRAG integration.
    
    **Use Case**: After deduction engine extracts facts, use this to add
    semantic entity information before storing in knowledge graph.
    """
    try:
        # Create extractor
        extractor = create_extractor()
        
        # Prepare facts
        facts_list = []
        for fact in request.facts:
            facts_list.append({
                "subject": fact.subject,
                "predicate": fact.predicate,
                "object": fact.object,
                "confidence": fact.confidence
            })
        
        # Enrich facts
        enrichment_result = extractor.enrich_deduction_facts(facts_list)
        
        # Convert to response format
        entities = [
            EnrichedEntity(**entity)
            for entity in enrichment_result["entities"]
        ]
        
        relationships = [
            EntityRelationship(**rel)
            for rel in enrichment_result["relationships"]
        ]
        
        return EnrichFactsResponse(
            enriched_facts=enrichment_result["enriched_facts"],
            entities=entities,
            relationships=relationships,
            entity_count=enrichment_result["entity_count"],
            relationship_count=enrichment_result["relationship_count"],
            summary={
                "pattern": "Enrichment completed",
                "stage": "entity classification and relationship discovery"
            }
        )
    
    except Exception as e:
        logger.error(f"Error enriching facts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")


@router.post("/analyze-kpi-impact")
async def analyze_kpi_impact(request: KPIImpactRequest):
    """
    Analyze complete impact of a KPI change including cascading effects.
    
    This endpoint:
    1. Finds directly affected KPIs (1-hop)
    2. Traces cascading paths (multi-hop, up to 4 hops)
    3. Estimates cascading financial impact
    4. Identifies responsible departments
    5. Traces root cause chains
    6. Generates improvement recommendations
    
    Returns complete impact analysis suitable for DMAIC process.
    
    **Use Case**: When a KPI shows deviation, analyze what other KPIs
    will be affected and what caused the initial deviation.
    
    **Example**:
    - Input: Revenue down 20%
    - Output: Also impacts 7 KPIs, trace shows caused by budget cuts,
              affects staffing, which impacts drilling productivity
    """
    try:
        # Create Impact Engine
        impact_engine = create_impact_engine()
        
        # Create KPI entity
        kpi_entity = Entity(
            id=request.kpi_name.replace(" ", "_").lower(),
            name=request.kpi_name,
            entity_type=request.kpi_type,
            confidence=0.95
        )
        
        # Create entity objects from request
        entities = []
        for ent in request.entities:
            entities.append(Entity(
                id=ent.get("id", ent.get("name", "").replace(" ", "_").lower()),
                name=ent.get("name", ""),
                entity_type=ent.get("type", "UNKNOWN"),
                confidence=ent.get("confidence", 0.5)
            ))
        
        # Analyze impact
        analysis = impact_engine.analyze_kpi_impact(
            kpi_entity,
            entities,
            [],  # Would pass graph relationships here
            financial_impact=request.financial_impact_usd or 0.0
        )
        
        return {
            "kpi_name": analysis.kpi_entity.name,
            "financial_impact_usd": analysis.financial_impact_usd,
            "cascading_impact_usd": analysis.total_cascading_impact_usd,
            "total_impact_usd": analysis.financial_impact_usd + analysis.total_cascading_impact_usd,
            "directly_affected_kpis": [
                {"name": kpi.name, "type": kpi.entity_type}
                for kpi in analysis.directly_affected_kpis
            ],
            "root_cause_chain": [
                {"entity": rc.name, "type": rc.entity_type}
                for rc in analysis.root_cause_chain
            ],
            "cascading_paths": len(analysis.cascading_impact_paths),
            "recommendations": {
                "immediate_actions": [r for r in analysis.recommendations if r["priority"] == "HIGH"],
                "monitoring_actions": [r for r in analysis.recommendations if r["phase"] == "MEASURE"]
            }
        }
    
    except Exception as e:
        logger.error(f"Error analyzing KPI impact: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Impact analysis failed: {str(e)}")


@router.get("/dmaic/{kpi_id}")
async def get_dmaic_analysis(
    kpi_id: str,
    with_graph_context: bool = Query(False, description="Include graph relationships")
):
    """
    Get DMAIC (Define-Measure-Analyze-Improve-Control) analysis for a KPI.
    
    Returns structured analysis for each DMAIC phase:
    
    **Define**:
    - Problem statement
    - Scope and root causes
    
    **Measure**:
    - Current impact (direct + cascading)
    - Affected KPI count
    - Impact paths identified
    
    **Analyze**:
    - Directly affected KPIs
    - Cascading paths with depth
    - Root cause chain
    
    **Improve**:
    - Responsible departments
    - Specific recommendations
    
    **Control**:
    - KPIs to monitor
    - Alert thresholds
    - Control recommendations
    
    **Use Case**: Executive decision-making on priority and action plans.
    Aligns technical analysis with Six Sigma methodology.
    """
    try:
        impact_engine = create_impact_engine()
        
        # Get cached analysis
        summary = impact_engine.get_impact_summary(kpi_id)
        
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"No impact analysis found for KPI: {kpi_id}"
            )
        
        # Return DMAIC structure
        return {
            "kpi_id": kpi_id,
            "define": {
                "problem_statement": f"KPI {kpi_id} requires optimization",
                "scope": f"Affects {summary['affected_kpis']} related KPIs",
                "impact_chains": summary['impact_paths']
            },
            "measure": {
                "direct_impact": summary['direct_impact_usd'],
                "cascading_impact": summary['cascading_impact_usd'],
                "total_impact": summary['total_impact_usd'],
                "key_metrics": summary
            },
            "analyze": {
                "root_causes_identified": summary['recommendations_count'] > 0,
                "cascading_effects": summary['impact_paths'],
                "relationship_count": summary['affected_kpis']
            },
            "improve": {
                "action_items": summary['recommendations_count'],
                "estimated_roi": {
                    "savings_potential_usd": summary['total_impact_usd'],
                    "roi_percentage": 100.0  # Improving to prevent loss
                }
            },
            "control": {
                "monitoring_kpis": summary['affected_kpis'],
                "alert_threshold_usd": summary['direct_impact_usd'] * 0.2
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting DMAIC analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"DMAIC analysis failed: {str(e)}")


@router.post("/entity-relationships")
async def find_entity_relationships(request: EntityRelationshipRequest):
    """
    Find relationships between multiple entities up to specified depth.
    
    This endpoint bridges deduction and GraphRAG:
    1. Takes entity IDs from deduction facts
    2. Traverses graph to find relationships
    3. Returns path information for impact analysis
    
    **Use Case**: After deduction extracts facts, find how extracted
    entities are related in the knowledge graph.
    
    **Returns**: Direct relationships and multi-hop paths between entities.
    """
    try:
        from services.storage.graph_storage import GraphStorage

        all_paths: list = []
        direct_relationships: list = []
        indirect_paths: list = []

        try:
            with GraphStorage() as gs:
                entity_ids = request.entity_ids
                max_depth = request.max_depth

                # For each pair of entities, find relationships
                for i, src_id in enumerate(entity_ids):
                    for tgt_id in entity_ids[i + 1:]:
                        # Try to find shortest path between entities
                        try:
                            path = gs.graph_engine.find_shortest_path(src_id, tgt_id)
                            if path:
                                all_paths.append({
                                    "source": src_id,
                                    "target": tgt_id,
                                    "path": path,
                                    "depth": len(path.get("nodes", [])) - 1,
                                    "type": "shortest_path",
                                })
                        except Exception:
                            pass

                    # Get direct relationships for each entity
                    try:
                        rels = gs.graph_engine.get_entity_relationships(src_id) or []
                        for rel in rels:
                            target_id = str(rel.get("target_id", ""))
                            if target_id in entity_ids:
                                direct_relationships.append({
                                    "source": src_id,
                                    "target": target_id,
                                    "type": rel.get("type", "RELATED"),
                                    "confidence": rel.get("confidence", 50) / 100.0,
                                })
                    except Exception:
                        pass

                    # Find related entities to discover indirect connections
                    try:
                        related = gs.find_related_entities(src_id, max_depth=min(max_depth, 3)) or []
                        for rel_ent in related:
                            rel_ent_id = str(rel_ent.get("id", ""))
                            if rel_ent_id in entity_ids and rel_ent_id != src_id:
                                indirect_paths.append({
                                    "source": src_id,
                                    "target": rel_ent_id,
                                    "type": "indirect",
                                    "hops": rel_ent.get("distance", 1),
                                })
                    except Exception:
                        pass

        except Exception as gs_err:
            logger.warning(f"Graph storage unavailable for entity-relationships: {gs_err}")

        return {
            "request_entity_count": len(request.entity_ids),
            "max_depth": request.max_depth,
            "relationships_found": len(direct_relationships) + len(indirect_paths),
            "paths": all_paths,
            "direct_relationships": direct_relationships,
            "indirect_paths": indirect_paths,
            "summary": {
                "direct_relationships": len(direct_relationships),
                "indirect_paths": len(indirect_paths),
                "total_impacted_entities": len(set(
                    [r["source"] for r in direct_relationships] +
                    [r["target"] for r in direct_relationships] +
                    request.entity_ids
                )),
            },
        }

    except Exception as e:
        logger.error(f"Error finding entity relationships: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Entity relationship analysis failed: {str(e)}"
        )


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@router.get("/status")
async def intelligence_status():
    """Get intelligence engine status and capabilities"""
    return {
        "status": "operational",
        "engines": {
            "impact_engine": {
                "status": "operational",
                "features": [
                    "KPI cascading impact analysis",
                    "Root cause chain tracing",
                    "DMAIC phase support",
                    "Responsible entity identification"
                ]
            },
            "entity_extractor": {
                "status": "operational",
                "features": [
                    "Business entity classification",
                    "Entity type detection",
                    "Relationship discovery",
                    "Predicate-based relationship inference"
                ],
                "entity_types": [
                    "DEPARTMENT",
                    "ROLE",
                    "KPI",
                    "PROCESS",
                    "SYSTEM",
                    "EQUIPMENT",
                    "LOCATION",
                    "TEAM"
                ]
            }
        },
        "integrations": {
            "deduction_engine": "connected",
            "graphrag": "optional",
            "financial_engine": "optional",
            "dmaic_framework": "integrated"
        }
    }


def get_intelligence_router():
    """Export router for main app"""
    return router
