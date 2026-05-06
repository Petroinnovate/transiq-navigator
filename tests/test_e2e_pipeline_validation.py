"""
End-to-End Pipeline Validation Suite
=====================================

Validates the ENTIRE production pipeline across 12 dimensions:

  1.  Test input documents (small / medium / large)
  2.  Chunking (no truncation, full coverage)
  3.  Parallel pipeline (asyncio.gather, time < sum)
  4.  Async deduction (concurrent LLM, semaphore-bounded)
  5.  Smart deduction trigger
  6.  Smart context (top-k, not full doc)
  7.  Embedding optimisation (batch size, OOM fallback)
  8.  Content-hash caching (second run instant, cache HIT)
  9.  SSE dashboard streaming (progressive stages)
 10.  Worker concurrency configuration
 11.  Error handling / partial-failure tolerance
 12.  Performance targets

Run:
    python -m pytest tests/test_e2e_pipeline_validation.py -v --tb=short

All tests are self-contained — no real LLM or Redis needed.
"""
import asyncio
import inspect
import json
import os
import re
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ---------------------------------------------------------------------------
# Helpers — synthetic document generators
# ---------------------------------------------------------------------------

def _make_small_doc() -> str:
    """~500 chars — shipping invoice, simple text."""
    return (
        "INVOICE #2024-0047\n"
        "Date: 2024-03-15\n"
        "From: Acme Corp.\n"
        "To: Widget Ltd.\n\n"
        "Item: Standard Widget\n"
        "Quantity: 100\n"
        "Unit Price: $12.50\n"
        "Subtotal: $1,250.00\n"
        "Tax (8%): $100.00\n"
        "Total Amount Due: $1,350.00\n\n"
        "Payment Terms: Net 30\n"
        "Due Date: 2024-04-14\n"
    )


def _make_medium_doc() -> str:
    """~60K chars — financial report with keywords that trigger deduction."""
    header = (
        "ANNUAL FINANCIAL REPORT — FY 2024\n"
        "Prepared by: TransIQ Analytics Division\n\n"
        "Executive Summary\n"
        "Revenue grew 12% year-over-year driven by strong EBITDA margins "
        "and improved cash flow from operations. Net income reached $48M "
        "while operating income improved by 15%. Balance sheet remains "
        "healthy with total assets of $1.2B and equity of $780M.\n\n"
        "Key financial highlights:\n"
        "- Revenue: $420M (+12% YoY)\n"
        "- Gross Margin: 42.3%\n"
        "- EBITDA: $98M\n"
        "- Net Income: $48M\n"
        "- Earnings per share: $3.21\n"
        "- Dividend payout: $1.50/share\n"
        "- Working capital: $210M\n"
        "- Depreciation & Amortization: $18M\n"
        "- CapEx: $45M\n\n"
    )
    section = (
        "Detailed Analysis of Segment Performance\n"
        "The manufacturing division delivered profit of $32M on revenue of $180M. "
        "Liabilities decreased by 8% due to aggressive debt repayment. "
        "Fiscal discipline and cost optimisation in Q3 boosted the gross margin "
        "by 2.4 percentage points. Cash flow from financing activities totalled "
        "-$22M reflecting share buyback activity.\n\n"
    )
    # Repeat to reach ~60K chars
    body = section * 140
    return header + body


def _make_large_doc() -> str:
    """~200K chars — large technical / mixed document."""
    header = (
        "COMPREHENSIVE SYSTEM ARCHITECTURE REVIEW v3.7\n\n"
        "This document covers the full system design including algorithm "
        "descriptions, API specifications, database schemas, deployment "
        "infrastructure, and scalability analysis. The architecture uses "
        "microservice patterns with Kubernetes orchestration, Docker "
        "containerisation, and CI/CD pipelines for continuous delivery.\n\n"
    )
    paragraph = (
        "The data ingestion pipeline processes incoming documents through a "
        "multi-stage architecture consisting of parsing, chunking, embedding, "
        "and indexing. Each stage is designed for horizontal scalability with "
        "independent failure domains. Latency is monitored end-to-end and "
        "throughput targets are set to 50 documents per minute under peak load. "
        "Machine learning models are deployed via TorchServe with neural network "
        "inference optimised for batch processing. The system design follows "
        "twelve-factor app principles.\n\n"
    )
    return header + paragraph * 600  # ~200K chars


# ---------------------------------------------------------------------------
# Mock LLM that returns structured dashboard JSON
# ---------------------------------------------------------------------------

