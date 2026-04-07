# Impact Engine & Deduction Enrichment - Developer Quick Reference

## Quick Start

### Import
```python
from app.intelligence import (
    ImpactEngine,
    BusinessEntityExtractor,
    create_impact_engine,
    create_extractor,
    Entity,
    EntityTypePattern,
    ImpactType,
)
```

---

## Deduction Enrichment Usage

### Pattern: Extract Entity Types from Facts

```python
from app.intelligence import create_extractor

# Create extractor
extractor = create_extractor()

# Raw facts from deduction engine
facts = [
    {
        "subject": "Finance Department",
        "predicate": "is_responsible_for",
        "object": "Revenue KPI",
        "confidence": 0.90
    },
    {
        "subject": "NPT",
        "predicate": "depends_on",
        "object": "Equipment Maintenance",
        "confidence": 0.85
    }
]

# Enrich with entity types
result = extractor.enrich_deduction_facts(facts)

# Access results
entities = result["entities"]          # List of {name, type, confidence}
relationships = result["relationships"] # List of {source, target, type, confidence}
enriched_facts = result["enriched_facts"] # Original facts + type info
```

### Entity Types Detected
```python
EntityTypePattern.DEPARTMENT   # Finance, Operations, Drilling, etc.
EntityTypePattern.ROLE         # CEO, CFO, Manager, Engineer, etc.
EntityTypePattern.KPI          # Revenue, Cost, NPT, ROP, TRIR, etc.
EntityTypePattern.PROCESS      # Drilling, Production, Maintenance, etc.
EntityTypePattern.SYSTEM       # ERP, MES, DCS, LIMS, etc.
EntityTypePattern.EQUIPMENT    # Rig, Pipeline, Compressor, etc.
EntityTypePattern.LOCATION     # Field, Basin, Country, Well, etc.
EntityTypePattern.TEAM         # Ad-hoc team groupings
```

### Keyword Dictionaries (Customizable)
```python
# In your code
extractor.DEPARTMENT_KEYWORDS.add("my_department")
extractor.KPI_KEYWORDS.add("my_custom_kpi")
extractor.ROLE_KEYWORDS.add("my_role_title")
```

---

## Impact Engine Usage

### Pattern: Analyze Complete KPI Impact

```python
from app.intelligence import create_impact_engine, Entity

# Create engine
engine = create_impact_engine()

# Define the KPI being analyzed
revenue_kpi = Entity(
    id="revenue_id",
    name="Revenue",
    entity_type="KPI",
    confidence=0.95
)

# List of all entities (from enrichment or graph)
entities = [
    Entity("revenue_id", "Revenue", "KPI", 0.95),
    Entity("market_id", "Market Downturn", "UNKNOWN", 0.87),
    Entity("finance_id", "Finance Department", "DEPARTMENT", 0.90),
    Entity("budget_id", "Budget Cuts", "PROCESS", 0.80),
]

# List of relationships (from enrichment or graph)
relationships = []  # Could pass from graph_engine if available

# Perform analysis
analysis = engine.analyze_kpi_impact(
    kpi_entity=revenue_kpi,
    entities=entities,
    relationships=relationships,
    financial_impact=1000000.0  # From Financial Engine
)

# Access results
print(f"Direct impact: ${analysis.financial_impact_usd:,.0f}")
print(f"Cascading impact: ${analysis.total_cascading_impact_usd:,.0f}")
print(f"Affected KPIs: {[k.name for k in analysis.directly_affected_kpis]}")
print(f"Root causes: {[r.name for r in analysis.root_cause_chain]}")
print(f"Responsible: {[d.name for d in analysis.responsible_entities]}")

# Get recommendations
for rec in analysis.recommendations:
    print(f"{rec['phase']}: {rec['action']}")
```

### Analysis Output Structure
```python
class KPIImpactAnalysis:
    kpi_entity: Entity                       # The KPI being analyzed
    financial_impact_usd: float              # From Financial Engine
    directly_affected_kpis: List[Entity]     # 1-hop impacts
    cascading_impact_paths: List[ImpactPath] # Multi-hop paths
    total_cascading_impact_usd: float        # $ estimate
    responsible_entities: List[Entity]       # Departments/teams
    root_cause_chain: List[Entity]           # Ordered causes
    recommendations: List[Dict]              # DMAIC actions
```

---

## DMAIC Analysis

### Get Phase-by-Phase Guidance

