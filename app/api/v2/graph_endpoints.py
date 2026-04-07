"""
GraphRAG API Endpoints (v2)
Graph-based entity and relationship queries
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel

from services.storage.graph_storage import GraphStorage
from pipelines.processing.graph_rag import GraphAnalytics
from app.config.security import verify_api_key
from core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v2/graph", tags=["GraphRAG"])

# ============================================================================
# Request/Response Models
# ============================================================================

class EntitySearchRequest(BaseModel):
    """Entity search request"""
    query: str
    entity_type: Optional[str] = None
    limit: int = 10


class RelationshipSearchRequest(BaseModel):
    """Relationship search request"""
    query: str
    limit: int = 10


class PathFindingRequest(BaseModel):
    """Path finding request"""
    source_entity_id: str
    target_entity_id: str
    max_depth: int = 5


class CentralityRequest(BaseModel):
    """Centrality analysis request"""
    metric: str = "degree"  # degree, closeness, betweenness
    limit: int = 20


class EntityFilterRequest(BaseModel):
    """Entity filter request"""
    entity_type: Optional[str] = None
    min_mentions: int = 1
    limit: int = 20


# ============================================================================
# Dependencies
# ============================================================================

async def get_graph_storage() -> GraphStorage:
    """Dependency: Get GraphStorage instance"""
    return GraphStorage()


# ============================================================================
# Entity Endpoints
# ============================================================================

@router.post("/entities/search")
async def search_entities(
    req: EntitySearchRequest,
    api_key: str = Depends(verify_api_key),
    graph: GraphStorage = Depends(get_graph_storage)
):
    """
    Search for entities by name
    
    Args:
        query: Search query (substring match)
        entity_type: Optional filter by entity type  
        limit: Maximum results
        
    Returns:
        List of matching entities
    """
    try:
        results = graph.search_entities(req.query, req.entity_type, req.limit)
        return {"query": req.query, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Entity search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")
    finally:
        graph.close()


@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    api_key: str = Depends(verify_api_key),
    graph: GraphStorage = Depends(get_graph_storage)
):
    """
    Get detailed entity profile
    
    Args:
        entity_id: Entity ID
        
    Returns:
        Entity profile with statistics and relationships
    """
    try:
        entity = graph.get_entity_profile(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Entity retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Retrieval failed")
    finally:
        graph.close()


@router.post("/entities/list")
async def list_entities(
    req: EntityFilterRequest,
    api_key: str = Depends(verify_api_key),
    graph: GraphStorage = Depends(get_graph_storage)
):
    """
    List entities with optional filtering
    
    Args:
        entity_type: Optional filter
        min_mentions: Minimum number of mentions
        limit: Maximum results
        
    Returns:
        List of entities
    """
    try:
        entities = graph.graph_engine.list_entities(req.entity_type, req.limit)
        
        # Filter by min mentions
        filtered = [
            {
                "id": e.id,
                "name": e.canonical_name,
                "type": e.entity_type,
                "mentions": e.mention_count,
                "confidence": e.total_confidence // e.mention_count if e.mention_count > 0 else 0
            }
            for e in entities
            if e.mention_count >= req.min_mentions
        ]
        
        return {"entities": filtered, "count": len(filtered)}
    except Exception as e:
        logger.error(f"Entity listing error: {e}")
        raise HTTPException(status_code=500, detail="Listing failed")
    finally:
        graph.close()


@router.get("/entities/{entity_id}/related")
async def get_related_entities(
    entity_id: str,
    max_depth: int = Query(2, ge=1, le=5),
    api_key: str = Depends(verify_api_key),
    graph: GraphStorage = Depends(get_graph_storage)
):
    """
    Find entities related to a given entity
    
    Args:
        entity_id: Entity ID
        max_depth: Maximum relationship hops
        
    Returns:
        List of related entities with paths
    """
    try:
        related = graph.find_related_entities(entity_id, max_depth)
        return {"entity_id": entity_id, "related": related, "count": len(related)}
    except Exception as e:
        logger.error(f"Related entities error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")
    finally:
        graph.close()


# ============================================================================
# Relationship Endpoints
# ============================================================================

@router.post("/relationships/search")
async def search_relationships(
    req: RelationshipSearchRequest,
    api_key: str = Depends(verify_api_key),
    graph: GraphStorage = Depends(get_graph_storage)
):
    """
    Search for relationships by type
    
    Args:
        query: Relationship type query (substring match)
        limit: Maximum results
        
    Returns:
        List of matching relationships
    """
    try:
        results = graph.search_relationships(req.query, req.limit)
        return {"query": req.query, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Relationship search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")
    finally:
        graph.close()


@router.get("/relationships/{entity_id}")
async def get_entity_relationships(
    entity_id: str,
    direction: str = Query("both", regex="^(both|outgoing|incoming)$"),
    rel_type: Optional[str] = None,
    api_key: str = Depends(verify_api_key),
    graph: GraphStorage = Depends(get_graph_storage)
):
    """
    Get relationships for an entity
    
    Args:
        entity_id: Entity ID
        direction: "incoming", "outgoing", or "both"
        rel_type: Optional filter by relationship type
        
    Returns:
        List of relationships
    """
    try:
        relationships = graph.graph_engine.get_relationships(
            entity_id, direction=direction, rel_type=rel_type
        )
        return {"entity_id": entity_id, "relationships": relationships, "count": len(relationships)}
    except Exception as e:
        logger.error(f"Relationship retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Retrieval failed")
    finally:
        graph.close()


@router.post("/relationships/list")
async def list_relationships(
    rel_type: Optional[str] = None,
    min_confidence: int = Query(0, ge=0, le=100),
    limit: int = 20,
    api_key: str = Depends(verify_api_key),
    graph: GraphStorage = Depends(get_graph_storage)
):
    """
    List all relationships with optional filtering
    
    Args:
        rel_type: Optional filter by type
        min_confidence: Minimum confidence threshold
        limit: Maximum results
        
    Returns:
        List of relationships
    """
    try:
        relationships = graph.graph_engine.list_relationships(rel_type, min_confidence, limit)
        return {"relationships": relationships, "count": len(relationships)}
    except Exception as e:
        logger.error(f"Relationship listing error: {e}")
        raise HTTPException(status_code=500, detail="Listing failed")
    finally:
        graph.close()


# ============================================================================
# Path Finding Endpoints
# ============================================================================

@router.post("/paths")
async def find_paths(
    req: PathFindingRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Find paths between two entities
    
    Args:
        source_entity_id: Source entity ID
        target_entity_id: Target entity ID
        max_depth: Maximum path length
        
    Returns:
        List of paths with entities and relationships
    """
    try:
        with GraphAnalytics() as analytics:
            paths = analytics.find_paths(
                req.source_entity_id,
                req.target_entity_id,
                req.max_depth
            )
        
        return {
            "source": req.source_entity_id,
            "target": req.target_entity_id,
            "paths": paths,
            "count": len(paths)
        }
    except Exception as e:
        logger.error(f"Path finding error: {e}")
        raise HTTPException(status_code=500, detail="Path finding failed")