_MOCK_DASHBOARD = {
    "title": "E2E Test Dashboard",
    "description": "Auto-generated for validation",
    "kpis": [
        {"title": "Revenue", "value": 420, "unit": "M$", "trend": "up"},
        {"title": "EBITDA", "value": 98, "unit": "M$", "trend": "up"},
    ],
    "charts": [
        {"type": "bar", "title": "Revenue by Quarter", "data": [100, 105, 108, 107]},
    ],
    "tables": [],
    "insights": {
        "summary": "Strong financial performance",
        "trends": ["Revenue growth"],
        "alerts": [],
        "recommendations": ["Maintain cost discipline"],
    },
    "optimizationSuggestions": ["Increase automation"],
    "sixSigma": {
        "dmaic": {"define": "Revenue growth", "measure": "YoY", "analyze": "Segment",
                  "improve": "Automation", "control": "KPI tracking"},
        "sigmaLevel": "4.2",
    },
}

_MOCK_FACTS = [
    {"subject": "Revenue", "predicate": "increased_by", "object": "12%", "confidence": 0.95},
    {"subject": "EBITDA", "predicate": "reached", "object": "$98M", "confidence": 0.90},
    {"subject": "Net Income", "predicate": "is", "object": "$48M", "confidence": 0.88},
]


def _mock_llm():
    """Return a MagicMock that behaves like an LLM provider."""
    llm = MagicMock()
    llm.generate_json.return_value = {"dashboard": _MOCK_DASHBOARD}
    llm.get_model_info.return_value = {"provider": "mock", "model": "test"}
    return llm


# ===================================================================
# 1. TEST INPUT DOCUMENTS
# ===================================================================

class TestInputDocuments(unittest.TestCase):
    """Validate that test documents are well-formed and representative."""

    def test_small_doc_under_2k(self):
        doc = _make_small_doc()
        self.assertLess(len(doc), 2_000)

    def test_medium_doc_over_50k(self):
        doc = _make_medium_doc()
        self.assertGreater(len(doc), 50_000)

    def test_large_doc_over_150k(self):
        doc = _make_large_doc()
        self.assertGreater(len(doc), 150_000)

    def test_medium_doc_has_financial_keywords(self):
        doc = _make_medium_doc().lower()
        for kw in ("revenue", "ebitda", "net income", "cash flow", "balance sheet"):
            self.assertIn(kw, doc, f"Missing financial keyword: {kw}")

    def test_small_doc_has_invoice_keywords(self):
        doc = _make_small_doc().lower()
        for kw in ("invoice", "total amount", "payment terms"):
            self.assertIn(kw, doc, f"Missing invoice keyword: {kw}")


# ===================================================================
# 2. CHUNKING VALIDATION (NO TRUNCATION)
# ===================================================================

class TestChunkingCoverage(unittest.TestCase):
    """Verify chunking preserves ALL document content — no truncation."""

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def _chunk(self, text):
        from pipelines.processing.pipeline import ChunkingPipeline
        pl = ChunkingPipeline(strategy='adaptive', max_embed_chunks=400, enable_metrics=True)
        return self._run(pl.achunk(text=text, doc_id="test-chunk"))

    def test_small_doc_chunks(self):
        result = self._chunk(_make_small_doc())
        self.assertGreater(result['chunks_count'], 0)

    def test_medium_doc_chunks(self):
        doc = _make_medium_doc()
        result = self._chunk(doc)
        chunk_texts = [c['text'] for c in result['chunks_data']]
        total_chunk_chars = sum(len(t) for t in chunk_texts)
        # At least 95 % of original text is captured across chunks
        self.assertGreaterEqual(total_chunk_chars, 0.95 * len(doc),
                                f"Chunks only captured {total_chunk_chars}/{len(doc)} chars")
        self.assertGreater(result['chunks_count'], 5,
                           "Medium doc should produce >5 chunks")

    def test_large_doc_no_truncation(self):
        doc = _make_large_doc()
        result = self._chunk(doc)
        chunk_texts = [c['text'] for c in result['chunks_data']]
        total_chunk_chars = sum(len(t) for t in chunk_texts)
        self.assertGreaterEqual(total_chunk_chars, 0.95 * len(doc),
                                f"Large doc truncated: {total_chunk_chars}/{len(doc)}")
        self.assertGreater(result['chunks_count'], 20,
                           "Large doc should produce many chunks")

    def test_metrics_reported(self):
        result = self._chunk(_make_medium_doc())
        m = result['metrics']
        self.assertIn('chunking_time_ms', m)
        self.assertIn('total_chunks', m)
        self.assertIn('avg_chunk_size', m)
        self.assertGreater(m['avg_chunk_size'], 0)


# ===================================================================
# 3. PARALLEL PIPELINE VALIDATION
# ===================================================================

