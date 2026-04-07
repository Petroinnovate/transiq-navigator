"""
Glossary Filter for TransIQ

Provides fast, pure-Python glossary pre-filtering.
No external libraries, no LLM calls, no regex per term.

Public API:
    build_term_index(glossary)           -> dict[str, str]
    filter_glossary(text, glossary, ...)  -> list[GlossaryEntry]
    format_for_prompt(terms)             -> str

Usage:
    from app.intelligence.domain_glossary import DOMAIN_GLOSSARY
    from app.intelligence.glossary_filter import build_term_index, filter_glossary, format_for_prompt

    _TERM_INDEX = build_term_index(DOMAIN_GLOSSARY)   # once at module load

    def before_llm_call(document_text):
        terms = filter_glossary(document_text, DOMAIN_GLOSSARY, _TERM_INDEX)
        return format_for_prompt(terms)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.intelligence.domain_glossary import GlossaryEntry


# ---------------------------------------------------------------------------
# Build index
# ---------------------------------------------------------------------------

def build_term_index(glossary: dict) -> dict[str, str]:
    """
    Pre-compute a flat lookup: lowercase_alias -> canonical_key.

    Called once at startup (not per request). Result is shared across all calls.

    Args:
        glossary: DOMAIN_GLOSSARY dict  {key: GlossaryEntry}

    Returns:
        Flat dict: {"dpmo": "DPMO", "defects per million": "DPMO", ...}
    """
    index: dict[str, str] = {}
    for key, entry in glossary.items():
        # Index the canonical term itself
        index[entry.term.lower()] = key
        # Index every alias
        for alias in entry.aliases:
            index[alias.lower()] = key
    return index


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

def filter_glossary(
    text: str,
    glossary: dict,
    term_index: dict[str, str],
    *,
    max_terms: int = 30,
) -> list:
    """
    Return relevant GlossaryEntry objects for the given document text.

    Strategy (pure string, no regex):
      1. Always include entries with always_include=True.
      2. Lowercase the document text once.
      3. Check each alias from term_index against the lowercased text.
      4. Rank by match count (how many aliases of that entry appear in text).
      5. Fill remaining slots up to max_terms, ordered by match count desc.

    Args:
        text:       Raw document text (any length).
        glossary:   DOMAIN_GLOSSARY dict.
        term_index: Output of build_term_index(glossary).
        max_terms:  Hard cap on returned terms.

    Returns:
        Ordered list of GlossaryEntry — always_include entries first,
        then remaining entries by relevance.
    """
    lowered = text.lower()

    # Count alias hits per glossary key
    hit_counts: dict[str, int] = {}
    for alias_lower, key in term_index.items():
        if alias_lower in lowered:
            hit_counts[key] = hit_counts.get(key, 0) + 1

    # Partition: always_include vs matched (not always_include)
    always: list = []
    matched: list = []

    seen_keys: set[str] = set()

    # Always-include first (regardless of hit count)
    for key, entry in glossary.items():
        if entry.always_include:
            always.append(entry)
            seen_keys.add(key)

    # Remaining: matched entries sorted by hit count descending
    ranked = sorted(
        [(key, count) for key, count in hit_counts.items() if key not in seen_keys],
        key=lambda x: x[1],
        reverse=True,
    )
    for key, _ in ranked:
        matched.append(glossary[key])

    # Combine and cap
    combined = always + matched
    return combined[:max_terms]


# ---------------------------------------------------------------------------
# Format for prompt
# ---------------------------------------------------------------------------

def format_for_prompt(terms: list) -> str:
    """
    Serialize filtered GlossaryEntry list into a compact prompt string.

    Format:
        "DMAIC: Six Sigma framework — Define, ... | DPMO: defects per million ..."

    Returns empty string if terms is empty (caller can skip injection).

    Args:
        terms: Output of filter_glossary().

    Returns:
        Pipe-delimited string of prompt_hints, or "" if no terms.
    """
    if not terms:
        return ""
    return " | ".join(entry.prompt_hint for entry in terms)


# ---------------------------------------------------------------------------
# Basic self-tests (run this file directly to verify)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from app.intelligence.domain_glossary import DOMAIN_GLOSSARY

    INDEX = build_term_index(DOMAIN_GLOSSARY)

    # ── Test 1: always_include terms appear even with empty text ─────────────
    result = filter_glossary("", DOMAIN_GLOSSARY, INDEX)
    always_terms = [e.term for e in result]
    always_expected = [k for k, v in DOMAIN_GLOSSARY.items() if v.always_include]
    assert len(result) == len(always_expected), (
        f"Test 1 FAILED: expected {len(always_expected)} always_include terms, got {len(result)}"
    )
    print(f"[PASS] Test 1 — always_include: {always_terms}")

    # ── Test 2: exact match — "DPMO" present in text ────────────────────────
    text_with_dpmo = "The process had a DPMO of 3400 last quarter."
    result2 = filter_glossary(text_with_dpmo, DOMAIN_GLOSSARY, INDEX)
    matched_terms = [e.term for e in result2]
    assert "DPMO" in matched_terms, f"Test 2 FAILED: DPMO not found in {matched_terms}"
    print(f"[PASS] Test 2 — exact match: 'DPMO' found in results")

    # ── Test 3: substring alias match — "rate of penetration" ───────────────
    text_with_rop = "Daily drilling report shows rate of penetration was 45 ft/hr."
    result3 = filter_glossary(text_with_rop, DOMAIN_GLOSSARY, INDEX)
    matched3 = [e.term for e in result3]
    assert "ROP" in matched3, f"Test 3 FAILED: ROP not found in {matched3}"
    print(f"[PASS] Test 3 — alias match: 'rate of penetration' → ROP found")

    # ── Test 4: max_terms cap ────────────────────────────────────────────────
    # Text that hits every single term
    rich_text = " ".join(
        alias
        for entry in DOMAIN_GLOSSARY.values()
        for alias in entry.aliases
    )
    result4 = filter_glossary(rich_text, DOMAIN_GLOSSARY, INDEX, max_terms=5)
    assert len(result4) <= 5, f"Test 4 FAILED: got {len(result4)} terms, expected ≤ 5"
    print(f"[PASS] Test 4 — max_terms cap: {len(result4)} terms returned (cap=5)")

    # ── Test 5: format_for_prompt returns non-empty string ───────────────────
    text_for_fmt = "The sigma level and DPMO were both reviewed."
    terms5 = filter_glossary(text_for_fmt, DOMAIN_GLOSSARY, INDEX)
    formatted = format_for_prompt(terms5)
    assert isinstance(formatted, str) and len(formatted) > 0, "Test 5 FAILED: empty format output"
    print(f"[PASS] Test 5 — format_for_prompt: {len(formatted)} chars, starts with '{formatted[:40]}...'")

    # ── Test 6: format_for_prompt empty list returns empty string ────────────
    formatted_empty = format_for_prompt([])
    assert formatted_empty == "", f"Test 6 FAILED: expected '', got '{formatted_empty}'"
    print("[PASS] Test 6 — format_for_prompt([]) returns empty string")

    print("\nAll tests passed.")
