# GraphRAG for TransIQ - User Guide

## Overview

GraphRAG (Graph-based Retrieval-Augmented Generation) is an advanced knowledge graph system integrated into TransIQ that enables:

- **Entity Resolution**: Automatically deduplicate and link entities across documents
- **Knowledge Graph**: Build a unified graph of entities and their relationships
- **Multi-hop Reasoning**: Find indirect connections between entities
- **Graph Analytics**: Analyze entity importance, detect anomalies, find communities
- **Intelligent Search**: Query the graph to answer complex questions

## How It Works

### 1. Document Processing Pipeline

```
Document → Deduction Engine → Facts Extraction
                                      ↓
                          Fact-to-Graph Converter
                                      ↓
                          Entity Resolution & Deduplication
                                      ↓
                          GraphRAG Storage
                                      ↓
                    Knowledge Graph (GraphEntity, GraphRelationship)
```

### 2. Fact Processing

When you upload a document with deduction enabled:

1. **Extraction**: Deduction engine extracts facts (subject-predicate-object triples)
2. **Conversion**: Facts are converted to entities and relationships
3. **Resolution**: Entities are matched and deduplicated across documents
4. **Storage**: Deduplicated entities and relationships are stored in the graph
5. **Analytics**: Graph is analyzed for centrality, communities, anomalies

## Using GraphRAG APIs

### Entity Search

**Endpoint**: `POST /api/v2/graph/entities/search`

Find entities by name:

```bash
curl -X POST http://localhost:8000/api/v2/graph/entities/search \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Apple",
    "entity_type": "ORGANIZATION",
    "limit": 10
  }'
```

Response:
```json
{
  "query": "Apple",
  "results": [
    {
      "id": "entity-123",
      "name": "Apple Inc",
      "type": "ORGANIZATION",
      "mentions": 45,
      "confidence": 88
    }
  ],
  "count": 1
}
```

### Get Entity Profile

**Endpoint**: `GET /api/v2/graph/entities/{entity_id}`

Get full profile including statistics and relationships:

```bash
curl -X GET "http://localhost:8000/api/v2/graph/entities/entity-123" \
  -H "X-API-Key: your-api-key"
```

Response:
```json
{
  "entity": {
    "id": "entity-123",
    "name": "Apple Inc",
    "type": "ORGANIZATION",
    "aliases": ["Apple", "Apple Computer Inc"],
    "properties": {},
    "created_at": "2026-03-27T10:30:00"
  },
  "statistics": {
    "id": "entity-123",
    "canonical_name": "Apple Inc",
    "entity_type": "ORGANIZATION",
    "mention_count": 45,
    "avg_confidence": 88,
    "aliases": ["Apple", "Apple Computer Inc"],
    "mention_locations": [
      {
        "doc_id": "doc-1",
        "chunk_id": "chunk-5",
        "text": "Apple Inc manufactures...",
        "confidence": 90
      }
    ]
  },
  "relationships": [
    {
      "direction": "outgoing",
      "source": "entity-123",
      "target": "entity-456",
      "type": "OWNS",
      "target_name": "Beats Electronics",
      "confidence": 85,
      "mention_count": 3
    }
  ],
  "mention_count": 45
}
```

### Search Relationships

**Endpoint**: `POST /api/v2/graph/relationships/search`

Find relationships by type:

```bash
curl -X POST http://localhost:8000/api/v2/graph/relationships/search \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "OWNS",
    "limit": 10
  }'
```

### Find Paths Between Entities

**Endpoint**: `POST /api/v2/graph/paths`

Find all paths connecting two entities:

```bash
curl -X POST http://localhost:8000/api/v2/graph/paths \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "source_entity_id": "entity-123",
    "target_entity_id": "entity-789",
    "max_depth": 5
  }'
```

Response:
```json
{
  "source": "entity-123",
  "target": "entity-789",
  "paths": [
    {
      "entities": ["entity-123", "entity-456", "entity-789"],
      "relationships": [
        {
          "id": "rel-1",
          "type": "OWNS",
          "confidence": 85
        },
        {
          "id": "rel-2",
          "type": "LOCATED_IN",
          "confidence": 90
        }
      ],
      "length": 2,
      "relevance": 0.5
    }
  ],
  "count": 1
}
```

### Get Most Central Entities

**Endpoint**: `POST /api/v2/graph/analytics/centrality`

Find the most important entities by various metrics:

