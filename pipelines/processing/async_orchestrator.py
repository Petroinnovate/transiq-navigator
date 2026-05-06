"""
Async Pipeline Orchestrator — Parallel document processing engine.

Architecture after chunking:

    Chunks ──┬── Embedding  → Qdrant       (IO-bound, threaded)
             ├── Deduction  → Knowledge Graph  (LLM, parallel async)
             └── Dashboard  → JSON Output      (LLM, context-aware async)

All three branches run concurrently via asyncio.gather().

Performance target:
    FROM: ~25s (serial)
    TO:   ~5-8s (parallel)
"""
import asyncio
import time
from typing import Any, Callable, Dict, List, Optional

from core.logging.logger import get_logger
from core.config.settings import settings
from services.cache.content_cache import ContentCache
from pipelines.processing.deduction_trigger import evaluate_deduction_trigger

logger = get_logger(__name__)

# ── Global LLM concurrency guard (per-process) ──────────────────────
# Prevents overloading LLM APIs when multiple worker processes run
# in parallel. Each process gets its own semaphore; across N workers
# with concurrency=4, max total LLM calls = N × _LLM_SEMAPHORE_LIMIT.
_LLM_SEMAPHORE_LIMIT = settings.PIPELINE_MAX_CONCURRENT_LLM
_llm_semaphore: Optional[asyncio.Semaphore] = None


def _get_llm_semaphore() -> asyncio.Semaphore:
    """Lazily create the per-event-loop semaphore."""
    global _llm_semaphore
    if _llm_semaphore is None:
        _llm_semaphore = asyncio.Semaphore(_LLM_SEMAPHORE_LIMIT)
    return _llm_semaphore


