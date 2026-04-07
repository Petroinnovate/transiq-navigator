"""
Deduction Enrichment Module - Business Entity Extraction

Enhances deduction engine facts with business entity metadata:
- Identifies entity types (DEPARTMENT, ROLE, PROCESS, SYSTEM, LOCATION, KPI)
- Extracts responsible departments and teams
- Discovers executive/role relationships
- Links KPIs to departments and processes

Works in tandem with impact_engine to provide relationship context.
"""

import logging
import re
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class EntityTypePattern(Enum):
    """Entity type patterns for classification"""
    DEPARTMENT = "DEPARTMENT"
    ROLE = "ROLE"
    PROCESS = "PROCESS"
    SYSTEM = "SYSTEM"
    LOCATION = "LOCATION"
    KPI = "KPI"
    TEAM = "TEAM"
    EQUIPMENT = "EQUIPMENT"


class BusinessEntityExtractor:
    """
    Extracts business entities and their types from deduction facts.
    
    Patterns:
    - DEPARTMENT: Finance, Operations, Drilling, Production, Subsurface, Facilities
    - ROLE: CEO, CFO, VP, Manager, Engineer, Analyst, Supervisor
    - PROCESS: Drilling, Production, Maintenance, Planning, Forecasting
    - SYSTEM: ERP, MES, LIMS, DCS, Safety System
    - EQUIPMENT: Rig, Pipeline, Generator, Compressor, Separator
    - KPI: All metrics with units or targets (Revenue, Cost, NPT, ROP, TRIR, LTIR)
    - LOCATION: Fields, Basins, Countries, Regions, Wells, Platforms
    """
    
    # Dictionary patterns for entity type classification
    DEPARTMENT_KEYWORDS = {
        'finance', 'accounting', 'operations', 'drilling', 'production',
        'subsurface', 'facilities', 'engineering', 'maintenance', 'planning',
        'procurement', 'hr', 'human resources', 'safety', 'compliance',
        'contracts', 'legal', 'supply chain', 'logistics', 'control room',
        'onshore', 'offshore', 'development', 'exploration', 'asset management'
    }
    
    ROLE_KEYWORDS = {
        'ceo', 'cfo', 'coo', 'cto', 'vp', 'vice president', 'director',
        'manager', 'engineer', 'analyst', 'supervisor', 'coordinator',
        'specialist', 'lead', 'head', 'chief', 'president', 'operator',
        'inspector', 'auditor', 'technician', 'administrator', 'advisor',
        'consultant', 'officer', 'controller', 'treasurer'
    }
    
    PROCESS_KEYWORDS = {
        'drilling', 'production', 'injection', 'compression', 'separation',
        'treatment', 'pipeline transport', 'maintenance', 'inspection',
        'planning', 'forecasting', 'budgeting', 'procurement', 'scheduling',
        'well abandonment', 'workovers', 'stimulation', 'completions',
        'reservoir management', 'asset optimization'
    }
    
    SYSTEM_KEYWORDS = {
        'erp', 'mes', 'lims', 'dcs', 'scada', 'hmi', 'plc', 'pcs',
        'wincc', 'aspen', 'hysys', 'pipesim', 'visio', 'sap', 'oracle',
        'database', 'lims', 'data lake', 'analytics platform', 'historians',
        'communications system', 'monitoring system', 'safety system',
        'pi system', 'ignition', 'wonderware', 'wonderware mES'
    }
    
    EQUIPMENT_KEYWORDS = {
        'rig', 'platform', 'pipeline', 'compressor', 'separator', 'generator',
        'turbine', 'pump', 'motor', 'tank', 'manifold', 'wellhead', 'bop',
        'drilling package', 'mud system', 'bhs', 'drill string', 'casing',
        'tubing', 'downhole', 'surface', 'subsea', 'topsides', 'jacket',
        'fpso', 'tlp', 'spar', 'semi-submersible', 'monopod'
    }
    
    LOCATION_KEYWORDS = {
        'field', 'basin', 'country', 'region', 'well', 'platform', 'facility',
        'block', 'asset', 'terminal', 'export', 'pipeline', 'hub', 'node',
        'station', 'camp', 'shore base', 'operating area', 'joa', 'concession'
    }
    
    KPI_KEYWORDS = {
        # Financial
        'revenue', 'cost', 'expense', 'profit', 'margin', 'cash flow', 'capex',
        'opex', 'budget', 'variance', 'roi', 'npl', 'irr', 'npv',
        
        # Production
        'production', 'output', 'rate', 'volume', 'barrels', 'mmcfd', 'bbl',
        'mcf', 'tonnes', 'efficiency', 'uptime', 'availability', 'throughput',
        
        # Drilling
        'npt', 'rop', 'rop', 'rate of penetration', 'well cost', 'afe',
        'wd', 'water depth', 'tvd', 'md', 'well count', 'drilling days',
        
        # Safety
        'trir', 'ltir', 'injury', 'incident', 'accident', 'lost time',
        'recordable', 'safety rate', 'near miss', 'hazard',
        
        # Environmental
        'co2', 'carbon', 'emission', 'ghg', 'water', 'spill', 'voc',
        'discharge', 'air quality', 'footprint',
        
        # Maintenance
        'mtbf', 'mttr', 'availability', 'downtime', 'failure', 'maintenance',
        'reliability', 'forecast', 'spare parts'
    }
    
    def __init__(self):
        self.entity_type_cache = {}
    
    def extract_entities_from_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float
    ) -> List[Tuple[str, EntityTypePattern, float]]:
        """
        Extract entities with types from a single fact triple.
        
        Returns:
            List of (entity_name, entity_type, confidence) tuples
        """
        entities = []
        
        # Classify subject
        subject_type, subject_conf = self._classify_entity(subject)
        if subject_type:
            entities.append((subject, subject_type, subject_conf * confidence))
        
        # Classify object
        obj_type, obj_conf = self._classify_entity(obj)
        if obj_type:
            entities.append((obj, obj_type, obj_conf * confidence))
        
        return entities
    
    def _classify_entity(self, entity_text: str) -> Tuple[Optional[EntityTypePattern], float]:
        """
        Classify an entity into a type based on keyword matching.
        
        Returns:
            (EntityType, confidence_score) or (None, 0.0) if not classified
        """
        # Check cache
        if entity_text in self.entity_type_cache:
            entity_type, conf = self.entity_type_cache[entity_text]
            return entity_type, conf
        
        entity_lower = entity_text.lower().strip()
        
        # Try to classify as KPI first (highest specificity)
        if self._matches_keywords(entity_lower, self.KPI_KEYWORDS):
            result = (EntityTypePattern.KPI, 0.90)
        # Try other types
        elif self._matches_keywords(entity_lower, self.DEPARTMENT_KEYWORDS):
            result = (EntityTypePattern.DEPARTMENT, 0.85)
        elif self._matches_keywords(entity_lower, self.ROLE_KEYWORDS):
            result = (EntityTypePattern.ROLE, 0.85)
        elif self._matches_keywords(entity_lower, self.EQUIPMENT_KEYWORDS):
            result = (EntityTypePattern.EQUIPMENT, 0.80)
        elif self._matches_keywords(entity_lower, self.SYSTEM_KEYWORDS):
            result = (EntityTypePattern.SYSTEM, 0.80)
        elif self._matches_keywords(entity_lower, self.PROCESS_KEYWORDS):
            result = (EntityTypePattern.PROCESS, 0.75)
        elif self._matches_keywords(entity_lower, self.LOCATION_KEYWORDS):
            result = (EntityTypePattern.LOCATION, 0.75)
        else:
            result = (None, 0.0)
        
        # Cache result
        self.entity_type_cache[entity_text] = result
        
        return result
    
    def _matches_keywords(self, text: str, keywords: Set[str]) -> bool:
        """Check if text contains any of the keywords"""
        text_lower = text.lower()
        
        # Exact word match first
        for keyword in keywords:
            if f" {keyword} " in f" {text_lower} ":
                return True
            if text_lower.startswith(keyword + " "):
                return True
            if text_lower.endswith(" " + keyword):
                return True
            if text_lower == keyword:
                return True
        
        return False
    
    def extract_relationships(
        self,
        entities: List[Tuple[str, EntityTypePattern, float]],
        predicate: str
    ) -> List[Dict]:
        """
        Extract relationships between entities based on predicate.
        
        Returns:
            List of relationship dictionaries ready for graph storage
        """
        relationships = []
        
        # Group entities by type
        entities_by_type = {}
        for entity_name, entity_type, conf in entities:
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append((entity_name, conf))
        
        # Create relationships based on entity types and predicate
        predicate_lower = predicate.lower()
        
        # Department responsible for KPI
        if (EntityTypePattern.DEPARTMENT in entities_by_type and
            EntityTypePattern.KPI in entities_by_type):
            for dept, dept_conf in entities_by_type[EntityTypePattern.DEPARTMENT]:
                for kpi, kpi_conf in entities_by_type[EntityTypePattern.KPI]:
                    if self._implies_responsibility(predicate_lower, dept, kpi):
                        relationships.append({
                            "source": dept,
                            "target": kpi,
                            "type": "RESPONSIBLE_FOR",
                            "confidence": min(dept_conf, kpi_conf),
                            "source_type": EntityTypePattern.DEPARTMENT.value,
                            "target_type": EntityTypePattern.KPI.value
                        })
        
        # Role manages Department
        if (EntityTypePattern.ROLE in entities_by_type and
            EntityTypePattern.DEPARTMENT in entities_by_type):
            for role, role_conf in entities_by_type[EntityTypePattern.ROLE]:
                for dept, dept_conf in entities_by_type[EntityTypePattern.DEPARTMENT]:
                    if self._implies_management(predicate_lower, role, dept):
                        relationships.append({
                            "source": role,
                            "target": dept,
                            "type": "MANAGES",
                            "confidence": min(role_conf, dept_conf),
                            "source_type": EntityTypePattern.ROLE.value,
                            "target_type": EntityTypePattern.DEPARTMENT.value
                        })
        
        # KPI depends on Process
        if (EntityTypePattern.KPI in entities_by_type and
            EntityTypePattern.PROCESS in entities_by_type):
            for kpi, kpi_conf in entities_by_type[EntityTypePattern.KPI]:
                for process, proc_conf in entities_by_type[EntityTypePattern.PROCESS]:
                    if self._implies_dependency(predicate_lower, kpi, process):
                        relationships.append({
                            "source": kpi,
                            "target": process,
                            "type": "DEPENDS_ON",
                            "confidence": min(kpi_conf, proc_conf),
                            "source_type": EntityTypePattern.KPI.value,
                            "target_type": EntityTypePattern.PROCESS.value
                        })
        
        # Process uses Equipment/System
        if (EntityTypePattern.PROCESS in entities_by_type and
            (EntityTypePattern.EQUIPMENT in entities_by_type or
             EntityTypePattern.SYSTEM in entities_by_type)):
            
            for process, proc_conf in entities_by_type[EntityTypePattern.PROCESS]:
                # Equipment
                if EntityTypePattern.EQUIPMENT in entities_by_type:
                    for equip, equip_conf in entities_by_type[EntityTypePattern.EQUIPMENT]:
                        relationships.append({
                            "source": process,
                            "target": equip,
                            "type": "USES",
                            "confidence": min(proc_conf, equip_conf) * 0.7,
                            "source_type": EntityTypePattern.PROCESS.value,
                            "target_type": EntityTypePattern.EQUIPMENT.value
                        })
                
                # System
                if EntityTypePattern.SYSTEM in entities_by_type:
                    for sys, sys_conf in entities_by_type[EntityTypePattern.SYSTEM]:
                        relationships.append({
                            "source": process,
                            "target": sys,
                            "type": "USES",
                            "confidence": min(proc_conf, sys_conf) * 0.7,
                            "source_type": EntityTypePattern.PROCESS.value,
                            "target_type": EntityTypePattern.SYSTEM.value
                        })
        
        return relationships
    
    def _implies_responsibility(self, predicate: str, entity1: str, entity2: str) -> bool:
        """Check if predicate implies responsibility relationship"""
        responsibility_keywords = {'manage', 'responsible', 'own', 'control', 'lead',
                                  'supervise', 'execute', 'oversee', 'govern', 'drive'}
        return any(keyword in predicate for keyword in responsibility_keywords)
    
    def _implies_management(self, predicate: str, role: str, department: str) -> bool:
        """Check if predicate implies management relationship"""
        management_keywords = {'manage', 'lead', 'head', 'direct', 'supervise',
                              'oversee', 'govern', 'control', 'owner', 'champion'}
        return any(keyword in predicate for keyword in management_keywords)
    
    def _implies_dependency(self, predicate: str, kpi: str, process: str) -> bool:
        """Check if predicate implies dependency relationship"""
        dependency_keywords = {'depend', 'require', 'need', 'caused', 'due to',
                              'result', 'impact', 'affect', 'driven', 'influenced'}
        return any(keyword in predicate for keyword in dependency_keywords)
    
    def enrich_deduction_facts(
        self,
        facts: List[Dict],
        predicate_mapping: Optional[Dict] = None
    ) -> Dict:
        """
        Enrich deduction facts with entity type and relationship information.
        
        Input facts format:
            [
                {
                    "subject": "Revenue",
                    "predicate": "decreased_due_to",
                    "object": "Market Downturn",
                    "confidence": 0.87
                },
                ...
            ]
        
        Returns:
            {
                "enriched_facts": [fact with entity_types],
                "entities": [{"name", "type", "confidence"}],
                "relationships": [{"source", "target", "type", "confidence"}]
            }
        """
        enriched_facts = []
        all_entities = {}
        all_relationships = []
        
        for fact in facts:
            subject = fact.get("subject", "")
            predicate = fact.get("predicate", "")
            obj = fact.get("object", "")
            confidence = fact.get("confidence", 0.5)
            
            if not subject or not obj:
                continue
            
            # Extract entities
            entities = self.extract_entities_from_fact(subject, predicate, obj, confidence)
            
            # Add entities to result
            for entity_name, entity_type, entity_conf in entities:
                if entity_name not in all_entities:
                    all_entities[entity_name] = {
                        "name": entity_name,
                        "type": entity_type.value,
                        "confidence": entity_conf
                    }
                else:
                    # Update confidence (max of existing and new)
                    all_entities[entity_name]["confidence"] = max(
                        all_entities[entity_name]["confidence"],
                        entity_conf
                    )
            
            # Extract relationships
            relationships = self.extract_relationships(entities, predicate)
            all_relationships.extend(relationships)
            
            # Enrich fact with entity types
            enriched_fact = dict(fact)
            enriched_fact["subject_type"] = next(
                (et.value for en, et, _ in entities if en == subject),
                "UNKNOWN"
            )
            enriched_fact["object_type"] = next(
                (et.value for en, et, _ in entities if en == obj),
                "UNKNOWN"
            )
            enriched_fact["entity_count"] = len(entities)
            enriched_fact["relationships_count"] = len(relationships)
            
            enriched_facts.append(enriched_fact)
        
        return {
            "enriched_facts": enriched_facts,
            "entities": list(all_entities.values()),
            "relationships": all_relationships,
            "entity_count": len(all_entities),
            "relationship_count": len(all_relationships)
        }


def create_extractor() -> BusinessEntityExtractor:
    """Factory function to create business entity extractor"""
    return BusinessEntityExtractor()