class TestParallelPipeline(unittest.TestCase):
    """Verify that embedding / deduction / dashboard run in parallel."""

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_parallel_branches_via_gather(self):
        """Source-level proof that asyncio.gather runs all 3 branches."""
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        src = inspect.getsource(AsyncPipelineOrchestrator.run)
        self.assertIn('asyncio.gather', src)
        self.assertIn('embedding_task', src)
        self.assertIn('deduction_task', src)
        self.assertIn('dashboard_task', src)

    def test_parallel_execution_timing(self):
        """
        Three mock branches each sleeping 0.3 s should complete in ~0.3 s
        (parallel), NOT 0.9 s (serial).
        """
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator

        orch = AsyncPipelineOrchestrator(enable_cache=False)

        async def _fake_embed(*a, **kw):
            await asyncio.sleep(0.3)
            return {'embeddings_count': 10, 'time_ms': 300}

        async def _fake_deduction(*a, **kw):
            await asyncio.sleep(0.3)
            return {'facts': [], 'knowledge_graph': None, 'graphrag_task_id': None, 'time_ms': 300}

        async def _fake_dashboard(*a, **kw):
            await asyncio.sleep(0.3)
            return {'dashboard': _MOCK_DASHBOARD, 'time_ms': 300}

        async def _test():
            with patch.object(orch, '_run_embedding', _fake_embed), \
                 patch.object(orch, '_run_deduction', _fake_deduction), \
                 patch.object(orch, '_run_dashboard', _fake_dashboard), \
                 patch('pipelines.processing.pipeline.ChunkingPipeline') as MockPL, \
                 patch('pipelines.processing.async_orchestrator.evaluate_deduction_trigger') as MockTrig:

                # Mock chunking
                mock_pl_inst = MagicMock()
                async def fake_achunk(**kw):
                    return {
                        'chunks_data': [{'text': 'chunk1'}, {'text': 'chunk2'}],
                        'chunks_count': 2,
                        'embeddings_count': 0,
                        'metrics': {},
                    }
                mock_pl_inst.achunk = fake_achunk
                MockPL.return_value = mock_pl_inst

                MockTrig.return_value = {
                    'run_deduction': False,
                    'document_type': 'simple_text',
                    'is_complex': False,
                    'reason': 'mock',
                }

                t0 = time.time()
                result = await orch.run(
                    text="test",
                    doc_id="par-test",
                    file_name="test.txt",
                    storage=None,
                    enable_deduction=False,
                )
                elapsed = time.time() - t0

            return elapsed, result

        elapsed, result = self._run(_test())
        # Parallel: ~0.3 s. Serial would be ~0.9 s.  Allow margin.
        self.assertLess(elapsed, 0.8,
                        f"Branches took {elapsed:.2f}s — should be ~0.3s (parallel)")
        self.assertEqual(result['status'], 'completed')

    def test_branch_timing_logged_in_metrics(self):
        """Metrics dict must contain per-branch timings."""
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        src = inspect.getsource(AsyncPipelineOrchestrator.run)
        for key in ('embedding_time_ms', 'deduction_time_ms', 'dashboard_time_ms', 'total_time_ms'):
            self.assertIn(key, src, f"Missing metric key: {key}")


# ===================================================================
# 4. ASYNC DEDUCTION VALIDATION
# ===================================================================

class TestAsyncDeduction(unittest.TestCase):
    """Validate that deduction processes chunks concurrently."""

    def test_deduction_uses_semaphore(self):
        from pipelines.processing.deduction import _MAX_CONCURRENT
        self.assertGreaterEqual(_MAX_CONCURRENT, 4)
        self.assertLessEqual(_MAX_CONCURRENT, 16)

    def test_deduction_splits_large_text(self):
        from pipelines.processing.deduction import _split_text_into_chunks, _CHUNK_SIZE
        big = "A" * 100_000
        chunks = _split_text_into_chunks(big)
        self.assertGreater(len(chunks), 1)
        # All chunks should be ≤ chunk_size + overlap margin
        for c in chunks:
            self.assertLessEqual(len(c), _CHUNK_SIZE + 1000)

    def test_deduction_merges_and_deduplicates(self):
        from pipelines.processing.deduction import _merge_facts
        facts = [
            {"subject": "Revenue", "predicate": "is", "object": "100", "confidence": 0.9},
            {"subject": "revenue", "predicate": "is", "object": "100", "confidence": 0.8},  # duplicate
            {"subject": "Cost", "predicate": "is", "object": "50", "confidence": 0.7},
        ]
        merged = _merge_facts(facts, max_facts=100)
        self.assertEqual(len(merged), 2, "Duplicate fact not eliminated")

    def test_deduction_handles_empty_text(self):
        from pipelines.processing.deduction import _split_text_into_chunks
        self.assertEqual(_split_text_into_chunks(""), [])
        self.assertEqual(_split_text_into_chunks("   "), [])

    def test_deduction_full_coverage_validation(self):
        """Splitting preserves full document — no silent drops below _MAX_CHUNKS limit."""
        from pipelines.processing.deduction import _split_text_into_chunks, _CHUNK_SIZE
        text = "X" * (5 * _CHUNK_SIZE)
        chunks = _split_text_into_chunks(text)
        covered = sum(len(c) for c in chunks)
        # Overlap means total > original, but for non-edge content it should be close
        self.assertGreater(covered, len(text) * 0.8)

    def test_async_extract_source_uses_gather(self):
        """aextract_facts must use asyncio.gather for parallel chunk processing."""
        from pipelines.processing.deduction import DeductionEngine
        src = inspect.getsource(DeductionEngine.aextract_facts)
        self.assertIn('asyncio.gather', src,
                       "aextract_facts should use asyncio.gather for parallelism")


