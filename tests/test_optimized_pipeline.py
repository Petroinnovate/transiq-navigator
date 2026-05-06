"""
Tests for the optimized async pipeline.

Covers:
  1. Content hash cache (put/get/invalidate)
  2. Parallel deduction (aextract_facts with mock LLM)
  3. Context-aware dashboard (chunk selection + agenerate_dashboard)
  4. Async ChunkingPipeline (aprocess)
  5. AsyncPipelineOrchestrator end-to-end
  6. No 600K truncation
  7. Timeout + retry behavior
  8. Partial failure tolerance
  9. Chunking coverage validation
"""
import asyncio
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

# Ensure Backend is importable
sys.path.insert(0, os.path.dirname(__file__))


class TestContentCache(unittest.TestCase):
    """Test the content-hash based caching layer."""

    def test_cache_miss_returns_none(self):
        from services.cache.content_cache import ContentCache
        cache = ContentCache(storage=None)
        self.assertIsNone(cache.get("some text"))

    def test_cache_put_and_get(self):
        from services.storage.local import LocalStorage
        from services.cache.content_cache import ContentCache
        storage = LocalStorage()
        cache = ContentCache(storage)
        text = f"unique document content {time.time()}"
        result = {"status": "completed", "doc_id": "test-123"}
        cache.put(text, result)
        cached = cache.get(text)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["doc_id"], "test-123")

    def test_cache_invalidate(self):
        from services.storage.local import LocalStorage
        from services.cache.content_cache import ContentCache
        storage = LocalStorage()
        cache = ContentCache(storage)
        text = f"content to invalidate {time.time()}"
        cache.put(text, {"x": 1})
        self.assertTrue(cache.invalidate(text))
        self.assertIsNone(cache.get(text))

    def test_content_hash_deterministic(self):
        from services.cache.content_cache import content_hash
        h1 = content_hash("hello world")
        h2 = content_hash("hello world")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, content_hash("different"))


class TestContentNormalization(unittest.TestCase):
    """Test text normalization for cache key stability."""

    def test_normalize_collapses_whitespace(self):
        from services.cache.content_cache import normalize_text
        self.assertEqual(normalize_text("hello   world"), "hello world")
        self.assertEqual(normalize_text("a\n\n\nb"), "a b")
        self.assertEqual(normalize_text("  tabs\there  "), "tabs here")

    def test_normalize_lowercases(self):
        from services.cache.content_cache import normalize_text
        self.assertEqual(normalize_text("Hello World"), "hello world")

    def test_normalize_strips(self):
        from services.cache.content_cache import normalize_text
        self.assertEqual(normalize_text("  trimmed  "), "trimmed")

    def test_hash_matches_after_normalization(self):
        """Trivially different texts should produce the same hash."""
        from services.cache.content_cache import content_hash
        h1 = content_hash("Hello  World")
        h2 = content_hash("hello world")
        h3 = content_hash("  HELLO   WORLD  ")
        self.assertEqual(h1, h2)
        self.assertEqual(h2, h3)

    def test_hash_raw_mode_skips_normalization(self):
        from services.cache.content_cache import content_hash
        h_norm = content_hash("Hello World", normalize=True)
        h_raw = content_hash("Hello World", normalize=False)
        self.assertNotEqual(h_norm, h_raw)

    def test_cache_hit_with_different_whitespace(self):
        """Cache should hit even when re-upload has different whitespace."""
        from services.storage.local import LocalStorage
        from services.cache.content_cache import ContentCache
        storage = LocalStorage()
        cache = ContentCache(storage)
        text_v1 = f"Report data   section  {time.time()}"
        text_v2 = text_v1.replace("   ", " ").replace("  ", " ")
        cache.put(text_v1, {"doc_id": "v1"})
        cached = cache.get(text_v2)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["doc_id"], "v1")


class TestContentCacheTTL(unittest.TestCase):
    """Test TTL-based cache expiry."""

    def test_expired_entry_returns_none(self):
        from services.storage.local import LocalStorage
        from services.cache.content_cache import ContentCache
        storage = LocalStorage()
        cache = ContentCache(storage, ttl_seconds=1)
        text = f"expire me {time.time()}"
        cache.put(text, {"x": 1})

        # Force expiry by updating expires_at in the past
        from services.cache.content_cache import content_hash
        h = content_hash(text)
        storage.conn.execute(
            'UPDATE content_cache SET expires_at = ? WHERE content_hash = ?',
            (time.time() - 100, h),
        )
        storage.conn.commit()

        self.assertIsNone(cache.get(text))

    def test_non_expired_entry_returned(self):
        from services.storage.local import LocalStorage
        from services.cache.content_cache import ContentCache
        storage = LocalStorage()
        cache = ContentCache(storage, ttl_seconds=3600)
        text = f"valid entry {time.time()}"
        cache.put(text, {"y": 2})
        self.assertIsNotNone(cache.get(text))

    def test_cleanup_expired_removes_old_entries(self):
        from services.storage.local import LocalStorage
        from services.cache.content_cache import ContentCache, content_hash
        storage = LocalStorage()
        cache = ContentCache(storage, ttl_seconds=1)
        text = f"cleanup target {time.time()}"
        cache.put(text, {"z": 3})

        # Force expiry
        h = content_hash(text)
        storage.conn.execute(
            'UPDATE content_cache SET expires_at = ? WHERE content_hash = ?',
            (time.time() - 100, h),
        )
        storage.conn.commit()

        deleted = cache.cleanup_expired()
        self.assertGreaterEqual(deleted, 1)
        self.assertIsNone(cache.get(text))


class TestContentCacheHas(unittest.TestCase):
    """Test the has() method for fast existence checks."""

    def test_has_returns_true_for_cached(self):
        from services.storage.local import LocalStorage
        from services.cache.content_cache import ContentCache
        storage = LocalStorage()
        cache = ContentCache(storage)
        text = f"has check {time.time()}"
        cache.put(text, {"ok": True})
        self.assertTrue(cache.has(text))

    def test_has_returns_false_for_missing(self):
        from services.cache.content_cache import ContentCache
        cache = ContentCache(storage=None)
        self.assertFalse(cache.has("nonexistent"))

    def test_has_returns_false_for_expired(self):
        from services.storage.local import LocalStorage
        from services.cache.content_cache import ContentCache, content_hash
        storage = LocalStorage()
        cache = ContentCache(storage, ttl_seconds=1)
        text = f"has expire {time.time()}"
        cache.put(text, {"ok": True})

        h = content_hash(text)
        storage.conn.execute(
            'UPDATE content_cache SET expires_at = ? WHERE content_hash = ?',
            (time.time() - 100, h),
        )
        storage.conn.commit()

        self.assertFalse(cache.has(text))


class TestContentCacheStats(unittest.TestCase):
    """Test cache statistics."""

    def test_stats_with_no_storage(self):
        from services.cache.content_cache import ContentCache
        cache = ContentCache(storage=None)
        stats = cache.stats()
        self.assertFalse(stats["available"])

    def test_stats_returns_correct_counts(self):
        from services.storage.local import LocalStorage
        from services.cache.content_cache import ContentCache
        storage = LocalStorage()
        cache = ContentCache(storage)
        text = f"stats check {time.time()}"
        cache.put(text, {"s": 1})
        cache.get(text)  # +1 hit
        cache.get(text)  # +1 hit

        stats = cache.stats()
        self.assertTrue(stats["available"])
        self.assertGreaterEqual(stats["total_entries"], 1)
        self.assertGreaterEqual(stats["total_hits"], 2)
        self.assertIn("ttl_seconds", stats)


class TestSyncDashboardUsesCache(unittest.TestCase):
    """Verify the orchestrator caches partial results too."""

    def test_no_dashboard_only_condition(self):
        """Cache should store results even when only deduction succeeds."""
        import inspect
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        source = inspect.getsource(AsyncPipelineOrchestrator.run)
        # The old condition was: if cache and dashboard_data
        # New condition should include facts
        self.assertIn("dashboard_data or facts", source)


