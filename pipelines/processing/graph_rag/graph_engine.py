"""
Knowledge Graph Engine for GraphRAG
Core graph structure, entity/relationship storage, and transactional operations
"""
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timezone
import uuid

from services.db.session import SessionLocal
from services.db.models import GraphEntity, GraphRelationship, GraphEntityMention, GraphRelationshipMention
from app.processors.graph_rag.entity_resolver import EntityResolver

logger = logging.getLogger(__name__)


class KnowledgeGraphEngine:
    """
    Core knowledge graph engine for storing and querying entity-relationship data
    
    Features:
    - Entity and relationship CRUD
    - Confidence score tracking
    - Bidirectional relationships
    - Transaction management
    - Multi-tenant data isolation
    """
    
    # Supported relationship types  (can be extended)
    VALID_REL_TYPES = {
        "OWNS", "OWNED_BY", "WORKS_FOR", "EMPLOYS",
        "LOCATED_IN", "HAS_LOCATION", "FOUNDED_BY", "FOUNDED",
        "MANAGES", "MANAGED_BY", "INVESTS_IN", "INVESTED_BY",
        "PARTNERS_WITH", "COMPETES_WITH", "ACQUIRES", "ACQUIRED_BY",
        "SUBSIDIARY_OF", "PARENT_OF", "PRODUCES", "PRODUCED_BY",
        "CONTAINS", "MEMBER_OF", "BASED_IN", "HAS_HEADQUARTERS",
        "MANUFACTURES", "SUPPLIES", "DISTRIBUTES", "RELATED_TO"
    }
    
    def __init__(self):
        """Initialize graph engine"""
        self.db = SessionLocal()
        self.entity_resolver = EntityResolver()
    
    def close(self):
        """Close database session"""
        if self.db:
            self.db.close()
        if self.entity_resolver:
            self.entity_resolver.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    # ========================================================================
    # Entity Operations
    # ========================================================================
    
    def create_entity(self, name: str, entity_type: str, doc_id: Optional[str] = None,
                     properties: Optional[Dict[str, Any]] = None, confidence: int = 50) -> str:
        """
        Create or resolve entity
        
        Args:
            name: Entity name
            entity_type: Entity type (PERSON, ORGANIZATION, LOCATION, etc.)
            doc_id: First document mentioning this entity
            properties: Additional properties (JSON)
            confidence: Extraction confidence (0-100)
            
        Returns:
            Entity ID
        """
        # Resolve through entity resolver (handles deduplication)
        entity_id = self.entity_resolver.resolve_entity(name, entity_type, doc_id, confidence)
        
        # Add properties if provided
        if properties:
            entity = self.db.query(GraphEntity).filter(GraphEntity.id == entity_id).first()
            if entity:
                entity.properties.update(properties)
                entity.updated_at = datetime.now(timezone.utc)
                self.db.commit()
        
        return entity_id
    
    def get_entity(self, entity_id: str) -> Optional[GraphEntity]:
        """Get entity by ID"""
        return self.db.query(GraphEntity).filter(GraphEntity.id == entity_id).first()
    
    def update_entity(self, entity_id: str, **kwargs) -> bool:
        """
        Update entity properties
        
        Args:
            entity_id: Entity ID
            **kwargs: Fields to update (name, properties, etc.)
            
        Returns:
            Success status
        """
        entity = self.db.query(GraphEntity).filter(GraphEntity.id == entity_id).first()
        if not entity:
            logger.error(f"Entity {entity_id} not found")
            return False
        
        # Update allowed fields
        if 'properties' in kwargs:
            entity.properties.update(kwargs['properties'])
        
        if 'entity_type' in kwargs:
            entity.entity_type = kwargs['entity_type']
        
        entity.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        
        logger.info(f"Updated entity {entity_id}")
        return True
    
    def delete_entity(self, entity_id: str) -> bool:
        """
        Delete entity and cascade relationships
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Success status
        """
        entity = self.db.query(GraphEntity).filter(GraphEntity.id == entity_id).first()
        if not entity:
            logger.error(f"Entity {entity_id} not found")
            return False
        
        self.db.delete(entity)  # Cascade will delete mentions and relationships
        self.db.commit()
        
        logger.info(f"Deleted entity {entity_id}")
        return True
    
    def list_entities(self, entity_type: Optional[str] = None, limit: int = 100) -> List[GraphEntity]:
        """
        List entities
        
        Args:
            entity_type: Filter by type
            limit: Maximum results
            
        Returns:
            List of entities
        """
        query = self.db.query(GraphEntity)
        
        if entity_type:
            query = query.filter(GraphEntity.entity_type == entity_type)
        
        return query.order_by(GraphEntity.mention_count.desc()).limit(limit).all()
    
    def get_top_entities(self, limit: int = 20, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get most important (most-mentioned) entities"""
        query = self.db.query(GraphEntity)
        
        if entity_type:
            query = query.filter(GraphEntity.entity_type == entity_type)
        
        entities = query.order_by(GraphEntity.mention_count.desc()).limit(limit).all()
        
        return [
            {
                "id": e.id,
                "name": e.canonical_name,
                "type": e.entity_type,
                "mentions": e.mention_count,
                "confidence": e.total_confidence // e.mention_count if e.mention_count > 0 else 0,
                "properties": e.properties
            }
            for e in entities
        ]
    
    # ========================================================================
    # Relationship Operations
    # ========================================================================
    
    def create_relationship(self, source_id: str, target_id: str, relationship_type: str,
                           confidence: int = 50, properties: Optional[Dict[str, Any]] = None,
                           doc_id: Optional[str] = None) -> str:
        """
        Create or update relationship between entities
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship (from VALID_REL_TYPES)
            confidence: Extraction confidence (0-100)
            properties: Additional properties
            doc_id: Document where relationship was found
            
        Returns:
            Relationship ID
        """
        # Validate relationship type
        if relationship_type not in self.VALID_REL_TYPES:
            logger.warning(f"Unknown relationship type: {relationship_type}. Using as-is.")
        
        # Check if relationship already exists
        existing = self.db.query(GraphRelationship).filter(
            GraphRelationship.source_entity_id == source_id,
            GraphRelationship.target_entity_id == target_id,
            GraphRelationship.relationship_type == relationship_type
        ).first()
        
        if existing:
            # Update existing relationship
            existing.mention_count += 1
            existing.total_documents += 1
            # Average confidence
            existing.confidence = int((existing.confidence + confidence) / 2)
            if properties:
                existing.properties.update(properties)
            existing.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            
            logger.debug(f"Updated relationship {existing.id}")
            return existing.id
        else:
            # Create new relationship
            rel_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            relationship = GraphRelationship(
                id=rel_id,
                source_entity_id=source_id,
                target_entity_id=target_id,
                relationship_type=relationship_type,
                confidence=confidence,
                properties=properties or {},
                created_at=now,
                updated_at=now
            )
            
            self.db.add(relationship)
            self.db.commit()
            
            logger.debug(f"Created new relationship {rel_id}")
            return rel_id
    
    def get_relationship(self, rel_id: str) -> Optional[GraphRelationship]:
        """Get relationship by ID"""
        return self.db.query(GraphRelationship).filter(GraphRelationship.id == rel_id).first()
    
    def delete_relationship(self, rel_id: str) -> bool:
        """Delete relationship"""
        rel = self.db.query(GraphRelationship).filter(GraphRelationship.id == rel_id).first()
        if not rel:
            logger.error(f"Relationship {rel_id} not found")
            return False
        
        self.db.delete(rel)
        self.db.commit()
        
        logger.info(f"Deleted relationship {rel_id}")
        return True
    
    def get_relationships(self, entity_id: str, direction: str = "both",
                         rel_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get relationships for an entity
        
        Args:
            entity_id: Entity ID
            direction: "outgoing", "incoming", or "both"
            rel_type: Filter by relationship type
            
        Returns:
            List of relationships
        """
        results = []
        
        if direction in ["outgoing", "both"]:
            query = self.db.query(GraphRelationship).filter(
                GraphRelationship.source_entity_id == entity_id
            )
            if rel_type:
                query = query.filter(GraphRelationship.relationship_type == rel_type)
            
            for rel in query.all():
                target = self.get_entity(rel.target_entity_id)
                results.append({
                    "id": rel.id,
                    "direction": "outgoing",
                    "source": entity_id,
                    "target": rel.target_entity_id,
                    "type": rel.relationship_type,
                    "target_name": target.canonical_name if target else "Unknown",
                    "confidence": rel.confidence,
                    "mention_count": rel.mention_count
                })
        
        if direction in ["incoming", "both"]:
            query = self.db.query(GraphRelationship).filter(
                GraphRelationship.target_entity_id == entity_id
            )
            if rel_type:
                query = query.filter(GraphRelationship.relationship_type == rel_type)
            
            for rel in query.all():
                source = self.get_entity(rel.source_entity_id)
                results.append({
                    "id": rel.id,
                    "direction": "incoming",
                    "source": rel.source_entity_id,
                    "target": entity_id,
                    "type": rel.relationship_type,
                    "source_name": source.canonical_name if source else "Unknown",
                    "confidence": rel.confidence,
                    "mention_count": rel.mention_count
                })
        
        return results
    
    def list_relationships(self, rel_type: Optional[str] = None,
                          min_confidence: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all relationships (optionally filtered)
        
        Args:
            rel_type: Filter by relationship type
            min_confidence: Minimum confidence threshold
            limit: Maximum results
            
        Returns:
            List of relationships
        """
        query = self.db.query(GraphRelationship)
        
        if rel_type:
            query = query.filter(GraphRelationship.relationship_type == rel_type)
        
        query = query.filter(GraphRelationship.confidence >= min_confidence)
        
        relationships = query.order_by(GraphRelationship.mention_count.desc()).limit(limit).all()
        
        return [
            {
                "id": r.id,
                "source_id": r.source_entity_id,
                "source_name": r.source_entity.canonical_name if r.source_entity else "Unknown",
                "target_id": r.target_entity_id,
                "target_name": r.target_entity.canonical_name if r.target_entity else "Unknown",
                "type": r.relationship_type,
                "confidence": r.confidence,
                "mentions": r.mention_count
            }
            for r in relationships
        ]
    
    # ========================================================================
    # Graph Statistics
    # ========================================================================
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get overall graph statistics"""
        entity_count = self.db.query(GraphEntity).count()
        rel_count = self. db.query(GraphRelationship).count()
        entity_types = self.db.query(GraphEntity.entity_type).distinct().count()
        rel_types = self.db.query(GraphRelationship.relationship_type).distinct().count()
        
        return {
            "total_entities": entity_count,
            "total_relationships": rel_count,
            "entity_types": entity_types,
            "relationship_types": rel_types,
            "avg_relationships_per_entity": rel_count * 2 / entity_count if entity_count > 0 else 0
        }
    
    def get_entity_degree(self, entity_id: str) -> Dict[str, int]:
        """Get in-degree and out-degree of entity"""
        out_degree = self.db.query(GraphRelationship).filter(
            GraphRelationship.source_entity_id == entity_id
        ).count()
        
        in_degree = self.db.query(GraphRelationship).filter(
            GraphRelationship.target_entity_id == entity_id
        ).count()
        
        return {
            "out_degree": out_degree,
            "in_degree": in_degree,
            "total_degree": out_degree + in_degree
        }
    
    # ========================================================================
    # Mentions
    # ========================================================================
    
    def add_entity_mention(self, entity_id: str, doc_id: str, chunk_id: str,
                          mention_text: str, position: int = 0, confidence: int = 50) -> str:
        """Record mention of entity in document"""
        mention_id = str(uuid.uuid4())
        
        mention = GraphEntityMention(
            id=mention_id,
            entity_id=entity_id,
            doc_id=doc_id,
            chunk_id=chunk_id,
            mention_text=mention_text,
            position=position,
            confidence=confidence,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(mention)
        self.db.commit()
        
        return mention_id
    
    def add_relationship_mention(self, rel_id: str, doc_id: str, chunk_id: Optional[str] = None,
                                mention_text: Optional[str] = None, confidence: int = 50) -> str:
        """Record mention of relationship in document"""
        mention_id = str(uuid.uuid4())
        
        mention = GraphRelationshipMention(
            id=mention_id,
            relationship_id=rel_id,
            doc_id=doc_id,
            chunk_id=chunk_id,
            mention_text=mention_text,
            confidence=confidence,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(mention)
        self.db.commit()
        
        return mention_id
    
    # ========================================================================
    # Batch Operations
    # ========================================================================
    
    def batch_create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Create multiple entities efficiently
        
        Args:
            entities: List of dicts with 'name', 'type', 'doc_id' (optional), etc.
            
        Returns:
            Mapping of names to entity IDs
        """
        results = {}
        
        for entity_data in entities:
            entity_id = self.create_entity(
                name=entity_data.get('name'),
                entity_type=entity_data.get('type', 'CONCEPT'),
                doc_id=entity_data.get('doc_id'),
                properties=entity_data.get('properties'),
                confidence=entity_data.get('confidence', 50)
            )
            results[entity_data.get('name')] = entity_id
        
        return results
    
    def batch_create_relationships(self, relationships: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Create multiple relationships efficiently
        
        Args:
            relationships: List of dicts with 'source_id', 'target_id', 'type', confidence', etc.
            
        Returns:
            Mapping of (source_id, target_id, type) to relationship ID
        """
        results = {}
        
        for rel_data in relationships:
            rel_id = self.create_relationship(
                source_id=rel_data.get('source_id'),
                target_id=rel_data.get('target_id'),
                relationship_type=rel_data.get('type'),
                confidence=rel_data.get('confidence', 50),
                properties=rel_data.get('properties'),
                doc_id=rel_data.get('doc_id')
            )
            key = (rel_data.get('source_id'), rel_data.get('target_id'), rel_data.get('type'))
            results[str(key)] = rel_id
        
        return results


def main():
    """Test knowledge graph engine"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    with KnowledgeGraphEngine() as kg:
        # Test stats
        stats = kg.get_graph_stats()
        print(f"\nGraph Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