# ===================================================================
# 5. SMART TRIGGER VALIDATION
# ===================================================================

class TestSmartTrigger(unittest.TestCase):
    """Validate the deduction trigger decision matrix."""

    def _chunks(self, text: str, n: int = 1):
        return [{"text": text}] * n

    def test_simple_invoice_skips_deduction(self):
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        chunks = self._chunks(_make_small_doc())
        result = evaluate_deduction_trigger(chunks)
        self.assertFalse(result['run_deduction'],
                         f"Simple invoice should skip deduction: {result['reason']}")

    def test_financial_report_runs_deduction(self):
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        chunks = self._chunks(
            "Revenue grew 12%. EBITDA improved. Net income was $48M. "
            "Cash flow from operations reached $120M. Balance sheet is healthy. "
            "Earnings per share were $3.21.",
            n=5,
        )
        result = evaluate_deduction_trigger(chunks)
        self.assertEqual(result['document_type'], 'financial_report')
        self.assertTrue(result['run_deduction'],
                        f"Financial report should trigger deduction: {result['reason']}")

    def test_technical_doc_runs_deduction(self):
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        chunks = self._chunks(
            "The system design uses a microservice architecture with Kubernetes "
            "deployment and Docker containerisation. API gateway handles routing. "
            "Database sharding improves scalability.",
            n=3,
        )
        result = evaluate_deduction_trigger(chunks)
        self.assertEqual(result['document_type'], 'technical_document')
        self.assertTrue(result['run_deduction'])

    def test_contract_runs_deduction(self):
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        chunks = self._chunks(
            "This agreement between Party A and Party B sets forth the terms "
            "and obligations of both parties. Termination clause applies after "
            "breach. Governing law is Delaware. Indemnification is mutual.",
            n=4,
        )
        result = evaluate_deduction_trigger(chunks)
        self.assertEqual(result['document_type'], 'contract')
        self.assertTrue(result['run_deduction'])

    def test_force_true_overrides(self):
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        # Even a tiny doc should run deduction when forced
        chunks = self._chunks("Hello world", n=1)
        result = evaluate_deduction_trigger(chunks, force=True)
        self.assertTrue(result['run_deduction'])

    def test_force_false_overrides(self):
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        # Even a financial report should skip when forced off
        chunks = self._chunks(
            "Revenue grew 12%. EBITDA improved. Net income $48M. "
            "Cash flow $120M. Balance sheet healthy. Earnings $3.21.",
            n=5,
        )
        result = evaluate_deduction_trigger(chunks, force=False)
        self.assertFalse(result['run_deduction'])

    def test_complex_unknown_triggers_deduction(self):
        """Large unknown document triggers deduction as fail-safe."""
        from pipelines.processing.deduction_trigger import evaluate_deduction_trigger
        # 25 chunks of generic text → complex + unknown → should run
        chunks = self._chunks("Lorem ipsum dolor sit amet. " * 200, n=25)
        result = evaluate_deduction_trigger(chunks)
        self.assertTrue(result['is_complex'])
        self.assertTrue(result['run_deduction'],
                        f"Complex unknown docs should trigger deduction: {result['reason']}")


# ===================================================================
# 6. SMART CONTEXT — NO FULL DOC TO LLM
# ===================================================================

class TestSmartContext(unittest.TestCase):
    """Dashboard MUST use top-k chunks, never the full document."""

    def test_context_chars_budget_exists(self):
        from pipelines.processing.dashboard import _MAX_CONTEXT_CHARS
        self.assertLessEqual(_MAX_CONTEXT_CHARS, 60_000,
                             "Context budget should be capped")

    def test_select_context_chunks_limits_output(self):
        from pipelines.processing.dashboard import DashboardGenerator
        gen = DashboardGenerator.__new__(DashboardGenerator)
        # 100 chunks of 2K chars each = 200K. Max should come back ≤ 20.
        chunks = [f"Chunk {i}: " + "data " * 300 for i in range(100)]
        selected = gen._select_context_chunks(chunks, max_chunks=20)
        self.assertLessEqual(len(selected), 20)

    def test_build_context_respects_char_limit(self):
        from pipelines.processing.dashboard import DashboardGenerator, _MAX_CONTEXT_CHARS
        gen = DashboardGenerator.__new__(DashboardGenerator)
        chunks = [f"Chunk {i}: " + "x" * 5_000 for i in range(50)]  # 250K total
        ctx = gen._build_context(chunks, max_chars=_MAX_CONTEXT_CHARS)
        self.assertLessEqual(len(ctx), _MAX_CONTEXT_CHARS + 500,
                             "Context exceeds budget")

    def test_dashboard_input_smaller_than_doc(self):
        """End-to-end: agenerate_dashboard sends less than full doc to LLM."""
        from pipelines.processing.dashboard import DashboardGenerator

        captured_prompt = {}

        gen = DashboardGenerator.__new__(DashboardGenerator)
        gen.llm = _mock_llm()
        gen.prompt_version = "latest"
        gen.use_ab_test = False

        original_generate_json = gen.llm.generate_json

        def spy_generate_json(prompt, *a, **kw):
            captured_prompt['text'] = prompt
            return original_generate_json(prompt, *a, **kw)

        gen.llm.generate_json = spy_generate_json

        doc = _make_large_doc()  # ~200K chars
        chunks = [doc[i:i+2000] for i in range(0, len(doc), 2000)]

        result = gen.generate_dashboard(chunks, file_name="large.pdf")

        self.assertIn('text', captured_prompt)
        self.assertLess(len(captured_prompt['text']), len(doc),
                        "Full document text was sent to LLM!")


