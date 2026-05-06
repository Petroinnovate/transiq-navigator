"""
End-to-End Integration Tests
=============================

Tests the full pipeline:  User → Chat/Agent → Planner → Tools → Composer → Response → Streaming

These tests call **real engines** (KPI, Six Sigma, Predictive, Risk) with
realistic data, only mocking the LLM layer.  This validates:

  * Planner → Executor → Tool dispatch → Result composition
  * Chat orchestrator reactive loop with real tool outputs
  * Memory injection and episode storage
  * Streaming event emission across the full flow
  * Correct final response structure
  * Error handling and recovery
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# ═══════════════════════════════════════════════════════════════════════
# Realistic test data
# ═══════════════════════════════════════════════════════════════════════

TEST_KPIS = [
    {
        "name": "ROP",
        "title": "Rate of Penetration",
        "unit": "ft/hr",
        "value": 85,
        "target": 100,
        "category": "drilling",
        "financialImpactScore": 88,
        "riskScore": 65,
        "deviationScore": 15,
        "trendScore": 80,
        "confidence": 0.92,
        "trend": "up",
        "changeType": "positive",
        "status": "warning",
        "direction": "increase",
        "history": [75, 78, 80, 82, 85, 86, 87, 88, 84, 85],
    },
    {
        "name": "NPT",
        "title": "Non-Productive Time",
        "unit": "hours",
        "value": 12,
        "target": 5,
        "category": "safety",
        "financialImpactScore": 75,
        "riskScore": 80,
        "deviationScore": 70,
        "trendScore": 30,
        "confidence": 0.85,
        "trend": "up",
        "changeType": "negative",
        "status": "critical",
        "direction": "decrease",
        "history": [8, 9, 10, 11, 12, 11, 13, 12, 14, 12],
    },
    {
        "name": "WOB",
        "title": "Weight on Bit",
        "unit": "klbs",
        "value": 22,
        "target": 25,
        "category": "drilling",
        "financialImpactScore": 40,
        "riskScore": 30,
        "deviationScore": 12,
        "trendScore": 60,
        "confidence": 0.78,
        "trend": "stable",
        "changeType": "positive",
        "status": "normal",
        "direction": "increase",
        "history": [20, 21, 22, 21, 22, 23, 22, 21, 22, 22],
    },
]


# ═══════════════════════════════════════════════════════════════════════
# LLM mock factories
# ═══════════════════════════════════════════════════════════════════════

def _make_llm_sequence(responses: List[Dict[str, Any]]):
    """Return a callable that yields LLM responses in order."""
    call_idx = {"n": 0}

    def _llm_mock(prompt: str, **kwargs) -> Dict[str, Any]:
        idx = call_idx["n"]
        call_idx["n"] += 1
        if idx < len(responses):
            return {"response": responses[idx], "provider_used": "mock", "error": None}
        # Default final answer for overflow
        return {
            "response": {"action": "final_answer", "response": "Analysis complete."},
            "provider_used": "mock",
            "error": None,
        }

    return _llm_mock


# ═══════════════════════════════════════════════════════════════════════
# 1. Six Sigma End-to-End Flow
# ═══════════════════════════════════════════════════════════════════════

class TestSixSigmaE2E:
    """Full flow: Chat → KPI scoring → Six Sigma analysis."""

    def test_six_sigma_via_chat(self):
        """LLM decides to call kpi_analysis then six_sigma, gets real results."""
        from services.chat.orchestrator import handle_chat

        llm = _make_llm_sequence([
            # Iteration 1: LLM decides to call kpi_analysis first
            {
                "action": "tool_call",
                "tool_name": "kpi_analysis",
                "tool_input": {"kpis": TEST_KPIS},
            },
            # Iteration 2: LLM sees KPI results, calls six_sigma
            {
                "action": "tool_call",
                "tool_name": "six_sigma_analysis",
                "tool_input": {"kpis": TEST_KPIS},
            },
            # Iteration 3: LLM synthesizes final answer
            {
                "action": "final_answer",
                "response": (
                    "Six Sigma analysis shows process instability. "
                    "Cpk indicates the process needs improvement. "
                    "Recommendations: reduce variation in ROP."
                ),
            },
        ])

        result = handle_chat(
            "Analyze process capability for our drilling KPIs",
            context={"kpis": TEST_KPIS},
            llm_generate_json=llm,
        )

        # Structure validation
        assert result["query"] == "Analyze process capability for our drilling KPIs"
        assert result["final_answer"] != ""
        assert len(result["tools_used"]) >= 2
        assert "kpi_analysis" in result["tools_used"]
        assert "six_sigma_analysis" in result["tools_used"]

        # Steps recorded
        assert len(result["steps"]) == 3
        assert result["steps"][0]["action"] == "tool_call"
        assert result["steps"][0]["tool_name"] == "kpi_analysis"

        # First tool call returned real data
        kpi_result = result["steps"][0]["tool_result"]
        assert kpi_result["status"] == "success"
        assert "result" in kpi_result
        assert kpi_result["result"]["count"] == 3

        # Second tool call returned real six sigma data
        sigma_result = result["steps"][1]["tool_result"]
        assert sigma_result["status"] == "success"
        sigma_data = sigma_result["result"]
        assert "sigmaLevel" in sigma_data
        assert "dmaic" in sigma_data

    def test_six_sigma_direct_agent(self):
        """Agent path: Planner creates multi-step plan, executor runs real tools."""
        from agents.orchestrator import run_agent

        llm = _make_llm_sequence([
            # Plan: 2-step analysis
            {
                "steps": [
                    {
                        "tool": "kpi_analysis",
                        "input": {"kpis": TEST_KPIS},
                        "reason": "Score and prioritize KPIs",
                    },
                    {
                        "tool": "six_sigma_analysis",
                        "input": {"kpis": TEST_KPIS},
                        "reason": "Run DMAIC analysis on scored KPIs",
                    },
                ]
            },
            # Compose response LLM call (from composer)
            {
                "summary": "Process analysis complete. ROP shows improvement potential.",
                "additional_insights": [],
                "additional_recommendations": [],
            },
            # Final answer LLM call
            {"answer": "Analysis shows sigma level needs improvement. Focus on ROP variation."},
        ])

        result = run_agent(
            "Analyze process capability for drilling KPIs",
            context={"kpis": TEST_KPIS},
            llm_generate_json=llm,
        )

        assert result["valid"] is True
        assert len(result["plan"]) == 2
        assert len(result["steps"]) == 2
        assert result["tools_used"] == ["kpi_analysis", "six_sigma_analysis"]
        assert result["final_answer"] != ""

        # Composed response available
        assert result["composed"] is not None
        assert "summary" in result["composed"]
        assert "insights" in result["composed"]
        assert "metrics" in result["composed"]
        assert "recommendations" in result["composed"]


# ═══════════════════════════════════════════════════════════════════════
# 2. Multi-Step DMAIC Flow
# ═══════════════════════════════════════════════════════════════════════

class TestMultiStepDMAICE2E:
    """Full DMAIC pipeline: KPI → Forecast → Risk → Six Sigma."""

    def test_full_dmaic_pipeline(self):
        """Agent plans and executes all 4 engines in sequence."""
        from agents.orchestrator import run_agent

        single_kpi = TEST_KPIS[0]  # ROP with history

        llm = _make_llm_sequence([
            # Plan: 4-step pipeline
            {
                "steps": [
                    {
                        "tool": "kpi_analysis",
                        "input": {"kpis": [single_kpi]},
                        "reason": "Score the KPI",
                    },
                    {
                        "tool": "predictive_forecast",
                        "input": {"kpi": single_kpi},
                        "reason": "Forecast trend",
                    },
                    {
                        "tool": "risk_analysis",
                        "input": {"kpi": single_kpi, "forecast_data": None},
                        "reason": "Assess risk",
                    },
                    {
                        "tool": "six_sigma_analysis",
                        "input": {"kpis": [single_kpi]},
                        "reason": "Full DMAIC analysis",
                    },
                ]
            },
            # Compose LLM call
            {
                "summary": "Full DMAIC analysis complete for ROP.",
                "additional_insights": ["ROP trending upward with moderate risk"],
                "additional_recommendations": ["Monitor closely"],
            },
            # Final answer
            {"answer": "ROP DMAIC analysis complete with forecast and risk assessment."},
        ])

        result = run_agent(
            "Why is ROP underperforming and what should we do?",
            context={"kpis": [single_kpi]},
            llm_generate_json=llm,
        )

        assert result["valid"] is True
        assert len(result["tools_used"]) >= 3  # At least 3 of 4 should succeed
        assert "final_answer" in result
        assert result["final_answer"] != ""

        # Verify each step ran
        for step in result["steps"]:
            # Each step should have a result or a clear error
            assert step["status"] in ("success", "error")
            if step["status"] == "success":
                assert step["result"] is not None

    def test_kpi_scoring_accuracy(self):
        """Verify the KPI engine produces correct priority ordering."""
        from features.kpi.kpi_engine import process_kpis

        enriched = process_kpis(TEST_KPIS)

        # All KPIs should have priorityScore
        for kpi in enriched:
            assert "priorityScore" in kpi
            assert 0 <= kpi["priorityScore"] <= 100
            assert "visibility" in kpi
            assert kpi["visibility"] in ("primary", "secondary", "hidden")

        # ROP or NPT should score highest (both have high impact scores)
        names_by_score = [k["name"] for k in enriched]
        assert names_by_score[0] in ("ROP", "NPT")  # Top priority first
        # WOB (low scores) should NOT be first
        assert names_by_score[0] != "WOB"


# ═══════════════════════════════════════════════════════════════════════
# 3. Error Handling
# ═══════════════════════════════════════════════════════════════════════

class TestErrorHandlingE2E:
    """System handles bad inputs gracefully — no crashes."""

    def test_invalid_tool_name(self):
        """Chat handles LLM calling a non-existent tool."""
        from services.chat.orchestrator import handle_chat

        llm = _make_llm_sequence([
            {
                "action": "tool_call",
                "tool_name": "nonexistent_tool",
                "tool_input": {},
            },
            {
                "action": "final_answer",
                "response": "I couldn't find the right tool. Please provide more context.",
            },
        ])

        result = handle_chat("Analyze ???", llm_generate_json=llm)
        assert result["final_answer"] != ""
        # Should not crash
        assert "steps" in result

    def test_empty_kpi_list(self):
        """Six Sigma with empty KPIs doesn't crash."""
        from features.six_sigma import run_six_sigma

        result = run_six_sigma(kpis=[])
        # Should return a result (possibly with warnings) but NOT crash
        assert isinstance(result, dict)

    def test_llm_failure_recovery(self):
        """Chat handles complete LLM failure gracefully."""
        from services.chat.orchestrator import handle_chat

        def _failing_llm(prompt, **kwargs):
            raise RuntimeError("LLM provider unavailable")

        result = handle_chat("Test query", llm_generate_json=_failing_llm)
        assert result["final_answer"] != ""
        # Expect a graceful degradation message
        assert "unable" in result["final_answer"].lower() or len(result["final_answer"]) > 0

    def test_partial_plan_failure(self):
        """Agent still produces output when some steps fail."""
        from agents.orchestrator import run_agent

        llm = _make_llm_sequence([
            # Plan includes a bogus tool
            {
                "steps": [
                    {
                        "tool": "kpi_analysis",
                        "input": {"kpis": TEST_KPIS},
                        "reason": "Score KPIs",
                    },
                    {
                        "tool": "nonexistent_engine",
                        "input": {},
                        "reason": "This will fail",
                    },
                ]
            },
            # Compose (may or may not be called)
            {
                "summary": "Partial analysis with some errors.",
                "additional_insights": [],
                "additional_recommendations": [],
            },
            # Final answer
            {"answer": "Analysis partial — some steps failed."},
        ])

        # stop_on_failure=False so second step still runs
        result = run_agent(
            "Do full analysis",
            context={"kpis": TEST_KPIS},
            llm_generate_json=llm,
            stop_on_failure=False,
        )

        assert "steps" in result
        assert result["final_answer"] != ""

    def test_bad_input_doesnt_crash_dispatcher(self):
        """Tool dispatcher rejects malformed input cleanly."""
        from services.tools import dispatch_tool

        result = dispatch_tool("kpi_analysis", {"wrong_key": 123})
        assert result["status"] == "error"
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════
# 4. Memory Integration
# ═══════════════════════════════════════════════════════════════════════

