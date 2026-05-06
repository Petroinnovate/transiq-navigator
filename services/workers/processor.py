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

    # Celery configuration — production-grade concurrency
    celery.conf.update(
        # Serialization
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        
        # Task tracking & limits
        task_track_started=True,
        task_time_limit=300,            # Hard limit: 5 minutes
        task_soft_time_limit=240,       # Soft limit: 4 minutes
        
        # Worker concurrency (from settings, overridable via env)
        worker_concurrency=settings.WORKER_CONCURRENCY,
        worker_prefetch_multiplier=settings.WORKER_PREFETCH_MULTIPLIER,
        worker_max_tasks_per_child=settings.WORKER_MAX_TASKS_PER_CHILD,
        worker_max_memory_per_child=settings.WORKER_MAX_MEMORY_PER_CHILD,
        
        # Reliability
        task_acks_late=True,            # Ack after execution (not before) — retry-safe
        task_reject_on_worker_lost=True,  # Re-queue if worker dies mid-task
        
        # Task routing — separate queues by task type
        task_routes={
            'services.workers.processor.process_document': {'queue': 'documents'},
            'services.workers.graph_processing.build_knowledge_graph': {'queue': 'graphs'},
            'services.workers.graph_processing.resolve_entity_duplicates': {'queue': 'maintenance'},
            'services.workers.graph_processing.analyze_graph_health': {'queue': 'maintenance'},
        },
        task_default_queue='documents',  # Default queue for unrouted tasks
        
        # Broker connection (fail fast)
        broker_connection_retry=False,
        broker_connection_max_retries=2,
        broker_connection_retry_on_startup=False,
        
        # Result backend
        result_backend_transport_options={
            'master_name': 'mymaster',
            'socket_keepalive': True,
            'socket_connect_timeout': 0.5,
            'retry_on_timeout': True,
            'max_connections': 10,       # Increased for concurrent workers
        },
        
        # Result expiry (clean up old results)
        result_expires=3600,  # 1 hour
    )
    
    logger.info(
        f"Celery configured: concurrency={settings.WORKER_CONCURRENCY}, "
        f"prefetch={settings.WORKER_PREFETCH_MULTIPLIER}, "
        f"pool={settings.WORKER_POOL}, "
        f"max_tasks_per_child={settings.WORKER_MAX_TASKS_PER_CHILD}"
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
# Celery Task: True Distributed Processing (now using async orchestrator)
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
        Celery task for distributed document processing.
        
        Delegates to AsyncPipelineOrchestrator for parallel execution:
          Chunks → asyncio.gather(Embed, Deduction, Dashboard)
        
        Progress is streamed via Redis Pub/Sub.
        """
        import asyncio
        from services.storage.local import LocalStorage
        from services.file_reader import read_file_content
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        
        task_id = self.request.id
        storage = LocalStorage()
        
        def _progress(stage: str, progress: int, message: str):
            """Bridge orchestrator progress to Redis Pub/Sub + DB."""
            try:
                storage.update_task_progress(task_id, stage, progress)
                _publish_progress(doc_id, stage, progress, message)
            except Exception:
                pass

        try:
            storage.save_task_status(task_id, doc_id, status='processing', stage='started', progress=0)
            _publish_progress(doc_id, 'started', 0, 'Task started')
            
            # Read file — NO truncation, full document
            logger.info(f"[Task {task_id}] Reading file: {doc_path}")
            _progress('reading_file', 10, 'Reading document')
            text = read_file_content(doc_path)
            file_name = os.path.basename(doc_path)
            logger.info(f"[Task {task_id}] Read {len(text):,} chars from {file_name}")
            
            # Run async orchestrator (parallel pipeline)
            orchestrator = AsyncPipelineOrchestrator(
                provider_name=provider_name,
                enable_cache=True,
            )
            
            result = asyncio.run(orchestrator.run(
                text=text,
                doc_id=doc_id,
                file_name=file_name,
                storage=storage,
                enable_deduction=enable_deduction,
                enable_patterns=enable_patterns,
                progress_cb=_progress,
            ))
            
            # Mark task completed
            storage.save_task_status(
                task_id, doc_id, status='completed', stage='completed',
                progress=100, result=result,
            )
            _publish_progress(doc_id, 'completed', 100, 'Processing complete', {"result": result})
            logger.info(f"[Task {task_id}] Document {doc_id} processed in {result.get('metrics', {}).get('total_time_ms', '?')}ms")
            return result
            
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            logger.error(f"[Task {task_id}] Processing failed: {error_msg}")
            logger.error(f"Traceback: {error_trace}")
            
            try:
                storage.save_document(doc_id, {"status": "failed", "error": error_msg})
                storage.save_task_status(task_id, doc_id, status='failed', error=error_msg)
                storage.update_batch_document_status(doc_id, "failed", error_msg)
                _publish_progress(doc_id, 'failed', 0, f'Processing failed: {error_msg}')
            except Exception as save_err:
                logger.error(f"Failed to save error status: {save_err}")
            
            if self.request.retries < self.max_retries:
                logger.info(f"[Task {task_id}] Retrying (attempt {self.request.retries + 1}/{self.max_retries})")
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
            
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
    Legacy entry point — delegates to process_document_sync which uses
    the AsyncPipelineOrchestrator for parallel processing.
    """
    return process_document_sync(
        doc_path=doc_path,
        doc_id=doc_id,
        provider_name=provider_name,
        enable_deduction=enable_deduction,
        enable_patterns=enable_patterns,
        chunking_strategy=chunking_strategy,
    )


def process_document_sync(
    doc_path: str,
    doc_id: str,
    provider_name: str = None,
    enable_deduction: bool = False,
    enable_patterns: bool = False,
    chunking_strategy: str = "adaptive"
):
    """
    Process document using AsyncPipelineOrchestrator (parallel pipeline).
    
    Called when Redis/Celery is not available. Runs the async orchestrator
    via asyncio.run() for maximum parallelism even in sync context.
    
    NO document truncation — full text is processed and intelligently chunked.
    """
    import asyncio

    try:
        from services.storage.local import LocalStorage
        from services.file_reader import read_file_content
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        
        logger.info(f"Starting parallel processing for document {doc_id}")
        
        storage = LocalStorage()
        
        # Read full file — NO truncation
        logger.info(f"Reading file: {doc_path}")
        text = read_file_content(doc_path)
        file_name = os.path.basename(doc_path)
        logger.info(f"Read {len(text):,} chars from {file_name}")

        # Run the async orchestrator (parallel: embed ∥ deduction ∥ dashboard)
        orchestrator = AsyncPipelineOrchestrator(
            provider_name=provider_name,
            enable_cache=True,
        )
        
        result = asyncio.run(orchestrator.run(
            text=text,
            doc_id=doc_id,
            file_name=file_name,
            storage=storage,
            enable_deduction=enable_deduction,
            enable_patterns=enable_patterns,
            chunking_strategy=chunking_strategy,
        ))
        
        logger.info(
            f"Document {doc_id} processed in {result.get('metrics', {}).get('total_time_ms', '?')}ms "
            f"(parallel pipeline)"
        )
        return result
        
    except Exception as e:
        logger.error(f"Document processing error: {e}")
        import traceback as tb
        logger.error(f"Traceback: {tb.format_exc()}")
        try:
            from services.storage.local import LocalStorage
            storage = LocalStorage()
            storage.save_document(doc_id, {"status": "failed", "error": str(e)})
            storage.update_batch_document_status(doc_id, "failed", str(e))
        except Exception as batch_error:
            logger.warning(f"Failed to update batch/document status: {batch_error}")
        raise