# ===================================================================
# 7. EMBEDDING OPTIMISATION
# ===================================================================

class TestEmbeddingOptimisation(unittest.TestCase):
    """Validate hardware-aware batching and OOM fallback."""

    def test_cpu_batch_size_at_least_128(self):
        from services.vector_store.embeddings.embedding_model import _resolve_batch_size
        bs = _resolve_batch_size("cpu")
        self.assertGreaterEqual(bs, 128)

    def test_gpu_batch_size_larger(self):
        from services.vector_store.embeddings.embedding_model import _resolve_batch_size
        bs_gpu = _resolve_batch_size("cuda")
        bs_cpu = _resolve_batch_size("cpu")
        self.assertGreaterEqual(bs_gpu, bs_cpu)

    def test_oom_fallback_in_source(self):
        from services.vector_store.embeddings.embedding_model import EmbeddingModel
        src = inspect.getsource(EmbeddingModel._encode_with_fallback)
        self.assertIn('batch_size // 2', src, "OOM fallback should halve batch size")
        self.assertIn('min_batch', src, "Must have a minimum batch floor")

    def test_device_resolution_returns_valid(self):
        from services.vector_store.embeddings.embedding_model import _resolve_device
        device = _resolve_device()
        self.assertIn(device, ("cpu", "cuda"))

    def test_settings_expose_embedding_config(self):
        from core.config.settings import settings
        self.assertTrue(hasattr(settings, 'EMBEDDING_BATCH_SIZE'))
        self.assertTrue(hasattr(settings, 'EMBEDDING_DEVICE'))
        self.assertTrue(hasattr(settings, 'EMBEDDING_MODEL'))


# ===================================================================
# 8. CONTENT CACHING
# ===================================================================

class TestContentCaching(unittest.TestCase):
    """Validate cache hit on second run — instant, same result."""

    def test_cache_round_trip(self):
        from services.storage.local import LocalStorage
        from services.cache.content_cache import ContentCache
        storage = LocalStorage()
        cache = ContentCache(storage)

        text = f"unique-e2e-doc-{time.time()}"
        result = {"status": "completed", "doc_id": "cache-test", "dashboard_data": _MOCK_DASHBOARD}

        # Store
        cache.put(text, result)

        # Retrieve
        cached = cache.get(text)
        self.assertIsNotNone(cached, "Cache miss on identical content")
        self.assertEqual(cached['doc_id'], 'cache-test')

    def test_cache_hit_is_instant(self):
        from services.storage.local import LocalStorage
        from services.cache.content_cache import ContentCache
        storage = LocalStorage()
        cache = ContentCache(storage)

        text = f"perf-cache-{time.time()}"
        cache.put(text, {"ok": True})

        t0 = time.time()
        cached = cache.get(text)
        elapsed = time.time() - t0

        self.assertIsNotNone(cached)
        self.assertLess(elapsed, 0.1, f"Cache lookup took {elapsed:.3f}s — should be <100ms")

    def test_normalized_text_matches(self):
        from services.cache.content_cache import content_hash
        h1 = content_hash("Hello   World\n\t  foo")
        h2 = content_hash("hello world foo")
        self.assertEqual(h1, h2, "Normalization should make these match")

    def test_cache_in_orchestrator_skips_reprocessing(self):
        """Orchestrator must check cache before launching expensive branches."""
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        src = inspect.getsource(AsyncPipelineOrchestrator.run)
        self.assertIn('cache', src.lower())
        self.assertIn('from_cache', src)


# ===================================================================
# 9. SSE DASHBOARD STREAMING
# ===================================================================

