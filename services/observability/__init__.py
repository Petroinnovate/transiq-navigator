"""
Observability Layer — Structured logging, tracing, and metrics.

Re-exports::

    from services.observability import obs_logger, tracer, metrics
    from services.observability import start_trace, end_trace
"""
from services.observability.logger import (              # noqa: F401
    request as log_request,
    tool_call as log_tool_call,
    llm_call as log_llm_call,
    response as log_response,
    error as log_error,
    capture_exception as log_capture_exception,
)
from services.observability.tracer import (              # noqa: F401
    Trace,
    start_trace,
    end_trace,
    get_trace,
    get_recent_traces,
)
from services.observability import metrics               # noqa: F401

# Convenience alias — callers can do ``from services.observability import obs_logger``
from services.observability import logger as obs_logger  # noqa: F401
