"""
Streaming Layer — Real-time event streaming for LLM + tool execution.

Re-exports the public API::

    from services.streaming import get_streaming_manager, StreamingManager
    from services.streaming import StreamEvent, ALL_EVENT_TYPES
"""
from services.streaming.event_types import (       # noqa: F401
    StreamEvent,
    ALL_EVENT_TYPES,
    LLM_START,
    LLM_TOKEN,
    LLM_END,
    TOOL_START,
    TOOL_PROGRESS,
    TOOL_END,
    FINAL_RESPONSE,
    llm_start_event,
    llm_token_event,
    llm_end_event,
    tool_start_event,
    tool_progress_event,
    tool_end_event,
    final_response_event,
)
from services.streaming.streamer import (          # noqa: F401
    StreamingManager,
    get_streaming_manager,
)
