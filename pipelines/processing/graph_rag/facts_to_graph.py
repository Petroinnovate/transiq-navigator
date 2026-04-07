"""
Facts-to-Graph Converter
Converts deduction engine facts into GraphRAG entities and relationships
"""
import logging
from typing import List, Dict, Any, Tuple
import uuid

logger = logging.getLogger(__name__)


class FactsToGraphConverter:
    """
    Converts extracted facts into deduplicated graph entities and relationships
    
    Flow:
    1. Receive facts: {"subject", "predicate", "object", "confidence"}
    2. Extract and resolve entities
    3. Create relationships between entities
    4. Return entities and relationships for storage
    """
    
    # Mapping of predicates to standardized relationship types
    PREDICATE_MAPPING = {
        # Ownership
        "owns": "OWNS",
        "owned by": "OWNED_BY",
        "is owned by": "OWNED_BY",
        "founder of": "FOUNDED",
        "founded by": "FOUNDED_BY",
        
        # Employment
        "works for": "WORKS_FOR",
        "works at": "WORKS_FOR",
        "employed by": "WORKS_FOR",
        "employs": "EMPLOYS",
        "manager of": "MANAGES",
        "managed by": "MANAGED_BY",
        "ceo of": "MANAGES",
        
        # Location
        "located in": "LOCATED_IN",
        "located at": "LOCATED_IN",
        "based in": "BASED_IN",
        "headquarters in": "HAS_HEADQUARTERS",
        "in": "LOCATED_IN",
        
        # Relationships
        "partners with": "PARTNERS_WITH",
        "partner of": "PARTNERS_WITH",
        "competes with": "COMPETES_WITH",
        "competitor of": "COMPETES_WITH",
        "related to": "RELATED_TO",
        "subsidiary of": "SUBSIDIARY_OF",
        "parent of": "PARENT_OF",
        "acquires": "ACQUIRES",
        "acquired by": "ACQUIRED_BY",
        
        # Products/Manufacturing
        "makes": "PRODUCES",
        "manufactures": "MANUFACTURES",
        "produces": "PRODUCES",
        "produced by": "PRODUCED_BY",
        "supplies": "SUPPLIES",
        "supplied by": "SUPPLIES",
        
        # Membership/Composition
        "member of": "MEMBER_OF",
        "contains": "CONTAINS",
        "is part of": "MEMBER_OF",
        
        # Investment
        "invests in": "INVESTS_IN",
        "invested by": "INVESTED_BY",
        "investment in": "INVESTS_IN",
    }
    
    def __init__(self):
        """Initialize converter"""
        pass
    
    # ========================================================================
    # Fact Validation
    # ========================================================================
    
    def validate_fact(self, fact: Dict[str, Any]) -> bool:
        """
        Validate fact structure
        
        Args:
            fact: Fact dictionary
            
        Returns:
            True if valid
        """
        required_fields = {"subject", "predicate", "object"}
        
        if not all(field in fact for field in required_fields):
            logger.warning(f"Fact missing required fields: {fact}")
            return False
        
        # Validate non-empty values
        if not (fact.get("subject") and fact.get("predicate") and fact.get("object")):
            logger.warning(f"Fact has empty values: {fact}")
            return False
        
        return True
    
    # ========================================================================
    # Entity Type Inference
    # ========================================================================
    
    def infer_entity_type(self, entity_text: str) -> str:
        """
        Infer entity type from text heuristics
        
        Args:
            entity_text: Entity text
            
        Returns:
            Entity type (PERSON, ORGANIZATION, LOCATION, CONCEPT)
        """
        text_lower = entity_text.lower()
        
        # Organization indicators
        org_keywords = {
            'company', 'corp', 'inc', 'ltd', 'llc', 'gmbh', 'ag', 'sa',
            'corporation', 'incorporated', 'limited', 'co', 'enterprises',
            'bank', 'hospital', 'university', 'school', 'foundation', 'group',
            'firm', 'business', 'institute', 'association'
        }
        
        # Person indicators
        person_keywords = {
            'mr', 'ms', 'mrs', 'dr', 'prof', 'sir', 'madam', 'jr', 'sr', 'ph.d',
            'himself', 'herself', 'he', 'she', 'person'
        }
        
        # Location indicators
        location_keywords = {
            'city', 'town', 'village', 'state', 'country', 'province',
            'region', 'district', 'county', 'street', 'avenue', 'road',
            'area', 'zone', 'territory', 'place', 'land'
        }
        
        # Check for keywords
        words = set(text_lower.split())
        
        if any(kw in text_lower for kw in org_keywords):
            return "ORGANIZATION"
        if any(kw in text_lower for kw in person_keywords):
            return "PERSON"
        if any(kw in text_lower for kw in location_keywords):
            return "LOCATION"
        
        # Default type
        return "CONCEPT"
    
    def normalize_predicate(self, predicate: str) -> str:
        """
        Normalize predicate to standard relationship type
        
        Args:
            predicate: Raw predicate text
            
        Returns:
            Standardized relationship type
        """
        normalized = predicate.strip().lower()
        
        # Check mapping
        if normalized in self.PREDICATE_MAPPING:
            return self.PREDICATE_MAPPING[normalized]
        
        # Check for partial matches
        for key, value in self.PREDICATE_MAPPING.items():
            if key in normalized or normalized in key:
                return value
        
        # Return uppercase predicate as-is
        return predicate.strip().upper()
    
    # ========================================================================
    # Conversion
    # ========================================================================
    
    def convert_fact(self, fact: Dict[str, Any], doc_id: str = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Convert single fact to entities and relationship
        
        Args:
            fact: Fact dictionary with subject, predicate, object, confidence
            doc_id: Document ID for tracking
            
        Returns:
            Tuple of (entities_list, relationships_list)
        """
        # Validate
        if not self.validate_fact(fact):
            return [], []
        
        subject = fact.get("subject", "").strip()
        predicate = fact.get("predicate", "").strip()
        obj = fact.get("object", "").strip()
        confidence = fact.get("confidence", 0.5)
        
        # Convert confidence to 0-100 scale
        if isinstance(confidence, float):
            confidence = int(confidence * 100)
        confidence = max(0, min(100, confidence))
        
        # Extract entities
        entities = []
        
        subject_entity = {
            "name": subject,
            "type": self.infer_entity_type(subject),
            "doc_id": doc_id,
            "confidence": confidence,
            "properties": {}
        }
        entities.append(subject_entity)
        
        object_entity = {
            "name": obj,
            "type": self.infer_entity_type(obj),
            "doc_id": doc_id,
            "confidence": confidence,
            "properties": {}
        }
        entities.append(object_entity)
        
        # Create relationship
        relationship = {
            "source_name": subject,
            "target_name": obj,
            "type": self.normalize_predicate(predicate),
            "confidence": confidence,
            "doc_id": doc_id,
            "properties": {
                "original_predicate": predicate,
                "fact_id": str(uuid.uuid4())
            }
        }
        
        relationships = [relationship]
        
        return entities, relationships
    
    def convert_facts(self, facts: List[Dict[str, Any]], doc_id: str = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Convert multiple facts to entities and relationships
        
        Args:
            facts: List of facts
            doc_id: Document ID
            
        Returns:
            Tuple of (entities_list, relationships_list)
        """
        all_entities = []
        all_relationships = []
        
        for fact in facts:
            try:
                entities, relationships = self.convert_fact(fact, doc_id)
                all_entities.extend(entities)
                all_relationships.extend(relationships)
            except Exception as e:
                logger.error(f"Error converting fact: {e}")
                continue
        
        # Deduplicate entities by name
        unique_entities = {}
        for entity in all_entities:
            key = entity["name"].lower()
            if key not in unique_entities:
                unique_entities[key] = entity
        
        entities = list(unique_entities.values())
        
        logger.info(f"Converted {len(facts)} facts → {len(entities)} entities, {len(all_relationships)} relationships")
        
        return entities, all_relationships
    
    # ========================================================================
    # Fact Extraction from Text (for comparison)
    # ========================================================================
    
    @staticmethod
    def extract_simple_facts(text: str, max_facts: int = 10) -> List[Dict[str, Any]]:
        """
        Extract simple facts using heuristics (for testing)
        
        This is a fallback when LLM-based extraction isn't available
        
        Args:
            text: Input text
            max_facts: Maximum facts to extract
            
        Returns:
            List of facts
        """
        facts = []
        sentences = text.split('.')
        
        import re
        
        for sentence in sentences[:max_facts]:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # Pattern 1: "X is Y"
            match = re.search(r'(\w+(?:\s+\w+)*)\s+is\s+(\w+(?:\s+\w+)*)', sentence, re.IGNORECASE)
            if match:
                facts.append({
                    "subject": match.group(1),
                    "predicate": "is",
                    "object": match.group(2),
                    "confidence": 0.5
                })
            
            # Pattern 2: "X verb Y"
            match = re.search(r'(\w+(?:\s+\w+)*)\s+(owns|manages|works at|located in|manufactures)\s+(\w+(?:\s+\w+)*)', sentence, re.IGNORECASE)
            if match:
                facts.append({
                    "subject": match.group(1),
                    "predicate": match.group(2),
                    "object": match.group(3),
                    "confidence": 0.5
                })
        
        return facts


def main():
    """Test facts converter"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    converter = FactsToGraphConverter()
    
    # Test fact
    test_fact = {
        "subject": "Apple Inc",
        "predicate": "owns",
        "object": "Beats Electronics",
        "confidence": 0.9
    }
    
    entities, relationships = converter.convert_fact(test_fact, "doc_123")
    
    print(f"\nFact: {test_fact}")
    print(f"\nEntities: {entities}")
    print(f"\nRelationships: {relationships}")
    
    # Test heuristic extraction
    text = "Apple Inc manufactures iPhones. Steve Jobs founded Apple. Apple is located in California."
    facts = converter.extract_simple_facts(text)
    
    print(f"\nExtracted {len(facts)} facts from text:")
    for fact in facts:
        print(f"  {fact}")


if __name__ == "__main__":
    main()
