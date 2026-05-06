"""
Tests for services.tools — Tool Registry, Dispatcher, and built-in wrappers.

Run:  python -m pytest tests/test_tool_registry.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from typing import Any, Dict


# ── helpers ────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset the global registry before each test."""
    from services.tools.registry import _reset
    _reset()
    yield
    _reset()


# ======================================================================
# schemas.py
# ======================================================================

class TestToolResult:
    def test_success_to_dict(self):
        from services.tools.schemas import ToolResult
        r = ToolResult(tool="t", status="success", result={"a": 1})
        d = r.to_dict()
        assert d == {"tool": "t", "status": "success", "result": {"a": 1}}

    def test_error_to_dict(self):
        from services.tools.schemas import ToolResult
        r = ToolResult(tool="t", status="error", error="boom")
        d = r.to_dict()
        assert d == {"tool": "t", "status": "error", "error": "boom"}

    def test_minimal_to_dict(self):
        from services.tools.schemas import ToolResult
        r = ToolResult(tool="t", status="success")
        d = r.to_dict()
        # result and error omitted when None
        assert "result" not in d
        assert "error" not in d


# ======================================================================
# registry.py
# ======================================================================

class TestRegistry:
    def test_register_and_get(self):
        from services.tools.registry import register_tool, get_tool
        from services.tools.schemas import ToolDef

        td = ToolDef(name="x", description="d", input_schema={}, handler=lambda i: i)
        register_tool(td)
        assert get_tool("x") is td

    def test_get_unknown_returns_none(self):
        from services.tools.registry import get_tool
        assert get_tool("nope") is None

    def test_duplicate_raises(self):
        from services.tools.registry import register_tool
        from services.tools.schemas import ToolDef

        td = ToolDef(name="dup", description="", input_schema={}, handler=lambda i: i)
        register_tool(td)
        with pytest.raises(ValueError, match="already registered"):
            register_tool(td)

    def test_list_tools(self):
        from services.tools.registry import register_tool, list_tools
        from services.tools.schemas import ToolDef

        register_tool(ToolDef(name="a", description="", input_schema={}, handler=lambda i: i))
        register_tool(ToolDef(name="b", description="", input_schema={}, handler=lambda i: i))
        assert [t.name for t in list_tools()] == ["a", "b"]

    def test_tool_names(self):
        from services.tools.registry import register_tool, tool_names
        from services.tools.schemas import ToolDef

        register_tool(ToolDef(name="c", description="", input_schema={}, handler=lambda i: i))
        assert tool_names() == ["c"]

    def test_build_tool_schemas(self):
        from services.tools.registry import register_tool, build_tool_schemas
        from services.tools.schemas import ToolDef

        register_tool(ToolDef(
            name="t1", description="desc", input_schema={"type": "object"}, handler=lambda i: i
        ))
        schemas = build_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0] == {"name": "t1", "description": "desc", "input_schema": {"type": "object"}}


# ======================================================================
# decorator.py
# ======================================================================

class TestDecorator:
    def test_decorator_registers(self):
        from services.tools.decorator import tool
        from services.tools.registry import get_tool

        @tool(name="deco_test", description="d", input_schema={"type": "object"})
        def my_handler(inp):
            return {"ok": True}

        td = get_tool("deco_test")
        assert td is not None
        assert td.name == "deco_test"
        assert td.handler is my_handler

    def test_decorated_function_still_callable(self):
        from services.tools.decorator import tool

        @tool(name="direct_call", description="d", input_schema={})
        def my_handler(inp):
            return inp

        assert my_handler({"x": 1}) == {"x": 1}


# ======================================================================
# dispatcher.py
# ======================================================================

