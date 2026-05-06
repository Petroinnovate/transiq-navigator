"""
Tests for the Streaming Layer (services/streaming).

Covers:
  - Event type definitions and factory helpers
  - StreamEvent envelope structure
  - StreamingManager buffering and lifecycle methods
  - Chat Orchestrator streaming integration
  - Agent Executor streaming integration
  - Fallback behaviour when no WebSocket is connected
"""
from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure Backend is on sys.path
# ---------------------------------------------------------------------------
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


# ===================================================================
# 1. Event Types
# ===================================================================


class TestEventTypes:
    """event_types.py — constants, StreamEvent, factory helpers."""

    def test_all_event_types_count(self):
        from services.streaming.event_types import ALL_EVENT_TYPES

        assert len(ALL_EVENT_TYPES) == 7

    def test_stream_event_envelope(self):
        from services.streaming.event_types import StreamEvent

        evt = StreamEvent(type="llm_start", data={"iteration": 1})
        d = evt.to_dict()
        assert d["type"] == "llm_start"
        assert "timestamp" in d
        assert d["data"]["iteration"] == 1

    def test_stream_event_is_frozen(self):
        from services.streaming.event_types import StreamEvent

        evt = StreamEvent(type="llm_start")
        with pytest.raises(AttributeError):
            evt.type = "other"  # type: ignore[misc]

    def test_timestamp_auto_generated(self):
        from services.streaming.event_types import StreamEvent

        evt = StreamEvent(type="test")
        assert evt.timestamp  # non-empty
        assert "T" in evt.timestamp  # ISO-8601

    def test_timestamp_can_be_overridden(self):
        from services.streaming.event_types import StreamEvent

        evt = StreamEvent(type="test", timestamp="2025-01-01T00:00:00Z")
        assert evt.timestamp == "2025-01-01T00:00:00Z"

    def test_llm_start_event(self):
        from services.streaming.event_types import llm_start_event

        evt = llm_start_event(iteration=2)
        assert evt.type == "llm_start"
        assert evt.to_dict()["data"]["iteration"] == 2

    def test_llm_token_event(self):
        from services.streaming.event_types import llm_token_event

        evt = llm_token_event("Hello", iteration=1)
        d = evt.to_dict()
        assert d["type"] == "llm_token"
        assert d["data"]["token"] == "Hello"

    def test_llm_end_event(self):
        from services.streaming.event_types import llm_end_event

        evt = llm_end_event(iteration=3, success=False)
        d = evt.to_dict()
        assert d["data"]["success"] is False

    def test_tool_start_event(self):
        from services.streaming.event_types import tool_start_event

        evt = tool_start_event("six_sigma_analysis", step=0)
        assert evt.type == "tool_start"
        assert evt.to_dict()["data"]["tool"] == "six_sigma_analysis"

    def test_tool_progress_event_with_detail(self):
        from services.streaming.event_types import tool_progress_event

        evt = tool_progress_event("kpi_analysis", "running", step=1, detail="50%")
        d = evt.to_dict()
        assert d["data"]["detail"] == "50%"
        assert d["data"]["status"] == "running"

    def test_tool_progress_event_without_detail(self):
        from services.streaming.event_types import tool_progress_event

        evt = tool_progress_event("kpi_analysis", "done")
        assert "detail" not in evt.to_dict()["data"]

    def test_tool_end_event(self):
        from services.streaming.event_types import tool_end_event

        evt = tool_end_event("risk_analysis", step=2, success=True)
        d = evt.to_dict()
        assert d["type"] == "tool_end"
        assert d["data"]["success"] is True

    def test_final_response_event(self):
        from services.streaming.event_types import final_response_event

        evt = final_response_event("Done.", tools_used=["kpi_analysis"])
        d = evt.to_dict()
        assert d["type"] == "final_response"
        assert d["data"]["answer"] == "Done."
        assert d["data"]["tools_used"] == ["kpi_analysis"]

    def test_final_response_event_no_tools(self):
        from services.streaming.event_types import final_response_event

        evt = final_response_event("Direct answer.")
        assert "tools_used" not in evt.to_dict()["data"]


# ===================================================================
# 2. StreamingManager
# ===================================================================


