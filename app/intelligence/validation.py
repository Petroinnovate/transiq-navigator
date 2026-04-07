"""
Validation Engine — KPI & Recommendation Quality Gate
======================================================

Filters out hallucinated, low-confidence, and duplicate KPIs before
they reach the frontend. All filtering is deterministic and traceable.

Key functions:
  validate_kpis(kpis)                → filtered + deduplicated KPI list
  validate_recommendations(recs, kpis) → recs that are KPI-anchored
  cross_check_values(kpis, raw_text) → drop KPIs whose values don't appear in source
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
MIN_CONFIDENCE = 0.55       # KPIs below this are dropped
MIN_TITLE_LEN = 3           # KPIs with < 3 char title are garbage
DUPLICATE_RATIO_THRESHOLD = 0.85  # >85% similar title → deduplicate
MAX_KPIS_OUT = 50           # Hard upper bound

# ---------------------------------------------------------------------------
# Embedding-based semantic similarity (with Jaccard fallback)
# ---------------------------------------------------------------------------
_embedding_model = None
_USE_EMBEDDINGS = True  # Set False to force Jaccard-only


def _get_embedding_model():
    """Lazy-load sentence-transformers model (cached after first call)."""
    global _embedding_model, _USE_EMBEDDINGS
    if _embedding_model is not None:
        return _embedding_model
    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Loaded sentence-transformers model for semantic dedup")
        return _embedding_model
    except ImportError:
        logger.info("sentence-transformers not installed — using Jaccard dedup")
        _USE_EMBEDDINGS = False
        return None
    except Exception as e:
        logger.warning(f"Failed to load embedding model: {e} — using Jaccard dedup")
        _USE_EMBEDDINGS = False
        return None


def _cosine_similarity(a, b) -> float:
    """Cosine similarity between two numpy arrays."""
    import numpy as np
    dot = float(np.dot(a, b))
    norm = float(np.linalg.norm(a) * np.linalg.norm(b))
    if norm == 0:
        return 0.0
    return dot / norm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_title(title: str) -> str:
    """Lowercase, remove punctuation, collapse whitespace."""
    s = unicodedata.normalize("NFKD", title).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _title_similarity(a: str, b: str) -> float:
    """
    Semantic similarity between two KPI titles.
    Uses embedding cosine similarity if sentence-transformers is available,
    falls back to Jaccard token overlap.
    """
    if _USE_EMBEDDINGS:
        model = _get_embedding_model()
        if model is not None:
            try:
                embeddings = model.encode([a, b], show_progress_bar=False)
                return float(_cosine_similarity(embeddings[0], embeddings[1]))
            except Exception:
                pass
    # Fallback: Jaccard token overlap
    return _jaccard_similarity(a, b)


def _jaccard_similarity(a: str, b: str) -> float:
    """Simple token overlap ratio (Jaccard-like)."""
    ta = set(_normalize_title(a).split())
    tb = set(_normalize_title(b).split())
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    intersection = ta & tb
    union = ta | tb
    return len(intersection) / len(union)


def _value_visible_in_text(value: Any, text: str) -> bool:
    """
    Check whether a numeric value appears in the source text.
    Allows slight formatting variation (commas, % sign, etc.).
    A value of 0 always passes (could be a legitimate zero-state).
    """
    if value is None:
        return False
    try:
        v = float(str(value).replace(",", ""))
    except ValueError:
        return True  # Non-numeric — can't cross-check; give benefit of doubt

    if v == 0:
        return True

    # Build regex for the number — matches 1,234.5 or 1234.5 or 1234 etc.
    pattern = re.compile(r"\b" + str(int(v)) + r"\b")
    return bool(pattern.search(text))


# ---------------------------------------------------------------------------
# Main validation functions
# ---------------------------------------------------------------------------

def validate_kpis(
    kpis: List[Dict[str, Any]],
    raw_text: str = "",
    *,
    apply_cross_check: bool = False,
) -> List[Dict[str, Any]]:
    """
    Full validation pipeline for a list of KPIs.

    Steps:
      1. Drop KPIs missing 'title' or 'value'
      2. Drop KPIs with tiny titles (noise)
      3. Drop KPIs with confidence < MIN_CONFIDENCE
      4. Optional: drop KPIs whose value doesn't appear in source text
      5. Deduplicate by title similarity (keep highest confidence)
      6. Cap at MAX_KPIS_OUT
    """
    passed: List[Dict[str, Any]] = []
    dropped_reasons: List[str] = []

    for idx, kpi in enumerate(kpis):
        title = (kpi.get("title") or "").strip()
        value = kpi.get("value")

        # 1. Must have a title
        if not title:
            dropped_reasons.append(f"[{idx}] missing title")
            continue

        # 2. Title must be meaningful
        if len(title) < MIN_TITLE_LEN:
            dropped_reasons.append(f"[{idx}] title too short: '{title}'")
            continue

        # 3. Must have a value (zero is OK)
        if value is None:
            dropped_reasons.append(f"[{idx}] '{title}' — missing value")
            continue

        # 4. Confidence gate
        conf = kpi.get("confidence")
        if conf is not None:
            try:
                if float(conf) < MIN_CONFIDENCE:
                    dropped_reasons.append(
                        f"[{idx}] '{title}' — confidence {conf} < {MIN_CONFIDENCE}"
                    )
                    continue
            except (TypeError, ValueError):
                pass

        # 5. Optional source cross-check
        if apply_cross_check and raw_text:
            if not _value_visible_in_text(value, raw_text):
                dropped_reasons.append(
                    f"[{idx}] '{title}' — value {value} not found in source text"
                )
                continue

        passed.append(kpi)

    if dropped_reasons:
        logger.debug("Validation dropped %d KPIs:\n  %s", len(dropped_reasons), "\n  ".join(dropped_reasons))

    # 6. Deduplicate by title similarity (keep highest confidence)
    deduplicated = _deduplicate_kpis(passed)

    # 7. Cap
    result = deduplicated[:MAX_KPIS_OUT]
    logger.info(
        "KPI validation: %d input → %d passed → %d after dedup → %d final",
        len(kpis), len(passed), len(deduplicated), len(result),
    )
    return result


def _deduplicate_kpis(kpis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove near-duplicate KPIs by title similarity.
    For each cluster of duplicates, keep the one with the highest confidence.
    """
    if not kpis:
        return []

    # Sort by confidence descending so we keep the best
    def _conf(k: Dict) -> float:
        try:
            return float(k.get("confidence") or 0)
        except (TypeError, ValueError):
            return 0.0

    sorted_kpis = sorted(kpis, key=_conf, reverse=True)
    result: List[Dict[str, Any]] = []

    for candidate in sorted_kpis:
        is_dup = False
        for accepted in result:
            sim = _title_similarity(candidate.get("title", ""), accepted.get("title", ""))
            if sim >= DUPLICATE_RATIO_THRESHOLD:
                is_dup = True
                break
        if not is_dup:
            result.append(candidate)

    return result