class TestMemoryE2E:
    """Memory system stores episodes and injects context into prompts."""

    def test_memory_store_and_recall(self):
        """Execute a chat, store episode, then recall it in next query."""
        from services.chat.orchestrator import handle_chat
        from services.memory.cortex import Cortex
        from services.memory.store import MemoryStore

        cortex = Cortex(store=MemoryStore())

        # First chat — analyze KPIs
        llm_calls = []

        def tracking_llm(prompt, **kwargs):
            llm_calls.append(prompt)
            return {
                "response": {
                    "action": "tool_call",
                    "tool_name": "kpi_analysis",
                    "tool_input": {"kpis": TEST_KPIS},
                },
                "provider_used": "mock",
                "error": None,
            }

        # Override to give final answer on second call
        call_count = {"n": 0}

        def sequenced_llm(prompt, **kwargs):
            call_count["n"] += 1
            llm_calls.append(prompt)
            if call_count["n"] == 1:
                return {
                    "response": {
                        "action": "tool_call",
                        "tool_name": "kpi_analysis",
                        "tool_input": {"kpis": TEST_KPIS},
                    },
                    "provider_used": "mock",
                    "error": None,
                }
            return {
                "response": {
                    "action": "final_answer",
                    "response": "ROP is the top priority KPI with score 92.",
                },
                "provider_used": "mock",
                "error": None,
            }

        result1 = handle_chat(
            "Analyze uptime KPI",
            context={"kpis": TEST_KPIS},
            llm_generate_json=sequenced_llm,
            memory=cortex,
        )

        # Store Episode
        ep_id = cortex.store_episode(result1)
        assert ep_id > 0

        # Second chat — memory should include the first episode
        call_count["n"] = 0
        llm_calls.clear()

        def recall_llm(prompt, **kwargs):
            call_count["n"] += 1
            llm_calls.append(prompt)
            return {
                "response": {
                    "action": "final_answer",
                    "response": "Based on previous analysis, ROP was the top KPI.",
                },
                "provider_used": "mock",
                "error": None,
            }

        result2 = handle_chat(
            "What changed from last analysis?",
            llm_generate_json=recall_llm,
            memory=cortex,
        )

        assert result2["final_answer"] != ""
        # The memory text should have been injected into the prompt
        assert len(llm_calls) >= 1
        # The recalled prompt should contain memory of previous episode
        assert "PREVIOUS" in llm_calls[0] or "MEMORY" in llm_calls[0] or "kpi_analysis" in llm_calls[0].lower()


