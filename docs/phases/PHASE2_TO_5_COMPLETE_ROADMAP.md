# Phase 2-5 Execution Roadmap: Complete & Integrated

**Status**: Phase 1 Complete → Phase 2 Starting  
**Total Remaining Work**: ~8-10 hours across 4 phases  
**Goal**: Fully integrated intelligent impact analysis system  

---

## **Phase 2: Integration Test + Demo** (1-2 hours)

### Objective
Validate all 4 modules work together with realistic data, create proof-of-concept

### What We're Building
A test scenario showing complete flow end-to-end

### Deliverables
- [ ] Integration test script (`tests/test_impact_integration.py`)
- [ ] Sample test data (realistic KPI + entity data)
- [ ] Demo output showing: facts → enrichment → analysis → DMAIC
- [ ] Success metrics defined

### Success Criteria
- ✅ All 4 modules import and initialize
- ✅ Data flows correctly between modules
- ✅ Impact analysis produces valid output
- ✅ DMAIC recommendations are coherent
- ✅ Financial impact calculations match Financial Engine

### Key Testing Points
```
Test 1: Enrichment works on deduction facts
  Input: Raw facts from deduction engine
  Output: Facts with entity types + relationships
  
Test 2: Impact analysis with enriched data
  Input: Enriched facts + entities
  Output: Impact analysis with cascading paths
  
Test 3: DMAIC analysis is phase-complete
  Input: KPI + impact analysis
  Output: Define/Measure/Analyze/Improve/Control phases filled
  
Test 4: Financial impact flows from Financial Engine
  Input: Financial impact from Financial Engine
  Output: Shows in cascading impact calculation
  
Test 5: Real-world scenario end-to-end
  Input: Oil & Gas report facts
  Output: Root causes + DMAIC plan
```

### Files to Create
```
tests/
├── test_impact_integration.py      (Main integration test)
├── fixtures/
│   ├── sample_kpis.json           (Test KPI data)
│   ├── sample_facts.json          (Deduction facts)
│   └── sample_entities.json       (Entity reference data)
└── test_scenarios/
    ├── drilling_npt_scenario.py   (Drilling-focused)
    ├── financial_scenario.py      (Finance-focused)
    └── esg_scenario.py            (ESG-focused)
```

### Timeline
- Create test fixtures: 20 min
- Write integration tests: 30 min
- Create demo scenarios: 30 min
- Run & validate: 20 min

**Blocker Dependencies**: None - all code exists

---

## **Phase 3: Dashboard Integration** (1-2 hours)

### Objective
Expose impact analysis results to the dashboard via new visualization endpoints

### What We're Building
2-3 new REST endpoints that return data formatted for visualization

### Deliverables
- [ ] New endpoint: `GET /api/v2/intelligence/dashboard/{kpi_id}`
- [ ] New endpoint: `GET /api/v2/intelligence/impact-network/{kpi_id}`
- [ ] New endpoint: `POST /api/v2/intelligence/batch-analysis`
- [ ] Pydantic models for visualization responses
- [ ] OpenAPI documentation

### Success Criteria
- ✅ Endpoints return visualization-ready JSON
- ✅ Impact paths include node/edge information
- ✅ Confidence metrics included
- ✅ DMAIC phases formatted for UI
- ✅ Batch analysis for multiple KPIs

### New Endpoints
```python
# 1. Dashboard Summary
GET /api/v2/intelligence/dashboard/{kpi_id}
Response: {
  "kpi_summary": {...},
  "impact_metrics": {...},
  "cascading_impacts": [cascade1, cascade2, ...],
  "dmaic_phases": {...},
  "recommendations": {...}
}

# 2. Impact Network (for visualization)
GET /api/v2/intelligence/impact-network/{kpi_id}
Response: {
  "nodes": [
    {"id": "revenue", "label": "Revenue", "type": "KPI", ...},
    {"id": "market", "label": "Market Downturn", "type": "UNKNOWN", ...}
  ],
  "edges": [
    {"source": "market", "target": "revenue", "type": "AFFECTS", ...}
  ],
  "layout": "force-directed"
}

# 3. Batch Analysis
POST /api/v2/intelligence/batch-analysis
Request: {"kpi_ids": ["revenue", "cost", "npt"]}
Response: {
  "analyses": [
    {"kpi": "revenue", "impact": 1000000, ...},
    {"kpi": "cost", "impact": 500000, ...},
    ...
  ],
  "summary": {...}
}
```