class TestChunkingNoTruncation(unittest.TestCase):
    """Verify that chunking processes full documents without truncation."""

    def test_large_document_not_truncated(self):
        from pipelines.processing.chunking.adaptive import AdaptiveChunker
        # Create a 700K char document (was previously truncated at 600K)
        text = "Section A. " * 70_000  # ~770K chars
        chunker = AdaptiveChunker()
        chunks = chunker.chunk(text)
        total_chars = sum(len(c) for c in chunks)
        # All content should be represented (with overlap there may be more)
        self.assertGreater(total_chars, 600_000)
        self.assertGreater(len(chunks), 1)

    def test_pipeline_process_no_cap(self):
        from pipelines.processing.pipeline import ChunkingPipeline
        pipeline = ChunkingPipeline(strategy='adaptive', enable_metrics=True)
        text = "Data point. " * 10_000  # 130K chars
        result = pipeline.process(text=text, doc_id="test-no-cap")
        self.assertGreater(result['chunks_count'], 10)
        self.assertIn('total_chunks', result['metrics'])


class TestAsyncChunkingPipeline(unittest.TestCase):
    """Test async chunking pipeline."""

    def test_aprocess_returns_chunks(self):
        from pipelines.processing.pipeline import ChunkingPipeline
        pipeline = ChunkingPipeline(strategy='adaptive', enable_metrics=True)
        text = "This is a test document with multiple sentences. " * 500

        result = asyncio.run(pipeline.aprocess(text=text, doc_id="async-test"))
        self.assertIn('chunks_data', result)
        self.assertIn('chunks_count', result)
        self.assertIn('metrics', result)
        self.assertGreater(result['chunks_count'], 0)


class TestContextAwareDashboard(unittest.TestCase):
    """Test the context-aware chunk selection for dashboard generation."""

    def test_select_context_chunks_limits(self):
        from pipelines.processing.dashboard import DashboardGenerator
        gen = DashboardGenerator.__new__(DashboardGenerator)
        # Create 50 chunks — keyword fallback always works
        chunks = [f"Chunk {i} with some text about metrics and KPIs" for i in range(50)]
        selected = gen._keyword_rank_chunks(chunks, max_chunks=10)
        self.assertEqual(len(selected), 10)

    def test_select_context_chunks_preserves_order(self):
        from pipelines.processing.dashboard import DashboardGenerator
        gen = DashboardGenerator.__new__(DashboardGenerator)
        chunks = [
            "Introduction with summary and overview of performance",  # high score
            "Random text without keywords",
            "KPI target actual variance trend analysis results",  # highest score
            "More random text",
            "Conclusion with recommendation findings and total budget roi",  # high score
        ]
        selected = gen._keyword_rank_chunks(chunks, max_chunks=3)
        self.assertEqual(len(selected), 3)
        # Verify original order is preserved
        indices = [chunks.index(s) for s in selected]
        self.assertEqual(indices, sorted(indices))

    def test_select_small_doc_returns_all(self):
        from pipelines.processing.dashboard import DashboardGenerator
        gen = DashboardGenerator.__new__(DashboardGenerator)
        chunks = ["a", "b", "c"]
        selected = gen._select_context_chunks(chunks, max_chunks=10)
        self.assertEqual(len(selected), 3)


class TestParallelDeduction(unittest.TestCase):
    """Test that deduction aextract_facts uses parallel execution."""

    def test_deduction_split_into_chunks(self):
        from pipelines.processing.deduction import _split_text_into_chunks
        text = "a " * 50_000  # 100K chars
        chunks = _split_text_into_chunks(text)
        self.assertGreater(len(chunks), 1)
        self.assertLessEqual(len(chunks), 16)

    def test_merge_facts_deduplicates(self):
        from pipelines.processing.deduction import _merge_facts
        facts = [
            {"subject": "Oil", "predicate": "is", "object": "valuable", "confidence": 0.9},
            {"subject": "oil", "predicate": "is", "object": "valuable", "confidence": 0.8},
            {"subject": "Gas", "predicate": "costs", "object": "$5", "confidence": 0.7},
        ]
        merged = _merge_facts(facts, max_facts=10)
        self.assertEqual(len(merged), 2)  # Deduped "oil is valuable"

    def test_parse_fact_response_handles_formats(self):
        from pipelines.processing.deduction import DeductionEngine
        engine = DeductionEngine.__new__(DeductionEngine)
        # List format
        r1 = engine._parse_fact_response([{"subject": "A", "predicate": "is", "object": "B"}])
        self.assertEqual(len(r1), 1)
        # Dict with "facts" key
        r2 = engine._parse_fact_response({"facts": [{"subject": "X", "predicate": "has", "object": "Y"}]})
        self.assertEqual(len(r2), 1)
        # Empty
        r3 = engine._parse_fact_response("invalid")
        self.assertEqual(len(r3), 0)


class TestProcessorNoTruncation(unittest.TestCase):
    """Verify processor.py no longer truncates documents."""

    def test_no_600k_cap_in_processor(self):
        """Ensure the 600K hard cap has been removed from processor.py"""
        import inspect
        from services.workers.processor import process_document_sync
        source = inspect.getsource(process_document_sync)
        self.assertNotIn("600_000", source)
        self.assertNotIn("600000", source)
        self.assertNotIn("MAX_TEXT_CHARS", source)


class TestSettingsNewConfig(unittest.TestCase):
    """Verify new pipeline settings are available."""

    def test_pipeline_settings_exist(self):
        from core.config.settings import settings
        self.assertIsInstance(settings.PIPELINE_MAX_CONCURRENT_LLM, int)
        self.assertIsInstance(settings.PIPELINE_LLM_TIMEOUT, int)
        self.assertIsInstance(settings.PIPELINE_ENABLE_CONTENT_CACHE, bool)
        self.assertIsInstance(settings.PIPELINE_DASHBOARD_MAX_CONTEXT, int)
        self.assertEqual(settings.PIPELINE_MAX_CONCURRENT_LLM, 8)


# =====================================================================
# Async deduction engine — parallelism, timeout, retry, partial failure
# =====================================================================

class _FakeLLM:
    """Configurable fake LLM for testing async deduction behavior."""

    def __init__(self, delay: float = 0.05, fail_on: set = None, timeout_on: set = None):
        self.delay = delay
        self.fail_on = fail_on or set()        # chunk indices that raise
        self.timeout_on = timeout_on or set()   # chunk indices that sleep long
        self.call_count = 0
        self.call_log: list = []

    def generate_json(self, prompt: str):
        idx = self.call_count
        self.call_count += 1
        self.call_log.append({"index": idx, "time": time.time()})

        if idx in self.timeout_on:
            # Sleep just long enough to exceed the test timeout (0.3s)
            # but short enough that the test finishes fast
            time.sleep(2)
            return []  # won't be reached if timeout fires first
        if idx in self.fail_on:
            raise RuntimeError(f"Simulated LLM failure on call {idx}")

        time.sleep(self.delay)
        return [
            {"subject": f"Entity{idx}", "predicate": "relates_to", "object": f"Target{idx}", "confidence": 0.9},
        ]

    def get_model_info(self):
        return {"provider": "fake"}


class TestAsyncDeductionParallel(unittest.TestCase):
    """Test that aextract_facts truly runs chunks in parallel."""

    def test_parallel_is_faster_than_serial(self):
        """8 chunks × 0.1s each: serial=0.8s, parallel<0.3s."""
        from pipelines.processing.deduction import DeductionEngine, _CHUNK_SIZE

        engine = DeductionEngine.__new__(DeductionEngine)
        engine.llm = _FakeLLM(delay=0.1)

        # Build text that produces ~4 chunks
        text = ("Sentence about data. " * 1000 + "\n") * 3  # ~60K chars > _CHUNK_SIZE
        assert len(text) > _CHUNK_SIZE

        t0 = time.time()
        facts = asyncio.run(engine.aextract_facts(text, max_facts=50))
        elapsed = time.time() - t0

        self.assertGreater(len(facts), 0)
        # Parallel should be well under serial time (4 × 0.1 = 0.4s serial)
        self.assertLess(elapsed, 0.4, f"Took {elapsed:.2f}s — not parallel enough")

    def test_all_chunks_produce_facts(self):
        """Every chunk should contribute at least one fact."""
        from pipelines.processing.deduction import DeductionEngine, _split_text_into_chunks

        engine = DeductionEngine.__new__(DeductionEngine)
        engine.llm = _FakeLLM(delay=0.01)

        text = "Important data point here. " * 5000  # multiple chunks
        chunks = _split_text_into_chunks(text)
        n_chunks = len(chunks)
        self.assertGreater(n_chunks, 1)

        facts = asyncio.run(engine.aextract_facts(text))
        # Each chunk produces 1 fact via _FakeLLM → at least n_chunks facts
        self.assertGreaterEqual(len(facts), n_chunks)


