"""
Tests for the Response Composer (services/response).

Covers:
  - Templates: empty_response, SECTION_TEMPLATES
  - Formatter: format_kpi, format_six_sigma, format_predictive, format_risk,
               format_tool_result dispatcher, graceful degradation
  - Composer: compose_response with agent-style and chat-style inputs,
              LLM summary, fallback summary, empty inputs, deduplication
  - Agent Orchestrator integration: composed key in run_agent output
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


# ===================================================================
# Fixtures — realistic engine outputs
# ===================================================================

KPI_RESULT = {
    "kpis": [
        {"name": "ROP", "value": 85, "unit": "ft/hr", "priorityScore": 92,
         "visibility": "visible", "selectionReason": "High financial impact"},
        {"name": "NPT", "value": 12, "unit": "hours", "priorityScore": 78,
         "visibility": "visible", "selectionReason": "Critical safety metric"},
        {"name": "WOB", "value": 22, "unit": "klbs", "priorityScore": 40,
         "visibility": "hidden", "selectionReason": ""},
    ],
    "count": 3,
}

SIGMA_RESULT = {
    "sigmaLevel": "4.2σ",
    "processCapability": "Good",
    "dataQuality": {"grade": "B", "overallScore": 78.5,
                     "details": {"completeness": 0.95}},
    "rootCauses": [
        {"cause": "Bit wear", "severity": "high", "confidence": 0.85,
         "type": "equipment", "evidence": "Correlation with ROP drop"},
        {"cause": "Mud weight", "severity": "medium", "confidence": 0.6,
         "type": "process", "evidence": "Variance in hole cleaning"},
    ],
    "ctq": [
        {"name": "ROP", "kpi_id": "rop-1", "value": 85, "unit": "ft/hr",
         "target": 100, "category": "efficiency",
         "financialImpactScore": 88, "riskScore": 65},
    ],
    "capability": {"overall": {}, "perMetric": []},
    "dmaic": {
        "define": {}, "measure": {}, "analyze": {},
        "improve": {"recommendedActions": [
            "Replace bit after 200 hours.",
            "Adjust mud weight to 10.5 ppg.",
        ], "solutions": []},
        "control": {},
    },
}

PREDICTIVE_RESULT = {
    "forecast": [86.0, 87.5, 89.0],
    "trend": "up",
    "slope": 1.5,
    "models": {"linear": [86], "arima": None, "prophet": [87], "xgboost": None,
               "ensemble": [86, 87.5, 89]},
    "modelsUsed": ["linear", "prophet"],
    "modelScores": {"linear": 3.2, "prophet": 2.8},
    "forecastSteps": 3,
    "historyLength": 20,
}

PREDICTIVE_INSUFFICIENT = {"forecast": None, "reason": "Insufficient history (min 5 points)"}

RISK_RESULT = {
    "risk": {
        "riskLevel": "high",
        "breachPredicted": True,
        "timeToBreach": 4,
        "financialRisk": 125000.0,
    },
    "decision": "HIGH RISK: ROP is likely to miss target (~$125k at risk). Escalate now.",
}


# ===================================================================
# 1. Templates
# ===================================================================


class TestTemplates:

    def test_empty_response_shape(self):
        from services.response.templates import empty_response
        r = empty_response()
        assert set(r.keys()) == {"summary", "insights", "metrics", "recommendations", "confidence", "explanation"}
        assert r["insights"] == []

    def test_empty_response_returns_fresh_copy(self):
        from services.response.templates import empty_response
        a = empty_response()
        b = empty_response()
        a["insights"].append("x")
        assert b["insights"] == []

    def test_section_templates_registered(self):
        from services.response.templates import SECTION_TEMPLATES
        assert set(SECTION_TEMPLATES.keys()) == {
            "kpi_analysis", "six_sigma_analysis",
            "predictive_forecast", "risk_analysis",
        }


# ===================================================================
# 2. Formatter — format_kpi
# ===================================================================


class TestFormatKpi:

    def test_basic(self):
        from services.response.formatter import format_kpi
        out = format_kpi(KPI_RESULT)
        assert out["count"] == 3
        assert len(out["top_kpis"]) == 3
        assert out["top_kpis"][0]["name"] == "ROP"

    def test_insights_from_selection_reason(self):
        from services.response.formatter import format_kpi
        out = format_kpi(KPI_RESULT)
        assert any("High financial impact" in i for i in out["insights"])

    def test_high_priority_recommendation(self):
        from services.response.formatter import format_kpi
        out = format_kpi(KPI_RESULT)
        assert any("high-priority" in r for r in out["recommendations"])

    def test_hidden_kpis_flagged(self):
        from services.response.formatter import format_kpi
        out = format_kpi(KPI_RESULT)
        assert any("hidden" in i for i in out["insights"])

    def test_empty_kpis(self):
        from services.response.formatter import format_kpi
        out = format_kpi({"kpis": [], "count": 0})
        assert out["count"] == 0
        assert out["top_kpis"] == []


# ===================================================================
# 3. Formatter — format_six_sigma
# ===================================================================


class TestFormatSixSigma:

    def test_basic(self):
        from services.response.formatter import format_six_sigma
        out = format_six_sigma(SIGMA_RESULT)
        assert out["sigma_level"] == "4.2σ"
        assert out["process_capability"] == "Good"
        assert out["data_quality_grade"] == "B"
        assert out["ctq_count"] == 1

    def test_root_causes_formatted(self):
        from services.response.formatter import format_six_sigma
        out = format_six_sigma(SIGMA_RESULT)
        assert len(out["root_causes"]) == 2
        assert out["root_causes"][0]["cause"] == "Bit wear"

    def test_high_severity_recommendation(self):
        from services.response.formatter import format_six_sigma
        out = format_six_sigma(SIGMA_RESULT)
        assert any("Bit wear" in r for r in out["recommendations"])

    def test_dmaic_actions_included(self):
        from services.response.formatter import format_six_sigma
        out = format_six_sigma(SIGMA_RESULT)
        assert any("Replace bit" in r for r in out["recommendations"])

    def test_poor_data_quality(self):
        from services.response.formatter import format_six_sigma
        bad = {**SIGMA_RESULT, "dataQuality": {"grade": "F"}}
        out = format_six_sigma(bad)
        assert any("unreliable" in i for i in out["insights"])
        assert any("data quality" in r.lower() for r in out["recommendations"])

    def test_empty_result(self):
        from services.response.formatter import format_six_sigma
        out = format_six_sigma({})
        assert out["sigma_level"] == "N/A"


# ===================================================================
# 4. Formatter — format_predictive
# ===================================================================


class TestFormatPredictive:

    def test_success(self):
        from services.response.formatter import format_predictive
        out = format_predictive(PREDICTIVE_RESULT)
        assert out["trend"] == "up"
        assert out["slope"] == 1.5
        assert out["forecast_steps"] == 3
        assert out["models_used"] == ["linear", "prophet"]

    def test_trend_recommendation(self):
        from services.response.formatter import format_predictive
        out = format_predictive(PREDICTIVE_RESULT)
        assert any("sustainability" in r for r in out["recommendations"])

    def test_down_trend(self):
        from services.response.formatter import format_predictive
        down = {**PREDICTIVE_RESULT, "trend": "down"}
        out = format_predictive(down)
        assert any("downward" in r for r in out["recommendations"])

    def test_insufficient_history(self):
        from services.response.formatter import format_predictive
        out = format_predictive(PREDICTIVE_INSUFFICIENT)
        assert out["trend"] == "unknown"
        assert out["forecast"] == []
        assert any("Insufficient" in i for i in out["insights"])
        assert any("historical data" in r for r in out["recommendations"])


# ===================================================================
# 5. Formatter — format_risk
# ===================================================================


class TestFormatRisk:

    def test_basic(self):
        from services.response.formatter import format_risk
        out = format_risk(RISK_RESULT)
        assert out["risk_level"] == "high"
        assert out["breach_predicted"] is True
        assert out["time_to_breach"] == 4
        assert out["financial_risk"] == 125000.0

    def test_breach_insight(self):
        from services.response.formatter import format_risk
        out = format_risk(RISK_RESULT)
        assert any("breach" in i.lower() for i in out["insights"])

    def test_financial_insight(self):
        from services.response.formatter import format_risk
        out = format_risk(RISK_RESULT)
        assert any("$125000" in i for i in out["insights"])

    def test_decision_as_recommendation(self):
        from services.response.formatter import format_risk
        out = format_risk(RISK_RESULT)
        assert any("Escalate" in r for r in out["recommendations"])

    def test_high_risk_escalation(self):
        from services.response.formatter import format_risk
        out = format_risk(RISK_RESULT)
        assert any("management" in r.lower() for r in out["recommendations"])

    def test_empty_risk(self):
        from services.response.formatter import format_risk
        out = format_risk({"risk": {}, "decision": ""})
        assert out["risk_level"] == "unknown"


# ===================================================================
# 6. Formatter — dispatcher
# ===================================================================


class TestFormatToolResult:

    def test_known_tool(self):
        from services.response.formatter import format_tool_result
        out = format_tool_result("kpi_analysis", KPI_RESULT)
        assert out is not None
        assert "count" in out

    def test_unknown_tool(self):
        from services.response.formatter import format_tool_result
        out = format_tool_result("unknown_tool", {"x": 1})
        assert out is None

    def test_malformed_input(self):
        from services.response.formatter import format_tool_result
        # Pass a string instead of dict — formatter should not crash
        out = format_tool_result("kpi_analysis", "not-a-dict")  # type: ignore
        assert out is None or isinstance(out, dict)


# ===================================================================
# 7. Composer — compose_response
# ===================================================================


class TestComposeResponse:

    def test_agent_style_steps(self):
        from services.response.composer import compose_response

        steps = [
            {"step": 0, "tool": "kpi_analysis", "status": "success",
             "result": KPI_RESULT, "error": None},
            {"step": 1, "tool": "risk_analysis", "status": "success",
             "result": RISK_RESULT, "error": None},
        ]
        out = compose_response("Assess well X", steps)

        assert "summary" in out
        assert len(out["insights"]) > 0
        assert "kpi_analysis" in out["metrics"]
        assert "risk_analysis" in out["metrics"]
        assert len(out["recommendations"]) > 0

    def test_chat_style_steps(self):
        from services.response.composer import compose_response

        steps = [
            {"tool_name": "predictive_forecast",
             "tool_result": {"status": "success", "result": PREDICTIVE_RESULT}},
        ]
        out = compose_response("Forecast ROP", steps)
        assert "predictive_forecast" in out["metrics"]
        assert any("trend" in i for i in out["insights"])

    def test_empty_results(self):
        from services.response.composer import compose_response
        out = compose_response("test", [])
        assert "No tool results" in out["summary"]

    def test_failed_steps_excluded(self):
        from services.response.composer import compose_response

        steps = [
            {"step": 0, "tool": "kpi_analysis", "status": "error",
             "result": None, "error": "boom"},
        ]
        out = compose_response("test", steps)
        assert out["metrics"] == {}

    def test_fallback_summary(self):
        from services.response.composer import compose_response

        steps = [
            {"step": 0, "tool": "six_sigma_analysis", "status": "success",
             "result": SIGMA_RESULT, "error": None},
        ]
        out = compose_response("Sigma check", steps)
        assert "4.2σ" in out["summary"]

    def test_llm_summary(self):
        from services.response.composer import compose_response

        def mock_llm(*a, **kw):
            return {"response": {"summary": "Executive summary from LLM."}}

        steps = [
            {"step": 0, "tool": "kpi_analysis", "status": "success",
             "result": KPI_RESULT, "error": None},
        ]
        out = compose_response("test", steps, llm_generate_json=mock_llm)
        assert out["summary"] == "Executive summary from LLM."

    def test_llm_failure_falls_back(self):
        from services.response.composer import compose_response

        def failing_llm(*a, **kw):
            raise ConnectionError("down")

        steps = [
            {"step": 0, "tool": "kpi_analysis", "status": "success",
             "result": KPI_RESULT, "error": None},
        ]
        out = compose_response("test", steps, llm_generate_json=failing_llm)
        assert "KPI Analysis" in out["summary"]

    def test_deduplicates_insights(self):
        from services.response.composer import compose_response

        # Two identical KPI steps → should not produce duplicate insights
        steps = [
            {"step": 0, "tool": "kpi_analysis", "status": "success",
             "result": KPI_RESULT, "error": None},
            {"step": 1, "tool": "kpi_analysis", "status": "success",
             "result": KPI_RESULT, "error": None},
        ]
        out = compose_response("test", steps)
        assert len(out["insights"]) == len(set(out["insights"]))

    def test_mixed_tools(self):
        from services.response.composer import compose_response

        steps = [
            {"step": 0, "tool": "kpi_analysis", "status": "success",
             "result": KPI_RESULT, "error": None},
            {"step": 1, "tool": "six_sigma_analysis", "status": "success",
             "result": SIGMA_RESULT, "error": None},
            {"step": 2, "tool": "predictive_forecast", "status": "success",
             "result": PREDICTIVE_RESULT, "error": None},
            {"step": 3, "tool": "risk_analysis", "status": "success",
             "result": RISK_RESULT, "error": None},
        ]
        out = compose_response("Full analysis", steps)
        assert len(out["metrics"]) == 4
        assert len(out["insights"]) >= 4
        assert len(out["recommendations"]) >= 3

    def test_unknown_tool_stored_raw(self):
        from services.response.composer import compose_response

        steps = [
            {"step": 0, "tool": "custom_tool", "status": "success",
             "result": {"custom_key": 42}, "error": None},
        ]
        out = compose_response("test", steps)
        assert out["metrics"]["custom_tool"]["custom_key"] == 42


# ===================================================================
# 8. Agent Orchestrator Integration
# ===================================================================


class TestAgentOrchestratorIntegration:

    @pytest.fixture(autouse=True)
    def _ensure_tools(self):
        from services.tools.registry import _reset
        _reset()
        import importlib
        import services.tools as st
        importlib.reload(st)
        yield
        _reset()

    def test_run_agent_includes_composed(self):
        from agents.orchestrator import run_agent

        call_idx = {"i": 0}

        def mock_llm(*args, **kwargs):
            idx = call_idx["i"]
            call_idx["i"] += 1
            if idx == 0:
                # Planner
                return {"response": json.dumps([
                    {"tool": "kpi_analysis",
                     "input": {"kpis": [{"name": "ROP", "value": 85}]},
                     "reason": "Score KPIs"},
                ])}
            if idx == 1:
                # Compose summary
                return {"response": {"summary": "KPI analysis complete."}}
            # Final answer synthesis
            return {"response": {"answer": "KPI analysis complete."}}

        with patch("features.kpi.kpi_engine.process_kpis") as mock_kpi:
            mock_kpi.return_value = [{"name": "ROP", "value": 85, "priorityScore": 92}]
            result = run_agent("Analyse", llm_generate_json=mock_llm)

        assert result["valid"] is True
        assert result["composed"] is not None
        assert "summary" in result["composed"]
        assert "kpi_analysis" in result["composed"]["metrics"]

    def test_run_agent_composed_none_on_failure(self):
        from agents.orchestrator import run_agent

        call_idx = {"i": 0}

        def mock_llm(*args, **kwargs):
            idx = call_idx["i"]
            call_idx["i"] += 1
            if idx == 0:
                # Plan with a valid tool name that will fail at execution
                return {"response": json.dumps([
                    {"tool": "kpi_analysis",
                     "input": {"kpis": [{"name": "X", "value": 1}]},
                     "reason": "will fail"},
                ])}
            return {"response": {"answer": "Failed."}}

        with patch("features.kpi.kpi_engine.process_kpis",
                   side_effect=RuntimeError("engine down")):
            result = run_agent("test", llm_generate_json=mock_llm)

        # Tool execution failed → valid=False → composed is None
        assert result["valid"] is False
        assert result["composed"] is None


# ===================================================================
# 9. Module Exports
# ===================================================================


class TestModuleExports:

    def test_public_api(self):
        from services.response import (
            compose_response,
            format_kpi,
            format_predictive,
            format_risk,
            format_six_sigma,
            format_tool_result,
            empty_response,
            RESPONSE_TEMPLATE,
            SECTION_TEMPLATES,
        )
        assert callable(compose_response)
        assert callable(format_kpi)
