"""
Tests for services.memory — Store, Episodes, Hippocampus, Cortex,
and integration with Chat Orchestrator.

All tests use in-memory SQLite (no disk files).

Run:  python -m pytest tests/test_memory_system.py -v
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch
from typing import Any, Dict, List


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture()
def store():
    from services.memory.store import MemoryStore
    s = MemoryStore(db_path=":memory:")
    yield s
    s.close()


@pytest.fixture()
def cortex(store):
    from services.memory.cortex import Cortex
    return Cortex(store=store)


@pytest.fixture(autouse=True)
def _ensure_tools():
    """Fresh tool registry for integration tests."""
    from services.tools.registry import _reset
    _reset()
    import importlib
    import services.tools as st
    importlib.reload(st)
    yield
    _reset()


def _fake_llm(responses):
    idx = {"n": 0}
    def _gen(prompt, **kw):
        i = idx["n"]; idx["n"] += 1
        resp = responses[i] if i < len(responses) else {"action": "final_answer", "response": "done"}
        return {"provider_used": "mock", "response": resp, "error": None, "attempts": 1}
    return _gen


# ======================================================================
# store.py
# ======================================================================

class TestMemoryStore:
    def test_save_and_retrieve_episode(self, store):
        row_id = store.save_episode(
            query="test query",
            tools_used=["kpi_analysis"],
            steps=[{"step": 1}],
            final_answer="the answer",
        )
        assert row_id >= 1

        eps = store.recent_episodes(limit=1)
        assert len(eps) == 1
        assert eps[0]["query"] == "test query"
        assert eps[0]["tools_used"] == ["kpi_analysis"]

    def test_search_episodes(self, store):
        store.save_episode(query="alpha bravo", tools_used=[], steps=[], final_answer="ok")
        store.save_episode(query="charlie delta", tools_used=[], steps=[], final_answer="ok")

        results = store.search_episodes("alpha")
        assert len(results) == 1
        assert "alpha" in results[0]["query"]

    def test_search_episodes_matches_answer(self, store):
        store.save_episode(query="q", tools_used=[], steps=[], final_answer="sigma 4.5")

        results = store.search_episodes("sigma")
        assert len(results) == 1

    def test_episode_count(self, store):
        assert store.episode_count() == 0
        store.save_episode(query="a", tools_used=[], steps=[], final_answer="")
        assert store.episode_count() == 1

    def test_save_and_retrieve_learning(self, store):
        row_id = store.save_learning(kind="rule", text="Always check data quality")
        assert row_id >= 1

        results = store.all_learnings()
        assert len(results) == 1
        assert results[0]["kind"] == "rule"

    def test_search_learnings(self, store):
        store.save_learning(kind="pattern", text="KPI before prediction")
        store.save_learning(kind="rule", text="Never skip MSA")

        results = store.search_learnings("KPI")
        assert len(results) == 1
        assert "KPI" in results[0]["text"]

    def test_search_learnings_by_kind(self, store):
        store.save_learning(kind="rule", text="Check quality")
        store.save_learning(kind="pattern", text="Check quality too")

        rules = store.search_learnings("Check", kind="rule")
        assert len(rules) == 1
        assert rules[0]["kind"] == "rule"

    def test_learning_count(self, store):
        assert store.learning_count() == 0
        store.save_learning(kind="preference", text="x")
        assert store.learning_count() == 1

    def test_trim_episodes(self, store):
        from services.memory.store import _MAX_EPISODES
        for i in range(_MAX_EPISODES + 10):
            store.save_episode(query=f"q{i}", tools_used=[], steps=[], final_answer="")
        assert store.episode_count() <= _MAX_EPISODES

    def test_trim_learnings(self, store):
        from services.memory.store import _MAX_LEARNINGS
        for i in range(_MAX_LEARNINGS + 10):
            store.save_learning(kind="pattern", text=f"l{i}")
        assert store.learning_count() <= _MAX_LEARNINGS


# ======================================================================
# episodes.py
# ======================================================================

class TestEpisodicMemory:
    def test_record_and_recall(self, store):
        from services.memory.episodes import EpisodicMemory
        em = EpisodicMemory(store)

        em.record(query="ROP sigma", tools_used=["six_sigma_analysis"],
                  steps=[], final_answer="Sigma 3.5")

        results = em.recall("sigma")
        assert len(results) == 1
        assert results[0]["tools_used"] == ["six_sigma_analysis"]

    def test_format_for_context(self, store):
        from services.memory.episodes import EpisodicMemory
        em = EpisodicMemory(store)

        em.record(query="test", tools_used=["kpi_analysis"], steps=[], final_answer="ok")
        episodes = em.recent(limit=1)
        text = em.format_for_context(episodes)

        assert "PAST CONVERSATIONS" in text
        assert "kpi_analysis" in text

    def test_format_empty(self, store):
        from services.memory.episodes import EpisodicMemory
        em = EpisodicMemory(store)
        assert em.format_for_context([]) == ""


# ======================================================================
# hippocampus.py
# ======================================================================

class TestHippocampus:
    def test_record_learning(self, store):
        from services.memory.hippocampus import Hippocampus
        hc = Hippocampus(store)

        hc.record_learning(kind="rule", text="Always verify data")
        rules = hc.all_rules()
        assert len(rules) == 1

    def test_heuristic_extraction(self, store):
        from services.memory.hippocampus import Hippocampus
        hc = Hippocampus(store)

        episode = {
            "id": 1,
            "query": "test",
            "tools_used": ["kpi_analysis", "predictive_forecast"],
            "final_answer": "done",
        }
        saved = hc.extract_learnings(episode)
        assert len(saved) >= 1
        assert "kpi_analysis" in saved[0]["text"]

    def test_llm_extraction(self, store):
        from services.memory.hippocampus import Hippocampus
        hc = Hippocampus(store)

        llm = _fake_llm([
            [{"kind": "preference", "text": "User prefers KPI first", "confidence": 0.9}],
        ])
        episode = {"id": 1, "query": "q", "tools_used": [], "final_answer": "a"}
        saved = hc.extract_learnings(episode, llm_generate_json=llm)

        assert len(saved) == 1
        assert saved[0]["kind"] == "preference"
        assert "KPI" in saved[0]["text"]

    def test_format_for_context(self, store):
        from services.memory.hippocampus import Hippocampus
        hc = Hippocampus(store)

        hc.record_learning(kind="rule", text="Check MSA always")
        learnings = hc.all_rules()
        text = hc.format_for_context(learnings)

        assert "LEARNED PATTERNS" in text
        assert "RULE" in text
        assert "Check MSA" in text

    def test_invalid_kind_defaults_to_pattern(self, store):
        from services.memory.hippocampus import Hippocampus
        hc = Hippocampus(store)

        hc.record_learning(kind="gibberish", text="test")
        all_l = store.all_learnings()
        assert all_l[0]["kind"] == "pattern"


# ======================================================================
# cortex.py
# ======================================================================

class TestCortex:
    def test_get_context_empty(self, cortex):
        ctx = cortex.get_context("anything")
        assert ctx["memory_text"] == ""
        assert ctx["episodes"] == []
        assert ctx["learnings"] == []

    def test_get_context_with_data(self, cortex):
        cortex.episodes.record(
            query="ROP sigma", tools_used=["six_sigma_analysis"],
            steps=[], final_answer="Sigma 3.5",
        )
        cortex.hippocampus.record_learning(kind="rule", text="Always check data quality")

        ctx = cortex.get_context("sigma")
        assert "sigma" in ctx["memory_text"].lower() or "PAST" in ctx["memory_text"]
        assert len(ctx["episodes"]) >= 1
        assert len(ctx["learnings"]) >= 1

    def test_store_episode(self, cortex):
        chat_result = {
            "query": "test",
            "tools_used": ["kpi_analysis"],
            "steps": [{"step": 1}],
            "final_answer": "42",
        }
        row_id = cortex.store_episode(chat_result)
        assert row_id >= 1
        assert cortex.episodes.count == 1

    def test_learn_heuristic(self, cortex):
        chat_result = {
            "id": 1,
            "query": "q",
            "tools_used": ["kpi_analysis", "predictive_forecast"],
            "final_answer": "done",
        }
        saved = cortex.learn(chat_result)
        assert len(saved) >= 1

    def test_stats(self, cortex):
        stats = cortex.stats
        assert stats["episodes"] == 0
        assert stats["learnings"] == 0

    def test_context_truncation(self, cortex):
        from services.memory.cortex import _MAX_CONTEXT_CHARS
        # Stuff enough data to exceed the limit
        for i in range(50):
            cortex.hippocampus.record_learning(
                kind="rule", text=f"Very long rule number {i} " * 20,
            )
        ctx = cortex.get_context("rule")
        assert len(ctx["memory_text"]) <= _MAX_CONTEXT_CHARS + 50  # +50 for truncation msg


# ======================================================================
# Chat Orchestrator integration
# ======================================================================

class TestChatOrchestratorMemoryIntegration:
    def test_memory_injected_into_prompt(self, cortex):
        """Memory text appears in the LLM prompt."""
        cortex.hippocampus.record_learning(kind="rule", text="Always check data quality first")

        captured = []

        def _capture(prompt, **kw):
            captured.append(prompt)
            return {
                "provider_used": "mock",
                "response": {"action": "final_answer", "response": "done"},
                "error": None,
                "attempts": 1,
            }

        from services.chat.orchestrator import handle_chat
        handle_chat("run sigma analysis", llm_generate_json=_capture, memory=cortex)

        # First captured prompt is the chat LLM call (second may be learn())
        assert len(captured) >= 1
        assert "Always check data quality" in captured[0]

    def test_episode_stored_after_chat(self, cortex):
        from services.chat.orchestrator import handle_chat

        llm = _fake_llm([
            {"action": "final_answer", "response": "Sigma is 4.0"},
        ])
        handle_chat("sigma?", llm_generate_json=llm, memory=cortex)

        assert cortex.episodes.count == 1
        eps = cortex.episodes.recent(limit=1)
        assert eps[0]["query"] == "sigma?"
        assert eps[0]["final_answer"] == "Sigma is 4.0"

    @patch("features.kpi.kpi_engine.process_kpis", return_value=[{"name": "ROP"}])
    def test_tool_call_stored_in_episode(self, mock_kpi, cortex):
        from services.chat.orchestrator import handle_chat

        llm = _fake_llm([
            {"action": "tool_call", "tool_name": "kpi_analysis", "tool_input": {"kpis": []}},
            {"action": "final_answer", "response": "done"},
        ])
        handle_chat("score KPIs", llm_generate_json=llm, memory=cortex)

        eps = cortex.episodes.recent(limit=1)
        assert "kpi_analysis" in eps[0]["tools_used"]

    def test_no_memory_still_works(self):
        """handle_chat works fine when memory=None (backward compat)."""
        from services.chat.orchestrator import handle_chat

        llm = _fake_llm([
            {"action": "final_answer", "response": "ok"},
        ])
        result = handle_chat("hi", llm_generate_json=llm)
        assert result["final_answer"] == "ok"

    def test_memory_error_does_not_crash_chat(self, cortex):
        """If memory raises, the chat still completes."""
        from services.chat.orchestrator import handle_chat

        # Sabotage the store so it throws
        cortex._store._db_path = "/nonexistent/path.db"
        cortex._store._local.conn = None

        llm = _fake_llm([
            {"action": "final_answer", "response": "still works"},
        ])
        # Should not raise — memory errors are caught
        result = handle_chat("test", llm_generate_json=llm, memory=cortex)
        assert result["final_answer"] == "still works"

    def test_second_call_recalls_first(self, cortex):
        """After one conversation, memory context includes it in the next call."""
        from services.chat.orchestrator import handle_chat

        llm1 = _fake_llm([
            {"action": "final_answer", "response": "Sigma is 3.5 for well X"},
        ])
        handle_chat("sigma for well X", llm_generate_json=llm1, memory=cortex)

        # Verify episode was stored
        assert cortex.episodes.count >= 1

        # Second call — capture the prompt to check memory injection
        captured = []

        def _capture(prompt, **kw):
            captured.append(prompt)
            return {
                "provider_used": "mock",
                "response": {"action": "final_answer", "response": "done"},
                "error": None,
                "attempts": 1,
            }

        handle_chat("sigma analysis", llm_generate_json=_capture, memory=cortex)

        # The first captured prompt (chat call) should contain the prior episode
        assert len(captured) >= 1
        assert "well X" in captured[0]
