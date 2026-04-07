# GraphRAG Implementation Plan for TransIQ

## Executive Summary
This document outlines a comprehensive step-by-step integration of GraphRAG into the existing TransIQ backend, leveraging the current deduction engine while adding advanced graph-based reasoning capabilities.

---

## Part 1: Current State Analysis

### Existing Strengths
1. **Deduction Engine** (`app/processors/deduction.py`)
   - Already extracts facts (subject-predicate-object triples)
   - Built-in knowledge graph construction with nodes and edges
   - Entity and relationship inference
   - Degree centrality calculation

2. **Storage Layer**
   - SQLite for document/chunk metadata
   - ORM models ready (User, Document, Chunk, GraphEdge)
   - FAISS/Qdrant for vector storage
   - Task status tracking

3. **Processing Pipeline**
   - Celery workers for background processing
   - Redis for task queue and caching
   - Multi-stage document processing
   - WebSocket progress tracking

### Current Limitations for GraphRAG
1. **Graph Storage**: Facts stored as JSON text in `graph_edges` table (not queryable)
2. **No Entity Linking**: Entities not deduplicated across documents
3. **No Multi-hop Reasoning**: Can't traverse relationships across documents
4. **No Entity Resolution**: No disambiguation or normalization
5. **Limited Graph Querying**: Only document-level edge storage, no cross-document queries
6. **No Graph Analytics**: Missing centrality metrics, community detection, path finding

---

## Part 2: GraphRAG Architecture Design

### Core Components to Add

```
┌─────────────────────────────────────────────────────────────┐
│                      GraphRAG Layer                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Entity Resolution & Deduplication Service             │  │
│  │ - Normalize entity names                              │  │
│  │ - Match entities across documents                     │  │
│  │ - Create entity canonical forms                       │  │
│  │ - Track aliases                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                              ▲                                │
│                              │                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Knowledge Graph Engine                                │  │
│  │ - Build/maintain graph structure                      │  │
│  │ - Entity-relationship storage (Neo4j style)           │  │
│  │ - Graph traversal and querying                        │  │
│  │ - Temporal information tracking                       │  │
│  │ - Confidence scoring                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                              ▲                                │
│                              │                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Graph Analytics & Reasoning                           │  │
│  │ - Multi-hop relationship queries                      │  │
│  │ - Path finding (shortest path, all paths)            │  │
│  │ - Community detection                                 │  │
│  │ - Centrality metrics (PageRank, Betweenness)         │  │
│  │ - Anomaly detection in relationships                  │  │
│  │ - Impact analysis                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                              ▲                                │
│                              │                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Deduction Engine Enhancement                          │  │
│  │ - Fact extraction → Entity linking                    │  │
│  │ - Build graph incrementally                           │  │
│  │ - Confidence propagation                              │  │
│  │ - Conflict resolution                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                              ▲                                │
└──────────────────────────────────────────────────────────────┘
```

### File Structure to Create

```
app/
├── processors/
│   ├── deduction.py (ENHANCE - add entity linking)
│   └── graph_rag/
│       ├── __init__.py
│       ├── entity_resolver.py      # Entity deduplication/normalization
│       ├── graph_engine.py          # Core graph storage & ops
│       ├── graph_analytics.py       # Path finding, centrality, etc.
│       ├── graph_querying.py        # Query language & traversal
│       └── facts_to_graph.py        # Convert facts → graph entities
│
├── storage/
│   └── graph_storage.py             # Graph persistence layer
│
├── api/v2/
│   └── graph_endpoints.py           # New graph query endpoints
│
└── workers/
    └── graph_processing.py          # Graph building worker tasks
```

---

## Part 3: Database Schema Changes

### New Tables to Add