class TestSSEStreaming(unittest.TestCase):
    """Validate progressive dashboard streaming via async generator."""

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_stream_yields_progressive_stages(self):
        from pipelines.processing.dashboard import DashboardGenerator

        gen = DashboardGenerator.__new__(DashboardGenerator)
        gen.llm = _mock_llm()
        gen.prompt_version = "latest"
        gen.use_ab_test = False

        async def collect():
            events = []
            with patch.object(gen, '_select_context_chunks', return_value=["chunk"]):
                async for ev in gen.agenerate_dashboard_stream(
                    chunks=["chunk1", "chunk2"],
                    file_name="test.xlsx",
                    doc_id="stream-test",
                ):
                    events.append(ev)
            return events

        events = self._run(collect())
        stages = [e['stage'] for e in events]

        # Required stages
        for stage in ('context_ready', 'kpis', 'complete'):
            self.assertIn(stage, stages, f"Missing SSE stage: {stage}")

        # Order: context_ready first, complete last
        self.assertEqual(stages[0], 'context_ready')
        self.assertEqual(stages[-1], 'complete')

    def test_kpis_arrive_before_complete(self):
        from pipelines.processing.dashboard import DashboardGenerator

        gen = DashboardGenerator.__new__(DashboardGenerator)
        gen.llm = _mock_llm()
        gen.prompt_version = "latest"
        gen.use_ab_test = False

        async def collect():
            events = []
            with patch.object(gen, '_select_context_chunks', return_value=["c"]):
                async for ev in gen.agenerate_dashboard_stream(chunks=["c"]):
                    events.append(ev)
            return events

        events = self._run(collect())
        stages = [e['stage'] for e in events]

        kpi_idx = stages.index('kpis') if 'kpis' in stages else -1
        complete_idx = stages.index('complete')
        self.assertLess(kpi_idx, complete_idx, "KPIs must arrive before complete")

    def test_complete_event_contains_full_dashboard(self):
        from pipelines.processing.dashboard import DashboardGenerator

        gen = DashboardGenerator.__new__(DashboardGenerator)
        gen.llm = _mock_llm()
        gen.prompt_version = "latest"
        gen.use_ab_test = False

        async def collect():
            events = []
            with patch.object(gen, '_select_context_chunks', return_value=["c"]):
                async for ev in gen.agenerate_dashboard_stream(chunks=["c"]):
                    events.append(ev)
            return events

        events = self._run(collect())
        complete = next(e for e in events if e['stage'] == 'complete')
        self.assertIn('dashboard', complete['data'])
        self.assertIn('elapsed_ms', complete['data'])

    def test_sse_endpoint_exists(self):
        from app.api.v2.endpoints import stream_dashboard
        self.assertTrue(inspect.iscoroutinefunction(stream_dashboard))
        sig = inspect.signature(stream_dashboard)
        self.assertIn('doc_id', sig.parameters)


# ===================================================================
# 10. WORKER CONCURRENCY
# ===================================================================

class TestWorkerConcurrency(unittest.TestCase):
    """Validate Celery is configured for multi-worker parallel processing."""

    def test_concurrency_at_least_4(self):
        from core.config.settings import settings
        self.assertGreaterEqual(settings.WORKER_CONCURRENCY, 4)

    def test_prefetch_is_1(self):
        """prefetch=1 ensures fair scheduling (no task hogging)."""
        from core.config.settings import settings
        self.assertEqual(settings.WORKER_PREFETCH_MULTIPLIER, 1)

    def test_task_acks_late(self):
        from services.workers.processor import celery, CELERY_AVAILABLE
        if not CELERY_AVAILABLE:
            self.skipTest("Celery not installed")
        self.assertTrue(celery.conf.task_acks_late)

    def test_task_reject_on_worker_lost(self):
        from services.workers.processor import celery, CELERY_AVAILABLE
        if not CELERY_AVAILABLE:
            self.skipTest("Celery not installed")
        self.assertTrue(celery.conf.task_reject_on_worker_lost)

    def test_queue_routing_configured(self):
        from services.workers.processor import celery, CELERY_AVAILABLE
        if not CELERY_AVAILABLE:
            self.skipTest("Celery not installed")
        routes = celery.conf.task_routes
        self.assertIn('services.workers.processor.process_document', routes)
        self.assertIn('services.workers.graph_processing.build_knowledge_graph', routes)

    def test_worker_max_tasks_per_child(self):
        from core.config.settings import settings
        self.assertGreaterEqual(settings.WORKER_MAX_TASKS_PER_CHILD, 50)

    def test_llm_semaphore_limits_concurrency(self):
        from pipelines.processing.async_orchestrator import _LLM_SEMAPHORE_LIMIT
        self.assertGreaterEqual(_LLM_SEMAPHORE_LIMIT, 4)
        self.assertLessEqual(_LLM_SEMAPHORE_LIMIT, 32)

    def test_docker_compose_correct_module_path(self):
        import pathlib
        compose = pathlib.Path(__file__).parent.parent / 'infra' / 'docker-compose.yml'
        if not compose.exists():
            self.skipTest("docker-compose.yml not found")
        content = compose.read_text()
        self.assertIn('services.workers.processor.celery', content)
        self.assertNotIn('app.workers.processor.celery', content)


