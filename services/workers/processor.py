"""
Celery worker for document processing
Integrates ChunkingPipeline for advanced document chunking and embedding
"""
import os
import json
import traceback
from datetime import datetime, timezone
try:
    from celery import Celery
    import redis
    CELERY_AVAILABLE = True
    REDIS_AVAILABLE = True
except ImportError as e:
    CELERY_AVAILABLE = False
    REDIS_AVAILABLE = False
    Celery = None
    redis = None
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)

# Initialize Redis client for Pub/Sub (separate from Celery broker)
redis_client = None
if REDIS_AVAILABLE:
    try:
        redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
        logger.info("Redis Pub/Sub client initialized") 
    except Exception as e:
        logger.warning(f"Redis Pub/Sub not available: {e}")
        redis_client = None

# Initialize Celery only if available
if CELERY_AVAILABLE:
    celery = Celery(
        'transiq_workers',
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND
    )

    # Celery configuration
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 minutes
        task_soft_time_limit=240,  # 4 minutes
        broker_connection_retry=False,  # Don't retry broker connection on startup
        broker_connection_max_retries=2,  # Max 2 retries
        broker_connection_retry_on_startup=False,  # Fail fast on startup
        result_backend_transport_options={
            'master_name': 'mymaster',
            'socket_keepalive': True,
            'socket_connect_timeout': 0.5,
            'retry_on_timeout': True,
            'max_connections': 2,
        },
    )
else:
    celery = None
    logger.warning("Celery not available - will use synchronous processing")