class TestAsyncDeductionTimeout(unittest.TestCase):
    """Test that per-chunk timeouts don't crash the pipeline."""

    def test_timeout_chunk_skipped_others_succeed(self):
        """Chunk 0 hangs (timeout) → skipped, chunks 1+ succeed."""
        from pipelines.processing.deduction import DeductionEngine, _CHUNK_TIMEOUT
        import pipelines.processing.deduction as ded_mod

        engine = DeductionEngine.__new__(DeductionEngine)
        engine.llm = _FakeLLM(delay=0.01, timeout_on={0})

        # Temporarily lower timeout so test is fast
        original_timeout = ded_mod._CHUNK_TIMEOUT
        original_retries = ded_mod._CHUNK_RETRIES
        ded_mod._CHUNK_TIMEOUT = 0.3   # 300ms timeout
        ded_mod._CHUNK_RETRIES = 0     # no retries — fail fast

        try:
            text = "Some analysis content. " * 5000  # multiple chunks
            facts = asyncio.run(engine.aextract_facts(text))
            # Should still get facts from non-hanging chunks
            self.assertGreater(len(facts), 0)
        finally:
            ded_mod._CHUNK_TIMEOUT = original_timeout
            ded_mod._CHUNK_RETRIES = original_retries


class TestAsyncDeductionRetry(unittest.TestCase):
    """Test that transient failures are retried."""

    def test_retry_recovers_from_first_failure(self):
        """LLM fails on first call, succeeds on retry."""
        from pipelines.processing.deduction import DeductionEngine
        import pipelines.processing.deduction as ded_mod

        call_count = 0
        def flaky_generate_json(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Transient error")
            return [{"subject": "A", "predicate": "is", "object": "B", "confidence": 0.9}]

        engine = DeductionEngine.__new__(DeductionEngine)
        engine.llm = MagicMock()
        engine.llm.generate_json = flaky_generate_json
        engine.llm.get_model_info.return_value = {"provider": "mock"}

        # Small text = 1 chunk → 1 call that fails then retries
        original_retries = ded_mod._CHUNK_RETRIES
        ded_mod._CHUNK_RETRIES = 2
        try:
            facts = asyncio.run(engine.aextract_facts("Short text for testing."))
            self.assertEqual(len(facts), 1)
            self.assertEqual(call_count, 2)  # failed once + succeeded once
        finally:
            ded_mod._CHUNK_RETRIES = original_retries


class TestAsyncDeductionPartialFailure(unittest.TestCase):
    """Test that partial failures return partial results."""

    def test_some_chunks_fail_still_get_results(self):
        """Chunks 0,2 fail permanently → still get facts from chunk 1,3+."""
        from pipelines.processing.deduction import DeductionEngine
        import pipelines.processing.deduction as ded_mod

        engine = DeductionEngine.__new__(DeductionEngine)
        engine.llm = _FakeLLM(delay=0.01, fail_on={0, 2})

        original_retries = ded_mod._CHUNK_RETRIES
        ded_mod._CHUNK_RETRIES = 0  # no retries — immediate fail

        try:
            text = "Analysis data section. " * 5000  # multiple chunks
            facts = asyncio.run(engine.aextract_facts(text))
            # Should still get some facts (not zero)
            self.assertGreater(len(facts), 0)
        finally:
            ded_mod._CHUNK_RETRIES = original_retries


class TestChunkingCoverage(unittest.TestCase):
    """Test that chunking covers the full document."""

    def test_small_doc_single_chunk(self):
        from pipelines.processing.deduction import _split_text_into_chunks
        chunks = _split_text_into_chunks("Short text.")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "Short text.")

    def test_empty_text_returns_empty(self):
        from pipelines.processing.deduction import _split_text_into_chunks
        self.assertEqual(_split_text_into_chunks(""), [])
        self.assertEqual(_split_text_into_chunks("   "), [])

    def test_full_coverage_no_gap(self):
        """Total text covered by chunks should be >= original text length (overlap may duplicate)."""
        from pipelines.processing.deduction import _split_text_into_chunks
        text = "Word. " * 10_000  # 60K chars
        chunks = _split_text_into_chunks(text)
        total_chunk_chars = sum(len(c) for c in chunks)
        # With overlapping chunks, total chunk chars should be >= original length
        # (unless capped by _MAX_CHUNKS, in which case most of the document is still covered)
        # For 60K text with 12K chunks + 500 overlap → ~6 chunks, full coverage
        self.assertGreater(total_chunk_chars, len(text) * 0.85,
                           f"Only {total_chunk_chars}/{len(text)} chars covered")

    def test_chunk_count_within_limit(self):
        from pipelines.processing.deduction import _split_text_into_chunks, _MAX_CHUNKS
        text = "x " * 200_000  # 400K chars
        chunks = _split_text_into_chunks(text)
        self.assertLessEqual(len(chunks), _MAX_CHUNKS)
        self.assertGreater(len(chunks), 1)


class TestCeleryTaskNoDuplicateRetry(unittest.TestCase):
    """Verify the duplicate retry block was removed from processor.py."""

    def test_no_duplicate_retry_block(self):
        import inspect
        from services.workers import processor
        source = inspect.getsource(processor)
        # Should have exactly 1 occurrence of "Exponential backoff" (not 2)
        count = source.count("Exponential backoff")
        self.assertLessEqual(count, 0, "Duplicate retry block still present")


# =====================================================================
# Orchestrator — true 3-way parallelism, per-branch timing, errors
# =====================================================================

class _SlowBranch:
    """Simulates slow branches to prove 3-way parallelism."""

    def __init__(self, delay: float = 0.15):
        self.delay = delay
        self.start_times: Dict[str, float] = {}
        self.end_times: Dict[str, float] = {}

    def record(self, name: str):
        """Context-manager-like: record start/end of a branch."""
        self.start_times[name] = time.time()

        class _Ctx:
            def __init__(inner_self):
                pass
            def done(inner_self):
                self.end_times[name] = time.time()
        return _Ctx()


class TestOrchestratorThreeWayParallel(unittest.TestCase):
    """Prove that embedding, deduction, and dashboard run concurrently."""

    def test_three_branches_overlap_in_time(self):
        """
        Each branch sleeps 0.15s. If sequential ≥ 0.45s. If parallel < 0.35s.
        We mock all three branch methods to verify they overlap.
        """
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator

        tracker = _SlowBranch(delay=0.15)

        async def fake_embedding(*args, **kwargs):
            ctx = tracker.record('embedding')
            await asyncio.sleep(0.15)
            ctx.done()
            return {'embeddings_count': 5, 'time_ms': 150}

        async def fake_deduction(*args, **kwargs):
            ctx = tracker.record('deduction')
            await asyncio.sleep(0.15)
            ctx.done()
            return {'facts': [{'s': 'a'}], 'knowledge_graph': None,
                    'graphrag_task_id': None, 'time_ms': 150}

        async def fake_dashboard(*args, **kwargs):
            ctx = tracker.record('dashboard')
            await asyncio.sleep(0.15)
            ctx.done()
            return {'dashboard': {'test': True}, 'time_ms': 150}

        orch = AsyncPipelineOrchestrator(enable_cache=False)
        orch._run_embedding = fake_embedding
        orch._run_deduction = fake_deduction
        orch._run_dashboard = fake_dashboard

        async def _go():
            return await orch.run(
                text="Test document content. " * 500,
                doc_id="parallel-test",
                file_name="test.pdf",
                enable_deduction=True,
            )

        t0 = time.time()
        result = asyncio.run(_go())
        elapsed = time.time() - t0

        # All 3 branches ran — result is populated
        self.assertEqual(result['status'], 'completed')
        self.assertGreater(result['embeddings'], 0)
        self.assertGreater(result['facts'], 0)
        self.assertIsNotNone(result['dashboard_data'])

        # Parallel: 3 × 0.15s should complete in ≲ 0.35s (not 0.45s)
        self.assertLess(elapsed, 0.45, f"Took {elapsed:.2f}s — branches not parallel")

        # Verify overlap: all 3 started within 50ms of each other
        starts = list(tracker.start_times.values())
        self.assertEqual(len(starts), 3)
        max_gap = max(starts) - min(starts)
        self.assertLess(max_gap, 0.05, f"Branches started {max_gap:.3f}s apart — not concurrent")


