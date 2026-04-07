"""
GraphRAG Migration Script
Migrates existing knowledge graph data from graph_edges to new GraphRAG schema
"""
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple, Optional
import uuid
from difflib import SequenceMatcher

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Extract DB path from DATABASE_URL
DB_PATH = settings.DATABASE_URL.replace('sqlite:///', '')


class GraphRAGMigration:
    """Handles migration from legacy graph_edges to new GraphRAG schema"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.entity_cache: Dict[str, str] = {}  # Maps normalized names to entity IDs
        self.entity_similarity_threshold = 0.80  # 80% similarity for matching
        
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.db_path}")
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def create_graphrag_tables(self):
        """Create new GraphRAG tables (AlembicORM migration)"""
        logger.info("Creating GraphRAG tables...")
        cur = self.conn.cursor()
        
        try:
            # Graph entities table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS graph_entities (
                    id TEXT PRIMARY KEY,
                    canonical_name TEXT NOT NULL UNIQUE,
                    entity_type TEXT NOT NULL,
                    aliases TEXT DEFAULT '[]',
                    first_doc_id TEXT,
                    mention_count INTEGER DEFAULT 1,
                    total_confidence INTEGER DEFAULT 0,
                    properties TEXT DEFAULT '{}',
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (first_doc_id) REFERENCES documents(id) ON DELETE SET NULL
                )
            ''')
            
            cur.execute('CREATE INDEX IF NOT EXISTS idx_entity_canonical ON graph_entities(canonical_name)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_entity_type ON graph_entities(entity_type)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_entity_mention_count ON graph_entities(mention_count)')
            
            # Graph relationships table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS graph_relationships (
                    id TEXT PRIMARY KEY,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    confidence INTEGER DEFAULT 50,
                    mention_count INTEGER DEFAULT 1,
                    total_documents INTEGER DEFAULT 1,
                    is_bidirectional INTEGER DEFAULT 0,
                    properties TEXT DEFAULT '{}',
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (source_entity_id) REFERENCES graph_entities(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_entity_id) REFERENCES graph_entities(id) ON DELETE CASCADE
                )
            ''')
            
            cur.execute('CREATE INDEX IF NOT EXISTS idx_rel_source ON graph_relationships(source_entity_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_rel_target ON graph_relationships(target_entity_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_rel_type ON graph_relationships(relationship_type)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_rel_source_target ON graph_relationships(source_entity_id, target_entity_id)')
            
            # Entity mentions table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS graph_entity_mentions (
                    id TEXT PRIMARY KEY,
                    entity_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    mention_text TEXT NOT NULL,
                    position INTEGER,
                    confidence INTEGER DEFAULT 50,
                    created_at TEXT,
                    FOREIGN KEY (entity_id) REFERENCES graph_entities(id) ON DELETE CASCADE,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
                )
            ''')
            
            cur.execute('CREATE INDEX IF NOT EXISTS idx_mention_entity ON graph_entity_mentions(entity_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_mention_doc ON graph_entity_mentions(doc_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_mention_chunk ON graph_entity_mentions(chunk_id)')
            
            # Relationship mentions table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS graph_relationship_mentions (
                    id TEXT PRIMARY KEY,
                    relationship_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    mention_text TEXT,
                    confidence INTEGER DEFAULT 50,
                    source_fact TEXT,
                    created_at TEXT,
                    FOREIGN KEY (relationship_id) REFERENCES graph_relationships(id) ON DELETE CASCADE,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
                )
            ''')
            
            cur.execute('CREATE INDEX IF NOT EXISTS idx_rel_mention_rel ON graph_relationship_mentions(relationship_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_rel_mention_doc ON graph_relationship_mentions(doc_id)')
            
            # Paths cache table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS graph_paths (
                    id TEXT PRIMARY KEY,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    path_data TEXT,
                    path_length INTEGER,
                    relevance_score INTEGER DEFAULT 50,
                    created_at TEXT,
                    expires_at TEXT,
                    FOREIGN KEY (source_entity_id) REFERENCES graph_entities(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_entity_id) REFERENCES graph_entities(id) ON DELETE CASCADE
                )
            ''')
            
            cur.execute('CREATE INDEX IF NOT EXISTS idx_path_source_target ON graph_paths(source_entity_id, target_entity_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_path_expires ON graph_paths(expires_at)')
            
            self.conn.commit()
            logger.info("✓ GraphRAG tables created successfully")
            
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                logger.info("✓ GraphRAG tables already exist")
            else:
                logger.error(f"Error creating tables: {e}")
                raise
    
    def fetch_existing_edges(self) -> List[Dict[str, Any]]:
        """Fetch all existing graph edges"""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT id, doc_id, edge, created_at 
            FROM graph_edges
            ORDER BY created_at ASC
        ''')
        
        edges = []
        for row in cur.fetchall():
            try:
                edge_data = json.loads(row['edge']) if isinstance(row['edge'], str) else row['edge']
                edges.append({
                    'id': row['id'],
                    'doc_id': row['doc_id'],
                    'edge': edge_data,
                    'created_at': row['created_at']
                })
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse edge {row['id']}: {e}")
                continue
        
        logger.info(f"Fetched {len(edges)} existing edges")
        return edges
    
    def normalize_entity_name(self, name: str, entity_type: str = None) -> str:
        """Normalize entity name for deduplication"""
        # Basic normalization
        normalized = name.strip().lower()
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        return normalized
    
    def find_similar_entity(self, normalized_name: str, entity_type: Optional[str] = None) -> Optional[str]:
        """Find existing entity by similarity matching"""
        for cached_name, entity_id in self.entity_cache.items():
            similarity = SequenceMatcher(None, normalized_name, cached_name).ratio()
            if similarity >= self.entity_similarity_threshold:
                # Also check type match if provided
                if entity_type:
                    cur = self.conn.cursor()
                    cur.execute('SELECT entity_type FROM graph_entities WHERE id = ?', (entity_id,))
                    row = cur.fetchone()
                    if row and row['entity_type'] == entity_type:
                        return entity_id
                else:
                    return entity_id
        return None
    
    def get_or_create_entity(self, name: str, entity_type: str = "CONCEPT", doc_id: str = None, confidence: int = 50) -> str:
        """Get or create entity with deduplication"""
        normalized_name = self.normalize_entity_name(name)
        
        # Check cache first
        if normalized_name in self.entity_cache:
            entity_id = self.entity_cache[normalized_name]
            # Update mention count
            cur = self.conn.cursor()
            cur.execute('''
                UPDATE graph_entities 
                SET mention_count = mention_count + 1,
                    total_confidence = total_confidence + ?,
                    updated_at = ?
                WHERE id = ?
            ''', (confidence, datetime.now(timezone.utc).isoformat(), entity_id))
            self.conn.commit()
            return entity_id
        
        # Check for similar entities
        similar_entity_id = self.find_similar_entity(normalized_name, entity_type)
        if similar_entity_id:
            self.entity_cache[normalized_name] = similar_entity_id
            return similar_entity_id
        
        # Create new entity
        entity_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO graph_entities 
            (id, canonical_name, entity_type, first_doc_id, mention_count, total_confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (entity_id, normalized_name, entity_type, doc_id, 1, confidence, now, now))
        
        self.conn.commit()
        self.entity_cache[normalized_name] = entity_id
        logger.debug(f"Created new entity: {normalized_name} ({entity_type})")
        return entity_id
    
    def infer_entity_type(self, text: str) -> str:
        """Basic entity type inference"""
        text_lower = text.lower()
        
        # Simple heuristics
        if any(word in text_lower for word in ['company', 'corp', 'inc', 'ltd', 'llc']):
            return "ORGANIZATION"
        elif any(word in text_lower for word in ['mr', 'ms', 'mr.', 'dr', 'dr.']):
            return "PERSON"
        elif any(word in text_lower for word in ['street', 'avenue', 'road', 'city', 'country', 'state']):
            return "LOCATION"
        
        return "CONCEPT"
    
    def parse_edge(self, edge: Dict[str, Any]) -> Tuple[str, str, str]:
        """Parse edge structure to extract source, predicate, target"""
        # Handle different edge formats
        if 'source' in edge and 'target' in edge and 'predicate' in edge:
            return edge['source'], edge['predicate'], edge['target']
        elif 'source' in edge and 'target' in edge and 'type' in edge:
            return edge['source'], edge['type'], edge['target']
        else:
            logger.warning(f"Unknown edge format: {edge}")
            return None, None, None
    
    def migrate_edges_to_graphrag(self):
        """Migrate edges from graph_edges to new GraphRAG schema"""
        logger.info("Starting edge migration...")
        edges = self.fetch_existing_edges()
        
        successful = 0
        failed = 0
        
        for edge_record in edges:
            try:
                edge = edge_record['edge']
                doc_id = edge_record['doc_id']
                
                source, predicate, target = self.parse_edge(edge)
                
                if not (source and predicate and target):
                    logger.warning(f"Skipping malformed edge {edge_record['id']}")
                    failed += 1
                    continue
                
                confidence = edge.get('confidence', 50)
                if isinstance(confidence, float):
                    confidence = int(confidence * 100)
                confidence = max(0, min(100, confidence))  # Clamp to 0-100
                
                # Infer entity types
                source_type = self.infer_entity_type(source)
                target_type = self.infer_entity_type(target)
                
                # Get or create entities
                source_entity_id = self.get_or_create_entity(source, source_type, doc_id, confidence)
                target_entity_id = self.get_or_create_entity(target, target_type, doc_id, confidence)
                
                # Get or create relationship
                rel_id = self._create_relationship(
                    source_entity_id, target_entity_id, predicate, confidence, doc_id, edge_record['created_at']
                )
                
                # Create relationship mention
                self._create_relationship_mention(
                    rel_id, doc_id, None, confidence, json.dumps(edge)
                )
                
                successful += 1
                
                if successful % 100 == 0:
                    logger.info(f"Migrated {successful} edges...")
                    
            except Exception as e:
                logger.error(f"Error migrating edge {edge_record['id']}: {e}")
                failed += 1
                continue
        
        logger.info(f"✓ Migration complete: {successful} successful, {failed} failed")
        return successful, failed
    
    def _create_relationship(self, source_id: str, target_id: str, rel_type: str, 
                            confidence: int, doc_id: str, created_at: str) -> str:
        """Create or update relationship"""
        cur = self.conn.cursor()
        
        # Check if relationship already exists
        cur.execute('''
            SELECT id FROM graph_relationships 
            WHERE source_entity_id = ? AND target_entity_id = ? AND relationship_type = ?
            LIMIT 1
        ''', (source_id, target_id, rel_type))
        
        row = cur.fetchone()
        if row:
            # Update existing relationship
            rel_id = row['id']
            cur.execute('''
                UPDATE graph_relationships
                SET mention_count = mention_count + 1,
                    total_documents = total_documents + 1,
                    confidence = (confidence + ?) / 2,
                    updated_at = ?
                WHERE id = ?
            ''', (confidence, datetime.now(timezone.utc).isoformat(), rel_id))
        else:
            # Create new relationship
            rel_id = str(uuid.uuid4())
            cur.execute('''
                INSERT INTO graph_relationships
                (id, source_entity_id, target_entity_id, relationship_type, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (rel_id, source_id, target_id, rel_type, confidence, created_at, datetime.now(timezone.utc).isoformat()))
        
        self.conn.commit()
        return rel_id
    
    def _create_relationship_mention(self, rel_id: str, doc_id: str, chunk_id: Optional[str], 
                                    confidence: int, source_fact: str):
        """Create relationship mention record"""
        cur = self.conn.cursor()
        mention_id = str(uuid.uuid4())
        
        cur.execute('''
            INSERT INTO graph_relationship_mentions
            (id, relationship_id, doc_id, chunk_id, confidence, source_fact, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (mention_id, rel_id, doc_id, chunk_id, confidence, source_fact, datetime.now(timezone.utc).isoformat()))
        
        self.conn.commit()
    
    def update_graph_edges_table(self):
        """Update existing graph_edges with references to new entities"""
        logger.info("Updating graph_edges table with new entity references...")
        cur = self.conn.cursor()
        
        # Add new columns if they don't exist
        try:
            cur.execute('ALTER TABLE graph_edges ADD COLUMN entity_source_id TEXT')
            cur.execute('ALTER TABLE graph_edges ADD COLUMN entity_target_id TEXT')
            cur.execute('ALTER TABLE graph_edges ADD COLUMN edge_type TEXT')
            cur.execute('ALTER TABLE graph_edges ADD COLUMN confidence REAL')
            self.conn.commit()
            logger.info("Added new columns to graph_edges")
        except sqlite3.OperationalError:
            logger.info("Columns already exist in graph_edges")
        
        # Update graph_edges with entity references
        cur.execute('SELECT id, edge FROM graph_edges WHERE entity_source_id IS NULL')
        edges_to_update = cur.fetchall()
        
        for edge_row in edges_to_update:
            try:
                edge = json.loads(edge_row['edge']) if isinstance(edge_row['edge'], str) else edge_row['edge']
                source, predicate, target = self.parse_edge(edge)
                
                if source and target:
                    source_normalized = self.normalize_entity_name(source)
                    target_normalized = self.normalize_entity_name(target)
                    
                    source_entity_id = self.entity_cache.get(source_normalized)
                    target_entity_id = self.entity_cache.get(target_normalized)
                    
                    if source_entity_id and target_entity_id:
                        cur.execute('''
                            UPDATE graph_edges
                            SET entity_source_id = ?, entity_target_id = ?, edge_type = ?, confidence = ?
                            WHERE id = ?
                        ''', (source_entity_id, target_entity_id, predicate, edge.get('confidence', 0.5), edge_row['id']))
            except Exception as e:
                logger.warning(f"Error updating edge {edge_row['id']}: {e}")
        
        self.conn.commit()
        logger.info("✓ graph_edges table updated")
    
    def run_migration(self):
        """Execute complete migration"""
        try:
            self.connect()
            logger.info("=" * 60)
            logger.info("GraphRAG Migration Started")
            logger.info("=" * 60)
            
            # Step 1: Create new tables
            self.create_graphrag_tables()
            
            # Step 2: Migrate edges to new schema
            success, fail = self.migrate_edges_to_graphrag()
            
            # Step 3: Update existing graph_edges for backward compatibility
            self.update_graph_edges_table()
            
            logger.info("=" * 60)
            logger.info("✓ GraphRAG Migration Completed Successfully!")
            logger.info(f"  - Entities created/updated: {len(self.entity_cache)}")
            logger.info(f"  - Edges migrated: {success}")
            logger.info(f"  - Edges failed: {fail}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
        finally:
            self.close()


def main():
    """Main migration entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    migrator = GraphRAGMigration()
    success = migrator.run_migration()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
