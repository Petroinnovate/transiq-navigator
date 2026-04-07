"""
SQLAlchemy ORM Models for TransIQ
Multi-tenant architecture with user isolation
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import uuid

from services.db.session import Base


def generate_uuid():
    """Generate UUID string"""
    return str(uuid.uuid4())


class User(Base):
    """User model for authentication and multi-tenancy"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Integer, default=1)  # 1=active, 0=disabled
    is_admin = Column(Integer, default=0)  # 0=user, 1=admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("TaskStatus", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Document(Base):
    """Document model with user ownership"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String)
    doc_metadata = Column(JSON)  # Renamed from 'metadata' (reserved by SQLAlchemy)
    dashboard_data = Column(JSON)  # Stores dashboard JSON
    status = Column(String, default="processing", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    graph_edges = relationship("GraphEdge", back_populates="document", cascade="all, delete-orphan")
    batch_documents = relationship("BatchDocument", back_populates="document")
    tasks = relationship("TaskStatus", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_documents_user_status', 'user_id', 'status'),
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, user_id={self.user_id}, filename={self.filename})>"


class Chunk(Base):
    """Text chunk model for RAG retrieval"""
    __tablename__ = "chunks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    doc_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer)
    chunk_metadata = Column(JSON)  # Renamed from 'metadata' (reserved by SQLAlchemy)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<Chunk(id={self.id}, doc_id={self.doc_id}, index={self.chunk_index})>"


class GraphEdge(Base):
    """Knowledge graph edge model"""
    __tablename__ = "graph_edges"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    doc_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    edge = Column(Text)  # Stores edge relationship (e.g., "entity1 -> relation -> entity2")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="graph_edges")
    
    def __repr__(self):
        return f"<GraphEdge(id={self.id}, doc_id={self.doc_id})>"


class Batch(Base):
    """Batch upload model with user ownership"""
    __tablename__ = "batches"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    total_files = Column(Integer, nullable=False)
    completed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    status = Column(String, default="processing", index=True)
    batch_metadata = Column(JSON)  # Renamed from 'metadata' (reserved by SQLAlchemy)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="batches")
    batch_documents = relationship("BatchDocument", back_populates="batch", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_batches_user_status', 'user_id', 'status'),
    )
    
    def __repr__(self):
        return f"<Batch(id={self.id}, user_id={self.user_id}, total_files={self.total_files})>"


class BatchDocument(Base):
    """Batch document mapping model"""
    __tablename__ = "batch_documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    batch_id = Column(String, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String)
    file_name = Column(String)
    status = Column(String, default="queued")
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    batch = relationship("Batch", back_populates="batch_documents")
    document = relationship("Document", back_populates="batch_documents")
    
    def __repr__(self):
        return f"<BatchDocument(id={self.id}, batch_id={self.batch_id}, doc_id={self.doc_id})>"


class TaskStatus(Base):
    """Celery task status tracking with user ownership"""
    __tablename__ = "task_status"
    
    task_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default="queued", index=True)
    stage = Column(String)
    progress = Column(Integer, default=0)
    error = Column(Text)
    result = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    document = relationship("Document", back_populates="tasks")
    
    __table_args__ = (
        Index('idx_task_status_user_status', 'user_id', 'status'),
        Index('idx_task_status_doc_status', 'doc_id', 'status'),
    )
    
    def __repr__(self):
        return f"<TaskStatus(task_id={self.task_id}, user_id={self.user_id}, status={self.status})>"


class PromptExecution(Base):
    """Prompt execution tracking for performance analysis and A/B testing"""
    __tablename__ = "prompt_executions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    prompt_name = Column(String(100), nullable=False, index=True)
    prompt_version = Column(String(50), nullable=False)
    doc_id = Column(String(36), index=True)
    user_id = Column(String(36), index=True)
    
    # Execution metrics
    latency_ms = Column(Integer, nullable=False)
    tokens_used = Column(Integer)
    cost = Column(Integer)  # Cost in cents (to avoid float precision issues)
    
    # Result metrics
    kpi_count = Column(Integer)
    chart_count = Column(Integer)
    success = Column(Integer, default=1)  # 1=success, 0=failure
    error_message = Column(String(500))
    
    # Metadata
    exec_metadata = Column(JSON)  # Additional metrics (quality scores, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_prompt_perf', 'prompt_name', 'prompt_version', 'created_at'),
        Index('idx_prompt_user', 'prompt_name', 'user_id'),
    )
    
    def __repr__(self):
        return f"<PromptExecution(id={self.id}, prompt={self.prompt_name}:{self.prompt_version}, success={self.success})>"


# ============================================================================
# GraphRAG Models - Knowledge Graph Storage
# ============================================================================

class GraphEntity(Base):
    """Canonical entity model for knowledge graph"""
    __tablename__ = "graph_entities"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    canonical_name = Column(String, nullable=False, index=True, unique=True)
    entity_type = Column(String, nullable=False, index=True)  # PERSON, ORG, LOCATION, CONCEPT, etc.
    aliases = Column(JSON, default=[])  # List of alternative names for this entity
    first_doc_id = Column(String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    
    # Statistics
    mention_count = Column(Integer, default=1)  # How many times mentioned across all documents
    total_confidence = Column(Integer, default=0)  # Sum of confidence scores (stored as integer 0-100)
    properties = Column(JSON, default={})  # Additional attributes {key: value, ...}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    first_document = relationship("Document", foreign_keys=[first_doc_id])
    mentions = relationship("GraphEntityMention", back_populates="entity", cascade="all, delete-orphan")
    outgoing_relationships = relationship(
        "GraphRelationship",
        foreign_keys="GraphRelationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan"
    )
    incoming_relationships = relationship(
        "GraphRelationship",
        foreign_keys="GraphRelationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_entity_canonical', 'canonical_name'),
        Index('idx_entity_type', 'entity_type'),
        Index('idx_entity_mention_count', 'mention_count'),
    )
    
    def __repr__(self):
        return f"<GraphEntity(id={self.id}, name={self.canonical_name}, type={self.entity_type})>"


class GraphRelationship(Base):
    """Relationship between entities in knowledge graph"""
    __tablename__ = "graph_relationships"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    source_entity_id = Column(String, ForeignKey("graph_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_id = Column(String, ForeignKey("graph_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String, nullable=False, index=True)  # OWNS, WORKS_FOR, LOCATED_IN, etc.
    
    # Confidence and tracking
    confidence = Column(Integer, default=50)  # 0-100 scale
    mention_count = Column(Integer, default=1)  # How many fact triples created this relationship
    total_documents = Column(Integer, default=1)  # How many documents contain this relationship
    is_bidirectional = Column(Integer, default=0)  # Can traverse both directions
    
    # Additional context
    properties = Column(JSON, default={})  # Additional context/attributes
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    source_entity = relationship(
        "GraphEntity",
        foreign_keys=[source_entity_id],
        back_populates="outgoing_relationships"
    )
    target_entity = relationship(
        "GraphEntity",
        foreign_keys=[target_entity_id],
        back_populates="incoming_relationships"
    )
    mentions = relationship("GraphRelationshipMention", back_populates="graph_relationship", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_rel_source', 'source_entity_id'),
        Index('idx_rel_target', 'target_entity_id'),
        Index('idx_rel_type', 'relationship_type'),
        Index('idx_rel_source_target', 'source_entity_id', 'target_entity_id'),
    )
    
    def __repr__(self):
        return f"<GraphRelationship(id={self.id}, {self.source_entity_id} --[{self.relationship_type}]--> {self.target_entity_id})>"


class GraphEntityMention(Base):
    """Track where entities are mentioned in documents"""
    __tablename__ = "graph_entity_mentions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    entity_id = Column(String, ForeignKey("graph_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String, ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Mention details
    mention_text = Column(String, nullable=False)  # Exact text from document
    position = Column(Integer)  # Character position in chunk
    confidence = Column(Integer, default=50)  # Extraction confidence (0-100)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    entity = relationship("GraphEntity", back_populates="mentions")
    document = relationship("Document", foreign_keys=[doc_id])
    chunk = relationship("Chunk", foreign_keys=[chunk_id])
    
    __table_args__ = (
        Index('idx_mention_entity', 'entity_id'),
        Index('idx_mention_doc', 'doc_id'),
        Index('idx_mention_chunk', 'chunk_id'),
    )
    
    def __repr__(self):
        return f"<GraphEntityMention(entity={self.entity_id}, doc={self.doc_id}, text={self.mention_text[:30]})>"


class GraphRelationshipMention(Base):
    """Track where relationships are mentioned in documents"""
    __tablename__ = "graph_relationship_mentions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    relationship_id = Column(String, ForeignKey("graph_relationships.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String, ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Mention details
    mention_text = Column(Text)  # Context where relationship was found
    confidence = Column(Integer, default=50)  # Extraction confidence (0-100)
    source_fact = Column(JSON)  # Original fact that created this relationship
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    graph_relationship = relationship("GraphRelationship", back_populates="mentions")
    document = relationship("Document", foreign_keys=[doc_id])
    chunk = relationship("Chunk", foreign_keys=[chunk_id])
    
    __table_args__ = (
        Index('idx_rel_mention_rel', 'relationship_id'),
        Index('idx_rel_mention_doc', 'doc_id'),
    )
    
    def __repr__(self):
        return f"<GraphRelationshipMention(rel={self.relationship_id}, doc={self.doc_id})>"


class GraphPath(Base):
    """Cached path query results for fast retrieval"""
    __tablename__ = "graph_paths"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    source_entity_id = Column(String, ForeignKey("graph_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_id = Column(String, ForeignKey("graph_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Path details
    path_data = Column(JSON)  # {edges: [...], entities: [...], relationships: [...]}
    path_length = Column(Integer)  # Number of hops/relationships
    relevance_score = Column(Integer, default=50)  # Quality metric (0-100)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))  # Cache TTL
    
    __table_args__ = (
        Index('idx_path_source_target', 'source_entity_id', 'target_entity_id'),
        Index('idx_path_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<GraphPath(id={self.id}, {self.source_entity_id} → {self.target_entity_id}, length={self.path_length})>"


# ============================================================================
# Six Sigma Analysis Persistence
# ============================================================================

class SavedAnalysis(Base):
    """Persisted Six Sigma analysis (moved from domain for purity)."""

    __tablename__ = "saved_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    api_key_hash = Column(String(16), nullable=True, index=True)
    analysis_type = Column(String(50), default="process_capability", nullable=False)
    inputs = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=False)
    chart_data = Column(JSON, nullable=False)
    warnings = Column(JSON, nullable=False, default=list)
    recommendations = Column(JSON, nullable=False, default=list)
