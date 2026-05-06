"""
Observability — In-Memory Metrics Collector.

Tracks three families of metrics:

  * **Latency** — per-component p50/p95/p99/mean/max durations (ms).
  * **Tool usage** — call counts per tool name.
  * **Error rates** — error counts per component.

All storage is in-memory (Python dicts + lists).  No external systems.

Usage::

    from services.observability import metrics

    metrics.record_latency("chat_orchestrator", 345.2)
    metrics.record_tool_usage("kpi_analysis")
    metrics.record_error("tool_dispatcher", "kpi_analysis")

    print(metrics.get_latency_stats("chat_orchestrator"))
    print(metrics.get_tool_usage())
    print(metrics.get_error_rates())
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Dict, List


_lock = threading.Lock()

# Latency: component → list of duration_ms floats
_latency: Dict[str, List[float]] = defaultdict(list)
_MAX_LATENCY_SAMPLES = 2000

# Tool usage: tool_name → call count
_tool_usage: Dict[str, int] = defaultdict(int)

# Errors: component → {error_key: count}
_errors: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

# Total requests per component
_requests: Dict[str, int] = defaultdict(int)


# ── Latency ────────────────────────────────────────────────────────────

def record_latency(component: str, duration_ms: float) -> None:
    """Append a latency sample for *component*."""
    with _lock:
        samples = _latency[component]
        samples.append(duration_ms)
        if len(samples) > _MAX_LATENCY_SAMPLES:
            # Trim oldest half
            _latency[component] = samples[len(samples) // 2:]


def get_latency_stats(component: str) -> Dict[str, Any]:
    """Return p50/p95/p99/mean/max/count for *component*."""
    with _lock:
        samples = list(_latency.get(component, []))
    if not samples:
        return {"component": component, "count": 0}
    samples.sort()
    n = len(samples)
    return {
        "component": component,
        "count": n,
        "mean_ms": round(sum(samples) / n, 2),
        "p50_ms": round(samples[n // 2], 2),
        "p95_ms": round(samples[int(n * 0.95)], 2),
        "p99_ms": round(samples[min(int(n * 0.99), n - 1)], 2),
        "max_ms": round(samples[-1], 2),
    }


def get_all_latency_stats() -> List[Dict[str, Any]]:
    """Return latency stats for every tracked component."""
    with _lock:
        components = list(_latency.keys())
    return [get_latency_stats(c) for c in components]


# ── Tool usage ─────────────────────────────────────────────────────────

def record_tool_usage(tool_name: str) -> None:
    """Increment call count for *tool_name*."""
    with _lock:
        _tool_usage[tool_name] += 1


def get_tool_usage() -> Dict[str, int]:
    """Return tool_name → call count mapping."""
    with _lock:
        return dict(_tool_usage)


# ── Errors ─────────────────────────────────────────────────────────────

def record_error(component: str, error_key: str = "unknown") -> None:
    """Increment error count for *component* / *error_key*."""
    with _lock:
        _errors[component][error_key] += 1


def get_error_rates() -> Dict[str, Dict[str, int]]:
    """Return component → {error_key: count}."""
    with _lock:
        return {c: dict(counts) for c, counts in _errors.items()}


def get_error_count(component: str) -> int:
    """Total error count for *component*."""
    with _lock:
        return sum(_errors.get(component, {}).values())


# ── Requests ───────────────────────────────────────────────────────────

def record_request(component: str) -> None:
    """Increment total request count for *component*."""
    with _lock:
        _requests[component] += 1


def get_request_counts() -> Dict[str, int]:
    """Return component → total request count."""
    with _lock:
        return dict(_requests)


# ── Snapshot ───────────────────────────────────────────────────────────

def snapshot() -> Dict[str, Any]:
    """Return a full metrics snapshot (latency + usage + errors + requests)."""
    return {
        "latency": get_all_latency_stats(),
        "tool_usage": get_tool_usage(),
        "errors": get_error_rates(),
        "requests": get_request_counts(),
    }


# ── Testing ────────────────────────────────────────────────────────────

def _reset() -> None:
    """Clear all metrics (for testing)."""
    with _lock:
        _latency.clear()
        _tool_usage.clear()
        _errors.clear()
        _requests.clear()
