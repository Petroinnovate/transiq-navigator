"""
Tests — Secure Scratchpad Sandbox.

Covers:
  * safety.py — AST validation, blocked modules/attrs/names
  * executor.py — subprocess execution, timeout, prior_state
  * scratchpad.py — session persistence, reset
  * __init__.py — tool registration via dispatch_tool
"""
from __future__ import annotations

import pytest

# ═══════════════════════════════════════════════════════════════════════
# 1. Safety layer
# ═══════════════════════════════════════════════════════════════════════

from services.sandbox.safety import (
    validate_code,
    BLOCKED_MODULES,
    BLOCKED_ATTRS,
    BLOCKED_NAMES,
    SAFE_BUILTINS,
    _ALLOWED_BUILTIN_NAMES,
)


class TestValidateCode:
    """Static validation of user-supplied code."""

    # ── Clean code ────────────────────────────────────────────────────

    def test_clean_arithmetic(self):
        assert validate_code("x = 1 + 2") == []

    def test_clean_function_def(self):
        assert validate_code("def add(a, b): return a + b") == []

    def test_clean_list_comprehension(self):
        assert validate_code("[x**2 for x in range(10)]") == []

    def test_clean_multiline(self):
        code = "x = 10\ny = 20\nprint(x + y)"
        assert validate_code(code) == []

    # ── Blocked imports ───────────────────────────────────────────────

    def test_blocks_os_import(self):
        errors = validate_code("import os")
        assert any("os" in e for e in errors)

    def test_blocks_subprocess_import(self):
        errors = validate_code("import subprocess")
        assert any("subprocess" in e for e in errors)

    def test_blocks_from_import(self):
        errors = validate_code("from socket import socket")
        assert any("socket" in e for e in errors)

    def test_blocks_nested_import(self):
        errors = validate_code("import os.path")
        assert any("os" in e for e in errors)

    def test_allows_math_import(self):
        # math is not in BLOCKED_MODULES
        assert validate_code("import math") == []

    # ── Blocked attributes ────────────────────────────────────────────

    def test_blocks_dunder_import(self):
        errors = validate_code("x.__import__('os')")
        assert len(errors) >= 1

    def test_blocks_system_attr(self):
        errors = validate_code("x.system('ls')")
        assert any("system" in e for e in errors)

    def test_blocks_subclasses(self):
        errors = validate_code("x.__subclasses__()")
        assert any("__subclasses__" in e for e in errors)

    # ── Blocked names ─────────────────────────────────────────────────

    def test_blocks_eval_call(self):
        errors = validate_code("eval('1+1')")
        assert any("eval" in e for e in errors)

    def test_blocks_exec_call(self):
        errors = validate_code("exec('x = 1')")
        assert any("exec" in e for e in errors)

    def test_blocks_open_call(self):
        errors = validate_code("open('/etc/passwd')")
        assert any("open" in e for e in errors)

    def test_blocks_getattr_call(self):
        errors = validate_code("getattr(obj, 'secret')")
        assert any("getattr" in e for e in errors)

    # ── Syntax errors ─────────────────────────────────────────────────

    def test_syntax_error(self):
        errors = validate_code("def foo(")
        assert any("Syntax error" in e for e in errors)

    def test_empty_code(self):
        assert validate_code("") == []


class TestBlockedLists:
    """Sanity-check the frozen sets contain expected entries."""

    @pytest.mark.parametrize("mod", ["os", "sys", "subprocess", "socket", "shutil"])
    def test_blocked_modules(self, mod):
        assert mod in BLOCKED_MODULES

    @pytest.mark.parametrize("attr", ["__import__", "system", "popen", "__subclasses__"])
    def test_blocked_attrs(self, attr):
        assert attr in BLOCKED_ATTRS

    @pytest.mark.parametrize("name", ["eval", "exec", "open", "getattr", "breakpoint"])
    def test_blocked_names(self, name):
        assert name in BLOCKED_NAMES


class TestSafeBuiltins:
    """Verify the safe-builtins allowlist is correct."""

    def test_print_included(self):
        assert "print" in SAFE_BUILTINS

    def test_open_excluded(self):
        assert "open" not in SAFE_BUILTINS

    def test_eval_excluded(self):
        assert "eval" not in SAFE_BUILTINS

    def test_range_included(self):
        assert "range" in SAFE_BUILTINS

    def test_int_included(self):
        assert "int" in SAFE_BUILTINS

    def test_allowed_names_tuple(self):
        assert isinstance(_ALLOWED_BUILTIN_NAMES, tuple)
        assert len(_ALLOWED_BUILTIN_NAMES) > 20


# ═══════════════════════════════════════════════════════════════════════
# 2. Executor
# ═══════════════════════════════════════════════════════════════════════

from services.sandbox.executor import execute_code