# ═══════════════════════════════════════════════════════════════════════
# 5. Streaming Events
# ═══════════════════════════════════════════════════════════════════════

class TestStreamingE2E:
    """Streaming events are emitted correctly through the full pipeline."""

    def test_chat_streaming_events(self):
        """Chat loop emits llm_start, tool_start, tool_end, llm_end, final_response."""
        from services.chat.orchestrator import handle_chat
        from services.streaming.streamer import StreamingManager

        streamer = StreamingManager(session_id="test-stream-e2e")

        llm = _make_llm_sequence([
            {
                "action": "tool_call",
                "tool_name": "kpi_analysis",
                "tool_input": {"kpis": TEST_KPIS},
            },
            {
                "action": "final_answer",
                "response": "KPI analysis complete.",
            },
        ])

        result = handle_chat(
            "Score my KPIs",
            context={"kpis": TEST_KPIS},
            llm_generate_json=llm,
            streamer=streamer,
        )

        # Check event sequence from the buffer
        emitted = streamer._buffer
        event_types = [e["type"] for e in emitted]
        assert "llm_start" in event_types
        assert "llm_end" in event_types
        assert "tool_start" in event_types
        assert "tool_end" in event_types

        # All events have timestamps
        for e in emitted:
            assert "timestamp" in e

    def test_agent_streaming_events(self):
        """Agent executor emits tool lifecycle events."""
        from agents.orchestrator import run_agent
        from services.streaming.streamer import StreamingManager

        streamer = StreamingManager(session_id="test-agent-stream")

        llm = _make_llm_sequence([
            {
                "steps": [
                    {"tool": "kpi_analysis", "input": {"kpis": TEST_KPIS}, "reason": "Score"},
                ]
            },
            {"summary": "Done.", "additional_insights": [], "additional_recommendations": []},
            {"answer": "KPIs scored."},
        ])

        result = run_agent(
            "Score KPIs",
            context={"kpis": TEST_KPIS},
            llm_generate_json=llm,
            streamer=streamer,
        )

        event_types = [e["type"] for e in streamer._buffer]
        assert "tool_start" in event_types
        assert "tool_end" in event_types