def _publish_progress(doc_id: str, stage: str, progress: int, message: str, metadata: dict = None):
    """
    Publish progress event to Redis Pub/Sub channel
    
    Args:
        doc_id: Document ID
        stage: Current processing stage
        progress: Progress percentage (0-100)
        message: Status message
        metadata: Optional additional metadata
    """
    if not redis_client:
        return
    
    try:
        event = {
            "doc_id": doc_id,
            "stage": stage,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            event.update(metadata)
        
        channel = f"doc:{doc_id}"
        redis_client.publish(channel, json.dumps(event))
        logger.debug(f"Published progress to {channel}: {stage} ({progress}%)")
    except Exception as e:
        logger.warning(f"Failed to publish progress event: {e}")


# ============================================================================
# Celery Task: True Distributed Processing
# ============================================================================

if CELERY_AVAILABLE:
    @celery.task(bind=True, max_retries=3, default_retry_delay=60)
    def process_document(
        self,
        doc_path: str,
        doc_id: str,
        provider_name: str = None,
        enable_deduction: bool = False,
        enable_patterns: bool = False
    ):
        """
        Celery task for distributed document processing with Redis Pub/Sub progress streaming
        
        Args:
            self: Celery task instance (bind=True)
            doc_path: Path to document file
            doc_id: Document ID
            provider_name: LLM provider name
            enable_deduction: Enable deduction engine
            enable_patterns: Enable pattern recognition
            
        Returns:
            Processing result dictionary
        """
        from services.storage.local import LocalStorage
        from services.file_reader import read_file_content, get_file_chunks_for_dashboard
        
        task_id = self.request.id
        storage = LocalStorage()
        
        try:
            # Save initial task status
            storage.save_task_status(task_id, doc_id, status='processing', stage='started', progress=0)
            _publish_progress(doc_id, 'started', 0, 'Task started')
            
            # Stage 1: Reading file (10%)
            logger.info(f"[Task {task_id}] Reading file: {doc_path}")
            _publish_progress(doc_id, 'reading_file', 10, 'Reading document')
            storage.update_task_progress(task_id, 'reading_file', 10)
            
            text = read_file_content(doc_path)
            file_name = os.path.basename(doc_path)
            
            # Hard cap text size
            MAX_TEXT_CHARS = 600_000
            if len(text) > MAX_TEXT_CHARS:
                logger.warning(f"Document too large ({len(text):,} chars), truncating")
                text = text[:MAX_TEXT_CHARS]
            
            # Stage 2: Chunking (20%)
            logger.info(f"[Task {task_id}] Initializing chunking pipeline")
            _publish_progress(doc_id, 'chunking', 20, 'Breaking document into chunks')
            storage.update_task_progress(task_id, 'chunking', 20)
            
            # Use ChunkingPipeline for advanced chunking
            from pipelines.processing.pipeline import ChunkingPipeline
            pipeline = ChunkingPipeline(
                strategy='adaptive',  # Use adaptive strategy by default
                max_embed_chunks=400,
                enable_metrics=True
            )
            
            # Execute pipeline: chunk -> embed -> index -> save
            logger.info(f"[Task {task_id}] Executing chunking pipeline")
            pipeline_result = pipeline.process(
                text=text,
                doc_id=doc_id,
                doc_path=doc_path,
                storage=storage,
                enable_caching=True
            )
            
            # Extract results
            chunks_data = pipeline_result['chunks_data']
            chunks = [c['text'] for c in chunks_data]
            chunk_count = pipeline_result['chunks_count']
            embedding_count = pipeline_result['embeddings_count']
            metrics = pipeline_result.get('metrics', {})
            
            # Stage 6: Dashboard generation (75%)
            logger.info(f"[Task {task_id}] Generating dashboard")
            _publish_progress(doc_id, 'generating_dashboard', 75, 'Generating AI dashboard')
            storage.update_task_progress(task_id, 'generating_dashboard', 75)
            
            dashboard_data = None
            try:
                from pipelines.processing.dashboard import DashboardGenerator
                file_chunks = get_file_chunks_for_dashboard(doc_path)
                dashboard_gen = DashboardGenerator(provider_name=provider_name)
                dashboard_result = dashboard_gen.generate_dashboard(file_chunks, file_name)
                dashboard_data = dashboard_result.get("dashboard")
                logger.info(f"[Task {task_id}] Dashboard generated successfully")
            except Exception as dash_err:
                logger.error(f"[Task {task_id}] Dashboard generation failed: {dash_err}")
            
            # Stage 7: KPI scoring (85%)
            if dashboard_data:
                logger.info(f"[Task {task_id}] Running KPI engine")
                _publish_progress(doc_id, 'kpi_scoring', 85, 'Scoring KPIs with AI')
                storage.update_task_progress(task_id, 'kpi_scoring', 85)
            
            # Stage 8: Predictive analysis (95%)
            if dashboard_data:
                logger.info(f"[Task {task_id}] Running predictive engine")
                _publish_progress(doc_id, 'predictive_analysis', 95, 'Generating forecasts')
                storage.update_task_progress(task_id, 'predictive_analysis', 95)
            
            # Final: Save document metadata
            doc_metadata = {
                "status": "completed",
                "chunks_count": chunk_count,
                "embeddings_count": embedding_count,
                "file_name": file_name,
                "pipeline_metrics": metrics
            }
            if dashboard_data:
                doc_metadata["dashboard_data"] = dashboard_data
            
            storage.save_document(doc_id, doc_metadata)
            
            # Update batch status if part of batch
            try:
                storage.update_batch_document_status(doc_id, "completed")
            except:
                pass
            
            # Mark task completed (100%)
            result = {
                "status": "completed",
                "doc_id": doc_id,
                "chunks": chunk_count,
                "embeddings": embedding_count,
                "has_dashboard": dashboard_data is not None,
                "metrics": metrics
            }
            storage.save_task_status(task_id, doc_id, status='completed', stage='completed', 
                                    progress=100, result=result)
            _publish_progress(doc_id, 'completed', 100, 'Processing complete', {"result": result})
            
            logger.info(f"[Task {task_id}] Document {doc_id} processed successfully")
            return result
            
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            logger.error(f"[Task {task_id}] Processing failed: {error_msg}")
            logger.error(f"Traceback: {error_trace}")
            
            # Save failure status
            try:
                storage.save_document(doc_id, {"status": "failed", "error": error_msg})
                storage.save_task_status(task_id, doc_id, status='failed', error=error_msg)
                storage.update_batch_document_status(doc_id, "failed", error_msg)
                _publish_progress(doc_id, 'failed', 0, f'Processing failed: {error_msg}')
            except Exception as save_err:
                logger.error(f"Failed to save error status: {save_err}")
            
            # Retry logic
            if self.request.retries < self.max_retries:
                logger.info(f"[Task {task_id}] Retrying (attempt {self.request.retries + 1}/{self.max_retries})")
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))  # Exponential backoff
            
            raise


