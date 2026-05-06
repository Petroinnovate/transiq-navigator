"""
Smart Deduction Trigger — decides whether the deduction engine should run.

Classifies documents via lightweight heuristics (zero LLM cost, <1 ms)
and only triggers deduction for documents that benefit from fact extraction.

Decision matrix:
    ┌──────────────────────┬──────────┬──────────────────────────┐
    │ Document type        │ Complex? │ Deduction?               │
    ├──────────────────────┼──────────┼──────────────────────────┤
    │ financial_report     │ any      │ YES                      │
    │ technical_document   │ any      │ YES                      │
    │ contract             │ any      │ YES                      │
    │ invoice              │ no       │ NO  (structured, simple) │
    │ invoice              │ yes      │ YES (unusual — inspect)  │
    │ simple_text          │ any      │ NO                       │
    │ unknown              │ yes      │ YES (fail-safe)          │
    │ unknown              │ no       │ NO                       │
    └──────────────────────┴──────────┴──────────────────────────┘

Performance: <1 ms for classification + complexity check.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Document type constants ──────────────────────────────────────────

DOCUMENT_TYPES = [
    "financial_report",
    "technical_document",
    "contract",
    "invoice",
    "simple_text",
    "unknown",
]

# Types that ALWAYS need deduction regardless of complexity
_DEDUCTION_REQUIRED_TYPES = frozenset([
    "financial_report",
    "technical_document",
    "contract",
])

# ── Keyword sets for classification (lowercase) ─────────────────────

_FINANCIAL_KEYWORDS = frozenset([
    "revenue", "ebitda", "profit", "balance sheet", "net income",
    "cash flow", "earnings", "fiscal", "dividend", "equity",
    "liabilities", "assets", "operating income", "gross margin",
    "depreciation", "amortization", "capex", "working capital",
])

_TECHNICAL_KEYWORDS = frozenset([
    "algorithm", "system design", "architecture", "api", "database",
    "microservice", "deployment", "infrastructure", "scalability",
    "latency", "throughput", "kubernetes", "docker", "ci/cd",
    "machine learning", "neural network", "pipeline",
])

_CONTRACT_KEYWORDS = frozenset([
    "agreement", "party", "terms", "contract", "obligations",
    "indemnification", "termination", "clause", "jurisdiction",
    "warranty", "liability", "confidentiality", "arbitration",
    "governing law", "effective date", "breach",
])

_INVOICE_KEYWORDS = frozenset([
    "invoice", "total amount", "gst", "bill", "due date",
    "purchase order", "payment terms", "unit price", "quantity",
    "subtotal", "tax", "discount", "remit",
])

# ── Complexity thresholds ────────────────────────────────────────────

_COMPLEXITY_CHUNK_THRESHOLD = 20     # >20 chunks → complex
_COMPLEXITY_CHAR_THRESHOLD = 50_000  # >50K chars → complex


# ====================================================================
# Public API
# ====================================================================

def classify_document(chunks: List[Dict[str, Any]]) -> str:
    """Classify document type from chunk data using keyword heuristics.

    Samples the first 5 chunks (title + opening usually contain the
    strongest signal) and matches against keyword sets.

    Args:
        chunks: List of chunk dicts with at least a ``text`` key.

    Returns:
        One of :data:`DOCUMENT_TYPES`.
    """
    if not chunks:
        return "unknown"

    sample = " ".join(c.get("text", "") for c in chunks[:5]).lower()

    # Score each type by keyword hits
    scores: Dict[str, int] = {
        "financial_report": sum(1 for kw in _FINANCIAL_KEYWORDS if kw in sample),
        "technical_document": sum(1 for kw in _TECHNICAL_KEYWORDS if kw in sample),
        "contract": sum(1 for kw in _CONTRACT_KEYWORDS if kw in sample),
        "invoice": sum(1 for kw in _INVOICE_KEYWORDS if kw in sample),
    }

    best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best_type] >= 2:
        return best_type

    # Single-keyword match still okay for high-signal words
    if scores[best_type] == 1:
        return best_type

    # Nothing matched — check length as simple_text heuristic
    total_chars = sum(len(c.get("text", "")) for c in chunks)
    if total_chars < 2000:
        return "simple_text"

    return "unknown"


def is_complex_document(chunks: List[Dict[str, Any]]) -> bool:
    """Determine whether a document is complex based on size heuristics.

    A document is complex if it has many chunks or the raw character
    count exceeds a threshold.  These are fast O(n) checks.

    Args:
        chunks: List of chunk dicts with at least a ``text`` key.

    Returns:
        ``True`` if the document exceeds complexity thresholds.
    """
    if not chunks:
        return False

    if len(chunks) > _COMPLEXITY_CHUNK_THRESHOLD:
        return True

    total_chars = sum(len(c.get("text", "")) for c in chunks)
    if total_chars > _COMPLEXITY_CHAR_THRESHOLD:
        return True

    return False


def should_run_deduction(
    doc_type: str,
    is_complex: bool,
    force: Optional[bool] = None,
) -> bool:
    """Decide whether the deduction engine should run.

    Args:
        doc_type:   Result of :func:`classify_document`.
        is_complex: Result of :func:`is_complex_document`.
        force:      Explicit override. ``True`` forces deduction on,
                    ``False`` forces it off, ``None`` uses smart logic.

    Returns:
        ``True`` when deduction should execute.
    """
    # Explicit override has highest priority
    if force is not None:
        return force

    # Types that always need deduction
    if doc_type in _DEDUCTION_REQUIRED_TYPES:
        return True

    # Complex documents of any type get deduction (fail-safe for unknown)
    if is_complex:
        return True

    # Simple / invoice / unknown-but-short → skip
    return False


def evaluate_deduction_trigger(
    chunks: List[Dict[str, Any]],
    force: Optional[bool] = None,
) -> Dict[str, Any]:
    """Run the full trigger evaluation and return a decision record.

    This is the primary entry point used by the orchestrator.  It
    combines classification, complexity detection, and the decision
    into a single call and returns all metadata for logging / storage.

    Args:
        chunks: Chunk dicts from the chunking stage.
        force:  ``True`` / ``False`` to override, ``None`` for smart mode.

    Returns:
        Dict with keys:
            - ``run_deduction`` (bool)
            - ``document_type`` (str)
            - ``is_complex`` (bool)
            - ``reason`` (str): human-readable explanation
    """
    try:
        doc_type = classify_document(chunks)
        complex_flag = is_complex_document(chunks)
        decision = should_run_deduction(doc_type, complex_flag, force=force)

        if force is True:
            reason = "forced by caller"
        elif force is False:
            reason = "disabled by caller"
        elif doc_type in _DEDUCTION_REQUIRED_TYPES:
            reason = f"document type '{doc_type}' requires deduction"
        elif complex_flag:
            reason = f"complex document ({len(chunks)} chunks)"
        else:
            reason = f"simple '{doc_type}' document — deduction skipped"

        logger.info(
            "Deduction trigger: type=%s, complex=%s, decision=%s (%s)",
            doc_type, complex_flag, decision, reason,
        )

        return {
            "run_deduction": decision,
            "document_type": doc_type,
            "is_complex": complex_flag,
            "reason": reason,
        }

    except Exception as exc:
        # Fail-safe: run deduction if classification itself errors
        logger.warning("Deduction trigger classification failed (%s) — defaulting to ON", exc)
        return {
            "run_deduction": True,
            "document_type": "unknown",
            "is_complex": False,
            "reason": f"classification error ({exc}) — fail-safe ON",
        }