#### 1. **graph_entities** - Canonical Entity Storage
```sql
CREATE TABLE graph_entities (
    id TEXT PRIMARY KEY,                          -- Generated UUID
    canonical_name TEXT NOT NULL UNIQUE,          -- Normalized name
    entity_type TEXT NOT NULL,                    -- PERSON, ORG, LOCATION, etc.
    aliases TEXT,                                 -- JSON list of alternative names
    first_doc_id TEXT,                            -- First document mentioning this
    mention_count INTEGER DEFAULT 1,              -- Number of mentions across docs
    total_confidence REAL DEFAULT 0.0,            -- Sum of confidence scores
    properties TEXT,                              -- JSON: {attr: value, ...}
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (first_doc_id) REFERENCES documents(id)
);

CREATE INDEX idx_entities_canonical ON graph_entities(canonical_name);
CREATE INDEX idx_entities_type ON graph_entities(entity_type);
```

#### 2. **graph_relationships** - Cross-Document Relationships
```sql
CREATE TABLE graph_relationships (
    id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL,               -- references graph_entities.id
    target_entity_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,              -- OWNS, WORKS_FOR, LOCATED_IN, etc.
    properties TEXT,                              -- JSON context/attributes
    confidence REAL DEFAULT 0.5,                  -- Based on source facts
    mention_count INTEGER DEFAULT 1,              -- How many doc pairs mention this
    total_documents INTEGER DEFAULT 1,            -- How many docs contain this rel
    is_bidirectional INTEGER DEFAULT 0,           -- Can traverse both ways
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (source_entity_id) REFERENCES graph_entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_entity_id) REFERENCES graph_entities(id) ON DELETE CASCADE
);

CREATE INDEX idx_rel_source ON graph_relationships(source_entity_id);
CREATE INDEX idx_rel_target ON graph_relationships(target_entity_id);
CREATE INDEX idx_rel_type ON graph_relationships(relationship_type);
```

#### 3. **graph_entity_mentions** - Track Where Entities Appear
```sql
CREATE TABLE graph_entity_mentions (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,                      -- references graph_entities.id
    doc_id TEXT NOT NULL,                         -- references documents.id
    chunk_id TEXT NOT NULL,                       -- references chunks.id
    mention_text TEXT,                            -- Exact text from document
    position INTEGER,                             -- Character position in chunk
    confidence REAL,                              -- Extraction confidence
    created_at TEXT,
    FOREIGN KEY (entity_id) REFERENCES graph_entities(id) ON DELETE CASCADE,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);

CREATE INDEX idx_mentions_entity ON graph_entity_mentions(entity_id);
CREATE INDEX idx_mentions_doc ON graph_entity_mentions(doc_id);
```

#### 4. **graph_paths** - Cached Path Queries
```sql
CREATE TABLE graph_paths (
    id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    path_data TEXT,                               -- JSON: [entity_ids, edges, ...]
    path_length INTEGER,                          -- Number of hops
    relevance_score REAL,                         -- Quality metric
    created_at TEXT,
    FOREIGN KEY (source_entity_id) REFERENCES graph_entities(id),
    FOREIGN KEY (target_entity_id) REFERENCES graph_entities(id)
);

CREATE INDEX idx_paths_source_target ON graph_paths(source_entity_id, target_entity_id);
```

#### 5. **Modify Existing: graph_edges** (for backward compatibility)
```sql
-- Add columns to existing graph_edges table
ALTER TABLE graph_edges ADD COLUMN entity_source_id TEXT;
ALTER TABLE graph_edges ADD COLUMN entity_target_id TEXT;
ALTER TABLE graph_edges ADD COLUMN edge_type TEXT;
ALTER TABLE graph_edges ADD COLUMN confidence REAL;

-- Add foreign keys
-- ALTER TABLE graph_edges ADD FOREIGN KEY (entity_source_id) REFERENCES graph_entities(id);
-- ALTER TABLE graph_edges ADD FOREIGN KEY (entity_target_id) REFERENCES graph_entities(id);
```

---

## Part 4: Component Details

### 1. Entity Resolver (`entity_resolver.py`)
**Purpose**: Deduplicate and normalize entities across documents

**Key Features**:
- Fuzzy matching for entity names (string similarity)
- Type-aware matching (same type = higher probability)
- Alias tracking
- Canonical name selection
- Multi-tenant isolation