```python
# Assuming analysis done above
dmaic = engine.dmaic_analysis(
    primary_kpi=revenue_kpi,
    entities=entities,
    relationships=relationships,
    kpi_data={
        "financial_impact": 1000000.0,
        "deviation_percent": -20.0,
        "affected_kpi_count": 7
    }
)

# Results for each phase
define_phase = dmaic["define_phase"]       # Problem, scope, root causes
measure_phase = dmaic["measure_phase"]     # Impact metrics
analyze_phase = dmaic["analyze_phase"]     # Paths, chains
improve_phase = dmaic["improve_phase"]     # Actions
control_phase = dmaic["control_phase"]     # Monitoring

# Common DMAIC workflow
print("DEFINE:", define_phase["problem_statement"])
print("MEASURE: Impact =", measure_phase["total_impact_usd"])
for cause in analyze_phase["root_cause_chain"]:
    print(f"  Root cause: {cause['entity']}")
for rec in improve_phase["recommendations"]:
    print(f"ACTION: {rec['action']}")
for kpi in control_phase["monitor_kpis"]:
    print(f"MONITOR: {kpi}")
```

---

## Integration with Pipeline

###Pattern: Add to Document Processing Pipeline

```python
# In app/workers/processor.py or similar

from app.intelligence import create_extractor, create_impact_engine
from app.intelligence.financial_engine import compute_financial_impact

def enrich_and_analyze_kpis(deduction_facts, kpis, doc_id):
    """
    1. Enrich facts with entity types
    2. Build impact analysis
    3. Return combined insights
    """
    
    # Step 1: Enrich deduction facts
    enricher = create_extractor()
    enriched = enricher.enrich_deduction_facts(deduction_facts)
    
    # Step 2: For each KPI, calculate impact
    engine = create_impact_engine()
    insights = {}
    
    for kpi_name, kpi_data in kpis.items():
        # Get financial impact first
        kpi_entity = Entity(
            id=kpi_name.replace(" ", "_").lower(),
            name=kpi_name,
            entity_type="KPI",
            confidence=0.95
        )
        
        # Create entity objects from enrichment
        entities = [
            Entity(e["name"].replace(" ", "_").lower(), e["name"], e["type"], e["confidence"])
            for e in enriched["entities"]
        ]
        
        # Analyze impact
        analysis = engine.analyze_kpi_impact(
            kpi_entity,
            entities,
            enriched["relationships"],
            financial_impact=kpi_data.get("impact_usd", 0.0)
        )
        
        # Get DMAIC guidance
        dmaic = engine.dmaic_analysis(
            kpi_entity, entities, enriched["relationships"], kpi_data
        )
        
        insights[kpi_name] = {
            "analysis": analysis,
            "dmaic": dmaic,
            "related_kpis": [k.name for k in analysis.directly_affected_kpis],
            "total_impact": analysis.financial_impact_usd + analysis.total_cascading_impact_usd
        }
    
    return insights
```

---

## API Integration

### Using the REST Endpoints

```bash
# 1. Enrich facts
curl -X POST http://localhost:8000/api/v2/intelligence/enrich-facts \
  -H "Content-Type: application/json" \
  -d '{
    "facts": [
      {
        "subject": "Revenue",
        "predicate": "decreased_due_to",
        "object": "Market Downturn",
        "confidence": 0.87
      }
    ]
  }'

# 2. Analyze KPI impact
curl -X POST http://localhost:8000/api/v2/intelligence/analyze-kpi-impact \
  -H "Content-Type: application/json" \
  -d '{
    "kpi_name": "Revenue",
    "entities": [
      {"id": "revenue", "name": "Revenue", "type": "KPI", "confidence": 0.95},
      {"id": "market", "name": "Market Downturn", "type": "UNKNOWN", "confidence": 0.87}
    ],
    "relationships": [],
    "financial_impact_usd": 1000000
  }'

# 3. Get DMAIC analysis
curl -X GET http://localhost:8000/api/v2/intelligence/dmaic/revenue

# 4. Check status
curl -X GET http://localhost:8000/api/v2/intelligence/status
```

---

## Common Patterns

### Pattern 1: Root Cause Analysis
```python
# "Why did KPI X drop?"
analysis = engine.analyze_kpi_impact(kpi_entity, entities, relationships)

print("Root causes:")
for root_cause in analysis.root_cause_chain:
    print(f"  - {root_cause.name} ({root_cause.entity_type})")
    print(f"    Confidence: {root_cause.confidence:.0%}")
```

