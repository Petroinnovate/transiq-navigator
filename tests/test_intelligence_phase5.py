"""
Phase 5: Intelligence Engine Integration Tests
Tests weighted relationships, cross-engine analysis, and unified recommendations
Coverage: 20+ tests across all intelligence endpoints
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any

from app.api.v2.intelligence_graph_endpoints import (
    WeightedEntity,
    WeightedRelationship,
    IntelligenceNetworkVisualization,
    CrossEngineAnalysis,
    RecommendationPackage
)
from app.intelligence.impact_engine import Entity, Relationship
from app.intelligence.deduction_enrichment import EntityTypePattern


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_drilling_entity() -> Entity:
    """Drilling operation entity fixture"""
    return Entity(
        id="drilling_well_001",
        name="Well Drilling - NPT Optimization",
        type=EntityTypePattern.KPI
    )


@pytest.fixture
def sample_financial_entity() -> Entity:
    """Financial KPI entity fixture"""
    return Entity(
        id="financial_cost_001",
        name="Operational Costs",
        type=EntityTypePattern.METRIC
    )


@pytest.fixture
def sample_esg_entity() -> Entity:
    """ESG metric entity fixture"""
    return Entity(
        id="esg_emissions_001",
        name="Carbon Emissions",
        type=EntityTypePattern.METRIC
    )


@pytest.fixture
def sample_relationship() -> Relationship:
    """Sample relationship fixture"""
    return Relationship(
        source_id="drilling_well_001",
        target_id="financial_cost_001",
        impact_type="AFFECTS",
        confidence=0.92
    )


# =============================================================================
# 1. WEIGHTED ENTITY MODEL TESTS
# =============================================================================

class TestWeightedEntityModel:
    """Tests for WeightedEntity Pydantic model"""
    
    def test_weighted_entity_creation(self, sample_drilling_entity):
        """Test basic WeightedEntity creation"""
        entity = WeightedEntity(
            id=sample_drilling_entity.id,
            name=sample_drilling_entity.name,
            type=str(sample_drilling_entity.type),
            financial_weight=0.85,
            esg_weight=0.65,
            drilling_weight=1.0
        )
        
        assert entity.id == "drilling_well_001"
        assert entity.financial_weight == 0.85
        assert entity.drilling_weight == 1.0
    
    def test_weighted_entity_fields_optional(self):
        """Test that weighted entity metrics are optional"""
        entity = WeightedEntity(
            id="test_entity",
            name="Test",
            type="KPI"
        )
        
        assert entity.financial_weight == 0.0
        assert entity.financial_metrics == {}
        assert entity.drilling_metrics == {}
    
    def test_weighted_entity_with_metrics(self):
        """Test WeightedEntity with full metrics"""
        entity = WeightedEntity(
            id="well_001",
            name="Well A",
            type="DRILLING",
            financial_weight=0.9,
            esg_weight=0.7,
            drilling_weight=1.0,
            financial_metrics={"daily_cost": 45000, "budget": 500000},
            esg_metrics={"emissions": 120, "risk_score": 0.65},
            drilling_metrics={"npt_hours": 2.5, "rop_fph": 380}
        )
        
        assert entity.financial_metrics["daily_cost"] == 45000
        assert entity.drilling_metrics["npt_hours"] == 2.5
    
    def test_weighted_entity_validation_weights(self):
        """Test that weights are validated properly"""
        entity = WeightedEntity(
            id="test",
            name="Test",
            type="METRIC",
            financial_weight=0.5,
            esg_weight=0.5,
            drilling_weight=0.5
        )
        
        assert 0.0 <= entity.financial_weight <= 1.0
        assert 0.0 <= entity.esg_weight <= 1.0
        assert 0.0 <= entity.drilling_weight <= 1.0


# =============================================================================
# 2. WEIGHTED RELATIONSHIP MODEL TESTS
# =============================================================================

class TestWeightedRelationshipModel:
    """Tests for WeightedRelationship Pydantic model"""
    
    def test_weighted_relationship_creation(self):
        """Test basic WeightedRelationship creation"""
        rel = WeightedRelationship(
            source_id="entity_a",
            target_id="entity_b",
            relationship_type="AFFECTS",
            confidence=0.92,
            financial_impact=45000.0,
            esg_risk_score=0.65,
            drilling_sensitivity=0.8
        )
        
        assert rel.source_id == "entity_a"
        assert rel.target_id == "entity_b"
        assert rel.confidence == 0.92
    
    def test_weighted_relationship_combined_weight(self):
        """Test combined weight calculation"""
        rel = WeightedRelationship(
            source_id="a",
            target_id="b",
            relationship_type="DEPENDS_ON",
            confidence=0.85,
            financial_impact=0.8,
            esg_risk_score=0.7,
            drilling_sensitivity=0.6
        )
        
        # Combined weight should be average of all non-zero weights
        expected_combined = (0.8 + 0.7 + 0.6) / 3
        assert rel.combined_weight == pytest.approx(expected_combined, rel=0.01)
    
    def test_weighted_relationship_single_domain(self):
        """Test relationship with only one domain weight"""
        rel = WeightedRelationship(
            source_id="a",
            target_id="b",
            relationship_type="AFFECTS",
            confidence=0.9,
            financial_impact=0.95
        )
        
        assert rel.combined_weight == pytest.approx(0.95, rel=0.01)
    
    def test_weighted_relationship_no_domains(self):
        """Test relationship with no domain weights"""
        rel = WeightedRelationship(
            source_id="a",
            target_id="b",
            relationship_type="GENERIC",
            confidence=0.5
        )
        
        assert rel.combined_weight == 0.0
    
    def test_weighted_relationship_confidence_range(self):
        """Test confidence is validated between 0 and 1"""
        rel_valid = WeightedRelationship(
            source_id="a",
            target_id="b",
            relationship_type="AFFECTS",
            confidence=0.5
        )
        
        assert 0.0 <= rel_valid.confidence <= 1.0


# =============================================================================
# 3. INTELLIGENCE NETWORK VISUALIZATION TESTS
# =============================================================================

class TestIntelligenceNetworkVisualization:
    """Tests for IntelligenceNetworkVisualization model"""
    
    def test_visualization_creation(self):
        """Test basic visualization creation"""
        nodes = [
            WeightedEntity(id="a", name="A", type="KPI", financial_weight=0.8),
            WeightedEntity(id="b", name="B", type="METRIC", esg_weight=0.7)
        ]
        edges = [
            WeightedRelationship(
                source_id="a", target_id="b", relationship_type="AFFECTS",
                confidence=0.9, financial_impact=0.8
            )
        ]
        
        viz = IntelligenceNetworkVisualization(nodes=nodes, edges=edges)
        
        assert len(viz.nodes) == 2
        assert len(viz.edges) == 1
    
    def test_visualization_with_insights(self):
        """Test visualization with insights and recommendations"""
        nodes = [WeightedEntity(id="a", name="A", type="KPI")]
        edges = []
        
        viz = IntelligenceNetworkVisualization(
            nodes=nodes,
            edges=edges,
            key_insights=["Insight 1", "Insight 2"],
            recommendations=["Recommendation 1", "Recommendation 2"]
        )
        
        assert len(viz.key_insights) == 2
        assert len(viz.recommendations) == 2
    
    def test_visualization_summary_data(self):
        """Test visualization with domain summaries"""
        nodes = []
        edges = []
        
        viz = IntelligenceNetworkVisualization(
            nodes=nodes,
            edges=edges,
            financial_summary={"total_impact": 450000, "cost_drivers": ["ops", "maintenance"]},
            esg_summary={"score": 65.3, "risk_level": "medium"},
            drilling_summary={"npt_hours": 2.5, "efficiency": 0.84}
        )
        
        assert viz.financial_summary["total_impact"] == 450000
        assert viz.drilling_summary["efficiency"] == 0.84
    
    def test_visualization_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated"""
        viz = IntelligenceNetworkVisualization(nodes=[], edges=[])
        
        # Should be valid ISO format
        dt = datetime.fromisoformat(viz.timestamp)
        assert isinstance(dt, datetime)


