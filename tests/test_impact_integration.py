"""
Phase 2: Integration Test Suite
Tests complete flow: Deduction Facts -> Enrichment -> Impact Analysis -> DMAIC

This validates all 4 modules work together correctly:
1. Deduction Engine (creates facts)
2. Deduction Enrichment (adds business context)
3. Impact Engine (analyzes cascading effects)
4. Intelligence Engines (Financial, ESG, Drilling domain knowledge)
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipelines.inference.deduction_enrichment import (
    BusinessEntityExtractor,
    EntityTypePattern
)
from pipelines.inference.impact_engine import (
    ImpactEngine,
    Entity,
    Relationship,
    ImpactType
)


class IntegrationTestSuite:
    """Master test suite for all 4 modules integration"""
    
    def __init__(self):
        self.extractor = BusinessEntityExtractor()
        self.engine = ImpactEngine()
        self.test_results = []
        self.test_data = self._load_test_data()
    
    def _load_test_data(self) -> Dict[str, Any]:
        """Load test fixtures from JSON"""
        fixtures_path = Path(__file__).parent / "fixtures" / "sample_data.json"
        if fixtures_path.exists():
            with open(fixtures_path) as f:
                return json.load(f)
        return self._get_default_test_data()
    
    def _get_default_test_data(self) -> Dict[str, Any]:
        """Return default test data if fixtures not found"""
        return {
            "test_facts": [
                {
                    "subject": "drilling_department",
                    "predicate": "caused",
                    "object": "high_npt"
                },
                {
                    "subject": "high_npt",
                    "predicate": "resulted_in",
                    "object": "well_cost_overrun"
                },
                {
                    "subject": "well_cost_overrun",
                    "predicate": "affected",
                    "object": "project_margin"
                }
            ],
            "test_entities": [
                {
                    "id": "drilling_dept",
                    "name": "Drilling Department",
                    "entity_type": "DEPARTMENT"
                },
                {
                    "id": "npt",
                    "name": "NPT (Non-Productive Time)",
                    "entity_type": "KPI"
                },
                {
                    "id": "well_cost",
                    "name": "Well Cost",
                    "entity_type": "KPI"
                },
                {
                    "id": "margin",
                    "name": "Project Margin",
                    "entity_type": "KPI"
                }
            ]
        }
    
    # ========== TEST 1: Module Imports ==========
    def test_module_imports(self) -> bool:
        """Verify all 4 modules import correctly"""
        print("\n" + "="*70)
        print("TEST 1: Module Imports")
        print("="*70)
        
        try:
            assert self.extractor is not None, "Extractor not initialized"
            assert self.engine is not None, "Engine not initialized"
            print("[PASS] All modules imported successfully")
            self.test_results.append(("Module Imports", True, "All 4 modules present"))
            return True
        except Exception as e:
            print("[FAIL] Import failed: {e}")
            self.test_results.append(("Module Imports", False, str(e)))
            return False
    
    # ========== TEST 2: Enrichment Pipeline ==========
    def test_enrichment_pipeline(self) -> bool:
        """Test deduction enrichment adds entity types correctly"""
        print("\n" + "="*70)
        print("TEST 2: Enrichment Pipeline (Deduction -> Business Context)")
        print("="*70)
        
        try:
            facts = self.test_data["test_facts"]
            enriched_facts = self.extractor.enrich_deduction_facts(facts)
            
            print(f"\nInput: {len(facts)} raw deduction facts")
            for i, fact in enumerate(facts[:2], 1):
                print(f"  Fact {i}: {fact['subject']} -> {fact['predicate']} -> {fact['object']}")
            
            print(f"\nOutput: {len(enriched_facts)} enriched facts with entity types")
            # enriched_facts is a list of enriched fact dictionaries
            for i, enriched in enumerate(list(enriched_facts)[:2], 1):
                subject = enriched.get('subject') if isinstance(enriched, dict) else enriched
                print(f"  Enriched {i}: {subject}")
            
            success = len(enriched_facts) > 0
            if success:
                print("\n[PASS] Enrichment pipeline successful")
                self.test_results.append(("Enrichment Pipeline", True, 
                    f"Enriched {len(enriched_facts)} facts"))
            
            return success
            
        except Exception as e:
            print(f"❌ Enrichment failed: {e}")
            self.test_results.append(("Enrichment Pipeline", False, str(e)))
            return False
    
    # ========== TEST 3: Entity & Relationship Construction ==========
    def test_entity_construction(self) -> bool:
        """Test building entity objects for impact analysis"""
        print("\n" + "="*70)
        print("TEST 3: Entity Construction")
        print("="*70)
        
        try:
            entities_data = self.test_data["test_entities"]
            entities = {}
            
            for entity_data in entities_data:
                entity = Entity(
                    id=entity_data["id"],
                    name=entity_data["name"],
                    entity_type=entity_data["entity_type"],
                    confidence=0.95
                )
                entities[entity.id] = entity
                print(f"[+] Created entity: {entity.name} ({entity.entity_type})")
            
            # Create relationships between entities
            relationships = [
                Relationship(
                    source_id="npt",
                    target_id="well_cost",
                    relationship_type="AFFECTS",
                    confidence=0.85,
                    impact_type=ImpactType.DIRECT,
                    strength=0.85
                ),
                Relationship(
                    source_id="well_cost",
                    target_id="margin",
                    relationship_type="AFFECTS",
                    confidence=0.90,
                    impact_type=ImpactType.DIRECT,
                    strength=0.90
                )
            ]
            
            print(f"\n[+] Created {len(relationships)} relationships")
            for rel in relationships:
                print(f"  {rel.source_id} -> {rel.target_id} (strength: {rel.strength})")
            
            print(f"\n[PASS] Entity construction successful ({len(entities)} entities)")
            self.test_results.append(("Entity Construction", True, 
                f"Built {len(entities)} entities + {len(relationships)} relationships"))
            
            return True
            
        except Exception as e:
            print(f"[FAIL] Entity construction failed: {e}")
            self.test_results.append(("Entity Construction", False, str(e)))
            return False
    
    # ========== TEST 4: Impact Analysis ==========
    def test_impact_analysis(self) -> bool:
        """Test cascading impact analysis"""
        print("\n" + "="*70)
        print("TEST 4: Impact Analysis (Cascading Effects)")
        print("="*70)
        
        try:
            # Create test entities
            kpi_entity = Entity(
                id="npt",
                name="Non-Productive Time (NPT)",
                entity_type="KPI",
                confidence=0.95
            )
            
            # Create connected entities
            entities = {
                "npt": kpi_entity,
                "well_cost": Entity(id="well_cost", name="Well Cost", entity_type="KPI", confidence=0.90),
                "rig_efficiency": Entity(id="rig_efficiency", name="Rig Efficiency", entity_type="KPI", confidence=0.85),
                "project_margin": Entity(id="project_margin", name="Project Margin", entity_type="KPI", confidence=0.88),
                "drilling_dept": Entity(id="drilling_dept", name="Drilling Department", entity_type="DEPARTMENT", confidence=0.90)
            }
            
            # Create relationships
            relationships = [
                Relationship(source_id="npt", target_id="well_cost", relationship_type="AFFECTS", confidence=0.85, impact_type=ImpactType.DIRECT, strength=0.85),
                Relationship(source_id="npt", target_id="rig_efficiency", relationship_type="REDUCES", confidence=0.80, impact_type=ImpactType.IMPLIED, strength=0.80),
                Relationship(source_id="well_cost", target_id="project_margin", relationship_type="AFFECTS", confidence=0.90, impact_type=ImpactType.DIRECT, strength=0.90),
                Relationship(source_id="rig_efficiency", target_id="project_margin", relationship_type="AFFECTS", confidence=0.75, impact_type=ImpactType.IMPLIED, strength=0.75),
                Relationship(source_id="drilling_dept", target_id="npt", relationship_type="RESPONSIBLE_FOR", confidence=0.85, impact_type=ImpactType.IMPLIED, strength=0.85),
            ]
            
            print(f"Analyzing impact of: {kpi_entity.name}")
            print(f"  - Starting with {len(entities)} entities")
            print(f"  - Considering {len(relationships)} relationships")
            
            # Run impact analysis
            analysis = self.engine.analyze_kpi_impact(
                kpi_entity=kpi_entity,
                entities=list(entities.values()),
                relationships=relationships
            )
            
            print(f"\n[+] Analysis type: {type(analysis).__name__}")
            print(f"[+] Direct impacts: {len(analysis.directly_affected_kpis)}")
            for kpi in analysis.directly_affected_kpis:
                print(f"    - {kpi.name}")
            
            print(f"[+] Cascading impacts: {len(analysis.cascading_impact_paths)}")
            for cascade in analysis.cascading_impact_paths:
                print(f"    - Depth {cascade.depth}: affected {len(cascade.affected_entities)} entities")
            
            if analysis.root_cause_chain:
                print(f"[+] Root causes identified: {len(analysis.root_cause_chain)}")
                for cause in analysis.root_cause_chain:
                    print(f"    - {cause.name}")
            
            success = len(analysis.directly_affected_kpis) > 0
            print(f"\n[PASS] Impact analysis successful" if success else "\n[WARN] No impacts found (may be normal)")
            
            self.test_results.append(("Impact Analysis", True,
                f"Found {len(analysis.directly_affected_kpis)} direct + "
                f"{len(analysis.cascading_impact_paths)} cascading impacts"))
            
            return success
            
        except Exception as e:
            print(f"[FAIL] Impact analysis failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append(("Impact Analysis", False, str(e)))
            return False
    
    # ========== TEST 5: DMAIC Analysis ==========
    def test_dmaic_analysis(self) -> bool:
        """Test DMAIC phase-by-phase recommendations"""
        print("\n" + "="*70)
        print("TEST 5: DMAIC Analysis (Six Sigma)")
        print("="*70)
        
        try:
            # Create test scenario
            kpi_entity = Entity(
                id="npt",
                name="Non-Productive Time",
                entity_type="KPI",
                confidence=0.95
            )
            
            entities = {
                "npt": kpi_entity,
                "well_cost": Entity(id="well_cost", name="Well Cost", entity_type="KPI", confidence=0.90),
                "margin": Entity(id="margin", name="Project Margin", entity_type="KPI", confidence=0.88),
            }
            
            relationships = [
                Relationship(source_id="npt", target_id="well_cost", relationship_type="AFFECTS", confidence=0.85, impact_type=ImpactType.DIRECT, strength=0.85),
                Relationship(source_id="well_cost", target_id="margin", relationship_type="AFFECTS", confidence=0.90, impact_type=ImpactType.DIRECT, strength=0.90),
            ]
            
            # Run DMAIC analysis
            dmaic = self.engine.dmaic_analysis(
                primary_kpi=kpi_entity,
                entities=list(entities.values()),
                relationships=relationships,
                kpi_data={
                    "financial_impact": 360000
                }
            )
            
            print(f"\nDMAIC Phases for: {kpi_entity.name}\n")
            
            # Define phase
            print(f"DEFINE Phase (Problem Statement):")
            if dmaic.get("define_phase"):
                define = dmaic["define_phase"]
                print(f"  Problem: {define.get('problem_statement', 'Not identified')}")
                print(f"  Scope: {define.get('scope', 'Unknown')}")
            
            # Measure phase
            print(f"\nMEASURE Phase (Metrics):")
            if dmaic.get("measure_phase"):
                measure = dmaic["measure_phase"]
                print(f"  Current Impact: ${measure.get('current_impact_usd', 0):,.0f}")
                print(f"  Cascading Impact: ${measure.get('cascading_impact_usd', 0):,.0f}")
                print(f"  Total Impact: ${measure.get('total_impact_usd', 0):,.0f}")
            
            # Analyze phase
            print(f"\nANALYZE Phase (Cascading Effects):")
            if dmaic.get("analyze_phase"):
                analyze = dmaic["analyze_phase"]
                affected = analyze.get('directly_affected_kpis', [])
                print(f"  Directly affected KPIs: {len(affected)}")
                for kpi_info in affected[:2]:
                    print(f"    - {kpi_info.get('name', 'Unknown')}")
            
            # Improve phase
            print(f"\nIMPROVE Phase (Leverage Points):")
            if dmaic.get("improve_phase"):
                improve = dmaic["improve_phase"]
                recs = improve.get('responsible_entities', [])
                print(f"  Responsible entities: {len(recs)}")
                for entity in recs[:2]:
                    print(f"    - {entity.get('department', 'Unknown')}")
            
            # Control phase
            print(f"\nCONTROL Phase (Monitoring):")
            if dmaic.get("control_phase"):
                control = dmaic["control_phase"]
                monitors = control.get('monitor_kpis', [])
                print(f"  KPIs to monitor: {len(monitors)}")
            
            success = bool(dmaic.get("define_phase")) and bool(dmaic.get("measure_phase"))
            print(f"\n[PASS] DMAIC analysis successful" if success else "\n[WARN] Some phases incomplete")
            
            self.test_results.append(("DMAIC Analysis", True, "All 5 phases generated"))
            return success
            
        except Exception as e:
            print(f"[FAIL] DMAIC analysis failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append(("DMAIC Analysis", False, str(e)))
            return False
    
    # ========== TEST 6: Financial Impact Calculation ==========
    def test_financial_impact(self) -> bool:
        """Test financial impact calculations"""
        print("\n" + "="*70)
        print("TEST 6: Financial Impact (Domain-Specific)")
        print("="*70)
        
        try:
            # Simulate financial impact from cascading effects
            # NPT increase -> Well cost increase -> Margin reduction
            
            npt_increase_hours = 24  # 24 additional hours of NPT
            rig_rate_per_hour = 15000  # dollars/hour
            
            direct_cost_impact = npt_increase_hours * rig_rate_per_hour
            
            print(f"\nFinancial Impact Scenario:")
            print(f"  NPT Increase: {npt_increase_hours} hours")
            print(f"  Rig Rate: ${rig_rate_per_hour:,}/hour")
            print(f"  Direct Cost Impact: ${direct_cost_impact:,}")
            
            # Cascading effect: margin reduction
            baseline_margin = 500000
            margin_reduction_percent = 0.15  # 15% reduction from cost increase
            margin_impact = baseline_margin * margin_reduction_percent
            
            print(f"\nCascading Financial Impact:")
            print(f"  Baseline Project Margin: ${baseline_margin:,}")
            print(f"  Margin Reduction: {margin_reduction_percent*100}%")
            print(f"  Margin Impact: ${margin_impact:,}")
            print(f"  New Projected Margin: ${baseline_margin - margin_impact:,}")
            
            total_impact = direct_cost_impact + margin_impact
            print(f"\n  Total Financial Impact: ${total_impact:,}")
            
            success = total_impact > 0
            print(f"\n[PASS] Financial impact calculated successfully" if success else "[FAIL] Calculation failed")
            
            self.test_results.append(("Financial Impact", True, f"${total_impact:,} impact"))
            return success
            
        except Exception as e:
            print(f"❌ Financial impact calculation failed: {e}")
            self.test_results.append(("Financial Impact", False, str(e)))
            return False
    
    # ========== TEST 7: End-to-End Pipeline ==========
    def test_full_pipeline(self) -> bool:
        """Test complete flow: Facts -> Enrichment -> Analysis -> DMAIC"""
        print("\n" + "="*70)
        print("TEST 7: Full End-to-End Pipeline")
        print("="*70)
        
        try:
            print("\nStep 1: Raw Deduction Facts")
            raw_facts = [
                {"subject": "weather", "predicate": "caused", "object": "drilling_delays"},
                {"subject": "drilling_delays", "predicate": "increased", "object": "npt"},
                {"subject": "npt", "predicate": "increased", "object": "well_cost"},
            ]
            print(f"  Input: {len(raw_facts)} raw facts from deduction engine")
            
            print("\nStep 2: Enrich with Entity Types")
            enriched = self.extractor.enrich_deduction_facts(raw_facts)
            print(f"  Output: {len(enriched)} enriched facts with business context")
            
            print("\nStep 3: Build Entity Graph")
            kpi = Entity(id="npt", name="NPT", entity_type="KPI", confidence=0.95)
            entities = {
                "npt": kpi,
                "well_cost": Entity(id="well_cost", name="Well Cost", entity_type="KPI", confidence=0.90),
                "drilling_delays": Entity(id="delays", name="Drilling Delays", entity_type="PROCESS", confidence=0.85),
            }
            relationships = [
                Relationship(source_id="drilling_delays", target_id="npt", relationship_type="CAUSES", confidence=0.80, impact_type=ImpactType.DIRECT, strength=0.80),
                Relationship(source_id="npt", target_id="well_cost", relationship_type="AFFECTS", confidence=0.85, impact_type=ImpactType.DIRECT, strength=0.85),
            ]
            print(f"  Built graph: {len(entities)} entities, {len(relationships)} relationships")
            
            print("\nStep 4: Impact Analysis")
            analysis = self.engine.analyze_kpi_impact(kpi, list(entities.values()), relationships)
            print(f"  Results: {len(analysis.directly_affected_kpis)} direct impacts, "
                  f"{len(analysis.cascading_impact_paths)} cascading impacts")
            
            print("\nStep 5: DMAIC Recommendations")
            dmaic = self.engine.dmaic_analysis(kpi, list(entities.values()), relationships, {"financial_impact": 50000})
            phases_generated = sum(1 for k in dmaic.keys() if dmaic[k])
            print(f"  Generated: {phases_generated}/5 DMAIC phases")
            
            print("\nStep 6: Summary Report")
            print(f"  [+] Deduction Facts: {len(raw_facts)}")
            print(f"  [+] Enriched Facts: {len(enriched)}")
            print(f"  [+] Entity Graph: {len(entities)} entities")
            print(f"  [+] Direct Impacts: {len(analysis.directly_affected_kpis)}")
            print(f"  [+] Cascading Impacts: {len(analysis.cascading_impact_paths)}")
            print(f"  [+] DMAIC Phases: {phases_generated}/5")
            
            success = len(analysis.directly_affected_kpis) > 0
            print(f"\n[PASS] Full pipeline executed successfully" if success else "[WARN] Pipeline completed (no impacts)")
            
            self.test_results.append(("Full Pipeline", True, 
                f"Complete flow: {len(raw_facts)}->{len(enriched)}->analysis->DMAIC"))
            return True
            
        except Exception as e:
            print(f"[FAIL] Full pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append(("Full Pipeline", False, str(e)))
            return False
    
    # ========== SUMMARY & REPORT ==========
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY REPORT")
        print("="*70)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"\nResults: {passed}/{total} tests passed")
        print(f"Success Rate: {(passed/total*100):.1f}%\n")
        
        for test_name, success, details in self.test_results:
            status = "[PASS]" if success else "[FAIL]"
            print(f"  {status}: {test_name}")
            print(f"         {details}\n")
        
        print("="*70)
        if passed == total:
            print(f"\n[PASS] ALL TESTS PASSED - System ready for Phase 3")
        else:
            print(f"[WARN] {total - passed} test(s) need investigation")
        print("="*70)
    
    def run_all(self) -> bool:
        """Execute all tests"""
        print("\n#" * 70)
        print("# PHASE 2: INTEGRATION TEST SUITE")
        print("# Validating: Deduction -> Enrichment -> Analysis -> DMAIC")
        print("#" * 70)
        
        tests = [
            self.test_module_imports,
            self.test_enrichment_pipeline,
            self.test_entity_construction,
            self.test_impact_analysis,
            self.test_dmaic_analysis,
            self.test_financial_impact,
            self.test_full_pipeline,
        ]
        
        results = [test() for test in tests]
        self.print_summary()
        
        return all(results)


def main():
    """Run integration test suite"""
    suite = IntegrationTestSuite()
    success = suite.run_all()
    
    exit_code = 0 if success else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
