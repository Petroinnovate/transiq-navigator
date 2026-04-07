"""
Phase 2: Real-World Scenario - Drilling NPT Impact
This demonstrates the complete integration on a realistic Oil & Gas scenario.

Scenario Context:
- A West Africa offshore drilling operation
- Recent drilling delays caused by weather
- Delays increased Non-Productive Time (NPT)
- Need to understand cascading impact on well cost and project margin
- DMAIC recommendations for improvement
"""

import json
from pathlib import Path
from typing import Dict, Any
import sys

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipelines.inference.deduction_enrichment import (
    BusinessEntityExtractor
)
from pipelines.inference.impact_engine import (
    ImpactEngine,
    Entity,
    Relationship,
    ImpactType
)


class DrillingNPTScenario:
    """Real-world drilling NPT scenario walkthrough"""
    
    def __init__(self):
        self.extractor = BusinessEntityExtractor()
        self.engine = ImpactEngine()
        
        # Load or use default financial context
        self.financial_context = {
            "rig_rate_per_hour": 15000,
            "baseline_well_cost": 2500000,
            "baseline_margin": 500000,
            "npt_increase_hours": 24,
            "weather_delay_hours": 8
        }
    
    def generate_scenario_facts(self) -> list:
        """Generate realistic deduction facts from a drilling operation"""
        return [
            {
                "subject": "weather_forecast",
                "predicate": "indicated",
                "object": "storm_approaching"
            },
            {
                "subject": "storm_approaching",
                "predicate": "caused",
                "object": "drilling_suspended"
            },
            {
                "subject": "drilling_suspended",
                "predicate": "resulted_in",
                "object": "24_hours_downtime"
            },
            {
                "subject": "24_hours_downtime",
                "predicate": "at_rate",
                "object": "rig_cost_15k_per_hour"
            },
            {
                "subject": "rig_cost_15k_per_hour",
                "predicate": "equates_to",
                "object": "360k_direct_cost"
            },
            {
                "subject": "360k_direct_cost",
                "predicate": "increased",
                "object": "well_cost"
            },
            {
                "subject": "well_cost",
                "predicate": "reduced",
                "object": "project_margin"
            },
            {
                "subject": "reduced_margin",
                "predicate": "triggered",
                "object": "cost_control_meeting"
            },
            {
                "subject": "cost_control_meeting",
                "predicate": "assigned_to",
                "object": "drilling_manager"
            },
            {
                "subject": "drilling_manager",
                "predicate": "responsible_for",
                "object": "npt_mitigation"
            }
        ]
    
    def print_scenario_header(self):
        """Print scenario context"""
        print("\n" + "="*70)
        print("DRILLING NPT IMPACT SCENARIO")
        print("="*70)
        print("""
CONTEXT:
- Offshore drilling operation: West Africa
- Recent weather caused 24-hour drilling suspension  
- Suspension increased Non-Productive Time (NPT)
- Rig rate: $15,000/hour
- Direct cost impact: $360,000 (24 hrs × $15k)

OBJECTIVE:
Analyze cascading impact through:
  1. Direct costs (NPT hours × rig rate)
  2. Well cost increase
  3. Project margin reduction
  4. Responsible parties and DMAIC recommendations

KEY METRICS:
- Baseline Well Cost: ${:,.0f}
- Baseline Project Margin: ${:,.0f}
- Expected Margin Impact: 15% reduction
""".format(
            self.financial_context["baseline_well_cost"],
            self.financial_context["baseline_margin"]
        ))
    
    def step_1_extract_facts(self):
        """Step 1: Extract deduction facts from scenario"""
        print("\n" + "-"*70)
        print("STEP 1: Deduction Facts Extraction")
        print("-"*70)
        
        facts = self.generate_scenario_facts()
        
        print(f"\nExtracted {len(facts)} facts from drilling operation report:\n")
        for i, fact in enumerate(facts, 1):
            print(f"  Fact {i:2}: {fact['subject']:30} -> {fact['predicate']:15} -> {fact['object']}")
        
        return facts
    
    def step_2_enrich_facts(self, facts: list) -> dict:
        """Step 2: Enrich facts with entity types and relationships"""
        print("\n" + "-"*70)
        print("STEP 2: Facts Enrichment (Add Business Context)")
        print("-"*70)
        
        enrichment_result = self.extractor.enrich_deduction_facts(facts)
        enriched_facts = enrichment_result.get("enriched_facts", [])
        
        print(f"\nEnriched {len(enriched_facts)} facts with entity types:\n")
        for i, enriched_fact in enumerate(enriched_facts[:5], 1):  # Show first 5
            subject = enriched_fact.get('subject') if isinstance(enriched_fact, dict) else "Unknown"
            print(f"  Enriched {i}: {subject}")
        
        if len(enriched_facts) > 5:
            print(f"  ... and {len(enriched_facts) - 5} more facts")
        
        return enrichment_result
    
    def step_3_build_entity_graph(self):
        """Step 3: Build entity graph for impact analysis"""
        print("\n" + "-"*70)
        print("STEP 3: Entity Graph Construction")
        print("-"*70)
        
        # Define entities for this scenario
        entities = {
            "npt": Entity(
                id="npt",
                name="Non-Productive Time",
                entity_type="KPI",
                confidence=0.95
            ),
            "well_cost": Entity(
                id="well_cost",
                name="Well Cost",
                entity_type="KPI",
                confidence=0.92
            ),
            "project_margin": Entity(
                id="project_margin",
                name="Project Margin",
                entity_type="KPI",
                confidence=0.90
            ),
            "rig_efficiency": Entity(
                id="rig_efficiency",
                name="Rig Efficiency",
                entity_type="KPI",
                confidence=0.88
            ),
            "weather": Entity(
                id="weather",
                name="Weather Conditions",
                entity_type="LOCATION",
                confidence=0.95
            ),
            "drilling_dept": Entity(
                id="drilling_dept",
                name="Drilling Department",
                entity_type="DEPARTMENT",
                confidence=0.90
            ),
            "drilling_manager": Entity(
                id="drilling_manager",
                name="Drilling Manager",
                entity_type="ROLE",
                confidence=0.85
            ),
            "cost_control": Entity(
                id="cost_control",
                name="Cost Control Process",
                entity_type="PROCESS",
                confidence=0.88
            )
        }
        
        # Define relationships
        relationships = [
            Relationship(
                source_id="weather",
                target_id="npt",
                relationship_type="CAUSES",
                confidence=0.92,
                impact_type=ImpactType.DIRECT,
                strength=0.92
            ),
            Relationship(
                source_id="npt",
                target_id="well_cost",
                relationship_type="AFFECTS",
                confidence=0.88,
                impact_type=ImpactType.DIRECT,
                strength=0.88
            ),
            Relationship(
                source_id="well_cost",
                target_id="project_margin",
                relationship_type="AFFECTS",
                confidence=0.90,
                impact_type=ImpactType.DIRECT,
                strength=0.90
            ),
            Relationship(
                source_id="npt",
                target_id="rig_efficiency",
                relationship_type="REDUCES",
                confidence=0.80,
                impact_type=ImpactType.IMPLIED,
                strength=0.80
            ),
            Relationship(
                source_id="drilling_dept",
                target_id="npt",
                relationship_type="RESPONSIBLE_FOR",
                confidence=0.90,
                impact_type=ImpactType.IMPLIED,
                strength=0.90
            ),
            Relationship(
                source_id="drilling_manager",
                target_id="drilling_dept",
                relationship_type="MANAGES",
                confidence=0.95,
                impact_type=ImpactType.IMPLIED,
                strength=0.95
            ),
            Relationship(
                source_id="cost_control",
                target_id="well_cost",
                relationship_type="MONITORS",
                confidence=0.85,
                impact_type=ImpactType.IMPLIED,
                strength=0.85
            )
        ]
        
        print(f"\nBuilt entity graph:")
        print(f"  Entities:      {len(entities)}")
        for entity_id, entity in entities.items():
            print(f"    - {entity.name:30} ({entity.entity_type})")
        
        print(f"\n  Relationships: {len(relationships)}")
        for rel in relationships:
            print(f"    - {rel.source_id:20} -> {rel.target_id:20} "
                  f"({rel.relationship_type}, strength={rel.strength})")
        
        return entities, relationships
    
    def step_4_impact_analysis(self, npt_entity, entities, relationships):
        """Step 4: Analyze cascading impacts"""
        print("\n" + "-"*70)
        print("STEP 4: Cascading Impact Analysis")
        print("-"*70)
        
        analysis = self.engine.analyze_kpi_impact(
            target_kpi=npt_entity,
            all_entities=entities,
            relationships=relationships
        )
        
        print(f"\nAnalysis of: {npt_entity.name}\n")
        
        # Direct impacts
        print(f"Direct Impacts (1-hop relationships):")
        if analysis.directly_affected_kpis:
            for affected in analysis.directly_affected_kpis:
                print(f"  ✓ {affected.name}")
        else:
            print(f"  (None identified)")
        
        # Cascading impacts
        print(f"\nCascading Impacts (multi-hop relationships):")
        if analysis.cascading_impacts:
            for cascade in analysis.cascading_impacts:
                depth = cascade['depth']
                path = " -> ".join(cascade['path'])
                confidence = cascade.get('confidence', 'N/A')
                print(f"  ✓ Depth {depth}: {path} (confidence: {confidence})")
        else:
            print(f"  (None identified)")
        
        # Root causes
        print(f"\nRoot Causes (why NPT increased):")
        if analysis.root_causes:
            for cause in analysis.root_causes:
                print(f"  ✓ {cause.name}")
        else:
            print(f"  (None identified)")
        
        # Responsible parties
        print(f"\nResponsible Parties (who can mitigate):")
        if analysis.responsible_entities:
            for responsible in analysis.responsible_entities:
                print(f"  ✓ {responsible.name}")
        else:
            print(f"  (None identified)")
        
        return analysis
    
    def step_5_financial_impact(self) -> Dict[str, Any]:
        """Step 5: Calculate concrete financial impacts"""
        print("\n" + "-"*70)
        print("STEP 5: Financial Impact Calculation")
        print("-"*70)
        
        npt_hours = self.financial_context["npt_increase_hours"]
        rig_rate = self.financial_context["rig_rate_per_hour"]
        baseline_margin = self.financial_context["baseline_margin"]
        baseline_cost = self.financial_context["baseline_well_cost"]
        
        # Direct cost impact
        direct_cost = npt_hours * rig_rate
        margin_reduction_percent = 0.15  # Conservative estimate
        margin_impact = baseline_margin * margin_reduction_percent
        
        # Calculations
        new_well_cost = baseline_cost + direct_cost
        new_margin = baseline_margin - margin_impact
        
        print(f"""
Direct Cost Impact:
  NPT Increase:        {npt_hours} hours
  Rig Rate:            ${rig_rate:,}/hour
  Direct Cost:         ${direct_cost:,}

Well Cost Impact:
  Baseline:            ${baseline_cost:,}
  Increase:            ${direct_cost:,}
  New Well Cost:       ${new_well_cost:,}

Project Margin Impact:
  Baseline Margin:     ${baseline_margin:,}
  Margin Reduction:    {margin_reduction_percent*100:.0f}%
  Margin Impact:       ${margin_impact:,}
  New Projected:       ${new_margin:,}

TOTAL FINANCIAL IMPACT: ${direct_cost + margin_impact:,}
  Direct Cost:         ${direct_cost:,}
  Cascading Effect:    ${margin_impact:,}
""")
        
        return {
            "direct_cost": direct_cost,
            "margin_impact": margin_impact,
            "total_impact": direct_cost + margin_impact,
            "new_well_cost": new_well_cost,
            "new_margin": new_margin
        }
    
    def step_6_dmaic_recommendations(self, analysis, npt_entity, entities, relationships):
        """Step 6: Generate DMAIC phase recommendations"""
        print("\n" + "-"*70)
        print("STEP 6: DMAIC Action Plan")
        print("-"*70)
        
        dmaic = self.engine.dmaic_analysis(
            kpi_entity=npt_entity,
            related_kpis=list(entities.values()),
            relationships=relationships,
            financial_context=self.financial_context
        )
        
        print("\nDEFINE PHASE (Problem Definition):")
        if dmaic.get("define"):
            define = dmaic["define"]
            print(f"  Problem: {define.get('problem', 'Excessive NPT reducing well economics')}")
            print(f"  Scope: Affects {len(define.get('affected_kpis', []))} KPIs")
            print(f"  Impact: ${self.financial_context.get('npt_increase_hours', 24) * self.financial_context.get('rig_rate_per_hour', 15000):,}")
        
        print("\nMEASURE PHASE (Metrics):")
        if dmaic.get("measure"):
            measure = dmaic["measure"]
            metrics = measure.get('key_metrics', [])
            for metric in metrics[:3]:
                print(f"  ✓ {metric}")
            if dmaic['measure'].get('baseline'):
                print(f"  Baseline: {dmaic['measure']['baseline']}")
        
        print("\nANALYZE PHASE (Root Causes):")
        if dmaic.get("analyze"):
            analyze = dmaic["analyze"]
            causes = analyze.get('root_causes', [])
            for cause in causes[:3]:
                print(f"  ✓ {cause}")
        
        print("\nIMPROVE PHASE (Recommended Solutions):")
        if dmaic.get("improve"):
            improve = dmaic["improve"]
            recommendations = improve.get('recommendations', [])
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"  {i}. {rec}")
        
        print("\nCONTROL PHASE (Monitoring & Prevention):")
        if dmaic.get("control"):
            control = dmaic["control"]
            measures = control.get('control_measures', [])
            for measure in measures[:3]:
                print(f"  ✓ {measure}")
        
        return dmaic
    
    def print_executive_summary(self, analysis, financial_impact, dmaic):
        """Print executive-level summary"""
        print("\n" + "="*70)
        print("EXECUTIVE SUMMARY")
        print("="*70)
        
        print(f"""
INCIDENT:
Weather-caused drilling suspension: 24 hours downtime

ROOT CAUSES:
{chr(10).join(f"  • {cause.name}" for cause in analysis.root_causes[:3]) if analysis.root_causes else "  • Weather conditions (unforeseeable)"}

CASCADING IMPACT PATH:
  Weather -> NPT -> Well Cost -> Project Margin

FINANCIAL IMPACT:
  Total: ${financial_impact['total_impact']:,}
    • Direct Cost: ${financial_impact['direct_cost']:,} (24 hrs × $15k/hr)
    • Cascading Effect: ${financial_impact['margin_impact']:,} (15% margin reduction)

RESPONSIBLE PARTIES:
{chr(10).join(f"  • {entity.name}" for entity in analysis.responsible_entities[:2]) if analysis.responsible_entities else "  • Drilling Department"}

RECOMMENDED ACTIONS (IMPROVE PHASE):
  1. Implement 48-hour weather forecast monitoring
  2. Establish crew pre-positioning protocols
  3. Develop contingency well design options
  4. Increase equipment redundancy for critical systems

EXPECTED OUTCOMES:
  • Reduce average NPT by 15-20% over next 12 months
  • Improve project margin recovery to baseline levels
  • Establish predictable weather delay response procedures
""")
    
    def run_complete_scenario(self):
        """Execute complete scenario walkthrough"""
        self.print_scenario_header()
        
        # Step 1: Extract facts
        facts = self.step_1_extract_facts()
        
        # Step 2: Enrich facts
        enriched_facts = self.step_2_enrich_facts(facts)
        
        # Step 3: Build entity graph
        entities, relationships = self.step_3_build_entity_graph()
        
        # Step 4: Impact analysis
        npt_entity = entities["npt"]
        analysis = self.step_4_impact_analysis(npt_entity, entities, relationships)
        
        # Step 5: Financial impact
        financial_impact = self.step_5_financial_impact()
        
        # Step 6: DMAIC recommendations
        dmaic = self.step_6_dmaic_recommendations(analysis, npt_entity, entities, relationships)
        
        # Executive summary
        self.print_executive_summary(analysis, financial_impact, dmaic)
        
        print("\n" + "="*70)
        print("✅ SCENARIO COMPLETE - NPT Impact Fully Analyzed")
        print("="*70)


def main():
    """Run drilling NPT scenario"""
    scenario = DrillingNPTScenario()
    scenario.run_complete_scenario()


if __name__ == "__main__":
    main()