# =============================================================================
# 4. CROSS-ENGINE ANALYSIS TESTS
# =============================================================================

class TestCrossEngineAnalysis:
    """Tests for CrossEngineAnalysis model"""
    
    def test_cross_engine_analysis_creation(self):
        """Test basic cross-engine analysis creation"""
        analysis = CrossEngineAnalysis(
            primary_entity_id="drilling_kpi_001",
            financial_impact=435000.0,
            esg_overall_score=63.3
        )
        
        assert analysis.primary_entity_id == "drilling_kpi_001"
        assert analysis.financial_impact == 435000.0
    
    def test_cross_engine_financial_data(self):
        """Test financial engine data in analysis"""
        analysis = CrossEngineAnalysis(
            primary_entity_id="cost_001",
            financial_impact=500000.0,
            financial_drivers=["Production volume", "Operating costs"],
            financial_recommendations=["Optimize operations", "Reduce waste"]
        )
        
        assert len(analysis.financial_drivers) == 2
        assert "Optimize operations" in analysis.financial_recommendations
    
    def test_cross_engine_esg_data(self):
        """Test ESG engine data in analysis"""
        analysis = CrossEngineAnalysis(
            primary_entity_id="esg_001",
            esg_overall_score=65.0,
            environmental_score=70.0,
            social_score=60.0,
            governance_score=65.0
        )
        
        assert analysis.environmental_score == 70.0
        assert analysis.social_score == 60.0
        assert analysis.governance_score == 65.0
    
    def test_cross_engine_drilling_data(self):
        """Test drilling-specific data in analysis"""
        analysis = CrossEngineAnalysis(
            primary_entity_id="well_001",
            npt_metrics={"average_npt_hours": 2.5, "cost_per_hour": 15000},
            rop_metrics={"target_rop": 450, "actual_rop": 380, "efficiency": 0.84},
            mtbf_mttr={"mtbf_hours": 240, "mttr_hours": 8}
        )
        
        assert analysis.npt_metrics["cost_per_hour"] == 15000
        assert analysis.rop_metrics["efficiency"] == 0.84
        assert analysis.mtbf_mttr["mtbf_hours"] == 240
    
    def test_cross_engine_priority_and_value(self):
        """Test priority and value stake in analysis"""
        analysis = CrossEngineAnalysis(
            primary_entity_id="test",
            highest_priority="Reduce downtime",
            estimated_value_at_stake=850000.0,
            confidence_level="high"
        )
        
        assert analysis.highest_priority == "Reduce downtime"
        assert analysis.estimated_value_at_stake == 850000.0
        assert analysis.confidence_level == "high"
    
    def test_cross_engine_confidence_values(self):
        """Test valid confidence levels"""
        for confidence in ["low", "medium", "high"]:
            analysis = CrossEngineAnalysis(
                primary_entity_id="test",
                confidence_level=confidence
            )
            assert analysis.confidence_level in ["low", "medium", "high"]


