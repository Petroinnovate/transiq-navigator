"""
Local storage using SQLite
"""
import os
import sqlite3
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Extract DB path from DATABASE_URL
DB_PATH = settings.DATABASE_URL.replace('sqlite:///', '')
Path(os.path.dirname(DB_PATH) or '.').mkdir(parents=True, exist_ok=True)


class LocalStorage:
    """Local SQLite storage implementation"""
    
    def __init__(self):
        """Initialize local storage"""
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        logger.info(f"Initialized local storage at {DB_PATH}")
    
    def _init_tables(self):
        """Initialize database tables"""
        cur = self.conn.cursor()
        
        # Documents table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                metadata TEXT,
                dashboard_data TEXT,
                status TEXT DEFAULT 'processing',
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # Add dashboard_data column if it doesn't exist (migration)
        try:
            cur.execute('ALTER TABLE documents ADD COLUMN dashboard_data TEXT')
        except sqlite3.OperationalError:
            # Column already exists, ignore error
            pass
        
        # Chunks table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                chunk_text TEXT NOT NULL,
                chunk_index INTEGER,
                metadata TEXT,
                created_at TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        ''')
        
        # Knowledge graph edges table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS graph_edges (
                id TEXT PRIMARY KEY,
                doc_id TEXT,
                edge TEXT,
                created_at TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        ''')
        
        # Batches table (for multi-file uploads)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                total_files INTEGER,
                completed_files INTEGER DEFAULT 0,
                failed_files INTEGER DEFAULT 0,
                status TEXT DEFAULT 'processing',
                metadata TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # Batch documents mapping table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS batch_documents (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                task_id TEXT,
                file_name TEXT,
                status TEXT DEFAULT 'queued',
                error TEXT,
                created_at TEXT,
                FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        ''')
        
        # Task status table (Celery task tracking)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS task_status (
                task_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                status TEXT DEFAULT 'queued',
                stage TEXT,
                progress INTEGER DEFAULT 0,
                error TEXT,
                result TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes
        cur.execute('CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_graph_edges_doc_id ON graph_edges(doc_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_batch_documents_batch_id ON batch_documents(batch_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_batch_documents_doc_id ON batch_documents(doc_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_task_status_doc_id ON task_status(doc_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_task_status_status ON task_status(status)')
        
        self.conn.commit()
    
    def save_document(self, doc_id: str, metadata: Dict[str, Any], user_id: str = "anonymous") -> str:
        """
        Save document metadata. Uses INSERT OR IGNORE + UPDATE to preserve created_at 
        on re-saves, and only overwrites dashboard_data when explicitly provided.
        """
        if not doc_id:
            doc_id = str(uuid.uuid4())
        
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.cursor()
        dashboard_data = metadata.get('dashboard_data')
        dashboard_json = json.dumps(dashboard_data) if dashboard_data else None
        status = metadata.get('status', 'processing')
        
        # Insert if new (preserves created_at for existing docs)
        cur.execute('''
            INSERT OR IGNORE INTO documents (id, user_id, metadata, dashboard_data, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (doc_id, user_id, json.dumps(metadata), dashboard_json, status, now, now))
        
        # Update existing — only overwrite dashboard_data when explicitly provided
        if dashboard_json is not None:
            cur.execute('''
                UPDATE documents 
                SET metadata = ?, dashboard_data = ?, status = ?, updated_at = ?, user_id = ?
                WHERE id = ?
            ''', (json.dumps(metadata), dashboard_json, status, now, user_id, doc_id))
        else:
            cur.execute('''
                UPDATE documents 
                SET metadata = ?, status = ?, updated_at = ?, user_id = ?
                WHERE id = ?
            ''', (json.dumps(metadata), status, now, user_id, doc_id))
        
        self.conn.commit()
        return doc_id
    
    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """
        Partially update a document without overwriting other fields.
        
        Args:
            doc_id: Document ID
            updates: Fields to update. Supported: 'status', 'dashboard_data', 'metadata'
            
        Returns:
            True if document was found and updated
        """
        cur = self.conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        set_clauses = ["updated_at = ?"]
        params = [now]
        
        if 'status' in updates:
            set_clauses.append("status = ?")
            params.append(updates['status'])
        
        if 'dashboard_data' in updates:
            set_clauses.append("dashboard_data = ?")
            params.append(json.dumps(updates['dashboard_data']) if updates['dashboard_data'] else None)
        
        if 'metadata' in updates:
            set_clauses.append("metadata = ?")
            params.append(json.dumps(updates['metadata']))
        
        params.append(doc_id)
        cur.execute(f'''
            UPDATE documents SET {", ".join(set_clauses)} WHERE id = ?
        ''', params)
        self.conn.commit()
        return cur.rowcount > 0
    
    def save_chunk(self, chunk_id: str, doc_id: str, text: str, metadata: Dict[str, Any] = None) -> str:
        """
        Save document chunk
        """
        if not chunk_id:
            chunk_id = str(uuid.uuid4())
        
        cur = self.conn.cursor()
        cur.execute('''
            INSERT OR REPLACE INTO chunks (id, doc_id, chunk_text, chunk_index, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            chunk_id,
            doc_id,
            text,
            metadata.get('index', 0) if metadata else 0,
            json.dumps(metadata or {}),
            datetime.now(timezone.utc).isoformat()
        ))
        self.conn.commit()
        return chunk_id
    
    def save_batch(self, batch_id: str, total_files: int, metadata: Dict[str, Any] = None, user_id: str = "anonymous") -> str:
        """
        Create a new batch record
        
        Args:
            batch_id: Batch ID
            total_files: Total number of files in batch
            metadata: Batch metadata
            user_id: User ID
            
        Returns:
            Batch ID
        """
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO batches (id, user_id, total_files, completed_files, failed_files, status, metadata, created_at, updated_at)
            VALUES (?, ?, ?, 0, 0, 'processing', ?, ?, ?)
        ''', (
            batch_id,
            user_id,
            total_files,
            json.dumps(metadata or {}),
            datetime.now(timezone.utc).isoformat(),
            datetime.now(timezone.utc).isoformat()
        ))
        self.conn.commit()
        return batch_id
    
    def save_batch_document(self, batch_id: str, doc_id: str, task_id: str, file_name: str) -> str:
        """
        Link a document to a batch
        
        Args:
            batch_id: Batch ID
            doc_id: Document ID
            task_id: Task ID
            file_name: Original file name
            
        Returns:
            Mapping ID
        """
        mapping_id = str(uuid.uuid4())
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO batch_documents (id, batch_id, doc_id, task_id, file_name, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'queued', ?)
        ''', (
            mapping_id,
            batch_id,
            doc_id,
            task_id,
            file_name,
            datetime.now(timezone.utc).isoformat()
        ))
        self.conn.commit()
        return mapping_id
    
    def update_batch_document_status(self, doc_id: str, status: str, error: str = None):
        """
        Update status of a document within a batch
        
        Args:
            doc_id: Document ID
            status: New status (processing, completed, failed)
            error: Error message if failed
        """
        cur = self.conn.cursor()
        cur.execute('''
            UPDATE batch_documents
            SET status = ?, error = ?
            WHERE doc_id = ?
        ''', (status, error, doc_id))
        
        # Update batch aggregates
        cur.execute('''
            UPDATE batches
            SET completed_files = (
                    SELECT COUNT(*) FROM batch_documents 
                    WHERE batch_id = batches.id AND status = 'completed'
                ),
                failed_files = (
                    SELECT COUNT(*) FROM batch_documents 
                    WHERE batch_id = batches.id AND status = 'failed'
                ),
                status = CASE
                    WHEN (SELECT COUNT(*) FROM batch_documents WHERE batch_id = batches.id AND status IN ('completed', 'failed')) = total_files
                    THEN 'completed'
                    ELSE 'processing'
                END,
                updated_at = ?
            WHERE id IN (SELECT batch_id FROM batch_documents WHERE doc_id = ?)
        ''', (datetime.now(timezone.utc).isoformat(), doc_id))
        
        self.conn.commit()
    
    def get_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get batch details including all documents
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Batch details with documents list
        """
        cur = self.conn.cursor()
        
        # Get batch info
        cur.execute('SELECT * FROM batches WHERE id = ?', (batch_id,))
        batch_row = cur.fetchone()
        if not batch_row:
            return None
        
        batch = dict(batch_row)
        batch['metadata'] = json.loads(batch['metadata']) if batch.get('metadata') else {}
        
        # Get all documents in batch
        cur.execute('''
            SELECT bd.*, d.metadata as doc_metadata
            FROM batch_documents bd
            LEFT JOIN documents d ON bd.doc_id = d.id
            WHERE bd.batch_id = ?
            ORDER BY bd.created_at
        ''', (batch_id,))
        
        documents = []
        for row in cur.fetchall():
            doc = dict(row)
            doc['doc_metadata'] = json.loads(doc['doc_metadata']) if doc.get('doc_metadata') else {}
            documents.append(doc)
        
        batch['documents'] = documents
        batch['progress'] = round((batch['completed_files'] + batch['failed_files']) / batch['total_files'] * 100, 1) if batch['total_files'] > 0 else 0
        
        return batch
    
    def save_task_status(self, task_id: str, doc_id: str, status: str = 'queued', 
                        stage: str = None, progress: int = 0, error: str = None, 
                        result: Any = None) -> None:
        """
        Save or update task status
        
        Args:
            task_id: Celery task ID
            doc_id: Document ID
            status: Task status (queued, processing, completed, failed)
            stage: Current processing stage
            progress: Progress percentage (0-100)
            error: Error message if failed
            result: Task result data
        """
        cur = self.conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        result_json = json.dumps(result) if result else None
        
        cur.execute('''
            INSERT OR REPLACE INTO task_status 
            (task_id, doc_id, status, stage, progress, error, result, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM task_status WHERE task_id = ?), ?),
                    ?)
        ''', (task_id, doc_id, status, stage, progress, error, result_json, task_id, now, now))
        
        self.conn.commit()
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status by task ID
        
        Args:
            task_id: Celery task ID
            
        Returns:
            Task status dictionary
        """
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM task_status WHERE task_id = ?', (task_id,))
        row = cur.fetchone()
        if not row:
            return None
        
        task = dict(row)
        task['result'] = json.loads(task['result']) if task.get('result') else None
        return task
    
    def update_task_progress(self, task_id: str, stage: str, progress: int) -> None:
        """
        Update task progress
        
        Args:
            task_id: Celery task ID
            stage: Current processing stage
            progress: Progress percentage (0-100)
        """
        cur = self.conn.cursor()
        cur.execute('''
            UPDATE task_status
            SET stage = ?, progress = ?, updated_at = ?
            WHERE task_id = ?
        ''', (stage, progress, datetime.now(timezone.utc).isoformat(), task_id))
        self.conn.commit()
    
    def save_edges(self, edge_id: str, doc_id: str, edge: Dict[str, Any]) -> str:
        """
        Save knowledge graph edge
        
        Args:
            edge_id: Edge ID (generated if not provided)
            doc_id: Document ID
            edge: Edge data
            
        Returns:
            Edge ID
        """
        if not edge_id:
            edge_id = str(uuid.uuid4())
        
        cur = self.conn.cursor()
        cur.execute('''
            INSERT OR REPLACE INTO graph_edges (id, doc_id, edge, created_at)
            VALUES (?, ?, ?, ?)
        ''', (
            edge_id,
            doc_id,
            json.dumps(edge),
            datetime.now(timezone.utc).isoformat()
        ))
        self.conn.commit()
        return edge_id
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
        row = cur.fetchone()
        if row:
            doc = dict(row)
            doc['metadata'] = json.loads(doc['metadata']) if doc.get('metadata') else {}
            if doc.get('dashboard_data'):
                try:
                    doc['dashboard_data'] = json.loads(doc['dashboard_data'])
                except:
                    doc['dashboard_data'] = None
            return doc
        return None
    
    def get_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a document"""
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_index', (doc_id,))
        rows = cur.fetchall()
        chunks = []
        for row in rows:
            chunk = dict(row)
            chunk['metadata'] = json.loads(chunk['metadata'])
            chunks.append(chunk)
        return chunks
    
    def get_edges(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all edges for a document"""
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM graph_edges WHERE doc_id = ?', (doc_id,))
        rows = cur.fetchall()
        edges = []
        for row in rows:
            edge = dict(row)
            edge['edge'] = json.loads(edge['edge'])
            edges.append(edge)
        return edges
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete document and all related data"""
        cur = self.conn.cursor()
        cur.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
        self.conn.commit()
        return cur.rowcount > 0
    
    def list_documents(self, user_id: str = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List documents"""
        cur = self.conn.cursor()
        if user_id:
            cur.execute('''
                SELECT * FROM documents 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
        else:
            cur.execute('''
                SELECT * FROM documents 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        
        rows = cur.fetchall()
        documents = []
        for row in rows:
            doc = dict(row)
            doc['metadata'] = json.loads(doc['metadata'])
            if doc.get('dashboard_data'):
                try:
                    doc['dashboard_data'] = json.loads(doc['dashboard_data'])
                except Exception:
                    doc['dashboard_data'] = None
            documents.append(doc)
        return documents

