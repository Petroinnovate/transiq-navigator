"""
Task enqueueing functions
"""
from pipelines.workers.processor import celery, process_document_sync, CELERY_AVAILABLE
from core.logging.logger import get_logger
import uuid
import threading
import socket

logger = get_logger(__name__)


def _is_redis_available() -> bool:
    """Quick check if Redis is available (without retries)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)  # 500ms timeout
        result = sock.connect_ex(('localhost', 6379))
        sock.close()
        return result == 0
    except:
        return False


def enqueue_document(
    doc_path: str,
    doc_id: str,
    provider_name: str = None,
    enable_deduction: bool = False,
    enable_patterns: bool = False
) -> str:
    """
    Enqueue document for processing - uses Celery if available, falls back to threads
    
    Args:
        doc_path: Path to document file
        doc_id: Document ID
        provider_name: LLM provider name
        enable_deduction: Enable deduction engine
        enable_patterns: Enable pattern recognition
        
    Returns:
        Task ID
    """
    # Try Celery first if available
    if CELERY_AVAILABLE and _is_redis_available():
        try:
            from pipelines.workers.processor import process_document
            from services.storage.local import LocalStorage
            
            # Dispatch Celery task
            logger.info(f"Dispatching Celery task for document {doc_id}")
            result = process_document.delay(
                doc_path=doc_path,
                doc_id=doc_id,
                provider_name=provider_name,
                enable_deduction=enable_deduction,
                enable_patterns=enable_patterns
            )
            
            task_id = result.id
            logger.info(f"Celery task {task_id} dispatched for document {doc_id}")
            
            # Save initial task status
            storage = LocalStorage()
            storage.save_task_status(task_id, doc_id, status='queued', stage='queued', progress=0)
            
            return task_id
            
        except Exception as celery_error:
            logger.warning(f"Celery dispatch failed: {celery_error}, falling back to threads")
    
    # Fallback: Use background thread (legacy mode)
    logger.info(f"Using background thread processing for {doc_id}")
    task_id = str(uuid.uuid4())
    
    # Process document in background thread (non-blocking)
    def process_in_background():
        try:
            logger.info(f"Starting synchronous processing for document {doc_id}")
            result = process_document_sync(
                doc_path=doc_path,
                doc_id=doc_id,
                provider_name=provider_name,
                enable_deduction=enable_deduction,
                enable_patterns=enable_patterns
            )
            logger.info(f"Completed synchronous processing for document {doc_id}")
            
            # Persist result to storage so polling endpoints can find it
            try:
                from services.storage.local import LocalStorage
                storage = LocalStorage()
                if isinstance(result, dict) and result.get('dashboard_data'):
                    storage.update_document(doc_id, {
                        'status': 'completed',
                        'dashboard_data': result['dashboard_data'],
                    })
                else:
                    storage.update_document(doc_id, {'status': 'completed'})
                # Also update task status for polling
                storage.save_task_status(task_id, doc_id, status='completed', 
                                        stage='completed', progress=100)
                logger.info(f"Persisted results for document {doc_id}")
            except Exception as persist_err:
                logger.error(f"Failed to persist results for {doc_id}: {persist_err}")
                
        except Exception as sync_error:
            logger.error(f"Synchronous processing failed for {doc_id}: {sync_error}")
            # Update document status to failed (partial update — preserves existing data)
            try:
                from services.storage.local import LocalStorage
                storage = LocalStorage()
                storage.update_document(doc_id, {'status': 'failed'})
                storage.save_task_status(task_id, doc_id, status='failed',
                                        error=str(sync_error))
            except Exception as save_err:
                logger.error(f"Failed to save error state for {doc_id}: {save_err}")
    
    # Start processing in background thread
    thread = threading.Thread(target=process_in_background, daemon=True)
    thread.start()
    
    logger.info(f"Generated task ID {task_id} for document {doc_id} (processing in thread)")
    return task_id