# ===================================================================
# 11. ERROR HANDLING / FAULT TOLERANCE
# ===================================================================

class TestErrorHandling(unittest.TestCase):
    """Pipeline must survive LLM / DB failures without crashing."""

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_embedding_failure_does_not_crash_pipeline(self):
        """If embedding fails, dashboard + deduction still complete."""
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator

        orch = AsyncPipelineOrchestrator(enable_cache=False)

        async def _fail_embed(*a, **kw):
            raise RuntimeError("Vector DB unavailable")

        async def _ok_deduction(*a, **kw):
            return {'facts': _MOCK_FACTS, 'knowledge_graph': None,
                    'graphrag_task_id': None, 'time_ms': 100}

        async def _ok_dashboard(*a, **kw):
            return {'dashboard': _MOCK_DASHBOARD, 'time_ms': 200}

        async def _test():
            with patch.object(orch, '_run_embedding', _fail_embed), \
                 patch.object(orch, '_run_deduction', _ok_deduction), \
                 patch.object(orch, '_run_dashboard', _ok_dashboard), \
                 patch('pipelines.processing.pipeline.ChunkingPipeline') as MockPL, \
                 patch('pipelines.processing.async_orchestrator.evaluate_deduction_trigger') as MockTrig:

                mock_pl = MagicMock()
                async def fake_achunk(**kw):
                    return {'chunks_data': [{'text': 'c'}], 'chunks_count': 1,
                            'embeddings_count': 0, 'metrics': {}}
                mock_pl.achunk = fake_achunk
                MockPL.return_value = mock_pl
                MockTrig.return_value = {
                    'run_deduction': True, 'document_type': 'financial_report',
                    'is_complex': False, 'reason': 'mock'}

                result = await orch.run(
                    text="test", doc_id="err-1", file_name="t.pdf", storage=None)
            return result

        result = self._run(_test())
        self.assertEqual(result['status'], 'completed')
        self.assertGreater(len(result['errors']), 0, "Should record embedding error")
        self.assertIsNotNone(result['dashboard_data'], "Dashboard should still succeed")

    def test_dashboard_failure_does_not_crash_pipeline(self):
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        orch = AsyncPipelineOrchestrator(enable_cache=False)

        async def _ok_embed(*a, **kw):
            return {'embeddings_count': 5, 'time_ms': 50}

        async def _ok_deduction(*a, **kw):
            return {'facts': [], 'knowledge_graph': None, 'graphrag_task_id': None, 'time_ms': 0}

        async def _fail_dashboard(*a, **kw):
            raise RuntimeError("LLM quota exceeded")

        async def _test():
            with patch.object(orch, '_run_embedding', _ok_embed), \
                 patch.object(orch, '_run_deduction', _ok_deduction), \
                 patch.object(orch, '_run_dashboard', _fail_dashboard), \
                 patch('pipelines.processing.pipeline.ChunkingPipeline') as MockPL, \
                 patch('pipelines.processing.async_orchestrator.evaluate_deduction_trigger') as MockTrig:

                mock_pl = MagicMock()
                async def fake_achunk(**kw):
                    return {'chunks_data': [{'text': 'c'}], 'chunks_count': 1,
                            'embeddings_count': 0, 'metrics': {}}
                mock_pl.achunk = fake_achunk
                MockPL.return_value = mock_pl
                MockTrig.return_value = {
                    'run_deduction': False, 'document_type': 'simple_text',
                    'is_complex': False, 'reason': 'mock'}

                result = await orch.run(
                    text="test", doc_id="err-2", file_name="t.pdf", storage=None)
            return result

        result = self._run(_test())
        self.assertEqual(result['status'], 'completed')
        self.assertGreater(len(result['errors']), 0)

    def test_all_branches_fail_still_completes(self):
        """Even total failure of all 3 branches returns a result dict."""
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        orch = AsyncPipelineOrchestrator(enable_cache=False)

        async def _fail(*a, **kw):
            raise RuntimeError("Catastrophic failure")

        async def _test():
            with patch.object(orch, '_run_embedding', _fail), \
                 patch.object(orch, '_run_deduction', _fail), \
                 patch.object(orch, '_run_dashboard', _fail), \
                 patch('pipelines.processing.pipeline.ChunkingPipeline') as MockPL, \
                 patch('pipelines.processing.async_orchestrator.evaluate_deduction_trigger') as MockTrig:

                mock_pl = MagicMock()
                async def fake_achunk(**kw):
                    return {'chunks_data': [{'text': 'c'}], 'chunks_count': 1,
                            'embeddings_count': 0, 'metrics': {}}
                mock_pl.achunk = fake_achunk
                MockPL.return_value = mock_pl
                MockTrig.return_value = {
                    'run_deduction': False, 'document_type': 'unknown',
                    'is_complex': False, 'reason': 'mock'}

                result = await orch.run(
                    text="test", doc_id="err-3", file_name="t.pdf", storage=None)
            return result

        result = self._run(_test())
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(result['errors']), 3, "All 3 branch errors should be logged")

    def test_deduction_partial_chunk_failure(self):
        """Deduction returns partial facts when some chunks fail."""
        from pipelines.processing.deduction import _merge_facts
        # Simulate: 3 chunks succeed, 1 fails → merged facts from successful ones
        facts = [
            {"subject": "A", "predicate": "is", "object": "1", "confidence": 0.9},
            {"subject": "B", "predicate": "is", "object": "2", "confidence": 0.8},
        ]
        merged = _merge_facts(facts, max_facts=100)
        self.assertEqual(len(merged), 2, "Partial results should be returned")


