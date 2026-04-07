"""
Entity Resolver for GraphRAG
Handles entity deduplication, normalization, and linking across documents
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
from datetime import datetime, timezone
import uuid
import json

from services.db.session import SessionLocal
from services.db.models import GraphEntity, GraphEntityMention, Document

logger = logging.getLogger(__name__)


class EntityResolver:
    """
    Resolves entities across documents with deduplication and normalization
    
    Features:
    - Fuzzy name matching
    - Type-aware resolution
    - Alias tracking
    - Canonical form selection
    - Multi-tenant isolation
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize entity resolver
        
        Args:
            similarity_threshold: Minimum string similarity (0-1) for matching entities
        """
        self.similarity_threshold = similarity_threshold
        self.db = SessionLocal()
        self.entity_cache: Dict[str, str] = {}  # Maps normalized names to entity IDs
    
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
    # Normalization
    # ========================================================================
    
    def normalize_entity_name(self, name: str) -> str:
        """
        Normalize entity name for comparison
        
        Args:
            name: Raw entity name
            
        Returns:
            Normalized name
        """
        # Basic cleanup
        normalized = name.strip().lower()
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Remove common prefixes/suffixes
        normalized = re.sub(r'^\b(the|a|an)\b\s+', '', normalized)
        normalized = re.sub(r'\s+(inc|ltd|llc|corp|co|company|corporation)\b$', '', normalized)
        
        return normalized
    
    def extract_type_hints(self, text: str) -> Optional[str]:
        """
        Extract entity type hints from text
        
        Examples:
        - "Apple Inc." → ORGANIZATION
        - "John Smith" → PERSON
        - "New York City" → LOCATION
        
        Args:
            text: Entity text
            
        Returns:
            Inferred entity type or None
        """
        text_lower = text.lower()
        
        # Organization indicators
        org_keywords = {'company', 'corp', 'inc', 'ltd', 'llc', 'gmbh', 'ag', 'sa', 
                       'corporation', 'incorporated', 'limited', 'co', 'enterprises',
                       'bank', 'hospital', 'university', 'school', 'foundation'}
        
        # Person indicators
        person_keywords = {'mr', 'ms', 'mrs', 'dr', 'prof', 'sir', 'madam', 'jr', 'sr', 'ph.d'}
        
        # Location indicators
        location_keywords = {'city', 'town', 'village', 'state', 'country', 'province',
                           'region', 'district', 'county', 'street', 'avenue', 'road',
                           'lake', 'river', 'mountain', 'island', 'peninsula'}
        
        # Check for keywords
        words = set(text_lower.split())
        
        if words & org_keywords:
            return "ORGANIZATION"
        if words & person_keywords:
            return "PERSON"
        if words & location_keywords:
            return "LOCATION"
        
        # Check for common name patterns
        if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', text):
            # Pattern: FirstName LastName
            return "PERSON"
        
        return None
    
    # ========================================================================
    # Matching and Similarity
    # ========================================================================
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two entity names
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            Similarity score (0-1)
        """
        # Normalize both names
        norm1 = self.normalize_entity_name(name1)
        norm2 = self.normalize_entity_name(name2)
        
        # Exact match
        if norm1 == norm2:
            return 1.0
        
        # Use SequenceMatcher for fuzzy matching
        ratio = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost score for substring matches
        if norm1 in norm2 or norm2 in norm1:
            ratio = min(1.0, ratio * 1.2)
        
        return ratio
    
    def find_similar_entities(self, name: str, entity_type: Optional[str] = None, 
                            threshold: Optional[float] = None) -> List[Tuple[str, str, float]]:
        """
        Find similar entities in database
        
        Args:
            name: Entity name to match
            entity_type: Filter by type (optional)
            threshold: Override default similarity threshold
            
        Returns:
            List of tuples: (entity_id, canonical_name, similarity_score)
        """
        if threshold is None:
            threshold = self.similarity_threshold
        
        normalized_name = self.normalize_entity_name(name)
        results = []
        
        # Build query
        query = self.db.query(GraphEntity)
        
        if entity_type:
            query = query.filter(GraphEntity.entity_type == entity_type)
        
        # Fetch all entities of matching type
        entities = query.all()
        
        for entity in entities:
            similarity = self.calculate_similarity(name, entity.canonical_name)
            
            if similarity >= threshold:
                results.append((entity.id, entity.canonical_name, similarity))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[2], reverse=True)
        
        return results
    
    # ========================================================================
    # Entity Resolution
    # ========================================================================
    
    def resolve_entity(self, name: str, entity_type: Optional[str] = None, 
                      doc_id: Optional[str] = None, confidence: int = 50) -> str:
        """
        Resolve entity name to canonical entity ID
        
        This is the main method - resolves a name to either:
        1. Existing entity (if high similarity match found)
        2. New entity (if no match)
        
        Args:
            name: Entity name from document
            entity_type: Entity type (inferred if not provided)
            doc_id: Document ID where entity appears
            confidence: Extraction confidence (0-100)
            
        Returns:
            Entity ID (either existing or newly created)
        """
        logger.debug(f"Resolving entity: {name} (type={entity_type})")
        
        # Infer type if not provided
        if not entity_type:
            entity_type = self.extract_type_hints(name) or "CONCEPT"
        
        # Try to find similar entities
        similar = self.find_similar_entities(name, entity_type)
        
        if similar:
            # Use best match
            best_entity_id, best_name, similarity = similar[0]
            logger.debug(f"  → Matched to existing entity: {best_name} (similarity={similarity:.2f})")
            
            # Update entity statistics
            entity = self.db.query(GraphEntity).filter(GraphEntity.id == best_entity_id).first()
            if entity:
                entity.mention_count += 1
                entity.total_confidence += confidence
                entity.updated_at = datetime.now(timezone.utc)
                self.db.commit()
            
            return best_entity_id
        
        # Create new entity if no match found
        logger.debug(f"  → Creating new entity: {name}")
        entity_id = self._create_entity(name, entity_type, doc_id, confidence)
        
        return entity_id
    
    def _create_entity(self, name: str, entity_type: str, doc_id: Optional[str] = None, 
                      confidence: int = 50) -> str:
        """Create new entity in database"""
        entity_id = str(uuid.uuid4())
        normalized_name = self.normalize_entity_name(name)
        now = datetime.now(timezone.utc)
        
        entity = GraphEntity(
            id=entity_id,
            canonical_name=normalized_name,
            entity_type=entity_type,
            first_doc_id=doc_id,
            mention_count=1,
            total_confidence=confidence,
            aliases=[name] if name != normalized_name else [],
            created_at=now,
            updated_at=now
        )
        
        self.db.add(entity)
        self.db.commit()
        
        logger.info(f"Created new entity: {entity_id} ({normalized_name}) [type={entity_type}]")
        return entity_id
    
    # ========================================================================
    # Entity Merging
    # ========================================================================
    
    def merge_entities(self, primary_id: str, secondary_ids: List[str]) -> str:
        """
        Merge multiple entities into one primary entity
        
        This consolidates duplicate entities by:
        1. Copying mentions from secondary to primary
        2. Redirecting relationships to primary
        3. Updating aliases
        4. Removing secondary entities
        
        Args:
            primary_id: Entity ID to keep
            secondary_ids: Entity IDs to merge into primary
            
        Returns:
            Primary entity ID
        """
        logger.info(f"Merging {len(secondary_ids)} entities into {primary_id}")
        
        primary = self.db.query(GraphEntity).filter(GraphEntity.id == primary_id).first()
        if not primary:
            logger.error(f"Primary entity {primary_id} not found")
            return None
        
        for secondary_id in secondary_ids:
            secondary = self.db.query(GraphEntity).filter(GraphEntity.id == secondary_id).first()
            if not secondary:
                continue
            
            # Merge mentions
            mentions = self.db.query(GraphEntityMention).filter(
                GraphEntityMention.entity_id == secondary_id
            ).all()
            
            for mention in mentions:
                mention.entity_id = primary_id
            
            # Merge aliases
            if secondary.aliases:
                primary.aliases.extend(secondary.aliases)
            
            # Update mention count
            primary.mention_count += secondary.mention_count
            primary.total_confidence += secondary.total_confidence
            
            # Delete secondary entity (cascade will handle relationships/mentions)
            self.db.delete(secondary)
        
        # Remove duplicate aliases
        primary.aliases = list(set(primary.aliases))
        primary.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        logger.info(f"✓ Merged {len(secondary_ids)} entities into {primary_id}")
        
        return primary_id
    
    # ========================================================================
    # Alias Management
    # ========================================================================
    
    def add_alias(self, entity_id: str, alias: str) -> bool:
        """
        Add alternative name (alias) to entity
        
        Args:
            entity_id: Entity ID
            alias: Alternative name
            
        Returns:
            Success status
        """
        entity = self.db.query(GraphEntity).filter(GraphEntity.id == entity_id).first()
        if not entity:
            logger.error(f"Entity {entity_id} not found")
            return False
        
        if alias not in entity.aliases:
            entity.aliases.append(alias)
            entity.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            logger.info(f"Added alias '{alias}' to entity {entity_id}")
        
        return True
    
    def get_aliases(self, entity_id: str) -> List[str]:
        """Get all aliases for an entity"""
        entity = self.db.query(GraphEntity).filter(GraphEntity.id == entity_id).first()
        return entity.aliases if entity else []
    
    # ========================================================================
    # Retrieval
    # ========================================================================
    
    def get_entity_by_name(self, name: str, user_id: Optional[str] = None) -> Optional[GraphEntity]:
        """
        Get entity by exact canonical name
        
        Args:
            name: Entity canonical name
            user_id: Filter by user (for multi-tenancy)
            
        Returns:
            GraphEntity or None
        """
        normalized_name = self.normalize_entity_name(name)
        
        query = self.db.query(GraphEntity).filter(
            GraphEntity.canonical_name == normalized_name
        )
        
        # Optional: Filter by user through documents
        if user_id:
            query = query.join(Document).filter(Document.user_id == user_id)
        
        return query.first()
    
    def get_entity_by_id(self, entity_id: str) -> Optional[GraphEntity]:
        """Get entity by ID"""
        return self.db.query(GraphEntity).filter(GraphEntity.id == entity_id).first()
    
    def get_entity_mentions(self, entity_id: str, doc_id: Optional[str] = None) -> List[GraphEntityMention]:
        """
        Get all mentions of an entity
        
        Args:
            entity_id: Entity ID
            doc_id: Filter by specific document
            
        Returns:
            List of mentions
        """
        query = self.db.query(GraphEntityMention).filter(
            GraphEntityMention.entity_id == entity_id
        )
        
        if doc_id:
            query = query.filter(GraphEntityMention.doc_id == doc_id)
        
        return query.all()
    
    def get_entity_statistics(self, entity_id: str) -> Dict[str, Any]:
        """Get statistics about an entity"""
        entity = self.db.query(GraphEntity).filter(GraphEntity.id == entity_id).first()
        if not entity:
            return {}
        
        mentions = self.get_entity_mentions(entity_id)
        
        return {
            "id": entity.id,
            "canonical_name": entity.canonical_name,
            "entity_type": entity.entity_type,
            "mention_count": entity.mention_count,
            "avg_confidence": entity.total_confidence / entity.mention_count if entity.mention_count > 0 else 0,
            "aliases": entity.aliases,
            "mention_locations": [
                {
                    "doc_id": m.doc_id,
                    "chunk_id": m.chunk_id,
                    "text": m.mention_text,
                    "confidence": m.confidence
                }
                for m in mentions
            ],
            "created_at": entity.created_at.isoformat() if entity.created_at else None,
            "updated_at": entity.updated_at.isoformat() if entity.updated_at else None
        }
    
    # ========================================================================
    # Batch Operations
    # ========================================================================
    
    def batch_resolve_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Resolve multiple entities efficiently
        
        Args:
            entities: List of dicts with 'name', 'type' (optional), 'doc_id' (optional)
            
        Returns:
            Mapping of original names to entity IDs
        """
        results = {}
        
        for entity_data in entities:
            name = entity_data.get('name')
            entity_type = entity_data.get('type')
            doc_id = entity_data.get('doc_id')
            confidence = entity_data.get('confidence', 50)
            
            if name:
                entity_id = self.resolve_entity(name, entity_type, doc_id, confidence)
                results[name] = entity_id
        
        return results
    
    def detect_duplicates(self, threshold: Optional[float] = None) -> List[Tuple[str, List[str]]]:
        """
        Find duplicate entities in database
        
        Args:
            threshold: Similarity threshold for considering entities duplicates
            
        Returns:
            List of tuples: (primary_entity_id, [duplicate_entity_ids])
        """
        if threshold is None:
            threshold = self.similarity_threshold
        
        # This is a simplistic approach - in production, use more sophisticated algorithms
        logger.info("Scanning for duplicate entities...")
        
        all_entities = self.db.query(GraphEntity).all()
        duplicates = []
        used_ids = set()
        
        for i, entity1 in enumerate(all_entities):
            if entity1.id in used_ids:
                continue
            
            matches = [entity1.id]
            
            for entity2 in all_entities[i+1:]:
                if entity2.id in used_ids:
                    continue
                
                # Only compare same types
                if entity1.entity_type != entity2.entity_type:
                    continue
                
                similarity = self.calculate_similarity(entity1.canonical_name, entity2.canonical_name)
                
                if similarity >= threshold:
                    matches.append(entity2.id)
                    used_ids.add(entity2.id)
            
            if len(matches) > 1:
                duplicates.append((matches[0], matches[1:]))
                used_ids.add(matches[0])
        
        logger.info(f"Found {len(duplicates)} potential duplicate groups")
        return duplicates
    
    def auto_merge_duplicates(self, threshold: Optional[float] = None) -> int:
        """
        Automatically find and merge duplicate entities
        
        Args:
            threshold: Similarity threshold
            
        Returns:
            Number of entities merged
        """
        duplicates = self.detect_duplicates(threshold)
        merged_count = 0
        
        for primary_id, secondary_ids in duplicates:
            try:
                self.merge_entities(primary_id, secondary_ids)
                merged_count += len(secondary_ids)
            except Exception as e:
                logger.error(f"Error merging entities {secondary_ids} into {primary_id}: {e}")
        
        return merged_count


def main():
    """Test entity resolver"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    with EntityResolver() as resolver:
        # Test normalization
        names = [
            "Apple Inc",
            "APPLE INC.",
            "apple incorporated",
            "Apple Computer Inc"
        ]
        
        for name in names:
            normalized = resolver.normalize_entity_name(name)
            print(f"'{name}' → '{normalized}'")
        
        # Test similarity
        print(f"\nSimilarity tests:")
        print(f"Apple Inc vs Apple Inc: {resolver.calculate_similarity('Apple Inc', 'Apple Inc')}")
        print(f"Apple Inc vs Apple Corporation: {resolver.calculate_similarity('Apple Inc', 'Apple Corporation')}")
        print(f"Apple Inc vs Microsoft: {resolver.calculate_similarity('Apple Inc', 'Microsoft')}")


if __name__ == "__main__":
    main()