class AsyncPipelineOrchestrator:
    """
    Coordinates parallel execution of the document processing pipeline.
    
    Usage::
    
        orchestrator = AsyncPipelineOrchestrator(provider_name="gemini")
        result = await orchestrator.run(
            text=full_document_text,
            doc_id="abc-123",
            file_name="report.pdf",
            storage=storage,
            enable_deduction=True,
        )
    """

    def __init__(
        self,
        provider_name: Optional[str] = None,
        max_embed_chunks: int = 400,
        enable_cache: bool = True,
    ):
        self.provider_name = provider_name
        self.max_embed_chunks = max_embed_chunks
        self.enable_cache = enable_cache

    async def run(
        self,
        text: str,
        doc_id: str,
        file_name: str = "document",
        storage=None,
        enable_deduction: bool = False,
        enable_patterns: bool = False,
        user_id: str = "anonymous",
        progress_cb: Optional[Callable] = None,
        chunking_strategy: str = "adaptive",
    ) -> Dict[str, Any]:
        """
        Execute the full processing pipeline with maximum parallelism.
        
        Pipeline stages:
            1. Cache check (instant)
            2. Chunking   (CPU, ~200-500ms)
            3. PARALLEL:
               a. Embedding + Qdrant upsert  (IO, ~1s)
               b. Deduction / fact extraction (LLM × N, ~3-4s)
               c. Dashboard generation        (LLM × 1, ~3-5s)
            4. Persist results
        
        Returns:
            Complete result dict with dashboard_data, metrics, facts, etc.
        """
        t_start = time.time()
        metrics: Dict[str, Any] = {}

        # ── 0. Content-hash cache check ──────────────────────────────
        cache = ContentCache(storage) if self.enable_cache and storage else None
        if cache:
            cached = cache.get(text)
            if cached:
                logger.info(f"[{doc_id}] Cache HIT — skipping all processing")
                if progress_cb:
                    progress_cb('completed', 100, 'Loaded from cache')
                cached['from_cache'] = True
                return cached

        if progress_cb:
            progress_cb('reading_file', 10, 'Document read complete')

        # ── 1. Chunking ONLY (CPU, no IO — full document, no truncation) ──
        from pipelines.processing.pipeline import ChunkingPipeline

        if progress_cb:
            progress_cb('chunking', 15, 'Breaking document into chunks')

        pipeline = ChunkingPipeline(
            strategy=chunking_strategy,
            max_embed_chunks=self.max_embed_chunks,
            enable_metrics=True,
        )

        chunk_result = await pipeline.achunk(
            text=text,
            doc_id=doc_id,
            progress_cb=progress_cb,
        )

        chunks_data = chunk_result['chunks_data']
        chunk_texts = [c['text'] for c in chunks_data]
        metrics['chunking'] = chunk_result.get('metrics', {})

        # Validate chunks before launching expensive branches
        if not chunk_texts:
            logger.error(f"[{doc_id}] Chunking produced 0 chunks — aborting pipeline")
            return {
                'status': 'failed',
                'doc_id': doc_id,
                'error': 'Chunking produced no output',
                'chunks': 0,
                'embeddings': 0,
                'facts': 0,
                'has_knowledge_graph': False,
                'graphrag_task_id': None,
                'has_patterns': False,
                'dashboard_data': None,
                'metrics': metrics,
                'errors': ['Chunking produced 0 chunks'],
            }

        if progress_cb:
            progress_cb('processing', 25, f'Processing {len(chunk_texts)} chunks in parallel')

        # ── Smart deduction trigger ──────────────────────────────────
        # Resolves enable_deduction:
        #   True  → force ON  (explicit API flag)
        #   False → smart mode (auto-classify, may still enable)
        # The "force" param: True=always, False=never, None=smart
        force_flag = True if enable_deduction else None
        trigger = evaluate_deduction_trigger(chunks_data, force=force_flag)
        effective_deduction = trigger['run_deduction']
        metrics['deduction_trigger'] = trigger

        logger.info(
            f"[{doc_id}] Deduction trigger: type={trigger['document_type']}, "
            f"complex={trigger['is_complex']}, run={effective_deduction} "
            f"({trigger['reason']})"
        )

        # ── 2. TRUE 3-way parallel: Embedding ∥ Deduction ∥ Dashboard ──
        embedding_task = asyncio.create_task(self._run_embedding(
            chunks_data, chunk_texts, doc_id, storage, progress_cb,
        ))
        deduction_task = asyncio.create_task(self._run_deduction(
            text, doc_id, chunk_texts, storage, effective_deduction, progress_cb,
        ))
        dashboard_task = asyncio.create_task(self._run_dashboard(
            chunk_texts, file_name, doc_id, user_id, progress_cb,
        ))

        embedding_result, deduction_result, dashboard_result = await asyncio.gather(
            embedding_task,
            deduction_task,
            dashboard_task,
            return_exceptions=True,
        )

        # ── 3. Collect results + errors from each branch ─────────────
        errors: List[str] = []

        # Branch A — Embedding
        embedding_count = 0
        if isinstance(embedding_result, dict):
            embedding_count = embedding_result.get('embeddings_count', 0)
            metrics['embedding_time_ms'] = embedding_result.get('time_ms', 0)
        elif isinstance(embedding_result, Exception):
            logger.error(f"[{doc_id}] Embedding failed: {embedding_result}")
            errors.append(f"embedding: {embedding_result}")

        # Branch B — Deduction
        facts = []
        knowledge_graph = None
        graphrag_task_id = None
        if isinstance(deduction_result, dict):
            facts = deduction_result.get('facts', [])
            knowledge_graph = deduction_result.get('knowledge_graph')
            graphrag_task_id = deduction_result.get('graphrag_task_id')
            metrics['deduction_time_ms'] = deduction_result.get('time_ms', 0)
        elif isinstance(deduction_result, Exception):
            logger.error(f"[{doc_id}] Deduction failed: {deduction_result}")
            errors.append(f"deduction: {deduction_result}")

        # Branch C — Dashboard
        dashboard_data = None
        if isinstance(dashboard_result, dict):
            dashboard_data = dashboard_result.get('dashboard')
            metrics['dashboard_time_ms'] = dashboard_result.get('time_ms', 0)
        elif isinstance(dashboard_result, Exception):
            logger.error(f"[{doc_id}] Dashboard failed: {dashboard_result}")
            errors.append(f"dashboard: {dashboard_result}")

        if errors:
            logger.warning(f"[{doc_id}] Pipeline completed with {len(errors)} branch error(s): {errors}")

        # Determine pipeline status based on branch outcomes
        if len(errors) == 3:
            pipeline_status = 'failed'
        elif errors:
            pipeline_status = 'partial_success'
        else:
            pipeline_status = 'completed'

        # ── 4. Persist final results ─────────────────────────────────
        if progress_cb:
            progress_cb('saving', 95, 'Saving results')

        metrics['total_time_ms'] = int((time.time() - t_start) * 1000)

        result = {
            'status': pipeline_status,
            'doc_id': doc_id,
            'chunks': chunk_result['chunks_count'],
            'embeddings': embedding_count,
            'facts': len(facts),
            'has_knowledge_graph': knowledge_graph is not None,
            'graphrag_task_id': graphrag_task_id,
            'has_patterns': False,
            'dashboard_data': dashboard_data,
            'metrics': metrics,
            'errors': errors,
            'document_type': trigger['document_type'],
            'deduction_enabled': effective_deduction,
        }

        # Save to DB
        if storage:
            doc_metadata = {
                'status': pipeline_status,
                'chunks_count': chunk_result['chunks_count'],
                'embeddings_count': embedding_count,
                'facts_count': len(facts),
                'has_knowledge_graph': knowledge_graph is not None,
                'graphrag_task_id': graphrag_task_id,
                'file_name': file_name,
                'pipeline_metrics': metrics,
                'document_type': trigger['document_type'],
                'deduction_enabled': effective_deduction,
            }
            if dashboard_data:
                # Only overwrite stored dashboard if new data is non-empty
                # (prevents AI failures from erasing previously cached good dashboards)
                from pipelines.processing.dashboard import DashboardGenerator
                if not DashboardGenerator._is_empty_dashboard({'dashboard': dashboard_data}):
                    doc_metadata['dashboard_data'] = dashboard_data
            await asyncio.to_thread(storage.save_document, doc_id, doc_metadata, user_id)

            # Update batch if applicable
            try:
                await asyncio.to_thread(storage.update_batch_document_status, doc_id, 'completed')
            except Exception:
                pass

        # Store in content cache for future re-uploads
        # Cache even partial results (e.g. deduction succeeded but dashboard failed)
        # so re-uploads don't repeat expensive LLM calls needlessly.
        if cache and (dashboard_data or facts):
            cache.put(text, result)

        if progress_cb:
            progress_cb('completed', 100, 'Processing complete')

        logger.info(
            f"[{doc_id}] Pipeline complete in {metrics['total_time_ms']}ms "
            f"(type={trigger['document_type']}, "
            f"chunks={chunk_result['chunks_count']}, "
            f"embeds={embedding_count}, "
            f"facts={len(facts)}, deduction={'yes' if effective_deduction else 'skip'}, "
            f"dashboard={'yes' if dashboard_data else 'no'}, "
            f"errors={len(errors)})"
        )
        return result

    # ------------------------------------------------------------------
    # Branch A: Embedding + Vector DB + Chunk save (IO-bound)
    # ------------------------------------------------------------------

    async def _run_embedding(
        self,
        chunks_data: List[Dict[str, Any]],
        chunk_texts: List[str],
        doc_id: str,
        storage,
        progress_cb: Optional[Callable],
    ) -> Dict[str, Any]:
        """Embed chunks into Qdrant and save to SQLite. IO-bound, threaded."""
        t0 = time.time()
        embed_texts = chunk_texts[:self.max_embed_chunks]

        if progress_cb:
            progress_cb('embedding', 30, f'Embedding {len(embed_texts)} chunks')

        async def _embed():
            try:
                from services.vector_store.indexing.vector_storage import VectorStorageService
                vs = VectorStorageService()
                count = await asyncio.to_thread(vs.upsert_chunks, embed_texts, doc_id)
                logger.info(f"[{doc_id}] Indexed {count} embeddings")
                return count
            except Exception as e:
                logger.warning(f"[{doc_id}] Vector indexing skipped: {e}")
                return 0

        async def _save_chunks():
            if not storage:
                return
            def _do():
                for idx, cm in enumerate(chunks_data):
                    chunk_id = f"{doc_id}-c-{idx}"
                    storage.save_chunk(chunk_id, doc_id, cm['text'], cm.get('metadata', {}))
            await asyncio.to_thread(_do)

        embedding_count, _ = await asyncio.gather(_embed(), _save_chunks())

        elapsed_ms = int((time.time() - t0) * 1000)
        if progress_cb:
            progress_cb('embedding', 55, f'Embedded {embedding_count} chunks in {elapsed_ms}ms')

        return {
            'embeddings_count': embedding_count,
            'time_ms': elapsed_ms,
        }

    # ------------------------------------------------------------------
    # Branch B: Deduction (parallel LLM calls)
    # ------------------------------------------------------------------

    async def _run_deduction(
        self,
        text: str,
        doc_id: str,
        chunk_texts: List[str],
        storage,
        enable_deduction: bool,
        progress_cb: Optional[Callable],
    ) -> Dict[str, Any]:
        """Run deduction engine with parallel fact extraction."""
        t0 = time.time()
        if not enable_deduction:
            return {'facts': [], 'knowledge_graph': None, 'graphrag_task_id': None, 'time_ms': 0}

        try:
            from pipelines.processing.deduction import DeductionEngine

            if progress_cb:
                progress_cb('deduction', 40, 'Extracting facts (parallel)')

            ded = DeductionEngine(provider_name=self.provider_name)

            # Use the async parallel extraction (bounded by global LLM semaphore)
            sem = _get_llm_semaphore()
            async with sem:
                facts = await ded.aextract_facts(text)
            knowledge_graph = ded.build_knowledge_graph(facts)

            # Save edges to storage
            if storage and knowledge_graph:
                def _save_edges():
                    for i, edge in enumerate(knowledge_graph.get('edges', [])):
                        edge_id = f"{doc_id}-e-{i}"
                        storage.save_edges(edge_id, doc_id, edge)
                await asyncio.to_thread(_save_edges)

            # GraphRAG integration (non-blocking)
            graphrag_task_id = None
            if facts:
                try:
                    graphrag_task_id = await asyncio.to_thread(
                        ded.publish_facts_to_graph, facts, doc_id
                    )
                except Exception as e:
                    logger.warning(f"GraphRAG integration failed: {e}")

            elapsed_ms = int((time.time() - t0) * 1000)
            if progress_cb:
                progress_cb('deduction', 70, f'Extracted {len(facts)} facts in {elapsed_ms}ms')

            return {
                'facts': facts,
                'knowledge_graph': knowledge_graph,
                'graphrag_task_id': graphrag_task_id,
                'time_ms': elapsed_ms,
            }

        except Exception as e:
            logger.error(f"Deduction engine error: {e}")
            return {'facts': [], 'knowledge_graph': None, 'graphrag_task_id': None, 'time_ms': int((time.time() - t0) * 1000)}

    # ------------------------------------------------------------------
    # Branch C: Dashboard (context-aware LLM call)
    # ------------------------------------------------------------------

    async def _run_dashboard(
        self,
        chunk_texts: List[str],
        file_name: str,
        doc_id: Optional[str],
        user_id: Optional[str],
        progress_cb: Optional[Callable],
    ) -> Dict[str, Any]:
        """Generate dashboard using context-aware async path."""
        t0 = time.time()
        try:
            from pipelines.processing.dashboard import DashboardGenerator

            if progress_cb:
                progress_cb('generating_dashboard', 50, 'Generating AI dashboard')

            gen = DashboardGenerator(provider_name=self.provider_name)

            # Acquire global LLM semaphore to prevent API overload
            # across concurrent worker processes
            sem = _get_llm_semaphore()
            async with sem:
                result = await gen.agenerate_dashboard(
                    chunks=chunk_texts,
                    file_name=file_name,
                    doc_id=doc_id,
                    user_id=user_id,
                )

            elapsed_ms = int((time.time() - t0) * 1000)
            if progress_cb:
                progress_cb('generating_dashboard', 80, f'Dashboard generated in {elapsed_ms}ms')

            result['time_ms'] = elapsed_ms
            return result

        except Exception as e:
            logger.error(f"Dashboard generation error: {e}")
            from pipelines.processing.dashboard import DashboardGenerator
            fallback = DashboardGenerator()._get_fallback_dashboard(file_name, str(e), chunks=chunk_texts, doc_id=doc_id)
            fallback['time_ms'] = int((time.time() - t0) * 1000)
            return fallback
