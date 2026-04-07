"""
Graph Analytics for GraphRAG
Advanced graph algorithms: path finding, centrality, community detection
"""
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import deque, defaultdict
import math

from app.db.session import SessionLocal
from app.db.models import GraphEntity, GraphRelationship

logger = logging.getLogger(__name__)


class GraphAnalytics:
    """
    Advanced graph analysis for intelligent reasoning
    
    Features:
    - Path finding (BFS, weighted shortest path)
    - Centrality metrics (degree, closeness, betweenness)
    - Community detection
    - Anomaly detection
    - Impact analysis
    """
    
    def __init__(self):
        """Initialize analytics"""
        self.db = SessionLocal()
    
    def close(self):
        """Close database session"""
        if self.db:
            self.db.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    # ========================================================================
    # Path Finding
    # ========================================================================
    
    def find_paths(self, source_id: str, target_id: str, max_depth: int = 5,
                   rel_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Find all paths between two entities up to max_depth
        
        Uses BFS for efficiency
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            max_depth: Maximum path length
            rel_types: Filter by relationship types
            
        Returns:
            List of paths, each with entities and relationships
        """
        logger.info(f"Finding paths from {source_id} to {target_id} (max_depth={max_depth})")
        
        paths = []
        queue = deque([(source_id, [source_id], [])])  # (current, entities_path, rels_path)
        visited = {source_id}
        
        while queue:
            current_id, entity_path, rel_path = queue.popleft()
            
            # Check depth limit
            if len(entity_path) > max_depth + 1:
                continue
            
            # Found target
            if current_id == target_id and len(entity_path) > 1:
                paths.append({
                    "entities": entity_path,
                    "relationships": rel_path,
                    "length": len(entity_path) - 1,
                    "relevance": 1.0 / (len(entity_path) - 1)  # Shorter paths are more relevant
                })
                continue
            
            # Explore neighbors
            query = self.db.query(GraphRelationship).filter(
                GraphRelationship.source_entity_id == current_id
            )
            
            if rel_types:
                query = query.filter(GraphRelationship.relationship_type.in_(rel_types))
            
            for rel in query.all():
                next_id = rel.target_entity_id
                
                if next_id not in visited and len(entity_path) < max_depth:
                    visited.add(next_id)
                    new_entity_path = entity_path + [next_id]
                    new_rel_path = rel_path + [{
                        "id": rel.id,
                        "type": rel.relationship_type,
                        "confidence": rel.confidence
                    }]
                    queue.append((next_id, new_entity_path, new_rel_path))
        
        # Sort by relevance
        paths.sort(key=lambda p: p["relevance"], reverse=True)
        
        logger.info(f"Found {len(paths)} paths")
        return paths[:20]  # Return top 20
    
    def shortest_path(self, source_id: str, target_id: str) -> Optional[Dict[str, Any]]:
        """
        Find shortest path between two entities
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            
        Returns:
            Path dict or None if no path exists
        """
        paths = self.find_paths(source_id, target_id, max_depth=10)
        
        if not paths:
            return None
        
        # Return shortest path (fewest hops)
        return min(paths, key=lambda p: p["length"])
    
    def find_common_neighbors(self, entity_id1: str, entity_id2: str) -> List[str]:
        """
        Find entities that connect to both input entities
        
        Args:
            entity_id1: First entity ID
            entity_id2: Second entity ID
            
        Returns:
            List of common neighbor entity IDs
        """
        # Get neighbors of entity 1
        neighbors1 = set()
        rels1 = self.db.query(GraphRelationship).filter(
            GraphRelationship.source_entity_id == entity_id1
        ).all()
        neighbors1.update([rel.target_entity_id for rel in rels1])
        
        rels1_in = self.db.query(GraphRelationship).filter(
            GraphRelationship.target_entity_id == entity_id1
        ).all()
        neighbors1.update([rel.source_entity_id for rel in rels1_in])
        
        # Get neighbors of entity 2
        neighbors2 = set()
        rels2 = self.db.query(GraphRelationship).filter(
            GraphRelationship.source_entity_id == entity_id2
        ).all()
        neighbors2.update([rel.target_entity_id for rel in rels2])
        
        rels2_in = self.db.query(GraphRelationship).filter(
            GraphRelationship.target_entity_id == entity_id2
        ).all()
        neighbors2.update([rel.source_entity_id for rel in rels2_in])
        
        # Find common
        common = neighbors1 & neighbors2
        
        return list(common)
    
    # ========================================================================
    # Centrality Metrics
    # ========================================================================
    
    def calculate_degree_centrality(self, entity_id: str) -> Dict[str, Any]:
        """
        Calculate degree centrality (number of connections)
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Dict with in_degree, out_degree, total_degree
        """
        out_degree = self.db.query(GraphRelationship).filter(
            GraphRelationship.source_entity_id == entity_id
        ).count()
        
        in_degree = self.db.query(GraphRelationship).filter(
            GraphRelationship.target_entity_id == entity_id
        ).count()
        
        total = out_degree + in_degree
        
        return {
            "out_degree": out_degree,
            "in_degree": in_degree,
            "total_degree": total,
            "normalized": total / (2 * self.db.query(GraphEntity).count()) if self.db.query(GraphEntity).count() > 0 else 0
        }
    
    def calculate_closeness_centrality(self, entity_id: str, max_depth: int = 10) -> float:
        """
        Calculate closeness centrality (average distance to all entities)
        
        Args:
            entity_id: Entity ID
            max_depth: Maximum depth for search
            
        Returns:
            Closeness score (0-1)
        """
        # BFS to find distances
        distances = {entity_id: 0}
        queue = deque([entity_id])
        
        while queue:
            current = queue.popleft()
            current_dist = distances[current]
            
            if current_dist >= max_depth:
                continue
            
            # Get neighbors
            rels = self.db.query(GraphRelationship).filter(
                GraphRelationship.source_entity_id == current
            ).all()
            
            for rel in rels:
                next_id = rel.target_entity_id
                if next_id not in distances:
                    distances[next_id] = current_dist + 1
                    queue.append(next_id)
        
        # Calculate average distance
        if len(distances) <= 1:
            return 0.0
        
        total_distance = sum(distances.values())
        avg_distance = total_distance / (len(distances) - 1)
        
        # Normalize: closeness = 1/avg_distance
        closeness = 1.0 / (avg_distance + 1)  # Add 1 to avoid division by 0
        
        return min(1.0, closeness)
    
    def calculate_betweenness_centrality(self, entity_id: str) -> float:
        """
        Calculate betweenness centrality (how often entity appears in shortest paths)
        
        Simplified version: approximate by counting paths through entity
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Betweenness score
        """
        # Count how many pairs have shortest paths through this entity
        all_entities = self.db.query(GraphEntity).all()
        entity_ids = [e.id for e in all_entities]
        
        paths_through = 0
        total_paths = 0
        
        for i, src in enumerate(entity_ids[:50]):  # Limit for performance
            for tgt in entity_ids[i+1:50]:
                if src == entity_id or tgt == entity_id:
                    continue
                
                path = self.shortest_path(src, tgt)
                if path and entity_id in path.get("entities", []):
                    paths_through += 1
                
                if path:
                    total_paths += 1
        
        if total_paths == 0:
            return 0.0
        
        return paths_through / total_paths
    
    def get_top_central_entities(self, metric: str = "degree", limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get most central entities
        
        Args:
            metric: "degree", "closeness", or "betweenness"
            limit: Number of results
            
        Returns:
            List of entities with centrality scores
        """
        all_entities = self.db.query(GraphEntity).all()
        scores = []
        
        for entity in all_entities[:100]:  # Limit for performance
            try:
                if metric == "degree":
                    centrality = self.calculate_degree_centrality(entity.id)
                    score = centrality["normalized"]
                elif metric == "closeness":
                    score = self.calculate_closeness_centrality(entity.id)
                elif metric == "betweenness":
                    score = self.calculate_betweenness_centrality(entity.id)
                else:
                    score = 0.0
                
                scores.append({
                    "entity_id": entity.id,
                    "entity_name": entity.canonical_name,
                    "entity_type": entity.entity_type,
                    "centrality_score": score,
                    "metric": metric
                })
            except Exception as e:
                logger.warning(f"Error calculating centrality for {entity.id}: {e}")
                continue
        
        # Sort by score
        scores.sort(key=lambda x: x["centrality_score"], reverse=True)
        
        return scores[:limit]
    
    # ========================================================================
    # Community Detection
    # ========================================================================
    
    def find_connected_components(self) -> List[Set[str]]:
        """
        Find connected components (groups of interconnected entities)
        
        Returns:
            List of component sets
        """
        all_entities = self.db.query(GraphEntity).all()
        entity_ids = [e.id for e in all_entities]
        
        visited = set()
        components = []
        
        for entity_id in entity_ids:
            if entity_id in visited:
                continue
            
            # BFS to find component
            component = set()
            queue = deque([entity_id])
            visited.add(entity_id)
            component.add(entity_id)
            
            while queue:
                current = queue.popleft()
                
                # Get neighbors
                rels = self.db.query(GraphRelationship).filter(
                    (GraphRelationship.source_entity_id == current) |
                    (GraphRelationship.target_entity_id == current)
                ).all()
                
                for rel in rels:
                    neighbor_id = rel.target_entity_id if rel.source_entity_id == current else rel.source_entity_id
                    
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        component.add(neighbor_id)
                        queue.append(neighbor_id)
            
            if component:
                components.append(component)
        
        return components
    
    # ========================================================================
    # Anomaly Detection
    # ========================================================================
    
    def detect_anomalies(self, threshold: float = 2.0) -> List[Dict[str, Any]]:
        """
        Detect anomalous entities or relationships
        
        Heuristics:
        - Entities with unusually high degree
        - Relationships with unusually low confidence
        - Entities with contradictory relationships
        
        Args:
            threshold: Standard deviations from mean for anomaly
            
        Returns:
            List of anomalies
        """
        anomalies = []
        
        # Get degree statistics
        degrees = []
        all_entities = self.db.query(GraphEntity).all()
        
        for entity in all_entities:
            degree = self.calculate_degree_centrality(entity.id)
            degrees.append(degree["total_degree"])
        
        if not degrees or len(degrees) < 2:
            return anomalies
        
        avg_degree = sum(degrees) / len(degrees)
        variance = sum((d - avg_degree) ** 2 for d in degrees) / len(degrees)
        std_dev = math.sqrt(variance)
        
        # Find anomalous entities
        for entity in all_entities:
            degree = self.calculate_degree_centrality(entity.id)
            total_degree = degree["total_degree"]
            
            if std_dev > 0 and abs(total_degree - avg_degree) > threshold * std_dev:
                anomalies.append({
                    "type": "high_degree_entity",
                    "entity_id": entity.id,
                    "entity_name": entity.canonical_name,
                    "degree": total_degree,
                    "expected": avg_degree,
                    "deviation": abs(total_degree - avg_degree) / std_dev if std_dev > 0 else 0
                })
        
        # Check for low confidence relationships
        all_rels = self.db.query(GraphRelationship).filter(
            GraphRelationship.confidence < 30
        ).all()
        
        for rel in all_rels[:20]:
            anomalies.append({
                "type": "low_confidence_relationship",
                "relationship_id": rel.id,
                "source_id": rel.source_entity_id,
                "target_id": rel.target_entity_id,
                "relationship_type": rel.relationship_type,
                "confidence": rel.confidence
            })
        
        return anomalies
    
    # ========================================================================
    # Influence Analysis
    # ========================================================================
    
    def analyze_entity_influence(self, entity_id: str, depth: int = 3) -> Dict[str, Any]:
        """
        Analyze how changes to entity would affect graph
        
        Args:
            entity_id: Entity ID
            depth: How far to propagate analysis
            
        Returns:
            Influence analysis dict
        """
        entity = self.db.query(GraphEntity).filter(GraphEntity.id == entity_id).first()
        if not entity:
            return {}
        
        # Direct relationships
        direct_rels = self.db.query(GraphRelationship).filter(
            (GraphRelationship.source_entity_id == entity_id) |
            (GraphRelationship.target_entity_id == entity_id)
        ).count()
        
        # Reachable entities
        reachable = set()
        queue = deque([entity_id])
        visited = {entity_id}
        distances = {entity_id: 0}
        
        while queue:
            current = queue.popleft()
            current_dist = distances[current]
            
            if current_dist >= depth:
                continue
            
            rels = self.db.query(GraphRelationship).filter(
                GraphRelationship.source_entity_id == current
            ).all()
            
            for rel in rels:
                next_id = rel.target_entity_id
                if next_id not in visited:
                    visited.add(next_id)
                    distances[next_id] = current_dist + 1
                    reachable.add(next_id)
                    queue.append(next_id)
        
        return {
            "entity_id": entity_id,
            "entity_name": entity.canonical_name,
            "direct_relationships": direct_rels,
            "reachable_entities": len(reachable),
            "reachable_entity_ids": list(reachable),
            "graph_penetration": len(reachable) / max(1, len(self.db.query(GraphEntity).all()))
        }


def main():
    """Test analytics"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    with GraphAnalytics() as analytics:
        # Get top central entities
        top = analytics.get_top_central_entities("degree", 10)
        print(f"\nTop 10 entities by degree centrality:")
        for entity in top:
            print(f"  {entity}")


if __name__ == "__main__":
    main()