### Files to Create
```
app/api/v2/
├── dashboard_endpoints.py           (Visualization endpoints)
└── visualization_models.py          (Pydantic response models)
```

### Integration Points
```
Dashboard Frontend ← Visualization Endpoints ← Impact Engine
                       ↑
                  Graph Data (from Phase 4)
                  Intelligence Engines (from Phase 5)
```

### Timeline
- Design response models: 20 min
- Implement 3 endpoints: 30 min
- Add batch processing: 20 min
- Test with sample data: 30 min

**Blocker Dependencies**: Phase 2 (needs validated data structure)

---

## **Phase 4: GraphRAG Deep Integration** (2-3 hours)

### Objective
Connect Impact Engine to actual GraphRAG relationships for live analysis

### What We're Building
Integration layer that queries graph_engine for real relationships

### Deliverables
- [ ] Integration module: `app/intelligence/graph_integration.py`
- [ ] Graph relationship queries for impact analysis
- [ ] Real-time entity linking from deduction to existing entities
- [ ] Multi-tenant relationship discovery
- [ ] Caching for performance

### Success Criteria
- ✅ Reads actual relationships from graph_entities/graph_relationships
- ✅ Finds duplicate entities and links them
- ✅ Uses graph confidence scores in impact calculation
- ✅ Queries are efficient (< 500ms)
- ✅ Handles multi-tenant isolation

### Key Components
```python
# 1. Query Graph for Relationships
def get_entity_relationships(entity_id, max_depth=4):
    """Query actual graph for entity relationships"""
    # Replaces hardcoded relationships in test data
    
# 2. Link Deduction Entities to Graph
def link_entity_to_graph(entity_name, entity_type):
    """Find if entity already exists in graph"""
    # Returns existing entity_id or creates new
    
# 3. Calculate Impact using Graph Data
def analyze_with_graph_relationships(kpi_entity):
    """Use real graph relationships instead of inferred ones"""
    # Replaces enriched_facts relationships with graph queries
    
# 4. Multi-hop Relationship Discovery
def discover_connected_entities(entity_id, relationship_type, max_depth):
    """Find all entities connected through relationships"""
    # Uses actual graph_relationships table
```

### Files to Create/Modify
```
New:
app/intelligence/graph_integration.py       (Graph query layer)

Modified:
app/intelligence/impact_engine.py           (Use graph instead of enriched facts)
app/processors/deduction.py                 (Link facts to graph entities)
```

### Integration Flow
```
Deduction Facts
    ↓
Enrichment (add types)
    ↓
Link to Graph → Query Existing Relationships
    ↓
Build Impact Analysis with Real Graph Data
    ↓
Return Confidence Scores from Graph
```

### Timeline
- Design graph query patterns: 30 min
- Implement graph_integration module: 45 min
- Modify impact_engine for graph: 30 min
- Query optimization + caching: 30 min

**Blocker Dependencies**: Phase 2 (needs validated logic), Phase 3 (optional - for visualization)

---

## **Phase 5: Intelligence Engine Integration** (2-3 hours)

### Objective
Connect Financial, ESG, and Drilling engines to impact analysis for domain-specific insights

### What We're Building
Integration layer that enhances impact with domain-specific calculations

### Deliverables
- [ ] `app/intelligence/integrated_analysis.py` - Main orchestrator
- [ ] Financial impact multipliers for cascading effects
- [ ] ESG impact propagation
- [ ] Drilling impact factors
- [ ] Combined recommendations from all engines
- [ ] Cross-engine conflict resolution

### Success Criteria
- ✅ Financial impact uses actual engine calculations
- ✅ ESG pillar impacts identified automatically
- ✅ Drilling KPI impacts recognized
- ✅ Recommendations from all engines merged
- ✅ No duplicate recommendations
- ✅ Cross-domain insights enabled