**Methods**:
```python
class EntityResolver:
    def resolve_entity(entity_text, entity_type, confidence) -> str
    def find_similar_entities(entity_text, threshold=0.8) -> List[Entity]
    def merge_entities(entity_ids) -> str  # Returns canonical ID
    def add_alias(canonical_id, alias_text) -> None
    def get_entity_by_name(name) -> Entity
```

### 2. Knowledge Graph Engine (`graph_engine.py`)
**Purpose**: Core graph structure, entity/relationship storage, and transactional consistency

**Key Features**:
- Entity CRUD operations
- Relationship CRUD with type validation
- Transaction management
- Confidence score propagation
- Bidirectional relationship tracking

**Methods**:
```python
class KnowledgeGraphEngine:
    def create_entity(name, entity_type, properties) -> EntityID
    def create_relationship(source_id, target_id, rel_type, confidence) -> RelID
    def update_entity_confidence(entity_id, new_score) -> None
    def get_entity(entity_id) -> Entity
    def get_relationships(entity_id, direction='both') -> List[Relationship]
    def delete_entity(entity_id) -> None
```

### 3. Graph Analytics (`graph_analytics.py`)
**Purpose**: Advanced graph algorithms for reasoning

**Key Features**:
- Path finding (BFS, Dijkstra)
- Centrality metrics (degree, betweenness, PageRank)
- Community detection (Louvain algorithm)
- Anomaly detection
- Impact analysis

**Methods**:
```python
class GraphAnalytics:
    def find_paths(source_id, target_id, max_depth=5) -> List[Path]
    def shortest_path(source_id, target_id) -> Path
    def calculate_centrality(entity_id) -> CentralityScore
    def find_communities() -> List[Community]
    def detect_anomalies() -> List[AnomalyAlert]
```

### 4. Graph Querying (`graph_querying.py`)
**Purpose**: Query interface for graph traversal and reasoning

**Key Features**:
- Simple node/relationship lookups
- Traversal queries (find all entities of type X connected to Y)
- Filtering by relationship type, confidence
- Limit and pagination

**Query Examples**:
```python
# Find all companies owned by a person
query = GraphQuery()
    .start_from_entity(person_id)
    .traverse("OWNS")
    .filter_type("ORGANIZATION")
    .limit(10)

# Find entities with degree centrality > threshold
query = GraphQuery()
    .filter_centrality_min(0.7)
    .filter_type("PERSON")
```

### 5. Facts-to-Graph Converter (`facts_to_graph.py`)
**Purpose**: Convert deduction engine facts into deduplicated graph entities

**Key Features**:
- Fact validation
- Entity extraction and linking
- Relationship creation
- Confidence propagation

**Flow**:
1. Receive facts: `[{"subject": "Apple", "predicate": "owns", "object": "Beats", ...}]`
2. Resolve "Apple" → entity_id (or create if new)
3. Resolve "Beats" → entity_id (or create if new)
4. Create relationship: (Apple) --[owns]-→ (Beats)
5. Update confidence scores

---

## Part 5: Integration Points

### 5.1 Deduction Engine Enhancement
**Current**: Generates facts, stores as JSON in graph_edges
**New**: Feed facts directly into graph engine

```python
# In app/processors/deduction.py - add after fact extraction
def integrate_with_graph(self, doc_id: str, facts: List[Dict]):
    """
    Publish extracted facts to GraphRAG layer
    """
    from app.processors.graph_rag.facts_to_graph import FactsToGraphConverter
    from app.storage.graph_storage import GraphStorage
    
    graph_storage = GraphStorage()
    converter = FactsToGraphConverter()
    
    for fact in facts:
        entities, relationships = converter.convert_fact(fact, doc_id)
        
        for entity in entities:
            graph_storage.add_entity(entity)
        
        for rel in relationships:
            graph_storage.add_relationship(rel)
```

### 5.2 Celery Worker for Graph Building
**New task**: `build_knowledge_graph` (runs after text chunking)