@router.get("/paths/shortest")
async def get_shortest_path(
    source_entity_id: str = Query(...),
    target_entity_id: str = Query(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Find shortest path between two entities
    
    Args:
        source_entity_id: Source entity ID
        target_entity_id: Target entity ID
        
    Returns:
        Shortest path or null if no path exists
    """
    try:
        with GraphAnalytics() as analytics:
            path = analytics.shortest_path(source_entity_id, target_entity_id)
        
        if not path:
            return {"source": source_entity_id, "target": target_entity_id, "path": None}
        
        return {
            "source": source_entity_id,
            "target": target_entity_id,
            "path": path
        }
    except Exception as e:
        logger.error(f"Shortest path error: {e}")
        raise HTTPException(status_code=500, detail="Path finding failed")


@router.get("/entities/{entity_id}/neighbors")
async def get_common_neighbors(
    entity_id1: str = Query(...),
    entity_id2: str = Query(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Find entities that connect to both input entities
    
    Args:
        entity_id1: First entity
        entity_id2: Second entity
        
    Returns:
        List of common neighbor IDs
    """
    try:
        with GraphAnalytics() as analytics:
            neighbors = analytics.find_common_neighbors(entity_id1, entity_id2)
        
        return {
            "entity1": entity_id1,
            "entity2": entity_id2,
            "common_neighbors": neighbors,
            "count": len(neighbors)
        }
    except Exception as e:
        logger.error(f"Common neighbors error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.post("/analytics/centrality")
async def get_central_entities(
    req: CentralityRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Get most central entities
    
    Args:
        metric: Centrality metric (degree, closeness, betweenness)
        limit: Maximum results
        
    Returns:
        List of entities with centrality scores
    """
    try:
        with GraphAnalytics() as analytics:
            entities = analytics.get_top_central_entities(req.metric, req.limit)
        
        return {
            "metric": req.metric,
            "entities": entities,
            "count": len(entities)
        }
    except Exception as e:
        logger.error(f"Centrality analysis error: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")


@router.get("/analytics/summary")
async def get_graph_summary(
    api_key: str = Depends(verify_api_key),
    graph: GraphStorage = Depends(get_graph_storage)
):
    """
    Get overall graph summary and statistics
    
    Returns:
        Graph statistics, top entities, anomalies
    """
    try:
        summary = graph.get_graph_summary()
        return summary
    except Exception as e:
        logger.error(f"Summary retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Retrieval failed")
    finally:
        graph.close()


@router.get("/analytics/quality")
async def get_data_quality(
    api_key: str = Depends(verify_api_key),
    graph: GraphStorage = Depends(get_graph_storage)
):
    """
    Get data quality metrics
    
    Returns:
        Quality metrics (confidence distribution, duplicate rate, etc.)
    """
    try:
        quality = graph.get_data_quality_metrics()
        return quality
    except Exception as e:
        logger.error(f"Quality analysis error: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")
    finally:
        graph.close()


@router.get("/analytics/anomalies")
async def detect_anomalies(
    api_key: str = Depends(verify_api_key)
):
    """
    Detect anomalies in the graph
    
    Returns:
        List of detected anomalies
    """
    try:
        with GraphAnalytics() as analytics:
            anomalies = analytics.detect_anomalies()
        
        return {"anomalies": anomalies, "count": len(anomalies)}
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=500, detail="Detection failed")


@router.get("/analytics/impact/{entity_id}")
async def analyze_entity_impact(
    entity_id: str,
    api_key: str = Depends(verify_api_key),
    graph: GraphStorage = Depends(get_graph_storage)
):
    """
    Analyze impact of an entity on the graph
    
    Args:
        entity_id: Entity ID
        
    Returns:
        Impact analysis results
    """
    try:
        impact = graph.get_entity_impact(entity_id)
        return impact
    except Exception as e:
        logger.error(f"Impact analysis error: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")
    finally:
        graph.close()


# ============================================================================
# Maintenance Endpoints
# ============================================================================

@router.post("/maintenance/resolve-duplicates")
async def resolve_duplicates(
    threshold: float = Query(0.85, ge=0.0, le=1.0),
    api_key: str = Depends(verify_api_key),
    graph: GraphStorage = Depends(get_graph_storage)
):
    """
    Find and merge duplicate entities
    
    Args:
        threshold: Similarity threshold for merging
        
    Returns:
        Number of entities merged
    """
    try:
        merged = graph.find_and_merge_duplicates(threshold)
        return {"status": "success", "entities_merged": merged}
    except Exception as e:
        logger.error(f"Duplicate resolution error: {e}")
        raise HTTPException(status_code=500, detail="Resolution failed")
    finally:
        graph.close()