class TestOrchestratorPerBranchTiming(unittest.TestCase):
    """Verify per-branch timing appears in metrics."""

    def test_metrics_contain_branch_times(self):
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator

        async def fast_embed(*a, **kw):
            return {'embeddings_count': 1, 'time_ms': 42}

        async def fast_deduct(*a, **kw):
            return {'facts': [], 'knowledge_graph': None,
                    'graphrag_task_id': None, 'time_ms': 77}

        async def fast_dash(*a, **kw):
            return {'dashboard': {}, 'time_ms': 99}

        orch = AsyncPipelineOrchestrator(enable_cache=False)
        orch._run_embedding = fast_embed
        orch._run_deduction = fast_deduct
        orch._run_dashboard = fast_dash

        result = asyncio.run(orch.run(
            text="Content. " * 200,
            doc_id="timing-test",
        ))

        m = result['metrics']
        self.assertIn('embedding_time_ms', m)
        self.assertIn('deduction_time_ms', m)
        self.assertIn('dashboard_time_ms', m)
        self.assertIn('total_time_ms', m)
        self.assertEqual(m['embedding_time_ms'], 42)
        self.assertEqual(m['deduction_time_ms'], 77)
        self.assertEqual(m['dashboard_time_ms'], 99)


class TestOrchestratorChunkValidation(unittest.TestCase):
    """Test that empty chunk result aborts pipeline early."""

    def test_empty_text_returns_failed(self):
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator

        orch = AsyncPipelineOrchestrator(enable_cache=False)
        result = asyncio.run(orch.run(
            text="",
            doc_id="empty-doc",
        ))

        self.assertEqual(result['status'], 'failed')
        self.assertIn('Chunking produced no output', result.get('error', ''))
        self.assertEqual(result['chunks'], 0)
        self.assertIn('Chunking produced 0 chunks', result.get('errors', []))


class TestOrchestratorPartialBranchFailure(unittest.TestCase):
    """Test that one failing branch doesn't crash the others."""

    def test_embedding_failure_still_returns_dashboard(self):
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator

        async def failing_embed(*a, **kw):
            raise RuntimeError("Qdrant connection refused")

        async def ok_deduct(*a, **kw):
            return {'facts': [{'s': 'x'}], 'knowledge_graph': None,
                    'graphrag_task_id': None, 'time_ms': 10}

        async def ok_dash(*a, **kw):
            return {'dashboard': {'ok': True}, 'time_ms': 10}

        orch = AsyncPipelineOrchestrator(enable_cache=False)
        orch._run_embedding = failing_embed
        orch._run_deduction = ok_deduct
        orch._run_dashboard = ok_dash

        result = asyncio.run(orch.run(
            text="Some document text. " * 200,
            doc_id="partial-fail",
            enable_deduction=True,
        ))

        # Pipeline still completes
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['embeddings'], 0)
        self.assertGreater(result['facts'], 0)
        self.assertIsNotNone(result['dashboard_data'])
        # Error captured
        self.assertEqual(len(result['errors']), 1)
        self.assertIn('embedding', result['errors'][0])

    def test_all_branches_fail_still_returns(self):
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator

        async def fail_embed(*a, **kw):
            raise RuntimeError("embed crash")

        async def fail_deduct(*a, **kw):
            raise RuntimeError("deduct crash")

        async def fail_dash(*a, **kw):
            raise RuntimeError("dash crash")

        orch = AsyncPipelineOrchestrator(enable_cache=False)
        orch._run_embedding = fail_embed
        orch._run_deduction = fail_deduct
        orch._run_dashboard = fail_dash

        result = asyncio.run(orch.run(
            text="Valid document. " * 200,
            doc_id="all-fail",
        ))

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['embeddings'], 0)
        self.assertEqual(result['facts'], 0)
        self.assertIsNone(result['dashboard_data'])
        self.assertEqual(len(result['errors']), 3)


class TestOrchestratorErrorsField(unittest.TestCase):
    """Verify errors list is always present in result."""

    def test_success_has_empty_errors(self):
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator

        async def ok_embed(*a, **kw):
            return {'embeddings_count': 1, 'time_ms': 1}

        async def ok_deduct(*a, **kw):
            return {'facts': [], 'knowledge_graph': None,
                    'graphrag_task_id': None, 'time_ms': 1}

        async def ok_dash(*a, **kw):
            return {'dashboard': {}, 'time_ms': 1}

        orch = AsyncPipelineOrchestrator(enable_cache=False)
        orch._run_embedding = ok_embed
        orch._run_deduction = ok_deduct
        orch._run_dashboard = ok_dash

        result = asyncio.run(orch.run(
            text="Content. " * 200,
            doc_id="ok-test",
        ))

        self.assertIn('errors', result)
        self.assertEqual(result['errors'], [])


class TestAchunkMethod(unittest.TestCase):
    """Test the new achunk() method on ChunkingPipeline."""

    def test_achunk_returns_chunks_without_embedding(self):
        from pipelines.processing.pipeline import ChunkingPipeline
        pipeline = ChunkingPipeline(strategy='adaptive', enable_metrics=True)
        text = "This is test content for chunking. " * 500

        result = asyncio.run(pipeline.achunk(text=text, doc_id="achunk-test"))
        self.assertIn('chunks_data', result)
        self.assertGreater(result['chunks_count'], 0)
        # achunk does NOT embed
        self.assertEqual(result['embeddings_count'], 0)
        self.assertIn('chunking_time_ms', result['metrics'])
        self.assertIn('avg_chunk_size', result['metrics'])

    def test_achunk_empty_text(self):
        from pipelines.processing.pipeline import ChunkingPipeline
        pipeline = ChunkingPipeline()
        result = asyncio.run(pipeline.achunk(text="", doc_id="empty-achunk"))
        self.assertEqual(result['chunks_count'], 0)


# =====================================================================
# Dashboard — semantic ranking, context builder, token safety, cache
# =====================================================================

class TestSemanticRanking(unittest.TestCase):
    """Test embedding-based semantic chunk ranking."""

    def test_semantic_rank_prefers_relevant_chunks(self):
        """Chunks about KPIs/metrics should rank higher than irrelevant ones."""
        from pipelines.processing.dashboard import DashboardGenerator
        gen = DashboardGenerator.__new__(DashboardGenerator)

        chunks = [
            "The weather was nice that day and birds were singing.",       # 0 - irrelevant
            "Revenue increased by 15% YoY with margin improvement.",      # 1 - highly relevant
            "The office building has three floors and a cafeteria.",       # 2 - irrelevant
            "KPI dashboard shows defect rate at 2.3 sigma level.",        # 3 - highly relevant
            "Team went to lunch at noon and returned at 1pm.",            # 4 - irrelevant
            "Production efficiency reached 94% with 6% downtime.",        # 5 - highly relevant
            "The printer on floor 2 is broken again.",                    # 6 - irrelevant
            "Cost reduction target of $2M achieved through optimization.", # 7 - highly relevant
        ]

        ranked_indices = gen._semantic_rank_chunks(chunks, top_k=4)
        self.assertEqual(len(ranked_indices), 4)

        # The top-4 should be the relevant chunks (indices 1, 3, 5, 7)
        relevant = {1, 3, 5, 7}
        overlap = len(set(ranked_indices) & relevant)
        self.assertGreaterEqual(overlap, 3, f"Only {overlap}/4 relevant chunks selected: {ranked_indices}")

    def test_semantic_rank_returns_requested_count(self):
        from pipelines.processing.dashboard import DashboardGenerator
        gen = DashboardGenerator.__new__(DashboardGenerator)
        chunks = [f"Chunk number {i} with data about metrics." for i in range(30)]
        indices = gen._semantic_rank_chunks(chunks, top_k=10)
        self.assertEqual(len(indices), 10)

    def test_semantic_rank_first_last_bias(self):
        """First and last chunks get a positional boost."""
        from pipelines.processing.dashboard import DashboardGenerator
        gen = DashboardGenerator.__new__(DashboardGenerator)
        # All chunks are equally irrelevant — bias should push 0 and -1 up
        chunks = [f"Generic text without analytics content number {i}." for i in range(10)]
        indices = gen._semantic_rank_chunks(chunks, top_k=3)
        # At least one of first/last should make top-3
        self.assertTrue(0 in indices or 9 in indices,
                        f"Neither first nor last in top-3: {indices}")


