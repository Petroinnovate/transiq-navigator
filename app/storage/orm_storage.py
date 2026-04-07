"""
ORM-based storage layer using SQLAlchemy
Multi-tenant with user isolation
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json

from app.db.models import User, Document, Chunk, GraphEdge, Batch, BatchDocument, TaskStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ORMStorage:
    """
    SQLAlchemy ORM storage layer with multi-tenant support
    
    All methods require user_id for data isolation (except admin operations)
    """
    
    def __init__(self, db: Session):
        """Initialize with database session"""
        self.db = db
    
    # ========================================================================
    # Document operations
    # ========================================================================
    
    def save_document(
        self, 
        doc_id: str, 
        user_id: str, 
        metadata: Dict[str, Any],
        filename: Optional[str] = None
    ) -> Document:
        """
        Save document metadata
        
        Args:
            doc_id: Document ID
            user_id: User ID (for multi-tenancy)
            metadata: Document metadata dict
            filename: Original filename
        
        Returns:
            Document ORM object
        """
        # Check if document exists
        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        
        if doc:
            # Update existing
            doc.metadata = metadata
            doc.filename = filename or doc.filename
            doc.updated_at = datetime.now(timezone.utc)
        else:
            # Create new
            doc = Document(
                id=doc_id,
                user_id=user_id,
                metadata=metadata,
                filename=filename,
                status="processing"
            )
            self.db.add(doc)
        
        self.db.commit()
        self.db.refresh(doc)
        
        logger.info(f"Document saved: {doc_id} (user: {user_id})")
        return doc
    
    def get_document(self, doc_id: str, user_id: str) -> Optional[Document]:
        """
        Get document by ID (with user isolation)
        
        Args:
            doc_id: Document ID
            user_id: User ID (ensures user owns this document)
        
        Returns:
            Document object or None
        """
        return self.db.query(Document).filter(
            Document.id == doc_id,
            Document.user_id == user_id
        ).first()
    
    def get_user_documents(
        self, 
        user_id: str, 
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Document]:
        """
        Get all documents for a user
        
        Args:
            user_id: User ID
            status: Optional status filter
            limit: Max number of documents
        
        Returns:
            List of Document objects
        """
        query = self.db.query(Document).filter(Document.user_id == user_id)
        
        if status:
            query = query.filter(Document.status == status)
        
        return query.order_by(Document.created_at.desc()).limit(limit).all()
    
    def update_document_status(self, doc_id: str, user_id: str, status: str):
        """Update document status"""
        doc = self.get_document(doc_id, user_id)
        if doc:
            doc.status = status
            doc.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            logger.info(f"Document {doc_id} status updated to: {status}")
    
    def save_dashboard(self, doc_id: str, user_id: str, dashboard_data: Dict[str, Any]):
        """
        Save dashboard data to document
        
        Args:
            doc_id: Document ID
            user_id: User ID (for access control)
            dashboard_data: Dashboard JSON data
        """
        doc = self.get_document(doc_id, user_id)
        if doc:
            doc.dashboard_data = dashboard_data
            doc.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            logger.info(f"Dashboard saved for document: {doc_id}")
    
    def get_dashboard(self, doc_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get dashboard data"""
        doc = self.get_document(doc_id, user_id)
        return doc.dashboard_data if doc else None
    
    # ========================================================================
    # Chunk operations
    # ========================================================================
    
    def save_chunks(self, chunks: List[Dict[str, Any]], user_id: str):
        """
        Save multiple chunks (with user validation)
        
        Args:
            chunks: List of chunk dicts with keys: id, doc_id, chunk_text, chunk_index, metadata
            user_id: User ID (validates document ownership)
        """
        for chunk_data in chunks:
            doc_id = chunk_data["doc_id"]
            
            # Validate user owns this document
            doc = self.get_document(doc_id, user_id)
            if not doc:
                logger.warning(f"User {user_id} attempted to save chunk for doc {doc_id} (not owned)")
                continue
            
            chunk = Chunk(
                id=chunk_data["id"],
                doc_id=doc_id,
                chunk_text=chunk_data["chunk_text"],
                chunk_index=chunk_data.get("chunk_index"),
                metadata=chunk_data.get("metadata")
            )
            self.db.add(chunk)
        
        self.db.commit()
        logger.info(f"Saved {len(chunks)} chunks")
    
    def get_chunks(self, doc_id: str, user_id: str, limit: Optional[int] = None) -> List[Chunk]:
        """Get chunks for a document (with user validation)"""
        # Validate user owns document
        doc = self.get_document(doc_id, user_id)
        if not doc:
            return []
        
        query = self.db.query(Chunk).filter(Chunk.doc_id == doc_id)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    # ========================================================================
    # Task status operations
    # ========================================================================
    
    def save_task_status(
        self,
        task_id: str,
        doc_id: str,
        user_id: str,
        status: str = "queued",
        stage: Optional[str] = None,
        progress: int = 0
    ):
        """Save task status"""
        # Validate document ownership
        doc = self.get_document(doc_id, user_id)
        if not doc:
            logger.error(f"Cannot save task {task_id}: user {user_id} does not own doc {doc_id}")
            return
        
        task = self.db.query(TaskStatus).filter(TaskStatus.task_id == task_id).first()
        
        if task:
            task.status = status
            task.stage = stage
            task.progress = progress
            task.updated_at = datetime.now(timezone.utc)
        else:
            task = TaskStatus(
                task_id=task_id,
                doc_id=doc_id,
                user_id=user_id,
                status=status,
                stage=stage,
                progress=progress
            )
            self.db.add(task)
        
        self.db.commit()
    
    def get_task_status(self, task_id: str, user_id: str) -> Optional[TaskStatus]:
        """Get task status (with user validation)"""
        return self.db.query(TaskStatus).filter(
            TaskStatus.task_id == task_id,
            TaskStatus.user_id == user_id
        ).first()
    
    def update_task_progress(
        self,
        task_id: str,
        user_id: str,
        stage: str,
        progress: int,
        status: Optional[str] = None
    ):
        """Update task progress"""
        task = self.get_task_status(task_id, user_id)
        if task:
            task.stage = stage
            task.progress = progress
            if status:
                task.status = status
            task.updated_at = datetime.now(timezone.utc)
            self.db.commit()
    
    # ========================================================================
    # Batch operations
    # ========================================================================
    
    def create_batch(
        self,
        batch_id: str,
        user_id: str,
        total_files: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Batch:
        """Create batch for multi-file upload"""
        batch = Batch(
            id=batch_id,
            user_id=user_id,
            total_files=total_files,
            completed_files=0,
            failed_files=0,
            status="processing",
            metadata=metadata
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        
        logger.info(f"Batch created: {batch_id} (user: {user_id}, files: {total_files})")
        return batch
    
    def get_batch(self, batch_id: str, user_id: str) -> Optional[Batch]:
        """Get batch (with user validation)"""
        return self.db.query(Batch).filter(
            Batch.id == batch_id,
            Batch.user_id == user_id
        ).first()
    
    def update_batch_progress(
        self,
        batch_id: str,
        user_id: str,
        completed: int,
        failed: int,
        status: Optional[str] = None
    ):
        """Update batch progress"""
        batch = self.get_batch(batch_id, user_id)
        if batch:
            batch.completed_files = completed
            batch.failed_files = failed
            if status:
                batch.status = status
            batch.updated_at = datetime.now(timezone.utc)
            self.db.commit()
    
    # ========================================================================
    # Graph operations
    # ========================================================================
    
    def save_graph_edges(self, doc_id: str, user_id: str, edges: List[str]):
        """Save knowledge graph edges"""
        # Validate document ownership
        doc = self.get_document(doc_id, user_id)
        if not doc:
            logger.warning(f"User {user_id} attempted to save graph edges for doc {doc_id} (not owned)")
            return
        
        for edge in edges:
            graph_edge = GraphEdge(doc_id=doc_id, edge=edge)
            self.db.add(graph_edge)
        
        self.db.commit()
        logger.info(f"Saved {len(edges)} graph edges for doc {doc_id}")
    
    def get_graph_edges(self, doc_id: str, user_id: str) -> List[str]:
        """Get graph edges"""
        # Validate document ownership
        doc = self.get_document(doc_id, user_id)
        if not doc:
            return []
        
        edges = self.db.query(GraphEdge).filter(GraphEdge.doc_id == doc_id).all()
        return [e.edge for e in edges]
