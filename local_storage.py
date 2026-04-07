"""
Local Storage Service - SQLite + FAISS fallback
Provides full functionality without requiring Supabase
"""

import sqlite3
import json
import pickle
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging
import numpy as np
import faiss

logger = logging.getLogger(__name__)


class LocalStorageService:
    """Local storage using SQLite + FAISS for vector search"""
    
    def __init__(self, db_path: str = "local_storage.db", index_path: str = "faiss_index.bin"):
        self.db_path = db_path
        self.index_path = index_path
        self.embedding_dim = 384
        self.index = None
        self.id_map = []  # Maps FAISS index positions to chunk IDs
        
        self._init_database()
        self._load_or_create_index()
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                original_file_path TEXT,
                total_chunks INTEGER DEFAULT 0,
                status TEXT DEFAULT 'processing',
                metadata TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # Create document_chunks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_text TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                embedding BLOB,
                metadata TEXT,
                created_at TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        ''')

        # Traceability-first insights table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS insights (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                insight_id TEXT NOT NULL,
                insight_text TEXT,
                insight_type TEXT,
                source_pages TEXT NOT NULL,
                source_chunks TEXT,
                supporting_groups TEXT,
                group_title TEXT,
                section_title TEXT,
                confidence REAL,
                metadata TEXT,
                created_at TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                CONSTRAINT uq_insight_per_doc UNIQUE(document_id, insight_id),
                CONSTRAINT check_source_pages_not_empty CHECK (json_array_length(source_pages) > 0)
            )
        ''')

        # Aggregation layer persistence (rig/group summaries)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rig_summaries (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                rig_id TEXT NOT NULL,
                rig_title TEXT,
                source_pages TEXT NOT NULL,
                source_section_ids TEXT,
                summary TEXT,
                findings TEXT,
                kpis TEXT,
                risks TEXT,
                confidence REAL,
                metadata TEXT,
                created_at TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                CONSTRAINT uq_rig_summary_per_doc UNIQUE(document_id, rig_id),
                CONSTRAINT check_rig_source_pages_not_empty CHECK (json_array_length(source_pages) > 0)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_insights_document ON insights(document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_insights_insight_id ON insights(insight_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rig_summaries_document ON rig_summaries(document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rig_summaries_rig_id ON rig_summaries(rig_id)')
        
        conn.commit()
        conn.close()
        logger.info(f"Local database initialized: {self.db_path}")
    
    def _load_or_create_index(self):
        """Load existing FAISS index or create new one"""
        if os.path.exists(self.index_path) and os.path.exists(self.index_path + ".map"):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.index_path + ".map", 'rb') as f:
                    self.id_map = pickle.load(f)
                logger.info(f"Loaded FAISS index with {len(self.id_map)} vectors")
            except Exception as e:
                logger.warning(f"Failed to load index: {e}. Creating new one.")
                self._create_new_index()
        else:
            self._create_new_index()
    
    def _create_new_index(self):
        """Create new FAISS index"""
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.id_map = []
        logger.info("Created new FAISS index")
    
    def _save_index(self):
        """Save FAISS index to disk"""
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.index_path + ".map", 'wb') as f:
                pickle.dump(self.id_map, f)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    # Document methods
    async def create_document(
        self,
        user_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
        file_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create document record"""
        try:
            import uuid
            doc_id = str(uuid.uuid4())
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO documents 
                (id, user_id, file_name, file_type, file_size, original_file_path, 
                 status, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_id, user_id, file_name, file_type, file_size, file_path,
                'processing', json.dumps(metadata or {}),
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "document": {
                    "id": doc_id,
                    "user_id": user_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "file_size": file_size
                }
            }
        except Exception as e:
            logger.error(f"Create document error: {e}")
            return {"success": False, "message": str(e)}
    
    async def update_document_status(
        self, document_id: str, status: str, total_chunks: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update document status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if total_chunks is not None:
                cursor.execute('''
                    UPDATE documents 
                    SET status = ?, total_chunks = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, total_chunks, datetime.now(timezone.utc).isoformat(), document_id))
            else:
                cursor.execute('''
                    UPDATE documents 
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, datetime.now(timezone.utc).isoformat(), document_id))
            
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            logger.error(f"Update document error: {e}")
            return {"success": False, "message": str(e)}
    
    async def get_user_documents(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user documents"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM documents 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get documents error: {e}")
            return []
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get specific document"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM documents WHERE id = ?', (document_id,))
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Get document error: {e}")
            return None
    
    async def delete_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
        """Delete document and chunks"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get chunk IDs to remove from FAISS
            cursor.execute('SELECT id FROM document_chunks WHERE document_id = ?', (document_id,))
            chunk_ids = [row[0] for row in cursor.fetchall()]
            
            # Delete from database
            cursor.execute('DELETE FROM documents WHERE id = ? AND user_id = ?', (document_id, user_id))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            # Remove from FAISS index
            if deleted and chunk_ids:
                self._rebuild_index_without_chunks(chunk_ids)
            
            return {"success": deleted, "message": "Document deleted" if deleted else "Not found"}
        except Exception as e:
            logger.error(f"Delete document error: {e}")
            return {"success": False, "message": str(e)}
    
    # Chunk methods
    async def store_chunks(self, chunks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store chunks with embeddings"""
        try:
            import uuid
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stored_chunks = []
            embeddings_to_add = []
            chunk_ids_to_add = []
            
            for chunk in chunks_data:
                chunk_id = str(uuid.uuid4())
                embedding = chunk.get('embedding')
                
                # Store in SQLite
                cursor.execute('''
                    INSERT INTO document_chunks 
                    (id, document_id, chunk_text, chunk_index, embedding, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chunk_id,
                    chunk['document_id'],
                    chunk['chunk_text'],
                    chunk['chunk_index'],
                    pickle.dumps(embedding) if embedding else None,
                    json.dumps(chunk.get('metadata', {})),
                    datetime.now(timezone.utc).isoformat()
                ))
                
                stored_chunks.append({"id": chunk_id})
                
                # Prepare for FAISS
                if embedding:
                    embeddings_to_add.append(embedding)
                    chunk_ids_to_add.append(chunk_id)
            
            conn.commit()
            conn.close()
            
            # Add to FAISS index
            if embeddings_to_add:
                embeddings_array = np.array(embeddings_to_add, dtype=np.float32)
                self.index.add(embeddings_array)
                self.id_map.extend(chunk_ids_to_add)
                self._save_index()
            
            logger.info(f"Stored {len(stored_chunks)} chunks")
            return {"success": True, "chunks": stored_chunks}
        except Exception as e:
            logger.error(f"Store chunks error: {e}")
            return {"success": False, "message": str(e)}
    
    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a document"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, document_id, chunk_text, chunk_index, metadata, created_at
                FROM document_chunks 
                WHERE document_id = ?
                ORDER BY chunk_index
            ''', (document_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get chunks error: {e}")
            return []

    async def store_insights(self, insights_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store traceable insights for a document."""
        try:
            if not insights_data:
                return {"success": True, "insights": []}

            import uuid
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            inserted = []
            now = datetime.now(timezone.utc).isoformat()
            for row in insights_data:
                source_pages = row.get("source_pages", [])
                if not isinstance(source_pages, list) or len(source_pages) == 0:
                    continue
                rec_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT OR REPLACE INTO insights (
                        id, document_id, insight_id, insight_text, insight_type,
                        source_pages, source_chunks, supporting_groups, group_title,
                        section_title, confidence, metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rec_id,
                    row.get("document_id"),
                    row.get("insight_id"),
                    row.get("insight_text"),
                    row.get("insight_type"),
                    json.dumps(source_pages),
                    json.dumps(row.get("source_chunks", [])),
                    json.dumps(row.get("supporting_groups", [])),
                    row.get("group_title"),
                    row.get("section_title"),
                    row.get("confidence"),
                    json.dumps(row.get("metadata", {})),
                    now,
                ))
                inserted.append({"id": rec_id, "insight_id": row.get("insight_id")})

            conn.commit()
            conn.close()
            return {"success": True, "insights": inserted}
        except Exception as e:
            logger.error(f"Store insights error: {e}")
            return {"success": False, "message": str(e)}

    async def get_insight(self, insight_id: str, document_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get one persisted insight by insight_id (optionally scoped to document)."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if document_id:
                cursor.execute(
                    'SELECT * FROM insights WHERE insight_id = ? AND document_id = ? LIMIT 1',
                    (insight_id, document_id),
                )
            else:
                cursor.execute('SELECT * FROM insights WHERE insight_id = ? LIMIT 1', (insight_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Get insight error: {e}")
            return None

    async def store_rig_summaries(self, summaries_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store rig/group summaries for report synthesis without vector retrieval."""
        try:
            if not summaries_data:
                return {"success": True, "summaries": []}

            import uuid
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            inserted = []
            now = datetime.now(timezone.utc).isoformat()
            for row in summaries_data:
                source_pages = row.get("source_pages", [])
                if not isinstance(source_pages, list) or len(source_pages) == 0:
                    continue
                rec_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT OR REPLACE INTO rig_summaries (
                        id, document_id, rig_id, rig_title, source_pages,
                        source_section_ids, summary, findings, kpis, risks,
                        confidence, metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rec_id,
                    row.get("document_id"),
                    row.get("rig_id"),
                    row.get("rig_title"),
                    json.dumps(source_pages),
                    json.dumps(row.get("source_section_ids", [])),
                    row.get("summary"),
                    json.dumps(row.get("findings", [])),
                    json.dumps(row.get("kpis", [])),
                    json.dumps(row.get("risks", [])),
                    row.get("confidence"),
                    json.dumps(row.get("metadata", {})),
                    now,
                ))
                inserted.append({"id": rec_id, "rig_id": row.get("rig_id")})

            conn.commit()
            conn.close()
            return {"success": True, "summaries": inserted}
        except Exception as e:
            logger.error(f"Store rig summaries error: {e}")
            return {"success": False, "message": str(e)}

    async def get_rig_summaries(self, document_id: str) -> List[Dict[str, Any]]:
        """Get persisted rig/group summaries for a document."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM rig_summaries WHERE document_id = ? ORDER BY created_at',
                (document_id,),
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Get rig summaries error: {e}")
            return []
    
    # Vector search
    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        user_id: Optional[str] = None,
        match_threshold: float = 0.5,
        match_count: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using FAISS"""
        try:
            if self.index.ntotal == 0:
                return []
            
            # Convert query to numpy array
            query_vec = np.array([query_embedding], dtype=np.float32)
            
            # Search in FAISS (get more than needed for filtering)
            k = min(match_count * 5, self.index.ntotal)
            distances, indices = self.index.search(query_vec, k)
            
            # Get chunk IDs from results
            chunk_ids = [self.id_map[idx] for idx in indices[0] if idx < len(self.id_map)]
            
            if not chunk_ids:
                return []
            
            # Fetch chunk details from SQLite
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            placeholders = ','.join('?' * len(chunk_ids))
            query = f'''
                SELECT c.*, d.file_name, d.user_id
                FROM document_chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.id IN ({placeholders})
            '''
            
            if user_id:
                query += ' AND d.user_id = ?'
                cursor.execute(query, chunk_ids + [user_id])
            else:
                cursor.execute(query, chunk_ids)
            
            rows = cursor.fetchall()
            conn.close()
            
            # Calculate similarities and filter
            results = []
            for i, row in enumerate(rows):
                if i < len(distances[0]):
                    # Convert L2 distance to similarity (inverse, normalized)
                    distance = distances[0][i]
                    similarity = 1 / (1 + distance)  # Simple conversion
                    
                    if similarity >= match_threshold:
                        result = dict(row)
                        result['similarity'] = float(similarity)
                        result['chunk_id'] = result['id']
                        results.append(result)
            
            # Sort by similarity and limit
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:match_count]
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def _rebuild_index_without_chunks(self, chunk_ids_to_remove: List[str]):
        """Rebuild FAISS index without specified chunks"""
        try:
            # Get all remaining chunks
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, embedding FROM document_chunks WHERE embedding IS NOT NULL')
            rows = cursor.fetchall()
            conn.close()
            
            # Rebuild index
            self._create_new_index()
            
            embeddings = []
            chunk_ids = []
            
            for chunk_id, embedding_blob in rows:
                if chunk_id not in chunk_ids_to_remove:
                    embedding = pickle.loads(embedding_blob)
                    embeddings.append(embedding)
                    chunk_ids.append(chunk_id)
            
            if embeddings:
                embeddings_array = np.array(embeddings, dtype=np.float32)
                self.index.add(embeddings_array)
                self.id_map = chunk_ids
                self._save_index()
                
            logger.info(f"Rebuilt FAISS index with {len(chunk_ids)} vectors")
        except Exception as e:
            logger.error(f"Rebuild index error: {e}")
    
    # Compatibility methods (for drop-in replacement)
    async def upload_file_to_storage(self, user_id: str, file_path: str, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """Store file locally"""
        try:
            storage_dir = "local_file_storage"
            os.makedirs(storage_dir, exist_ok=True)
            
            local_path = os.path.join(storage_dir, f"{user_id}_{file_name}")
            with open(local_path, 'wb') as f:
                f.write(file_content)
            
            return {"success": True, "path": local_path}
        except Exception as e:
            logger.error(f"File storage error: {e}")
            return {"success": False, "message": str(e)}


# Global instance
_local_storage_instance = None


def get_local_storage() -> LocalStorageService:
    """Get or create local storage instance"""
    global _local_storage_instance
    if _local_storage_instance is None:
        _local_storage_instance = LocalStorageService()
    return _local_storage_instance


if __name__ == "__main__":
    # Test local storage
    import asyncio
    
    async def test():
        storage = get_local_storage()
        print("✓ Local storage initialized")
        print(f"  Database: {storage.db_path}")
        print(f"  FAISS index: {storage.index_path}")
        print(f"  Vectors in index: {storage.index.ntotal}")
    
    asyncio.run(test())