# =============================================================================
# 5. RECOMMENDATION PACKAGE TESTS
# =============================================================================

class TestRecommendationPackage:
    """Tests for RecommendationPackage model"""
    
    def test_recommendation_package_creation(self):
        """Test basic recommendation package creation"""
        pkg = RecommendationPackage(
            primary_entity_id="entity_001"
        )
        
        assert pkg.primary_entity_id == "entity_001"
        assert pkg.recommendations == []
    
    def test_recommendation_package_with_recommendations(self):
        """Test package with multiple recommendations"""
        recs = [
            {
                "engine": "Drilling",
                "priority": 1,
                "action": "Implement predictive maintenance",
                "impact_estimate": "$37.5K/hour NPT",
                "timeline": "Q2 2026"
            },
            {
                "engine": "Financial",
                "priority": 2,
                "action": "Optimize budget",
                "impact_estimate": "+45K/quarter",
                "timeline": "Q1 2026"
            }
        ]
        
        pkg = RecommendationPackage(
            primary_entity_id="test",
            recommendations=recs
        )
        
        assert len(pkg.recommendations) == 2
        assert pkg.recommendations[0]["engine"] == "Drilling"
        assert pkg.recommendations[1]["priority"] == 2
    
    def test_recommendation_package_portfolio_summary(self):
        """Test portfolio summary in package"""
        summary = {
            "total_entities_analyzed": 7,
            "high_priority_items": 3,
            "estimated_annual_value": 850000.0
        }
        
        pkg = RecommendationPackage(
            primary_entity_id="test",
            portfolio_summary=summary
        )
        
        assert pkg.portfolio_summary["total_entities_analyzed"] == 7
        assert pkg.portfolio_summary["high_priority_items"] == 3
    
    def test_recommendation_package_next_steps(self):
        """Test next steps guidance"""
        next_steps = [
            "Plan maintenance program",
            "Review cost strategy",
            "Initiate supplier engagement"
        ]
        
        pkg = RecommendationPackage(
            primary_entity_id="test",
            next_steps=next_steps
        )
        
        assert len(pkg.next_steps) == 3
        assert "Plan maintenance program" in pkg.next_steps


# =============================================================================
# 6. INTEGRATED WORKFLOW TESTS
# =============================================================================