```python
@celery.task
def build_knowledge_graph(doc_id: str, facts: List[Dict]):
    """
    Post-processing task to integrate facts into knowledge graph
    Runs after deduction engine completes
    """
    from app.processors.graph_rag import FactsToGraphConverter
    from app.storage.graph_storage import GraphStorage
    
    try:
        converter = FactsToGraphConverter()
        entities, relationships = converter.convert_facts(facts, doc_id)
        
        graph_storage = GraphStorage()
        graph_storage.bulk_add_entities(entities)
        graph_storage.bulk_add_relationships(relationships)
        
        # Perform entity resolution in background
        perform_entity_resolution.delay(doc_id)
        
    except Exception as e:
        logger.error(f"Graph building failed for {doc_id}: {e}")
        raise
```

### 5.3 API Endpoints for Graph Queries
**New endpoints** in `app/api/v2/graph_endpoints.py`:

```
POST /api/v2/graph/entities           # List all entities
  Query: {entity_type, confidence_min, limit}

GET /api/v2/graph/entities/{id}       # Get entity details

POST /api/v2/graph/relationships      # List relationships
  Query: {source_type, target_type, rel_type}

POST /api/v2/graph/paths              # Find paths between entities
  Body: {source_id, target_id, max_depth}

POST /api/v2/graph/communities        # Find entity communities
  Query: {min_size, algorithm}

POST /api/v2/graph/central-entities   # Get most important entities
  Query: {metric, limit, doc_filter}

POST /api/v2/graph/impact-analysis    # Analyze relationship impact
  Body: {source_id, relationship_type}
```

---

## Part 6: Implementation Roadmap

### Phase 1: Foundation (Steps 1-3)
- Create new database tables
- Implement entity resolver
- Implement graph engine

### Phase 2: Core Integration (Steps 4-6)
- Implement graph analytics
- Connect deduction engine to graph
- Create graph storage layer

### Phase 3: Advanced Features (Steps 7-9)
- Build graph querying interface
- Create API endpoints
- Implement Celery workers

### Phase 4: Polish (Step 10)
- Update documentation
- Create examples
- Performance tuning

---

## Part 7: Data Migration Strategy

### For Existing Documents
1. Query all existing `graph_edges` entries
2. Parse JSON structure
3. Run through entity resolver
4. Populate new `graph_entities` and `graph_relationships` tables
5. Update `graph_edges` with new entity IDs (backward compatibility)

### Migration Script Location
`app/scripts/migrate_to_graphrag.py`

---

## Part 8: Performance Considerations

### Indexing Strategy
- Index `graph_entities.canonical_name` (entity lookup)
- Index `graph_relationships.source_entity_id`, `target_entity_id`
- Index `graph_relationships.relationship_type` (type filtering)
- Index `graph_paths` on source/target pairs (caching)

### Caching
- Use Redis for frequent path queries
- Cache centrality metrics
- TTL-based cache invalidation on graph updates

### Batch Operations
- Batch insert entities/relationships
- Async entity resolution (background task)
- Periodic graph analytics computation

---

## Part 9: Testing Strategy

### Unit Tests
- Entity resolver (matching algorithms)
- Graph engine (CRUD operations)
- Facts converter (fact validation)

### Integration Tests
- End-to-end document → facts → graph
- Cross-document entity linking
- Path finding correctness

### Performance Tests
- Bulk entity/relationship insertion
- Path finding with large graphs
- Centrality calculation on big graphs

### Data Quality Tests
- Entity deduplication accuracy
- Relationship validation
- Confidence score propagation

---

## Part 10: Security & Multi-tenancy

### Data Isolation
- All graph queries filtered by `user_id`
- Graph tables include user context (via document)
- No cross-tenant entity linking

### Example Query Constraint
```python
def get_user_entities(user_id: str):
    """Return only entities from user's documents"""
    return db.query(GraphEntity).join(
        GraphEntityMention
    ).join(
        Document
    ).filter(Document.user_id == user_id)
```

---

## Implementation Begins Here →

Ready to start building! The next sections show step-by-step code implementation.
