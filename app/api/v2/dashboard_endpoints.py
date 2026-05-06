"""
Dashboard visualization endpoints for impact analysis.
Provides graph-ready data structures for frontend visualization (D3, Cytoscape, etc).

Phase 3: Dashboard Integration - TransIQ Intelligence System
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from pipelines.inference.impact_engine import ImpactEngine, Entity, Relationship, ImpactPath, ImpactType
from pipelines.inference.deduction_enrichment import BusinessEntityExtractor, EntityTypePattern

# =============================================================================
# VISUALIZATION MODELS
# =============================================================================

class DashboardNode(BaseModel):
    """Graph node representation for visualization"""
    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Display label")
    type: str = Field(..., description="Entity type (DEPARTMENT, ROLE, KPI, etc)")
    value: float = Field(default=0.0, description="Metric value (impact amount, confidence, etc)")
    color: str = Field(default="#4A90E2", description="Node color hex code")
    size: int = Field(default=30, description="Node size for visualization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional node properties")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "kpi_001",
                "label": "Oil Price Impact",
                "type": "KPI",
                "value": 435000.0,
                "color": "#E74C3C",
                "size": 45,
                "metadata": {"units": "USD", "confidence": 0.92}
            }
        }


class DashboardEdge(BaseModel):
    """Graph edge representation for visualization"""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    weight: float = Field(default=1.0, description="Edge weight/confidence (0-1)")
    type: str = Field(default="impacts", description="Relationship type")
    label: str = Field(default="", description="Edge label for display")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional edge properties")

    class Config:
        json_schema_extra = {
            "example": {
                "source": "kpi_001",
                "target": "dept_002",
                "weight": 0.92,
                "type": "impacts",
                "label": "Direct Impact",
                "metadata": {"impact_amount": 435000.0}
            }
        }


class ImpactNetworkVisualization(BaseModel):
    """Complete graph structure for visualization"""
    nodes: List[DashboardNode] = Field(..., description="Graph nodes")
    edges: List[DashboardEdge] = Field(..., description="Graph edges")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Network-level metadata")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Network statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "nodes": [
                    {
                        "id": "kpi_001",
                        "label": "Oil Price Impact",
                        "type": "KPI",
                        "value": 435000.0,
                        "color": "#E74C3C"
                    }
                ],
                "edges": [
                    {
                        "source": "kpi_001",
                        "target": "dept_002",
                        "weight": 0.92
                    }
                ],
                "metadata": {
                    "kpi_id": "kpi_001",
                    "analysis_timestamp": "2026-03-27T14:30:00Z"
                },
                "stats": {
                    "total_nodes": 12,
                    "total_edges": 15,
                    "max_impact": 435000.0,
                    "avg_confidence": 0.87
                }
            }
        }


class DashboardSummary(BaseModel):
    """High-level impact summary for dashboard cards"""
    kpi_id: str = Field(..., description="Primary KPI identifier")
    kpi_name: str = Field(..., description="Human-readable KPI name")
    total_impact: float = Field(..., description="Total cascading impact amount")
    direct_impact: float = Field(..., description="Direct impact (1-hop)")
    cascading_impact: float = Field(..., description="Cascading impact (2+ hops)")
    affected_entities_count: int = Field(..., description="Number of affected entities")
    confidence_score: float = Field(..., description="Overall confidence (0-1)")
    primary_drivers: List[str] = Field(default_factory=list, description="Top 5 impact drivers")
    affected_departments: List[str] = Field(default_factory=list, description="Impacted departments")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Analysis timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "kpi_id": "kpi_001",
                "kpi_name": "Oil Price Per Barrel",
                "total_impact": 435000.0,
                "direct_impact": 360000.0,
                "cascading_impact": 75000.0,
                "affected_entities_count": 7,
                "confidence_score": 0.92,
                "primary_drivers": ["Operations Cost", "Revenue Impact", "Production Volume"],
                "affected_departments": ["Finance", "Operations", "Drilling"],
                "timestamp": "2026-03-27T14:30:00Z"
            }
        }


class DMAICPhaseVisualization(BaseModel):
    """DMAIC phase with visual formatting"""
    phase_name: str = Field(..., description="DMAIC phase (Define/Measure/Analyze/Improve/Control)")
    phase_number: int = Field(..., ge=1, le=5, description="Phase sequence (1-5)")
    description: str = Field(..., description="Phase description and findings")
    key_metrics: Dict[str, Any] = Field(default_factory=dict, description="Phase-specific metrics")
    actions: List[str] = Field(default_factory=list, description="Recommended actions")
    completion_percentage: int = Field(default=0, ge=0, le=100, description="Phase completion %")

    class Config:
        json_schema_extra = {
            "example": {
                "phase_name": "Define",
                "phase_number": 1,
                "description": "Problem identified: 24-hour NPT event caused $360K direct impact",
                "key_metrics": {
                    "problem_statements": 1,
                    "root_causes_identified": 3
                },
                "actions": [
                    "Document NPT event details",
                    "Identify affected operations"
                ],
                "completion_percentage": 100
            }
        }


class DMAICDashboard(BaseModel):
    """Complete DMAIC analysis for dashboard"""
    kpi_id: str = Field(..., description="Primary KPI")
    kpi_name: str = Field(..., description="Human-readable KPI name")
    phases: List[DMAICPhaseVisualization] = Field(..., description="All 5 DMAIC phases")
    overall_improvement_potential: float = Field(..., description="Estimated improvement potential")
    confidence_level: str = Field(..., description="Analysis confidence (Low/Medium/High)")
    timeline_weeks: int = Field(..., description="Estimated implementation timeline")

    class Config:
        json_schema_extra = {
            "example": {
                "kpi_id": "kpi_001",
                "kpi_name": "Oil Price Per Barrel",
                "phases": [
                    {
                        "phase_name": "Define",
                        "phase_number": 1,
                        "description": "24-hour NPT in West Africa",
                        "key_metrics": {},
                        "actions": [],
                        "completion_percentage": 100
                    }
                ],
                "overall_improvement_potential": 435000.0,
                "confidence_level": "High",
                "timeline_weeks": 4
            }
        }


class BatchAnalysisRequest(BaseModel):
    """Request for analyzing multiple KPIs"""
    kpi_ids: List[str] = Field(..., min_items=1, max_items=10, description="KPI IDs to analyze")
    include_network: bool = Field(default=False, description="Include impact network graphs")
    include_dmaic: bool = Field(default=False, description="Include DMAIC analysis")

    class Config:
        json_schema_extra = {
            "example": {
                "kpi_ids": ["kpi_001", "kpi_002", "kpi_003"],
                "include_network": True,
                "include_dmaic": False
            }
        }


class BatchAnalysisResponse(BaseModel):
    """Response for batch KPI analysis"""
    analyses: List[DashboardSummary] = Field(..., description="Individual KPI analyses")
    combined_impact: float = Field(..., description="Total combined impact across all KPIs")
    analysis_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    networks: Optional[List[ImpactNetworkVisualization]] = Field(default=None, description="Impact networks if requested")
    dmaic_dashboards: Optional[List[DMAICDashboard]] = Field(default=None, description="DMAIC analyses if requested")

    class Config:
        json_schema_extra = {
            "example": {
                "analyses": [],
                "combined_impact": 850000.0,
                "analysis_timestamp": "2026-03-27T14:30:00Z"
            }
        }


# =============================================================================
# ROUTER & ENDPOINTS
# =============================================================================

router = APIRouter(
    prefix="/api/v2/intelligence",
    tags=["dashboard"],
    responses={404: {"description": "Resource not found"}},
)


def _entity_to_dashboard_node(entity: Entity, impact_value: float = 0.0) -> DashboardNode:
    """Convert Entity to dashboard node"""
    type_color_map = {
        "DEPARTMENT": "#3498DB",      # Blue
        "ROLE": "#9B59B6",            # Purple
        "KPI": "#E74C3C",             # Red
        "PROCESS": "#F39C12",         # Orange
        "SYSTEM": "#16A085",          # Teal
        "EQUIPMENT": "#8E44AD",       # Deep Purple
        "LOCATION": "#2ECC71",        # Green
        "TEAM": "#E67E22",            # Dark Orange
    }
    
    entity_type = getattr(entity, 'type', 'UNKNOWN')
    color = type_color_map.get(str(entity_type), "#95A5A6")
    
    return DashboardNode(
        id=entity.id,
        label=entity.name,
        type=str(entity_type),
        value=impact_value,
        color=color,
        size=30 + int(min(impact_value / 10000, 40)),  # Size based on impact
        metadata={
            "description": getattr(entity, 'description', ''),
            "impact_amount": impact_value,
            "confidence": getattr(entity, 'confidence', 0.5)
        }
    )


def _create_impact_network_visualization(
    primary_entity: Entity,
    entities: List[Entity],
    relationships: List[Relationship],
    impact_paths: List[ImpactPath],
) -> ImpactNetworkVisualization:
    """Create visualization-ready impact network"""
    
    # Create nodes (one per entity)
    nodes_by_id = {}
    for entity in entities:
        impact = sum(
            path.total_impact
            for path in impact_paths
            if path.source_id == entity.id or path.target_id == entity.id
        )
        node = _entity_to_dashboard_node(entity, impact)
        nodes_by_id[entity.id] = node
    
    # Create edges from relationships
    edges = []
    for rel in relationships:
        weight = getattr(rel, 'confidence', 0.5)
        edge = DashboardEdge(
            source=rel.source_id,
            target=rel.target_id,
            weight=weight,
            type=str(getattr(rel, 'impact_type', 'impacts')),
            label=str(getattr(rel, 'impact_type', 'impacts')).title(),
            metadata={
                "confidence": weight,
                "description": getattr(rel, 'description', '')
            }
        )
        edges.append(edge)
    
    # Calculate statistics
    total_impact = sum(path.total_impact for path in impact_paths)
    avg_confidence = (
        sum(path.confidence for path in impact_paths) / len(impact_paths)
        if impact_paths else 0.0
    )
    
    return ImpactNetworkVisualization(
        nodes=list(nodes_by_id.values()),
        edges=edges,
        metadata={
            "kpi_id": primary_entity.id,
            "kpi_name": primary_entity.name,
            "analysis_timestamp": datetime.utcnow().isoformat()
        },
        stats={
            "total_nodes": len(nodes_by_id),
            "total_edges": len(edges),
            "max_impact": max((path.total_impact for path in impact_paths), default=0.0),
            "avg_confidence": round(avg_confidence, 3),
            "total_impact": round(total_impact, 2)
        }
    )


def _create_dashboard_summary(
    primary_entity: Entity,
    impact_analysis: Any,  # KPIImpactAnalysis from impact_engine
) -> DashboardSummary:
    """Create dashboard summary from impact analysis"""
    
    # Extract metrics from impact analysis
    total_impact = getattr(impact_analysis, 'total_impact', 0.0)
    direct_impact = sum(
        p.total_impact
        for p in getattr(impact_analysis, 'directly_affected_entities', [])
    )
    cascading_impact = total_impact - direct_impact
    
    affected_entities = list(set(
        [p.target_id for p in getattr(impact_analysis, 'directly_affected_entities', [])] +
        [p.target_id for p in getattr(impact_analysis, 'cascading_impact_paths', [])]
    ))
    
    # Extract top drivers
    all_paths = (
        getattr(impact_analysis, 'directly_affected_entities', []) +
        getattr(impact_analysis, 'cascading_impact_paths', [])
    )
    top_drivers = list(set(
        p.target_name for p in all_paths[:5]
    ))
    
    # Extract affected departments
    responsible = getattr(impact_analysis, 'responsible_entities', [])
    affected_depts = list(set(
        r.name for r in responsible
        if getattr(r, 'type', '') == 'DEPARTMENT'
    ))
    
    confidence = (
        sum(p.confidence for p in all_paths) / len(all_paths)
        if all_paths else 0.5
    )
    
    return DashboardSummary(
        kpi_id=primary_entity.id,
        kpi_name=primary_entity.name,
        total_impact=round(total_impact, 2),
        direct_impact=round(direct_impact, 2),
        cascading_impact=round(cascading_impact, 2),
        affected_entities_count=len(affected_entities),
        confidence_score=round(confidence, 3),
        primary_drivers=top_drivers,
        affected_departments=affected_depts,
        timestamp=datetime.utcnow().isoformat()
    )


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get(
    "/dashboard/{kpi_id}",
    response_model=DashboardSummary,
    summary="Get KPI impact summary for dashboard",
    description="Returns high-level impact summary suitable for dashboard card display"
)
async def get_kpi_dashboard(kpi_id: str):
    """
    Get dashboard summary for a KPI.
    
    Returns:
    - Total and cascading impact amounts
    - Affected entity count and confidence
    - Primary impact drivers
    - Affected departments
    """
    try:
        engine = ImpactEngine()
        
        # Create a KPI entity (in real system, fetch from database)
        kpi_entity = Entity(
            id=kpi_id,
            name=kpi_id.replace("_", " ").title(),
            entity_type="KPI",
            confidence=0.95
        )
        
        # Perform impact analysis
        impact_analysis = engine.analyze_kpi_impact(
            kpi_entity=kpi_entity,
            entities=[kpi_entity],
            relationships=[]
        )
        
        # Convert to dashboard summary
        summary = _create_dashboard_summary(kpi_entity, impact_analysis)
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/impact-network/{kpi_id}",
    response_model=ImpactNetworkVisualization,
    summary="Get impact network for visualization",
    description="Returns nodes and edges formatted for D3.js, Cytoscape, or similar graph visualization"
)
async def get_impact_network(
    kpi_id: str,
    max_depth: int = Query(default=3, ge=1, le=5, description="Maximum relationship depth")
):
    """
    Get impact network graph for visualization.
    
    Returns:
    - Nodes: Entities with impact values and colors by type
    - Edges: Relationships with confidence weights
    - Metadata: Network-level stats and timestamps
    
    Perfect for D3.js, Cytoscape.js, or similar graph libraries.
    """
    try:
        engine = ImpactEngine()
        
        # Create primary KPI entity
        kpi_entity = Entity(
            id=kpi_id,
            name=kpi_id.replace("_", " ").title(),
            entity_type="KPI",
            confidence=0.95
        )
        
        # Build test entities for visualization
        test_entities = [kpi_entity]
        test_relationships = []
        
        for i in range(3):
            dept = Entity(
                id=f"dept_{i}",
                name=f"Department {i}",
                entity_type="DEPARTMENT",
                confidence=0.9
            )
            test_entities.append(dept)
            
            rel = Relationship(
                source_id=kpi_id,
                target_id=f"dept_{i}",
                relationship_type="AFFECTS",
                confidence=0.8 + (i * 0.05),
                impact_type=ImpactType.DIRECT
            )
            test_relationships.append(rel)
        
        # Perform impact analysis
        impact_analysis = engine.analyze_kpi_impact(
            kpi_entity=kpi_entity,
            entities=test_entities,
            relationships=test_relationships
        )
        
        # Get impact paths
        impact_paths = (
            getattr(impact_analysis, 'directly_affected_entities', []) +
            getattr(impact_analysis, 'cascading_impact_paths', [])
        )
        
        # Create visualization
        network = _create_impact_network_visualization(
            kpi_entity,
            test_entities,
            test_relationships,
            impact_paths
        )
        
        return network
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/dmaic-dashboard/{kpi_id}",
    response_model=DMAICDashboard,
    summary="Get DMAIC analysis for dashboard",
    description="Returns all 5 DMAIC phases with metrics and recommended actions"
)
async def get_dmaic_dashboard(kpi_id: str):
    """
    Get DMAIC Six Sigma analysis formatted for dashboard display.
    
    Returns all 5 phases (Define, Measure, Analyze, Improve, Control) with:
    - Phase descriptions
    - Key metrics
    - Recommended actions
    - Completion percentages
    """
    try:
        engine = ImpactEngine()
        
        kpi_entity = Entity(
            id=kpi_id,
            name=kpi_id.replace("_", " ").title(),
            entity_type="KPI",
            confidence=0.95
        )
        
        # Get DMAIC analysis
        dmaic_result = engine.dmaic_analysis(
            primary_kpi=kpi_entity,
            entities=[kpi_entity],
            relationships=[],
            kpi_data={}
        )
        
        # Convert phases to visualization format
        phases_viz = []
        phase_names = ["Define", "Measure", "Analyze", "Improve", "Control"]
        
        for i, (phase_name, phase_data) in enumerate(dmaic_result.items(), 1):
            phase_viz = DMAICPhaseVisualization(
                phase_name=phase_name,
                phase_number=i,
                description=phase_data.get("description", ""),
                key_metrics=phase_data.get("metrics", {}),
                actions=phase_data.get("actions", []),
                completion_percentage=100 if i <= 2 else 0  # Simulate partial completion
            )
            phases_viz.append(phase_viz)
        
        # Calculate improvement potential
        improvement = dmaic_result.get("Measure", {}).get("metrics", {}).get("total_impact", 0.0)
        
        dashboard = DMAICDashboard(
            kpi_id=kpi_id,
            kpi_name=kpi_entity.name,
            phases=phases_viz,
            overall_improvement_potential=improvement,
            confidence_level="High",
            timeline_weeks=4
        )
        
        return dashboard
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/batch-analysis",
    response_model=BatchAnalysisResponse,
    summary="Analyze multiple KPIs together",
    description="Performs impact analysis on multiple KPIs and optionally returns combined networks"
)
async def batch_analyze_kpis(request: BatchAnalysisRequest):
    """
    Analyze multiple KPIs in a single request.
    
    Useful for:
    - Portfolio-level impact assessment
    - Cross-functional impact analysis
    - Decision support for executive dashboards
    
    Query Parameters:
    - include_network: Return graph visualizations for each KPI
    - include_dmaic: Include full DMAIC analysis
    """
    try:
        engine = ImpactEngine()
        
        analyses = []
        networks = [] if request.include_network else None
        dmaic_dashboards = [] if request.include_dmaic else None
        combined_impact = 0.0
        
        for kpi_id in request.kpi_ids:
            # Create KPI entity
            kpi_entity = Entity(
                id=kpi_id,
                name=kpi_id.replace("_", " ").title(),
                entity_type="KPI",
                confidence=0.95
            )
            
            # Analyze
            impact_analysis = engine.analyze_kpi_impact(
                kpi_entity=kpi_entity,
                entities=[kpi_entity],
                relationships=[]
            )
            
            # Create summary
            summary = _create_dashboard_summary(kpi_entity, impact_analysis)
            analyses.append(summary)
            combined_impact += summary.total_impact
            
            # Add network if requested
            if request.include_network:
                impact_paths = (
                    getattr(impact_analysis, 'directly_affected_entities', []) +
                    getattr(impact_analysis, 'cascading_impact_paths', [])
                )
                network = _create_impact_network_visualization(
                    kpi_entity,
                    [kpi_entity],
                    [],
                    impact_paths
                )
                networks.append(network)
            
            # Add DMAIC if requested
            if request.include_dmaic:
                dmaic_result = engine.dmaic_analysis(
                    primary_kpi=kpi_entity,
                    entities=[kpi_entity],
                    relationships=[],
                    kpi_data={}
                )
                phases_viz = []
                for i, (phase_name, phase_data) in enumerate(dmaic_result.items(), 1):
                    phase_viz = DMAICPhaseVisualization(
                        phase_name=phase_name,
                        phase_number=i,
                        description=phase_data.get("description", ""),
                        key_metrics=phase_data.get("metrics", {}),
                        actions=phase_data.get("actions", [])
                    )
                    phases_viz.append(phase_viz)
                
                dmaic_dashboard = DMAICDashboard(
                    kpi_id=kpi_id,
                    kpi_name=kpi_entity.name,
                    phases=phases_viz,
                    overall_improvement_potential=summary.total_impact,
                    confidence_level="High",
                    timeline_weeks=4
                )
                dmaic_dashboards.append(dmaic_dashboard)
        
        return BatchAnalysisResponse(
            analyses=analyses,
            combined_impact=round(combined_impact, 2),
            networks=networks,
            dmaic_dashboards=dmaic_dashboards
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/dashboard-status",
    summary="Health check with dashboard capabilities",
    description="Returns service status and available dashboard features"
)
async def dashboard_status():
    """
    Health check endpoint for dashboard service.
    
    Returns:
    - Service status
    - Available endpoints
    - Supported visualization types
    - Max analysis batch size
    """
    return {
        "status": "operational",
        "service": "Dashboard Intelligence System",
        "version": "3.0",
        "capabilities": {
            "endpoints": [
                "GET /dashboard/{kpi_id}",
                "GET /impact-network/{kpi_id}",
                "GET /dmaic/{kpi_id}",
                "POST /batch-analysis",
            ],
            "visualization_types": [
                "Force-directed graphs (D3.js, Cytoscape)",
                "Summary cards with KPIs",
                "DMAIC process flows",
                "Batch analysis dashboards"
            ],
            "max_batch_size": 10,
            "supported_depths": [1, 2, 3, 4, 5]
        },
        "last_startup": datetime.utcnow().isoformat(),
        "ready_for_dashboard": True
    }
