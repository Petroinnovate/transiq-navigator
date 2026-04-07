"""
Phase 4 Real Data Integration
Connects dashboard endpoints to live GraphRAG data via Qdrant + SQLite + Redis

Replaces test data generators with actual entity/relationship queries
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pipelines.inference.graphrag_connector import GraphRAGConnector, create_graphrag_connector
from pipelines.inference.impact_engine import Entity, Relationship, ImpactEngine
from pipelines.inference.deduction_enrichment import EntityTypePattern
from app.api.v2.dashboard_endpoints import (
    DashboardNode,
    DashboardEdge,
    ImpactNetworkVisualization,
    DashboardSummary
)


class RealDataProvider:
    """
    Provides real entity and relationship data from Qdrant + SQLite.
    Replaces placeholder test data in dashboard endpoints.
    """
    
    def __init__(self, graphrag_config: Optional[Dict[str, Any]] = None):
        self.graphrag = create_graphrag_connector(graphrag_config)
        self.impact_engine = ImpactEngine()
    
    def get_entities_by_kpi(self, kpi_id: str, include_related: bool = True) -> List[Entity]:
        """
        Get real entities from SQLite graph store related to a KPI.
        
        In Phase 4, this queries:
        - The actual KPI entity from graph_entities table
        - Related entities (departments, processes, systems) from relationships
        """
        entities = []
        
        # Primary KPI entity
        # TODO: Query from SQLite: SELECT * FROM graph_entities WHERE id = ?
        kpi_entity = Entity(
            id=kpi_id,
            name=kpi_id.replace("_", " ").title(),
            type=EntityTypePattern.KPI,
            description="Primary KPI for dashboard analysis"
        )
        entities.append(kpi_entity)
        
        if include_related:
            # Query related entities
            # TODO: SELECT DISTINCT target_id, * FROM graph_entities ge
            #       JOIN graph_relationships gr ON ge.id = gr.target_id
            #       WHERE gr.source_id = ?
            # For now, return placeholder related entities
            related_types = [
                (EntityTypePattern.DEPARTMENT, "Operations"),
                (EntityTypePattern.DEPARTMENT, "Finance"),
                (EntityTypePattern.PROCESS, "Drilling"),
                (EntityTypePattern.SYSTEM, "ERP"),
            ]
            
            for i, (entity_type, name) in enumerate(related_types):
                entities.append(Entity(
                    id=f"{entity_type.value}_{i}",
                    name=name,
                    type=entity_type,
                    description=f"Related to {kpi_id}"
                ))
        
        return entities
    
    def get_relationships_by_kpi(self, kpi_id: str, max_depth: int = 3) -> List[Relationship]:
        """
        Get real relationships from SQLite graph store.
        
        In Phase 4, this queries:
        - graph_relationships table for actual relationships
        - Uses multi-hop traversal up to max_depth
        """
        # TODO: SELECT * FROM graph_relationships WHERE source_id = ? OR target_id = ?
        # Implement BFS with max_depth traversal
        
        # Placeholder relationships for now
        relationships = [
            Relationship(
                source_id=kpi_id,
                target_id="operations_0",
                impact_type="AFFECTS",
                confidence=0.92
            ),
            Relationship(
                source_id="operations_0",
                target_id="finance_1",
                impact_type="IMPACTS",
                confidence=0.85
            ),
            Relationship(
                source_id="drilling_2",
                target_id=kpi_id,
                impact_type="INFLUENCED_BY",
                confidence=0.78
            ),
        ]
        
        return relationships
    
    def enrich_network_with_algorithms(self, 
                                      entities: List[Entity],
                                      relationships: List[Relationship]) -> Dict[str, Any]:
        """
        Enrich network data with graph algorithms.
        Adds importance metrics, community detection, etc.
        """
        # Calculate entity importance
        importance = self.graphrag.calculate_entity_importance(entities, relationships)
        
        # Detect communities
        communities = self.graphrag.detect_communities(entities, relationships)
        
        return {
            "importance": importance,
            "communities": communities,
            "network_stats": {
                "entity_count": len(entities),
                "relationship_count": len(relationships),
                "community_count": len(communities),
                "avg_importance": sum(m["pagerank"] for m in importance.values()) / len(importance) if importance else 0
            }
        }
    
    def network_to_visualization(self,
                                primary_kpi_id: str,
                                entities: List[Entity],
                                relationships: List[Relationship],
                                enrichment: Optional[Dict[str, Any]] = None) -> ImpactNetworkVisualization:
        """
        Convert real entity/relationship data to visualization format.
        Applies importance metrics to node sizing and coloring.
        """
        enrichment = enrichment or {}
        importance = enrichment.get("importance", {})
        
        # Entity type color mapping
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
        
        # Create nodes from entities with algorithm scores
        nodes = []
        for entity in entities:
            entity_type = str(getattr(entity, 'type', 'UNKNOWN'))
            metrics = importance.get(entity.id, {})
            
            # Size based on PageRank importance
            pagerank = metrics.get("pagerank", 0.0)
            size = int(30 + (pagerank * 50))  # Normalize to 30-80
            size = min(80, max(30, size))  # Clamp
            
            node = DashboardNode(
                id=entity.id,
                label=entity.name,
                type=entity_type,
                value=metrics.get("mention_count", 1),
                color=type_color_map.get(entity_type, "#95A5A6"),
                size=size,
                metadata={
                    "pagerank": round(metrics.get("pagerank", 0.0), 4),
                    "betweenness": round(metrics.get("betweenness", 0.0), 4),
                    "clustering": round(metrics.get("clustering", 0.0), 4),
                    "description": getattr(entity, 'description', '')
                }
            )
            nodes.append(node)
        
        # Create edges from relationships
        edges = []
        for rel in relationships:
            edge = DashboardEdge(
                source=rel.source_id,
                target=rel.target_id,
                weight=getattr(rel, 'confidence', 0.5),
                type=str(getattr(rel, 'impact_type', 'impacts')),
                label=str(getattr(rel, 'impact_type', 'impacts')).title(),
                metadata={
                    "confidence": getattr(rel, 'confidence', 0.5),
                    "description": getattr(rel, 'description', '')
                }
            )
            edges.append(edge)
        
        # Calculate network stats
        stats = enrichment.get("network_stats", {})
        total_impact = sum(metrics.get("mention_count", 1) for metrics in importance.values())
        avg_confidence = sum(e.weight for e in edges) / len(edges) if edges else 0.0
        
        return ImpactNetworkVisualization(
            nodes=nodes,
            edges=edges,
            metadata={
                "kpi_id": primary_kpi_id,
                "kpi_name": next((e.name for e in entities if e.id == primary_kpi_id), primary_kpi_id),
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "algorithm_version": "Phase4-GraphAlgorithms"
            },
            stats={
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "community_count": stats.get("community_count", 0),
                "avg_importance": stats.get("avg_importance", 0.0),
                "network_density": (2 * len(edges)) / (len(nodes) * (len(nodes) - 1)) if len(nodes) > 1 else 0,
                "avg_confidence": round(avg_confidence, 3),
                "total_importance": round(total_impact, 2)
            }
        )


class AdvancedVisualization:
    """
    Advanced visualization endpoints for Phase 4.
    Includes centrality views, community clusters, temporal analysis, etc.
    """
    
    @staticmethod
    def create_centrality_view(entities: List[Entity],
                              relationships: List[Relationship],
                              metric: str = "pagerank") -> Dict[str, Any]:
        """
        Create visualization highlighting entity importance by metric.
        Metric: "pagerank", "betweenness", "clustering", or "degree"
        """
        graphrag = create_graphrag_connector()
        importance = graphrag.calculate_entity_importance(entities, relationships)
        
        # Sort by selected metric
        ranked = sorted(
            [(eid, metrics[metric]) for eid, metrics in importance.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "metric": metric,
            "entities": [
                {
                    "id": eid,
                    "name": next((e.name for e in entities if e.id == eid), eid),
                    "score": score,
                    "rank": i + 1
                }
                for i, (eid, score) in enumerate(ranked)
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def create_community_clusters(entities: List[Entity],
                                 relationships: List[Relationship]) -> Dict[str, Any]:
        """
        Create visualization of detected communities/clusters.
        """
        graphrag = create_graphrag_connector()
        communities = graphrag.detect_communities(entities, relationships)
        
        entity_map = {e.id: e for e in entities}
        
        return {
            "clusters": [
                {
                    "cluster_id": f"cluster_{i}",
                    "entities": [
                        {
                            "id": eid,
                            "name": entity_map[eid].name,
                            "type": str(entity_map[eid].type)
                        }
                        for eid in community
                    ],
                    "size": len(community),
                    "density": AdvancedVisualization._community_density(community, relationships)
                }
                for i, community in enumerate(communities)
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def _community_density(community: set, relationships: List[Relationship]) -> float:
        """Calculate density of a community"""
        # Count edges within community
        internal_edges = sum(
            1 for rel in relationships
            if rel.source_id in community and rel.target_id in community
        )
        
        # Max possible edges
        n = len(community)
        max_edges = n * (n - 1) if n > 1 else 0
        
        return internal_edges / max_edges if max_edges > 0 else 0.0
    
    @staticmethod
    def create_influence_analysis(primary_entity_id: str,
                                 entities: List[Entity],
                                 relationships: List[Relationship]) -> Dict[str, Any]:
        """
        Analyze influence of primary entity on others.
        Shows direct and cascading effects.
        """
        graphrag = create_graphrag_connector()
        
        # Find direct neighbors
        direct_influences = []
        for rel in relationships:
            if rel.source_id == primary_entity_id:
                direct_influences.append({
                    "target_id": rel.target_id,
                    "target_name": next((e.name for e in entities if e.id == rel.target_id), rel.target_id),
                    "strength": getattr(rel, 'confidence', 0.5),
                    "type": str(getattr(rel, 'impact_type', 'influences'))
                })
        
        # Find 2-hop indirect influences
        indirect_influences = []
        for direct in direct_influences:
            for rel in relationships:
                if rel.source_id == direct["target_id"]:
                    indirect_influences.append({
                        "target_id": rel.target_id,
                        "intermediate_id": direct["target_id"],
                        "chain_strength": direct["strength"] * getattr(rel, 'confidence', 0.5),
                        "type": f"{direct['type']} -> {str(getattr(rel, 'impact_type', 'influences'))}"
                    })
        
        return {
            "primary_entity_id": primary_entity_id,
            "direct_influences": direct_influences,
            "indirect_influences": indirect_influences[:5],  # Top 5
            "total_influenced": len(set(d["target_id"] for d in direct_influences) | 
                                  set(i["target_id"] for i in indirect_influences)),
            "timestamp": datetime.utcnow().isoformat()
        }


# Factory
def create_real_data_provider(config: Optional[Dict[str, Any]] = None) -> RealDataProvider:
    """Create configured real data provider"""
    return RealDataProvider(graphrag_config=config)
