"""
Graph Storage Layer
High-level interface for persisting and retrieving graph data
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from services.db.session import SessionLocal
from services.db.models import GraphEntity, GraphRelationship, GraphEntityMention, GraphRelationshipMention
from pipelines.processing.graph_rag import EntityResolver, KnowledgeGraphEngine, FactsToGraphConverter

logger = logging.getLogger(__name__)


class GraphStorage:
    """
    High-level graph storage interface
    
    Coordinates entity resolution, graph engine, and facts conversion
    for seamless graph building from raw facts
    """
    
    def __init__(self):
        """Initialize storage components"""
        self.db = SessionLocal()
        self.entity_resolver = EntityResolver()
        self.graph_engine = KnowledgeGraphEngine()
        self.facts_converter = FactsToGraphConverter()
    
    def close(self):
        """Close all connections"""
        if self.db:
            self.db.close()
        if self.entity_resolver:
            self.entity_resolver.close()
        if self.graph_engine:
            self.graph_engine.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    # ========================================================================
    # Facts Integration
    # ========================================================================
    
    def integrate_facts(self, facts: List[Dict[str, Any]], doc_id: str = None,
                       user_id: str = None) -> Dict[str, Any]:
        """
        Integrate extracted facts into knowledge graph
        
        Complete pipeline:
        1. Convert facts to entities and relationships
        2. Resolve entities (deduplication)
        3. Create relationships in graph
        4. Track mentions
        
        Args:
            facts: List of facts from deduction engine
            doc_id: Document ID for tracking
            user_id: User ID for multi-tenancy (optional)
            
        Returns:
            Integration result dict
        """
        logger.info(f"Integrating {len(facts)} facts from doc {doc_id}")
        
        # Convert facts to entities and relationships
        entity_dicts, rel_dicts = self.facts_converter.convert_facts(facts, doc_id)
        
        logger.info(f"Converted to {len(entity_dicts)} entities, {len(rel_dicts)} relationships")
        
        # Create entities with deduplication
        entity_map = {}  # Maps entity_name to entity_id
        
        for entity_dict in entity_dicts:
            entity_id = self.graph_engine.create_entity(
                name=entity_dict.get('name'),
                entity_type=entity_dict.get('type'),
                doc_id=doc_id,
                properties=entity_dict.get('properties', {}),
                confidence=entity_dict.get('confidence', 50)
            )
            entity_map[entity_dict.get('name')] = entity_id
        
        # Create relationships
        rels_created = 0
        for rel_dict in rel_dicts:
            source_id = entity_map.get(rel_dict.get('source_name'))
            target_id = entity_map.get(rel_dict.get('target_name'))
            
            if source_id and target_id:
                rel_id = self.graph_engine.create_relationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=rel_dict.get('type'),
                    confidence=rel_dict.get('confidence', 50),
                    properties=rel_dict.get('properties', {}),
                    doc_id=doc_id
                )
                
                # Track relationship mention
                self.graph_engine.add_relationship_mention(
                    rel_id=rel_id,
                    doc_id=doc_id,
                    confidence=rel_dict.get('confidence', 50)
                )
                
                rels_created += 1
        
        result = {
            "doc_id": doc_id,
            "facts_processed": len(facts),
            "entities_created": len(entity_dicts),
            "unique_entities": len(set(e.get('name') for e in entity_dicts)),
            "relationships_created": rels_created,
            "entity_map": entity_map
        }
        
        logger.info(f"✓ Integration complete: {result}")
        return result
    
    # ========================================================================
    # Bulk Operations
    # ========================================================================
    
    def bulk_add_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Add multiple entities
        
        Args:
            entities: List of entity dicts
            
        Returns:
            Mapping of names to entity IDs
        """
        return self.graph_engine.batch_create_entities(entities)
    
    def bulk_add_relationships(self, relationships: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Add multiple relationships
        
        Args:
            relationships: List of relationship dicts
            
        Returns:
            Key to relationship ID mapping
        """
        return self.graph_engine.batch_create_relationships(relationships)
    
    # ========================================================================
    # Query Operations
    # ========================================================================
    
    def get_entity_profile(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full profile of entity including statistics and relationships
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity profile dict
        """
        entity = self.graph_engine.get_entity(entity_id)
        if not entity:
            return None
        
        # Get relationships
        relationships = self.graph_engine.get_relationships(entity_id, direction="both")
        
        # Get statistics
        stats = self.entity_resolver.get_entity_statistics(entity_id)
        
        return {
            "entity": {
                "id": entity.id,
                "name": entity.canonical_name,
                "type": entity.entity_type,
                "aliases": entity.aliases,
                "properties": entity.properties,
                "created_at": entity.created_at.isoformat() if entity.created_at else None
            },
            "statistics": stats,
            "relationships": relationships,
            "mention_count": entity.mention_count
        }
    
    def find_related_entities(self, entity_id: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """
        Find entities related to a given entity
        
        Args:
            entity_id: Entity ID
            max_depth: Maximum relationship hops
            
        Returns:
            List of related entities with paths
        """
        from pipelines.processing.graph_rag import GraphAnalytics
        
        related = []
        
        with GraphAnalytics() as analytics:
            # Get all reachable entities
            all_entities = self.db.query(GraphEntity).all()
            
            for other_entity in all_entities[:100]:  # Limit for performance
                if other_entity.id == entity_id:
                    continue
                
                path = analytics.shortest_path(entity_id, other_entity.id)
                
                if path and path.get("length") <= max_depth:
                    related.append({
                        "entity_id": other_entity.id,
                        "entity_name": other_entity.canonical_name,
                        "entity_type": other_entity.entity_type,
                        "path_length": path.get("length"),
                        "path": path.get("entities"),
                        "relationships": path.get("relationships")
                    })
            
            # Sort by path length (closer first)
            related.sort(key=lambda x: x["path_length"])
        
        return related
    
    # ========================================================================
    # Search Operations
    # ========================================================================
    
    def search_entities(self, query: str, entity_type: Optional[str] = None,
                       limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for entities by name
        
        Args:
            query: Search query
            entity_type: Filter by type
            limit: Maximum results
            
        Returns:
            List of matching entities
        """
        db_query = self.db.query(GraphEntity)
        
        if entity_type:
            db_query = db_query.filter(GraphEntity.entity_type == entity_type)
        
        # Simple substring search on canonical name
        entities = db_query.filter(
            GraphEntity.canonical_name.ilike(f"%{query}%")
        ).limit(limit).all()
        
        return [
            {
                "id": e.id,
                "name": e.canonical_name,
                "type": e.entity_type,
                "mentions": e.mention_count,
                "confidence": e.total_confidence // e.mention_count if e.mention_count > 0 else 0
            }
            for e in entities
        ]
    
    def search_relationships(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search relationships by type
        
        Args:
            query: Relationship type query
            limit: Maximum results
            
        Returns:
            List of matching relationships
        """
        relationships = self.db.query(GraphRelationship).filter(
            GraphRelationship.relationship_type.ilike(f"%{query}%")
        ).limit(limit).all()
        
        return [
            {
                "id": r.id,
                "source": r.source_entity.canonical_name if r.source_entity else "Unknown",
                "target": r.target_entity.canonical_name if r.target_entity else "Unknown",
                "type": r.relationship_type,
                "confidence": r.confidence,
                "mentions": r.mention_count
            }
            for r in relationships
        ]
    
    # ========================================================================
    # Analytics
    # ========================================================================
    
    def get_graph_summary(self) -> Dict[str, Any]:
        """Get overall graph summary"""
        from pipelines.processing.graph_rag import GraphAnalytics
        
        with GraphAnalytics() as analytics:
            stats = self.graph_engine.get_graph_stats()
            top_entities = analytics.get_top_central_entities("degree", 10)
            anomalies = analytics.detect_anomalies()
            components = analytics.find_connected_components()
            
            return {
                "stats": stats,
                "top_entities": top_entities,
                "anomalies": anomalies[:5],  # Top 5 anomalies
                "components": [len(c) for c in components],
                "largest_component": max(len(c) for c in components) if components else 0,
                "num_components": len(components)
            }
    
    def get_entity_impact(self, entity_id: str) -> Dict[str, Any]:
        """Get impact analysis for entity"""
        from pipelines.processing.graph_rag import GraphAnalytics
        
        with GraphAnalytics() as analytics:
            return analytics.analyze_entity_influence(entity_id)
    
    # ========================================================================
    # Data Quality
    # ========================================================================
    
    def find_and_merge_duplicates(self, threshold: float = 0.85) -> int:
        """
        Automatically find and merge duplicate entities
        
        Args:
            threshold: Similarity threshold
            
        Returns:
            Number of entities merged
        """
        return self.entity_resolver.auto_merge_duplicates(threshold)
    
    def get_data_quality_metrics(self) -> Dict[str, Any]:
        """Get data quality metrics"""
        total_entities = self.db.query(GraphEntity).count()
        total_rels = self.db.query(GraphRelationship).count()
        
        # Low confidence relationships
        low_confidence = self.db.query(GraphRelationship).filter(
            GraphRelationship.confidence < 30
        ).count()
        
        # Entities with single mention
        single_mention = self.db.query(GraphEntity).filter(
            GraphEntity.mention_count == 1
        ).count()
        
        # Average confidence
        avg_confidence = self.db.query(GraphRelationship).filter(
            GraphRelationship.confidence > 0
        ).count()
        
        return {
            "total_entities": total_entities,
            "total_relationships": total_rels,
            "low_confidence_relationships": low_confidence,
            "entities_single_mention": single_mention,
            "quality_score": max(0, 1 - (low_confidence / max(1, total_rels)) - (single_mention / max(1, total_entities)))
        }


def main():
    """Test graph storage"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    with GraphStorage() as storage:
        # Test fact integration
        facts = [
            {"subject": "Apple Inc", "predicate": "owns", "object": "Beats Electronics", "confidence": 0.9},
            {"subject": "Apple Inc", "predicate": "manufactures", "object": "iPhone", "confidence": 0.95},
            {"subject": "Steve Jobs", "predicate": "founded", "object": "Apple Inc", "confidence": 0.9}
        ]
        
        result = storage.integrate_facts(facts, "doc_123")
        print(f"\nIntegration result: {result}")
        
        # Test summary
        summary = storage.get_graph_summary()
        print(f"\nGraph summary: {summary}")


if __name__ == "__main__":
    main()