class TestDispatcher:
    def _register_echo(self):
        from services.tools.registry import register_tool
        from services.tools.schemas import ToolDef

        register_tool(ToolDef(
            name="echo",
            description="Echoes input",
            input_schema={
                "type": "object",
                "properties": {"msg": {"type": "string"}},
                "required": ["msg"],
            },
            handler=lambda inp: {"echo": inp["msg"]},
        ))

    def test_success(self):
        from services.tools.dispatcher import dispatch_tool
        self._register_echo()

        res = dispatch_tool("echo", {"msg": "hi"})
        assert res["status"] == "success"
        assert res["result"] == {"echo": "hi"}
        assert res["tool"] == "echo"

    def test_unknown_tool(self):
        from services.tools.dispatcher import dispatch_tool
        res = dispatch_tool("nope", {})
        assert res["status"] == "error"
        assert "Unknown tool" in res["error"]

    def test_missing_required_field(self):
        from services.tools.dispatcher import dispatch_tool
        self._register_echo()

        res = dispatch_tool("echo", {})
        assert res["status"] == "error"
        assert "Missing required" in res["error"]

    def test_type_validation_array(self):
        from services.tools.registry import register_tool
        from services.tools.schemas import ToolDef
        from services.tools.dispatcher import dispatch_tool

        register_tool(ToolDef(
            name="arr",
            description="",
            input_schema={
                "type": "object",
                "properties": {"items": {"type": "array"}},
                "required": ["items"],
            },
            handler=lambda inp: {},
        ))

        res = dispatch_tool("arr", {"items": "not_a_list"})
        assert res["status"] == "error"
        assert "must be an array" in res["error"]

    def test_handler_exception_caught(self):
        from services.tools.registry import register_tool
        from services.tools.schemas import ToolDef
        from services.tools.dispatcher import dispatch_tool

        def boom(inp):
            raise RuntimeError("kaboom")

        register_tool(ToolDef(name="boom", description="", input_schema={}, handler=boom))

        res = dispatch_tool("boom", {})
        assert res["status"] == "error"
        assert "failed during execution" in res["error"]

    def test_call_counter_limit(self):
        from services.tools.dispatcher import dispatch_tool, make_call_counter
        self._register_echo()

        counter = make_call_counter(limit=2)
        dispatch_tool("echo", {"msg": "1"}, counter=counter)
        dispatch_tool("echo", {"msg": "2"}, counter=counter)
        res = dispatch_tool("echo", {"msg": "3"}, counter=counter)
        assert res["status"] == "error"
        assert "limit exceeded" in res["error"]

    def test_counter_tracks_count(self):
        from services.tools.dispatcher import dispatch_tool, make_call_counter
        self._register_echo()

        counter = make_call_counter()
        dispatch_tool("echo", {"msg": "1"}, counter=counter)
        assert counter.count == 1


# ======================================================================
# Built-in tool wrappers (via __init__.py import)
# ======================================================================

