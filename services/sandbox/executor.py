"""
Sandbox — Subprocess-based code executor.

Runs user-supplied Python code in an **isolated subprocess** with:

* Restricted builtins (no ``open``, ``eval``, ``exec``, etc.)
* Blocked dangerous modules (``os``, ``subprocess``, ``socket``, …)
* Hard timeout (default 5 seconds).
* No shared memory with the main application.

Usage::

    from services.sandbox.executor import execute_code
    result = execute_code("x = 2 + 2\\nprint(x)")
    # {"output": "4\\n", "error": None, "execution_time_ms": 12.3}
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import time
from typing import Any, Dict, Optional

from services.sandbox.safety import validate_code

# ── Defaults ───────────────────────────────────────────────────────────
MAX_EXECUTION_SECONDS = 5
MAX_OUTPUT_BYTES = 50_000  # 50 KB stdout cap


# ── Subprocess wrapper script ──────────────────────────────────────────
# This is injected as the ``-c`` argument to a new Python process.
# It:
#   1. Removes dangerous modules from sys.modules.
#   2. Restricts builtins.
#   3. Captures stdout and any exception.
#   4. Prints a JSON envelope to stdout for the parent to parse.

_RUNNER_TEMPLATE = textwrap.dedent(r'''
import sys, json, io, time as _time

# ── 1. Remove dangerous modules ──────────────────────────────────────
_BLOCKED = {blocked_modules}
for _m in list(sys.modules):
    if _m.split(".")[0] in _BLOCKED:
        del sys.modules[_m]

# ── 2. Build restricted builtins ─────────────────────────────────────
_ALLOWED = {allowed_builtins}
_bi = __builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__
_safe = {{k: _bi[k] for k in _ALLOWED if k in _bi}}

# Capture stdout
_buf = io.StringIO()
_safe["print"] = lambda *a, **kw: print(*a, **kw, file=_buf)

# ── 3. Execute user code ─────────────────────────────────────────────
_ns = {{"__builtins__": _safe}}

# Inject prior state if provided
_prior_state = {prior_state}
_ns.update(_prior_state)

_err = None
_t0 = _time.perf_counter()
try:
    exec({user_code!r}, _ns)
except Exception as _e:
    _err = f"{{type(_e).__name__}}: {{_e}}"
_elapsed = (_time.perf_counter() - _t0) * 1000

# ── 4. Collect output + user-defined variables ───────────────────────
_output = _buf.getvalue()
_user_vars = {{}}
for _k, _v in _ns.items():
    if _k.startswith("_") or _k == "__builtins__":
        continue
    try:
        json.dumps(_v)          # only JSON-serialisable values
        _user_vars[_k] = _v
    except (TypeError, ValueError, OverflowError):
        _user_vars[_k] = repr(_v)

print(json.dumps({{"output": _output, "error": _err,
                   "execution_time_ms": round(_elapsed, 2),
                   "variables": _user_vars}}), file=sys.stdout)
''')


def _build_runner(
    code: str,
    prior_state: Dict[str, Any] | None = None,
) -> str:
    """Render the runner script with the user code embedded."""
    from services.sandbox.safety import BLOCKED_MODULES, _ALLOWED_BUILTIN_NAMES

    return _RUNNER_TEMPLATE.format(
        blocked_modules=repr(set(BLOCKED_MODULES)),
        allowed_builtins=repr(list(_ALLOWED_BUILTIN_NAMES)),
        user_code=code,
        prior_state=repr(prior_state or {}),
    )


# ── Public API ─────────────────────────────────────────────────────────

def execute_code(
    code: str,
    *,
    timeout: int = MAX_EXECUTION_SECONDS,
    prior_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Execute *code* in an isolated subprocess.

    Parameters
    ----------
    code:
        Python source code to execute.
    timeout:
        Maximum wall-clock seconds before the subprocess is killed.
    prior_state:
        Optional dict of variable bindings to inject (for session
        persistence).

    Returns
    -------
    ::

        {
            "output": str,       # captured stdout
            "error": str | None, # exception message if any
            "execution_time_ms": float,
            "variables": dict,   # user-defined variables (JSON-safe)
        }
    """
    # ── Static validation first ────────────────────────────────────────
    violations = validate_code(code)
    if violations:
        return {
            "output": "",
            "error": "Code policy violation: " + "; ".join(violations),
            "execution_time_ms": 0,
            "variables": {},
        }

    runner = _build_runner(code, prior_state)

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-c", runner],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        elapsed = (time.perf_counter() - t0) * 1000
        return {
            "output": "",
            "error": f"Execution timed out after {timeout}s",
            "execution_time_ms": round(elapsed, 2),
            "variables": {},
        }
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return {
            "output": "",
            "error": f"Subprocess error: {exc}",
            "execution_time_ms": round(elapsed, 2),
            "variables": {},
        }

    elapsed = (time.perf_counter() - t0) * 1000

    # ── Parse the JSON envelope from stdout ────────────────────────────
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    # The runner prints exactly one JSON line as the last output
    lines = stdout.strip().rsplit("\n", 1)
    if len(lines) == 2:
        # Runner captured print + JSON
        json_line = lines[1]
    elif len(lines) == 1:
        json_line = lines[0]
    else:
        json_line = ""

    try:
        result = json.loads(json_line)
    except (json.JSONDecodeError, TypeError):
        # Runner itself crashed — fall back to stderr
        return {
            "output": stdout[:MAX_OUTPUT_BYTES],
            "error": stderr[:MAX_OUTPUT_BYTES] if stderr else "Sandbox runner failed",
            "execution_time_ms": round(elapsed, 2),
            "variables": {},
        }

    # Enforce output cap
    if len(result.get("output", "")) > MAX_OUTPUT_BYTES:
        result["output"] = result["output"][:MAX_OUTPUT_BYTES] + "\n... (output truncated)"

    result["execution_time_ms"] = round(elapsed, 2)
    return result
