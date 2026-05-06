"""
Tests for the Observability Layer (services/observability).

Covers:
  - Structured logger: all event types, capture_exception
  - Tracer: start_trace, end_trace, add_step, add_llm_call, recent traces
  - Metrics: latency, tool usage, error rates, snapshot, reset
  - Chat Orchestrator integration: trace creation, metrics recording
  - Agent Orchestrator integration: trace creation, metrics recording
  - Tool Dispatcher integration: latency + usage recording
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_observability():
    """Reset metrics and tracer state before each test."""
    from services.observability.metrics import _reset as reset_metrics
    from services.observability.tracer import _reset as reset_tracer
    reset_metrics()
    reset_tracer()
    yield
    reset_metrics()
    reset_tracer()


@pytest.fixture()
def _ensure_tools():
    """Fresh tool registry for integration tests."""
    from services.tools.registry import _reset
    _reset()
    import importlib
    import services.tools as st
    importlib.reload(st)
    yield
    _reset()


# ===================================================================
# 1. Structured Logger
# ===================================================================


class TestStructuredLogger:

    def test_request_event(self, caplog):
        from services.observability.logger import request

        with caplog.at_level(logging.INFO, logger="transiq.observability"):
            request("Forecast ROP", trace_id="abc", component="chat")

        assert len(caplog.records) == 1
        data = json.loads(caplog.records[0].message)
        assert data["event"] == "request"
        assert data["query"] == "Forecast ROP"
        assert data["trace_id"] == "abc"
        assert data["component"] == "chat"

    def test_tool_call_event(self, caplog):
        from services.observability.logger import tool_call

        with caplog.at_level(logging.INFO, logger="transiq.observability"):
            tool_call("kpi_analysis", status="success", duration_ms=120.5, step=1)

        data = json.loads(caplog.records[0].message)
        assert data["event"] == "tool_call"
        assert data["tool"] == "kpi_analysis"
        assert data["duration_ms"] == 120.5
        assert data["step"] == 1

    def test_llm_call_event(self, caplog):
        from services.observability.logger import llm_call

        with caplog.at_level(logging.INFO, logger="transiq.observability"):
            llm_call(status="success", duration_ms=450, iteration=2, trace_id="t1")

        data = json.loads(caplog.records[0].message)
        assert data["event"] == "llm_call"
        assert data["iteration"] == 2

    def test_response_event(self, caplog):
        from services.observability.logger import response

        with caplog.at_level(logging.INFO, logger="transiq.observability"):
            response(component="chat_orchestrator", duration_ms=500,
                     tools_used=["kpi_analysis"], success=True)

        data = json.loads(caplog.records[0].message)
        assert data["event"] == "response"
        assert data["tools_used"] == ["kpi_analysis"]

    def test_error_event(self, caplog):
        from services.observability.logger import error

        with caplog.at_level(logging.ERROR, logger="transiq.observability"):
            error("tool_dispatcher", error_msg="boom", error_type="RuntimeError",
                  trace_id="xyz")

        data = json.loads(caplog.records[0].message)
        assert data["event"] == "error"
        assert data["component"] == "tool_dispatcher"
        assert data["error_type"] == "RuntimeError"

    def test_capture_exception(self, caplog):
        from services.observability.logger import capture_exception

        try:
            raise ValueError("bad input")
        except ValueError as exc:
            with caplog.at_level(logging.ERROR, logger="transiq.observability"):
                capture_exception("parser", exc, trace_id="t2")

        data = json.loads(caplog.records[0].message)
        assert data["event"] == "error"
        assert data["error_type"] == "ValueError"
        assert "bad input" in data["error"]
        assert "Traceback" in data["stack_trace"]

    def test_extra_fields_merged(self, caplog):
        from services.observability.logger import tool_call

        with caplog.at_level(logging.INFO, logger="transiq.observability"):
            tool_call("kpi_analysis", extra={"custom_key": 42})

        data = json.loads(caplog.records[0].message)
        assert data["custom_key"] == 42


# ===================================================================
# 2. Tracer
# ===================================================================


class TestTracer:

    def test_start_and_end_trace(self):
        from services.observability.tracer import start_trace, end_trace

        t = start_trace("test query", component="test")
        assert t.trace_id
        assert t.query == "test query"
        assert t.component == "test"

        summary = end_trace(t.trace_id)
        assert summary["trace_id"] == t.trace_id
        assert summary["duration_ms"] >= 0

    def test_add_steps(self):
        from services.observability.tracer import start_trace, end_trace

        t = start_trace("q")
        t.add_step("kpi_analysis", status="success", duration_ms=100, step=0)
        t.add_step("risk_analysis", status="error", duration_ms=50, step=1)

        summary = end_trace(t.trace_id)
        assert len(summary["steps"]) == 2
        assert summary["steps"][0]["tool"] == "kpi_analysis"
        assert summary["tools_used"] == ["kpi_analysis", "risk_analysis"]

    def test_add_llm_call(self):
        from services.observability.tracer import start_trace, end_trace

        t = start_trace("q")
        t.add_llm_call(status="success", duration_ms=200, iteration=1)
        summary = end_trace(t.trace_id)
        assert summary["steps"][0]["tool"] == "__llm__"
        # __llm__ should not appear in tools_used
        assert "__llm__" not in summary["tools_used"]

    def test_add_error(self):
        from services.observability.tracer import start_trace, end_trace

        t = start_trace("q")
        t.add_error("tool_dispatcher", "boom", error_type="RuntimeError")
        summary = end_trace(t.trace_id)
        assert len(summary["errors"]) == 1
        assert summary["errors"][0]["error"] == "boom"

    def test_get_trace(self):
        from services.observability.tracer import start_trace, end_trace, get_trace

        t = start_trace("q")
        # Active trace
        active = get_trace(t.trace_id)
        assert active is not None
        assert active["query"] == "q"

        end_trace(t.trace_id)
        # Completed trace
        completed = get_trace(t.trace_id)
        assert completed is not None
        assert completed["duration_ms"] > 0

    def test_get_recent_traces(self):
        from services.observability.tracer import start_trace, end_trace, get_recent_traces

        for i in range(5):
            t = start_trace(f"q{i}")
            end_trace(t.trace_id)

        recent = get_recent_traces(limit=3)
        assert len(recent) == 3
        # Newest first
        assert recent[0]["query"] == "q4"

    def test_unknown_trace_id(self):
        from services.observability.tracer import end_trace

        result = end_trace("nonexistent")
        assert result.get("error") == "unknown trace"

    def test_custom_trace_id(self):
        from services.observability.tracer import start_trace, end_trace

        t = start_trace("q", trace_id="custom-123")
        assert t.trace_id == "custom-123"
        end_trace("custom-123")


# ===================================================================
# 3. Metrics
# ===================================================================


class TestMetrics:

    def test_record_and_get_latency(self):
        from services.observability.metrics import record_latency, get_latency_stats

        for v in [100, 200, 300, 400, 500]:
            record_latency("test", v)

        stats = get_latency_stats("test")
        assert stats["count"] == 5
        assert stats["mean_ms"] == 300.0
        assert stats["p50_ms"] == 300.0
        assert stats["max_ms"] == 500.0

    def test_empty_latency(self):
        from services.observability.metrics import get_latency_stats

        stats = get_latency_stats("nonexistent")
        assert stats["count"] == 0

    def test_record_tool_usage(self):
        from services.observability.metrics import record_tool_usage, get_tool_usage

        record_tool_usage("kpi_analysis")
        record_tool_usage("kpi_analysis")
        record_tool_usage("risk_analysis")

        usage = get_tool_usage()
        assert usage["kpi_analysis"] == 2
        assert usage["risk_analysis"] == 1

    def test_record_error(self):
        from services.observability.metrics import record_error, get_error_rates, get_error_count

        record_error("tool_dispatcher", "kpi_analysis")
        record_error("tool_dispatcher", "kpi_analysis")
        record_error("tool_dispatcher", "risk_analysis")

        rates = get_error_rates()
        assert rates["tool_dispatcher"]["kpi_analysis"] == 2
        assert get_error_count("tool_dispatcher") == 3

    def test_record_request(self):
        from services.observability.metrics import record_request, get_request_counts

        record_request("chat_orchestrator")
        record_request("chat_orchestrator")
        record_request("agent_orchestrator")

        counts = get_request_counts()
        assert counts["chat_orchestrator"] == 2
        assert counts["agent_orchestrator"] == 1

    def test_snapshot(self):
        from services.observability.metrics import (
            record_latency, record_tool_usage, record_error,
            record_request, snapshot,
        )

        record_latency("chat", 100)
        record_tool_usage("kpi_analysis")
        record_error("tool_dispatcher", "x")
        record_request("chat")

        snap = snapshot()
        assert "latency" in snap
        assert "tool_usage" in snap
        assert "errors" in snap
        assert "requests" in snap

    def test_all_latency_stats(self):
        from services.observability.metrics import record_latency, get_all_latency_stats

        record_latency("a", 10)
        record_latency("b", 20)

        stats = get_all_latency_stats()
        components = {s["component"] for s in stats}
        assert components == {"a", "b"}

    def test_latency_trim(self):
        from services.observability.metrics import record_latency, get_latency_stats
        from services.observability.metrics import _MAX_LATENCY_SAMPLES

        for i in range(_MAX_LATENCY_SAMPLES + 100):
            record_latency("trim", float(i))

        stats = get_latency_stats("trim")
        assert stats["count"] <= _MAX_LATENCY_SAMPLES


# ===================================================================
# 4. Chat Orchestrator Integration
# ===================================================================


class TestChatOrchestratorObservability:

    def test_trace_created_and_metrics_recorded(self):
        from services.chat.orchestrator import handle_chat
        from services.observability.metrics import get_request_counts, get_latency_stats
        from services.observability.tracer import get_recent_traces

        def mock_llm(*a, **kw):
            return {"response": {"action": "final_answer", "response": "ok"}}

        handle_chat("test query", llm_generate_json=mock_llm)

        # Metrics recorded
        counts = get_request_counts()
        assert counts.get("chat_orchestrator", 0) >= 1

        lat = get_latency_stats("chat_orchestrator")
        assert lat["count"] >= 1

        llm_lat = get_latency_stats("llm")
        assert llm_lat["count"] >= 1

        # Trace completed
        traces = get_recent_traces(limit=1)
        assert len(traces) >= 1
        assert traces[0]["component"] == "chat_orchestrator"

    def test_tool_metrics_from_chat(self, _ensure_tools):
        from services.chat.orchestrator import handle_chat
        from services.observability.metrics import get_tool_usage

        call_idx = {"i": 0}

        def mock_llm(*a, **kw):
            idx = call_idx["i"]
            call_idx["i"] += 1
            if idx == 0:
                return {"response": {"action": "tool_call", "tool_name": "kpi_analysis",
                                     "tool_input": {"kpis": [{"name": "A", "value": 1}]}}}
            return {"response": {"action": "final_answer", "response": "done"}}

        with patch("features.kpi.kpi_engine.process_kpis") as mock:
            mock.return_value = [{"name": "A", "priorityScore": 50}]
            handle_chat("test", llm_generate_json=mock_llm)

        usage = get_tool_usage()
        assert usage.get("kpi_analysis", 0) >= 1

    def test_llm_failure_records_error_metric(self):
        from services.chat.orchestrator import handle_chat
        from services.observability.metrics import get_error_rates

        def failing_llm(*a, **kw):
            raise ConnectionError("down")

        handle_chat("test", llm_generate_json=failing_llm)
        errors = get_error_rates()
        assert errors.get("chat_orchestrator", {}).get("llm_failure", 0) >= 1


# ===================================================================
# 5. Agent Orchestrator Integration
# ===================================================================


class TestAgentOrchestratorObservability:

    @pytest.fixture(autouse=True)
    def _tools(self):
        from services.tools.registry import _reset
        _reset()
        import importlib
        import services.tools as st
        importlib.reload(st)
        yield
        _reset()

    def test_trace_and_metrics(self):
        from agents.orchestrator import run_agent
        from services.observability.metrics import get_request_counts, get_latency_stats
        from services.observability.tracer import get_recent_traces

        call_idx = {"i": 0}

        def mock_llm(*a, **kw):
            idx = call_idx["i"]
            call_idx["i"] += 1
            if idx == 0:
                return {"response": json.dumps([
                    {"tool": "kpi_analysis",
                     "input": {"kpis": [{"name": "A", "value": 1}]},
                     "reason": "score"},
                ])}
            if idx == 1:
                return {"response": {"summary": "done"}}
            return {"response": {"answer": "ok"}}

        with patch("features.kpi.kpi_engine.process_kpis") as mock:
            mock.return_value = [{"name": "A", "priorityScore": 50}]
            run_agent("test", llm_generate_json=mock_llm)

        counts = get_request_counts()
        assert counts.get("agent_orchestrator", 0) >= 1

        lat = get_latency_stats("agent_orchestrator")
        assert lat["count"] >= 1

        traces = get_recent_traces(limit=1)
        assert len(traces) >= 1
        assert traces[0]["component"] == "agent_orchestrator"


# ===================================================================
# 6. Tool Dispatcher Integration
# ===================================================================


class TestToolDispatcherObservability:

    @pytest.fixture(autouse=True)
    def _tools(self):
        from services.tools.registry import _reset
        _reset()
        import importlib
        import services.tools as st
        importlib.reload(st)
        yield
        _reset()

    def test_success_records_latency_and_usage(self):
        from services.tools.dispatcher import dispatch_tool
        from services.observability.metrics import get_tool_usage, get_latency_stats

        with patch("features.kpi.kpi_engine.process_kpis") as mock:
            mock.return_value = [{"name": "A"}]
            dispatch_tool("kpi_analysis", {"kpis": [{"name": "A", "value": 1}]})

        usage = get_tool_usage()
        assert usage.get("kpi_analysis", 0) >= 1

        lat = get_latency_stats("tool.kpi_analysis")
        assert lat["count"] >= 1

    def test_failure_records_error(self):
        from services.tools.dispatcher import dispatch_tool
        from services.observability.metrics import get_error_rates

        with patch("features.kpi.kpi_engine.process_kpis",
                   side_effect=RuntimeError("crash")):
            dispatch_tool("kpi_analysis", {"kpis": [{"name": "A", "value": 1}]})

        errors = get_error_rates()
        assert errors.get("tool_dispatcher", {}).get("kpi_analysis", 0) >= 1


# ===================================================================
# 7. Module Exports
# ===================================================================


class TestModuleExports:

    def test_public_api(self):
        from services.observability import (
            obs_logger,
            metrics,
            start_trace,
            end_trace,
            get_trace,
            get_recent_traces,
            Trace,
            log_request,
            log_tool_call,
            log_llm_call,
            log_response,
            log_error,
            log_capture_exception,
        )
        assert callable(start_trace)
        assert callable(log_request)