### Integration Pattern
```python
class IntegratedIntelligenceAnalysis:
    """
    Orchestrates Financial + ESG + Drilling + Impact engines
    """
    
    def analyze_kpi(self, kpi):
        # Step 1: Base impact analysis
        impact = self.impact_engine.analyze_kpi_impact(kpi)
        
        # Step 2: Financial impact calculations
        financial = self.financial_engine.compute_financial_impact(
            kpi, impact.affected_kpis
        )
        
        # Step 3: ESG impact if applicable
        if self.is_esg_kpi(kpi):
            esg = self.esg_engine.analyze_esg_impact(kpi)
            impact.esg_implications = esg
        
        # Step 4: Drilling impact if applicable
        if self.is_drilling_kpi(kpi):
            drilling = self.drilling_engine.analyze_drilling_impact(kpi)
            impact.drilling_implications = drilling
        
        # Step 5: Merge recommendations
        all_recs = self.merge_recommendations(
            impact, financial, esg, drilling
        )
        
        return IntegratedAnalysis(impact, financial, esg, drilling, all_recs)
```

### New Endpoints
```python
# Integrated analysis with all engines
POST /api/v2/intelligence/full-analysis
  → Returns: Impact + Financial + ESG + Drilling + Merged DMAIC

# Domain-specific analysis
GET /api/v2/intelligence/financial-impact/{kpi_id}
GET /api/v2/intelligence/esg-impact/{kpi_id}
GET /api/v2/intelligence/drilling-impact/{kpi_id}
```

### Files to Create/Modify
```
New:
app/intelligence/integrated_analysis.py     (Orchestrator)
app/api/v2/integrated_endpoints.py         (Combined endpoints)

Modified:
app/intelligence/__init__.py                (Export orchestrator)
```

### Integration Flow
```
KPI → Impact Engine
   ↓
   ├→ Financial Engine ($ impact of cascading)
   ├→ ESG Engine (Environmental/Social/Governance)
   ├→ Drilling Engine (Domain-specific metrics)
   └→ Merge Recommendations
   
   Output: Unified view across all domains
```

### Timeline
- Design orchestrator pattern: 30 min
- Financial engine integration: 30 min
- ESG engine integration: 30 min
- Drilling engine integration: 30 min
- Recommendation merging logic: 30 min

**Blocker Dependencies**: Phase 2 (validated logic), Phase 4 (optional - for real relationships)

---

## **Execution Strategy: Parallel vs Sequential**

### **RECOMMENDED: Sequential with Validation Feedback**

```
Phase 2 (2 hrs) ─┐
                 ├→ Run & Validate ──┐
                 │                   │
                 └───────────────────┤
                                     │
Phase 3 (2 hrs) ─┐                   │
                 ├→ Run & Validate ──┤──→ Continue
                 │                   │
         (builds on Phase 2) ────────┤
                                     │
Phase 4 (3 hrs) ─┐                   │
                 ├→ Run & Validate ──┤
                 │                   │
         (builds on Phase 3)────────┤
                                     │
Phase 5 (3 hrs) ─┐                   │
                 ├→ Run & Validate ──┘
                 │
         (builds on Phase 4)
```

### **WHY Sequential?**
- ✅ Each phase validates previous work
- ✅ Easier debugging if something breaks
- ✅ Can adjust approach based on learnings
- ✅ Less risk of cascading failures
- ✅ Clearer success/failure points

**Total Time**: 10 hours  
**Quality Gate**: Each phase must pass tests before next starts

---

## **Critical Checkpoints**

### **After Phase 2**
```
Questions to answer:
☐ Do all modules import correctly?
☐ Does data flow correctly between modules?
☐ Are impact calculations realistic?
☐ Does DMAIC output make sense?
☐ Can we reproduce with real data?

If NO to any: Debug before continuing to Phase 3
```

### **After Phase 3**
```
Questions to answer:
☐ Do visualization endpoints return correct format?
☐ Can frontend consume the responses?
☐ Are impact networks visualizable?
☐ Does batch analysis scale?

If NO to any: Adjust models before continuing to Phase 4
```

### **After Phase 4**
```
Questions to answer:
☐ Can we query actual graph relationships?
☐ Does entity linking work correctly?
☐ Are real graph scores affecting impact?
☐ Is performance acceptable (< 500ms)?

If NO to any: Optimize queries before continuing to Phase 5
```

