"""
Impact Engine - Relationship-Based KPI Impact Analysis

Integrates GraphRAG with Financial/ESG/Drilling engines to provide:
- Cross-document impact propagation
- Cascading failure analysis
- Root cause chains for DMAIC
- Enhanced financial recommendations

DMAIC Integration:
- Define: Identify problem KPI and related entities
- Measure: Calculate financial impact + affected KPIs
- Analyze: Trace relationships to root causes
- Improve: Recommend actions on related KPIs
- Control: Monitor related KPIs for regression
"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import deque

logger = logging.getLogger(__name__)


class ImpactType(Enum):
    """Types of impact relationships between KPIs"""
    DIRECT = "direct"           # A directly causes B
    IMPLIED = "implied"         # A suggests B may be affected
    HISTORICAL = "historical"   # A and B are correlated historically
    CASCADING = "cascading"     # A→B→C chain effect
    MITIGATING = "mitigating"   # A can reduce impact of B


@dataclass
class Entity:
    """Business entity from deduction engine"""
    id: str
    name: str
    entity_type: str  # DEPARTMENT, ROLE, KPI, PROCESS, SYSTEM, LOCATION
    confidence: float
    properties: Dict = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        return isinstance(other, Entity) and self.id == other.id


@dataclass
class Relationship:
    """Relationship between entities from deduction/graph"""
    source_id: str
    target_id: str
    relationship_type: str  # RESPONSIBLE_FOR, DEPENDS_ON, AFFECTS, etc.
    confidence: float
    impact_type: ImpactType
    strength: float = 1.0  # 0-1 multiplier for impact magnitude


@dataclass
class ImpactPath:
    """Traced impact propagation path"""
    root_cause: Entity
    affected_entities: List[Entity]
    relationships: List[Relationship]
    total_impact_usd: float
    affected_kpis_count: int
    depth: int  # Hops from root cause
    confidence: float  # Confidence in this path


@dataclass
class KPIImpactAnalysis:
    """Complete impact analysis for a KPI"""
    kpi_entity: Entity
    financial_impact_usd: float
    directly_affected_kpis: List[Entity]
    cascading_impact_paths: List[ImpactPath]
    total_cascading_impact_usd: float
    responsible_entities: List[Entity]  # Departments/teams that can mitigate
    root_cause_chain: List[Entity]  # Ordered from root to effect
    recommendations: List[Dict]


class ImpactEngine:
    """
    Analyzes KPI impacts using entity relationships from GraphRAG.
    
    Provides DMAIC support:
    - Define phase: Identifies all related entities
    - Measure phase: Calculates total impact (direct + cascading)
    - Analyze phase: Traces root cause chains
    - Improve phase: Recommends leverage points
    - Control phase: Identifies monitoring entities
    """
    
    def __init__(self, graph_engine=None, financial_engine=None):
        """
        Initialize Impact Engine with optional dependencies
        
        Args:
            graph_engine: GraphRAG engine for entity relationships
            financial_engine: Financial engine for $ calculations
        """
        self.graph_engine = graph_engine
        self.financial_engine = financial_engine
        self.impact_cache = {}
    
    def analyze_kpi_impact(
        self,
        kpi_entity: Entity,
        entities: List[Entity],
        relationships: List[Relationship],
        financial_impact: float = 0.0
    ) -> KPIImpactAnalysis:
        """
        Analyze complete impact of a KPI change using entity relationships.
        
        Args:
            kpi_entity: The KPI being analyzed
            entities: All entities from deduction engine
            relationships: All relationships from graph
            financial_impact: Base financial impact from Financial Engine
            
        Returns:
            Complete impact analysis with cascading effects
        """
        logger.info(f"Analyzing impact of KPI: {kpi_entity.name}")
        
        # Step 1: Find directly affected KPIs (1 hop)
        directly_affected = self._find_directly_affected(
            kpi_entity, entities, relationships
        )
        
        # Step 2: Trace cascading paths (multi-hop)
        cascading_paths = self._find_cascading_paths(
            kpi_entity, entities, relationships, max_depth=4
        )
        
        # Step 3: Calculate total cascading impact
        total_cascading = self._estimate_cascading_impact(cascading_paths)
        
        # Step 4: Identify responsible entities
        responsible = self._find_responsible_entities(
            kpi_entity, relationships
        )
        
        # Step 5: Trace root cause chain
        root_causes = self._find_root_causes(
            kpi_entity, entities, relationships
        )
        
        # Step 6: Generate recommendations
        recommendations = self._generate_recommendations(
            kpi_entity, directly_affected, responsible, root_causes,
            financial_impact, total_cascading
        )
        
        analysis = KPIImpactAnalysis(
            kpi_entity=kpi_entity,
            financial_impact_usd=financial_impact,
            directly_affected_kpis=directly_affected,
            cascading_impact_paths=cascading_paths,
            total_cascading_impact_usd=total_cascading,
            responsible_entities=responsible,
            root_cause_chain=root_causes,
            recommendations=recommendations
        )
        
        # Cache result
        self.impact_cache[kpi_entity.id] = analysis
        
        return analysis
    
    def _find_directly_affected(
        self,
        primary_kpi: Entity,
        all_entities: List[Entity],
        relationships: List[Relationship]
    ) -> List[Entity]:
        """Find KPIs directly affected by primary KPI (1 hop)"""
        affected = set()
        
        # Find relationships where primary_kpi is source
        for rel in relationships:
            if rel.source_id == primary_kpi.id and rel.impact_type != ImpactType.MITIGATING:
                target = next(
                    (e for e in all_entities if e.id == rel.target_id),
                    None
                )
                if target and target.entity_type == "KPI":
                    affected.add(target)
        
        return list(affected)
    
    def _find_cascading_paths(
        self,
        root_kpi: Entity,
        all_entities: List[Entity],
        relationships: List[Relationship],
        max_depth: int = 4
    ) -> List[ImpactPath]:
        """
        Trace cascading impact paths using BFS through entity relationships.
        
        Algorithm: Breadth-first search from root KPI
        - Only follow DIRECT, IMPLIED, CASCADING, HISTORICAL relationships
        - Skip MITIGATING relationships (they reduce impact)
        - Stop at max_depth to prevent infinite loops
        """
        paths = []
        visited = set()
        queue = deque([(root_kpi, [], 0, 1.0)])  # (entity, path, depth, confidence)
        
        while queue:
            current_entity, path_rels, depth, path_confidence = queue.popleft()
            
            if depth >= max_depth or current_entity.id in visited:
                continue
            
            visited.add(current_entity.id)
            
            # Find outgoing relationships
            outgoing = [
                r for r in relationships
                if r.source_id == current_entity.id
                and r.impact_type != ImpactType.MITIGATING
            ]
            
            for rel in outgoing:
                next_entity = next(
                    (e for e in all_entities if e.id == rel.target_id),
                    None
                )
                
                if next_entity and next_entity.id not in visited:
                    # Build path
                    new_path_rels = path_rels + [rel]
                    new_confidence = path_confidence * rel.confidence
                    new_path_entities = [e for _, e in [(r, next(
                        (ent for ent in all_entities if ent.id == r.target_id), None
                    )) for r in new_path_rels] if e]
                    
                    # Store path if it ends at a KPI or important entity
                    if next_entity.entity_type in ["KPI", "PROCESS", "SYSTEM"]:
                        affected_kpis = [
                            e for e in new_path_entities
                            if e.entity_type == "KPI"
                        ]
                        
                        if affected_kpis:
                            impact_path = ImpactPath(
                                root_cause=root_kpi,
                                affected_entities=new_path_entities,
                                relationships=new_path_rels,
                                total_impact_usd=0.0,  # Calculated later
                                affected_kpis_count=len(affected_kpis),
                                depth=depth + 1,
                                confidence=new_confidence
                            )
                            paths.append(impact_path)
                    
                    # Continue traversal
                    queue.append((next_entity, new_path_rels, depth + 1, new_confidence))
        
        return sorted(paths, key=lambda p: p.confidence, reverse=True)
    
    def _estimate_cascading_impact(self, paths: List[ImpactPath]) -> float:
        """
        Estimate total cascading financial impact.
        
        Conservative approach: Sum of (path_impact * confidence * decay_factor)
        - Decay factor = (1 / depth) to reduce impact of distant effects
        - Confidence weighting for relationship certainty
        """
        total_impact = 0.0
        
        for path in paths:
            # Base impact estimate: assume cascading has 30-60% of root impact
            base_cascade_ratio = 0.3 + (path.affected_kpis_count * 0.1)
            base_cascade_ratio = min(base_cascade_ratio, 0.6)
            
            # Apply confidence and decay
            decay_factor = 1.0 / max(1, path.depth)
            path_impact = path.total_impact_usd * base_cascade_ratio * path.confidence * decay_factor
            
            total_impact += path_impact
        
        return total_impact
    
    def _find_responsible_entities(
        self,
        kpi: Entity,
        relationships: List[Relationship]
    ) -> List[Entity]:
        """
        Find departments/teams responsible for the KPI.
        
        Looks for relationships like:
        - Department RESPONSIBLE_FOR KPI
        - Role MANAGES KPI
        - Team OWNS KPI
        """
        responsible = []
        
        # Find reverse relationships (entities that manage/own this KPI)
        for rel in relationships:
            if rel.target_id == kpi.id and "RESPONSIBLE" in rel.relationship_type.upper():
                responsible.append((rel.source_id, rel.confidence))
        
        return [Entity(id=src, name=src, entity_type="DEPARTMENT", confidence=conf) 
                for src, conf in responsible]
    
    def _find_root_causes(
        self,
        effect_kpi: Entity,
        all_entities: List[Entity],
        relationships: List[Relationship]
    ) -> List[Entity]:
        """
        Trace root cause chain backwards from effect KPI.
        
        Algorithm: Reverse BFS
        - Follow relationships where effect_kpi is target
        - Continue backwards until we find entities with no incoming relationships
        - Return ordered chain from root to effect
        """
        root_causes = []
        visited = set()
        queue = deque([(effect_kpi, 0)])  # (entity, depth)
        source_map = {}  # Track sources for each entity
        
        while queue:
            current, depth = queue.popleft()
            
            if current.id in visited or depth > 5:
                continue
            
            visited.add(current.id)
            
            # Find incoming relationships
            incoming = [
                r for r in relationships
                if r.target_id == current.id
                and r.impact_type in [ImpactType.DIRECT, ImpactType.IMPLIED, ImpactType.CASCADING]
            ]
            
            if not incoming:
                # This is a root cause (no incoming relationships)
                root_causes.append(current)
            else:
                # Continue backwards
                for rel in incoming:
                    source = next(
                        (e for e in all_entities if e.id == rel.source_id),
                        None
                    )
                    if source and source.id not in visited:
                        source_map[source.id] = rel
                        queue.append((source, depth + 1))
        
        return sorted(root_causes, key=lambda e: e.confidence, reverse=True)
    
    def _generate_recommendations(
        self,
        primary_kpi: Entity,
        affected_kpis: List[Entity],
        responsible_entities: List[Entity],
        root_causes: List[Entity],
        financial_impact: float,
        cascading_impact: float
    ) -> List[Dict]:
        """
        Generate DMAIC-aligned recommendations.
        
        Provides:
        1. Improve: Actions to fix primary KPI
        2. Control: Monitor these KPIs for cascading effects
        3. Define: Root causes for Six Sigma projects
        4. Measure: Financial impact tracking
        """
        recommendations = []
        
        # Define phase: Identify root causes
        for root_cause in root_causes[:3]:  # Top 3
            recommendations.append({
                "phase": "DEFINE",
                "priority": "HIGH",
                "action": f"Initiate Six Sigma project for root cause: {root_cause.name}",
                "impact": f"Resolving could eliminate ${financial_impact:,.0f} impact",
                "responsible": "Process Improvement team",
                "type": "ROOT_CAUSE_PROJECT"
            })
        
        # Measure & Analyze: Monitor affected KPIs
        for affected in affected_kpis[:5]:  # Top 5
            recommendations.append({
                "phase": "MEASURE",
                "priority": "MEDIUM",
                "action": f"Monitor {affected.name} for cascading effects",
                "impact": f"Could save ${cascading_impact * 0.3:,.0f} by early intervention",
                "responsible": f"Owner of {affected.name}",
                "type": "MONITORING"
            })
        
        # Improve: Fix responsible department action items
        for responsible in responsible_entities[:3]:
            recommendations.append({
                "phase": "IMPROVE",
                "priority": "HIGH",
                "action": f"{responsible.name} should focus on improving {primary_kpi.name}",
                "impact": f"Direct impact: ${financial_impact:,.0f}",
                "responsible": responsible.name,
                "type": "ACTION_ITEM"
            })
        
        # Control: Preventive monitoring
        all_impacted = affected_kpis + [kpi for path in [ImpactPath(
            primary_kpi, [], [], 0, 0, 0, 0
        )] for kpi in path.affected_entities if kpi.entity_type == "KPI"]
        
        recommendations.append({
            "phase": "CONTROL",
            "priority": "MEDIUM",
            "action": f"Set up automated alerts for {len(set([kpi.id for kpi in all_impacted]))} related KPIs",
            "impact": "Early warning system for cascading failures",
            "responsible": "Analytics team",
            "type": "CONTROL_SYSTEM"
        })
        
        return recommendations
    
    def dmaic_analysis(
        self,
        primary_kpi: Entity,
        entities: List[Entity],
        relationships: List[Relationship],
        kpi_data: Dict
    ) -> Dict:
        """
        Generate complete DMAIC analysis enhanced by entity relationships.
        
        Returns structured analysis for each DMAIC phase:
        - Define: Problem statement + root causes
        - Measure: Current impact + affected KPIs
        - Analyze: Relationship chains + cascading effects
        - Improve: Recommended actions + leverage points
        - Control: Monitoring strategy
        """
        
        # Get impact analysis
        financial_impact = kpi_data.get("financial_impact", 0.0)
        impact_analysis = self.analyze_kpi_impact(
            primary_kpi, entities, relationships, financial_impact
        )
        
        return {
            "define_phase": {
                "problem_statement": f"{primary_kpi.name} has ${financial_impact:,.0f} impact",
                "scope": f"Affects {len(impact_analysis.directly_affected_kpis)} direct KPIs",
                "root_causes": [
                    {
                        "entity": rc.name,
                        "type": rc.entity_type,
                        "confidence": rc.confidence
                    }
                    for rc in impact_analysis.root_cause_chain[:3]
                ]
            },
            "measure_phase": {
                "current_impact_usd": financial_impact,
                "cascading_impact_usd": impact_analysis.total_cascading_impact_usd,
                "total_impact_usd": financial_impact + impact_analysis.total_cascading_impact_usd,
                "affected_kpi_count": len(impact_analysis.directly_affected_kpis),
                "impact_paths": len(impact_analysis.cascading_impact_paths)
            },
            "analyze_phase": {
                "directly_affected_kpis": [
                    {"name": kpi.name, "type": kpi.entity_type}
                    for kpi in impact_analysis.directly_affected_kpis
                ],
                "cascading_paths": [
                    {
                        "depth": path.depth,
                        "affected_count": path.affected_kpis_count,
                        "confidence": path.confidence,
                        "impact_estimate": path.total_impact_usd
                    }
                    for path in impact_analysis.cascading_impact_paths[:5]
                ],
                "root_cause_chain": [
                    {
                        "entity": rc.name,
                        "type": rc.entity_type
                    }
                    for rc in impact_analysis.root_cause_chain
                ]
            },
            "improve_phase": {
                "responsible_entities": [
                    {"department": re.name, "confidence": re.confidence}
                    for re in impact_analysis.responsible_entities
                ],
                "recommendations": [
                    r for r in impact_analysis.recommendations
                    if r["phase"] == "IMPROVE"
                ]
            },
            "control_phase": {
                "monitor_kpis": [
                    kpi.name for kpi in impact_analysis.directly_affected_kpis
                ],
                "alert_threshold": financial_impact * 0.2,
                "control_recommendations": [
                    r for r in impact_analysis.recommendations
                    if r["phase"] == "CONTROL"
                ]
            },
            "summary": {
                "total_potential_savings": financial_impact + impact_analysis.total_cascading_impact_usd,
                "critical_actions": len([r for r in impact_analysis.recommendations if r["priority"] == "HIGH"]),
                "monitoring_required": len(impact_analysis.directly_affected_kpis)
            }
        }
    
    def get_impact_summary(self, kpi_id: str) -> Optional[Dict]:
        """Get cached impact analysis for a KPI"""
        if kpi_id in self.impact_cache:
            analysis = self.impact_cache[kpi_id]
            return {
                "kpi": analysis.kpi_entity.name,
                "direct_impact_usd": analysis.financial_impact_usd,
                "cascading_impact_usd": analysis.total_cascading_impact_usd,
                "total_impact_usd": analysis.financial_impact_usd + analysis.total_cascading_impact_usd,
                "affected_kpis": len(analysis.directly_affected_kpis),
                "impact_paths": len(analysis.cascading_impact_paths),
                "recommendations_count": len(analysis.recommendations)
            }
        return None


def create_impact_engine(graph_engine=None, financial_engine=None) -> ImpactEngine:
    """Factory function to create Impact Engine with dependencies"""
    return ImpactEngine(graph_engine=graph_engine, financial_engine=financial_engine)
