# TransIQ GraphRAG & Qdrant Implementation Analysis

**Date**: March 2026  
**Status**: Complete exploration of existing GraphRAG and Qdrant implementation  
**Scope**: Full data flow, storage formats, graph algorithms, entity/KPI framework

---

## EXECUTIVE SUMMARY

TransIQ has **comprehensive GraphRAG implementation** with:

- ✅ **Qdrant vector storage**: 384D embeddings (all-MiniLM-L6-v2), cosine similarity, local persistence
- ✅ **Knowledge graph**: Canonical entities, typed relationships, mention tracking, multi-tenant isolation
- ✅ **Graph algorithms**: BFS path finding, entity resolution (85% fuzzy matching), cascading impact analysis
- ✅ **Intelligence layer**: 4-stage LLM pipeline (KPI extraction → DMAIC reasoning → recommendations)
- ✅ **Domain analytics**: Drilling KPIs, financial impact scoring, ESG classification
- ✅ **Hybrid retrieval**: BM25 + vector fusion (RRF), semantic chunking, prompt compression
- ✅ **Evidence tracking**: Mention database for cross-document correlation

**Next phase (Phase 4)**: Expand graph algorithms, add community detection, enhance impact visualization.

---

## 1. QDRANT CONFIGURATION & CONNECTION SETUP

