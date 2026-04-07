"""
Graph Building Celery Worker
Post-processes deduction engine facts into knowledge graph
"""
import logging
from typing import List, Dict, Any
import traceback

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None

from app.config.settings import settings
from app.storage.graph_storage import GraphStorage
from app.processors.graph_rag.entity_resolver import EntityResolver
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize Celery if available
if CELERY_AVAILABLE:
    celery = Celery(
        'transiq_graph_workers',
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND
    )
    
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
    )
else:
    celery = None


# ============================================================================
# Celery Tasks for Graph Building
# ============================================================================

if CELERY_AVAILABLE and celery:
    
    @celery.task(bind=True, max_retries=2)
    def build_knowledge_graph(self, doc_id: str, facts: List[Dict[str, Any]],
                             user_id: str = None):
        """
        Post-processing task: Build knowledge graph from extracted facts
        
        Runs after deduction engine completes
        
        Args:
            self: Celery task instance
            doc_id: Document ID
            facts: List of facts from deduction engine
            user_id: User ID for multi-tenancy
            
        Returns:
            Integration result
        """
        task_id = self.request.id
        
        try:
            logger.info(f"[Task {task_id}] Building knowledge graph for doc {doc_id}")
            
            if not facts:
                logger.info(f"[Task {task_id}] No facts provided, skipping graph building")
                return {"doc_id": doc_id, "facts_count": 0, "status": "skipped"}
            
            # Integrate facts into graph
            with GraphStorage() as graph_storage:
                result = graph_storage.integrate_facts(facts, doc_id, user_id)
            
            logger.info(f"[Task {task_id}] ✓ Graph building complete: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[Task {task_id}] Graph building error: {e}\n{traceback.format_exc()}")
            
            # Retry with exponential backoff
            try:
                self.retry(countdown=60 * (2 ** self.request.retries))
            except self.MaxRetriesExceededError:
                logger.error(f"[Task {task_id}] Graph building failed after max retries")
                return {"doc_id": doc_id, "status": "failed", "error": str(e)}
    
    
    @celery.task(bind=True)
    def resolve_entity_duplicates(self, doc_id: str = None, threshold: float = 0.85):
        """
        Background task: Find and merge duplicate entities
        
        Can be called manually or on schedule
        
        Args:
            self: Celery task instance
            doc_id: Optional - only process entities from specific document
            threshold: Similarity threshold for merging
            
        Returns:
            Merge result
        """
        task_id = self.request.id
        
        try:
            logger.info(f"[Task {task_id}] Resolving entity duplicates (threshold={threshold})")
            
            with GraphStorage() as graph_storage:
                merged_count = graph_storage.find_and_merge_duplicates(threshold)
            
            logger.info(f"[Task {task_id}] ✓ Merged {merged_count} entities")
            return {"status": "success", "merged_count": merged_count}
            
        except Exception as e:
            logger.error(f"[Task {task_id}] Duplicate resolution error: {e}")
            return {"status": "failed", "error": str(e)}
    
    
    @celery.task(bind=True)
    def analyze_graph_health(self, doc_id: str = None):
        """
        Background task: Analyze graph health and quality
        
        Args:
            self: Celery task instance
            doc_id: Optional - only analyze specific document
            
        Returns:
            Health analysis
        """
        task_id = self.request.id
        
        try:
            logger.info(f"[Task {task_id}] Analyzing graph health")
            
            with GraphStorage() as graph_storage:
                summary = graph_storage.get_graph_summary()
                quality = graph_storage.get_data_quality_metrics()
            
            logger.info(f"[Task {task_id}] ✓ Analysis complete")
            return {
                "status": "success",
                "summary": summary,
                "quality": quality
            }
            
        except Exception as e:
            logger.error(f"[Task {task_id}] Health analysis error: {e}")
            return {"status": "failed", "error": str(e)}


# ============================================================================
# Synchronous Functions (for non-Celery environments)
# ============================================================================

def build_knowledge_graph_sync(doc_id: str, facts: List[Dict[str, Any]],
                               user_id: str = None) -> Dict[str, Any]:
    """
    Synchronous version of graph building (for testing/development)
    
    Args:
        doc_id: Document ID
        facts: List of facts
        user_id: User ID
        
    Returns:
        Integration result
    """
    logger.info(f"Building knowledge graph for doc {doc_id} (sync mode)")
    
    try:
        with GraphStorage() as graph_storage:
            result = graph_storage.integrate_facts(facts, doc_id, user_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Graph building error: {e}")
        return {"doc_id": doc_id, "status": "failed", "error": str(e)}


def enqueue_graph_building(doc_id: str, facts: List[Dict[str, Any]],
                           user_id: str = None) -> str:
    """
    Enqueue graph building (uses Celery if available, falls back to sync)
    
    Args:
        doc_id: Document ID
        facts: List of facts
        user_id: User ID
        
    Returns:
        Task ID (or empty string if sync)
    """
    if CELERY_AVAILABLE and celery and build_knowledge_graph:
        try:
            result = build_knowledge_graph.delay(doc_id, facts, user_id)
            logger.info(f"Enqueued graph building task {result.id} for doc {doc_id}")
            return result.id
        except Exception as e:
            logger.warning(f"Celery dispatch failed: {e}, falling back to sync")
    
    # Fallback to synchronous processing
    logger.info(f"Building graph synchronously for {doc_id}")
    build_knowledge_graph_sync(doc_id, facts, user_id)
    return ""


async def enqueue_graph_building_async(doc_id: str, facts: List[Dict[str, Any]],
                                       user_id: str = None) -> str:
    """
    Async version of graph building enqueue
    
    Args:
        doc_id: Document ID
        facts: List of facts
        user_id: User ID
        
    Returns:
        Task ID
    """
    return enqueue_graph_building(doc_id, facts, user_id)


# ============================================================================
# Periodic Tasks
# ============================================================================

if CELERY_AVAILABLE and celery:
    
    # Run duplicate resolution every 6 hours
    celery.add_periodic_task(
        6 * 60 * 60,  # Every 6 hours
        resolve_entity_duplicates.s(threshold=0.85),
        name='resolve-duplicates-periodic'
    )
    
    # Run health analysis every 12 hours
    celery.add_periodic_task(
        12 * 60 * 60,  # Every 12 hours
        analyze_graph_health.s(),
        name='analyze-graph-health-periodic'
    )


def main():
    """Test graph building"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Test facts
    test_facts = [
        {"subject": "Apple Inc", "predicate": "owns", "object": "Beats Electronics", "confidence": 0.9},
        {"subject": "Apple Inc", "predicate": "manufactures", "object": "iPhone", "confidence": 0.95},
        {"subject": "Steve Jobs", "predicate": "founded", "object": "Apple Inc", "confidence": 0.9}
    ]
    
    result = build_knowledge_graph_sync("test_doc_123", test_facts)
    print(f"\nGraph building result: {result}")


if __name__ == "__main__":
    main()