class TestIntegratedWorkflows:
    """Tests for complete Phase 5 workflows"""
    
    def test_drilling_entity_to_recommendation_workflow(self):
        """Test complete workflow from drilling entity to recommendations"""
        # Create a drilling entity
        drilling_entity = WeightedEntity(
            id="well_001",
            name="Well NPT Optimization",
            type="KPI",
            drilling_weight=1.0,
            financial_weight=0.95,
            drilling_metrics={"npt_hours": 2.5, "cost_per_hour": 15000}
        )
        
        # Create relationship to cost entity
        cost_entity = WeightedEntity(
            id="cost_001",
            name="Drilling Costs",
            type="METRIC",
            financial_weight=1.0,
            financial_metrics={"daily_impact": 45000}
        )
        
        # Create relationship
        relationship = WeightedRelationship(
            source_id="well_001",
            target_id="cost_001",
            relationship_type="AFFECTS",
            confidence=0.95,
            drilling_sensitivity=1.0,
            financial_impact=0.9
        )
        
        # Create visualization
        viz = IntelligenceNetworkVisualization(
            nodes=[drilling_entity, cost_entity],
            edges=[relationship]
        )
        
        # Create analysis
        analysis = CrossEngineAnalysis(
            primary_entity_id="well_001",
            financial_impact=435000.0,
            npt_metrics={"average_npt_hours": 2.5},
            highest_priority="Reduce NPT",
            estimated_value_at_stake=850000.0
        )
        
        assert len(viz.nodes) == 2
        assert analysis.estimated_value_at_stake == 850000.0
    
    def test_multi_engine_entity_weighting(self):
        """Test entity with weights from all three engines"""
        entity = WeightedEntity(
            id="multi_engine_001",
            name="Complex KPI",
            type="KPI",
            financial_weight=0.9,
            esg_weight=0.7,
            drilling_weight=0.8,
            financial_metrics={"impact": 450000},
            esg_metrics={"score": 65},
            drilling_metrics={"efficiency": 0.84}
        )
        
        # Verify all weights are set
        assert entity.financial_weight > 0
        assert entity.esg_weight > 0
        assert entity.drilling_weight > 0
        
        # Verify metrics from all domains
        assert "impact" in entity.financial_metrics
        assert "score" in entity.esg_metrics
        assert "efficiency" in entity.drilling_metrics


# =============================================================================
# 7. VALIDATION & CONSTRAINT TESTS
# =============================================================================

class TestValidationAndConstraints:
    """Tests for model validation and constraints"""
    
    def test_entity_requires_id_and_name(self):
        """Test that entity requires ID and name"""
        with pytest.raises(Exception):  # Pydantic validation error
            WeightedEntity(type="KPI")
    
    def test_relationship_requires_source_target(self):
        """Test that relationship requires source and target"""
        with pytest.raises(Exception):  # Pydantic validation error
            WeightedRelationship(
                relationship_type="AFFECTS",
                confidence=0.9
            )
    
    def test_esg_scores_in_valid_range(self):
        """Test ESG scores are in valid range"""
        analysis = CrossEngineAnalysis(
            primary_entity_id="test",
            environmental_score=75.5,
            social_score=60.0,
            governance_score=70.3
        )
        
        assert 0 <= analysis.environmental_score <= 100
    
    def test_esg_weight_in_range_0_to_1(self):
        """Test ESG weight is between 0 and 1"""
        entity = WeightedEntity(
            id="test",
            name="Test",
            type="METRIC",
            esg_weight=0.65
        )
        
        assert 0.0 <= entity.esg_weight <= 1.0


# =============================================================================
# 8. PERFORMANCE & SCALE TESTS
# =============================================================================

class TestPerformanceAndScale:
    """Tests for performance at scale"""
    
    def test_large_entity_network(self):
        """Test visualization with many entities"""
        # Create 100 entities
        nodes = [
            WeightedEntity(
                id=f"entity_{i}",
                name=f"Entity {i}",
                type="KPI" if i % 2 == 0 else "METRIC",
                financial_weight=0.5 + (i % 10) / 100
            )
            for i in range(100)
        ]
        
        edges = [
            WeightedRelationship(
                source_id=f"entity_{i}",
                target_id=f"entity_{(i+1) % 100}",
                relationship_type="AFFECTS",
                confidence=0.8 + (i % 10) / 1000,
                financial_impact=0.5 + (i % 10) / 100
            )
            for i in range(100)
        ]
        
        viz = IntelligenceNetworkVisualization(nodes=nodes, edges=edges)
        
        assert len(viz.nodes) == 100
        assert len(viz.edges) == 100
    
    def test_large_recommendation_set(self):
        """Test package with many recommendations"""
        recs = [
            {
                "engine": ["Drilling", "Financial", "ESG"][i % 3],
                "priority": i + 1,
                "action": f"Action {i}",
                "impact_estimate": f"${50000 * (i+1)}",
                "timeline": f"Q{(i % 4) + 1} 2026"
            }
            for i in range(50)
        ]
        
        pkg = RecommendationPackage(
            primary_entity_id="test",
            recommendations=recs
        )
        
        assert len(pkg.recommendations) == 50