```bash
curl -X POST http://localhost:8000/api/v2/graph/analytics/centrality \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "metric": "degree",
    "limit": 10
  }'
```

Supported metrics:
- `degree`: Number of connections (in + out)
- `closeness`: Average distance to other entities
- `betweenness`: How often entity appears in shortest paths

### Detect Anomalies

**Endpoint**: `GET /api/v2/graph/analytics/anomalies`

Detect unusual patterns in the graph:

```bash
curl -X GET http://localhost:8000/api/v2/graph/analytics/anomalies \
  -H "X-API-Key: your-api-key"
```

Detects:
- Entities with unusually high degree (hub entities)
- Relationships with unusually low confidence
- Entities with contradictory relationships

### Analyze Entity Impact

**Endpoint**: `GET /api/v2/graph/analytics/impact/{entity_id}`

Understand how important an entity is to the overall graph:

```bash
curl -X GET "http://localhost:8000/api/v2/graph/analytics/impact/entity-123" \
  -H "X-API-Key: your-api-key"
```

Response:
```json
{
  "entity_id": "entity-123",
  "entity_name": "Apple Inc",
  "direct_relationships": 12,
  "reachable_entities": 156,
  "reachable_entity_ids": ["entity-456", "entity-789", ...],
  "graph_penetration": 0.45
}
```

## Python Integration

### Using GraphStorage Directly

```python
from app.storage.graph_storage import GraphStorage
from app.processors.graph_rag import GraphAnalytics

# Integrate facts into graph
with GraphStorage() as graph:
    result = graph.integrate_facts(
        facts=[
            {
                "subject": "Apple Inc",
                "predicate": "owns",
                "object": "Beats Electronics",
                "confidence": 0.9
            }
        ],
        doc_id="doc-123"
    )
    
    # Search entities
    results = graph.search_entities("Apple", "ORGANIZATION", limit=10)
    
    # Find related entities
    related = graph.find_related_entities("entity-123", max_depth=3)

# Analyze graph
with GraphAnalytics() as analytics:
    # Find paths
    paths = analytics.find_paths("entity-123", "entity-789")
    
    # Get central entities
    top = analytics.get_top_central_entities("degree", limit=10)
    
    # Detect anomalies
    anomalies = analytics.detect_anomalies()
```

### Using Entity Resolver

```python
from app.processors.graph_rag import EntityResolver

with EntityResolver() as resolver:
    # Resolve and deduplicate entities
    entity_id = resolver.resolve_entity("Apple Inc", "ORGANIZATION", doc_id="doc-123")
    
    # Find similar entities
    similar = resolver.find_similar_entities("Apple Corporation")
    
    # Merge duplicates
    merged_id = resolver.merge_entities("primary-entity-id", ["dup-1", "dup-2"])
    
    # Add aliases
    resolver.add_alias("entity-123", "Apple Inc")
```

## Advanced Features

### Multi-hop Queries

Find complex relationships spanning multiple entities:

```python
with GraphAnalytics() as analytics:
    # Find indirect connections
    paths = analytics.find_paths(
        source_id="person-123",    # CEO
        target_id="location-456",   # Country
        max_depth=5                 # Up to 5 hops
    )
    
    # Analyze: Person → Company → Location
    # This finds how the CEO is connected to countries where the company operates
```

### Community Detection

Identify clusters of closely-connected entities:

```python
with GraphAnalytics() as analytics:
    components = analytics.find_connected_components()
    
    # Find largest community
    largest = max(components, key=len)
    print(f"Largest community has {len(largest)} entities")
```

### Data Quality Monitoring

Check and improve graph quality:

```python
with GraphStorage() as graph:
    # Get quality metrics
    quality = graph.get_data_quality_metrics()
    print(f"Quality score: {quality['quality_score']:.2%}")
    print(f"Low confidence rels: {quality['low_confidence_relationships']}")
    
    # Auto-merge duplicates
    merged = graph.find_and_merge_duplicates(threshold=0.85)
    print(f"Merged {merged} entities")
```

## Configuration

### Environment Variables

```bash
# GraphRAG settings
GRAPHRAG_ENTITY_MATCH_THRESHOLD=0.85  # Similarity threshold for entity matching
GRAPHRAG_MIN_CONFIDENCE=30             # Minimum confidence for relationships
GRAPHRAG_AUTO_RESOLVE_DUPLICATES=true # Auto-merge duplicates
```