### Pattern 2: Impact Cascade Estimation
```python
# "What's the total damage?"
direct = analysis.financial_impact_usd
cascading = analysis.total_cascading_impact_usd
total = direct + cascading

print(f"Direct impact: ${direct:,.0f}")
print(f"Cascading impact: ${cascading:,.0f}")
print(f"Total business impact: ${total:,.0f}")
print(f"Amplification factor: {(total/direct):.1f}x")
```

### Pattern 3: Responsible Party Identification
```python
# "Who can fix this?"
print("Responsible entities:")
for entity in analysis.responsible_entities:
    print(f"  {entity.name} (confidence: {entity.confidence:.0%})")

# Related monitoring
print("Monitor these KPIs:")
for kpi in analysis.directly_affected_kpis:
    print(f"  - {kpi.name}")
```

### Pattern 4: DMAIC Action Planning
```python
# Organize recommendations by DMAIC phase
for rec in analysis.recommendations:
    phase = rec["phase"]      # DEFINE, MEASURE, ANALYZE, IMPROVE, CONTROL
    action = rec["action"]    # What to do
    impact = rec["impact"]    # Why it matters
    responsible = rec["responsible"]  # Who does it
    
    print(f"\n{phase}: {action}")
    print(f"  Impact: {impact}")
    print(f"  Owner: {responsible}")
```

---

## Performance Tips

### 1. Cache Entity Types
```python
extractor = create_extractor()
# The extractor automatically caches entity classifications
# This speeds up repeated enrichments
```

### 2. Limit Cascading Depth
```python
# In impact_engine.py, modify function
paths = engine._find_cascading_paths(
    root_kpi, entities, relationships, max_depth=3  # Reduce if slow
)
```

### 3. Batch Process
```python
# Process multiple KPIs in order
for kpi in kpis:
    analysis = engine.analyze_kpi_impact(...)
    # Impact paths are cached internally
    # Subsequent calls are faster
```

### 4. Profile Code
```python
import time

start = time.time()
analysis = engine.analyze_kpi_impact(kpi, entities, relationships)
elapsed = time.time() - start

print(f"Analysis took {elapsed:.3f}s")
print(f"Paths found: {len(analysis.cascading_impact_paths)}")
print(f"Throughput: {len(analysis.cascading_impact_paths)/elapsed:.0f} paths/sec")
```

---

## Error Handling

### Graceful Degradation
```python
try:
    analysis = engine.analyze_kpi_impact(kpi, entities, relationships)
except Exception as e:
    logging.error(f"Impact analysis failed: {e}")
    # Fallback: return simple impact without cascading
    return {
        "kpi": kpi.name,
        "financial_impact": financial_impact_only,
        "cascading_impact": 0,
        "recommendation": "Manual review required"
    }
```

### Validation
```python
# Ensure valid inputs
if not kpi_entity or not isinstance(entities, list):
    raise ValueError("Invalid inputs to analyze_kpi_impact")

if kpi_entity not in entities:
    logging.warning(f"KPI {kpi_entity.name} not in entities list")
```

---

## Testing

### Unit Test Example
```python
from app.intelligence import create_impact_engine, Entity

def test_impact_analysis():
    engine = create_impact_engine()
    kpi = Entity("revenue", "Revenue", "KPI", 0.95)
    entities = [kpi]
    
    analysis = engine.analyze_kpi_impact(kpi, entities, [], 1000000)
    
    assert analysis.kpi_entity.name == "Revenue"
    assert analysis.financial_impact_usd == 1000000
    assert len(analysis.recommendations) > 0

test_impact_analysis()
print("✓ All tests passed")
```

---

## Troubleshooting

| Issue | Check | Fix |
|-------|-------|-----|
| No entities detected | Fact text and keywords | Add keywords to category dicts |
| Cascading paths empty | Relationships list empty | Ensure relationships passed from graph |
| Low confidence | Entity classification | Review keyword keyword dictionaries |
| Slow analysis | Graph size | Reduce max_depth parameter |
| Wrong entity type | Classification logic | Check EntityTypePattern keywords |

---

## Next Steps

1. **Test with real documents** - Run through full pipeline
2. **Integrate with dashboard** - Visualize impact paths
3. **Add GraphRAG queries** - Use actual graph relationships
4. **Tune thresholds** - Adjust similarity, confidence, depth based on data
5. **Add temporal analysis** - Track how relationships change over time

For detailed architecture, see: **PHASE1_INTELLIGENT_ENTITY_NETWORK.md**