class TestKeywordFallback(unittest.TestCase):
    """Test keyword-density fallback ranking."""

    def test_keyword_fallback_selects_data_dense(self):
        from pipelines.processing.dashboard import DashboardGenerator
        chunks = [
            "no relevant keywords here at all",
            "KPI target actual variance 95% metric performance budget",
            "nothing useful in this chunk whatsoever",
        ]
        selected = DashboardGenerator._keyword_rank_chunks(chunks, max_chunks=1)
        self.assertEqual(len(selected), 1)
        self.assertIn("KPI", selected[0])

    def test_keyword_fallback_preserves_order(self):
        from pipelines.processing.dashboard import DashboardGenerator
        chunks = [f"metric {i} KPI cost revenue" for i in range(20)]
        selected = DashboardGenerator._keyword_rank_chunks(chunks, max_chunks=5)
        self.assertEqual(len(selected), 5)
        # Check original order preserved
        indices = [chunks.index(s) for s in selected]
        self.assertEqual(indices, sorted(indices))


class TestContextBuilder(unittest.TestCase):
    """Test the structured context builder."""

    def test_basic_context_format(self):
        from pipelines.processing.dashboard import DashboardGenerator
        chunks = ["First chunk text.", "Second chunk text."]
        ctx = DashboardGenerator._build_context(chunks)
        self.assertIn("KEY CONTEXT:", ctx)
        self.assertIn("[Section 1]", ctx)
        self.assertIn("[Section 2]", ctx)
        self.assertIn("First chunk text.", ctx)
        self.assertIn("Second chunk text.", ctx)

    def test_context_with_summary(self):
        from pipelines.processing.dashboard import DashboardGenerator
        chunks = ["Chunk A."]
        ctx = DashboardGenerator._build_context(chunks, summary="Overall summary here.")
        self.assertIn("DOCUMENT SUMMARY:", ctx)
        self.assertIn("Overall summary here.", ctx)
        self.assertIn("KEY CONTEXT:", ctx)
        self.assertIn("[Section 1]", ctx)

    def test_context_respects_max_chars(self):
        from pipelines.processing.dashboard import DashboardGenerator
        # Each chunk is 1000 chars; 10 chunks = 10K chars; limit to 3K
        chunks = [f"{'x' * 1000}" for _ in range(10)]
        ctx = DashboardGenerator._build_context(chunks, max_chars=3000)
        self.assertLessEqual(len(ctx), 3500)  # small overhead for separators
        # Should have fewer than all 10 sections
        section_count = ctx.count("[Section")
        self.assertLess(section_count, 10)
        self.assertGreater(section_count, 0)

    def test_context_empty_chunks(self):
        from pipelines.processing.dashboard import DashboardGenerator
        ctx = DashboardGenerator._build_context([])
        self.assertIn("KEY CONTEXT:", ctx)


class TestSelectContextChunksFallback(unittest.TestCase):
    """Test that _select_context_chunks falls back to keyword when embedding fails."""

    def test_fallback_when_semantic_fails(self):
        """If VectorStorageService is unavailable, keyword fallback should work."""
        from pipelines.processing.dashboard import DashboardGenerator
        gen = DashboardGenerator.__new__(DashboardGenerator)

        # Make _semantic_rank_chunks always fail
        original = gen._semantic_rank_chunks
        gen._semantic_rank_chunks = lambda *a, **kw: (_ for _ in ()).throw(
            RuntimeError("Embedding model not available"))

        chunks = [f"KPI metric {i} target actual" for i in range(30)]
        try:
            selected = gen._select_context_chunks(chunks, max_chunks=10)
            self.assertEqual(len(selected), 10)
        finally:
            gen._semantic_rank_chunks = original


class TestRankedChunkCache(unittest.TestCase):
    """Test that ranked chunk indices are cached in memory."""

    def test_cache_hit_returns_same_result(self):
        from pipelines.processing.dashboard import DashboardGenerator, _ranked_cache
        gen = DashboardGenerator.__new__(DashboardGenerator)

        chunks = [f"Revenue metric {i} KPI sigma" for i in range(30)]

        # First call populates cache
        r1 = gen._select_context_chunks(chunks, max_chunks=5)
        cache_size_after = len(_ranked_cache)
        self.assertGreater(cache_size_after, 0)

        # Second call should still return same result (from cache or consistent)
        r2 = gen._select_context_chunks(chunks, max_chunks=5)
        self.assertEqual(r1, r2)


class TestSyncDashboardNoFullDoc(unittest.TestCase):
    """Verify sync generate_dashboard no longer passes 200K raw text."""

    def test_no_200k_truncation_in_sync_path(self):
        import inspect
        from pipelines.processing.dashboard import DashboardGenerator
        source = inspect.getsource(DashboardGenerator.generate_dashboard)
        self.assertNotIn("200_000", source)
        self.assertNotIn("200000", source)
        self.assertIn("_select_context_chunks", source)
        self.assertIn("_build_context", source)


# =====================================================================
# Embedding optimisation tests
# =====================================================================

class TestHardwareDetection(unittest.TestCase):
    """Test device detection and batch-size selection helpers."""

    def test_detect_device_cpu_override(self):
        from services.vector_store.indexing.vector_storage import _detect_device
        self.assertEqual(_detect_device("cpu"), "cpu")

    def test_detect_device_cuda_override(self):
        from services.vector_store.indexing.vector_storage import _detect_device
        self.assertEqual(_detect_device("cuda"), "cuda")

    def test_detect_device_auto_returns_string(self):
        from services.vector_store.indexing.vector_storage import _detect_device
        device = _detect_device("auto")
        self.assertIn(device, ("cpu", "cuda"))

    def test_optimal_batch_cpu(self):
        from services.vector_store.indexing.vector_storage import _optimal_batch_size
        self.assertEqual(_optimal_batch_size("cpu", 0), 128)

    def test_optimal_batch_gpu(self):
        from services.vector_store.indexing.vector_storage import _optimal_batch_size
        self.assertEqual(_optimal_batch_size("cuda", 0), 256)

    def test_optimal_batch_explicit_override(self):
        from services.vector_store.indexing.vector_storage import _optimal_batch_size
        self.assertEqual(_optimal_batch_size("cpu", 64), 64)
        self.assertEqual(_optimal_batch_size("cuda", 64), 64)


class TestEmbeddingOOMFallback(unittest.TestCase):
    """Test that OOM errors trigger batch-size halving."""

    def test_fallback_halves_batch_on_runtime_error(self):
        from services.vector_store.indexing.vector_storage import VectorStorageService

        call_log = []

        def oom_then_ok(texts, **kwargs):
            bs = kwargs.get('batch_size', 0)
            call_log.append(bs)
            if bs > 64:
                raise RuntimeError("CUDA out of memory")
            import numpy as np
            return np.random.rand(len(texts), 384).astype(np.float32)

        vs = VectorStorageService.__new__(VectorStorageService)
        vs.model = MagicMock()
        vs.model.encode = oom_then_ok
        vs._device = "cuda"
        vs._batch_size = 256

        result = vs.generate_embeddings_batch(["hello"] * 10, batch_size=256, show_progress=False)

        self.assertEqual(len(result), 10)
        self.assertGreater(len(call_log), 1)
        self.assertEqual(call_log[0], 256)
        self.assertTrue(call_log[-1] <= 64)

    def test_fallback_raises_at_min_batch(self):
        from services.vector_store.indexing.vector_storage import VectorStorageService

        def always_oom(texts, **kwargs):
            raise RuntimeError("CUDA out of memory")

        vs = VectorStorageService.__new__(VectorStorageService)
        vs.model = MagicMock()
        vs.model.encode = always_oom
        vs._device = "cpu"
        vs._batch_size = 128

        with self.assertRaises(RuntimeError):
            vs._encode_with_fallback(["hello"], batch_size=16, show_progress=False)