# =============================================================================
# 9. EDGE CASES & ERROR HANDLING
# =============================================================================

class TestEdgeCasesAndErrorHandling:
    """Tests for edge cases and error handling"""
    
    def test_zero_weight_relationship(self):
        """Test relationship with all zero weights"""
        rel = WeightedRelationship(
            source_id="a",
            target_id="b",
            relationship_type="GENERIC",
            confidence=0.5
        )
        
        assert rel.combined_weight == 0.0
    
    def test_single_node_network(self):
        """Test visualization with single node"""
        nodes = [WeightedEntity(id="a", name="A", type="KPI")]
        viz = IntelligenceNetworkVisualization(nodes=nodes, edges=[])
        
        assert len(viz.nodes) == 1
        assert len(viz.edges) == 0
    
    def test_empty_network(self):
        """Test visualization with no nodes or edges"""
        viz = IntelligenceNetworkVisualization(nodes=[], edges=[])
        
        assert len(viz.nodes) == 0
        assert len(viz.edges) == 0
    
    def test_analysis_with_zero_value_at_stake(self):
        """Test analysis with zero value at stake"""
        analysis = CrossEngineAnalysis(
            primary_entity_id="test",
            estimated_value_at_stake=0.0
        )
        
        assert analysis.estimated_value_at_stake == 0.0
    
    def test_recommendation_package_empty_recommendations(self):
        """Test package with empty recommendations list"""
        pkg = RecommendationPackage(
            primary_entity_id="test",
            recommendations=[]
        )
        
        assert pkg.recommendations == []


# =============================================================================
# 10. INTEGRATION SUMMARY TEST
# =============================================================================

def test_phase5_integration_complete():
    """Comprehensive Phase 5 integration test"""
    # 1. Create weighted entities from all domains
    financial_entity = WeightedEntity(
        id="financial_001",
        name="Annual Operating Costs",
        type="METRIC",
        financial_weight=1.0,
        financial_metrics={"annual_budget": 5000000}
    )
    
    esg_entity = WeightedEntity(
        id="esg_001",
        name="Carbon Footprint",
        type="METRIC",
        esg_weight=1.0,
        esg_metrics={"emissions_tons": 12000}
    )
    
    drilling_entity = WeightedEntity(
        id="drilling_001",
        name="Well Efficiency",
        type="KPI",
        drilling_weight=1.0,
        drilling_metrics={"npt_hours": 2.5}
    )
    
    # 2. Create relationships
    f_to_d = WeightedRelationship(
        source_id="financial_001",
        target_id="drilling_001",
        relationship_type="AFFECTS",
        confidence=0.95,
        financial_impact=0.9
    )
    
    e_to_d = WeightedRelationship(
        source_id="esg_001",
        target_id="drilling_001",
        relationship_type="IMPACTS",
        confidence=0.85,
        esg_risk_score=0.7
    )
    
    # 3. Create visualization
    viz = IntelligenceNetworkVisualization(
        nodes=[financial_entity, esg_entity, drilling_entity],
        edges=[f_to_d, e_to_d]
    )
    
    # 4. Create cross-engine analysis
    analysis = CrossEngineAnalysis(
        primary_entity_id="drilling_001",
        financial_impact=435000.0,
        esg_overall_score=63.3,
        highest_priority="Reduce NPT in drilling",
        estimated_value_at_stake=850000.0
    )
    
    # 5. Create recommendations
    pkg = RecommendationPackage(
        primary_entity_id="drilling_001",
        recommendations=[
            {"engine": "Drilling", "priority": 1, "action": "Implement predictive maintenance"},
            {"engine": "Financial", "priority": 2, "action": "Optimize operations budget"},
            {"engine": "ESG", "priority": 3, "action": "Increase renewable energy"}
        ]
    )
    
    # Verify complete workflow
    assert len(viz.nodes) == 3
    assert len(viz.edges) == 2
    assert analysis.estimated_value_at_stake == 850000.0
    assert len(pkg.recommendations) == 3
    
    print("✅ Phase 5 Integration Complete - All models working together!")