# ═══════════════════════════════════════════════════════════════════════
# 6. Tool Accuracy — Real Engine Outputs
# ═══════════════════════════════════════════════════════════════════════

class TestToolAccuracy:
    """Validate engines produce numerically correct, well-structured outputs."""

    def test_kpi_engine_scoring(self):
        """KPI engine enriches with priority scores in valid range."""
        from features.kpi.kpi_engine import process_kpis

        enriched = process_kpis(TEST_KPIS)
        assert len(enriched) == 3

        for kpi in enriched:
            assert "priorityScore" in kpi
            assert isinstance(kpi["priorityScore"], (int, float))
            assert 0 <= kpi["priorityScore"] <= 100
            assert kpi["visibility"] in ("primary", "secondary", "hidden")
            assert isinstance(kpi["selectionReason"], str)

    def test_six_sigma_real_output(self):
        """Six Sigma engine returns DMAIC structure with real numeric values."""
        from features.six_sigma import run_six_sigma

        result = run_six_sigma(kpis=TEST_KPIS)

        assert "sigmaLevel" in result
        assert "dmaic" in result
        assert "dataQuality" in result

        # Sigma should be a string (could be "3.2σ" or "N/A" depending on data)
        assert isinstance(result["sigmaLevel"], str)
        assert len(result["sigmaLevel"]) > 0

        # DMAIC should have at least some phases
        dmaic = result["dmaic"]
        assert isinstance(dmaic, dict)
        assert len(dmaic) > 0

    def test_predictive_engine_with_history(self):
        """Predictive engine produces forecast from KPI history."""
        from features.predictive.predictive_engine import forecast_kpi

        kpi = TEST_KPIS[0]  # ROP with 10 history points
        result = forecast_kpi(kpi)

        # Should NOT be None (has 10 history points)
        assert result is not None
        assert "forecast" in result
        assert isinstance(result["forecast"], list)
        assert len(result["forecast"]) > 0
        assert "trend" in result
        assert result["trend"] in ("up", "down", "stable")
        assert "modelsUsed" in result
        assert len(result["modelsUsed"]) >= 1

    def test_predictive_engine_insufficient_data(self):
        """Predictive engine returns None when history is too short."""
        from features.predictive.predictive_engine import forecast_kpi

        kpi = {"name": "Short", "history": [1, 2]}  # Only 2 points < 5 minimum
        result = forecast_kpi(kpi)
        assert result is None

    def test_risk_engine(self):
        """Risk engine detects risk level from KPI + forecast data."""
        from features.risk.risk_engine import detect_risk, generate_decision
        from features.predictive.predictive_engine import forecast_kpi

        kpi = TEST_KPIS[0]
        forecast = forecast_kpi(kpi)

        risk = detect_risk(kpi, forecast)
        assert risk is not None or forecast is None  # Risk needs forecast
        if risk is not None:
            assert "riskLevel" in risk
            assert risk["riskLevel"] in ("low", "medium", "high", "critical")
            assert "breachPredicted" in risk
            assert isinstance(risk["breachPredicted"], bool)

            decision = generate_decision(kpi, forecast, risk)
            assert isinstance(decision, str)
            assert len(decision) > 0

    def test_response_composer_with_real_data(self):
        """Response composer formats real engine outputs correctly."""
        from services.response.composer import compose_response
        from features.kpi.kpi_engine import process_kpis
        from features.six_sigma import run_six_sigma

        enriched = process_kpis(TEST_KPIS)
        sigma = run_six_sigma(TEST_KPIS)

        # Build agent-style step results
        steps = [
            {
                "step": 0,
                "tool": "kpi_analysis",
                "status": "success",
                "result": {"kpis": enriched, "count": len(enriched)},
                "error": None,
            },
            {
                "step": 1,
                "tool": "six_sigma_analysis",
                "status": "success",
                "result": sigma,
                "error": None,
            },
        ]

        composed = compose_response(
            "Analyze drilling KPIs",
            steps,
            llm_generate_json=None,  # Use fallback summary
        )

        assert "summary" in composed
        assert "insights" in composed
        assert isinstance(composed["insights"], list)
        assert "metrics" in composed
        assert isinstance(composed["metrics"], dict)
        assert "recommendations" in composed
        assert isinstance(composed["recommendations"], list)
        assert composed["summary"] != ""