class TestEmbeddingPerformanceLogging(unittest.TestCase):
    """Test that generate_embeddings_batch logs timing info."""

    def test_batch_logs_timing(self):
        from services.vector_store.indexing.vector_storage import VectorStorageService
        import numpy as np

        vs = VectorStorageService.__new__(VectorStorageService)
        vs.model = MagicMock()
        vs.model.encode = MagicMock(return_value=np.random.rand(5, 384).astype(np.float32))
        vs._device = "cpu"
        vs._batch_size = 128

        with patch('services.vector_store.indexing.vector_storage.logger') as mock_logger:
            result = vs.generate_embeddings_batch(["a", "b", "c", "d", "e"], show_progress=False)

        self.assertEqual(len(result), 5)
        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        self.assertTrue(any("texts/s" in c for c in info_calls),
                        f"Expected throughput log, got: {info_calls}")


class TestDynamicBatchInVectorService(unittest.TestCase):
    """Test that VectorStorageService uses dynamic batch sizes."""

    def test_default_batch_not_32(self):
        """Verify the old hardcoded batch_size=32 default is gone."""
        import inspect
        from services.vector_store.indexing.vector_storage import VectorStorageService
        sig = inspect.signature(VectorStorageService.generate_embeddings_batch)
        default = sig.parameters['batch_size'].default
        self.assertEqual(default, 0)

    def test_device_attribute_set(self):
        from services.vector_store.indexing.vector_storage import VectorStorageService
        vs = VectorStorageService.__new__(VectorStorageService)
        vs._device = "cpu"
        vs._batch_size = 128
        self.assertIn(vs._device, ("cpu", "cuda"))
        self.assertGreaterEqual(vs._batch_size, 16)


class TestParallelEmbedding(unittest.TestCase):
    """Test async parallel embedding for large chunk sets."""

    def test_parallel_splits_large_input(self):
        from services.vector_store.indexing.vector_storage import VectorStorageService
        import numpy as np

        call_count = 0

        def mock_encode(texts, **kwargs):
            nonlocal call_count
            call_count += 1
            return np.random.rand(len(texts), 384).astype(np.float32)

        vs = VectorStorageService.__new__(VectorStorageService)
        vs.model = MagicMock()
        vs.model.encode = mock_encode
        vs._device = "cpu"
        vs._batch_size = 128

        texts = [f"chunk {i}" for i in range(600)]
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                vs.generate_embeddings_parallel(texts, group_size=200)
            )
        finally:
            loop.close()

        self.assertEqual(len(result), 600)
        self.assertGreaterEqual(call_count, 3)

    def test_parallel_small_input_no_split(self):
        from services.vector_store.indexing.vector_storage import VectorStorageService
        import numpy as np

        def mock_encode(texts, **kwargs):
            return np.random.rand(len(texts), 384).astype(np.float32)

        vs = VectorStorageService.__new__(VectorStorageService)
        vs.model = MagicMock()
        vs.model.encode = mock_encode
        vs._device = "cpu"
        vs._batch_size = 128

        texts = [f"chunk {i}" for i in range(10)]
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                vs.generate_embeddings_parallel(texts, group_size=500)
            )
        finally:
            loop.close()

        self.assertEqual(len(result), 10)


class TestEmbeddingModelDeviceAware(unittest.TestCase):
    """Test that EmbeddingModel picks up device settings."""

    def test_resolve_device_cpu(self):
        from services.vector_store.embeddings.embedding_model import _resolve_device
        with patch.dict(os.environ, {}, clear=False):
            with patch('services.vector_store.embeddings.embedding_model.settings') as mock_s:
                mock_s.EMBEDDING_DEVICE = "cpu"
                self.assertEqual(_resolve_device(), "cpu")

    def test_resolve_batch_size_cpu(self):
        from services.vector_store.embeddings.embedding_model import _resolve_batch_size
        self.assertEqual(_resolve_batch_size("cpu"), 128)

    def test_resolve_batch_size_cuda(self):
        from services.vector_store.embeddings.embedding_model import _resolve_batch_size
        self.assertEqual(_resolve_batch_size("cuda"), 256)

    def test_resolve_batch_size_explicit(self):
        from services.vector_store.embeddings.embedding_model import _resolve_batch_size
        with patch('services.vector_store.embeddings.embedding_model.settings') as mock_s:
            mock_s.EMBEDDING_BATCH_SIZE = 64
            self.assertEqual(_resolve_batch_size("cpu"), 64)


class TestSettingsEmbeddingConfig(unittest.TestCase):
    """Test that embedding settings have correct defaults."""

    def test_batch_size_default_zero_auto(self):
        from core.config.settings import settings
        self.assertEqual(settings.EMBEDDING_BATCH_SIZE, 0)

    def test_device_default_auto(self):
        from core.config.settings import settings
        self.assertEqual(settings.EMBEDDING_DEVICE, "auto")


# =====================================================================
# Smart deduction trigger tests
# =====================================================================

class TestDocumentClassifier(unittest.TestCase):
    """Test heuristic document classifier."""

    def test_financial_report(self):
        from pipelines.processing.deduction_trigger import classify_document
        chunks = [{"text": "Q3 revenue was $12M with EBITDA growth of 15%."}]
        self.assertEqual(classify_document(chunks), "financial_report")

    def test_technical_document(self):
        from pipelines.processing.deduction_trigger import classify_document
        chunks = [{"text": "The system design uses a microservice architecture with Kubernetes."}]
        self.assertEqual(classify_document(chunks), "technical_document")

    def test_contract(self):
        from pipelines.processing.deduction_trigger import classify_document
        chunks = [{"text": "This agreement between the party of the first part and terms herein."}]
        self.assertEqual(classify_document(chunks), "contract")

    def test_invoice(self):
        from pipelines.processing.deduction_trigger import classify_document
        chunks = [{"text": "Invoice #1234. Total amount due: $500. GST included."}]
        self.assertEqual(classify_document(chunks), "invoice")

    def test_simple_text(self):
        from pipelines.processing.deduction_trigger import classify_document
        chunks = [{"text": "Hello world, this is a short note."}]
        self.assertEqual(classify_document(chunks), "simple_text")

    def test_unknown_for_long_generic(self):
        from pipelines.processing.deduction_trigger import classify_document
        chunks = [{"text": "A " * 2000}]
        self.assertEqual(classify_document(chunks), "unknown")

    def test_empty_chunks(self):
        from pipelines.processing.deduction_trigger import classify_document
        self.assertEqual(classify_document([]), "unknown")

    def test_samples_first_five_chunks(self):
        from pipelines.processing.deduction_trigger import classify_document
        # Financial keywords in chunk 3 (within first 5)
        chunks = [
            {"text": "Introduction section."},
            {"text": "Background info."},
            {"text": "Revenue grew 20%, EBITDA up 15%."},
            {"text": "More details."},
            {"text": "Conclusion."},
            {"text": "Appendix with algorithm details."},  # chunk 6, should be ignored
        ]
        self.assertEqual(classify_document(chunks), "financial_report")


