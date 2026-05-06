"""
Tests for agents.orchestrator — Planner, Executor, Validator, run_agent.

All LLM calls are mocked.  Tool engines are also mocked.

Run:  python -m pytest tests/test_agent_orchestrator.py -v
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch
from typing import Any, Dict, List


# ── Helpers ────────────────────────────────────────────────────────────

def _llm_returning(response):
    """Create a mock LLM callable that always returns *response*."""
    def _gen(prompt: str, **kw) -> Dict[str, Any]:
        return {
            "provider_used": "mock",
            "fallback_used": False,
            "response": response,
            "error": None,
            "attempts": 1,
        }
    return _gen


def _llm_sequence(responses: list):
    """Mock LLM that returns a different response each call."""
    idx = {"n": 0}

    def _gen(prompt: str, **kw) -> Dict[str, Any]:
        i = idx["n"]
        idx["n"] += 1
        resp = responses[i] if i < len(responses) else {"answer": "done"}
        return {
            "provider_used": "mock",
            "fallback_used": False,
            "response": resp,
            "error": None,
            "attempts": 1,
        }
    return _gen


@pytest.fixture(autouse=True)
def _ensure_tools():
    """Fresh tool registry for each test."""
    from services.tools.registry import _reset
    _reset()
    import importlib
    import services.tools as st
    importlib.reload(st)
    yield
    _reset()


# ======================================================================
# planner.py
# ======================================================================

class TestPlanner:
    def test_creates_valid_plan(self):
        from agents.orchestrator.planner import create_plan

        llm = _llm_returning([
            {"tool": "kpi_analysis", "input": {"kpis": []}, "reason": "score first"},
            {"tool": "six_sigma_analysis", "input": {"kpis": []}, "reason": "then sigma"},
        ])
        plan = create_plan("Analyse KPIs", llm_generate_json=llm)

        assert len(plan) == 2
        assert plan[0]["tool"] == "kpi_analysis"
        assert plan[1]["tool"] == "six_sigma_analysis"

    def test_strips_unknown_tools(self):
        from agents.orchestrator.planner import create_plan

        llm = _llm_returning([
            {"tool": "kpi_analysis", "input": {"kpis": []}},
            {"tool": "nonexistent_tool", "input": {}},
        ])
        plan = create_plan("test", llm_generate_json=llm)
        assert len(plan) == 1
        assert plan[0]["tool"] == "kpi_analysis"

    def test_enforces_max_steps(self):
        from agents.orchestrator.planner import create_plan, MAX_PLAN_STEPS

        llm = _llm_returning(
            [{"tool": "kpi_analysis", "input": {"kpis": []}}] * (MAX_PLAN_STEPS + 5)
        )
        plan = create_plan("big plan", llm_generate_json=llm)
        assert len(plan) == MAX_PLAN_STEPS

    def test_returns_empty_on_direct_answer(self):
        from agents.orchestrator.planner import create_plan

        llm = _llm_returning([])
        plan = create_plan("What time is it?", llm_generate_json=llm)
        assert plan == []

    def test_handles_llm_exception(self):
        from agents.orchestrator.planner import create_plan

        def _boom(prompt, **kw):
            raise RuntimeError("boom")

        plan = create_plan("test", llm_generate_json=_boom)
        assert plan == []

    def test_handles_unparseable_response(self):
        from agents.orchestrator.planner import create_plan

        llm = _llm_returning("this is not json at all")
        plan = create_plan("test", llm_generate_json=llm)
        assert plan == []

    def test_parses_markdown_fenced_response(self):
        from agents.orchestrator.planner import create_plan

        llm = _llm_returning(
            '```json\n[{"tool": "kpi_analysis", "input": {"kpis": []}}]\n```'
        )
        plan = create_plan("test", llm_generate_json=llm)
        assert len(plan) == 1

    def test_handles_all_providers_failed(self):
        from agents.orchestrator.planner import create_plan

        def _fail(prompt, **kw):
            return {"provider_used": None, "response": "", "error": "all dead", "attempts": 3}

        plan = create_plan("test", llm_generate_json=_fail)
        assert plan == []

    def test_context_appears_in_prompt(self):
        from agents.orchestrator.planner import create_plan

        captured = []

        def _capture(prompt, **kw):
            captured.append(prompt)
            return {
                "provider_used": "mock",
                "response": [],
                "error": None,
                "attempts": 1,
            }

        create_plan("test", context={"well": "X-99"}, llm_generate_json=_capture)
        assert "X-99" in captured[0]


# ======================================================================
# executor.py
# ======================================================================

class TestExecutor:
    @patch("features.kpi.kpi_engine.process_kpis")
    def test_single_step(self, mock_kpi):
        from agents.orchestrator.executor import execute_plan

        mock_kpi.return_value = [{"name": "ROP", "priorityScore": 85}]

        plan = [{"tool": "kpi_analysis", "input": {"kpis": [{"name": "ROP"}]}}]
        results = execute_plan(plan)

        assert len(results) == 1
        assert results[0]["status"] == "success"
        assert results[0]["tool"] == "kpi_analysis"

    @patch("features.risk.risk_engine.generate_decision")
    @patch("features.risk.risk_engine.detect_risk")
    @patch("features.predictive.predictive_engine.forecast_kpi")
    def test_multi_step(self, mock_fc, mock_risk, mock_dec):
        from agents.orchestrator.executor import execute_plan

        mock_fc.return_value = {"forecast": [100], "trend": "down"}
        mock_risk.return_value = {"riskLevel": "high"}
        mock_dec.return_value = "Act now."

        plan = [
            {"tool": "predictive_forecast",
             "input": {"kpi": {"name": "X", "history": [1, 2, 3, 4, 5]}}},
            {"tool": "risk_analysis",
             "input": {"kpi": {"name": "X", "target": 120, "value": 100},
                       "forecast_data": {"$ref": 0}}},
        ]
        results = execute_plan(plan)

        assert len(results) == 2
        assert results[0]["status"] == "success"
        assert results[1]["status"] == "success"
        # $ref should have been resolved
        assert results[1]["input"]["forecast_data"]["forecast"] == [100]

    def test_stops_on_failure(self):
        from agents.orchestrator.executor import execute_plan

        plan = [
            {"tool": "nonexistent", "input": {}},
            {"tool": "kpi_analysis", "input": {"kpis": []}},
        ]
        results = execute_plan(plan, stop_on_failure=True)

        assert len(results) == 1
        assert results[0]["status"] == "error"

    @patch("features.kpi.kpi_engine.process_kpis", return_value=[])
    def test_continues_on_failure_when_disabled(self, mock_kpi):
        from agents.orchestrator.executor import execute_plan

        plan = [
            {"tool": "nonexistent", "input": {}},
            {"tool": "kpi_analysis", "input": {"kpis": []}},
        ]
        results = execute_plan(plan, stop_on_failure=False)

        assert len(results) == 2
        assert results[0]["status"] == "error"
        assert results[1]["status"] == "success"

    def test_ref_with_out_of_range_index(self):
        """$ref to non-existent step leaves value as-is."""
        from agents.orchestrator.executor import execute_plan

        plan = [
            {"tool": "risk_analysis",
             "input": {"kpi": {"name": "X", "target": 1, "value": 1},
                       "forecast_data": {"$ref": 99}}},
        ]
        with patch("features.risk.risk_engine.detect_risk", return_value=None), \
             patch("features.risk.risk_engine.generate_decision", return_value="ok"):
            results = execute_plan(plan)

        assert len(results) == 1
        # forecast_data kept the unresolved $ref dict
        assert "$ref" in results[0]["input"]["forecast_data"]

    def test_empty_plan(self):
        from agents.orchestrator.executor import execute_plan
        assert execute_plan([]) == []


# ======================================================================
# validator.py
# ======================================================================

class TestValidator:
    def test_empty_fails(self):
        from agents.orchestrator.validator import validate_results
        assert validate_results([]) is False

    def test_all_errors_fails(self):
        from agents.orchestrator.validator import validate_results

        results = [
            {"step": 0, "tool": "a", "status": "error", "result": None, "error": "boom"},
        ]
        assert validate_results(results) is False

    def test_one_success_passes(self):
        from agents.orchestrator.validator import validate_results

        results = [
            {"step": 0, "tool": "a", "status": "error", "result": None, "error": "boom"},
            {"step": 1, "tool": "b", "status": "success", "result": {"x": 1}, "error": None},
        ]
        assert validate_results(results) is True

    def test_all_success(self):
        from agents.orchestrator.validator import validate_results

        results = [
            {"step": 0, "tool": "a", "status": "success", "result": {}, "error": None},
        ]
        assert validate_results(results) is True

    def test_summarise(self):
        from agents.orchestrator.validator import summarise_results

        results = [
            {"step": 0, "tool": "a", "status": "success", "result": {"v": 1}, "error": None},
            {"step": 1, "tool": "b", "status": "error", "result": None, "error": "fail"},
        ]
        s = summarise_results(results)
        assert s["ok"] is True
        assert s["steps_ok"] == 1
        assert s["steps_failed"] == 1
        assert len(s["outputs"]) == 1
        assert len(s["errors"]) == 1


# ======================================================================
# __init__.py  — run_agent end-to-end
# ======================================================================

class TestRunAgent:
    @patch("features.kpi.kpi_engine.process_kpis")
    def test_full_pipeline(self, mock_kpi):
        from agents.orchestrator import run_agent

        mock_kpi.return_value = [{"name": "ROP", "priorityScore": 90}]

        llm = _llm_sequence([
            # Planner response
            [{"tool": "kpi_analysis", "input": {"kpis": [{"name": "ROP"}]}, "reason": "score"}],
            # Response Composer LLM summary
            {"summary": "ROP scores 90 — high priority."},
            # Final-answer response
            {"answer": "ROP scores 90."},
        ])

        res = run_agent("Score my KPIs", llm_generate_json=llm)

        assert res["query"] == "Score my KPIs"
        assert len(res["plan"]) == 1
        assert len(res["steps"]) == 1
        assert res["valid"] is True
        assert res["tools_used"] == ["kpi_analysis"]
        assert "90" in res["final_answer"]

    def test_empty_plan_direct_answer(self):
        from agents.orchestrator import run_agent

        llm = _llm_sequence([
            [],  # Planner: no tools needed
            {"answer": "42"},  # Final answer
        ])

        res = run_agent("What is 6 * 7?", llm_generate_json=llm)

        assert res["plan"] == []
        assert res["steps"] == []
        assert res["valid"] is True
        assert "42" in res["final_answer"]

    def test_all_steps_fail(self):
        from agents.orchestrator import run_agent

        llm = _llm_sequence([
            [{"tool": "nonexistent", "input": {}}],  # Planner (invalid tool stripped)
        ])

        res = run_agent("bad plan", llm_generate_json=llm)

        # Plan is empty because nonexistent was stripped
        assert res["plan"] == []

    @patch("features.six_sigma.run_six_sigma")
    @patch("features.kpi.kpi_engine.process_kpis")
    def test_multi_tool_plan(self, mock_kpi, mock_ss):
        from agents.orchestrator import run_agent

        mock_kpi.return_value = [{"name": "ROP", "priorityScore": 80}]
        mock_ss.return_value = {"sigmaLevel": "3.5σ"}

        llm = _llm_sequence([
            # Planner
            [
                {"tool": "kpi_analysis", "input": {"kpis": [{"name": "ROP"}]}, "reason": "score"},
                {"tool": "six_sigma_analysis", "input": {"kpis": [{"name": "ROP"}]}, "reason": "sigma"},
            ],
            # Final answer
            {"answer": "KPI scored 80, sigma 3.5."},
        ])

        res = run_agent("Full analysis", llm_generate_json=llm)

        assert len(res["plan"]) == 2
        assert len(res["steps"]) == 2
        assert res["valid"] is True
        assert res["tools_used"] == ["kpi_analysis", "six_sigma_analysis"]

    def test_execution_failure_produces_error_answer(self):
        from agents.orchestrator import run_agent

        # Planner gives a valid tool, but execution will fail (mock raises)
        llm = _llm_sequence([
            [{"tool": "kpi_analysis", "input": {"kpis": []}, "reason": "score"}],
        ])

        with patch("features.kpi.kpi_engine.process_kpis", side_effect=RuntimeError("db down")):
            res = run_agent("test", llm_generate_json=llm)

        assert res["valid"] is False
        assert "error" in res["final_answer"].lower()

    def test_planner_llm_failure_returns_graceful(self):
        from agents.orchestrator import run_agent

        def _boom(prompt, **kw):
            raise RuntimeError("LLM dead")

        res = run_agent("test", llm_generate_json=_boom)
        # Planner returns [] → LLM called for direct answer → also fails → fallback
        assert res["plan"] == []
        assert res["final_answer"]  # Non-empty fallback