# ═══════════════════════════════════════════════════════════════════════
# 7. Response Structure Compliance
# ═══════════════════════════════════════════════════════════════════════

class TestResponseStructure:
    """Final responses match the expected UX-ready format."""

    def test_chat_response_keys(self):
        """Chat result contains all required top-level keys."""
        from services.chat.orchestrator import handle_chat

        llm = _make_llm_sequence([
            {"action": "final_answer", "response": "All good."},
        ])

        result = handle_chat("Simple question", llm_generate_json=llm)
        assert "query" in result
        assert "steps" in result
        assert "final_answer" in result
        assert "tools_used" in result

    def test_agent_response_keys(self):
        """Agent result contains all required top-level keys."""
        from agents.orchestrator import run_agent

        llm = _make_llm_sequence([
            {"steps": [{"tool": "kpi_analysis", "input": {"kpis": TEST_KPIS}, "reason": "Score"}]},
            {"summary": "Done.", "additional_insights": [], "additional_recommendations": []},
            {"answer": "Complete."},
        ])

        result = run_agent("Score KPIs", context={"kpis": TEST_KPIS}, llm_generate_json=llm)
        assert "query" in result
        assert "plan" in result
        assert "steps" in result
        assert "valid" in result
        assert "final_answer" in result
        assert "tools_used" in result
        assert "composed" in result

    def test_composed_response_is_json_serializable(self):
        """Entire response including composed output is JSON-serializable."""
        from agents.orchestrator import run_agent

        llm = _make_llm_sequence([
            {"steps": [{"tool": "kpi_analysis", "input": {"kpis": TEST_KPIS}, "reason": "Score"}]},
            {"summary": "Done.", "additional_insights": [], "additional_recommendations": []},
            {"answer": "Complete."},
        ])

        result = run_agent("Score KPIs", context={"kpis": TEST_KPIS}, llm_generate_json=llm)

        # Must be fully JSON-serializable (no dataclass, no datetime objects)
        serialized = json.dumps(result, default=str)
        assert len(serialized) > 100  # Non-trivial output