class TestStreamingManager:
    """streamer.py — StreamingManager buffer, emit helpers, fallback."""

    def test_buffer_accumulates(self):
        from services.streaming.streamer import StreamingManager

        sm = StreamingManager("sess-1")
        sm.emit_llm_start(iteration=1)
        sm.emit_llm_end(iteration=1)
        assert len(sm.events) == 2
        assert sm.events[0]["type"] == "llm_start"
        assert sm.events[1]["type"] == "llm_end"

    def test_session_id_property(self):
        from services.streaming.streamer import StreamingManager

        sm = StreamingManager("abc-123")
        assert sm.session_id == "abc-123"

    def test_clear_buffer(self):
        from services.streaming.streamer import StreamingManager

        sm = StreamingManager("s")
        sm.emit_llm_start()
        assert len(sm.events) == 1
        sm.clear()
        assert len(sm.events) == 0

    def test_events_returns_copy(self):
        from services.streaming.streamer import StreamingManager

        sm = StreamingManager("s")
        sm.emit_llm_start()
        evts = sm.events
        evts.clear()
        assert len(sm.events) == 1  # original unmodified

    def test_tool_lifecycle(self):
        from services.streaming.streamer import StreamingManager

        sm = StreamingManager("s")
        sm.emit_tool_start("six_sigma_analysis", step=0)
        sm.emit_tool_progress("six_sigma_analysis", "running", step=0, detail="halfway")
        sm.emit_tool_end("six_sigma_analysis", step=0, success=True)
        types = [e["type"] for e in sm.events]
        assert types == ["tool_start", "tool_progress", "tool_end"]

    def test_stream_tool_progress_alias(self):
        from services.streaming.streamer import StreamingManager

        sm = StreamingManager("s")
        sm.stream_tool_progress("kpi_analysis", "in_progress")
        assert sm.events[0]["type"] == "tool_progress"
        assert sm.events[0]["data"]["tool"] == "kpi_analysis"

    def test_stream_llm_tokens(self):
        from services.streaming.streamer import StreamingManager

        sm = StreamingManager("s")

        def gen():
            yield "Hello"
            yield " world"

        result = sm.stream_llm_tokens(gen(), iteration=2)
        assert result == "Hello world"
        types = [e["type"] for e in sm.events]
        assert types == ["llm_token", "llm_token"]
        assert sm.events[0]["data"]["token"] == "Hello"
        assert sm.events[1]["data"]["iteration"] == 2

    def test_final_response(self):
        from services.streaming.streamer import StreamingManager

        sm = StreamingManager("s")
        sm.emit_final_response("analysis done", tools_used=["risk_analysis"])
        d = sm.events[0]
        assert d["type"] == "final_response"
        assert d["data"]["answer"] == "analysis done"

    def test_no_websocket_is_silent(self):
        """When connection manager is not importable, operations are no-ops."""
        from services.streaming.streamer import StreamingManager

        sm = StreamingManager("s")
        # Patch _get_connection_manager to return None
        with patch("services.streaming.streamer._get_connection_manager", return_value=None):
            sm.emit_llm_start()
            sm.emit_tool_start("x")
            sm.emit_final_response("done")
        # Buffer still works
        assert len(sm.events) == 3

    def test_get_streaming_manager_factory(self):
        from services.streaming.streamer import get_streaming_manager

        sm = get_streaming_manager("test-id")
        assert sm.session_id == "test-id"


# ===================================================================
# 3. Chat Orchestrator + Streaming Integration
# ===================================================================


def _make_llm_mock(responses):
    """Build a mock llm_generate_json that returns responses in sequence."""
    call_idx = {"i": 0}

    def mock_llm(*args, **kwargs):
        idx = call_idx["i"]
        call_idx["i"] += 1
        if idx < len(responses):
            return responses[idx]
        return {"response": {"action": "final_answer", "response": "fallback"}}

    return mock_llm


class TestChatOrchestratorStreaming:
    """Verify streaming events are emitted during chat orchestration."""

    def test_streamer_receives_llm_and_final_events(self):
        from services.streaming.streamer import StreamingManager
        from services.chat.orchestrator import handle_chat

        sm = StreamingManager("chat-1")
        mock_llm = _make_llm_mock([
            {"response": {"action": "final_answer", "response": "The sigma is 4.2"}}
        ])

        result = handle_chat(
            "What is the sigma level?",
            context={"kpis": []},
            llm_generate_json=mock_llm,
            streamer=sm,
        )

        types = [e["type"] for e in sm.events]
        assert "llm_start" in types
        assert "llm_end" in types
        assert "final_response" in types
        assert result["final_answer"] == "The sigma is 4.2"

    def test_streamer_receives_tool_events(self):
        from services.streaming.streamer import StreamingManager
        from services.chat.orchestrator import handle_chat

        sm = StreamingManager("chat-2")
        mock_llm = _make_llm_mock([
            {"response": {"action": "tool_call", "tool_name": "kpi_analysis",
                          "tool_input": {"kpis": [{"name": "ROP", "value": 50}]}}},
            {"response": {"action": "final_answer", "response": "KPI done"}},
        ])

        with patch("services.tools.handle_kpi_analysis") as mock_kpi:
            mock_kpi.return_value = {"kpis": [], "count": 0}
            result = handle_chat(
                "Analyse KPIs",
                llm_generate_json=mock_llm,
                streamer=sm,
            )

        types = [e["type"] for e in sm.events]
        assert "tool_start" in types
        assert "tool_end" in types
        assert "kpi_analysis" in result["tools_used"]

    def test_no_streamer_still_works(self):
        """Passing streamer=None (default) must not change behaviour."""
        from services.chat.orchestrator import handle_chat

        mock_llm = _make_llm_mock([
            {"response": {"action": "final_answer", "response": "ok"}}
        ])
        result = handle_chat("hi", llm_generate_json=mock_llm)
        assert result["final_answer"] == "ok"

    def test_streamer_failure_is_silent(self):
        """If streamer.emit_* raises, chat still completes."""
        from services.streaming.streamer import StreamingManager
        from services.chat.orchestrator import handle_chat

        sm = StreamingManager("chat-err")

        mock_llm = _make_llm_mock([
            {"response": {"action": "final_answer", "response": "still works"}}
        ])

        with patch.object(sm, "emit_llm_start", side_effect=RuntimeError("boom")), \
             patch.object(sm, "emit_llm_end", side_effect=RuntimeError("boom")), \
             patch.object(sm, "emit_final_response", side_effect=RuntimeError("boom")):
            result = handle_chat("test", llm_generate_json=mock_llm, streamer=sm)

        assert result["final_answer"] == "still works"

    def test_llm_failure_emits_llm_end_failed(self):
        from services.streaming.streamer import StreamingManager
        from services.chat.orchestrator import handle_chat

        sm = StreamingManager("chat-fail")

        def failing_llm(*a, **kw):
            raise ConnectionError("LLM down")

        result = handle_chat("test", llm_generate_json=failing_llm, streamer=sm)
        llm_end_events = [e for e in sm.events if e["type"] == "llm_end"]
        assert any(e["data"]["success"] is False for e in llm_end_events)