class TestExecuteCode:
    """Subprocess-based code execution."""

    def test_basic_arithmetic(self):
        r = execute_code("x = 2 + 3")
        assert r["error"] is None
        assert r["variables"]["x"] == 5

    def test_print_capture(self):
        r = execute_code("print('hello')")
        assert r["error"] is None
        assert "hello" in r["output"]

    def test_multiline(self):
        code = "a = 10\nb = 20\nc = a + b\nprint(c)"
        r = execute_code(code)
        assert r["error"] is None
        assert r["variables"]["c"] == 30
        assert "30" in r["output"]

    def test_returns_execution_time(self):
        r = execute_code("x = 1")
        assert "execution_time_ms" in r
        assert r["execution_time_ms"] >= 0

    def test_runtime_error(self):
        r = execute_code("x = 1 / 0")
        assert r["error"] is not None
        assert "ZeroDivisionError" in r["error"]

    def test_name_error(self):
        r = execute_code("print(undefined_var)")
        assert r["error"] is not None

    def test_policy_violation_import_os(self):
        r = execute_code("import os")
        assert r["error"] is not None
        assert "violation" in r["error"].lower() or "not allowed" in r["error"].lower()

    def test_policy_violation_open(self):
        r = execute_code("open('test.txt')")
        assert r["error"] is not None

    def test_timeout(self):
        r = execute_code("while True: pass", timeout=1)
        assert r["error"] is not None
        assert "timed out" in r["error"].lower()

    def test_prior_state_injection(self):
        r = execute_code("y = x * 2", prior_state={"x": 21})
        assert r["error"] is None
        assert r["variables"]["y"] == 42

    def test_prior_state_preserved_in_output(self):
        """Prior state variables should appear in output variables."""
        r = execute_code("y = x + 1", prior_state={"x": 10})
        assert r["variables"]["x"] == 10
        assert r["variables"]["y"] == 11

    def test_list_operations(self):
        r = execute_code("nums = [1, 2, 3]\ntotal = sum(nums)")
        assert r["error"] is None
        assert r["variables"]["total"] == 6

    def test_dict_operations(self):
        r = execute_code("d = {'a': 1, 'b': 2}\nkeys = list(d.keys())")
        assert r["error"] is None
        assert r["variables"]["keys"] == ["a", "b"]

    def test_string_operations(self):
        r = execute_code("s = 'hello world'\nupper = s.upper()")
        assert r["error"] is None
        assert r["variables"]["upper"] == "HELLO WORLD"

    def test_function_definition(self):
        code = "def double(n): return n * 2\nresult = double(7)"
        r = execute_code(code)
        assert r["error"] is None
        assert r["variables"]["result"] == 14


# ═══════════════════════════════════════════════════════════════════════
# 3. Scratchpad session
# ═══════════════════════════════════════════════════════════════════════

from services.sandbox.scratchpad import ScratchpadSession


class TestScratchpadSession:
    """Session-based execution with persistent state."""

    def test_session_id_auto(self):
        s = ScratchpadSession()
        assert s.session_id
        assert len(s.session_id) == 12

    def test_session_id_custom(self):
        s = ScratchpadSession(session_id="my-session")
        assert s.session_id == "my-session"

    def test_basic_execute(self):
        s = ScratchpadSession()
        r = s.execute("x = 42")
        assert r["error"] is None
        assert r["variables"]["x"] == 42

    def test_state_persists(self):
        """Variable from step 1 is available in step 2."""
        s = ScratchpadSession()
        s.execute("x = 10")
        r = s.execute("y = x + 5")
        assert r["error"] is None
        assert r["variables"]["y"] == 15

    def test_state_accumulates(self):
        """Multiple steps build up state."""
        s = ScratchpadSession()
        s.execute("a = 1")
        s.execute("b = 2")
        r = s.execute("c = a + b")
        assert r["error"] is None
        assert r["variables"]["c"] == 3

    def test_state_property(self):
        s = ScratchpadSession()
        s.execute("x = 99")
        state = s.state
        assert state["x"] == 99
        # Returned is a copy
        state["x"] = 0
        assert s.state["x"] == 99

    def test_history_recorded(self):
        s = ScratchpadSession()
        s.execute("x = 1")
        s.execute("y = 2")
        assert len(s.history) == 2
        assert s.history[0]["code"] == "x = 1"
        assert s.history[1]["code"] == "y = 2"

    def test_reset(self):
        s = ScratchpadSession()
        s.execute("x = 100")
        s.reset()
        assert s.state == {}
        assert s.history == []

    def test_reset_clears_state_for_next_execute(self):
        s = ScratchpadSession()
        s.execute("x = 100")
        s.reset()
        r = s.execute("print(x)")
        # x should not be available after reset
        assert r["error"] is not None

    def test_error_does_not_corrupt_state(self):
        s = ScratchpadSession()
        s.execute("x = 5")
        s.execute("y = 1 / 0")  # error
        assert s.state["x"] == 5
        r = s.execute("z = x + 1")
        assert r["variables"]["z"] == 6


# ═══════════════════════════════════════════════════════════════════════
# 4. Tool registration
# ═══════════════════════════════════════════════════════════════════════

class TestToolRegistration:
    """python_sandbox is registered in the tool registry."""

    def test_tool_exists(self):
        from services.sandbox import ScratchpadSession  # noqa: F401 — triggers registration
        from services.tools.registry import get_tool

        t = get_tool("python_sandbox")
        assert t is not None
        assert t.name == "python_sandbox"

    def test_tool_schema(self):
        from services.tools.registry import get_tool

        t = get_tool("python_sandbox")
        assert "code" in t.input_schema["properties"]
        assert "code" in t.input_schema["required"]

    def test_dispatch_clean_code(self):
        from services.tools.dispatcher import dispatch_tool

        r = dispatch_tool("python_sandbox", {"code": "x = 1 + 1\nprint(x)"})
        assert r["status"] == "success"
        assert "2" in r["result"]["output"]

    def test_dispatch_blocked_code(self):
        from services.tools.dispatcher import dispatch_tool

        r = dispatch_tool("python_sandbox", {"code": "import os"})
        # The handler returns error string but dispatch itself succeeds
        assert r["status"] == "success"
        assert r["result"]["error"] is not None
        assert "not allowed" in r["result"]["error"].lower() or "rejected" in r["result"]["error"].lower()

    def test_dispatch_runtime_error(self):
        from services.tools.dispatcher import dispatch_tool

        r = dispatch_tool("python_sandbox", {"code": "x = 1 / 0"})
        assert r["status"] == "success"
        assert r["result"]["error"] is not None