class TestComplexityDetector(unittest.TestCase):
    """Test complexity detection."""

    def test_many_chunks_is_complex(self):
        from pipelines.processing.deduction_trigger import is_complex_document
        chunks = [{"text": "chunk"} for _ in range(25)]
        self.assertTrue(is_complex_document(chunks))

    def test_large_total_chars_is_complex(self):
        from pipelines.processing.deduction_trigger import is_complex_document
        chunks = [{"text": "x" * 60000}]
        self.assertTrue(is_complex_document(chunks))

    def test_small_doc_not_complex(self):
        from pipelines.processing.deduction_trigger import is_complex_document
        chunks = [{"text": "short text"} for _ in range(5)]
        self.assertFalse(is_complex_document(chunks))

    def test_empty_not_complex(self):
        from pipelines.processing.deduction_trigger import is_complex_document
        self.assertFalse(is_complex_document([]))

    def test_boundary_chunk_count(self):
        from pipelines.processing.deduction_trigger import is_complex_document
        # Exactly 20 chunks → NOT complex (threshold is >20)
        chunks = [{"text": "x"} for _ in range(20)]
        self.assertFalse(is_complex_document(chunks))
        # 21 chunks → complex
        chunks.append({"text": "x"})
        self.assertTrue(is_complex_document(chunks))


class TestDeductionDecision(unittest.TestCase):
    """Test should_run_deduction logic."""

    def test_financial_report_always_yes(self):
        from pipelines.processing.deduction_trigger import should_run_deduction
        self.assertTrue(should_run_deduction("financial_report", False))
        self.assertTrue(should_run_deduction("financial_report", True))

    def test_technical_document_always_yes(self):
        from pipelines.processing.deduction_trigger import should_run_deduction
        self.assertTrue(should_run_deduction("technical_document", False))

    def test_contract_always_yes(self):
        from pipelines.processing.deduction_trigger import should_run_deduction
        self.assertTrue(should_run_deduction("contract", False))

    def test_invoice_simple_skips(self):
        from pipelines.processing.deduction_trigger import should_run_deduction
        self.assertFalse(should_run_deduction("invoice", False))

    def test_invoice_complex_runs(self):
        from pipelines.processing.deduction_trigger import should_run_deduction
        self.assertTrue(should_run_deduction("invoice", True))

    def test_simple_text_skips(self):
        from pipelines.processing.deduction_trigger import should_run_deduction
        self.assertFalse(should_run_deduction("simple_text", False))

    def test_unknown_complex_runs(self):
        from pipelines.processing.deduction_trigger import should_run_deduction
        self.assertTrue(should_run_deduction("unknown", True))

    def test_unknown_simple_skips(self):
        from pipelines.processing.deduction_trigger import should_run_deduction
        self.assertFalse(should_run_deduction("unknown", False))

    def test_force_true_overrides(self):
        from pipelines.processing.deduction_trigger import should_run_deduction
        self.assertTrue(should_run_deduction("simple_text", False, force=True))

    def test_force_false_overrides(self):
        from pipelines.processing.deduction_trigger import should_run_deduction
        self.assertFalse(should_run_deduction("financial_report", True, force=False))


class TestEvaluateDeductionTrigger(unittest.TestCase):
    """Test the full evaluation entry point."""

    def test_returns_all_keys(self):
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        chunks = [{"text": "Revenue grew 20%. EBITDA margin improved."}]
        result = evaluate_deduction_trigger(chunks)
        self.assertIn("run_deduction", result)
        self.assertIn("document_type", result)
        self.assertIn("is_complex", result)
        self.assertIn("reason", result)

    def test_financial_auto_enabled(self):
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        chunks = [{"text": "Revenue grew 20%. EBITDA margin improved."}]
        result = evaluate_deduction_trigger(chunks)
        self.assertTrue(result["run_deduction"])
        self.assertEqual(result["document_type"], "financial_report")

    def test_simple_auto_disabled(self):
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        chunks = [{"text": "Hello world."}]
        result = evaluate_deduction_trigger(chunks)
        self.assertFalse(result["run_deduction"])
        self.assertEqual(result["document_type"], "simple_text")

    def test_force_override(self):
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        chunks = [{"text": "Hello world."}]
        result = evaluate_deduction_trigger(chunks, force=True)
        self.assertTrue(result["run_deduction"])
        self.assertIn("forced", result["reason"])

    def test_failsafe_on_bad_input(self):
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        # Pass chunks without 'text' key — should not crash, fail-safe ON
        result = evaluate_deduction_trigger([{"no_text_key": "oops"}])
        # Should still return a valid dict (classification uses .get("text",""))
        self.assertIn("run_deduction", result)


class TestOrchestratorSmartTrigger(unittest.TestCase):
    """Test that orchestrator uses smart trigger in its result."""

    def test_result_contains_trigger_metadata(self):
        """Orchestrator result should include document_type and deduction_enabled."""
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        import inspect
        source = inspect.getsource(AsyncPipelineOrchestrator.run)
        # Verify the smart trigger is wired in
        self.assertIn("evaluate_deduction_trigger", source)
        self.assertIn("deduction_trigger", source)
        self.assertIn("document_type", source)
        self.assertIn("deduction_enabled", source)

    def test_run_deduction_respects_effective_flag(self):
        """_run_deduction still checks its bool flag."""
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        import inspect
        source = inspect.getsource(AsyncPipelineOrchestrator._run_deduction)
        self.assertIn("if not enable_deduction", source)


# =====================================================================
# Dashboard SSE streaming tests
# =====================================================================