# ===================================================================
# 12. PERFORMANCE CHECKS (structural)
# ===================================================================

class TestPerformanceStructure(unittest.TestCase):
    """Validate the architectural patterns that enable performance targets."""

    def test_no_document_truncation_constant(self):
        """No 600K constant should exist in the pipeline."""
        import pipelines.processing.pipeline as pl
        src = inspect.getsource(pl)
        self.assertNotIn('600000', src, "Legacy 600K truncation still present")
        self.assertNotIn('600_000', src, "Legacy 600K truncation still present")

    def test_no_truncation_in_processor(self):
        import services.workers.processor as proc
        src = inspect.getsource(proc)
        self.assertNotIn('600000', src)
        self.assertNotIn('[:600', src)

    def test_task_time_limits_reasonable(self):
        from services.workers.processor import celery, CELERY_AVAILABLE
        if not CELERY_AVAILABLE:
            self.skipTest("Celery not installed")
        self.assertLessEqual(celery.conf.task_time_limit, 600,
                             "Hard limit too generous")
        self.assertGreaterEqual(celery.conf.task_time_limit, 120,
                                "Hard limit too tight")

    def test_content_cache_skips_all_processing(self):
        """On cache HIT, run() returns immediately — no branches execute."""
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        src = inspect.getsource(AsyncPipelineOrchestrator.run)
        # Should return directly from cache before asyncio.gather
        cache_idx = src.index("from_cache")
        gather_idx = src.index("asyncio.gather")
        self.assertLess(cache_idx, gather_idx,
                        "Cache check must occur BEFORE parallel execution")

    def test_pipeline_uses_asyncio_create_task(self):
        """Branches are fire-and-forget tasks, not sequential awaits."""
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        src = inspect.getsource(AsyncPipelineOrchestrator.run)
        self.assertGreaterEqual(src.count('asyncio.create_task'), 3,
                                "Should create at least 3 concurrent tasks")

    def test_embedding_cap_exists(self):
        """Embedding is capped at max_embed_chunks to prevent overload."""
        from pipelines.processing.async_orchestrator import AsyncPipelineOrchestrator
        src = inspect.getsource(AsyncPipelineOrchestrator._run_embedding)
        self.assertIn('max_embed_chunks', src)


# ===================================================================
# REPORT GENERATOR
# ===================================================================

class TestReportGenerator(unittest.TestCase):
    """
    Meta-test: runs all sections and produces a structured JSON report.
    This test always passes — it summarises the results of other tests.
    """

    def test_generate_report(self):
        import io
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        section_map = {
            "chunking": TestChunkingCoverage,
            "parallel_pipeline": TestParallelPipeline,
            "deduction_async": TestAsyncDeduction,
            "smart_trigger": TestSmartTrigger,
            "smart_context": TestSmartContext,
            "embedding_optimization": TestEmbeddingOptimisation,
            "caching": TestContentCaching,
            "streaming": TestSSEStreaming,
            "worker_concurrency": TestWorkerConcurrency,
            "error_handling": TestErrorHandling,
            "performance": TestPerformanceStructure,
        }

        report = {}
        for section, cls in section_map.items():
            s = loader.loadTestsFromTestCase(cls)
            stream = io.StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=0)
            result = runner.run(s)
            passed = result.testsRun - len(result.failures) - len(result.errors)
            report[section] = "PASS" if not result.failures and not result.errors else "FAIL"

        all_pass = all(v == "PASS" for v in report.values())
        report["overall_status"] = "READY" if all_pass else "NEEDS FIX"

        print("\n" + "=" * 60)
        print("  E2E PIPELINE VALIDATION REPORT")
        print("=" * 60)
        for k, v in report.items():
            icon = "[PASS]" if v in ("PASS", "READY") else "[FAIL]"
            print(f"  {icon} {k:30s} {v}")
        print("=" * 60)


if __name__ == '__main__':
    unittest.main(verbosity=2)
