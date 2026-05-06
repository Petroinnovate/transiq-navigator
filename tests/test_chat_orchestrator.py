"""
Tests for services.chat — Orchestrator, Session, Schemas.

All LLM calls are mocked.  The Tool Registry is populated with its
4 built-in tools (also mocked at the engine level).

Run:  python -m pytest tests/test_chat_orchestrator.py -v
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock
from typing import Any, Dict


# ── helpers ────────────────────────────────────────────────────────────

def _fake_llm_json_factory(decisions: list[dict]):
    """Return a callable that yields one LLM decision per call.

    Each item in *decisions* is the JSON the LLM would return
    (action/tool_name/tool_input/response).
    """
    call_idx = {"n": 0}

    def _generate(prompt: str, **kwargs) -> Dict[str, Any]:
        idx = call_idx["n"]
        call_idx["n"] += 1
        if idx < len(decisions):
            return {
                "provider_used": "mock",
                "fallback_used": False,
                "response": decisions[idx],
                "error": None,
                "attempts": 1,
            }
        # Fallback: final_answer so loop terminates
        return {
            "provider_used": "mock",
            "fallback_used": False,
            "response": {"action": "final_answer", "response": "done"},
            "error": None,
            "attempts": 1,
        }

    return _generate


@pytest.fixture(autouse=True)
def _ensure_tools():
    """Make sure the tool registry is populated for every test."""
    from services.tools.registry import _reset, _REGISTRY
    _reset()
    import importlib
    import services.tools as st
    importlib.reload(st)
    yield
    _reset()


# ======================================================================
# schemas.py
# ======================================================================

class TestChatSchemas:
    def test_chat_step_to_dict_tool_call(self):
        from services.chat.schemas import ChatStep

        s = ChatStep(step=1, action="tool_call", tool_name="kpi_analysis",
                     tool_input={"kpis": []}, tool_result={"status": "success"})
        d = s.to_dict()
        assert d["step"] == 1
        assert d["tool_name"] == "kpi_analysis"
        assert "tool_result" in d

    def test_chat_step_to_dict_final(self):
        from services.chat.schemas import ChatStep

        s = ChatStep(step=2, action="final_answer", response="All good")
        d = s.to_dict()
        assert "tool_name" not in d
        assert d["response"] == "All good"

    def test_chat_response_to_dict(self):
        from services.chat.schemas import ChatResponse, ChatStep

        cr = ChatResponse(query="test", final_answer="yes", tools_used=["a", "b"])
        cr.steps.append(ChatStep(step=1, action="final_answer", response="yes"))
        d = cr.to_dict()
        assert d["query"] == "test"
        assert d["final_answer"] == "yes"
        assert d["tools_used"] == ["a", "b"]
        assert len(d["steps"]) == 1


# ======================================================================
# orchestrator.py — direct final answer (no tool calls)
# ======================================================================

class TestDirectAnswer:
    def test_direct_final_answer(self):
        from services.chat.orchestrator import handle_chat

        llm = _fake_llm_json_factory([
            {"action": "final_answer", "response": "The sigma level is 3.2."},
        ])
        res = handle_chat("What is the sigma?", llm_generate_json=llm)

        assert res["final_answer"] == "The sigma level is 3.2."
        assert res["tools_used"] == []
        assert len(res["steps"]) == 1
        assert res["steps"][0]["action"] == "final_answer"

    def test_empty_context_ok(self):
        from services.chat.orchestrator import handle_chat

        llm = _fake_llm_json_factory([
            {"action": "final_answer", "response": "ok"},
        ])
        res = handle_chat("hi", context=None, llm_generate_json=llm)
        assert res["final_answer"] == "ok"


# ======================================================================
# orchestrator.py — single tool call then final answer
# ======================================================================

class TestSingleToolCall:
    @patch("features.kpi.kpi_engine.process_kpis")
    def test_kpi_then_answer(self, mock_kpi):
        from services.chat.orchestrator import handle_chat

        mock_kpi.return_value = [{"name": "ROP", "priorityScore": 90}]

        llm = _fake_llm_json_factory([
            {
                "action": "tool_call",
                "tool_name": "kpi_analysis",
                "tool_input": {"kpis": [{"name": "ROP"}]},
            },
            {
                "action": "final_answer",
                "response": "ROP scores 90.",
            },
        ])

        res = handle_chat("Score my KPIs", llm_generate_json=llm)

        assert res["tools_used"] == ["kpi_analysis"]
        assert len(res["steps"]) == 2
        assert res["steps"][0]["action"] == "tool_call"
        assert res["steps"][0]["tool_name"] == "kpi_analysis"
        assert res["steps"][1]["action"] == "final_answer"
        assert res["final_answer"] == "ROP scores 90."


# ======================================================================
# orchestrator.py — multi tool chain
# ======================================================================

class TestMultiToolChain:
    @patch("features.risk.risk_engine.generate_decision")
    @patch("features.risk.risk_engine.detect_risk")
    @patch("features.predictive.predictive_engine.forecast_kpi")
    def test_predict_then_risk(self, mock_fc, mock_risk, mock_dec):
        from services.chat.orchestrator import handle_chat

        mock_fc.return_value = {"forecast": [100, 95, 90], "trend": "down"}
        mock_risk.return_value = {"riskLevel": "high", "breachPredicted": True}
        mock_dec.return_value = "High risk — act now."

        llm = _fake_llm_json_factory([
            {
                "action": "tool_call",
                "tool_name": "predictive_forecast",
                "tool_input": {"kpi": {"name": "ROP", "history": [110, 108, 105, 102, 100]}},
            },
            {
                "action": "tool_call",
                "tool_name": "risk_analysis",
                "tool_input": {
                    "kpi": {"name": "ROP", "target": 120, "value": 100, "direction": "increase"},
                    "forecast_data": {"forecast": [100, 95, 90], "trend": "down"},
                },
            },
            {
                "action": "final_answer",
                "response": "ROP is declining with high breach risk.",
            },
        ])

        res = handle_chat("Forecast and assess risk for ROP", llm_generate_json=llm)

        assert res["tools_used"] == ["predictive_forecast", "risk_analysis"]
        assert len(res["steps"]) == 3
        assert res["final_answer"] == "ROP is declining with high breach risk."


# ======================================================================
# orchestrator.py — safety limits
# ======================================================================

class TestSafetyLimits:
    def test_max_iterations(self):
        """Loop terminates after MAX_ITERATIONS even without final_answer."""
        from services.chat.orchestrator import handle_chat, MAX_ITERATIONS

        # LLM always returns tool_call for a non-existent tool
        llm = _fake_llm_json_factory([
            {"action": "tool_call", "tool_name": "unknown_tool", "tool_input": {}}
        ] * (MAX_ITERATIONS + 5))

        res = handle_chat("loop forever", llm_generate_json=llm)

        assert len(res["steps"]) == MAX_ITERATIONS
        assert "maximum" in res["final_answer"].lower()

    def test_unknown_tool_handled(self):
        from services.chat.orchestrator import handle_chat

        llm = _fake_llm_json_factory([
            {"action": "tool_call", "tool_name": "nonexistent", "tool_input": {}},
            {"action": "final_answer", "response": "Could not find that tool."},
        ])

        res = handle_chat("do something", llm_generate_json=llm)

        assert res["steps"][0]["tool_result"]["status"] == "error"
        assert "Unknown tool" in res["steps"][0]["tool_result"]["error"]


# ======================================================================
# orchestrator.py — LLM failure modes
# ======================================================================

class TestLLMFailures:
    def test_llm_exception(self):
        """If the LLM call throws, orchestrator returns graceful message."""
        from services.chat.orchestrator import handle_chat

        def _explode(prompt, **kw):
            raise RuntimeError("boom")

        res = handle_chat("hi", llm_generate_json=_explode)
        assert res["final_answer"] == "I'm unable to process your request right now."
        assert res["tools_used"] == []

    def test_llm_returns_all_providers_failed(self):
        from services.chat.orchestrator import handle_chat

        def _fail(prompt, **kw):
            return {"provider_used": None, "response": "", "error": "all dead", "attempts": 4}

        res = handle_chat("hi", llm_generate_json=_fail)
        assert res["final_answer"] == "I'm unable to process your request right now."

    def test_llm_returns_unparseable_string(self):
        from services.chat.orchestrator import handle_chat

        def _garbled(prompt, **kw):
            return {"provider_used": "mock", "response": "not json at all!!!", "error": None, "attempts": 1}

        res = handle_chat("hi", llm_generate_json=_garbled)
        assert "unable" in res["final_answer"].lower()

    def test_llm_returns_json_in_markdown_fence(self):
        """LLM wraps JSON in ```json ... ``` — we should still parse it."""
        from services.chat.orchestrator import handle_chat

        def _fenced(prompt, **kw):
            return {
                "provider_used": "mock",
                "response": '```json\n{"action": "final_answer", "response": "parsed"}\n```',
                "error": None,
                "attempts": 1,
            }

        res = handle_chat("test", llm_generate_json=_fenced)
        assert res["final_answer"] == "parsed"

    def test_invalid_action_treated_as_final(self):
        from services.chat.orchestrator import handle_chat

        llm = _fake_llm_json_factory([
            {"action": "something_weird", "response": "fallback answer"},
        ])
        res = handle_chat("test", llm_generate_json=llm)
        assert res["final_answer"] == "fallback answer"


# ======================================================================
# orchestrator.py — context forwarding
# ======================================================================

class TestContextForwarding:
    def test_context_included_in_prompt(self):
        """Verify that context data reaches the LLM prompt."""
        from services.chat.orchestrator import handle_chat

        captured_prompts = []

        def _capture(prompt, **kw):
            captured_prompts.append(prompt)
            return {
                "provider_used": "mock",
                "response": {"action": "final_answer", "response": "done"},
                "error": None,
                "attempts": 1,
            }

        handle_chat("test", context={"well": "A-47"}, llm_generate_json=_capture)
        assert "A-47" in captured_prompts[0]

    def test_tool_results_fed_back_to_prompt(self):
        """After a tool call, its result appears in the next LLM prompt."""
        from services.chat.orchestrator import handle_chat

        captured_prompts = []

        call_idx = {"n": 0}

        def _capture(prompt, **kw):
            captured_prompts.append(prompt)
            idx = call_idx["n"]
            call_idx["n"] += 1
            if idx == 0:
                return {
                    "provider_used": "mock",
                    "response": {
                        "action": "tool_call",
                        "tool_name": "kpi_analysis",
                        "tool_input": {"kpis": [{"name": "X"}]},
                    },
                    "error": None, "attempts": 1,
                }
            return {
                "provider_used": "mock",
                "response": {"action": "final_answer", "response": "done"},
                "error": None, "attempts": 1,
            }

        with patch("features.kpi.kpi_engine.process_kpis", return_value=[]):
            handle_chat("test", llm_generate_json=_capture)

        # The second prompt should contain the tool result
        assert len(captured_prompts) == 2
        assert "PREVIOUS TOOL RESULTS" in captured_prompts[1]
        assert "kpi_analysis" in captured_prompts[1]


# ======================================================================
# orchestrator.py — deduplication of tools_used
# ======================================================================

class TestDedup:
    @patch("features.kpi.kpi_engine.process_kpis", return_value=[])
    def test_tools_used_deduped(self, mock_kpi):
        from services.chat.orchestrator import handle_chat

        llm = _fake_llm_json_factory([
            {"action": "tool_call", "tool_name": "kpi_analysis", "tool_input": {"kpis": []}},
            {"action": "tool_call", "tool_name": "kpi_analysis", "tool_input": {"kpis": []}},
            {"action": "final_answer", "response": "done"},
        ])
        res = handle_chat("test", llm_generate_json=llm)
        assert res["tools_used"] == ["kpi_analysis"]   # no duplication


# ======================================================================
# session.py
# ======================================================================

class TestChatSession:
    def test_session_run(self):
        from services.chat.session import ChatSession

        llm = _fake_llm_json_factory([
            {"action": "final_answer", "response": "Hello from session."},
        ])
        session = ChatSession(query="hi", llm_generate_json=llm)
        res = session.run()

        assert res["query"] == "hi"
        assert res["final_answer"] == "Hello from session."

    @patch("features.six_sigma.run_six_sigma")
    def test_session_with_tool(self, mock_ss):
        from services.chat.session import ChatSession

        mock_ss.return_value = {"sigmaLevel": "4.0σ"}

        llm = _fake_llm_json_factory([
            {"action": "tool_call", "tool_name": "six_sigma_analysis",
             "tool_input": {"kpis": [{"name": "A"}]}},
            {"action": "final_answer", "response": "Sigma is 4.0."},
        ])
        session = ChatSession(query="Sigma?", context={"well": "X"}, llm_generate_json=llm)
        res = session.run()

        assert res["tools_used"] == ["six_sigma_analysis"]
        assert res["final_answer"] == "Sigma is 4.0."