def _process_document_impl(
    doc_path: str,
    doc_id: str,
    provider_name: str = None,
    enable_deduction: bool = False,
    enable_patterns: bool = False,
    progress_callback=None,
    chunking_strategy: str = "adaptive"
):
    """
    Core document processing implementation using ChunkingPipeline
    
    Args:
        doc_path: Path to document file
        doc_id: Document ID
        provider_name: LLM provider name
        enable_deduction: Enable deduction engine
        enable_patterns: Enable pattern recognition
        progress_callback: Optional callback for progress updates
        chunking_strategy: Chunking strategy to use ('adaptive', 'semantic', 'hierarchical')
        
    Returns:
        Processing result dictionary
    """
    try:
        from pipelines.processing.pipeline import ChunkingPipeline
        from pipelines.processing.deduction import DeductionEngine
        from pipelines.processing.patterns import PatternRecognizer
        from services.storage.local import LocalStorage
        from services.file_reader import read_file_content
        
        # Update progress
        if progress_callback:
            progress_callback('PROCESSING', {'step': 'initializing'})
        
        # Initialize components
        storage = LocalStorage()
        
        # Read file
        if progress_callback:
            progress_callback('PROCESSING', {'step': 'reading_file'})
        text = read_file_content(doc_path)
        
        # Initialize chunking pipeline
        if progress_callback:
            progress_callback('PROCESSING', {'step': 'chunking'})
        logger.info(f"Initializing ChunkingPipeline with strategy '{chunking_strategy}'")
        
        pipeline = ChunkingPipeline(
            strategy=chunking_strategy,
            max_embed_chunks=400,
            enable_metrics=True
        )
        
        # Execute pipeline
        logger.info(f"Executing chunking pipeline for document {doc_id}")
        pipeline_result = pipeline.process(
            text=text,
            doc_id=doc_id,
            doc_path=doc_path,
            storage=storage,
            enable_caching=True
        )
        
        # Extract results
        chunks_data = pipeline_result['chunks_data']
        chunk_count = pipeline_result['chunks_count']
        embedding_count = pipeline_result['embeddings_count']
        metrics = pipeline_result.get('metrics', {})
        
        logger.info(f"Pipeline complete: {chunk_count} chunks, {embedding_count} embeddings")
        
        # Deduction engine
        facts = []
        knowledge_graph = None
        graphrag_task_id = None
        if enable_deduction:
            try:
                if progress_callback:
                    progress_callback('PROCESSING', {'step': 'deduction'})
                ded = DeductionEngine(provider_name=provider_name)
                facts = ded.extract_facts(text)
                knowledge_graph = ded.build_knowledge_graph(facts)
                
                # Save edges to legacy storage
                for i, edge in enumerate(knowledge_graph.get('edges', [])):
                    edge_id = f"{doc_id}-e-{i}"
                    storage.save_edges(edge_id, doc_id, edge)
                
                # ============================================================
                # GraphRAG Integration
                # ============================================================
                # Publish facts to GraphRAG for advanced knowledge graph
                if facts and progress_callback:
                    progress_callback('PROCESSING', {'step': 'graphrag'})
                
                try:
                    graphrag_task_id = ded.publish_facts_to_graph(facts, doc_id)
                    logger.info(f"GraphRAG integration queued: task_id={graphrag_task_id}")
                except Exception as graphrag_error:
                    logger.warning(f"GraphRAG integration failed: {graphrag_error}")
                    # Don't fail the entire document processing if GraphRAG fails
                    
            except Exception as e:
                logger.error(f"Deduction engine error: {e}")
        
        # Pattern recognition
        patterns = None
        if enable_patterns:
            try:
                if progress_callback:
                    progress_callback('PROCESSING', {'step': 'patterns'})
                recognizer = PatternRecognizer()
                # Extract numeric data if available
                # This is simplified - in production, extract from structured data
                patterns = {"status": "completed", "note": "Pattern recognition requires structured data"}
            except Exception as e:
                logger.error(f"Pattern recognition error: {e}")
        
        # Update document status
        storage.save_document(doc_id, {
            "status": "completed",
            "chunks_count": chunk_count,
            "embeddings_count": embedding_count,
            "facts_count": len(facts),
            "has_knowledge_graph": knowledge_graph is not None,
            "graphrag_task_id": graphrag_task_id,
            "chunking_strategy": chunking_strategy,
            "pipeline_metrics": metrics
        })
        
        # Update batch status if this document is part of a batch
        try:
            storage.update_batch_document_status(doc_id, "completed")
        except Exception as batch_error:
            logger.warning(f"Failed to update batch status for doc {doc_id}: {batch_error}")
        
        result = {
            "status": "completed",
            "doc_id": doc_id,
            "chunks": chunk_count,
            "embeddings": embedding_count,
            "facts": len(facts),
            "has_knowledge_graph": knowledge_graph is not None,
            "graphrag_task_id": graphrag_task_id,
            "has_patterns": patterns is not None,
            "chunking_strategy": chunking_strategy,
            "metrics": metrics
        }
        
        logger.info(f"Document {doc_id} processed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Document processing error: {e}")
        # Update document status to failed
        try:
            from services.storage.local import LocalStorage
            storage = LocalStorage()
            storage.save_document(doc_id, {"status": "failed", "error": str(e)})
            # Update batch status if this document is part of a batch
            storage.update_batch_document_status(doc_id, "failed", str(e))
        except Exception as batch_error:
            logger.warning(f"Failed to update batch/document status: {batch_error}")
        
        raise