def validate_recommendations(
    recs: List[Dict[str, Any]],
    kpis: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Validate recommendations:
    - Must have 'title' or 'action'
    - Prefer recs that reference a kpi_id or kpiId matching a known KPI
    - Flag as 'generic' those without KPI linkage (don't drop — just tag)
    """
    kpi_ids = {k.get("id") for k in kpis if k.get("id")}
    kpi_titles = {_normalize_title(k.get("title", "")) for k in kpis}

    result: List[Dict[str, Any]] = []
    for rec in recs:
        title = (rec.get("title") or rec.get("action") or "").strip()
        if not title:
            continue

        r = dict(rec)
        linked = False

        kpi_ref = rec.get("kpi_id") or rec.get("kpiId")
        if kpi_ref and kpi_ref in kpi_ids:
            linked = True

        # Also try title match
        if not linked and kpi_ref:
            if _normalize_title(str(kpi_ref)) in kpi_titles:
                linked = True

        r["kpi_linked"] = linked
        if not linked:
            r["quality_flag"] = "generic — no KPI anchor"
        result.append(r)

    # Sort: KPI-linked recs first
    result.sort(key=lambda r: (0 if r.get("kpi_linked") else 1))
    return result


def validate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate findings — keep ones that have a meaningful description.
    Drops empty or very short findings.
    """
    result: List[Dict[str, Any]] = []
    seen_norms: List[str] = []

    for f in findings:
        desc = (f.get("finding") or f.get("description") or f.get("text") or "").strip()
        if len(desc) < 10:
            continue

        norm = _normalize_title(desc[:60])
        # Check for near-duplicate findings
        is_dup = any(_title_similarity(norm, s) > 0.85 for s in seen_norms)
        if is_dup:
            continue

        seen_norms.append(norm)
        result.append(f)

    return result