### Connection Topology
**File**: [vector_storage.py](vector_storage.py#L20-L50)

```python
# Configuration
QDRANT_URL      = os.getenv("QDRANT_URL")              # Docker: http://qdrant:6333
QDRANT_PATH     = os.getenv("QDRANT_PATH", "./qdrant_storage")
USE_LOCAL_QDRANT = os.getenv("USE_LOCAL_QDRANT", "true").lower() == "true"
COLLECTION_NAME = "transiq_chunks"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM   = 384
```

**Connection Priority** (Lines 80-103):
1. **Docker Qdrant** (if `QDRANT_URL` set and `USE_LOCAL_QDRANT=false`)
   - Uses `QdrantClient(url=QDRANT_URL, timeout=5.0)`
   - Health check via `get_collections()`
   - Sets `_is_docker_mode = True`

2. **Local File Storage** (fallback)
   - Path: `./qdrant_storage/`
   - Uses `QdrantClient(path=QDRANT_PATH)`
   - SQLite + MMAP persistence
   - Sets `_is_docker_mode = False`

### Collection Initialization
**Lines 104-110**:
- Auto-creates collection if missing
- **Collection name**: `transiq_chunks`
- **Vector config**: VectorParams(size=384, distance=Distance.COSINE)
- **Payload index**: KEYWORD index on `doc_id` field for fast filtering

### Data Directory Structure
```
qdrant_storage/
├── .lock                              # SQLite write lock
├── meta.json                          # Collection metadata (schema, stats)
└── collection/
    └── transiq_chunks/
        ├── segments/                  # MMAP-backed vector segments
        └── [segment data files]       # Binary vector data
```

**File Persistence**: Qdrant stores everything as memory-mapped binary for:
- ⚡ Fast indexing (~384-dim cosine search in <10ms for 100k vectors)
- 💾 SQLite fallback for metadata ACID guarantees
- 🔄 Automatic recovery on crash

---

## 2. ENTITY STORAGE FORMAT

### Core Data Models
**File**: [app/db/models.py](app/db/models.py#L215-L350)

#### GraphEntity Table
```sql
CREATE TABLE graph_entities (
  id                TEXT PRIMARY KEY,                    -- UUID
  canonical_name    TEXT NOT NULL UNIQUE,                -- Normalized name
  entity_type       TEXT NOT NULL,                       -- PERSON, ORG, LOCATION, KPI, etc.
  aliases           JSON,                                -- List of alternate names
  first_doc_id      TEXT,                                -- FK to documents
  mention_count     INTEGER DEFAULT 1,                   -- Cross-document frequency
  total_confidence  REAL DEFAULT 0.0,                    -- Sum of confidence scores
  properties        JSON DEFAULT '{}',                   -- Custom attributes
  created_at        DATETIME(timezone),
  updated_at        DATETIME(timezone)
);

CREATE INDEX idx_entity_canonical ON graph_entities(canonical_name);
CREATE INDEX idx_entity_type ON graph_entities(entity_type);
CREATE INDEX idx_entity_mention_count ON graph_entities(mention_count);
```

**Entity Types** (from deduction_enrichment.py):
- DEPARTMENT, ROLE, KPI, PROCESS, SYSTEM, LOCATION, TEAM, EQUIPMENT

**Example Entity**:
```json
{
  "id": "ent_abc123",
  "canonical_name": "paragon mss1",
  "entity_type": "EQUIPMENT",
  "aliases": ["PARAGON MSS1", "Paragon Rig", "MSS-1"],
  "mention_count": 47,
  "total_confidence": 42.5,
  "properties": {
    "rig_class": "semi-submersible",
    "location": "Gulf of Mexico",
    "operator": "BP Operations"
  }
}
```

#### GraphRelationship Table
```sql
CREATE TABLE graph_relationships (
  id                    TEXT PRIMARY KEY,                -- UUID
  source_entity_id      TEXT NOT NULL,                   -- FK
  target_entity_id      TEXT NOT NULL,                   -- FK
  relationship_type     TEXT NOT NULL,                   -- OWNS, WORKS_FOR, AFFECTS, etc.
  confidence            REAL DEFAULT 0.5,                -- Extraction confidence (0-1)
  mention_count         INTEGER DEFAULT 1,               -- How many docs mention this
  total_documents       INTEGER DEFAULT 1,               -- Across how many documents
  is_bidirectional      INTEGER DEFAULT 0,               -- Can traverse both ways
  properties            JSON DEFAULT '{}',               -- Context/evidence
  created_at            DATETIME(timezone),
  updated_at            DATETIME(timezone),
  FOREIGN KEY (source_entity_id) REFERENCES graph_entities(id) ON DELETE CASCADE,
  FOREIGN KEY (target_entity_id) REFERENCES graph_entities(id) ON DELETE CASCADE
);

CREATE INDEX idx_rel_source ON graph_relationships(source_entity_id);
CREATE INDEX idx_rel_target ON graph_relationships(target_entity_id);
CREATE INDEX idx_rel_type ON graph_relationships(relationship_type);
CREATE INDEX idx_rel_source_target ON graph_relationships(source_entity_id, target_entity_id);
```

**Relationship Types**:
- Ownership: OWNS, OWNED_BY
- Employment: WORKS_FOR, EMPLOYS, MANAGES, MANAGED_BY
- Location: LOCATED_IN, BASED_IN, HAS_HEADQUARTERS
- Structure: SUBSIDIARY_OF, PARENT_OF, MEMBER_OF
- Business: PARTNERS_WITH, COMPETES_WITH, ACQUIRES, INVESTS_IN
- Production: PRODUCES, SUPPLIES, DISTRIBUTES, MANUFACTURES
- Domain: DEPENDS_ON, AFFECTS, RELATED_TO

**Example Relationship**:
```json
{
  "id": "rel_xyz789",
  "source_entity_id": "ent_abc123",              // PARAGON MSS1 rig
  "target_entity_id": "ent_def456",              // Gulf of Mexico
  "relationship_type": "LOCATED_IN",
  "confidence": 0.95,
  "mention_count": 12,
  "total_documents": 3,
  "properties": {
    "evidence": [
      "PARAGON MSS1 operates in the Gulf of Mexico",
      "The rig is stationed offshore in GoM Block 101"
    ],
    "coordinates": [-89.5, 27.2]
  }
}
```

#### Mention Tables (Evidence Tracking)
- **GraphEntityMention**: Links entity to chunks
- **GraphRelationshipMention**: Evidence for relationships
- Supports multi-hop confidence calculation via aggregated mentions

---

## 3. VECTOR EMBEDDING APPROACH

### Embedding Generation Pipeline
**File**: [vector_storage.py](vector_storage.py#L120-L180)

#### Model Configuration
```python
# SentenceTransformer model
Model:        "all-MiniLM-L6-v2" (80MB)
Dimensions:   384
Speed:        ~1000 sentences/second (CPU), 10k/sec (GPU)
Download:     HuggingFace (cached to ~/.cache/torch/sentence_transformers/)
```

#### Embedding Methods

**Single embedding** (Lines 116-120):
```python
def generate_embedding(self, text: str) -> List[float]:
    return self.model.encode(text, convert_to_tensor=False).tolist()
```

**Batch embeddings** (Lines 122-135):
```python
def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
    embeddings = self.model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_tensor=False
    )
    return [e.tolist() for e in embeddings]
```

**For queries**:
```python
def generate_query_embedding(self, query: str) -> List[float]:
    return self.generate_embedding(query)
```

### Qdrant Vector Storage
**File**: [vector_storage.py](vector_storage.py#L155-L195)

Each document chunk is stored as a `PointStruct`:

```python
PointStruct(
    id=str(uuid.uuid4()),                        # Unique point ID
    vector=embedding,                            # 384D float array
    payload={
        "doc_id":           "doc_uuid",          # Document reference
        "chunk_text":       "full chunk content", # For ranking/display
        "chunk_index":      0,                   # Chunk sequence
        "rig_name":         "PARAGON MSS1",      # Custom metadata
        "report_date":      "2024-01-15",
        "source_section":   "Operations Report",
        "raw_evidence":     "exact quote",
        **additional_metadata
    }
)
```

**Upsert Process** (Lines 161-190):
1. Generate embeddings in batches
2. Create PointStructs with payload
3. Upsert in batches of 64 points
4. Log upsert count

```python
batch_size = 64
for i in range(0, len(points), batch_size):
    self._client.upsert(
        collection_name=COLLECTION_NAME,
        points=points[i : i + batch_size]
    )
```

### Search & Filtering
**File**: [vector_storage.py](vector_storage.py#L200-L225)

```python
def search(self, query_embedding, doc_id: Optional[str] = None, top_k: int = 8):
    # Build filter for single document if specified
    search_filter = None
    if doc_id:
        search_filter = Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        )
    
    # Search with cosine similarity
    results = self._client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        query_filter=search_filter,           # Fuzzy payload filtering
        limit=top_k,
        with_payload=True                     # Return full metadata
    )
    
    return [(r.payload["chunk_text"], r.score) for r in results]
```

**Performance**: ~5-50ms for 100k vectors with doc_id filter (depends on index state)

---

## 4. EXISTING VECTOR STORAGE & GRAPH DATABASE FILES

### Directory Inventory

#### Qdrant Local Storage
**Location**: `TransIQ-backend-master/qdrant_storage/`

| File/Directory | Purpose | Size |
|---|---|---|
| `.lock` | SQLite write lock (prevents concurrent access) | <1KB |
| `meta.json` | Collection schema, stats, version info | ~1-5KB |
| `collection/transiq_chunks/` | Vector data segments | ~100MB+ |
| `collection/transiq_chunks/segments/` | MMAP-backed Binary files | Dynamic |

**Current State**: Fresh collections start empty, grow as chunks are upserted

#### SQLite Database
**Location**: `storage/local_storage.db`

**Tables**:
- `documents` - File metadata, user ownership
- `chunks` - Text with metadata
- `graph_entities` - Canonical entities (deduplicated)
- `graph_relationships` - Entity relationships
- `graph_entity_mentions` - Where entities appear
- `graph_relationship_mentions` - Evidence for relationships
- `users`, `batches`, `tasks` - Multi-tenant scaffolding

**Current Size**: Grows with document processing (~100KB baseline)

### Data Flow Diagram

```
PDF/CSV Upload
    ↓
chunker.py (semantic splitting)
    ↓
vector_storage.py (embedding + upsert)
    ↓
Qdrant (384D vectors + payloads)
    ↓
SQLite: chunks table (metadata)
    ↓
deduction.py (fact extraction)
    ↓
facts_to_graph.py (conversion)
    ↓
entity_resolver.py (deduplication @ 85%)
    ↓
SQLite: graph_entities + graph_relationships
    ↓
graph_analytics.py (path finding, centrality)
    ↓
impact_engine.py (cascading impact analysis)
    ↓
Pipeline KPI framework (financial scoring)
```

---

## 5. RELATIONSHIP QUERIES & GRAPH ALGORITHMS

### GraphAnalytics API
**File**: [app/processors/graph_rag/graph_analytics.py](app/processors/graph_rag/graph_analytics.py)

#### Path Finding (BFS)
```python
def find_paths(source_id: str, target_id: str, max_depth: int = 5, 
               rel_types: Optional[List[str]] = None) -> List[Dict]:
    """Find all paths between entities"""
    # Uses queue-based BFS with visited set
    # Returns paths sorted by relevance (shorter = higher)
    # Time complexity: O(V + E) where V = entities, E = relationships
```

**Algorithm** (Lines 61-110):
1. Initialize queue with source entity
2. Pop current, explore neighbors via relationships
3. Track visited to avoid cycles
4. Check depth limit
5. Found target → record path with relevance score
6. Sort paths by 1/(path_length) relevance

**Returns**:
```python
[
    {
        "entities": ["ent_1", "ent_2", "ent_3"],
        "relationships": [
            {"id": "rel_1", "type": "AFFECTS", "confidence": 0.9},
            {"id": "rel_2", "type": "DEPENDS_ON", "confidence": 0.85}
        ],
        "length": 2,
        "relevance": 0.5
    }
    # ... up to 20 paths
]
```

#### Shortest Path
```python
def shortest_path(source_id: str, target_id: str) -> Optional[Dict]:
    paths = self.find_paths(source_id, target_id, max_depth=10)
    return min(paths, key=lambda p: p["length"]) if paths else None
```

#### Common Neighbors
```python
def find_common_neighbors(entity_id1, entity_id2) -> List[str]:
    # Find entities that connect to both inputs
    # Uses set intersection of neighbors
```

### Impact Engine (Cascading Analysis)
**File**: [app/intelligence/impact_engine.py](app/intelligence/impact_engine.py)

#### Core Method
```python
def analyze_kpi_impact(kpi_entity: Entity, entities: List[Entity],
                      relationships: List[Relationship], 
                      financial_impact: float = 0.0) -> KPIImpactAnalysis:
    """Analyze complete impact of a KPI change"""
    
    # Step 1: Direct impact (1 hop)
    directly_affected = self._find_directly_affected(kpi_entity, entities, relationships)
    
    # Step 2: Cascading paths (multi-hop, max 4 hops)
    cascading_paths = self._find_cascading_paths(kpi_entity, entities, relationships, max_depth=4)
    
    # Step 3: Calculate total cascading $ impact
    total_cascading = self._estimate_cascading_impact(cascading_paths)
    
    # Step 4: Identify who can mitigate
    responsible = self._find_responsible_entities(kpi_entity, relationships)
    
    # Step 5: Trace root causes
    root_causes = self._find_root_causes(kpi_entity, entities, relationships)
    
    # Step 6: Generate actionable recommendations
    recommendations = self._generate_recommendations(...)
    
    return KPIImpactAnalysis(
        kpi_entity=kpi_entity,
        financial_impact_usd=financial_impact,
        directly_affected_kpis=directly_affected,
        cascading_impact_paths=cascading_paths,
        total_cascading_impact_usd=total_cascading,
        responsible_entities=responsible,
        root_cause_chain=root_causes,
        recommendations=recommendations
    )
```

#### Data Structures

**Entity**:
```python
@dataclass
class Entity:
    id: str
    name: str
    entity_type: str                           # DEPARTMENT, ROLE, KPI, PROCESS, SYSTEM, LOCATION
    confidence: float
    properties: Dict = field(default_factory=dict)
```

**Relationship**:
```python
@dataclass
class Relationship:
    source_id: str
    target_id: str
    relationship_type: str                     # RESPONSIBLE_FOR, DEPENDS_ON, AFFECTS, etc.
    confidence: float
    impact_type: ImpactType                    # DIRECT, IMPLIED, CASCADING, MITIGATING
    strength: float = 1.0                      # Multiplier for impact magnitude
```

**ImpactType Enum**:
- DIRECT = "direct" (A directly causes B)
- IMPLIED = "implied" (A suggests B may be affected)
- HISTORICAL = "historical" (A and B are correlated historically)
- CASCADING = "cascading" (A→B→C chain)
- MITIGATING = "mitigating" (A can reduce impact of B)

**ImpactPath**:
```python
@dataclass
class ImpactPath:
    root_cause: Entity
    affected_entities: List[Entity]
    relationships: List[Relationship]
    total_impact_usd: float
    affected_kpis_count: int
    depth: int                                 # Hops from root
    confidence: float
```

### Entity Resolution (Deduplication)
**File**: [app/processors/graph_rag/entity_resolver.py](app/processors/graph_rag/entity_resolver.py)

#### Core Matching Algorithm
```python
def find_similar_entities(self, name: str, entity_type: Optional[str] = None,
                         threshold: float = 0.85) -> List[Tuple[str, str, float]]:
    """Find existing entities similar to a new one"""
    
    normalized_name = self.normalize_entity_name(name)
    results = []
    
    # Fetch all entities (optionally filtered by type)
    entities = self.db.query(GraphEntity)
    if entity_type:
        entities = entities.filter(GraphEntity.entity_type == entity_type)
    
    # Calculate similarity for each
    for entity in entities.all():
        similarity = self.calculate_similarity(name, entity.canonical_name)
        if similarity >= threshold:
            results.append((entity.id, entity.canonical_name, similarity))
    
    # Sort by similarity (desc)
    results.sort(key=lambda x: x[2], reverse=True)
    return results
```

**Normalization** (Lines 59-76):
- Lowercase + strip whitespace
- Remove articles (the, a, an)
- Remove suffixes (inc, ltd, llc, corp, etc.)
- Collapse multiple spaces

**Similarity** (Lines 134-155):
```python
ratio = SequenceMatcher(None, norm1, norm2).ratio()  # Base token overlap
if norm1 in norm2 or norm2 in norm1:
    ratio = min(1.0, ratio * 1.2)                    # Boost substring matches
return ratio
```

**Threshold**: Default 0.85 (85% match required for auto-merge)

#### Resolution Flow
```python
def resolve_entity(self, name: str, entity_type: str, doc_id: str, confidence: int):
    # 1. Find similar entities in DB
    similar = self.find_similar_entities(name, entity_type, threshold=0.85)
    
    if similar:
        # 2. Use highest-confidence existing entity
        best_entity_id = similar[0][0]
        
        # 3. Update mention count and confidence
        entity = self.db.query(GraphEntity).filter(GraphEntity.id == best_entity_id).first()
        entity.mention_count += 1
        entity.total_confidence += confidence
        
        # 4. Track mention (evidence)
        self.add_entity_mention(best_entity_id, doc_id, name, confidence)
        
        return best_entity_id
    else:
        # 5. Create new entity
        entity = GraphEntity(...)
        self.db.add(entity)
        self.db.commit()
        return entity.id
```

---

## 6. DOCUMENT CHUNKING & EMBEDDING PIPELINE

### Semantic Chunking
**File**: [chunker.py](chunker.py)

#### Main Entry Point
```python
def chunk_text(text, chunk_size=1000) -> List[str]:
    """Split text using semantic boundaries"""
    
    # 1. Try semantic splitting (respects structure)
    chunks = split_by_semantic_units(text, chunk_size)
    
    # 2. Fall back to recursive split if needed
    if not chunks or any(len(c) > chunk_size * 1.5 for c in chunks):
        chunks = split_by_recursive_algorithm(text, chunk_size)
    
    # 3. Merge chunks shorter than 100 chars
    min_chunk_size = max(100, chunk_size // 10)
    chunks = merge_short_chunks(chunks, min_chunk_size, chunk_size)
    
    # 4. Clean chunks (remove excessive whitespace)
    return [clean_chunk(c) for c in chunks]
```

#### Boundary Detection (Lines 30-70)
**Priority order** (lower number = stronger break):
1. **Headings** (Priority 1): `^#{1,4}\s`, `^\d+\.+`, `**`, `__`
2. **Paragraph breaks** (Priority 3): `\n\s*\n`
3. **List items** (Priority 4): `^\s*[-•*+]\s+`
4. **Sentence endings** (Priority 5): `[.!?]\s+[A-Z]`

**Algorithm**:
- Identify all breakpoints with priority scores
- Start from position 0
- Find best breakpoint within chunk_size window
- If found, split there; else cut at chunk_size
- Advance by max(overlap, remaining_chars)

#### Configuration
```python
DEFAULT_CHUNK_SIZE = 8000           # Default max chars per chunk
DEFAULT_CHUNK_OVERLAP = 400         # Overlap for context continuity
```

### End-to-End Embedding Pipeline
**File**: [vector_storage.py](vector_storage.py#L239-L268)

```python
def prepare_chunks_for_storage(
    self,
    chunks: List[str],
    document_id: str,
    metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Complete pipeline: chunk → embed → upsert → return structured
    """
    
    # 1. Generate embeddings
    embeddings = self.generate_embeddings_batch(chunks, show_progress=True)
    
    # 2. Upsert to Qdrant
    self.upsert_chunks(chunks, doc_id=document_id, metadata=metadata)
    
    # 3. Return structured chunks for DB storage
    return [
        {
            "document_id": document_id,
            "chunk_text": chunk,
            "chunk_index": idx,
            "embedding": emb,
            "metadata": metadata or {}
        }
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings))
    ]
```

### Backward Compatibility
**Singleton pattern** (`get_vector_service()` at bottom of vector_storage.py):
```python
_vector_service_instance = None

def get_vector_service(model_name=EMBEDDING_MODEL):
    global _vector_service_instance
    if _vector_service_instance is None:
        _vector_service_instance = VectorStorageService(model_name)
    return _vector_service_instance
```

Module-level functions:
```python
def generate_embedding(text):
    return get_vector_service().generate_embedding(text)

def prepare_chunks_with_embeddings(chunks, document_id, metadata=None):
    return get_vector_service().prepare_chunks_for_storage(chunks, document_id, metadata)
```

---

## 7. FACT STORAGE & RETRIEVAL

### Fact Extraction
**File**: [app/processors/deduction.py](app/processors/deduction.py)

#### LLM-based Extraction
```python
def extract_facts(self, text: str, max_facts: int = 50) -> List[Dict]:
    """Extract atomic facts from text"""
    
    prompt = f"""Extract atomic facts from the text as triples.
    
    Return ONLY a valid JSON array with:
    - "subject": entity or concept
    - "predicate": relationship or attribute
    - "object": value or target entity
    - "confidence": 0-1 confidence score
    
    Text: {text[:5000]}
    Max facts: {max_facts}"""
    
    response = self.llm.generate_json(prompt)
    
    # Validate and clean
    validated_facts = []
    for fact in response[:max_facts]:
        if fact.get("subject") and fact.get("predicate"):
            validated_facts.append({
                "subject": str(fact["subject"]),
                "predicate": str(fact["predicate"]),
                "object": str(fact["object"]),
                "confidence": float(fact.get("confidence", 0.5))
            })
    
    return validated_facts
```

#### Knowledge Graph Construction
```python
def build_knowledge_graph(self, facts: List[Dict]) -> Dict:
    """Convert facts to graph structure"""
    
    nodes = {}
    edges = []
    
    for fact in facts:
        subject = fact["subject"].strip()
        predicate = fact["predicate"].strip()
        obj = fact["object"].strip()
        confidence = fact["confidence"]
        
        # Create nodes
        for entity in [subject, obj]:
            if entity not in nodes:
                nodes[entity] = {
                    "id": entity,
                    "label": entity,
                    "type": "entity",
                    "count": 0
                }
            nodes[entity]["count"] += 1
        
        # Create edge
        edges.append({
            "source": subject,
            "target": obj,
            "label": predicate,
            "confidence": confidence
        })
    
    return {"nodes": nodes, "edges": edges}
```

### Facts-to-Graph Conversion
**File**: [app/processors/graph_rag/facts_to_graph.py](app/processors/graph_rag/facts_to_graph.py)

#### Fact Validation
```python
def validate_fact(self, fact: Dict) -> bool:
    required = {"subject", "predicate", "object"}
    if not all(f in fact for f in required):
        return False
    if not (fact.get("subject") and fact.get("predicate") and fact.get("object")):
        return False
    return True
```

#### Entity Type Inference
```python
def infer_entity_type(self, entity_text: str) -> str:
    """Heuristic entity classification"""
    
    org_keywords = {'company', 'corp', 'inc', 'ltd', 'bank', 'hospital', ...}
    person_keywords = {'mr', 'ms', 'dr', 'prof', ...}
    location_keywords = {'city', 'country', 'field', 'basin', ...}
    
    if any(kw in entity_text.lower() for kw in org_keywords):
        return "ORGANIZATION"
    if any(kw in entity_text.lower() for kw in person_keywords):
        return "PERSON"
    if any(kw in entity_text.lower() for kw in location_keywords):
        return "LOCATION"
    
    return "CONCEPT"  # Default
```

#### Predicate Mapping
```python
# 50+ predicate types normalize to ~25 relationship types
PREDICATE_MAPPING = {
    "owns": "OWNS",
    "works for": "WORKS_FOR",
    "located in": "LOCATED_IN",
    "depends on": "DEPENDS_ON",
    "affects": "AFFECTS",
    # ... 50+ more mappings
}
```

### Graph Storage Orchestration
**File**: [app/storage/graph_storage.py](app/storage/graph_storage.py)

#### Integration Pipeline
```python
def integrate_facts(self, facts: List[Dict], doc_id: str, user_id: str = None) -> Dict:
    """End-to-end fact → graph storage"""
    
    # 1. Convert facts to entities and relationships
    entity_dicts, rel_dicts = self.facts_converter.convert_facts(facts, doc_id)
    
    # 2. Resolve entities (deduplication via entity_resolver)
    entity_map = {}
    for entity_dict in entity_dicts:
        entity_id = self.graph_engine.create_entity(
            name=entity_dict["name"],
            entity_type=entity_dict["type"],
            doc_id=doc_id,
            properties=entity_dict.get("properties", {}),
            confidence=entity_dict.get("confidence", 50)
        )
        entity_map[entity_dict["name"]] = entity_id
    
    # 3. Create relationships
    rels_created = 0
    for rel_dict in rel_dicts:
        source_id = entity_map.get(rel_dict["source_name"])
        target_id = entity_map.get(rel_dict["target_name"])
        
        if source_id and target_id:
            rel_id = self.graph_engine.create_relationship(
                source_id=source_id,
                target_id=target_id,
                relationship_type=rel_dict["type"],
                confidence=rel_dict.get("confidence", 50),
                properties=rel_dict.get("properties", {}),
                doc_id=doc_id
            )
            
            # Track evidence
            self.graph_engine.add_relationship_mention(rel_id, doc_id, rel_dict["confidence"])
            rels_created += 1
    
    return {
        "facts_processed": len(facts),
        "entities_created": len(entity_dicts),
        "relationships_created": rels_created,
        "entity_map": entity_map
    }
```

### Hybrid Retrieval
**File**: [app/retrieval/hybrid_retrieval.py](app/retrieval/hybrid_retrieval.py)

#### Document Classification
```python
def classify_document(text: str, file_type: str = "") -> str:
    """Determine retrieval strategy (0 LLM calls)"""
    
    char_count = len(text)
    has_headings = bool(re.search(r"^#{1,4}\s|\n[A-Z][A-Z\s]{5,}\n", text, re.M))
    has_tables = bool(re.search(r"\|.+\|.+\|", text))
    
    if (char_count <= 8_000 and not has_headings) or file_type in ("csv", "xlsx"):
        return DocumentComplexity.SIMPLE
    
    if char_count >= 30_000 and (has_headings or has_tables):
        return DocumentComplexity.COMPLEX
    
    return DocumentComplexity.MEDIUM
```

**Strategy Routes**:
1. **SIMPLE** → BM25 + Qdrant vector → RRF fusion (0 LLM calls)
2. **COMPLEX** → Reasoning-based PageIndex tree search (1-3 LLM calls first time, cached)
3. **MEDIUM** → Hybrid approach

#### Reciprocal Rank Fusion (RRF)
```python
def reciprocal_rank_fusion(bm25_results, vector_results, k=60, top_n=8):
    """Combine BM25 and vector rankings"""
    
    scores = {}
    
    # BM25 contribution
    for rank, (chunk, _) in enumerate(bm25_results, 1):
        scores[chunk] = scores.get(chunk, 0.0) + 1.0 / (k + rank)
    
    # Vector contribution
    for rank, (chunk, _) in enumerate(vector_results, 1):
        scores[chunk] = scores.get(chunk, 0.0) + 1.0 / (k + rank)
    
    # Return top-n by combined score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in ranked[:top_n]]
```

#### Prompt Compression
```python
def compress_chunks(chunks: List[str], max_total_chars: int = 500_000) -> List[str]:
    """Remove boilerplate before sending to LLM"""
    
    compressed = []
    total = 0
    
    for chunk in chunks:
        # Remove excessive whitespace (25-35% token reduction)
        cleaned = re.sub(r"\n{3,}", "\n\n", chunk)        # Remove blank lines
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)      # Collapse spaces
        cleaned = cleaned.strip()
        
        # Budget guard
        if total + len(cleaned) > max_total_chars:
            remaining = max_total_chars - total
            if remaining > 200:
                cleaned = cleaned[:remaining] + "…"
                compressed.append(cleaned)
            break
        
        compressed.append(cleaned)
        total += len(cleaned)
    
    return compressed
```

---

## 8. INTELLIGENCE LAYER & KPI FRAMEWORK

### Multi-Stage LLM Pipeline
**File**: [app/intelligence/pipeline.py](app/intelligence/pipeline.py)

#### Architecture
```
Stage 1: KPI Extraction              (fast/cheap model)
    ↓
Stage 2: DMAIC + Six Sigma Reasoning (strong model)
    ↓
Stage 3: Recommendations             (fast/cheap model)
    ↓
Stage 4: Final Assembly              (strong model)
```

#### Models
```python
_CHEAP_MODEL = "gemini-2.0-flash"    # Stages 1, 3: Fast & cheap
_SMART_MODEL = "gemini-2.5-flash"    # Stages 2, 4: Reasoning required
```

#### Stage 1: KPI Extraction
**System prompt** (Lines 34-38):
> "You are a KPI extraction specialist. Extract 15-50 KPIs from documents. Return STRICT JSON only."

**Output format**:
```json
{
  "kpis": [
    {
      "id": "kpi_001",
      "title": "Well Completion Cost",
      "value": 2850000,
      "unit": "$",
      "target": 2500000,
      "trend": "deteriorating",
      "changeType": "negative",
      "confidence": 0.88,
      "category": "financial|safety|operations|efficiency|reliability|quality",
      "priority": "tier1|tier2|tier3|tier4",
      "owner": "Operations|HSE|Finance|Engineering|Safety",
      "source_reference": {
        "rig_name": "PARAGON MSS1",
        "report_date": "2024-01-15",
        "source_section": "Well Completion",
        "raw_evidence": "Well-A3 completed at $2.85M, vs $2.5M budget",
        "calculation_method": "direct_extract|sum|average|derived|inferred"
      },
      "deviationScore": 14,       // (2850-2500)/2500 * 100
      "financialImpactScore": 85,
      "riskScore": 72,
      "trendScore": 30,           // deteriorating = lower score
      "icon": "dollar|trending|chart",
      "color": "red|green|yellow"
    }
  ]
}
```

#### Stage 2: DMAIC Reasoning
**Input**: KPIs from Stage 1  
**Output**: Root-cause analysis, DMAIC phase recommendations

**Framework**:
- **Define**: Problem KPI statement + context
- **Measure**: Baseline metrics + deviation analysis
- **Analyze**: Root causes (queries graph for related KPIs)
- **Improve**: Recommended actions with leverage points
- **Control**: Monitoring specifics

#### Stage 3: Recommendations
**Input**: KPIs + DMAIC analysis  
**Output**: Structured recommendations with ROI

**Structure**:
```json
{
  "recommendations": [
    {
      "id": "rec_001",
      "title": "Optimize well completion workflow",
      "description": "Reduce non-productive time by 15% through revised completion procedures",
      "estimated_roi": 425000,           // Annual $ savings
      "implementation_effort": "medium",
      "timeline_weeks": 8,
      "kpi_references": ["kpi_001", "kpi_005", "kpi_012"],
      "responsible_parties": ["Operations Manager", "Engineering Lead"],
      "dependencies": ["Supply chain approval"],
      "success_metrics": ["Completion cost < $2.5M", "NPT < 8%"],
      "risk_level": "low"
    }
  ]
}
```

#### Stage 4: Final Assembly
**Input**: All prior stages  
**Output**: Executive dashboards (CEO view, Manager view, Boardroom view)

### KPI Data Structures
**File**: [app/intelligence/pipeline.py](app/intelligence/pipeline.py)

```python
# Core KPI object (from extraction)
{
    "id": str,
    "title": str,                           # Max 5 words
    "value": float,                         # Actual measurement
    "unit": "$|%|count|hrs|days|bbl|mcf|psi|ft|score",
    "target": float | null,
    "trend": "improving|deteriorating|stable",
    "changeType": "positive|negative|neutral",
    "confidence": 0.0-1.0,
    "category": "financial|safety|operations|efficiency|reliability|quality",
    "priority": "tier1|tier2|tier3|tier4",
    "owner": "Department|Role",
    "source_reference": {
        "rig_name": str,
        "report_date": "YYYY-MM-DD",
        "source_section": str,
        "raw_evidence": str,                # Max 40 words
        "calculation_method": str
    },
    "deviationScore": 0-100,               # |actual - target| / target * 100
    "financialImpactScore": 0-100,         # From financial_engine
    "riskScore": 0-100,                    # Safety/reliability emphasis
    "trendScore": 0-100,                   # Improvement vs deterioration
    "icon": "dollar|activity|trending|users|chart",
    "color": "green|red|blue|yellow|purple"
}
```

### Financial Engine (Deterministic Scoring)
**File**: [app/intelligence/financial_engine.py](app/intelligence/financial_engine.py)

#### Category Multipliers
```python
_CATEGORY_MULTIPLIERS = {
    "financial":    1.0,         # Already in $
    "safety":       50_000.0,    # Each incident = $50K cost
    "operations":   10_000.0,    # Each % downtime = $10K
    "efficiency":   5_000.0,
    "reliability":  8_000.0,
    "quality":      3_000.0
}
```

#### Unit Multipliers
```python
_UNIT_MULTIPLIERS = {
    "$":    1.0,
    "bbl":  70.0,                # $70/barrel (market-dependent)
    "mcf":  3.5,                 # $3.50/mcf gas
    "%":    10_000.0,
    "hrs":  5_000.0,             # Hour of downtime
    "days": 50_000.0,            # Day of downtime
    "count": 15_000.0,           # Each incident
    "psi":  500.0,               # Pressure deviation
}
```

#### Key Functions
```python
def compute_deviation_score(kpi: Dict) -> float:
    """How far from target (0=on-target, 100=severely-off)"""
    value = kpi.get("value")
    target = kpi.get("target")
    if not target:
        return 20.0  # Unknown
    pct = abs(value - target) / abs(target)
    return min(pct * 100, 100)

def compute_financial_impact(kpi: Dict) -> Optional[float]:
    """Annual $ financial impact of KPI deviation"""
    unit = kpi.get("unit", "default").lower()
    category = kpi.get("category", "default").lower()
    
    # Priority: explicit unit > category > default
    multiplier = _UNIT_MULTIPLIERS.get(unit) or _CATEGORY_MULTIPLIERS.get(category, 2_000)
    
    # Deviation-adjusted impact
    deviation = compute_deviation_score(kpi)
    return (kpi["value"] * deviation / 100) * multiplier

def compute_recommendation_roi(rec: Dict, kpis: List[Dict]) -> float:
    """ROI of a recommendation based on impacted KPIs"""
    total_impact = 0
    for kpi_id in rec.get("kpi_references", []):
        kpi = next((k for k in kpis if k["id"] == kpi_id), None)
        if kpi:
            impact = compute_financial_impact(kpi)
            total_impact += impact or 0
    
    # Implementation cost (rough estimate)
    effort_hours = {
        "low": 100,
        "medium": 300,
        "high": 800
    }.get(rec.get("implementation_effort"), 300)
    
    impl_cost = effort_hours * 150  # $150/hour blended cost
    
    return total_impact - impl_cost
```

### Drilling Domain Analytics
**File**: [app/intelligence/drilling_engine.py](app/intelligence/drilling_engine.py)

#### KPI Classification
```python
def extract_drilling_kpis(kpis: List[Dict]) -> Dict:
    """Classify KPIs into drilling sub-domains"""
    
    result = {
        "npt": [],           # Non-Productive Time
        "rop": [],           # Rate of Penetration
        "reliability": [],   # MTBF/MTTR
        "cost": [],
        "mud": [],
        "other": []
    }
    
    for kpi in kpis:
        title = kpi.get("title", "").lower()
        
        if re.search(r"\b(npt|downtime|stuck|blowout|kick)\b", title):
            result["npt"].append(kpi)
        elif re.search(r"\b(rop|penetration|drilling speed)\b", title):
            result["rop"].append(kpi)
        # ... more patterns
    
    return result
```

#### Specific Metrics
```python
def compute_npt_analysis(kpis):
    """Non-Productive Time cost analysis"""
    cost_per_hour = 15_000  # rig rate + services
    return {
        "total_npt_hours": sum_matching_kpis("npt"),
        "npt_cost": total_npt_hours * cost_per_hour,
        "top_causes": ["stuck pipe", "equipment failure", ...],
        "cost_by_cause": {...}
    }

def compute_rop_metrics(kpis):
    """Rate of Penetration optimization"""
    benchmark_cost = 450  # $/foot
    improvement_potential = 0.15  # 15% faster drilling
    
    return {
        "current_rop": ...,
        "rop_efficiency": ...,
        "potential_time_savings": ...,
        "potential_cost_savings": ...,
        "optimization_opportunities": [...]
    }
```

### Entity Extraction & Enrichment
**File**: [app/intelligence/deduction_enrichment.py](app/intelligence/deduction_enrichment.py)

#### Entity Types
```python
class EntityTypePattern(Enum):
    DEPARTMENT = "DEPARTMENT"     # Finance, Operations, Drilling, HSE, etc.
    ROLE = "ROLE"                 # CEO, CFO, VP, Manager, Engineer, Inspector
    PROCESS = "PROCESS"           # Drilling, Production, Maintenance, Planning
    SYSTEM = "SYSTEM"             # ERP, MES, SCADA, LIMS, PI System, DCS
    EQUIPMENT = "EQUIPMENT"       # Rig, Pipeline, Compressor, Pump, BHA, Wellhead
    LOCATION = "LOCATION"         # Field, Basin, Well, Platform, Block, Region
    KPI = "KPI"                   # Metrics with units/targets
```

#### Keyword-Based Classification
```python
# 100+ keywords pre-classified
DEPARTMENT_KEYWORDS = {
    'finance', 'operations', 'drilling', 'production',
    'subsurface', 'facilities', 'engineering', 'maintenance',
    'safety', 'compliance', ...
}

ROLE_KEYWORDS = {
    'ceo', 'cfo', 'director', 'manager', 'engineer',
    'analyst', 'supervisor', 'operator', 'inspector', ...
}

# ... similar for PROCESS, SYSTEM, EQUIPMENT, LOCATION, KPI
```

---

## 9. PHASE 4 INTEGRATION OPPORTUNITIES

### Immediate Extensions

#### 1. Community Detection
```python
# Add to graph_analytics.py
def find_communities(self, min_size: int = 3) -> List[List[str]]:
    """
    Identify clusters of related entities using Louvain or similar
    
    For example:
    - Community: [Finance Manager, CFO, Cost KPI, Budget System]
    - Community: [Drilling Rig, ROP Metric, NPT Metric, Equipment Failures]
    """
```

#### 2. Enhanced Anomaly Detection
```python
# Add to graph_analytics.py or impact_engine.py
def detect_anomalies(self) -> List[Dict]:
    """
    Find unusual patterns:
    - Entity with high mention but low confidence
    - Relationship that exists in only 1 document (weak evidence)
    - KPI with sudden trend inversion
    - Orphaned entities (no relationships)
    """
```

#### 3. Cross-Document Fact Validation
```python
# Leverage mentions tables
def validate_cross_document(self, entity_id: str) -> Dict:
    """
    Check consistency of entity across documents:
    - Total mentions: 47 docs
    - Confidence range: 0.65-0.98
    - Aliases found: [PARAGON, MSS1, Rig-101]
    - Conflicting properties: location (2 mentions of GoM, 1 of SE Asia)
    
    Return validation score + conflicts list
    """
```

#### 4. Temporal Analysis
```python
# Enhance storage with timestamps
def analyze_trends(self, entity_id: str, time_window: str = "month") -> Dict:
    """
    Track KPI values, confidence, relationships over time
    - Jan: $45/bbl, confidence 0.92, mentions 12 docs
    - Feb: $42/bbl, confidence 0.88, mentions 15 docs
    - Feb trend: Improving (cost down, more evidence)
    """
```

#### 5. Graph Visualization API
```python
# Add to graph_analytics.py
def export_to_cytoscape(self, entity_ids: List[str], max_hops: int = 2):
    """
    Export subgraph in Cytoscape.js format for frontend visualization
    
    Returns:
    {
        "nodes": [{"id": "...", "label": "...", "type": "..."}],
        "edges": [{"source": "...", "target": "...", "label": "..."}]
    }
    """
```

### Integration with Existing APIs
- **[vector_storage.py](vector_storage.py)**: Already integrated, ready for Phase 4
- **[app/storage/graph_storage.py](app/storage/graph_storage.py)**: Orchestration layer ready
- **[app/intelligence/impact_engine.py](app/intelligence/impact_engine.py)**: Core DMAIC engine in place
- **[app/retrieval/hybrid_retrieval.py](app/retrieval/hybrid_retrieval.py)**: Can use graph for relevance re-ranking

---

## 10. CURRENT SYSTEM HEALTH

### Strengths ✅
- **Deduplication**: 85% fuzzy matching catches entity aliases
- **Evidence tracking**: Mention tables provide traceability
- **Deterministic scoring**: Financial impact calculated, not LLM-guessed
- **Multi-stage pipeline**: Reduces hallucinations (4 focused stages, not 1 monolithic)
- **Local persistence**: Qdrant + SQLite = zero external dependencies for vector/graph storage
- **Semantic chunking**: Respects document structure (headings, lists, tables)
- **Hybrid retrieval**: BM25 + vector takes advantages of both ranking methods
- **Domain expertise**: Drilling KPIs, DMAIC framework, ESG scoring built-in

### Ready for Phase 4 🚀
- Vector storage: Fully implemented with payload filtering
- Graph CRUD: Entity/relationship creation + mentions tracking
- Path finding: BFS algorithm with relevance scoring
- Cascading impact: Multi-hop analysis with $ aggregation
- Entity resolution: Database-backed deduplication

---

## 11. QUICK START FOR PHASE 4 DEVELOPMENT

### Accessing Current Data

**Qdrant vectors**:
```python
from vector_storage import get_vector_service

svc = get_vector_service()
query_emb = svc.generate_embedding("Well cost anomaly")
results = svc.search(query_emb, doc_id="doc_123", top_k=5)
# Returns: [(chunk_text, similarity_score), ...]
```

**Graph entities**:
```python
from app.processors.graph_rag.entity_resolver import EntityResolver

resolver = EntityResolver()
similar = resolver.find_similar_entities("PARAGON MSS1", entity_type="EQUIPMENT", threshold=0.85)
# Returns: [(entity_id, canonical_name, similarity), ...]
```

**Graph relationships**:
```python
from app.processors.graph_rag.graph_analytics import GraphAnalytics

analytics = GraphAnalytics()
paths = analytics.find_paths("ent_001", "ent_005", max_depth=4)
# Returns: [{"entities": [...], "relationships": [...], "length": 2}, ...]
```

**Impact analysis**:
```python
from app.intelligence.impact_engine import ImpactEngine, Entity, Relationship

engine = ImpactEngine()
kpi_entity = Entity(id="ent_001", name="Well Cost", entity_type="KPI", confidence=0.95)
analysis = engine.analyze_kpi_impact(kpi_entity, entities, relationships, financial_impact=350_000)
# Returns: Total cascading impact, root causes, recommended actions
```

### Adding Extensions

**New graph algorithm**:
1. Add method to `GraphAnalytics` class
2. Query SQLite tables: `GraphEntity`, `GraphRelationship`
3. Return structured result (List[Dict])

**New KPI enrichment**:
1. Add method to domain engine (drilling_engine.py, esg_engine.py)
2. Call `compute_financial_impact()` for $ scoring
3. Return enhanced KPI dict

**New retrieval strategy**:
1. Add classifier rule to `classify_document()`
2. Implement strategy in `HybridRetrieval` class
3. Use RRF if combining rankings

---

## APPENDIX: File Location Reference

| Component | File | Key Classes/Functions |
|---|---|---|
| **Vector Storage** | [vector_storage.py](vector_storage.py) | `VectorStorageService`, `get_vector_service()` |
| **Graph Engine** | [app/processors/graph_rag/graph_engine.py](app/processors/graph_rag/graph_engine.py) | `KnowledgeGraphEngine` |
| **Entity Resolution** | [app/processors/graph_rag/entity_resolver.py](app/processors/graph_rag/entity_resolver.py) | `EntityResolver`, `normalize_entity_name()`, `find_similar_entities()` |
| **Graph Analytics** | [app/processors/graph_rag/graph_analytics.py](app/processors/graph_rag/graph_analytics.py) | `GraphAnalytics`, `find_paths()`, `shortest_path()` |
| **Fact Conversion** | [app/processors/graph_rag/facts_to_graph.py](app/processors/graph_rag/facts_to_graph.py) | `FactsToGraphConverter` |
| **Graph Storage** | [app/storage/graph_storage.py](app/storage/graph_storage.py) | `GraphStorage`, `integrate_facts()` |
| **Deduction** | [app/processors/deduction.py](app/processors/deduction.py) | `DeductionEngine`, `extract_facts()`, `build_knowledge_graph()` |
| **Impact Analysis** | [app/intelligence/impact_engine.py](app/intelligence/impact_engine.py) | `ImpactEngine`, `analyze_kpi_impact()`, `Entity`, `Relationship`, `ImpactPath` |
| **Financial Engine** | [app/intelligence/financial_engine.py](app/intelligence/financial_engine.py) | `compute_deviation_score()`, `compute_financial_impact()`, `compute_recommendation_roi()` |
| **Drilling Analytics** | [app/intelligence/drilling_engine.py](app/intelligence/drilling_engine.py) | `extract_drilling_kpis()`, `compute_npt_analysis()`, `build_drilling_view()` |
| **Deduction Enrichment** | [app/intelligence/deduction_enrichment.py](app/intelligence/deduction_enrichment.py) | `BusinessEntityExtractor`, `EntityTypePattern` |
| **Intelligence Pipeline** | [app/intelligence/pipeline.py](app/intelligence/pipeline.py) | 4-stage KPI pipeline, `run_pipeline()` |
| **Validation** | [app/intelligence/validation.py](app/intelligence/validation.py) | `validate_kpis()`, `validate_recommendations()` |
| **Chunking** | [chunker.py](chunker.py) | `chunk_text()`, `split_by_semantic_units()` |
| **Hybrid Retrieval** | [app/retrieval/hybrid_retrieval.py](app/retrieval/hybrid_retrieval.py) | `HybridRetrieval`, `reciprocal_rank_fusion()`, `classify_document()` |
| **Database Models** | [app/db/models.py](app/db/models.py) | `GraphEntity`, `GraphRelationship`, `GraphEntityMention`, `GraphRelationshipMention` |

---

**End of Analysis** ✅
