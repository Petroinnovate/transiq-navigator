"""
Sandbox — Safety layer.

Validates code **before** execution by:

1. AST-level static analysis — blocks imports, attribute access, and calls
   to dangerous names.
2. Restricted builtins — only a curated allowlist is available at runtime.
3. Blocked module list — even if an import somehow gets through, the
   subprocess environment removes these from ``sys.modules``.

Usage::

    from services.sandbox.safety import validate_code, SAFE_BUILTINS
    errors = validate_code("import os; os.system('rm -rf /')")
    assert errors  # ["Import of module 'os' is not allowed", ...]
"""
from __future__ import annotations

import ast
from typing import List


# ── Blocked modules ────────────────────────────────────────────────────
# These are never importable inside the sandbox.

BLOCKED_MODULES: frozenset[str] = frozenset({
    "os", "sys", "subprocess", "shutil", "pathlib",
    "socket", "http", "urllib", "requests", "httpx",
    "ctypes", "importlib", "runpy", "code", "codeop",
    "signal", "multiprocessing", "threading", "_thread",
    "pickle", "shelve", "marshal",
    "webbrowser", "antigravity",
    "builtins", "__builtin__",
    "io", "tempfile", "glob", "fnmatch",
    "sqlite3", "dbm",
    "smtplib", "ftplib", "telnetlib",
    "xml", "html",
})

# ── Blocked attribute names ────────────────────────────────────────────
# Accessing these on *any* object is rejected.

BLOCKED_ATTRS: frozenset[str] = frozenset({
    "__import__", "__subclasses__", "__bases__", "__class__",
    "__globals__", "__code__", "__builtins__",
    "system", "popen", "exec", "eval", "compile",
    "execfile", "input",
})

# ── Blocked global names / calls ───────────────────────────────────────

BLOCKED_NAMES: frozenset[str] = frozenset({
    "eval", "exec", "compile", "__import__",
    "globals", "locals", "vars",
    "getattr", "setattr", "delattr",
    "open", "input", "breakpoint",
    "exit", "quit",
})

# ── Safe builtins allowlist ────────────────────────────────────────────
# Only these are injected into the sandbox namespace.

_ALLOWED_BUILTIN_NAMES: tuple[str, ...] = (
    # Types
    "bool", "int", "float", "complex", "str", "bytes", "bytearray",
    "list", "tuple", "set", "frozenset", "dict",
    "type", "object", "None", "True", "False",
    # Iteration / functional
    "range", "enumerate", "zip", "map", "filter", "reversed", "sorted",
    "iter", "next",
    # Math / conversion
    "abs", "round", "min", "max", "sum", "pow", "divmod",
    "bin", "oct", "hex", "ord", "chr",
    "len", "hash", "id", "isinstance", "issubclass",
    # String / repr
    "repr", "format", "ascii",
    # Containers
    "all", "any",
    # Exceptions (so user code can catch them)
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "ZeroDivisionError", "AttributeError", "RuntimeError", "StopIteration",
    "ArithmeticError", "LookupError", "OverflowError",
    # Printing (captured by sandbox)
    "print",
)

import builtins as _builtins

SAFE_BUILTINS: dict[str, object] = {
    name: getattr(_builtins, name)
    for name in _ALLOWED_BUILTIN_NAMES
    if hasattr(_builtins, name)
}


# ── AST validator ──────────────────────────────────────────────────────

class _Validator(ast.NodeVisitor):
    """Walk the AST and collect policy violations."""

    def __init__(self) -> None:
        self.errors: List[str] = []

    # ── Imports ────────────────────────────────────────────────────────

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in BLOCKED_MODULES:
                self.errors.append(f"Import of module '{alias.name}' is not allowed")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            root = node.module.split(".")[0]
            if root in BLOCKED_MODULES:
                self.errors.append(f"Import from '{node.module}' is not allowed")
        self.generic_visit(node)

    # ── Attribute access ───────────────────────────────────────────────

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in BLOCKED_ATTRS:
            self.errors.append(f"Access to attribute '{node.attr}' is not allowed")
        self.generic_visit(node)

    # ── Name access ────────────────────────────────────────────────────

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in BLOCKED_NAMES:
            self.errors.append(f"Use of '{node.id}' is not allowed")
        self.generic_visit(node)

    # ── Call-site checks ───────────────────────────────────────────────

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_NAMES:
            self.errors.append(f"Call to '{node.func.id}' is not allowed")
        self.generic_visit(node)


# ── Public API ─────────────────────────────────────────────────────────

def validate_code(code: str) -> List[str]:
    """Return a list of policy violations found in *code*.

    An empty list means the code passed static validation.
    This does NOT guarantee safety — the sandbox also enforces
    runtime restrictions.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"Syntax error: {exc}"]

    v = _Validator()
    v.visit(tree)
    return v.errors