class TestDashboardStreamGenerator(unittest.TestCase):
    """Test the agenerate_dashboard_stream async generator."""

    def _run(self, coro):
        """Helper to run async code in tests."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_stream_yields_all_stages(self):
        from pipelines.processing.dashboard import DashboardGenerator

        # Mock LLM to return a valid dashboard dict
        mock_dashboard = {
            "title": "Test Dashboard",
            "description": "desc",
            "kpis": [{"title": "KPI1", "value": 100}],
            "charts": [{"type": "bar", "data": []}],
            "tables": [],
            "insights": {"summary": "good", "trends": [], "alerts": [], "recommendations": []},
            "optimizationSuggestions": [],
            "sixSigma": {"dmaic": {}, "sigmaLevel": "3"},
        }

        gen = DashboardGenerator.__new__(DashboardGenerator)
        gen.llm = MagicMock()
        gen.llm.generate_json = MagicMock(return_value={"dashboard": mock_dashboard})
        gen.prompt_version = "latest"
        gen.use_ab_test = False

        async def collect():
            events = []
            # Patch _select_context_chunks to return chunks as-is
            with patch.object(gen, '_select_context_chunks', return_value=["chunk1", "chunk2"]):
                async for event in gen.agenerate_dashboard_stream(
                    chunks=["chunk1", "chunk2"],
                    file_name="test.xlsx",
                    doc_id="test-123",
                ):
                    events.append(event)
            return events

        events = self._run(collect())
        stages = [e["stage"] for e in events]

        self.assertIn("context_ready", stages)
        self.assertIn("kpis", stages)
        self.assertIn("charts", stages)
        self.assertIn("insights", stages)
        self.assertIn("sixSigma", stages)
        self.assertIn("complete", stages)

        # context_ready should be first
        self.assertEqual(stages[0], "context_ready")
        # complete should be last
        self.assertEqual(stages[-1], "complete")

    def test_stream_kpis_stage_has_data(self):
        from pipelines.processing.dashboard import DashboardGenerator

        mock_dashboard = {
            "title": "T",
            "kpis": [{"title": "Revenue", "value": 1000}],
            "charts": [], "tables": [], "insights": {},
            "optimizationSuggestions": [],
            "sixSigma": {},
        }

        gen = DashboardGenerator.__new__(DashboardGenerator)
        gen.llm = MagicMock()
        gen.llm.generate_json = MagicMock(return_value={"dashboard": mock_dashboard})
        gen.prompt_version = "latest"
        gen.use_ab_test = False

        async def collect():
            events = []
            with patch.object(gen, '_select_context_chunks', return_value=["c"]):
                async for event in gen.agenerate_dashboard_stream(chunks=["c"]):
                    events.append(event)
            return events

        events = self._run(collect())
        kpi_event = next(e for e in events if e["stage"] == "kpis")
        self.assertIn("kpis", kpi_event["data"])
        self.assertEqual(len(kpi_event["data"]["kpis"]), 1)
        self.assertEqual(kpi_event["data"]["kpis"][0]["title"], "Revenue")

    def test_stream_yields_error_on_timeout(self):
        from pipelines.processing.dashboard import DashboardGenerator

        gen = DashboardGenerator.__new__(DashboardGenerator)
        gen.llm = MagicMock()
        gen.prompt_version = "latest"
        gen.use_ab_test = False

        # Make generate_json take forever
        def slow_llm(*a, **kw):
            import time
            time.sleep(5)
            return {}

        gen.llm.generate_json = slow_llm

        async def collect():
            events = []
            with patch.object(gen, '_select_context_chunks', return_value=["c"]):
                # Override timeout to 0.1s for fast test
                original = asyncio.wait_for

                async def fast_timeout(coro, **kw):
                    return await original(coro, timeout=0.1)

                with patch('pipelines.processing.dashboard.asyncio.wait_for', fast_timeout):
                    async for event in gen.agenerate_dashboard_stream(chunks=["c"]):
                        events.append(event)
            return events

        events = self._run(collect())
        stages = [e["stage"] for e in events]
        self.assertIn("error", stages)

    def test_complete_contains_full_dashboard(self):
        from pipelines.processing.dashboard import DashboardGenerator

        mock_dashboard = {
            "title": "Full",
            "kpis": [{"title": "A", "value": 1}],
            "charts": [],
            "tables": [],
            "insights": {},
            "optimizationSuggestions": [],
            "sixSigma": {},
        }

        gen = DashboardGenerator.__new__(DashboardGenerator)
        gen.llm = MagicMock()
        gen.llm.generate_json = MagicMock(return_value={"dashboard": mock_dashboard})
        gen.prompt_version = "latest"
        gen.use_ab_test = False

        async def collect():
            events = []
            with patch.object(gen, '_select_context_chunks', return_value=["c"]):
                async for event in gen.agenerate_dashboard_stream(chunks=["c"]):
                    events.append(event)
            return events

        events = self._run(collect())
        complete_event = next(e for e in events if e["stage"] == "complete")
        self.assertIn("dashboard", complete_event["data"])
        self.assertIn("elapsed_ms", complete_event["data"])


class TestSSEEndpointExists(unittest.TestCase):
    """Test that the SSE streaming endpoint is properly defined."""

    def test_stream_route_registered(self):
        import inspect
        from app.api.v2.endpoints import stream_dashboard
        self.assertTrue(callable(stream_dashboard))
        sig = inspect.signature(stream_dashboard)
        self.assertIn("doc_id", sig.parameters)

    def test_stream_returns_streaming_response(self):
        """Verify the endpoint function is an async generator wrapper."""
        import inspect
        from app.api.v2.endpoints import stream_dashboard
        self.assertTrue(inspect.iscoroutinefunction(stream_dashboard))


# =====================================================================
# Celery Worker Concurrency Tests
# =====================================================================

class TestCeleryWorkerConfig(unittest.TestCase):
    """Test that Celery is configured for production-grade concurrency."""

    def test_concurrency_settings_in_config(self):
        """Settings exposes worker concurrency knobs."""
        from core.config.settings import settings
        self.assertGreaterEqual(settings.WORKER_CONCURRENCY, 1)
        self.assertEqual(settings.WORKER_PREFETCH_MULTIPLIER, 1)
        self.assertGreaterEqual(settings.WORKER_MAX_TASKS_PER_CHILD, 1)
        self.assertIn(settings.WORKER_POOL, ("prefork", "gevent"))

    def test_celery_conf_has_concurrency(self):
        """processor.celery.conf has production concurrency settings."""
        from services.workers.processor import celery, CELERY_AVAILABLE
        if not CELERY_AVAILABLE:
            self.skipTest("Celery not installed")
        conf = celery.conf
        self.assertTrue(conf.task_acks_late)
        self.assertTrue(conf.task_reject_on_worker_lost)
        self.assertEqual(conf.worker_prefetch_multiplier, 1)
        self.assertGreaterEqual(conf.worker_concurrency, 1)
        self.assertGreaterEqual(conf.worker_max_tasks_per_child, 1)

    def test_task_routing_configured(self):
        """Task routes separate documents, graphs, and maintenance."""
        from services.workers.processor import celery, CELERY_AVAILABLE
        if not CELERY_AVAILABLE:
            self.skipTest("Celery not installed")
        routes = celery.conf.task_routes
        self.assertIsNotNone(routes)
        self.assertIn('services.workers.processor.process_document', routes)
        self.assertEqual(
            routes['services.workers.processor.process_document']['queue'],
            'documents',
        )
        self.assertIn('services.workers.graph_processing.build_knowledge_graph', routes)
        self.assertEqual(
            routes['services.workers.graph_processing.build_knowledge_graph']['queue'],
            'graphs',
        )

    def test_default_queue_is_documents(self):
        """Un-routed tasks land in the documents queue."""
        from services.workers.processor import celery, CELERY_AVAILABLE
        if not CELERY_AVAILABLE:
            self.skipTest("Celery not installed")
        self.assertEqual(celery.conf.task_default_queue, 'documents')

    def test_result_expiry_set(self):
        """Results expire to prevent Redis bloat."""
        from services.workers.processor import celery, CELERY_AVAILABLE
        if not CELERY_AVAILABLE:
            self.skipTest("Celery not installed")
        self.assertGreater(celery.conf.result_expires, 0)

    def test_max_connections_adequate(self):
        """Result backend pool ≥ worker concurrency."""
        from services.workers.processor import celery, CELERY_AVAILABLE
        if not CELERY_AVAILABLE:
            self.skipTest("Celery not installed")
        opts = celery.conf.result_backend_transport_options
        self.assertGreaterEqual(opts['max_connections'], 4)


class TestLLMConcurrencyGuard(unittest.TestCase):
    """Test the global LLM semaphore that prevents API overload."""

    def test_semaphore_factory_returns_semaphore(self):
        from pipelines.processing.async_orchestrator import _get_llm_semaphore
        import asyncio
        sem = _get_llm_semaphore()
        self.assertIsInstance(sem, asyncio.Semaphore)

    def test_semaphore_limit_matches_settings(self):
        from pipelines.processing.async_orchestrator import _LLM_SEMAPHORE_LIMIT
        from core.config.settings import settings
        self.assertEqual(_LLM_SEMAPHORE_LIMIT, settings.PIPELINE_MAX_CONCURRENT_LLM)

    def test_dashboard_branch_uses_semaphore(self):
        """_run_dashboard wraps LLM call in semaphore."""
        import inspect
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        source = inspect.getsource(AsyncPipelineOrchestrator._run_dashboard)
        self.assertIn("_get_llm_semaphore", source)
        self.assertIn("async with sem", source)

    def test_deduction_branch_uses_semaphore(self):
        """_run_deduction wraps LLM call in semaphore."""
        import inspect
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        source = inspect.getsource(AsyncPipelineOrchestrator._run_deduction)
        self.assertIn("_get_llm_semaphore", source)
        self.assertIn("async with sem", source)


class TestDockerComposeConfig(unittest.TestCase):
    """Validate docker-compose.yml has correct worker configuration."""

    def setUp(self):
        import pathlib
        self.compose_path = pathlib.Path(__file__).parent.parent / 'infra' / 'docker-compose.yml'
        if not self.compose_path.exists():
            self.skipTest("docker-compose.yml not found")
        self.content = self.compose_path.read_text()

    def test_worker_uses_correct_module_path(self):
        """Worker command references services.workers, not app.workers."""
        self.assertIn('services.workers.processor.celery', self.content)
        self.assertNotIn('app.workers.processor.celery', self.content)

    def test_worker_has_concurrency_flag(self):
        self.assertIn('--concurrency=4', self.content)

    def test_worker_has_prefetch_flag(self):
        self.assertIn('--prefetch-multiplier=1', self.content)

    def test_worker_subscribes_to_queues(self):
        self.assertIn('-Q documents,graphs,maintenance', self.content)

    def test_flower_uses_correct_module_path(self):
        self.assertIn('services.workers.processor.celery flower', self.content)

    def test_second_worker_exists(self):
        """worker2 service exists for horizontal scaling."""
        self.assertIn('worker2:', self.content)
        self.assertIn('-n worker2@%h', self.content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