### **After Phase 5**
```
Questions to answer:
☐ Do all engines contribute meaningfully?
☐ Are recommendations from all engines present?
☐ Are cascading impacts calculated correctly?
☐ Does cross-domain analysis work?

If NO to any: Adjust integration before production
```

---

## **Risk Mitigation**

### **Risk 1: Phase X breaks everything**
**Mitigation**: Each phase has isolated tests, git commits checkpoint

### **Risk 2: Real graph relationships don't match expectations**
**Mitigation**: Phase 4 has fallback to enriched relationships

### **Risk 3: Intelligence engines conflict**
**Mitigation**: Phase 5 has explicit conflict resolution logic

### **Risk 4: Performance degrades with real data**
**Mitigation**: Caching + batch queries implemented per phase

### **Risk 5: Running out of time/resources**
**Mitigation**: Phase 2-3 are highest priority (MVP), Phase 4-5 are enhancements

---

## **Success Definition**

### **Minimum (MVP)**
- ✅ Phase 2: Core integration test passes
- ✅ Phase 3: Dashboard can visualize impact
- **Decision point**: Launch MVP or continue?

### **Standard**
- ✅ Phase 2-3: MVP working
- ✅ Phase 4: Using real graph relationships
- **Good enough for production**

### **Complete**
- ✅ Phase 2-5: All integrated
- ✅ All intelligence engines connected
- ✅ Domain-specific insights enabled
- **Full system capabilities unlocked**

---

## **Resource Allocation**

```
Total: 10 hours
├── Phase 2: 2 hours    (20%)  ← Highest priority (MVP blocker)
├── Phase 3: 2 hours    (20%)  ← Critical for value delivery
├── Phase 4: 3 hours    (30%)  ← Foundation for full system
└── Phase 5: 3 hours    (30%)  ← Advanced capabilities

Recommended Daily Allocation:
Day 1: Phase 2 (2 hrs) + Phase 3 (1 hr) = 3 hours
Day 2: Phase 3 (1 hr) + Phase 4 (1.5 hrs) = 2.5 hours
Day 3: Phase 4 (1.5 hrs) + Phase 5 (1.5 hrs) = 3 hours
Day 4: Phase 5 (1.5 hrs) + Testing (1 hr) = 2.5 hours
```

---

## **How to Not Forget**

### **Git Commit Strategy**
```
Phase 2 complete commit: "Phase 2: Integration test + demo"
Phase 3 complete commit: "Phase 3: Dashboard integration endpoints"
Phase 4 complete commit: "Phase 4: GraphRAG live relationships"
Phase 5 complete commit: "Phase 5: Intelligence engine integration"
```

### **Documentation Strategy**
```
After each phase:
- Update this checklist
- Create phase completion summary
- Document any deviations from plan
- Log learnings for next phase
```

### **Testing Strategy**
```
After each phase:
- Run test_impact_integration.py
- Validate all new endpoints work
- Check performance benchmarks
- Ensure no regressions
```

---

## **Current Status**

```
Phase 1: COMPLETE ✅
├── Impact Engine ........................... ✅
├── Deduction Enrichment .................... ✅
├── API Endpoints ........................... ✅
└── Documentation ........................... ✅

Phase 2: STARTING 🔄
├── Integration test script ................. ← NEXT
├── Test data fixtures .....................
├── Demo scenarios .........................
└── Validation ............................

Phase 3: PLANNED ⏳
├── Visualization endpoints ................
├── Dashboard integration ..................
└── Response models .......................

Phase 4: PLANNED ⏳
├── Graph integration module ...............
├── Entity linking .........................
└── Relationship queries ...................

Phase 5: PLANNED ⏳
├── Integrated orchestrator ................
├── Engine integration .....................
└── Merged recommendations .................
```

---

## **Next Step: Start Phase 2**

Ready to create the integration test framework?

Key files to create:
1. `tests/test_impact_integration.py` - Main test suite
2. `tests/fixtures/sample_data.json` - Test data
3. `tests/test_scenarios/` - Real-world examples

**Proceed?** ✅ YES / ⏸️ PAUSE / 🔄 ADJUST PLAN