def process_document_sync(
    doc_path: str,
    doc_id: str,
    provider_name: str = None,
    enable_deduction: bool = False,
    enable_patterns: bool = False,
    chunking_strategy: str = "adaptive"
):
    """
    Process document synchronously using ChunkingPipeline
    This is used when Redis/Celery is not available
    
    Args:
        doc_path: Path to document file
        doc_id: Document ID
        provider_name: LLM provider name
        enable_deduction: Enable deduction engine
        enable_patterns: Enable pattern recognition
        chunking_strategy: Chunking strategy to use ('adaptive', 'semantic', 'hierarchical')
        
    Returns:
        Processing result dictionary
    """
    try:
        from pipelines.processing.pipeline import ChunkingPipeline
        from pipelines.processing.deduction import DeductionEngine
        from pipelines.processing.patterns import PatternRecognizer
        from services.storage.local import LocalStorage
        from services.file_reader import read_file_content, get_file_chunks_for_dashboard
        
        logger.info(f"Starting synchronous processing for document {doc_id} with strategy '{chunking_strategy}'")
        
        # Initialize components
        storage = LocalStorage()
        
        # Read file (handle different file types)
        logger.info(f"Reading file: {doc_path}")
        text = read_file_content(doc_path)
        file_name = os.path.basename(doc_path)

        # Hard cap text size to prevent MemoryError on huge PDFs
        MAX_TEXT_CHARS = 600_000  # ~120K words — enough for semantic search
        if len(text) > MAX_TEXT_CHARS:
            logger.warning(f"Document too large ({len(text):,} chars), truncating to {MAX_TEXT_CHARS:,} for indexing")
            text = text[:MAX_TEXT_CHARS]

        # Initialize and execute chunking pipeline
        logger.info(f"Initializing ChunkingPipeline with '{chunking_strategy}' strategy")
        pipeline = ChunkingPipeline(
            strategy=chunking_strategy,
            max_embed_chunks=400,  # Cap for embedding model
            enable_metrics=True    # Collect performance metrics
        )
        
        # Execute full pipeline: chunk -> embed -> index -> save
        logger.info(f"Executing chunk pipeline for document {doc_id}")
        pipeline_result = pipeline.process(
            text=text,
            doc_id=doc_id,
            doc_path=doc_path,
            storage=storage,
            enable_caching=True
        )
        
        # Extract results from pipeline
        chunks_data = pipeline_result['chunks_data']
        chunks_count = pipeline_result['chunks_count']
        embedding_count = pipeline_result['embeddings_count']
        metrics = pipeline_result.get('metrics', {})
        
        logger.info(f"Pipeline results: {chunks_count} chunks, {embedding_count} embeddings")
        logger.info(f"Pipeline metrics: {metrics}")
        
        # Run optional additional processors
        facts = []
        knowledge_graph = None
        if enable_deduction:
            try:
                logger.info("Running deduction engine")
                ded = DeductionEngine(provider_name=provider_name)
                facts = ded.extract_facts(text)
                knowledge_graph = ded.build_knowledge_graph(facts)
                
                # Save edges
                for i, edge in enumerate(knowledge_graph.get('edges', [])):
                    edge_id = f"{doc_id}-e-{i}"
                    storage.save_edges(edge_id, doc_id, edge)
            except Exception as e:
                logger.error(f"Deduction engine error: {e}")
        
        # Pattern recognition
        patterns = None
        if enable_patterns:
            try:
                logger.info("Running pattern recognition")
                recognizer = PatternRecognizer()
                patterns = {"status": "completed", "note": "Pattern recognition requires structured data"}
            except Exception as e:
                logger.error(f"Pattern recognition error: {e}")
        
        # Generate dashboard data
        dashboard_data = None
        try:
            logger.info("Generating dashboard data")
            from pipelines.processing.dashboard import DashboardGenerator
            
            # Get file chunks for dashboard generation
            file_chunks = get_file_chunks_for_dashboard(doc_path)
            
            # Generate dashboard
            dashboard_gen = DashboardGenerator(provider_name=provider_name)
            dashboard_result = dashboard_gen.generate_dashboard(file_chunks, file_name)
            dashboard_data = dashboard_result.get("dashboard")
            
            logger.info("Dashboard data generated successfully")
        except Exception as e:
            logger.error(f"Dashboard generation error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Update document status with dashboard data
        doc_metadata = {
            "status": "completed",
            "chunks_count": chunks_count,
            "embeddings_count": embedding_count,
            "facts_count": len(facts),
            "has_knowledge_graph": knowledge_graph is not None,
            "file_name": file_name,
            "chunking_strategy": chunking_strategy,
            "pipeline_metrics": metrics
        }
        if dashboard_data:
            doc_metadata["dashboard_data"] = dashboard_data
        
        storage.save_document(doc_id, doc_metadata)
        
        # Update batch status if this document is part of a batch
        try:
            storage.update_batch_document_status(doc_id, "completed")
        except Exception as batch_error:
            logger.warning(f"Failed to update batch status for doc {doc_id}: {batch_error}")
        
        result = {
            "status": "completed",
            "doc_id": doc_id,
            "chunks": chunks_count,
            "embeddings": embedding_count,
            "facts": len(facts),
            "has_knowledge_graph": knowledge_graph is not None,
            "has_patterns": patterns is not None,
            "chunking_strategy": chunking_strategy,
            "metrics": metrics
        }
        
        logger.info(f"Document {doc_id} processed successfully (synchronous)")
        return result
        
    except Exception as e:
        logger.error(f"Document processing error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Update document status to failed
        try:
            from services.storage.local import LocalStorage
            storage = LocalStorage()
            storage.save_document(doc_id, {"status": "failed", "error": str(e)})
            # Update batch status if this document is part of a batch
            storage.update_batch_document_status(doc_id, "failed", str(e))
        except Exception as batch_error:
            logger.warning(f"Failed to update batch/document status: {batch_error}")
        
        raise