# ═══════════════════════════════════════════════════════════════════════
# 8. Performance Baseline
# ═══════════════════════════════════════════════════════════════════════

class TestPerformanceBaseline:
    """Establish timing baselines for tool execution (LLM excluded)."""

    def test_kpi_engine_under_100ms(self):
        """KPI scoring should complete in < 100ms for 3 KPIs."""
        from features.kpi.kpi_engine import process_kpis

        t0 = time.perf_counter()
        process_kpis(TEST_KPIS)
        elapsed = (time.perf_counter() - t0) * 1000

        assert elapsed < 100, f"KPI engine took {elapsed:.1f}ms (>100ms)"

    def test_six_sigma_under_500ms(self):
        """Six Sigma analysis should complete in < 500ms for 3 KPIs."""
        from features.six_sigma import run_six_sigma

        t0 = time.perf_counter()
        run_six_sigma(kpis=TEST_KPIS)
        elapsed = (time.perf_counter() - t0) * 1000

        assert elapsed < 500, f"Six Sigma took {elapsed:.1f}ms (>500ms)"

    def test_forecast_under_500ms(self):
        """Forecast for one KPI should complete in < 500ms."""
        from features.predictive.predictive_engine import forecast_kpi

        t0 = time.perf_counter()
        forecast_kpi(TEST_KPIS[0])
        elapsed = (time.perf_counter() - t0) * 1000

        assert elapsed < 500, f"Forecast took {elapsed:.1f}ms (>500ms)"

    def test_full_chat_loop_under_2s(self):
        """Full chat loop (mock LLM, real tools) under 2 seconds."""
        from services.chat.orchestrator import handle_chat

        llm = _make_llm_sequence([
            {"action": "tool_call", "tool_name": "kpi_analysis", "tool_input": {"kpis": TEST_KPIS}},
            {"action": "final_answer", "response": "Done."},
        ])

        t0 = time.perf_counter()
        handle_chat("Quick analysis", context={"kpis": TEST_KPIS}, llm_generate_json=llm)
        elapsed = (time.perf_counter() - t0) * 1000

        assert elapsed < 2000, f"Full chat loop took {elapsed:.1f}ms (>2000ms)"
