"""
Response Module — Clean, structured, user-friendly response composition.

Re-exports::

    from services.response import compose_response
    from services.response import format_kpi, format_predictive, format_risk, format_six_sigma
"""
from services.response.composer import compose_response              # noqa: F401
from services.response.formatter import (                            # noqa: F401
    format_kpi,
    format_predictive,
    format_risk,
    format_six_sigma,
    format_tool_result,
)
from services.response.templates import (                            # noqa: F401
    RESPONSE_TEMPLATE,
    empty_response,
    SECTION_TEMPLATES,
)