# ===================================================================
# 4. Agent Executor + Streaming Integration
# ===================================================================


class TestAgentExecutorStreaming:
    """Verify streaming events emitted during plan execution."""

    @pytest.fixture(autouse=True)
    def _ensure_tools(self):
        from services.tools.registry import _reset
        _reset()
        import importlib
        import services.tools as st
        importlib.reload(st)
        yield
        _reset()

    def test_executor_emits_tool_lifecycle(self):
        from services.streaming.streamer import StreamingManager
        from agents.orchestrator.executor import execute_plan

        sm = StreamingManager("agent-1")
        plan = [
            {"tool": "kpi_analysis", "input": {"kpis": [{"name": "A", "value": 1}]}, "reason": "score"},
        ]

        with patch("features.kpi.kpi_engine.process_kpis") as mock:
            mock.return_value = [{"name": "A", "priorityScore": 50}]
            results = execute_plan(plan, streamer=sm)

        types = [e["type"] for e in sm.events]
        assert types == ["tool_start", "tool_end"]
        assert sm.events[0]["data"]["tool"] == "kpi_analysis"

    def test_executor_no_streamer(self):
        """Existing tests pass without a streamer."""
        from agents.orchestrator.executor import execute_plan

        plan = [
            {"tool": "kpi_analysis", "input": {"kpis": [{"name": "A", "value": 1}]}, "reason": "score"},
        ]

        with patch("features.kpi.kpi_engine.process_kpis") as mock:
            mock.return_value = [{"name": "A", "priorityScore": 50}]
            results = execute_plan(plan)

        assert results[0]["status"] == "success"

    def test_executor_tool_failure_emits_end_false(self):
        from services.streaming.streamer import StreamingManager
        from agents.orchestrator.executor import execute_plan

        sm = StreamingManager("agent-fail")
        plan = [
            {"tool": "nonexistent_tool", "input": {}, "reason": "test"},
        ]
        results = execute_plan(plan, streamer=sm)
        end_events = [e for e in sm.events if e["type"] == "tool_end"]
        assert end_events[0]["data"]["success"] is False

    def test_executor_multiple_steps(self):
        from services.streaming.streamer import StreamingManager
        from agents.orchestrator.executor import execute_plan

        sm = StreamingManager("agent-multi")
        plan = [
            {"tool": "kpi_analysis", "input": {"kpis": [{"name": "A", "value": 1}]}, "reason": "score"},
            {"tool": "six_sigma_analysis", "input": {"kpis": [{"name": "A", "value": 1}]}, "reason": "sigma"},
        ]

        with patch("features.kpi.kpi_engine.process_kpis") as m1, \
             patch("features.six_sigma.run_six_sigma") as m2:
            m1.return_value = [{"name": "A", "priorityScore": 50}]
            m2.return_value = {"sigmaLevel": 4}
            results = execute_plan(plan, stop_on_failure=False, streamer=sm)

        types = [e["type"] for e in sm.events]
        assert types == ["tool_start", "tool_end", "tool_start", "tool_end"]
        assert sm.events[0]["data"]["step"] == 0
        assert sm.events[2]["data"]["step"] == 1


# ===================================================================
# 5. Module Exports
# ===================================================================


class TestModuleExports:
    """Verify __init__.py re-exports."""

    def test_streaming_public_api(self):
        from services.streaming import (
            StreamingManager,
            get_streaming_manager,
            StreamEvent,
            ALL_EVENT_TYPES,
            LLM_START,
            TOOL_END,
            FINAL_RESPONSE,
        )
        assert LLM_START == "llm_start"
        assert TOOL_END == "tool_end"
        assert FINAL_RESPONSE == "final_response"