### Advanced Settings

Edit `app/config/settings.py`:

```python
# Entity resolver
ENTITY_SIMILARITY_THRESHOLD = 0.85
ENTITY_TYPE_WEIGHT = 0.2  # How much entity type matters in matching

# Graph analytics
MAX_PATH_DEPTH = 10
ANOMALY_DETECTION_THRESHOLD = 2.0  # Standard deviations from mean

# Performance
GRAPH_BATCH_SIZE = 100  # Entities processed per batch
CACHE_TTL = 3600  # Cache expiration (seconds)
```

## Performance Tuning

### For Large Graphs (>100k entities)

1. **Enable relationship indexing**: Pre-compute centrality metrics
2. **Use path caching**: Cache frequently-queried paths
3. **Batch operations**: Process entities in batches
4. **Periodic maintenance**: Schedule duplicate resolution and cleanup

```python
from app.workers.graph_processing import resolve_entity_duplicates, analyze_graph_health

# Schedule periodic maintenance
celery_beat.add_periodic_task(
    crontab(hour=2, minute=0),  # Run at 2 AM daily
    resolve_entity_duplicates.s(threshold=0.85)
)
```

### For Real-time Queries

1. **Use connection pooling**: Multiple DB connections
2. **Enable query caching**: Redis-backed query results
3. **Async processing**: Offload analytics to background tasks
4. **Index optimization**: Ensure indexes on frequently-queried fields

## Troubleshooting

### Too Many Duplicates

Increase entity resolution threshold:

```python
with EntityResolver() as resolver:
    merged = resolver.auto_merge_duplicates(threshold=0.9)
```

### Slow Path Queries

For large graphs, limit search depth:

```python
paths = analytics.find_paths(source_id, target_id, max_depth=3)
```

Or use shortest path only:

```python
shortest = analytics.shortest_path(source_id, target_id)
```

### Memory Issues with Large Documents

Process in chunks:

```python
chunk_size = 100
for i in range(0, len(facts), chunk_size):
    graph.integrate_facts(facts[i:i+chunk_size], doc_id)
```

## Examples

### Example 1: Find Companies Owned by a Person

```python
with GraphStorage() as graph:
    # Find the person
    person_results = graph.search_entities("Steve Jobs", "PERSON")
    person_id = person_results[0]["id"]
    
    # Get their relationships
    rels = graph.graph_engine.get_relationships(person_id, "outgoing")
    
    # Find OWNS relationships to ORGANIZATIONS
    companies = [
        r for r in rels
        if r["type"] == "OWNS"
        and r["target_type"] == "ORGANIZATION"
    ]
    
    for company in companies:
        print(f"Owns: {company['target_name']} (confidence: {company['confidence']}%)")
```

### Example 2: Find Indirect Business Relationships

```python
with GraphAnalytics() as analytics:
    # Find all paths between two companies
    paths = analytics.find_paths(
        source_id="apple-id",
        target_id="microsoft-id",
        max_depth=4
    )
    
    # Analyze relationship chains
    for path in paths[:5]:  # Top 5 paths
        entities = path["entities"]
        print(f"Path: {' → '.join(entity_names)}")
```

### Example 3: Monitor Graph Quality

```python
with GraphStorage() as graph:
    # Regular quality checks
    quality = graph.get_data_quality_metrics()
    
    if quality["quality_score"] < 0.8:
        print("⚠️ Graph quality degraded")
        
        # Auto-repair
        merged = graph.find_and_merge_duplicates(0.9)
        print(f"Fixed by merging {merged} entities")
```

## API Reference Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/graph/entities/search` | POST | Search entities by name |
| `/graph/entities/{id}` | GET | Get entity profile |
| `/graph/entities/list` | POST | List entities with filters |
| `/graph/relationships/search` | POST | Search relationships |
| `/graph/paths` | POST | Find paths between entities |
| `/graph/analytics/centrality` | POST | Get central entities |
| `/graph/analytics/summary` | GET | Graph overview |
| `/graph/analytics/anomalies` | GET | Detect anomalies |
| `/graph/analytics/impact/{id}` | GET | Analyze entity impact |

## Next Steps

1. **Upload documents** with deduction enabled
2. **Query the graph** using GraphRAG endpoints
3. **Analyze results** for insights and patterns
4. **Monitor quality** and perform maintenance
5. **Scale** to larger datasets with performance tuning