class TestBuiltInTools:
    """Verify the 4 engine wrappers are registered and dispatch correctly."""

    def _ensure_registered(self):
        """Import __init__ which fires the @tool decorators."""
        # We need a fresh registry, then re-import to register
        import importlib
        import services.tools as st
        importlib.reload(st)

    # ── six_sigma_analysis ─────────────────────────────────────────────
    @patch("features.six_sigma.run_six_sigma")
    def test_six_sigma_tool(self, mock_run):
        self._ensure_registered()
        from services.tools import dispatch_tool

        mock_run.return_value = {"sigmaLevel": "4.5σ", "sigmaNumeric": 4.5}

        res = dispatch_tool("six_sigma_analysis", {
            "kpis": [{"name": "ROP", "value": 120}],
        })
        assert res["status"] == "success"
        assert res["result"]["sigmaLevel"] == "4.5σ"
        mock_run.assert_called_once_with(
            kpis=[{"name": "ROP", "value": 120}],
            financial_threshold=60,
            risk_threshold=60,
        )

    @patch("features.six_sigma.run_six_sigma")
    def test_six_sigma_custom_thresholds(self, mock_run):
        self._ensure_registered()
        from services.tools import dispatch_tool

        mock_run.return_value = {}
        dispatch_tool("six_sigma_analysis", {
            "kpis": [],
            "financial_threshold": 80,
            "risk_threshold": 70,
        })
        mock_run.assert_called_once_with(
            kpis=[], financial_threshold=80, risk_threshold=70,
        )

    # ── kpi_analysis ───────────────────────────────────────────────────
    @patch("features.kpi.kpi_engine.process_kpis")
    def test_kpi_tool(self, mock_proc):
        self._ensure_registered()
        from services.tools import dispatch_tool

        mock_proc.return_value = [
            {"name": "ROP", "priorityScore": 85, "visibility": "primary"},
        ]
        res = dispatch_tool("kpi_analysis", {"kpis": [{"name": "ROP"}]})
        assert res["status"] == "success"
        assert res["result"]["count"] == 1
        assert res["result"]["kpis"][0]["visibility"] == "primary"

    # ── predictive_forecast ────────────────────────────────────────────
    @patch("features.predictive.predictive_engine.forecast_kpi")
    def test_predictive_tool(self, mock_fc):
        self._ensure_registered()
        from services.tools import dispatch_tool

        mock_fc.return_value = {"forecast": [1, 2, 3], "trend": "up"}
        res = dispatch_tool("predictive_forecast", {
            "kpi": {"name": "ROP", "history": [10, 12, 14, 16, 18]},
        })
        assert res["status"] == "success"
        assert res["result"]["trend"] == "up"

    @patch("features.predictive.predictive_engine.forecast_kpi")
    def test_predictive_insufficient_data(self, mock_fc):
        self._ensure_registered()
        from services.tools import dispatch_tool

        mock_fc.return_value = None
        res = dispatch_tool("predictive_forecast", {
            "kpi": {"name": "ROP", "history": [10]},
        })
        assert res["status"] == "success"
        assert res["result"]["forecast"] is None

    # ── risk_analysis ──────────────────────────────────────────────────
    @patch("features.risk.risk_engine.generate_decision")
    @patch("features.risk.risk_engine.detect_risk")
    def test_risk_tool(self, mock_risk, mock_dec):
        self._ensure_registered()
        from services.tools import dispatch_tool

        mock_risk.return_value = {"riskLevel": "high", "breachPredicted": True}
        mock_dec.return_value = "CRITICAL: take action"

        res = dispatch_tool("risk_analysis", {
            "kpi": {"name": "ROP", "target": 100, "value": 50},
            "forecast_data": {"forecast": [40, 30, 20]},
        })
        assert res["status"] == "success"
        assert res["result"]["risk"]["riskLevel"] == "high"
        assert "CRITICAL" in res["result"]["decision"]

    def test_risk_tool_without_forecast(self):
        """risk_analysis accepts kpi without forecast_data."""
        self._ensure_registered()
        from services.tools import dispatch_tool

        with patch("features.risk.risk_engine.detect_risk", return_value=None), \
             patch("features.risk.risk_engine.generate_decision", return_value="No data"):
            res = dispatch_tool("risk_analysis", {
                "kpi": {"name": "ROP", "target": 100, "value": 90},
            })
        assert res["status"] == "success"

    # ── list / schemas ─────────────────────────────────────────────────
    def test_all_four_registered(self):
        self._ensure_registered()
        from services.tools import tool_names

        names = tool_names()
        assert "six_sigma_analysis" in names
        assert "kpi_analysis" in names
        assert "predictive_forecast" in names
        assert "risk_analysis" in names

    def test_build_schemas_has_all(self):
        self._ensure_registered()
        from services.tools import build_tool_schemas

        schemas = build_tool_schemas()
        schema_names = {s["name"] for s in schemas}
        assert schema_names == {
            "six_sigma_analysis",
            "kpi_analysis",
            "predictive_forecast",
            "risk_analysis",
        }

    def test_schemas_have_required_keys(self):
        self._ensure_registered()
        from services.tools import build_tool_schemas

        for s in build_tool_schemas():
            assert "name" in s
            assert "description" in s
            assert "input_schema" in s
            assert s["description"], f"{s['name']} has empty description"
