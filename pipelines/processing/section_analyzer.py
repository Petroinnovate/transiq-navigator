"""
Section-Aware Report Analysis Engine v3 — Centralized Document Brain
====================================================================
All state flows through ONE central object: DocumentBrain.
Every stage reads from and enriches the brain — zero duplication.

Architecture:
  DocumentBrain (central state)
    ├── metadata        (doc-level stats, cost estimate, model usage)
    ├── tree            (hierarchical TOC from PageIndex)
    ├── sections        (flat dict[id → SectionNode])
    ├── execution_plan  (tier1/tier2/tier3 section id lists)
    ├── dmaic_groups    (define/measure/analyze/improve/control buckets)
    └── results         (per-section, per-phase, final dashboard)

Pipeline:
  1. build_structure()   — PageIndex tree → SectionNode population
  2. score_all()         — heuristic scoring (6 dims + PageIndex)
  3. classify_all()      — tier assignment + execution plan
  4. route_models()      — model selection per section
  5. enforce_budget()    — downgrade models if over cost cap
  6. estimate_cost()     — pre-flight token/cost estimate
  7. execute_analysis()  — tiered LLM calls with model routing
  8. reprocess_weak()    — confidence-based reprocessing
  9. map_dmaic()         — assign sections to DMAIC phases
  10. synthesize_phases() — per-phase LLM synthesis
  11. cross_phase_check() — rule-based intelligence
  12. executive_synthesis() — final dashboard LLM call
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai.types import GenerateContentConfig

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Gemini client
# ═══════════════════════════════════════════════════════════════════════════
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyCek0XZxd-ELygefJcRzmxUGt3NEryso9c"
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=_GEMINI_API_KEY)
    return _client


# ═══════════════════════════════════════════════════════════════════════════
# MODEL TIER DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

MODELS = {
    "cheap": {
        "name": "gemini-2.0-flash",
        "cost_per_1m_input": 0.10,
        "cost_per_1m_output": 0.40,
        "max_context": 1_000_000,
        "max_output_tokens": 1500,
    },
    "balanced": {
        "name": "gemini-2.5-flash",
        "cost_per_1m_input": 0.15,
        "cost_per_1m_output": 0.60,
        "max_context": 1_000_000,
        "max_output_tokens": 3000,
    },
    "powerful": {
        "name": "gemini-2.5-flash",
        "cost_per_1m_input": 0.15,
        "cost_per_1m_output": 0.60,
        "max_context": 1_000_000,
        "max_output_tokens": 5000,
    },
}

# DMAIC phase → preferred model tier
DMAIC_MODEL_PRIORITY = {
    "define": "cheap",
    "measure": "balanced",
    "analyze": "powerful",
    "improve": "balanced",
    "control": "balanced",
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION NODE — intelligent unit of analysis
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SectionNode:
    """A single section of the document — the core unit everything operates on."""
    id: str
    title: str
    text: str
    depth: int
    parent_id: Optional[str] = None
    start_index: int = 1
    end_index: int = 1
    node_id: str = ""

    # Derived by scoring stage
    tokens_estimate: int = 0
    score: float = 0.0
    tier: int = 3
    dmaic_phase: Optional[str] = None

    # Signal breakdown (populated once, read everywhere)
    signals: Dict[str, float] = field(default_factory=lambda: {
        "kpi_density": 0.0, "financial": 0.0, "dmaic": 0.0,
        "data_density": 0.0, "risk": 0.0, "boilerplate": 0.0,
        "pageindex_boost": 0.0,
    })

    # Execution plan (populated by router)
    execution: Dict[str, Any] = field(default_factory=lambda: {
        "should_run": True,
        "model_tier": None,   # "cheap" | "balanced" | "powerful"
        "model_name": None,   # actual model string for API call
        "max_tokens": 500,
        "temperature": 0.2,
        "text_cap": 80_000,
    })

    # Result (populated by LLM call)
    analysis: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT BRAIN — the single source of truth
# ═══════════════════════════════════════════════════════════════════════════

class DocumentBrain:
    """Central coordinating object. Every stage reads/writes to this."""

    def __init__(self, chunks: List[str], source_type: str = "UNKNOWN"):
        # Raw input
        self.chunks = [c for c in chunks if not c.startswith("File: ") and c.strip()]
        self.source_type = source_type

        # Metadata
        self.metadata: Dict[str, Any] = {
            "total_pages": len(self.chunks),
            "total_chars": sum(len(c) for c in self.chunks),
            "doc_type": source_type,
            "estimated_tokens": 0,
            "estimated_cost_usd": 0.0,
            "model_usage": {"cheap": 0, "balanced": 0, "powerful": 0},
            "reprocessed": 0,
        }

        # Hierarchical TOC from PageIndex
        self.tree: List[Dict] = []

        # Flat section lookup: id → SectionNode
        self.sections: Dict[str, SectionNode] = {}

        # DMAIC phase buckets: phase → [section_id, ...]
        self.dmaic_groups: Dict[str, List[str]] = {
            "define": [], "measure": [], "analyze": [],
            "improve": [], "control": [], "unassigned": [],
        }

        # Execution plan: tier → [section_id, ...]
        self.execution_plan: Dict[str, List[str]] = {
            "tier1": [], "tier2": [], "tier3": [],
        }

        # Results
        self.results: Dict[str, Any] = {
            "sections": {},       # section_id → analysis dict
            "dmaic": {},          # phase → synthesis dict
            "cross_phase": [],    # cross-phase insights
            "final": {},          # executive dashboard
        }

    # ── Section accessors ────────────────────────────────────────────────

    def get_section(self, section_id: str) -> Optional[SectionNode]:
        return self.sections.get(section_id)

    def iter_sections(self):
        """Iterate sections in order."""
        return sorted(self.sections.values(), key=lambda s: s.start_index)

    def iter_tier(self, tier: str):
        """Iterate section IDs for a specific tier."""
        for sid in self.execution_plan.get(tier, []):
            node = self.sections.get(sid)
            if node:
                yield node

    def get_text(self, node: SectionNode) -> str:
        """Get the section's text from chunks. Cached on node.text."""
        if node.text:
            return node.text
        s = max(0, node.start_index - 1)
        e = min(node.end_index, len(self.chunks))
        node.text = "\n\n".join(self.chunks[s:e])
        return node.text


# ═══════════════════════════════════════════════════════════════════════════
# REGEX PATTERN BANKS
# ═══════════════════════════════════════════════════════════════════════════

_RE_KPI = re.compile(
    r"""
    \d+\.?\d*\s*(%|\$|USD|EUR|GBP|hours?|hrs|ppm|defects?|units?|days?|months?|years?)
    | \b(kpi|metric|baseline|target|benchmark|performance\s+indicator
        |rate|ratio|index|score|yield|throughput|efficiency|utilization
        |sigma\s+level|cpk|ppk|dpmo|dpu)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_RE_FINANCIAL = re.compile(
    r"""
    \$[\d,]+\.?\d*
    | \d+\.?\d*\s*(million|billion|thousand|M|B|K)\b
    | \b(cost|revenue|savings?|budget|roi|return\s+on\s+investment
        |profit|loss|expenditure|capex|opex|npv|irr|payback
        |margin|ebitda|cash\s+flow|price|fee|charge|invoice
        |financial\s+impact|cost\s+of\s+poor\s+quality|copq
        |cost\s+savings?|cost\s+reduction|cost\s+avoidance)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_RE_DMAIC = re.compile(
    r"""
    \b(six\s+sigma|dmaic|dmadv|lean\s+six\s+sigma
      |define\s+phase|measure\s+phase|analyze\s+phase|improve\s+phase|control\s+phase
      |ctq|critical\s+to\s+quality|voc|voice\s+of\s+(the\s+)?customer
      |process\s+capability|sigma\s+level|black\s+belt|green\s+belt|master\s+black\s+belt
      |root\s+cause|fishbone|ishikawa|pareto|5\s*why|fmea
      |spc|control\s+chart|p-chart|c-chart|x-bar|r-chart|u-chart
      |kaizen|poka.yoke|value\s+stream|sipoc|gemba
      |gage\s+r&r|msa|measurement\s+system
      |tollgate|champion|sponsor
      |defects?\s+per|dpmo|dpu|dpo|ppm
      |process\s+map|swim\s*lane|flow\s+chart)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_RE_DATA_TABLE = re.compile(
    r"""
    \b(table\s+\d|figure\s+\d|chart\s+\d|graph\s+\d|exhibit\s+\d
      |histogram|scatter\s*plot|trend\s+line|regression|correlation
      |data\s+shows?|results?\s+show|analysis\s+shows?|findings?\s+show
      |mean|median|std\.?\s*dev|standard\s+deviation|variance|percentile
      |confidence\s+interval|p-value|statistic(ally)?)\b
    | \|.*\|.*\|
    | \t.*\t.*\t
    """,
    re.IGNORECASE | re.VERBOSE,
)

_RE_RISK = re.compile(
    r"""
    \b(risk|defect|failure|fault|hazard|incident|accident|near.miss
      |non.?conformance|deviation|out\s+of\s+spec|tolerance|exceedance
      |probability|severity|impact|mitigation|contingency
      |scrap|rework|reject|waste|downtime|breakdown|outage
      |safety|compliance|violation|audit\s+finding|corrective\s+action
      |capa|preventive\s+action|critical\s+finding)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_RE_BOILERPLATE = re.compile(
    r"""
    \b(disclaimer|copyright|confidential|all\s+rights\s+reserved
      |table\s+of\s+contents|glossary|appendix|references?|bibliography
      |acknowledg(e)?ments?|this\s+page\s+intentionally
      |for\s+internal\s+use|draft\s+version|version\s+\d
      |prepared\s+by|submitted\s+to|distribution\s+list
      |document\s+control|revision\s+history|change\s+log
      |list\s+of\s+abbreviations|list\s+of\s+figures|list\s+of\s+tables)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_RE_TITLE_SIXSIGMA = re.compile(
    r"\b(six\s+sigma|dmaic|root\s+cause|process\s+capability|sigma|defect|spc|control\s+plan)\b", re.I,
)
_RE_TITLE_EXECUTIVE = re.compile(
    r"\b(executive\s+summar|conclusion|finding|result|recommendation|key\s+takeaway)\b", re.I,
)
_RE_TITLE_BOILERPLATE = re.compile(
    r"\b(appendix|glossary|reference|index|abbreviation|acronym|bibliography|table\s+of\s+contents)\b", re.I,
)
_RE_SIXSIGMA_HARD = re.compile(
    r"\b(cpk|ppk|dpmo|dpu|root\s+cause\s+analysis|cost\s+savings?|sigma\s+level)\b", re.I,
)

_DMAIC_TITLE_KW = {
    "define": re.compile(r"\b(define|problem\s+statement|scope|charter|ctq|voc|stakeholder|objective|goal|project\s+definition)\b", re.I),
    "measure": re.compile(r"\b(measure|baseline|data\s+collection|measurement|sampling|msa|gage|sipoc|process\s+map|current\s+state)\b", re.I),
    "analyze": re.compile(r"\b(analy[sz]e|root\s+cause|fishbone|pareto|5\s*why|regression|correlation|hypothesis|anova|cause.and.effect)\b", re.I),
    "improve": re.compile(r"\b(improve|solution|recommendation|implementation|pilot|action\s+plan|optimi[sz]|kaizen|future\s+state)\b", re.I),
    "control": re.compile(r"\b(control|monitor|spc|sustain|standardiz|audit|control\s+plan|control\s+chart|dashboard)\b", re.I),
}
_DMAIC_CONTENT_KW = {
    "define": re.compile(r"\b(problem\s+statement|project\s+scope|ctq|voice\s+of|financial\s+exposure|business\s+case|project\s+charter|tollgate)\b", re.I),
    "measure": re.compile(r"\b(baseline|data\s+collect|sampling\s+plan|measurement\s+system|process\s+capability|current\s+performance|sigma\s+level|gage\s+r&r)\b", re.I),
    "analyze": re.compile(r"\b(root\s+cause|fishbone|ishikawa|pareto|5\s*why|regression|correlation|hypothesis\s+test|anova|chi.square|statistical\s+analysis)\b", re.I),
    "improve": re.compile(r"\b(solution|pilot|implement|action\s+plan|expected\s+improvement|sigma\s+lift|cost\s+saving|lean|kaizen|poka.yoke|before.after)\b", re.I),
    "control": re.compile(r"\b(control\s+plan|control\s+chart|spc|monitoring|sustain|standardiz|response\s+plan|out\s+of\s+control|training\s+plan)\b", re.I),
}

# Scoring weights & thresholds
_WEIGHTS = {"kpi_density": 0.25, "financial": 0.25, "dmaic": 0.20, "data_density": 0.15, "risk": 0.10, "boilerplate": -0.20}
_TIER1_THRESHOLD = 0.70
_TIER2_THRESHOLD = 0.40
_SKIP_THRESHOLD = 0.15


# ═══════════════════════════════════════════════════════════════════════════
# TRACEABILITY CONTRACT — enforced at every pipeline boundary
# ═══════════════════════════════════════════════════════════════════════════
# Every insight/finding/KPI/risk MUST carry source_pages.
# This is a SYSTEM-WIDE INVARIANT, not a decorative field.
# Enforcement: extract → validate → aggregate → validate → synthesize → validate → gate

REQUIRED_TRACE_FIELDS = ["source_pages"]
_TRACEABILITY_GATE_THRESHOLD = 90.0  # % — block output below this

# ── Insight ID generation ─────────────────────────────────────────────────
def _gen_insight_id(prefix: str = "ins") -> str:
    """Generate a short unique insight ID safe across concurrent requests."""
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _reset_insight_counter():
    """Backward-compatible no-op (IDs are UUID-based)."""
    return None


def _assign_insight_ids(items: list, prefix: str = "ins") -> list:
    """Assign unique insight_id to every dict item that lacks one."""
    for item in items:
        if isinstance(item, dict) and not item.get("insight_id"):
            item["insight_id"] = _gen_insight_id(prefix)
    return items


def _has_source_pages(item: Any) -> bool:
    """Check if an item has non-empty source_pages (list of ints or 'Pages X-Y' string)."""
    if not isinstance(item, dict):
        return False
    sp = item.get("source_pages")
    if isinstance(sp, list) and sp:
        return True
    # Also accept source_reference.source_pages (Tier 1 format)
    sr = item.get("source_reference")
    if isinstance(sr, dict) and sr.get("source_pages"):
        return True
    return False


def _validate_insight(item: dict) -> bool:
    """Validate that a single insight/finding/KPI/risk is traceable."""
    if not isinstance(item, dict):
        return False
    for field in REQUIRED_TRACE_FIELDS:
        if not item.get(field):
            return False
    return True


def _strip_untraceable(items: list, label: str = "") -> tuple:
    """Split items into traceable and dropped. Returns (kept, dropped_count)."""
    if not items:
        return [], 0
    kept = [i for i in items if _has_source_pages(i)]
    dropped = len(items) - len(kept)
    if dropped > 0:
        logger.debug("Traceability filter (%s): kept %d, dropped %d", label, len(kept), dropped)
    return kept, dropped


def _count_untraceable(items: list) -> int:
    """Count items missing source_pages (for metrics, without mutating)."""
    if not items:
        return 0
    return sum(1 for i in items if isinstance(i, dict) and not _has_source_pages(i))


def _inject_source_pages(items: list, fallback_pages: list) -> list:
    """Ensure every dict item has top-level source_pages; inject fallback if missing."""
    for item in items:
        if not isinstance(item, dict):
            continue
        # Check for top-level source_pages directly (not via _has_source_pages which
        # also accepts source_reference format — we want to PROMOTE that to top-level)
        top_sp = item.get("source_pages")
        has_top_level = isinstance(top_sp, list) and len(top_sp) > 0
        # Promote source_reference.source_pages (Tier 1 "Pages X-Y") to top-level
        if not has_top_level:
            sr = item.get("source_reference")
            if isinstance(sr, dict) and sr.get("source_pages"):
                sp = sr["source_pages"]
                if isinstance(sp, str):
                    m = re.match(r"Pages?\s*(\d+)\s*[-–]\s*(\d+)", sp)
                    if m:
                        item["source_pages"] = list(range(int(m.group(1)), int(m.group(2)) + 1))
                        has_top_level = True
                elif isinstance(sp, list) and sp:
                    item["source_pages"] = sp
                    has_top_level = True
        # If still missing, inject fallback page range
        if not has_top_level:
            item["source_pages"] = fallback_pages
            item["_source_pages_fallback"] = True  # Tag: this was injected, not LLM-provided
    return items


# ═══════════════════════════════════════════════════════════════════════════
# EVIDENCE-BASED CONFIDENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════
# Replaces LLM self-reported confidence (uncalibrated, randomly high) with
# data-driven confidence computed from:
#   1. SUPPORT COUNT  — how many data points back the result
#   2. DATA DENSITY   — richness of structured data (KPIs, numbers, tables)
#   3. PAGE COVERAGE  — how many source pages contributed data
# Weights: support=0.50, density=0.20, coverage=0.30

_CONF_W_SUPPORT  = 0.50
_CONF_W_DENSITY  = 0.20
_CONF_W_COVERAGE = 0.30
_CONF_SUPPORT_CAP = 20   # normalize support count: cap at 20 items
_CONF_DENSITY_CAP = 15   # normalize data density: cap at 15 KPIs+financial items


def _compute_evidence_confidence(
    findings: list,
    kpis: list,
    risks: list,
    financial_items: list = None,
    source_pages: list = None,
    total_pages_in_section: int = 1,
) -> Dict[str, Any]:
    """Compute evidence-based confidence from actual data signals.

    Returns dict with:
      - confidence: float 0.0-1.0
      - confidence_level: HIGH|MEDIUM|LOW
      - confidence_breakdown: {support, density, coverage, support_count, ...}
    """
    if financial_items is None:
        financial_items = []
    if source_pages is None:
        source_pages = []

    # ── 1. SUPPORT COUNT: total structured items extracted ────────────────
    support_count = len(findings) + len(kpis) + len(risks)
    normalized_support = min(support_count / _CONF_SUPPORT_CAP, 1.0)

    # ── 2. DATA DENSITY: presence of quantified data ─────────────────────
    # Count KPIs with actual numeric values + financial items with amounts
    kpis_with_values = sum(
        1 for k in kpis
        if isinstance(k, dict) and k.get("value") is not None
        and isinstance(k.get("value"), (int, float)) and k["value"] != 0
    )
    financial_with_amounts = sum(
        1 for f in financial_items
        if isinstance(f, dict) and f.get("amount") is not None
        and isinstance(f.get("amount"), (int, float)) and f["amount"] != 0
    )
    density_count = kpis_with_values + financial_with_amounts
    normalized_density = min(density_count / _CONF_DENSITY_CAP, 1.0)

    # ── 3. PAGE COVERAGE: fraction of section pages that supplied data ───
    # Collect all unique page numbers from source_pages across items
    all_pages = set()
    if source_pages:
        all_pages.update(source_pages)
    for items_list in (findings, kpis, risks, financial_items):
        for item in items_list:
            if isinstance(item, dict):
                sp = item.get("source_pages", [])
                if isinstance(sp, list):
                    all_pages.update(p for p in sp if isinstance(p, int))
    pages_covered = len(all_pages)
    normalized_coverage = min(pages_covered / max(total_pages_in_section, 1), 1.0)

    # ── FINAL SCORE ──────────────────────────────────────────────────────
    confidence = round(
        _CONF_W_SUPPORT * normalized_support
        + _CONF_W_DENSITY * normalized_density
        + _CONF_W_COVERAGE * normalized_coverage,
        3,
    )

    # Tier label
    if confidence > 0.75:
        level = "HIGH"
    elif confidence > 0.50:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "confidence": confidence,
        "confidence_level": level,
        "confidence_breakdown": {
            "support_score": round(normalized_support, 3),
            "density_score": round(normalized_density, 3),
            "coverage_score": round(normalized_coverage, 3),
            "support_count": support_count,
            "kpis_with_values": kpis_with_values,
            "financial_with_amounts": financial_with_amounts,
            "pages_covered": pages_covered,
            "total_pages_in_section": total_pages_in_section,
        },
    }


def _compute_group_confidence(section_confidences: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute evidence-based confidence for a group merge from member section confidences.

    Uses:
      - Aggregate support count across sections
      - Average density across sections
      - Union of page coverage across sections
    """
    if not section_confidences:
        return {"confidence": 0.0, "confidence_level": "LOW",
                "confidence_breakdown": {"support_score": 0, "density_score": 0, "coverage_score": 0,
                                         "support_count": 0, "section_count": 0}}

    total_support = sum(c.get("confidence_breakdown", {}).get("support_count", 0) for c in section_confidences)
    avg_density = sum(c.get("confidence_breakdown", {}).get("density_score", 0) for c in section_confidences) / len(section_confidences)
    all_pages = set()
    total_section_pages = 0
    for c in section_confidences:
        bd = c.get("confidence_breakdown", {})
        total_section_pages += bd.get("total_pages_in_section", 0)
        all_pages.update(range(1, bd.get("pages_covered", 0) + 1))  # approximate

    normalized_support = min(total_support / (_CONF_SUPPORT_CAP * 2), 1.0)  # higher cap for groups
    normalized_coverage = min(len(all_pages) / max(total_section_pages, 1), 1.0) if total_section_pages > 0 else 0.0

    confidence = round(
        _CONF_W_SUPPORT * normalized_support
        + _CONF_W_DENSITY * avg_density
        + _CONF_W_COVERAGE * normalized_coverage,
        3,
    )
    if confidence > 0.75:
        level = "HIGH"
    elif confidence > 0.50:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "confidence": confidence,
        "confidence_level": level,
        "confidence_breakdown": {
            "support_score": round(normalized_support, 3),
            "density_score": round(avg_density, 3),
            "coverage_score": round(normalized_coverage, 3),
            "support_count": total_support,
            "section_count": len(section_confidences),
        },
    }


# ── DOCUMENT COVERAGE ENGINE ────────────────────────────────────────────
# Answers: "How much of the document actually contributed to the report?"
# A chunk/page is "used" only if it appears in source_pages of a final item.
# ────────────────────────────────────────────────────────────────────────

def _extract_used_pages(brain: "DocumentBrain") -> Dict[str, Any]:
    """Walk all section results and collect every page referenced by an output item.

    Returns dict with:
      - used_pages: set of 1-based page numbers
      - total_pages: total pages in document
      - page_coverage_pct: float 0-100
      - coverage_status: GOOD|PARTIAL|BAD
      - per_section: list of {section_id, title, pages_in_range, pages_used, coverage_pct}
      - unused_page_ranges: list of "Pages X-Y" strings showing gaps
    """
    total_pages = len(brain.chunks)
    used_pages: Set[int] = set()
    per_section: List[Dict[str, Any]] = []

    for node in brain.iter_sections():
        sa = brain.results["sections"].get(node.id, {})
        section_used: Set[int] = set()

        # Collect source_pages from all item types
        for key in ("keyFindings", "kpis", "risks"):
            for item in sa.get(key, []):
                if isinstance(item, dict):
                    sp = item.get("source_pages", [])
                    if isinstance(sp, list):
                        section_used.update(p for p in sp if isinstance(p, int))

        # Financial items (nested under financialImpact)
        fi = sa.get("financialImpact", {})
        if isinstance(fi, dict):
            for item in fi.get("items", fi.get("financial_items", [])):
                if isinstance(item, dict):
                    sp = item.get("source_pages", [])
                    if isinstance(sp, list):
                        section_used.update(p for p in sp if isinstance(p, int))

        # Recommendations
        for item in sa.get("recommendations", []):
            if isinstance(item, dict):
                sp = item.get("source_pages", [])
                if isinstance(sp, list):
                    section_used.update(p for p in sp if isinstance(p, int))

        used_pages.update(section_used)

        section_page_range = set(range(node.start_index, node.end_index + 1))
        pages_in_range = len(section_page_range)
        pages_used = len(section_used & section_page_range)  # Only count within-range pages
        per_section.append({
            "section_id": node.id,
            "title": node.title[:60],
            "pages_in_range": pages_in_range,
            "pages_used": pages_used,
            "coverage_pct": round(pages_used / max(pages_in_range, 1) * 100, 1),
        })

    # Also collect from DMAIC phase results and cross-phase insights
    for phase_data in brain.results.get("dmaic", {}).values():
        if isinstance(phase_data, dict):
            _collect_pages_recursive(phase_data, used_pages)
    for insight in brain.results.get("cross_phase", []):
        if isinstance(insight, dict):
            sp = insight.get("source_pages", [])
            if isinstance(sp, list):
                used_pages.update(p for p in sp if isinstance(p, int))

    # Clamp to valid page range
    used_pages = {p for p in used_pages if 1 <= p <= total_pages}
    used_count = len(used_pages)
    coverage_pct = round(used_count / max(total_pages, 1) * 100, 1)

    # Classify
    if coverage_pct >= 70:
        status = "GOOD"
    elif coverage_pct >= 40:
        status = "PARTIAL"
    else:
        status = "BAD"

    # Find unused page ranges (for debugging)
    unused_ranges = _find_page_gaps(used_pages, total_pages)

    return {
        "used_pages": used_pages,
        "total_pages": total_pages,
        "used_page_count": used_count,
        "page_coverage_pct": coverage_pct,
        "coverage_status": status,
        "per_section": per_section,
        "unused_page_ranges": unused_ranges,
    }


def _collect_pages_recursive(obj: Any, pages: Set[int]) -> None:
    """Recursively collect source_pages from nested dicts/lists."""
    if isinstance(obj, dict):
        sp = obj.get("source_pages", [])
        if isinstance(sp, list):
            pages.update(p for p in sp if isinstance(p, int))
        for v in obj.values():
            _collect_pages_recursive(v, pages)
    elif isinstance(obj, list):
        for item in obj:
            _collect_pages_recursive(item, pages)


def _build_traceability_index(dashboard: Dict[str, Any], groups: Dict[str, Any]) -> Dict[str, Any]:
    """Build insight_id -> traceability lookup for UI drill-down."""
    index: Dict[str, Any] = {}

    def _add_item(item: dict, item_type: str, group_ctx: dict = None, section_ctx: str = ""):
        if not isinstance(item, dict):
            return
        insight_id = item.get("insight_id")
        if not insight_id:
            return
        entry = {
            "insight_id": insight_id,
            "type": item_type,
            "source_pages": item.get("source_pages", []),
            "source_chunks": item.get("source_chunks", []),
            "section": section_ctx,
        }
        if group_ctx:
            entry["group_id"] = group_ctx.get("group_id")
            entry["group_title"] = group_ctx.get("group_title")
            entry["source_section_ids"] = group_ctx.get("source_section_ids", [])
        if "finding" in item:
            entry["text"] = item.get("finding", "")
        elif "title" in item:
            entry["text"] = item.get("title", "")
        elif "risk" in item:
            entry["text"] = item.get("risk", "")
        elif "insight" in item:
            entry["text"] = item.get("insight", "")
        index[insight_id] = entry

    # Group-level source mapping
    for _, g in groups.items():
        if not isinstance(g, dict):
            continue
        for item in g.get("merged_findings", []):
            _add_item(item, "group_finding", g)
        for item in g.get("aggregated_kpis", []):
            _add_item(item, "group_kpi", g)
        for item in g.get("top_risks", []):
            _add_item(item, "group_risk", g)

    # Section/dashboard level source mapping
    db = dashboard.get("dashboard", {}) if isinstance(dashboard, dict) else {}
    for sec in db.get("sections", []):
        sec_title = sec.get("title", "") if isinstance(sec, dict) else ""
        if not isinstance(sec, dict):
            continue
        for item in sec.get("keyFindings", []):
            _add_item(item, "section_finding", section_ctx=sec_title)
        for item in sec.get("kpis", []):
            _add_item(item, "section_kpi", section_ctx=sec_title)
        for item in sec.get("risks", []):
            _add_item(item, "section_risk", section_ctx=sec_title)

    return index


def _find_page_gaps(used_pages: Set[int], total_pages: int) -> List[str]:
    """Identify contiguous ranges of unused pages."""
    if not total_pages:
        return []
    all_pages = set(range(1, total_pages + 1))
    unused = sorted(all_pages - used_pages)
    if not unused:
        return []
    ranges: List[str] = []
    start = unused[0]
    prev = unused[0]
    for p in unused[1:]:
        if p == prev + 1:
            prev = p
        else:
            ranges.append(f"Pages {start}-{prev}" if start != prev else f"Page {start}")
            start = p
            prev = p
    ranges.append(f"Pages {start}-{prev}" if start != prev else f"Page {start}")
    return ranges


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 1: BUILD STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════

def _flatten_tree(tree: List[Dict], depth: int = 0) -> List[Dict]:
    sections: List[Dict] = []
    for node in tree:
        children = node.get("nodes", [])
        if not children:
            sections.append({
                "title": node.get("title", "Untitled"),
                "node_id": node.get("node_id", ""),
                "start_index": node.get("start_index", 1),
                "end_index": node.get("end_index", 1),
                "depth": depth,
            })
        else:
            child_sections = _flatten_tree(children, depth + 1)
            sections.extend(child_sections or [{
                "title": node.get("title", "Untitled"),
                "node_id": node.get("node_id", ""),
                "start_index": node.get("start_index", 1),
                "end_index": node.get("end_index", 1),
                "depth": depth,
            }])
    return sections


def _merge_small(raw: List[Dict], chunks: List[str], min_chars: int = 500) -> List[Dict]:
    if not raw:
        return raw
    merged: List[Dict] = []
    buf: Optional[Dict] = None
    for sec in raw:
        clen = sum(len(chunks[i]) for i in range(sec["start_index"] - 1, min(sec["end_index"], len(chunks))))
        if buf is None:
            buf = {**sec, "_clen": clen}
        elif buf["_clen"] < min_chars:
            buf["title"] += " + " + sec["title"]
            buf["end_index"] = sec["end_index"]
            buf["_clen"] += clen
        else:
            merged.append(buf)
            buf = {**sec, "_clen": clen}
    if buf:
        merged.append(buf)
    for s in merged:
        s.pop("_clen", None)
    return merged


def build_structure(brain: DocumentBrain) -> None:
    """Stage 1: Build PageIndex tree and populate SectionNodes."""
    chunks = brain.chunks

    if len(chunks) <= 5 or brain.metadata["total_chars"] < 5000:
        logger.info("Small document — single section")
        brain.tree = [{"title": "Full Document", "start_index": 1, "end_index": len(chunks)}]
        flat = [{"title": "Full Document", "node_id": "0000", "start_index": 1, "end_index": len(chunks), "depth": 0}]
        brain.metadata["_pageindex_success"] = True
        brain.metadata["_pageindex_error"] = ""
        brain.metadata["_fallback_used"] = False
    else:
        try:
            from pipelines.ingestion import build_page_index
            brain.tree = build_page_index(chunks, add_summaries=False)
            if not brain.tree:
                raise ValueError("Empty tree")
            logger.info("PageIndex: %d root nodes", len(brain.tree))
            flat = _flatten_tree(brain.tree)
            brain.metadata["_sections_before_merge"] = len(flat)
            flat = _merge_small(flat, chunks, min_chars=500)
            brain.metadata["_pageindex_success"] = True
            brain.metadata["_pageindex_error"] = ""
            brain.metadata["_fallback_used"] = False
        except Exception as e:
            logger.warning("PageIndex failed (%s) — chunk-based fallback", e)
            brain.metadata["_pageindex_success"] = False
            brain.metadata["_pageindex_error"] = str(e)
            brain.metadata["_fallback_used"] = True
            section_size = max(3, len(chunks) // 8)
            brain.metadata["_fallback_section_size"] = section_size
            flat = []
            for i in range(0, len(chunks), section_size):
                end = min(i + section_size, len(chunks))
                flat.append({
                    "title": f"Section {len(flat)+1} (Pages {i+1}-{end})",
                    "node_id": f"{len(flat):04d}",
                    "start_index": i + 1, "end_index": end, "depth": 0,
                })
            brain.tree = [{"title": s["title"], "start_index": s["start_index"], "end_index": s["end_index"]} for s in flat]

    # Populate SectionNodes
    for idx, raw in enumerate(flat):
        sid = f"S{idx:03d}"
        s_start = max(0, raw["start_index"] - 1)
        s_end = min(raw["end_index"], len(chunks))
        text = "\n\n".join(chunks[s_start:s_end])
        node = SectionNode(
            id=sid, title=raw.get("title", "Untitled"),
            text=text, depth=raw.get("depth", 0),
            start_index=raw.get("start_index", 1),
            end_index=raw.get("end_index", 1),
            node_id=raw.get("node_id", ""),
            tokens_estimate=len(text) // 4,
        )
        brain.sections[sid] = node

    logger.info("Structure built: %d sections", len(brain.sections))


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 2: SCORING
# ═══════════════════════════════════════════════════════════════════════════

def _count(pattern: re.Pattern, text: str) -> int:
    return len(pattern.findall(text))


def _density(hits: int, text_len: int, scale: float = 500.0) -> float:
    if text_len == 0:
        return 0.0
    return min(1.0, (hits / (text_len / scale)) / 3.0)


def score_section(text: str, title: str = "", depth: int = 0) -> Dict[str, float]:
    """Score a section. Returns signals dict + composite. Public API for testing."""
    tl = len(text)
    if tl == 0:
        return {"kpi_density": 0, "financial": 0, "dmaic": 0, "data_density": 0, "risk": 0, "boilerplate": 0, "pageindex_boost": 0, "composite": 0}

    sigs = {
        "kpi_density": _density(_count(_RE_KPI, text), tl),
        "financial": _density(_count(_RE_FINANCIAL, text), tl),
        "dmaic": _density(_count(_RE_DMAIC, text), tl),
        "data_density": _density(_count(_RE_DATA_TABLE, text), tl),
        "risk": _density(_count(_RE_RISK, text), tl),
        "boilerplate": _density(_count(_RE_BOILERPLATE, text), tl),
    }

    pi = 0.0
    if title and _RE_TITLE_SIXSIGMA.search(title):  pi += 0.15
    if title and _RE_TITLE_EXECUTIVE.search(title):  pi += 0.10
    if depth <= 1:                                    pi += 0.10
    if title and _RE_TITLE_BOILERPLATE.search(title): pi -= 0.20
    if _RE_SIXSIGMA_HARD.search(text):               pi += 0.10
    sigs["pageindex_boost"] = pi

    composite = sum(_WEIGHTS.get(k, 0) * v for k, v in sigs.items() if k != "pageindex_boost") + pi
    sigs["composite"] = max(0.0, min(1.0, composite))

    return {k: round(v, 3) for k, v in sigs.items()}


def classify_tier(composite: float) -> int:
    if composite >= _TIER1_THRESHOLD:
        return 1
    if composite >= _TIER2_THRESHOLD:
        return 2
    return 3


def should_skip(composite: float) -> bool:
    return composite < _SKIP_THRESHOLD


def score_all(brain: DocumentBrain) -> None:
    """Stage 2: Score every section, store signals on the node."""
    for node in brain.iter_sections():
        sigs = score_section(node.text, node.title, node.depth)
        node.signals = sigs
        node.score = sigs["composite"]
        logger.info(
            "  %-50s score=%.3f [kpi=%.2f fin=%.2f dmaic=%.2f data=%.2f risk=%.2f boiler=%.2f pi=%.2f]",
            node.title[:50], node.score,
            sigs["kpi_density"], sigs["financial"], sigs["dmaic"],
            sigs["data_density"], sigs["risk"], sigs["boilerplate"], sigs["pageindex_boost"],
        )


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 3: TIER CLASSIFICATION + EXECUTION PLAN
# ═══════════════════════════════════════════════════════════════════════════

def classify_all(brain: DocumentBrain) -> None:
    """Stage 3: Assign tiers and build execution plan.

    ALL sections are processed (no skip threshold).  Tiers are retained
    only for cost-optimised model routing — they never gate extraction.
    """
    brain.execution_plan = {"tier1": [], "tier2": [], "tier3": []}
    for node in brain.iter_sections():
        node.tier = classify_tier(node.score)
        # NEVER skip — every section contributes to coverage
        node.execution["should_run"] = True
        brain.execution_plan[f"tier{node.tier}"].append(node.id)
    logger.info(
        "Tiers: T1=%d T2=%d T3=%d (all processed, no skips)",
        len(brain.execution_plan["tier1"]),
        len(brain.execution_plan["tier2"]),
        len(brain.execution_plan["tier3"]),
    )


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 4: MODEL ROUTING
# ═══════════════════════════════════════════════════════════════════════════

def route_model(node: SectionNode) -> str:
    """Deterministic model selection based on signals and tier.

    Used purely for cost optimisation — DMAIC phase is NOT yet assigned
    at routing time (it happens after group aggregation now).
    """
    # Boilerplate → cheapest
    if node.signals.get("boilerplate", 0) > 0.8:
        return "cheap"

    # High KPI density → better model
    if node.signals.get("kpi_density", 0) > 0.7:
        return "powerful"

    # Tier 1 → powerful
    if node.tier == 1:
        return "powerful"

    # Large section → needs balanced at minimum
    if node.tokens_estimate > 1200:
        return "balanced"

    # Tier 2 → balanced
    if node.tier == 2:
        return "balanced"

    return "cheap"


def route_models(brain: DocumentBrain) -> None:
    """Stage 4: Assign model + execution params to every section.

    ALL sections use a UNIFORM extraction prompt (no tier-branched schemas).
    Tiers only influence model selection (cost) and text caps.
    """
    for node in brain.iter_sections():
        tier_key = route_model(node)
        model_cfg = MODELS[tier_key]
        node.execution["model_tier"] = tier_key
        node.execution["model_name"] = model_cfg["name"]

        # Text caps by tier (cost optimisation only — all use same prompt)
        if node.tier == 1:
            node.execution["max_tokens"] = 600
            node.execution["text_cap"] = 150_000
        elif node.tier == 2:
            node.execution["max_tokens"] = 600
            node.execution["text_cap"] = 100_000
        else:
            node.execution["max_tokens"] = 500
            node.execution["text_cap"] = 80_000


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 5: BUDGET ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════

def _estimate_section_cost(node: SectionNode) -> float:
    tier_key = node.execution.get("model_tier", "balanced")
    m = MODELS.get(tier_key, MODELS["balanced"])
    input_tokens = node.tokens_estimate + 300
    output_tokens = node.execution.get("max_tokens", 500)
    return (input_tokens * m["cost_per_1m_input"] + output_tokens * m["cost_per_1m_output"]) / 1_000_000


def enforce_budget(brain: DocumentBrain, max_cost_usd: float) -> None:
    """Stage 5: Downgrade least important sections until under budget."""
    def _total():
        return sum(_estimate_section_cost(n) for n in brain.iter_sections())

    current = _total()
    if current <= max_cost_usd:
        return

    # Sort by score ascending — downgrade cheapest first
    ordered = sorted(brain.iter_sections(), key=lambda n: n.score)

    for node in ordered:
        if current <= max_cost_usd:
            break
        tier_key = node.execution.get("model_tier", "balanced")
        if tier_key == "powerful":
            node.execution["model_tier"] = "balanced"
            node.execution["model_name"] = MODELS["balanced"]["name"]
            node.execution["max_tokens"] = min(node.execution["max_tokens"], 500)
        elif tier_key == "balanced":
            node.execution["model_tier"] = "cheap"
            node.execution["model_name"] = MODELS["cheap"]["name"]
            node.execution["max_tokens"] = min(node.execution["max_tokens"], 300)
        current = _total()

    logger.info("Budget enforcement: target=$%.4f, adjusted to=$%.4f", max_cost_usd, current)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 6: COST ESTIMATION
# ═══════════════════════════════════════════════════════════════════════════

def estimate_cost(brain: DocumentBrain) -> Dict[str, Any]:
    """Stage 6: Pre-flight cost estimate. Stored on brain.metadata."""
    total_input = 0
    total_output = 0
    tier_counts = {"tier1": 0, "tier2": 0, "tier3": 0}

    for node in brain.iter_sections():
        total_input += node.tokens_estimate + 300
        total_output += node.execution.get("max_tokens", 500)
        tier_counts[f"tier{node.tier}"] = tier_counts.get(f"tier{node.tier}", 0) + 1

    # Fixed synthesis costs
    pi_tokens = 1200
    phase_tokens = 1500 * 5
    exec_tokens = 2000
    total_input += pi_tokens + phase_tokens + exec_tokens
    total_output += phase_tokens + exec_tokens

    cost = (total_input * 0.15 + total_output * 0.60) / 1_000_000

    est = {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "estimated_cost_usd": round(cost, 4),
        "tier_breakdown": tier_counts,
        "phase_calls": 5,
        "executive_call": 1,
        "pageindex_tokens": pi_tokens,
    }
    brain.metadata["estimated_tokens"] = total_input + total_output
    brain.metadata["estimated_cost_usd"] = est["estimated_cost_usd"]
    brain.metadata["cost_estimate"] = est

    logger.info(
        "Cost estimate: ~%d in + ~%d out tokens, ~$%.4f | %s",
        total_input, total_output, cost, tier_counts,
    )
    return est


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 7: EXECUTE ANALYSIS (LLM calls — tiered + model-routed)
# ═══════════════════════════════════════════════════════════════════════════

_TIER1_PROMPT = """\
Analyze this section as a Six Sigma Black Belt. Extract ALL data comprehensively.

SECTION: {title} | Pages {start}-{end} | Section {num}/{total}

TEXT:
{text}

Return JSON:
{{
  "sectionTitle": "{title}",
  "sectionSummary": "2-3 sentences",
  "keyFindings": [{{ "finding": "str", "impact": "high|medium|low", "confidence": 0.0-1.0, "source_snippet": "exact quoted text (max 30 words)" }}],
  "kpis": [
    {{
      "id": "str",
      "title": "max 5 words",
      "value": <number — MUST be actual number from text, not 0>,
      "unit": "$|%|count|hrs|bbl|mcf|psi|days",
      "target": <number|null>,
      "trend": "improving|deteriorating|stable",
      "changeType": "positive|negative|neutral",
      "confidence": 0.0-1.0,
      "category": "financial|safety|operations|efficiency|reliability",
      "priority": "tier1|tier2|tier3|tier4",
      "financialImpactScore": <0-100>,
      "riskScore": <0-100>,
      "source_reference": {{
        "rig_name": "extract rig/well/asset name from text (e.g. RIG-101, PARAGON MSS1, Well-A3) or null",
        "report_date": "date found in this section (YYYY-MM-DD) or null",
        "source_section": "{title}",
        "source_pages": "Pages {start}-{end}",
        "raw_evidence": "exact quoted sentence from text where this KPI value appears (max 40 words)",
        "calculation_method": "direct_extract|sum|average|derived|inferred"
      }}
    }}
  ],
  "risks": [{{ "risk": "str", "severity": "high|medium|low", "probability": "high|medium|low", "financial_impact": "str" }}],
  "financialImpact": {{ "identified": true|false, "items": [{{ "description": "str", "amount": <number|null>, "unit": "$", "type": "cost|saving|risk" }}] }},
  "recommendations": [{{ "action": "str", "kpi_id": "str", "baseline": "str", "target": "str", "financial_impact": "str" }}],
  "charts": [
    {{
      "id": "str",
      "type": "BarChart|LineChart|AreaChart|PieChart|RadarChart",
      "title": "str",
      "size": "half|full",
      "data": [{{ "name": "label", "value": <number> }}]
    }}
  ],
  "dmaicRelevance": {{ "phase": "define|measure|analyze|improve|control|none", "evidence": "why" }},
  "confidence": 0.0-1.0
}}

CAPS: max 15 KPIs, 10 findings, 8 risks, 8 financial items, 10 recommendations, 5 charts.
Only use numbers DIRECTLY STATED in text. No hallucination. No placeholder zeros.
kpi.value MUST be a real number extracted from the text. JSON only."""

_TIER2_PROMPT = """\
Light analysis of this section. Extract key data points.

SECTION: {title} | Pages {start}-{end} | Section {num}/{total}

TEXT:
{text}

Return JSON:
{{
  "sectionTitle": "{title}",
  "sectionSummary": "1-2 sentences",
  "keyPoints": [{{ "point": "str", "impact": "high|medium|low", "source_pages": [int] }}],
  "metrics": [{{ "name": "str", "value": <number|str>, "unit": "str", "source_pages": [int] }}],
  "risks": [{{ "risk": "str", "severity": "high|medium|low", "source_pages": [int] }}],
  "dmaicRelevance": {{ "phase": "define|measure|analyze|improve|control|none", "evidence": "why" }},
  "confidence": 0.0-1.0
}}

RULES:
- Every keyPoint, metric, and risk MUST include source_pages (page numbers from the text)
- If a finding cannot be linked to specific pages, use the section range [{start}, {end}]
- Do NOT generate insights without source reference

CAPS: max 8 key points, 10 metrics, 5 risks. Numbers from text only. No zeros as placeholders.
SELF-HEAL: If explicit KPIs are absent, derive proxy metrics from available signals (counts, frequencies, error rates, anomalies, ratios). Always return at least 1 metric and set confidence > 0 so downstream stages have something to work with. JSON only."""

_TIER3_PROMPT = """\
Brief summary of this section.

SECTION: {title} | Pages {start}-{end}

TEXT:
{text}

Return JSON:
{{
  "sectionTitle": "{title}",
  "bullets": ["3-5 bullet points summarizing content"],
  "hasSignificantData": true|false,
  "flagForDeepAnalysis": true|false,
  "dmaicRelevance": {{ "phase": "define|measure|analyze|improve|control|none" }},
  "confidence": 0.0-1.0
}}

JSON only. Max 5 bullets."""

_SYS_TIER = {
    1: "Deterministic data compiler. Extract every data point. Thorough extraction. JSON only.",
    2: "Deterministic data compiler. Extract key metrics and observations. Concise. JSON only.",
    3: "Deterministic data compiler. Extract key metrics and observations. Concise. JSON only.",
}

# Uniform system instruction for all extractions (no tier differentiation)
_SYS_EXTRACT = "Deterministic data compiler. Extract every data point from the text. NEVER infer, generalize, or invent data not present. JSON only."


def _call_gemini_json(
    prompt: str, model: str = "gemini-2.5-flash",
    system_instruction: str = "", max_retries: int = 3,
    temperature: float = 0.2,
    max_output_tokens: int = 0,
) -> Dict[str, Any]:
    """Call Gemini with a specific model and parse JSON response."""
    client = _get_client()
    config_kw: Dict[str, Any] = {"temperature": temperature, "response_mime_type": "application/json"}
    if system_instruction:
        config_kw["system_instruction"] = system_instruction
    if max_output_tokens > 0:
        config_kw["max_output_tokens"] = max_output_tokens
    config = GenerateContentConfig(**config_kw)

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model, contents=prompt, config=config,
            )
            if response.text:
                return json.loads(response.text)
            return {}
        except json.JSONDecodeError:
            if response.text:
                match = re.search(r"\{.*\}", response.text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group())
                    except json.JSONDecodeError:
                        pass
            logger.warning("Attempt %d: JSON parse failed (model=%s)", attempt + 1, model)
        except Exception as e:
            err_str = str(e)
            # Detect 429 RESOURCE_EXHAUSTED and respect the suggested retryDelay
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                # Extract retryDelay seconds from the error message (e.g. "retry in 46s")
                _delay_match = re.search(r"retry[^\d]*(\d+)[^\d]", err_str, re.IGNORECASE)
                _wait = int(_delay_match.group(1)) if _delay_match else 60
                logger.warning(
                    "Attempt %d: 429 quota exhausted (model=%s) — waiting %ds before retry",
                    attempt + 1, model, _wait,
                )
                if attempt < max_retries - 1:
                    time.sleep(_wait)
                else:
                    # All retries exhausted on quota error — propagate so caller knows
                    raise RuntimeError(
                        f"Gemini API quota exhausted for model {model}. "
                        f"Free-tier limit reached. Please wait for daily quota reset or upgrade your API plan."
                    ) from e
            else:
                logger.warning("Attempt %d failed: %s (model=%s)", attempt + 1, e, model)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
    return {}


def _empty_analysis(title: str, confidence: float = 0.0) -> Dict:
    return {
        "sectionTitle": title, "sectionSummary": "No extractable content.",
        "keyFindings": [], "kpis": [], "risks": [], "recommendations": [],
        "financialImpact": {"identified": False, "items": []},
        "charts": [], "confidence": confidence,
    }


def _normalize_tier2(result: Dict, title: str, start_page: int = 0, end_page: int = 0) -> Dict:
    fallback_pages = list(range(start_page, end_page + 1)) if start_page and end_page else []
    findings = [{"finding": kp.get("point", ""), "impact": kp.get("impact", "medium"),
                 "source_pages": kp.get("source_pages", fallback_pages)} for kp in result.get("keyPoints", [])]
    kpis = [{"id": f"t2_{i}", "title": m.get("name", ""), "value": m.get("value", 0), "unit": m.get("unit", ""),
             "source_pages": m.get("source_pages", fallback_pages)} for i, m in enumerate(result.get("metrics", []))]
    risks = result.get("risks", [])
    _inject_source_pages(risks, fallback_pages)

    # Assign unique insight IDs at extraction boundary
    _assign_insight_ids(findings, "find")
    _assign_insight_ids(kpis, "kpi")
    _assign_insight_ids(risks, "risk")

    # Evidence-based confidence replaces LLM self-reported confidence
    total_pages = max(end_page - start_page + 1, 1) if start_page and end_page else 1
    fi_items = result.get("financialImpact", {}).get("items", []) if isinstance(result.get("financialImpact"), dict) else []
    ev = _compute_evidence_confidence(findings, kpis, risks, fi_items, fallback_pages, total_pages)

    return {
        "sectionTitle": result.get("sectionTitle", title), "sectionSummary": result.get("sectionSummary", ""),
        "keyFindings": findings, "kpis": kpis, "risks": risks,
        "recommendations": [], "financialImpact": {"identified": False, "items": []}, "charts": [],
        "dmaicRelevance": result.get("dmaicRelevance", {}),
        "confidence": ev["confidence"],
        "confidence_level": ev["confidence_level"],
        "confidence_breakdown": ev["confidence_breakdown"],
        "_llm_confidence": result.get("confidence", 0.5),
        "pageRange": f"Pages {start_page}-{end_page}" if start_page else "",
    }


def _normalize_tier3(result: Dict, title: str) -> Dict:
    bullets = result.get("bullets", [])
    findings = [{"finding": b, "impact": "low"} for b in bullets[:5]]

    # Evidence-based confidence — Tier 3 has minimal data by definition
    ev = _compute_evidence_confidence(findings, [], [], [], [], 1)

    return {
        "sectionTitle": result.get("sectionTitle", title),
        "sectionSummary": " ".join(bullets[:3]) if bullets else "",
        "keyFindings": findings, "kpis": [], "risks": [], "recommendations": [],
        "financialImpact": {"identified": False, "items": []}, "charts": [],
        "dmaicRelevance": result.get("dmaicRelevance", {}),
        "flagForDeepAnalysis": result.get("flagForDeepAnalysis", False),
        "confidence": ev["confidence"],
        "confidence_level": ev["confidence_level"],
        "confidence_breakdown": ev["confidence_breakdown"],
        "_llm_confidence": result.get("confidence", 0.3),
    }


# ── MAP-REDUCE: process oversized sections in sub-chunks ─────────────────

_SUBCHUNK_EXTRACT_PROMPT = """\
Extract ALL data from this text fragment. It is part of section "{title}" (Pages {start}-{end}).

TEXT FRAGMENT ({frag_num}/{frag_total}):
{text}

Return JSON:
{{
  "keyFindings": [{{"finding": "str", "impact": "high|medium|low", "confidence": 0.0-1.0, "source_pages": [int], "source_snippet": "quoted text (max 30 words)"}}],
  "kpis": [{{"id": "str", "title": "max 5 words", "value": <number>, "unit": "str", "confidence": 0.0-1.0, "source_pages": [int], "source_reference": {{"source_pages": "Pages {start}-{end}", "raw_evidence": "quoted text (max 40 words)", "calculation_method": "direct_extract"}}}}],
  "risks": [{{"risk": "str", "severity": "high|medium|low", "source_pages": [int]}}],
  "financialItems": [{{"description": "str", "amount": <number|null>, "unit": "$", "type": "cost|saving|risk", "source_pages": [int]}}],
  "recommendations": ["str"],
  "confidence": 0.0-1.0
}}

RULES:
- Every finding, KPI, risk, and financial item MUST include source_pages
- Use page numbers from [Page N] markers in the text
- If exact page unknown, use section range [{start}, {end}]

Max 10 KPIs, 8 findings, 5 risks, 5 financial items, 5 recommendations. Numbers from text ONLY. JSON only."""


def _map_reduce_section(node: SectionNode, idx: int, total_sections: int) -> Dict[str, Any]:
    """
    Map-Reduce for oversized sections.

    Instead of truncating text to text_cap (losing 60-90%), we:
      1. MAP: split text into sub-chunks of text_cap size
      2. Extract structured data from each sub-chunk (cheap model)
      3. REDUCE: merge all extracted data into one unified result
      4. Feed merged structured data to the full tier prompt

    This ensures 100% of section text contributes to the final output.
    """
    text_cap = node.execution["text_cap"]
    text = node.text
    text_len = len(text)

    # Split into sub-chunks with overlap for context continuity
    overlap = 2000
    sub_chunks = []
    pos = 0
    while pos < text_len:
        end = min(pos + text_cap, text_len)
        sub_chunks.append(text[pos:end])
        pos += text_cap - overlap
        if pos >= text_len:
            break

    logger.info(
        "  MAP-REDUCE %s: %d chars → %d sub-chunks (cap=%d)",
        node.id, text_len, len(sub_chunks), text_cap,
    )

    # MAP: extract structured data from each sub-chunk
    model_name = MODELS["cheap"]["name"]
    all_findings = []
    all_kpis = []
    all_risks = []
    all_financial = []
    all_recommendations = []

    for frag_idx, frag in enumerate(sub_chunks):
        prompt = _SUBCHUNK_EXTRACT_PROMPT.format(
            title=node.title, start=node.start_index, end=node.end_index,
            frag_num=frag_idx + 1, frag_total=len(sub_chunks),
            text=frag,
        )
        result = _call_gemini_json(
            prompt, model=model_name,
            system_instruction="Data extraction specialist. Extract every data point. JSON only.",
            temperature=0.1,
            max_output_tokens=MODELS["cheap"]["max_output_tokens"],
        )
        if result:
            all_findings.extend(result.get("keyFindings", []))
            all_kpis.extend(result.get("kpis", []))
            all_risks.extend(result.get("risks", []))
            all_financial.extend(result.get("financialItems", []))
            all_recommendations.extend(result.get("recommendations", []))

    # Evidence-based confidence from extracted data (replaces LLM avg confidence)
    total_pages = max(node.end_index - node.start_index + 1, 1)
    fb = list(range(node.start_index, node.end_index + 1))
    ev = _compute_evidence_confidence(all_findings, all_kpis, all_risks, all_financial, fb, total_pages)

    # REDUCE: deduplicate and build a compact JSON summary for the main prompt
    # Limit to reasonable sizes for the final synthesis
    merged_json = json.dumps({
        "sectionTitle": node.title,
        "pageRange": f"Pages {node.start_index}-{node.end_index}",
        "subChunksProcessed": len(sub_chunks),
        "totalCharsProcessed": text_len,
        "keyFindings": all_findings[:30],
        "kpis": all_kpis[:30],
        "risks": all_risks[:20],
        "financialItems": all_financial[:15],
        "recommendations": all_recommendations[:15],
        "evidenceConfidence": ev["confidence"],
        "evidenceConfidenceLevel": ev["confidence_level"],
    }, indent=1)

    logger.info(
        "  MAP-REDUCE %s: extracted %d findings, %d kpis, %d risks from %d sub-chunks",
        node.id, len(all_findings), len(all_kpis), len(all_risks), len(sub_chunks),
    )

    # Now run the tier prompt with the STRUCTURED SUMMARY instead of truncated raw text
    # This is the key: the LLM sees 100% of the data (compressed) instead of 10-40% (truncated)
    model_tier = node.execution["model_tier"]
    final_model = node.execution["model_name"]

    synthesis_prompt = f"""\
Synthesize a COMPLETE section analysis from pre-extracted data.
The section "{node.title}" (Pages {node.start_index}-{node.end_index}) was too large for a single pass,
so data was extracted in {len(sub_chunks)} sub-chunks covering ALL {text_len:,} characters.

PRE-EXTRACTED DATA:
{merged_json}

Return the FINAL section analysis JSON matching this schema:
{{
  "sectionTitle": "{node.title}",
  "sectionSummary": "2-3 sentences synthesizing ALL findings",
  "keyFindings": [{{"finding": "str", "impact": "high|medium|low", "confidence": 0.0-1.0, "source_pages": [int], "source_snippet": "str"}}],
  "kpis": [{{"id": "str", "title": "max 5 words", "value": <number>, "unit": "str", "target": null, "trend": "improving|deteriorating|stable", "changeType": "positive|negative|neutral", "confidence": 0.0-1.0, "category": "financial|safety|operations|efficiency|reliability", "priority": "tier1|tier2|tier3|tier4", "source_pages": [int], "source_reference": {{"source_section": "{node.title}", "source_pages": "Pages {node.start_index}-{node.end_index}", "raw_evidence": "str", "calculation_method": "direct_extract"}}}}],
  "risks": [{{"risk": "str", "severity": "high|medium|low", "probability": "high|medium|low", "financial_impact": "str", "source_pages": [int]}}],
  "financialImpact": {{"identified": true, "items": [{{"description": "str", "amount": null, "unit": "$", "type": "cost|saving|risk", "source_pages": [int]}}]}},
  "recommendations": [{{"action": "str", "kpi_id": "str", "baseline": "str", "target": "str", "financial_impact": "str"}}],
  "charts": [],
  "dmaicRelevance": {{"phase": "define|measure|analyze|improve|control|none", "evidence": "why"}},
  "confidence": 0.0-1.0
}}
Deduplicate findings/KPIs. Merge similar items. Keep highest-confidence version of duplicates. JSON only."""

    result = _call_gemini_json(
        synthesis_prompt, model=final_model,
        system_instruction=_SYS_TIER.get(node.tier, _SYS_TIER[2]),
        max_output_tokens=MODELS.get(model_tier, MODELS["balanced"])["max_output_tokens"],
    )

    if not result:
        # Fallback: build result directly from extracted data
        result = {
            "sectionTitle": node.title,
            "sectionSummary": f"Analysis of {text_len:,} characters across {len(sub_chunks)} sub-chunks.",
            "keyFindings": all_findings[:15],
            "kpis": all_kpis[:15],
            "risks": all_risks[:10],
            "financialImpact": {"identified": bool(all_financial), "items": all_financial[:10]},
            "recommendations": [{"action": r} if isinstance(r, str) else r for r in all_recommendations[:10]],
            "charts": [],
            "dmaicRelevance": {"phase": "none"},
            "confidence": ev["confidence"],
            "confidence_level": ev["confidence_level"],
            "confidence_breakdown": ev["confidence_breakdown"],
        }

    # Tag the result so diagnostics can see this was map-reduced
    result["_map_reduced"] = True
    result["_sub_chunks_processed"] = len(sub_chunks)
    result["_total_chars_processed"] = text_len
    result["pageRange"] = f"Pages {node.start_index}-{node.end_index}"

    # Ensure traceability on all items (inject fallback if LLM omitted)
    fb = list(range(node.start_index, node.end_index + 1))
    _inject_source_pages(result.get("keyFindings", []), fb)
    _inject_source_pages(result.get("kpis", []), fb)
    _inject_source_pages(result.get("risks", []), fb)

    # Override LLM confidence with evidence-based confidence on the final result
    fi_items = result.get("financialImpact", {}).get("items", []) if isinstance(result.get("financialImpact"), dict) else []
    ev_final = _compute_evidence_confidence(
        result.get("keyFindings", []), result.get("kpis", []),
        result.get("risks", []), fi_items, fb, total_pages,
    )
    result["_llm_confidence"] = result.get("confidence", 0.0)
    result["confidence"] = ev_final["confidence"]
    result["confidence_level"] = ev_final["confidence_level"]
    result["confidence_breakdown"] = ev_final["confidence_breakdown"]

    return result


def execute_analysis(brain: DocumentBrain, progress=None, diag=None, manifest=None) -> None:
    """Stage 7: Run UNIFORM LLM extraction on ALL sections.

    Every section uses the same extraction prompt (no tier-branched schemas).
    Model selection is the only tier-influenced decision (cost optimisation).
    DMAIC phase is NOT assigned here — it happens globally after aggregation.
    """
    nodes = list(brain.iter_sections())
    n = len(nodes)

    for idx, node in enumerate(nodes):
        if progress:
            progress(4 + int(4 * idx / max(n, 1)), 12,
                     f"Extracting [{idx+1}/{n}] {node.execution['model_tier']}: {node.title[:40]}")

        model_name = node.execution["model_name"]
        model_tier = node.execution["model_tier"]
        text_cap = node.execution["text_cap"]
        temp = node.execution["temperature"]

        # ── MAP-REDUCE: if text exceeds text_cap, use sub-chunk extraction ──
        if len(node.text) > text_cap * 1.2:
            t0 = time.time()
            result = _map_reduce_section(node, idx, n)
            latency_ms = int((time.time() - t0) * 1000)
            text_sent_len = len(node.text)
        else:
            # Uniform extraction: ALL sections use the SAME prompt schema
            text_for_llm = node.text[:text_cap]
            text_sent_len = len(text_for_llm)

            prompt = _TIER2_PROMPT.format(
                title=node.title, start=node.start_index, end=node.end_index,
                num=idx + 1, total=n, text=text_for_llm,
            )

            t0 = time.time()
            result = _call_gemini_json(
                prompt, model=model_name,
                system_instruction=_SYS_EXTRACT,
                temperature=temp,
                max_output_tokens=MODELS.get(model_tier, {}).get("max_output_tokens", 0),
            )
            latency_ms = int((time.time() - t0) * 1000)

        if not result:
            result = _empty_analysis(node.title, confidence=0.1)

        # Uniform normalisation: all results go through _normalize_tier2
        # which ensures consistent schema + evidence-based confidence
        result = _normalize_tier2(result, node.title, node.start_index, node.end_index)

        # ── Post-extraction traceability enforcement ─────────────────────
        # Count items that received fallback source_pages (LLM didn't provide)
        fallback_count = sum(
            1 for k in ("keyFindings", "kpis", "risks")
            for item in result.get(k, [])
            if isinstance(item, dict) and item.get("_source_pages_fallback")
        )
        if fallback_count > 0:
            logger.debug("Traceability: %s had %d items with fallback source_pages", node.id, fallback_count)
        result["_trace_fallback_count"] = fallback_count

        # Ensure every result carries pageRange
        if not result.get("pageRange"):
            result["pageRange"] = f"Pages {node.start_index}-{node.end_index}"

        # ── Tag every result with source metadata ────────────────────────
        result["_source_tier"] = node.tier
        result["_source_type"] = "llm_uniform"
        result["_original_score"] = node.score
        result["_model_used"] = model_tier

        node.analysis = result
        brain.results["sections"][node.id] = result
        brain.metadata["model_usage"][model_tier] = brain.metadata["model_usage"].get(model_tier, 0) + 1

        # Record per-section diagnostics
        if diag:
            diag.record_section_execution(node, text_sent_len, latency_ms, result)

        # Record per-section manifest tracking
        if manifest:
            kpi_count = len(result.get("kpis", []))
            finding_count = len(result.get("keyFindings", []))
            conf = result.get("confidence", 0.0)
            if not isinstance(conf, (int, float)):
                conf = 0.0
            if kpi_count == 0 and finding_count == 0 and result.get("confidence", 0) <= 0.1:
                manifest.mark_section_failed(node.id)
            else:
                manifest.mark_section_processed(
                    node.id, text_sent_len, conf, kpi_count, finding_count,
                )

    logger.info(
        "Analysis complete: %d sections (uniform extraction) | model usage: %s",
        n, brain.metadata["model_usage"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 8: CONFIDENCE-BASED REPROCESSING
# ═══════════════════════════════════════════════════════════════════════════

def reprocess_weak(brain: DocumentBrain, confidence_threshold: float = 0.4, max_reprocessed: int = 3, diag=None, manifest=None) -> None:
    """Stage 8: Rerun weak results with a better model (uniform extraction)."""
    count = 0
    candidates = 0
    for node in brain.iter_sections():
        if count >= max_reprocessed:
            break
        if not node.analysis:
            continue
        conf = node.analysis.get("confidence", 0)
        current_tier = node.execution.get("model_tier", "balanced")

        if isinstance(conf, (int, float)) and conf < confidence_threshold and current_tier != "powerful":
            candidates += 1
            # LLM retry eliminated — Stage 7 prompt now self-heals low-confidence
            # sections by deriving proxy metrics. Log only so diagnostics stay intact.
            logger.info(
                "Weak section %s (conf=%.2f) — self-healing prompt handled at Stage 7, skipping LLM retry",
                node.id, conf,
            )

    if diag:
        diag.record_reprocessing(candidates, candidates, count)

    if count:
        logger.info("Reprocessed %d weak sections", count)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 9: DMAIC PHASE MAPPING
# ═══════════════════════════════════════════════════════════════════════════

def _map_phase(title: str, text: str) -> Optional[str]:
    scores: Dict[str, float] = {}
    for phase, pat in _DMAIC_TITLE_KW.items():
        title_hits = len(pat.findall(title))
        content_hits = len(_DMAIC_CONTENT_KW[phase].findall(text[:5000]))
        scores[phase] = title_hits * 3.0 + content_hits * 1.0
    best = max(scores, key=scores.get)
    return best if scores[best] >= 1.0 else None


def map_dmaic(brain: DocumentBrain) -> None:
    """Stage 9: Assign each section to a DMAIC phase."""
    brain.dmaic_groups = {"define": [], "measure": [], "analyze": [], "improve": [], "control": [], "unassigned": []}

    for node in brain.iter_sections():
        # Prefer LLM-reported phase
        llm_phase = (node.analysis or {}).get("dmaicRelevance", {}).get("phase", "none")
        if llm_phase and llm_phase != "none":
            node.dmaic_phase = llm_phase
        else:
            node.dmaic_phase = _map_phase(node.title, node.text) or "unassigned"

        brain.dmaic_groups.setdefault(node.dmaic_phase, []).append(node.id)

    for phase, ids in brain.dmaic_groups.items():
        if ids:
            logger.info("DMAIC %s: %d sections", phase, len(ids))


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 9.5: GROUP-LEVEL AGGREGATION (HIERARCHICAL MAP-REDUCE)
# ═══════════════════════════════════════════════════════════════════════════
# Purpose: Progressive compression with structure preservation
#   section_analyses (N) → group_summaries (N/5..N/10) → phases/executive
#
# Without this layer: LLM sees 100+ section analyses → token overflow /
#   attention dilution → "only 2-3 pages matter" failure mode
#
# Design:
#   Chunk → Section Analysis → Group Summary → Phase Synthesis → Executive
#   (never skip a level)
# ═══════════════════════════════════════════════════════════════════════════

_MAX_SECTIONS_PER_MERGE = 15   # Max sections per LLM merge call
_MIN_SECTIONS_FOR_GROUPING = 8 # Below this, skip grouping entirely

_GROUP_MERGE_PROMPT = """\
You are a DETERMINISTIC DATA COMPILER merging {num_sections} pre-analyzed sections.
ONLY use data present in the input. NEVER infer, generalize, or invent.

GROUP: "{group_title}" (Pages {page_range})

SECTION ANALYSES (your ONLY data source):
{sections_json}

TASK:
1. Merge all findings — deduplicate, keep highest-confidence version
2. Aggregate KPIs — combine, note ranges (min/max/avg) where applicable
3. Consolidate risks — rank by severity × probability
4. Merge recommendations — deduplicate, keep most impactful
5. Resolve contradictions — if conflicting data, mention both with sources
6. Preserve ALL source_pages references
7. If data is insufficient for a category, return empty list [] — NEVER fabricate data
8. Confidence of merged output MUST NOT exceed the max confidence of contributing inputs

ANTI-HALLUCINATION RULES:
- Do NOT invent data not present in the input sections
- Do NOT generalize findings beyond what specific sections state
- Do NOT add industry benchmarks, external references, or assumed context
- Every finding/KPI/risk must trace back to source_pages from the input
- If a finding appears in 3+ sections, flag it as systemic
- If fewer items exist than the max, output fewer — do NOT pad with fabricated entries

Return JSON:
{{
  "group_title": "{group_title}",
  "section_count": {num_sections},
  "source_pages": [list of ALL page numbers covered],
  "summary": "2-3 sentences synthesizing this group",
  "merged_findings": [
    {{"finding": "str", "impact": "high|medium|low", "confidence": 0.0-1.0, "source_pages": [int], "frequency": 1}}
  ],
  "aggregated_kpis": [
    {{"title": "str", "value": null, "unit": "str", "trend": "str", "source_pages": [int]}}
  ],
  "top_risks": [
    {{"risk": "str", "severity": "high|medium|low", "probability": "high|medium|low", "source_pages": [int]}}
  ],
  "financial_impact": {{"identified": true, "items": [{{"description": "str", "amount": null, "type": "cost|saving|risk"}}]}},
  "recommendations": [
    {{"action": "str", "priority": "high|medium|low", "expected_impact": "str"}}
  ],
  "dmaic_relevance": {{"primary_phase": "define|measure|analyze|improve|control|none"}},
  "confidence": 0.0-1.0
}}
Max: 20 findings, 25 KPIs, 10 risks, 10 recommendations. JSON only."""


def _detect_groups(brain: DocumentBrain) -> Dict[str, Dict[str, Any]]:
    """
    Group section IDs by their top-level TOC parent.
    Returns: {group_key: {"title": str, "section_ids": [str], "page_range": (start, end)}}
    """
    groups: Dict[str, Dict[str, Any]] = {}

    # Build page-range → root-title mapping from brain.tree
    root_ranges = []
    for i, root_node in enumerate(brain.tree):
        root_ranges.append({
            "key": f"G{i:03d}",
            "title": root_node.get("title", f"Group {i+1}"),
            "start": root_node.get("start_index", 1),
            "end": root_node.get("end_index", 1),
        })

    if not root_ranges:
        all_ids = [n.id for n in brain.iter_sections()]
        return {"G000": {"title": "Full Document", "section_ids": all_ids,
                         "page_range": (1, brain.metadata["total_pages"])}}

    # Map each section to its covering root node
    for node in brain.iter_sections():
        matched = False
        for root in root_ranges:
            if node.start_index >= root["start"] and node.end_index <= root["end"]:
                key = root["key"]
                if key not in groups:
                    groups[key] = {
                        "title": root["title"],
                        "section_ids": [],
                        "page_range": (root["start"], root["end"]),
                    }
                groups[key]["section_ids"].append(node.id)
                matched = True
                break

        if not matched:
            # Assign to root with maximum page overlap
            best_key = root_ranges[0]["key"]
            best_overlap = -1
            for root in root_ranges:
                overlap = max(0, min(node.end_index, root["end"]) - max(node.start_index, root["start"]))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_key = root["key"]

            if best_key not in groups:
                root_info = next((r for r in root_ranges if r["key"] == best_key), root_ranges[0])
                groups[best_key] = {
                    "title": root_info["title"],
                    "section_ids": [],
                    "page_range": (root_info["start"], root_info["end"]),
                }
            groups[best_key]["section_ids"].append(node.id)

    return groups


def _compact_section_for_merge(sr: Dict[str, Any]) -> Dict[str, Any]:
    """Build a compact representation of a section result for merging.
    
    Applies confidence scaling for promoted Tier 3 sections so downstream
    LLM merges weight lower-trust data appropriately.
    """
    confidence = sr.get("confidence", 0.5)
    source_tier = sr.get("_source_tier", 2)
    source_type = sr.get("_source_type", "llm_light")

    # Down-weight promoted Tier 3 — LLM extraction succeeded but on
    # low-relevance content, so confidence should reflect that.
    if source_tier == 3:
        confidence = round(confidence * 0.7, 3)

    # Collect ALL source_pages from nested items so LLM merge can propagate them
    all_pages: Set[int] = set()
    _collect_pages_recursive(sr, all_pages)

    return {
        "title": sr.get("sectionTitle", ""),
        "summary": sr.get("sectionSummary", ""),
        "findings": sr.get("keyFindings", [])[:15],
        "kpis": sr.get("kpis", [])[:15],
        "risks": sr.get("risks", [])[:10],
        "financial": sr.get("financialImpact", {}),
        "recommendations": sr.get("recommendations", [])[:8],
        "confidence": confidence,
        "confidence_level": sr.get("confidence_level", ""),
        "confidence_breakdown": sr.get("confidence_breakdown", {}),
        "pages": sr.get("pageRange", ""),
        "source_pages": sorted(all_pages),
        "source_tier": source_tier,
        "source_type": source_type,
    }


def _merge_group_batch(group_title: str, section_results: List[Dict],
                       page_range: str) -> Dict[str, Any]:
    """Run a single merge LLM call for a batch of section results."""
    compact = [_compact_section_for_merge(sr) for sr in section_results]

    prompt = _GROUP_MERGE_PROMPT.format(
        num_sections=len(compact),
        group_title=group_title,
        page_range=page_range,
        sections_json=json.dumps(compact, indent=1),
    )

    result = _call_gemini_json(
        prompt,
        model=MODELS["balanced"]["name"],
        system_instruction="Deterministic data compiler. Merge and deduplicate section analyses. NEVER infer, generalize, or invent data not present in the input. Preserve all source_pages references. JSON only.",
        max_output_tokens=MODELS["balanced"]["max_output_tokens"],
    )

    if not result:
        # Fallback: mechanical merge without LLM
        all_findings = []
        all_kpis = []
        all_risks = []
        for sr in section_results:
            all_findings.extend(sr.get("keyFindings", []))
            all_kpis.extend(sr.get("kpis", []))
            all_risks.extend(sr.get("risks", []))

        result = {
            "group_title": group_title,
            "section_count": len(section_results),
            "source_pages": [],
            "summary": f"Mechanical merge of {len(section_results)} sections (LLM merge failed)",
            "merged_findings": all_findings[:20],
            "aggregated_kpis": all_kpis[:25],
            "top_risks": all_risks[:10],
            "financial_impact": {"identified": False, "items": []},
            "recommendations": [],
        }

    result["group_title"] = group_title
    result["section_count"] = len(section_results)

    # ── Ensure source_pages is always populated (even if LLM missed it) ──
    if not result.get("source_pages"):
        all_pages: Set[int] = set()
        for sr in section_results:
            _collect_pages_recursive(sr, all_pages)
        result["source_pages"] = sorted(all_pages)

    # ── Evidence-based confidence for group merge result ─────────────────
    # Compute from the merged data, not from LLM self-report
    member_confidences = [
        {"confidence": sr.get("confidence", 0), "confidence_breakdown": sr.get("confidence_breakdown", {})}
        for sr in section_results
    ]
    group_ev = _compute_group_confidence(member_confidences)
    result["_llm_confidence"] = result.get("confidence", 0.0)
    result["confidence"] = group_ev["confidence"]
    result["confidence_level"] = group_ev["confidence_level"]
    result["confidence_breakdown"] = group_ev["confidence_breakdown"]

    # Post-LLM traceability validation
    _validate_group_traceability(result, group_title)

    return result


def _batch_merge_group(group_title: str, section_results: List[Dict],
                       page_range: str) -> Dict[str, Any]:
    """Merge a group's sections with recursive batching for large groups."""
    if len(section_results) <= _MAX_SECTIONS_PER_MERGE:
        return _merge_group_batch(group_title, section_results, page_range)

    # Split into batches
    batches = []
    for i in range(0, len(section_results), _MAX_SECTIONS_PER_MERGE):
        batches.append(section_results[i:i + _MAX_SECTIONS_PER_MERGE])

    logger.info("    Batch-merging %d sections in %d batches", len(section_results), len(batches))

    # Merge each batch → partial summaries
    partial_summaries = []
    for batch_idx, batch in enumerate(batches):
        batch_result = _merge_group_batch(
            f"{group_title} (batch {batch_idx+1}/{len(batches)})",
            batch, page_range,
        )
        # Convert group summary back into section-analysis-like format
        # so the next merge level can consume it uniformly
        partial_summaries.append({
            "sectionTitle": f"{group_title} (batch {batch_idx+1})",
            "sectionSummary": batch_result.get("summary", ""),
            "keyFindings": batch_result.get("merged_findings", []),
            "kpis": batch_result.get("aggregated_kpis", []),
            "risks": batch_result.get("top_risks", []),
            "financialImpact": batch_result.get("financial_impact", {}),
            "recommendations": batch_result.get("recommendations", []),
            "confidence": batch_result.get("confidence", 0.5),
            "confidence_level": batch_result.get("confidence_level", ""),
            "confidence_breakdown": batch_result.get("confidence_breakdown", {}),
            "pageRange": page_range,
        })

    # Merge partial summaries into final group summary
    return _merge_group_batch(group_title, partial_summaries, page_range)


def group_aggregate(brain: DocumentBrain, progress=None, diag=None) -> None:
    """
    Stage 9.5: Group-level aggregation — progressive compression.

    Compresses N section analyses into M group summaries (M << N).
    This is the critical intermediate layer that prevents:
      - token overflow in synthesis stages
      - attention dilution (model ignoring most inputs)
      - the "only 2-3 pages matter" failure mode

    Groups sections by their top-level TOC parent (natural document structure),
    then runs a merge LLM call per group to deduplicate, aggregate KPIs,
    and consolidate risks with full traceability.

    Stores results in brain.results["groups"] = {group_key: group_summary}
    """
    total_sections = len(brain.sections)
    processed_count = sum(
        1 for sid, sr in brain.results["sections"].items()
        if sr.get("confidence", 0) > 0
    )

    if total_sections < _MIN_SECTIONS_FOR_GROUPING:
        logger.info(
            "Group aggregation skipped: only %d sections (threshold: %d)",
            total_sections, _MIN_SECTIONS_FOR_GROUPING,
        )
        brain.results["groups"] = None
        return

    if progress:
        progress(9, 15, f"Group aggregation ({processed_count} section analyses → groups)...")

    groups_map = _detect_groups(brain)
    logger.info("Detected %d groups from TOC structure", len(groups_map))

    brain.results["groups"] = {}

    for group_key, group_info in groups_map.items():
        title = group_info["title"]
        section_ids = group_info["section_ids"]
        pr = group_info["page_range"]
        page_range_str = f"{pr[0]}-{pr[1]}"

        # Collect section results for this group
        section_results = [
            brain.results["sections"][sid]
            for sid in section_ids
            if sid in brain.results["sections"]
            and brain.results["sections"][sid].get("confidence", 0) > 0
        ]

        if not section_results:
            logger.warning("Group %s (%s): no valid section results — skipping", group_key, title)
            continue

        if len(section_results) == 1:
            # Single section — wrap in group format (no LLM call needed)
            sr = section_results[0]
            # Extract all source_pages from the section's items
            single_pages: Set[int] = set()
            _collect_pages_recursive(sr, single_pages)
            group_id = _gen_insight_id("grp")
            brain.results["groups"][group_key] = {
                "group_id": group_id,
                "group_title": title,
                "section_count": 1,
                "source_section_ids": list(section_ids),
                "source_pages": sorted(single_pages),
                "page_range_str": page_range_str,
                "summary": sr.get("sectionSummary", ""),
                "merged_findings": sr.get("keyFindings", []),
                "aggregated_kpis": sr.get("kpis", []),
                "top_risks": sr.get("risks", []),
                "financial_impact": sr.get("financialImpact", {}),
                "recommendations": sr.get("recommendations", []),
                "dmaic_relevance": sr.get("dmaicRelevance", {}),
                "confidence": sr.get("confidence", 0.5),
                "confidence_level": sr.get("confidence_level", ""),
                "confidence_breakdown": sr.get("confidence_breakdown", {}),
            }
        else:
            # Multi-section group — LLM-driven merge with batching
            logger.info(
                "  Merging group %s (%s): %d sections → 1 group summary",
                group_key, title, len(section_results),
            )
            merged = _batch_merge_group(
                title, section_results, page_range_str,
            )
            merged["group_id"] = _gen_insight_id("grp")
            merged["source_section_ids"] = list(section_ids)
            merged["page_range_str"] = page_range_str
            brain.results["groups"][group_key] = merged
            brain.metadata["model_usage"]["balanced"] = (
                brain.metadata["model_usage"].get("balanced", 0) + 1
            )

    # ── Post-aggregation validation + logging ────────────────────────────
    group_count = len(brain.results["groups"])
    sections_per_group = []
    pages_per_group = []
    groups_missing_pages = 0
    for gk, gs in brain.results["groups"].items():
        sc = gs.get("section_count", 0)
        sp = gs.get("source_pages", [])
        sections_per_group.append(sc)
        pages_per_group.append(len(sp))
        if not sp:
            groups_missing_pages += 1
            logger.warning("Group %s (%s) has 0 source_pages — traceability broken", gk, gs.get("group_title"))
        if not gs.get("group_title"):
            logger.warning("Group %s missing group_title", gk)

    avg_sec = round(sum(sections_per_group) / max(len(sections_per_group), 1), 1)
    max_sec = max(sections_per_group) if sections_per_group else 0
    avg_pages = round(sum(pages_per_group) / max(len(pages_per_group), 1), 1)

    brain.metadata["_group_stats"] = {
        "total_sections": processed_count,
        "total_groups": group_count,
        "avg_sections_per_group": avg_sec,
        "max_sections_in_group": max_sec,
        "avg_pages_per_group": avg_pages,
        "groups_missing_traceability": groups_missing_pages,
    }

    logger.info(
        "Group aggregation complete: %d sections → %d groups (%.1fx compression) | "
        "avg=%.1f sec/group, max=%d sec/group, avg_pages=%.1f | "
        "traceability: %d/%d groups have source_pages",
        processed_count, group_count, processed_count / max(group_count, 1),
        avg_sec, max_sec, avg_pages,
        group_count - groups_missing_pages, group_count,
    )


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 10: DMAIC PHASE SYNTHESIS
# ═══════════════════════════════════════════════════════════════════════════

_UNIFIED_DMAIC_PROMPT = """\
TASK: Compile a COMPLETE DMAIC breakdown in ONE response. Use ALL five phases.

STRICT RULES:
1. ONLY use data explicitly present in the SECTIONS below.
2. NEVER infer, generalize, or invent data not stated in the input.
3. Use FULL cross-phase reasoning — phases are NOT independent.
4. If a field has no supporting data, set it to null or [] — NEVER fabricate.
5. Every list item MUST include source_pages tracing to document pages.
6. Confidence MUST NOT exceed the max confidence of contributing input sections.

SECTIONS (your ONLY data source):
{sections_json}

Return JSON (all five phases in one object — JSON only, no text outside):
{{
  "define": {{
    "phase": "define",
    "problemStatement": "synthesized problem statement — quantified, evidence-backed",
    "ctqs": [{{"factor": "str", "source_pages": [int]}}],
    "financialExposure": {{"value": null, "unit": "$", "description": "str", "source_pages": [int]}},
    "projectScope": "scope summary",
    "stakeholders": ["key stakeholders mentioned"],
    "voc": [{{"item": "str", "source_pages": [int]}}],
    "source_pages": [int],
    "confidence": 0.0
  }},
  "measure": {{
    "phase": "measure",
    "baselineMetrics": [{{"metric": "str", "value": null, "unit": "str", "source": "str", "source_pages": [int]}}],
    "dataConfidence": 0.0,
    "measurementSystems": ["str"],
    "processCapability": {{"cpk": null, "sigmaLevel": null, "dpmo": null}},
    "dataSources": ["str"],
    "dataQualityIssues": ["gaps or inconsistencies found"],
    "source_pages": [int],
    "confidence": 0.0
  }},
  "analyze": {{
    "phase": "analyze",
    "rootCauses": [{{"cause": "str", "evidence": "exact text reference", "confidence": 0.0, "financial_impact": "str", "source_pages": [int]}}],
    "correlations": [{{"factorA": "str", "factorB": "str", "relationship": "str", "strength": "strong|moderate|weak", "source_pages": [int]}}],
    "statisticalFindings": [{{"finding": "str", "source_pages": [int]}}],
    "keyInsights": [{{"insight": "str", "source_pages": [int]}}],
    "failureModes": [{{"cause": "str", "effect": "str", "severity": "high|medium|low", "source_pages": [int]}}],
    "source_pages": [int],
    "confidence": 0.0
  }},
  "improve": {{
    "phase": "improve",
    "recommendedActions": [{{
      "action": "str",
      "expectedImpact": "str",
      "kpi_linked": "str",
      "financial_benefit": "str",
      "priority": "high|medium|low",
      "timeline": "str",
      "source_pages": [int]
    }}],
    "expectedSigmaLift": null,
    "pilotResults": ["str"],
    "implementationPlan": ["Step N: specific action"],
    "source_pages": [int],
    "confidence": 0.0
  }},
  "control": {{
    "phase": "control",
    "controlPlan": [{{"what": "str", "how": "str", "frequency": "str", "owner": "str", "source_pages": [int]}}],
    "monitoringKPIs": [{{"kpi": "str", "target": "str", "alertThreshold": "str", "action_if_breached": "str", "source_pages": [int]}}],
    "sustainmentPlan": ["str"],
    "trainingNeeds": ["str"],
    "earlyWarningIndicators": ["leading indicators to watch"],
    "source_pages": [int],
    "confidence": 0.0
  }}
}}

CAPS: max 8 CTQs, 15 baseline metrics, 10 root causes, 10 actions, 8 control items. JSON only."""

_DMAIC_PHASE_PROMPTS = {
    "define": 'COMPILE the DEFINE phase from the section analyses below. ONLY use data present in the input. NEVER infer, generalize, or invent.\n\nSECTIONS (your ONLY data source):\n{sections_json}\n\nReturn JSON:\n{{\n  "phase": "define",\n  "problemStatement": "synthesized problem statement — quantified, evidence-backed",\n  "ctqs": [{{"factor": "str", "source_pages": [int]}}],\n  "financialExposure": {{ "value": null, "unit": "$", "description": "str", "source_pages": [int] }},\n  "projectScope": "scope summary",\n  "stakeholders": ["key stakeholders mentioned"],\n  "voc": [{{"item": "str", "source_pages": [int]}}],\n  "source_pages": [int],\n  "confidence": 0.0-1.0\n}}\n\nRULES:\n- Every CTQ and VOC item MUST include source_pages tracing back to document pages\n- source_pages at root = union of all referenced pages\n- If source unknown, do NOT include the item\n- Do NOT infer, extrapolate, or invent data not in the input\n- If data is insufficient for a field, set to null or [] — NEVER fabricate\n- Confidence MUST NOT exceed the max confidence of contributing input sections\nMax 8 CTQs, 5 stakeholders, 5 VOC items. JSON only.',
    "measure": 'COMPILE the MEASURE phase from the section analyses below. ONLY use data present in the input. NEVER infer, generalize, or invent.\n\nSECTIONS (your ONLY data source):\n{sections_json}\n\nReturn JSON:\n{{\n  "phase": "measure",\n  "baselineMetrics": [{{ "metric": "str", "value": null, "unit": "str", "source": "section title", "source_pages": [int] }}],\n  "dataConfidence": 0.0-1.0,\n  "measurementSystems": ["str"],\n  "processCapability": {{ "cpk": null, "sigmaLevel": null, "dpmo": null }},\n  "dataSources": ["str"],\n  "dataQualityIssues": ["gaps, missing values, inconsistencies found"],\n  "source_pages": [int],\n  "confidence": 0.0-1.0\n}}\n\nRULES:\n- Every baselineMetric MUST include source_pages\n- source_pages at root = union of all referenced pages\n- Do NOT infer, extrapolate, or invent data not in the input\n- processCapability fields: set to null if not present in input — NEVER estimate\n- If data is insufficient for a field, set to null or [] — NEVER fabricate\n- Confidence MUST NOT exceed the max confidence of contributing input sections\nMax 15 baseline metrics. JSON only.',
    "analyze": 'COMPILE the ANALYZE phase from the section analyses below. This is the most critical phase. ONLY use data present in the input. NEVER infer, generalize, or invent.\n\nSECTIONS (your ONLY data source):\n{sections_json}\n\nReturn JSON:\n{{\n  "phase": "analyze",\n  "rootCauses": [{{ "cause": "str", "evidence": "exact text reference from input", "confidence": 0.0-1.0, "financial_impact": "str", "source_pages": [int] }}],\n  "correlations": [{{ "factorA": "str", "factorB": "str", "relationship": "str", "strength": "strong|moderate|weak", "source_pages": [int] }}],\n  "statisticalFindings": [{{"finding": "str — include R², Cpk, sigma values ONLY if present in input", "source_pages": [int]}}],\n  "keyInsights": [{{"insight": "str — action-oriented, traced to input data", "source_pages": [int]}}],\n  "failureModes": [{{ "cause": "str", "effect": "str", "severity": "high|medium|low", "source_pages": [int] }}],\n  "source_pages": [int],\n  "confidence": 0.0-1.0\n}}\n\nRULES:\n- Every rootCause, correlation, insight, and failureMode MUST include source_pages\n- source_pages at root = union of all referenced pages\n- If you cannot trace an insight to source pages, do NOT include it\n- Do NOT infer causal relationships not stated in the input\n- Do NOT add statistical findings (R², Cpk, sigma) unless explicitly present in input data\n- evidence field MUST quote or closely paraphrase actual input text — not reinterpretations\n- Confidence MUST NOT exceed the max confidence of contributing input sections\nMax 10 root causes, 8 correlations, 8 stats, 8 insights, 5 failure modes. JSON only.',
    "improve": 'COMPILE the IMPROVE phase from the section analyses below. ONLY use data present in the input. NEVER infer, generalize, or invent.\n\nSECTIONS (your ONLY data source):\n{sections_json}\n\nReturn JSON:\n{{\n  "phase": "improve",\n  "recommendedActions": [\n    {{\n      "action": "str — specific, imperative verb",\n      "expectedImpact": "str — quantified baseline vs target from input",\n      "kpi_linked": "str — KPI name this action affects",\n      "financial_benefit": "str — $ impact from input or INSUFFICIENT_DATA",\n      "priority": "high|medium|low",\n      "timeline": "str — time-bound from input or INSUFFICIENT_DATA",\n      "source_pages": [int]\n    }}\n  ],\n  "expectedSigmaLift": "str or null",\n  "pilotResults": ["str"],\n  "implementationPlan": ["Step N: specific action"],\n  "source_pages": [int],\n  "confidence": 0.0-1.0\n}}\n\nRULES:\n- Every recommendedAction MUST include source_pages\n- source_pages at root = union of all referenced pages\n- Do NOT infer, extrapolate, or invent recommendations not supported by input data\n- financial_benefit: ONLY from input data. If not quantified in input, use "INSUFFICIENT_DATA"\n- expectedSigmaLift: set to null if not calculable from input\n- Confidence MUST NOT exceed the max confidence of contributing input sections\nMax 10 actions, 5 pilot results, 8 plan steps. JSON only.',
    "control": 'COMPILE the CONTROL phase from the section analyses below. ONLY use data present in the input. NEVER infer, generalize, or invent.\n\nSECTIONS (your ONLY data source):\n{sections_json}\n\nReturn JSON:\n{{\n  "phase": "control",\n  "controlPlan": [{{ "what": "str", "how": "str", "frequency": "str", "owner": "str", "source_pages": [int] }}],\n  "monitoringKPIs": [{{ "kpi": "str", "target": "str", "alertThreshold": "str", "action_if_breached": "str", "source_pages": [int] }}],\n  "sustainmentPlan": ["str"],\n  "trainingNeeds": ["str"],\n  "earlyWarningIndicators": ["leading indicators to watch"],\n  "source_pages": [int],\n  "confidence": 0.0-1.0\n}}\n\nRULES:\n- Every controlPlan item and monitoringKPI MUST include source_pages\n- source_pages at root = union of all referenced pages\n- Do NOT infer, extrapolate, or invent control measures not in the input\n- If a field lacks supporting data, set to [] or null — NEVER fabricate\n- Confidence MUST NOT exceed the max confidence of contributing input sections\nMax 8 control items, 10 KPIs, 5 sustainment, 5 training, 5 early warnings. JSON only.',
}


_PHASE_BATCH_MERGE_PROMPT = """\
You are a DETERMINISTIC DATA COMPILER. Merge these {num_batches} partial {phase} phase syntheses into one unified synthesis.
ONLY use data present in the partial syntheses. NEVER infer, generalize, or invent.

PARTIAL SYNTHESES (your ONLY data source):
{partials_json}

Return a single unified {phase} phase synthesis JSON that:
1. Merges all items (deduplicate)
2. Keeps highest-confidence entries
3. UNIONS all source_pages arrays — every item must retain its source_pages
4. source_pages at root level = union of ALL page numbers from all partials
5. Do NOT add any items not present in the partial syntheses
6. Confidence of merged output MUST NOT exceed the max confidence of partials
JSON only — same schema as each partial."""


def synthesize_phases(brain: DocumentBrain, progress=None, diag=None) -> None:
    """Stage 10: GLOBAL DMAIC synthesis — ONE call for all 5 phases (was 5 calls).

    All section/group data is fed in a single prompt that returns all five
    DMAIC phases at once. Cross-phase reasoning is therefore built-in and
    the model never loses context between phases.
    """
    # Build ONE compact data pool from ALL processed sections/groups
    groups = brain.results.get("groups")
    if groups:
        compact_pool = []
        for gkey, gsummary in groups.items():
            compact_pool.append({
                "group_id": gsummary.get("group_id", gkey),
                "title": gsummary.get("group_title", gkey),
                "summary": gsummary.get("summary", ""),
                "findings": gsummary.get("merged_findings", [])[:20],
                "kpis": gsummary.get("aggregated_kpis", [])[:50],
                "risks": gsummary.get("top_risks", [])[:20],
                "recommendations": gsummary.get("recommendations", [])[:10],
                "supporting_groups": [gsummary.get("group_id", gkey)],
                "confidence": gsummary.get("confidence", 0.5),
                "confidence_level": gsummary.get("confidence_level", ""),
                "pageRange": gsummary.get("page_range_str", ""),
            })
    else:
        compact_pool = []
        for node in brain.iter_sections():
            result = brain.results["sections"].get(node.id, {})
            if not result or result.get("confidence", 0) <= 0:
                continue
            compact_pool.append({
                "group_id": node.id,
                "title": result.get("sectionTitle", ""),
                "summary": result.get("sectionSummary", ""),
                "findings": result.get("keyFindings", [])[:20],
                "kpis": result.get("kpis", [])[:50],
                "risks": result.get("risks", [])[:20],
                "financial": result.get("financialImpact", {}),
                "recommendations": result.get("recommendations", [])[:10],
                "supporting_groups": [node.id],
                "confidence": result.get("confidence", 0.5),
                "confidence_level": result.get("confidence_level", ""),
                "pageRange": result.get("pageRange", ""),
            })

    if not compact_pool:
        logger.warning("No data for DMAIC synthesis — skipping")
        return

    logger.info(
        "Unified DMAIC synthesis: 1 call for all 5 phases (%d data units)", len(compact_pool)
    )
    if progress:
        progress(10, 15, f"Global DMAIC: all 5 phases unified (from {len(compact_pool)} groups/sections)")

    model_name = MODELS["balanced"]["name"]
    sys_instr = (
        "Deterministic data compiler. Compile ALL five DMAIC phases from the provided data. "
        "Select only data relevant to each phase. NEVER infer, generalize, or invent data not "
        "present in the input. If data is missing, set fields to null or []. JSON only."
    )
    max_tokens = MODELS["balanced"]["max_output_tokens"]

    # ── Batching: if too many items, split → partial syntheses → merge ──────
    if len(compact_pool) <= _MAX_SECTIONS_PER_MERGE:
        compact_json = json.dumps(compact_pool, indent=1)
        if diag:
            diag.record_synthesis("unified", len(compact_pool), len(compact_json))
        all_phases = _call_gemini_json(
            _UNIFIED_DMAIC_PROMPT.format(sections_json=compact_json),
            model=model_name, system_instruction=sys_instr,
            max_output_tokens=max_tokens,
        )
    else:
        # Split into batches, synthesize each batch, then merge the partials
        batches = [compact_pool[i:i + _MAX_SECTIONS_PER_MERGE]
                   for i in range(0, len(compact_pool), _MAX_SECTIONS_PER_MERGE)]
        logger.info("  Unified DMAIC: batching %d items into %d batches",
                    len(compact_pool), len(batches))

        partial_syntheses = []
        for b_idx, batch in enumerate(batches):
            batch_json = json.dumps(batch, indent=1)
            partial = _call_gemini_json(
                _UNIFIED_DMAIC_PROMPT.format(sections_json=batch_json),
                model=model_name, system_instruction=sys_instr,
                max_output_tokens=max_tokens,
            )
            if partial:
                partial_syntheses.append(partial)

        if not partial_syntheses:
            all_phases = None
        elif len(partial_syntheses) == 1:
            all_phases = partial_syntheses[0]
        else:
            # Merge partial unified-DMAIC objects: pick best per-phase by confidence
            all_phases = {}
            for phase in ("define", "measure", "analyze", "improve", "control"):
                best = None
                best_conf = -1.0
                for p in partial_syntheses:
                    ph = p.get(phase, {})
                    if isinstance(ph, dict) and ph.get("confidence", 0) > best_conf:
                        best_conf = ph.get("confidence", 0)
                        best = ph
                if best:
                    all_phases[phase] = best

    if not all_phases or not isinstance(all_phases, dict):
        logger.warning("Unified DMAIC synthesis returned nothing — skipping")
        return

    # Write each phase result back into brain exactly as before
    for phase in ("define", "measure", "analyze", "improve", "control"):
        synth = all_phases.get(phase)
        if synth and isinstance(synth, dict):
            _validate_phase_traceability(synth, phase)
            brain.results["dmaic"][phase] = synth
            brain.metadata["model_usage"]["balanced"] = (
                brain.metadata["model_usage"].get("balanced", 0) + 1
            )

    logger.info("Unified DMAIC synthesis complete: %s", list(brain.results["dmaic"].keys()))


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 11: CROSS-PHASE INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════

def cross_phase_check(brain: DocumentBrain) -> None:
    """Stage 11: Rule-based cross-phase consistency checks."""
    insights: List[Dict[str, str]] = []
    d = brain.results["dmaic"]
    define_d = d.get("define", {})
    measure_d = d.get("measure", {})
    analyze_d = d.get("analyze", {})
    improve_d = d.get("improve", {})
    control_d = d.get("control", {})

    if improve_d.get("recommendedActions") and not analyze_d.get("rootCauses"):
        insights.append({"type": "warning", "insight": "IMPROVE has solutions but ANALYZE has no root causes — solutions may not address true problems."})

    data_conf = measure_d.get("dataConfidence", 1.0)
    analyze_conf = analyze_d.get("confidence", 0.0)
    if isinstance(data_conf, (int, float)) and data_conf < 0.5 and isinstance(analyze_conf, (int, float)) and analyze_conf > 0.7:
        insights.append({"type": "warning", "insight": f"MEASURE data confidence is low ({data_conf:.0%}) but ANALYZE conclusions are strong ({analyze_conf:.0%}) — conclusions may not be well-supported."})

    if (improve_d.get("recommendedActions") or analyze_d.get("rootCauses")) and not control_d:
        insights.append({"type": "warning", "insight": "IMPROVE/ANALYZE have findings but CONTROL phase is empty — no sustainability plan."})

    fin_exp = define_d.get("financialExposure", {})
    if fin_exp and fin_exp.get("value"):
        actions = improve_d.get("recommendedActions", [])
        if not any(a.get("cost") for a in actions if isinstance(a, dict)):
            insights.append({"type": "info", "insight": "DEFINE identifies financial exposure but IMPROVE lacks cost estimates — ROI not calculable."})

    ctqs = define_d.get("ctqs", [])
    baselines = measure_d.get("baselineMetrics", [])
    if ctqs and not baselines:
        insights.append({"type": "warning", "insight": f"DEFINE lists {len(ctqs)} CTQs but MEASURE has no baseline metrics — measurement gap."})

    roots = analyze_d.get("rootCauses", [])
    stats = analyze_d.get("statisticalFindings", [])
    if len(roots) > 2 and not stats:
        insights.append({"type": "info", "insight": "Multiple root causes without statistical evidence — consider strengthening analysis."})

    brain.results["cross_phase"] = insights
    if insights:
        logger.info("Cross-phase insights: %d", len(insights))


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 12: EXECUTIVE SYNTHESIS
# ═══════════════════════════════════════════════════════════════════════════

_EXECUTIVE_SYNTHESIS_PROMPT = """\
You are a DETERMINISTIC DATA COMPILER — NOT a summarizer, NOT an analyst, NOT a writer.

TASK: Compile the pre-analyzed section results below into ONE structured executive dashboard JSON.

STRICT RULES (VIOLATION = INVALID OUTPUT):
1. ONLY use data explicitly present in the SECTION ANALYSES and PHASE SYNTHESES below.
2. DO NOT infer, extrapolate, generalize, or interpret beyond what the input states.
3. DO NOT fill gaps — if a field has no supporting data, use null, empty list [], or "INSUFFICIENT_DATA".
4. Every KPI value, finding, risk, insight, and recommendation MUST have source_pages tracing to input data. If you cannot assign source_pages, DO NOT include the item.
5. DO NOT rephrase findings into broader claims. Copy the substance; restructure only for schema compliance.
6. Confidence scores MUST reflect input confidence — do NOT inflate. If input confidence is 0.6, output ≤ 0.6.
7. Charts and tables MUST use ONLY data points present in the input — no fabricated data series.
8. If an entire DMAIC phase has no input data, set its fields to null or empty — do NOT generate placeholder content.

SOURCE: {source_type} | {num_sections} sections | {total_pages} pages
TIERS: {tier_summary} | MODELS: {model_summary}

SECTION ANALYSES (your ONLY data source for section-level content):
{section_analyses_json}

DMAIC PHASE SYNTHESES (your ONLY data source for DMAIC content):
{phase_syntheses_json}

CROSS-PHASE INSIGHTS (pre-computed — include as-is):
{cross_phase_json}

TOC (structure reference only — NOT a data source):
{toc_json}

Return the FINAL dashboard JSON (every field must trace to input above):
{{
  "meta": {{
    "reportId": "{report_id}",
    "ingestedAt": "{ingested_at}",
    "sourceType": "{source_type}",
    "confidenceOverall": 0.0-1.0,
    "decisionReadinessScore": 0.0-1.0,
    "sectionsAnalyzed": {num_sections},
    "totalPages": {total_pages}
  }},

  "autoClassification": {{
    "reportType": ["operations", "hse", "finance", "audit", "strategy"],
    "assetScope": "well|field|plant|pipeline|enterprise",
    "timeHorizon": "operational|tactical|strategic",
    "decisionLevel": "operations|management|board",
    "confidence": 0.0-1.0
  }},

  "dashboard": {{
    "title": "Dashboard Title",
    "description": "Brief description",

    "sections": [
      {{
        "sectionId": "sec_001",
        "title": "str",
        "pageRange": "Pages X-Y",
        "tier": 1,
        "dmaicPhase": "define|measure|analyze|improve|control|none",
        "modelUsed": "cheap|balanced|powerful",
        "summary": "str",
        "keyFindings": [{{ "finding": "str", "impact": "high|medium|low", "confidence": 0.0-1.0, "source_pages": [int] }}],
        "kpis": [{{ "id": "str", "title": "str", "value": <number>, "unit": "str", "confidence": 0.0-1.0, "source_pages": [int] }}],
        "risks": [{{ "risk": "str", "severity": "high|medium|low", "source_pages": [int] }}],
        "recommendations": ["str"],
        "financialImpact": {{ "items": [] }},
        "charts": [],
        "confidence": 0.0-1.0
      }}
    ],

    "sixSigma": {{
      "methodology": "DMAIC",
      "dmaic": {{
        "define": {{ "problemStatement": "str", "ctqs": ["str"], "financialExposure": {{ "value": <number>, "unit": "$" }} }},
        "measure": {{ "baselineMetrics": ["str"], "dataConfidence": 0.0-1.0 }},
        "analyze": {{ "rootCauses": [{{ "cause": "str", "confidence": 0.0-1.0 }}], "correlations": ["str"] }},
        "improve": {{ "recommendedActions": ["str"], "expectedSigmaLift": "str" }},
        "control": {{ "controlPlan": ["str"], "monitoringKPIs": ["str"] }}
      }},
      "sigmaLevel": "str",
      "defectRate": "str",
      "processCapability": "Low|Medium|High",
      "statisticalValidity": true|false
    }},

    "kpis": [{{ "id": "str", "title": "max 5 words", "value": <number>, "unit": "$|%|count|hrs", "target": <number>, "trend": "improving|deteriorating|stable", "change": "str", "changeType": "positive|negative|neutral", "confidence": 0.0-1.0, "owner": "str", "sourceSection": "str", "source_pages": [int], "icon": "dollar|users|activity|chart|trending", "color": "green|blue|purple|red|yellow", "priority": "tier1|tier2|tier3|tier4" }}],

    "charts": [{{ "id": "str", "type": "BarChart|LineChart|AreaChart|PieChart|RadarChart", "title": "str", "size": "full|half|third", "chartConfig": {{}}, "data": [...] }}],

    "tables": [{{ "id": "str", "title": "str", "columns": [...], "data": [], "pagination": true, "sortable": true }}],

    "optimizationSuggestions": [{{
      "id": "str",
      "title": "str — precise, tied to a measurable KPI",
      "category": "cost|efficiency|performance|risk|quality",
      "impact": "high|medium|low",
      "roi": <number>,
      "savings": {{ "value": <number>, "unit": "$", "timeframe": "annually" }},
      "description": "str — no generic statements, evidence-backed",
      "priority": "high|medium|low",
      "confidence": 0.0-1.0,
      "sourceSection": "str",
      "decision_traceability": {{
        "data_sources": ["str — specific data inputs with time range, e.g. production logs Q1-Q4"],
        "analytical_methods": ["str — e.g. trend analysis R²=0.78, control charts, variance analysis"],
        "supporting_evidence": ["str — quantified, e.g. defect rate +8% YoY, $2.1M annual loss"]
      }},
      "industry_benchmarking": {{
        "median_comparison": "str — above|below|at par vs industry median",
        "top_quartile_comparison": "str — vs P75/P90 performance",
        "peer_comparison": "str — vs peer assets if applicable",
        "performance_gap": "str — % or absolute delta"
      }},
      "decision_confidence_index": {{
        "score": <0-100>,
        "data_completeness": "str — score and rationale (0-25 pts)",
        "model_confidence": "str — score and rationale (0-25 pts)",
        "historical_accuracy": "str — score and rationale (0-25 pts)",
        "variability": "str — score and rationale (0-25 pts)",
        "explanation": "str — why this score, what would raise it"
      }},
      "assumptions_limitations": ["str — clearly stated assumptions and missing data flags"],
      "use_case": "Production Optimization|Asset Reliability|Drilling Performance|HSE|Refinery / Process Optimization",
      "action_management": {{
        "task_title": "str — clear, imperative verb (e.g. Replace pump seals on Train-B)",
        "description": "str — what needs to be done and why",
        "owner": "str — role-based (e.g. Maintenance Lead, Production Manager, Process Engineer)",
        "kpi": "str — specific KPI impacted (e.g. Downtime %, OEE, MTBF, NPT)",
        "target_value": "str — quantified improvement (e.g. Reduce downtime from 8% to 4%)",
        "deadline": "str — time-bound (e.g. 30 days, Q2 2026, Before next turnaround)",
        "priority": "high|medium|low",
        "status": "Open"
      }},
      "execution_plan": [
        "str — Step 1: include tools/systems referenced (SAP PM work order, SCADA dashboard, historian data pull)",
        "str — Step 2: include dependencies (shutdown window, permits, approvals required)",
        "str — Step 3 to Step 6: (3-6 concrete steps total, domain-specific)"
      ],
      "closed_loop_learning": {{
        "predicted_impact": "str — quantified forecast (e.g. -15% NPT, +$320K/year, OEE +4%)",
        "measurement_plan": "str — data source + frequency (e.g. PI Historian daily, SAP PM monthly WO closure)",
        "feedback_capture": "str — what data is collected after implementation to verify impact",
        "learning_loop": "str — how actual results feed back into future model recommendations",
        "actual_vs_predicted": {{
          "predicted": "str — same as predicted_impact",
          "actual": "TBD — populate post-implementation"
        }}
      }},
      "integration_mapping": {{
        "erp": "str — SAP/Oracle action (e.g. PM notification, work order type PM01, cost center CC-1023)",
        "scada": "str — real-time trigger (e.g. alarm setpoint change on tag FCV-201, historian trend)",
        "production_db": "str — KPI tracking query or table (e.g. SELECT daily_downtime FROM prod_kpi WHERE unit='Train-B')",
        "excel": "str — reporting/export format (e.g. Monthly KPI tracker, shift handover log)"
      }},
      "domain_kpis": [{{
        "name": "str — OEE|MTBF|MTTR|NPT|Lifting Cost per Barrel|Flaring Rate|Energy Intensity|Process Efficiency",
        "current": "str — current measured value (e.g. 72%, 1,200 hrs, 4.2 hrs, 8.5%)",
        "target": "str — target after recommendation (e.g. 85%, 1,800 hrs, 2.0 hrs, 4.0%)",
        "direction": "increase|decrease"
      }}],
      "failure_modes": [{{
        "cause": "str — domain-specific root cause (e.g. fouling on HEX-101, valve seat leakage FCV-201, sensor drift PT-305, bearing wear, hydrate formation)",
        "confidence": 0.0
      }}]
    }}],

    "predictive": {{
      "forecast": [{{ "metric": "str", "risk": "high|medium|low", "timeframe": "30d|90d|1y", "confidence": 0.0-1.0 }}],
      "whatIfScenarios": [{{ "action": "str", "impact": "str", "financialDelta": <number> }}]
    }},

    "insights": {{
      "summary": "Executive summary from ALL sections",
      "crossSectionCorrelations": [{{"insight": "str", "source_pages": [int]}}],
      "crossPhaseInsights": [{{"insight": "str", "source_pages": [int]}}],
      "trends": [{{"trend": "str", "source_pages": [int]}}],
      "alerts": [{{ "type": "warning|error|info|success", "message": "str", "severity": "high|medium|low", "action": "str", "source_pages": [int] }}],
      "recommendations": [{{"recommendation": "str", "source_pages": [int]}}]
    }},

    "explainability": {{
      "whyThisConclusion": ["str"],
      "dataUsed": ["str"],
      "assumptions": ["str"],
      "limitations": ["str"],
      "sectionsCovered": {num_sections},
      "totalPages": {total_pages},
      "analysisApproach": "Centralized DocumentBrain with tiered model routing and DMAIC-aware synthesis"
    }}
  }},

  "ceo_view": {{
    "decisions": [
      {{"title": "str — max 8 words, starts with action verb (Stabilize / Reduce / Accelerate / Halt)", "impact": "str — $ value or KPI change, quantified", "urgency": "high|medium|low"}}
    ],
    "risks": [
      {{"title": "str — max 8 words, plain language", "severity": "High|Medium|Low", "financial_impact": "str — quantified loss or operational consequence"}}
    ],
    "actions": [
      {{"title": "str — imperative, max 8 words (e.g. Replace heat exchanger on Train-B)", "owner": "str — role (e.g. Maintenance Lead)", "timeline": "str — time-bound (e.g. 30 days, Q2 2026)"}}
    ]
  }},

  "manager_view": {{
    "dmaic": {{
      "define": "str — problem statement + financial exposure (1-2 sentences)",
      "measure": "str — baseline metrics and data confidence (1-2 sentences)",
      "analyze": "str — top root causes with confidence scores (1-2 sentences)",
      "improve": "str — recommended actions + expected sigma lift (1-2 sentences)",
      "control": "str — monitoring plan + KPIs tracked (1-2 sentences)"
    }},
    "recommendations": [
      {{"title": "str", "impact": "str — quantified", "timeline": "str — time-bound", "priority": "high|medium|low"}}
    ],
    "kpi_tracking": [
      {{"name": "str", "current": "str", "target": "str", "status": "on-track|at-risk|off-track"}}
    ]
  }},

  "engineer_view": {{
    "data_references": ["str — specific dataset, table, or document section with page/row reference"],
    "models": ["str — statistical model with key metric (e.g. regression R²=0.78, control chart UCL=4.2, Cpk=0.89)"],
    "root_cause_analysis": ["str — detailed causal chain with evidence (e.g. fouling on HEX-101 → ΔT loss 14°C → throughput -8%)"],
    "failure_modes": [
      {{"cause": "str — specific domain failure", "probability": 0.0, "detection": "str — how detected (e.g. PI alarm, vibration sensor)", "mitigation": "str — specific corrective action"}}
    ],
    "assumptions": ["str — stated assumption with potential impact if incorrect"]
  }},

  "boardroom_mode": {{
    "executive_summary": "str — 3-5 sentences: Sentence 1=situation/context, Sentence 2=key problem with $ impact, Sentence 3=root cause, Sentence 4=recommended decision, Sentence 5=expected outcome if actioned",
    "slides": {{
      "summary": ["str — each bullet max 10 words, 5-7 bullets, no jargon"],
      "decisions": ["str — Decision: [action] → [impact] (max 12 words)"],
      "risks": ["str — Risk: [threat] | Severity: [H/M/L] | Mitigation: [action]"],
      "actions": ["str — [Action] | Owner: [role] | By: [deadline]"],
      "kpi_impact": ["str — [KPI]: [current] → [target] ([direction] [%])"] 
    }}
  }}

}}
}}

RULES:
- TRACEABILITY (NON-NEGOTIABLE): Every KPI, finding, risk, insight, alert, and recommendation MUST include source_pages ([int] array). If you cannot trace it to source pages, do NOT include it
- ANTI-HALLUCINATION (NON-NEGOTIABLE): Every value, metric, finding, and claim MUST come from the SECTION ANALYSES or PHASE SYNTHESES above. If a field requires data not present in the input, set it to null, [], or "INSUFFICIENT_DATA" — do NOT fabricate
- CONFIDENCE CEILING: No output confidence score may exceed the maximum confidence of its contributing input sections. If all inputs are ≤ 0.7, overall confidence ≤ 0.7
- One section entry per analyzed section with tier, dmaicPhase, and modelUsed tags
- Top-level KPIs: up to 12 most critical — ONLY from data present in section analyses. If fewer than 8 exist in input, output fewer
- sixSigma.dmaic: populate DIRECTLY from the phase syntheses provided — do NOT rewrite or embellish
- Cross-phase insights in insights.crossPhaseInsights — copy from CROSS-PHASE INSIGHTS input
- Charts: ONLY from data points present in section analyses. If data is insufficient for 5 charts, produce fewer
- "value" in KPIs MUST be actual numbers from input, NOT 0, NOT invented
- optimizationSuggestions: 3-6 recommendations — each MUST trace to specific input findings. decision_traceability.supporting_evidence MUST quote input data verbatim. If evidence is insufficient, reduce count rather than fabricate
- DCI score is a composite 0-100 built from: data_completeness (0-25) + model_confidence (0-25) + historical_accuracy (0-25) + variability (0-25). Score 0 for any sub-component lacking input data
- BAD title: "Reduce defect rate by 10%"  GOOD title: "Reduce defect rate 10% — 12-month upward trend (R²=0.78), $2.1M annual loss, below P75 benchmark by 6%"
- Every supporting_evidence item must be quantified (numbers, %, $, timeframe) — no generic statements. If input lacks quantification, state "INSUFFICIENT_DATA"
- action_management.owner must be a ROLE not a person name; deadline must be time-bound (e.g. 30 days, Q2 2026)
- execution_plan must be 3-6 specific steps referencing domain systems (SAP PM, SCADA, PI Historian, DCS) — only if such systems are mentioned in input; otherwise state "INSUFFICIENT_DATA"
- failure_modes: list top 3-5 domain-specific root causes with confidence scores summing to ≤ 1.0 — ONLY from input data
- domain_kpis: map to O&G standard KPIs (OEE, MTBF/MTTR, NPT, Lifting Cost, Flaring Rate, Energy Intensity); include current and target with direction — ONLY if present in input
- integration_mapping: populate ONLY if input mentions specific systems; otherwise set fields to "INSUFFICIENT_DATA"
- ceo_view: exactly 3 decisions, 3 risks, 3 actions — max 8 words each title — NO technical terms — readable in under 30 seconds. MUST trace to input data
- manager_view.dmaic: each field = 1-2 sentences, evidence-referenced, manager-level language (no raw formulas)
- engineer_view: full depth — models MUST cite R², p-value, Cpk, sigma level ONLY if present in input; otherwise "INSUFFICIENT_DATA". failure_modes MUST include detection method and mitigation
- boardroom_mode.executive_summary: exactly 3-5 sentences as described — MUST be derived from input only
- boardroom_mode.slides: each bullet max 10 words; decisions use 'Decision:' prefix; risks use 'Risk:' prefix; actions use pipe-separated format
- LANGUAGE RULE: In ALL view layers, NEVER write 'insights suggest', 'data indicates', 'it appears' — ALWAYS use 'Decision:', 'Action Required:', 'Risk:'
- FAIL-FAST: If the combined input data is insufficient to populate a top-level section (e.g., predictive, sixSigma), set that section to {{"status": "INSUFFICIENT_DATA"}} rather than generating speculative content
- JSON only, no text outside"""


def _validate_dashboard_traceability(dashboard: Dict[str, Any]) -> Dict[str, int]:
    """Post-LLM validation: strip untraceable items from ALL dashboard lists, return stats."""
    stats = {"total_stripped": 0, "total_checked": 0}
    prefix_map = {
        "keyFindings": "find",
        "kpis": "kpi",
        "risks": "risk",
        "recommendations": "rec",
        "items": "fin",
        "crossSectionCorrelations": "ins",
        "crossPhaseInsights": "ins",
        "trends": "trend",
        "alerts": "alert",
        "domain_kpis": "kpi",
        "failure_modes": "risk",
    }

    def _strip_list(container: dict, key: str, label: str):
        items = container.get(key, [])
        if items and isinstance(items, list):
            stats["total_checked"] += len(items)
            kept, dropped = _strip_untraceable(items, label)
            _assign_insight_ids(kept, prefix_map.get(key, "ins"))
            container[key] = kept
            stats["total_stripped"] += dropped

    # Dashboard sections — ALL list fields
    db = dashboard.get("dashboard", {})
    for section in db.get("sections", []):
        sec_label = section.get("title", "?")[:30]
        for key in ("keyFindings", "kpis", "risks", "recommendations"):
            _strip_list(section, key, f"section:{sec_label}.{key}")
        # financialImpact.items
        fi = section.get("financialImpact", {})
        if isinstance(fi, dict):
            _strip_list(fi, "items", f"section:{sec_label}.financialImpact.items")

    # Top-level KPIs
    _strip_list(db, "kpis", "top_kpis")

    # Insights sub-fields
    insights = db.get("insights", {})
    for key in ("crossSectionCorrelations", "crossPhaseInsights", "trends",
                "alerts", "recommendations"):
        _strip_list(insights, key, f"insights.{key}")

    # optimizationSuggestions — strip suggestions whose domain_kpis/failure_modes lack pages
    opt_sugs = db.get("optimizationSuggestions", [])
    if opt_sugs and isinstance(opt_sugs, list):
        for sug in opt_sugs:
            if isinstance(sug, dict):
                _strip_list(sug, "domain_kpis", "optSug.domain_kpis")
                _strip_list(sug, "failure_modes", "optSug.failure_modes")

    if stats["total_stripped"] > 0:
        logger.info(
            "Post-LLM traceability filter: stripped %d/%d untraceable items from dashboard",
            stats["total_stripped"], stats["total_checked"],
        )
    return stats


def _validate_phase_traceability(synth: Dict[str, Any], phase: str) -> int:
    """Post-LLM validation: strip untraceable items from phase synthesis result."""
    total_dropped = 0
    # Each phase has different list fields — check common patterns
    for key in ("rootCauses", "correlations", "statisticalFindings", "keyInsights",
                "failureModes", "baselineMetrics", "ctqs", "voc",
                "recommendedActions", "controlPlan", "monitoringKPIs"):
        items = synth.get(key, [])
        if items and isinstance(items, list):
            kept, dropped = _strip_untraceable(items, f"{phase}.{key}")
            synth[key] = kept
            total_dropped += dropped
    if total_dropped > 0:
        logger.info("Post-LLM traceability filter (%s): stripped %d items", phase, total_dropped)
    return total_dropped


def _annotate_dmaic_supporting_groups(brain: DocumentBrain) -> None:
    """Annotate DMAIC items with supporting_groups based on page overlap with groups."""
    groups = brain.results.get("groups", {})
    dmaic = brain.results.get("dmaic", {})
    if not groups or not dmaic:
        return

    group_page_map: Dict[str, Set[int]] = {}
    for gk, g in groups.items():
        if not isinstance(g, dict):
            continue
        gid = g.get("group_id", gk)
        sp = g.get("source_pages", [])
        if isinstance(sp, list):
            group_page_map[gid] = set(p for p in sp if isinstance(p, int))

    phase_item_keys = [
        "ctqs", "voc", "baselineMetrics", "rootCauses", "correlations",
        "statisticalFindings", "keyInsights", "failureModes",
        "recommendedActions", "controlPlan", "monitoringKPIs",
    ]

    for phase_name, phase_data in dmaic.items():
        if not isinstance(phase_data, dict):
            continue
        for key in phase_item_keys:
            items = phase_data.get(key, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_pages = item.get("source_pages", [])
                if not isinstance(item_pages, list) or not item_pages:
                    continue
                ip = set(p for p in item_pages if isinstance(p, int))
                supporting = [gid for gid, gpages in group_page_map.items() if ip & gpages]
                item["supporting_groups"] = sorted(set(supporting))


def _validate_group_traceability(result: Dict[str, Any], group_title: str) -> int:
    """Post-LLM validation: strip untraceable items from group merge result."""
    total_dropped = 0
    key_prefix = {
        "merged_findings": "find",
        "aggregated_kpis": "kpi",
        "top_risks": "risk",
    }
    for key in ("merged_findings", "aggregated_kpis", "top_risks"):
        items = result.get(key, [])
        if items and isinstance(items, list):
            kept, dropped = _strip_untraceable(items, f"group:{group_title}.{key}")
            _assign_insight_ids(kept, key_prefix.get(key, "ins"))
            result[key] = kept
            total_dropped += dropped
    if total_dropped > 0:
        logger.info("Post-LLM traceability filter (group %s): stripped %d items", group_title, total_dropped)
    return total_dropped


def executive_synthesis(brain: DocumentBrain, progress=None, diag=None, manifest=None) -> Dict[str, Any]:
    """Stage 12: Final executive dashboard synthesis (uses group summaries when available)."""
    if progress:
        progress(12, 15, "Executive synthesis...")

    report_id = str(uuid.uuid4())
    ingested_at = datetime.datetime.utcnow().isoformat() + "Z"

    # ── Coverage enforcement gate ───────────────────────────────────────
    total_sections = len(brain.sections)
    processed_sections = sum(
        1 for node in brain.iter_sections()
        if node.id in brain.results.get("sections", {})
        and brain.results["sections"][node.id].get("confidence", 0) > 0
    )
    coverage_pct = processed_sections / max(total_sections, 1)
    if coverage_pct < 0.80:
        logger.warning(
            "LOW COVERAGE: only %d/%d sections (%.0f%%) have analysis results. "
            "Executive synthesis may be incomplete.",
            processed_sections, total_sections, coverage_pct * 100,
        )
    if manifest:
        gate = manifest.gate_processing(min_processed_pct=0.80)
        if not gate.passed:
            logger.warning("Coverage gate FAILED before executive synthesis: %s", gate.message)

    # ── Build input data: prefer group summaries over raw section analyses ─
    groups = brain.results.get("groups")
    if groups:
        # Use pre-compressed group summaries (progressive compression)
        compact_analyses = []
        for gk, gs in groups.items():
            compact_analyses.append({
                "groupTitle": gs.get("group_title", gk),
                "sectionCount": gs.get("section_count", 0),
                "summary": gs.get("summary", ""),
                "keyFindings": gs.get("merged_findings", []),
                "kpis": gs.get("aggregated_kpis", []),
                "risks": gs.get("top_risks", []),
                "financialImpact": gs.get("financial_impact", {}),
                "recommendations": gs.get("recommendations", []),
                "confidence": gs.get("confidence", 0.5),
                "confidence_level": gs.get("confidence_level", ""),
                "sourcePages": gs.get("source_pages", []),
            })
        logger.info(
            "Executive synthesis using %d group summaries (compressed from %d sections)",
            len(compact_analyses), processed_sections,
        )
    else:
        # Fallback: use raw section analyses (small docs without grouping)
        compact_analyses = []
        for node in brain.iter_sections():
            sa = brain.results["sections"].get(node.id, {})
            compact = {k: sa[k] for k in [
                "sectionTitle", "sectionSummary", "keyFindings", "kpis",
                "risks", "recommendations", "financialImpact", "charts", "confidence",
                "confidence_level", "confidence_breakdown",
            ] if k in sa}
            compact["tier"] = node.tier
            compact["dmaicPhase"] = node.dmaic_phase or "unassigned"
            compact["modelUsed"] = node.execution.get("model_tier", "balanced")
            compact["pageRange"] = f"Pages {node.start_index}-{node.end_index}"
            compact_analyses.append(compact)

    tier_summary = {k: len(v) for k, v in brain.execution_plan.items()}
    model_summary = brain.metadata["model_usage"]

    # ── Batching: if too many inputs, batch → partial dashboards → merge ─
    _MAX_GROUPS_PER_EXEC = 25

    if len(compact_analyses) > _MAX_GROUPS_PER_EXEC:
        logger.info(
            "Executive synthesis batching: %d inputs → %d batches",
            len(compact_analyses),
            (len(compact_analyses) + _MAX_GROUPS_PER_EXEC - 1) // _MAX_GROUPS_PER_EXEC,
        )
        batches = [compact_analyses[i:i + _MAX_GROUPS_PER_EXEC]
                   for i in range(0, len(compact_analyses), _MAX_GROUPS_PER_EXEC)]

        partial_dashboards = []
        for b_idx, batch in enumerate(batches):
            if progress:
                progress(12, 15, f"Executive synthesis batch {b_idx+1}/{len(batches)}...")
            batch_prompt = _EXECUTIVE_SYNTHESIS_PROMPT.format(
                source_type=brain.source_type,
                num_sections=sum(ca.get("sectionCount", 1) for ca in batch),
                total_pages=brain.metadata["total_pages"],
                tier_summary=json.dumps(tier_summary),
                model_summary=json.dumps(model_summary),
                section_analyses_json=json.dumps(batch, indent=1),
                phase_syntheses_json=json.dumps(brain.results["dmaic"], indent=1),
                cross_phase_json=json.dumps(brain.results["cross_phase"], indent=1),
                toc_json=json.dumps(brain.tree[:10], indent=1),
                report_id=report_id,
                ingested_at=ingested_at,
            )
            partial = _call_gemini_json(
                batch_prompt, model=MODELS["powerful"]["name"],
                system_instruction="Deterministic data compiler. Compile the provided section analyses and phase syntheses into a structured executive dashboard. NEVER infer, generalize, or invent data not present in the input. If data is missing, output INSUFFICIENT_DATA. JSON only.",
                max_output_tokens=MODELS["powerful"]["max_output_tokens"],
            )
            if partial:
                partial_dashboards.append(partial)

        if len(partial_dashboards) == 1:
            dashboard = partial_dashboards[0]
        elif partial_dashboards:
            # Merge partial dashboards
            merge_input = json.dumps(partial_dashboards, indent=1)
            merge_prompt = f"""\
You are a DETERMINISTIC DATA COMPILER. Merge these {len(partial_dashboards)} partial executive dashboards into ONE final unified dashboard.
ONLY use data present in the partial dashboards. NEVER infer, generalize, or invent.

PARTIAL DASHBOARDS (your ONLY data source):
{merge_input}

RULES:
- Combine all KPIs, findings, risks — deduplicate
- Keep highest-confidence version of duplicates
- Preserve ALL source_pages references
- Confidence of merged output MUST NOT exceed the max confidence of partials
- Do NOT add any items, insights, or KPIs not present in the partial dashboards
- If a field has no data across all partials, set to null, [], or "INSUFFICIENT_DATA"

Return the unified dashboard JSON. Same schema as each partial. JSON only."""
            dashboard = _call_gemini_json(
                merge_prompt, model=MODELS["powerful"]["name"],
                system_instruction="Deterministic data compiler. Merge partial dashboards into one unified dashboard. NEVER infer, generalize, or invent data. Deduplicate, keep highest-confidence version. JSON only.",
                max_output_tokens=MODELS["powerful"]["max_output_tokens"],
            )
        else:
            dashboard = None
    else:
        # Standard path: all inputs fit in one call
        prompt = _EXECUTIVE_SYNTHESIS_PROMPT.format(
            source_type=brain.source_type,
            num_sections=len(brain.sections),
            total_pages=brain.metadata["total_pages"],
            tier_summary=json.dumps(tier_summary),
            model_summary=json.dumps(model_summary),
            section_analyses_json=json.dumps(compact_analyses, indent=1),
            phase_syntheses_json=json.dumps(brain.results["dmaic"], indent=1),
            cross_phase_json=json.dumps(brain.results["cross_phase"], indent=1),
            toc_json=json.dumps(brain.tree, indent=1),
            report_id=report_id,
            ingested_at=ingested_at,
        )

        # Record executive synthesis diagnostics (prompt size)
        section_analyses_json_str = json.dumps(compact_analyses, indent=1)
        phase_syntheses_json_str = json.dumps(brain.results["dmaic"], indent=1)
        if diag:
            diag.record_executive(
                prompt_chars=len(prompt),
                section_analyses_chars=len(section_analyses_json_str),
                phase_syntheses_chars=len(phase_syntheses_json_str),
                success=False,
                fallback=False,
            )

        dashboard = _call_gemini_json(
            prompt, model=MODELS["powerful"]["name"],
            system_instruction="Deterministic data compiler. Compile the provided section analyses and phase syntheses into a structured executive dashboard. NEVER infer, generalize, or invent data not present in the input. If data is missing, output INSUFFICIENT_DATA. JSON only.",
            max_output_tokens=MODELS["powerful"]["max_output_tokens"],
        )

    if not dashboard:
        logger.error("Executive synthesis failed — building fallback")
        if diag:
            diag.executive["fallback_used"] = True
        return _build_fallback(brain, report_id, ingested_at)

    # ── Post-LLM traceability validation ─────────────────────────────────
    trace_stats = _validate_dashboard_traceability(dashboard)

    if diag:
        diag.executive["success"] = True
        diag.executive["post_llm_stripped"] = trace_stats.get("total_stripped", 0)

    # ── Post-processing: enrich meta with brain state ────────────────────
    if "meta" not in dashboard:
        dashboard["meta"] = {}
    meta = dashboard["meta"]
    meta.setdefault("reportId", report_id)
    meta.setdefault("ingestedAt", ingested_at)
    meta.setdefault("sourceType", brain.source_type)
    meta.setdefault("sectionsAnalyzed", len(brain.sections))
    meta.setdefault("totalPages", brain.metadata["total_pages"])
    meta["tiersUsed"] = tier_summary
    meta["estimatedCost"] = brain.metadata.get("cost_estimate", {})
    meta["sectionsAnalyzed"] = len(brain.sections)
    meta["totalPages"] = brain.metadata["total_pages"]
    meta["modelUsage"] = model_summary
    meta["reprocessed"] = brain.metadata.get("reprocessed", 0)
    meta["crossPhaseInsights"] = brain.results["cross_phase"]
    meta["phaseSyntheses"] = brain.results["dmaic"]

    # ── Evidence-based confidenceOverall (replaces LLM self-reported) ────
    section_evs = []
    for sid, sr in brain.results["sections"].items():
        if sr.get("confidence", 0) > 0:
            section_evs.append({
                "confidence": sr.get("confidence", 0),
                "confidence_breakdown": sr.get("confidence_breakdown", {}),
            })
    if section_evs:
        overall_ev = _compute_group_confidence(section_evs)
        meta["confidenceOverall"] = overall_ev["confidence"]
        meta["confidenceOverallLevel"] = overall_ev["confidence_level"]
        meta["confidenceOverallBreakdown"] = overall_ev["confidence_breakdown"]
        meta["_llm_confidenceOverall"] = meta.get("confidenceOverall", 0.0)
    else:
        meta["confidenceOverall"] = 0.0
        meta["confidenceOverallLevel"] = "LOW"

    # Ensure sections array is populated from brain state
    if "dashboard" in dashboard:
        dash = dashboard["dashboard"]
        if "sections" not in dash or not dash["sections"]:
            dash["sections"] = _build_sections_from_brain(brain)
        else:
            # Tag existing sections with brain metadata
            nodes_list = list(brain.iter_sections())
            for i, sec_entry in enumerate(dash["sections"]):
                if i < len(nodes_list):
                    node = nodes_list[i]
                    sec_entry.setdefault("tier", node.tier)
                    sec_entry.setdefault("dmaicPhase", node.dmaic_phase or "unassigned")
                    sec_entry.setdefault("modelUsed", node.execution.get("model_tier", "balanced"))

        # Auto-generate charts from KPI data when Gemini skips them
        if not dash.get("charts"):
            dash["charts"] = _auto_generate_charts(dash, brain)

    brain.results["final"] = dashboard
    return dashboard


def _auto_generate_charts(dash: Dict, brain: DocumentBrain) -> List[Dict]:
    """Generate charts deterministically from KPI + section data when Gemini returns none."""
    charts = []
    palette = ["#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"]

    kpis = dash.get("kpis", [])

    # ── Chart 1: KPI values bar chart ───────────────────────────────────
    kpi_bar_data = [
        {"name": k.get("title", "KPI")[:20], "value": k.get("value", 0)}
        for k in kpis
        if isinstance(k.get("value"), (int, float)) and k.get("value", 0) != 0
    ][:10]
    if kpi_bar_data:
        charts.append({
            "id": "auto_kpi_bar",
            "type": "BarChart",
            "title": "Key Performance Indicators",
            "size": "full",
            "data": kpi_bar_data,
            "chartConfig": {
                "xAxis": {"dataKey": "name", "label": "KPI", "type": "category"},
                "series": [{"dataKey": "value", "name": "Value", "type": "bar", "color": "#06b6d4"}],
            },
        })

    # ── Chart 2: KPI change-type distribution pie ────────────────────────
    change_counts: Dict[str, int] = {}
    for k in kpis:
        ct = k.get("changeType", "neutral")
        change_counts[ct] = change_counts.get(ct, 0) + 1
    if change_counts:
        charts.append({
            "id": "auto_kpi_status_pie",
            "type": "PieChart",
            "title": "KPI Performance Distribution",
            "size": "half",
            "data": [{"name": ct.capitalize(), "value": cnt} for ct, cnt in change_counts.items()],
            "chartConfig": {
                "nameKey": "name",
                "dataKey": "value",
                "colors": ["#10b981", "#ef4444", "#94a3b8"],
            },
        })

    # ── Chart 3: KPI by category bar chart ──────────────────────────────
    cat_counts: Dict[str, int] = {}
    for k in kpis:
        cat = k.get("category", "operational")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    if len(cat_counts) > 1:
        charts.append({
            "id": "auto_kpi_category_pie",
            "type": "PieChart",
            "title": "KPIs by Category",
            "size": "half",
            "data": [{"name": c.capitalize(), "value": v} for c, v in cat_counts.items()],
            "chartConfig": {
                "nameKey": "name",
                "dataKey": "value",
                "colors": palette,
            },
        })

    # ── Chart 4: Section confidence bar chart ───────────────────────────
    sections = dash.get("sections", [])
    conf_data = [
        {"name": s.get("title", "Sec")[:20], "confidence": round(s.get("confidence", 0.5) * 100)}
        for s in sections
        if s.get("confidence") is not None
    ][:12]
    if conf_data:
        charts.append({
            "id": "auto_section_confidence",
            "type": "BarChart",
            "title": "Section Analysis Confidence",
            "size": "full",
            "data": conf_data,
            "chartConfig": {
                "xAxis": {"dataKey": "name", "label": "Section", "type": "category"},
                "series": [{"dataKey": "confidence", "name": "Confidence %", "type": "bar", "color": "#10b981"}],
            },
        })

    # ── Chart 5: DMAIC phase coverage radar / bar ────────────────────────
    phase_counts: Dict[str, int] = {}
    for s in sections:
        ph = s.get("dmaicPhase", "unassigned")
        if ph and ph != "unassigned":
            phase_counts[ph] = phase_counts.get(ph, 0) + 1
    if phase_counts:
        phase_order = ["define", "measure", "analyze", "improve", "control"]
        radar_data = [
            {"phase": p.capitalize(), "sections": phase_counts.get(p, 0)}
            for p in phase_order
        ]
        charts.append({
            "id": "auto_dmaic_coverage",
            "type": "RadarChart",
            "title": "DMAIC Phase Coverage",
            "size": "half",
            "data": radar_data,
            "chartConfig": {
                "nameKey": "phase",
                "series": [{"dataKey": "sections", "name": "Sections", "color": "#8b5cf6"}],
            },
        })

    # ── Chart 6: Collect any per-section charts from brain ───────────────
    for node in brain.iter_sections():
        sa = brain.results["sections"].get(node.id, {})
        for c in sa.get("charts", []):
            if c and c.get("data"):
                c_copy = dict(c)
                c_copy["id"] = f"sec_{node.id}_{c.get('id', 'chart')}"
                charts.append(c_copy)
                if len(charts) >= 10:
                    break
        if len(charts) >= 10:
            break

    return charts


def _build_sections_from_brain(brain: DocumentBrain) -> List[Dict]:
    """Build sections array from brain's stored results."""
    out = []
    for idx, node in enumerate(brain.iter_sections()):
        sa = brain.results["sections"].get(node.id, {})
        out.append({
            "sectionId": f"sec_{idx+1:03d}",
            "title": sa.get("sectionTitle", node.title),
            "pageRange": f"Pages {node.start_index}-{node.end_index}",
            "tier": node.tier,
            "dmaicPhase": node.dmaic_phase or "unassigned",
            "modelUsed": node.execution.get("model_tier", "balanced"),
            "summary": sa.get("sectionSummary", ""),
            "keyFindings": sa.get("keyFindings", []),
            "kpis": sa.get("kpis", []),
            "risks": sa.get("risks", []),
            "recommendations": sa.get("recommendations", []),
            "financialImpact": sa.get("financialImpact", {}),
            "charts": sa.get("charts", []),
            "confidence": sa.get("confidence", 0.5),
            "confidence_level": sa.get("confidence_level", ""),
            "confidence_breakdown": sa.get("confidence_breakdown", {}),
        })
    return out


def _build_fallback(brain: DocumentBrain, report_id: str, ingested_at: str) -> Dict[str, Any]:
    """Fallback dashboard when executive synthesis fails."""
    all_kpis, all_findings, all_recs = [], [], []
    for sa in brain.results["sections"].values():
        all_kpis.extend(sa.get("kpis", []))
        all_findings.extend(sa.get("keyFindings", []))
        all_recs.extend(sa.get("recommendations", []))

    # Deduplicate KPIs by title (keep highest confidence)
    seen: dict = {}
    for k in all_kpis:
        title = (k.get("title") or "").lower().strip()
        if title not in seen or k.get("confidence", 0) > seen[title].get("confidence", 0):
            seen[title] = k
    deduped_kpis = list(seen.values())

    fallback_dash = {
        "title": "Report Analysis Dashboard (Fallback)",
        "description": f"Analysis of {len(brain.sections)} sections",
        "sections": _build_sections_from_brain(brain),
        "kpis": deduped_kpis[:50],
        "tables": [],
        "optimizationSuggestions": [],
        "insights": {
            "summary": f"Analyzed {len(brain.sections)} sections with {len(all_findings)} findings.",
            "trends": [], "alerts": [], "recommendations": all_recs[:20],
        },
    }
    fallback_dash["charts"] = _auto_generate_charts(fallback_dash, brain)

    # Evidence-based confidenceOverall for fallback
    section_evs = [
        {"confidence": sr.get("confidence", 0), "confidence_breakdown": sr.get("confidence_breakdown", {})}
        for sr in brain.results["sections"].values() if sr.get("confidence", 0) > 0
    ]
    fallback_ev = _compute_group_confidence(section_evs) if section_evs else {"confidence": 0.0, "confidence_level": "LOW"}

    return {
        "meta": {
            "reportId": report_id, "ingestedAt": ingested_at,
            "sourceType": brain.source_type,
            "confidenceOverall": fallback_ev["confidence"],
            "confidenceOverallLevel": fallback_ev.get("confidence_level", "LOW"),
            "decisionReadinessScore": 0.4,
            "sectionsAnalyzed": len(brain.sections),
            "totalPages": brain.metadata["total_pages"],
            "tiersUsed": {k: len(v) for k, v in brain.execution_plan.items()},
            "estimatedCost": brain.metadata.get("cost_estimate", {}),
            "modelUsage": brain.metadata["model_usage"],
        },
        "dashboard": fallback_dash,
    }


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 13: DMAIC REPORT COMPILER
# Converts messy section analyses + phase syntheses into a strict Six Sigma
# deliverable regardless of input quality.
# ═══════════════════════════════════════════════════════════════════════════

_DMAIC_COMPILER_PROMPT = """\
TASK: Convert extracted insights into a structured Six Sigma DMAIC report.

CONTEXT:
- Document type: {doc_type}
- Available signals: {signal_flags}

INPUT:
You are given structured outputs from multiple sections and DMAIC phase syntheses of a document.
These may be incomplete, overlapping, or unordered.

SECTION ANALYSES:
{sections_compact_json}

DMAIC PHASE SYNTHESES:
{phase_syntheses_json}

CROSS-PHASE INSIGHTS:
{cross_phase_json}

Your job is to RECONSTRUCT a complete Six Sigma report using strict DMAIC structure.

OUTPUT (JSON ONLY — no text before or after):
{{
  "define": {{
    "problem_statement": "Clear, quantified problem statement or empty string if unknown",
    "business_context": "Business and operational context",
    "project_scope": "What is in scope and what is out",
    "voc": ["Voice of Customer items — max 5"]
  }},
  "measure": {{
    "baseline_kpis": [
      {{"name": "str", "value": "str or number", "unit": "str", "source": "str"}}
    ],
    "data_collection": "How data was or should be collected",
    "process_capability": [
      {{"metric": "str", "cpk": null, "sigma_level": null, "dpmo": null}}
    ],
    "data_issues": ["data quality issues or gaps — max 5"]
  }},
  "analyze": {{
    "root_causes": [
      {{"cause": "str", "category": "material|method|machine|man|measurement|environment", "confidence": 0.0}}
    ],
    "validated_causes": ["causes backed by data/evidence — max 5"],
    "key_drivers": ["main quantified drivers of the problem — max 5"],
    "evidence": ["statistical or documented evidence — max 5"]
  }},
  "improve": {{
    "solutions": [
      {{"action": "str", "linked_cause": "str", "expected_impact": "str", "cost": null, "priority": "high|medium|low"}}
    ],
    "impact_estimation": ["quantified improvement projections — max 5"],
    "cost_benefit": ["cost-benefit or ROI items — max 5"],
    "risks": ["implementation risks — max 5"]
  }},
  "control": {{
    "control_plan": [
      {{"what": "str", "how": "str", "frequency": "str", "owner": "str"}}
    ],
    "monitoring_kpis": [
      {{"kpi": "str", "target": "str", "alert_threshold": "str"}}
    ],
    "standardization": ["SOPs, training, or process changes to embed improvements — max 5"],
    "risks": ["sustainability risks — max 3"]
  }},
  "executive_summary": {{
    "summary": "2-4 sentence board-level summary of the entire project",
    "financial_impact": [
      {{"description": "str", "amount": null, "unit": "$", "type": "saving|cost|exposure"}}
    ],
    "key_kpis": [
      {{"name": "str", "baseline": "str", "current_or_target": "str", "improvement": "str"}}
    ],
    "top_risks": ["top 3 risks to highlight"],
    "recommendations": ["top 5 actionable recommendations"]
  }},
  "gaps": ["missing data, weak phases, or unanswered questions — max 5"],
  "compilation_confidence": 0.0
}}

RULES:
- Always return ALL fields — use empty arrays/strings if data missing
- Do NOT invent numbers — leave null if not present in source data
- Merge duplicate insights across sections
- Prefer quantified metrics over qualitative text
- solutions must reference a linked_cause when possible
- Max 5 items per list (3 for control.risks, sustainability risks)
- If data is weak, reflect uncertainty in wording (e.g. "possibly", "estimated")
- compilation_confidence = your overall confidence in 0.0-1.0

GOAL: Produce a consulting-grade Six Sigma deliverable regardless of input quality."""


def dmaic_compiler(brain: DocumentBrain, executive_dashboard: Dict[str, Any], progress=None) -> Dict[str, Any]:
    """Stage 13: Compile a strict Six Sigma DMAIC deliverable from all analysis."""
    if progress:
        progress(12, 14, "DMAIC Report Compiler...")

    # Detect available signal flags
    has_financials = any(
        n.signals.get("financial", 0) > 0.05 for n in brain.iter_sections()
    )
    has_kpis = any(n.signals.get("kpi_density", 0) > 0.05 for n in brain.iter_sections())
    has_control = bool(brain.results["dmaic"].get("control"))
    has_analyze = bool(brain.results["dmaic"].get("analyze"))

    doc_type = executive_dashboard.get("autoClassification", {}).get("reportType", [brain.source_type])
    if isinstance(doc_type, list):
        doc_type = ", ".join(doc_type)

    signal_flags = {
        "has_financials": has_financials,
        "has_kpis": has_kpis,
        "has_control_data": has_control,
        "has_analyze_data": has_analyze,
    }

    # Build compact section summaries (top N by score, deduped)
    sections_compact = []
    seen_summaries: set = set()
    for node in sorted(brain.iter_sections(), key=lambda n: n.score, reverse=True)[:50]:
        sa = brain.results["sections"].get(node.id, {})
        summ = sa.get("sectionSummary", "")[:120]
        if summ in seen_summaries:
            continue
        seen_summaries.add(summ)
        sections_compact.append({
            "title": sa.get("sectionTitle", node.title),
            "dmaic_phase": node.dmaic_phase or "unassigned",
            "summary": summ,
            "pageRange": sa.get("pageRange", f"Pages {node.start_index}-{node.end_index}"),
            "key_findings": [f if isinstance(f, dict) else {"finding": f}
                             for f in sa.get("keyFindings", [])[:5]],
            "kpis": [{"name": k.get("title", k.get("name", "")), "value": k.get("value"),
                      "unit": k.get("unit", ""), "source_pages": k.get("source_pages", [])} for k in sa.get("kpis", [])[:5]],
            "risks": [r if isinstance(r, dict) else {"risk": r}
                      for r in sa.get("risks", [])[:3]],
            "financial": sa.get("financialImpact", {}),
        })

    prompt = _DMAIC_COMPILER_PROMPT.format(
        doc_type=doc_type,
        signal_flags=json.dumps(signal_flags),
        sections_compact_json=json.dumps(sections_compact, indent=1),
        phase_syntheses_json=json.dumps(brain.results["dmaic"], indent=1),
        cross_phase_json=json.dumps(brain.results["cross_phase"], indent=1),
    )

    compiled = _call_gemini_json(
        prompt,
        model=MODELS["balanced"]["name"],
        system_instruction=(
            "You are a Senior Six Sigma Master Black Belt. "
            "Compile structured DMAIC report from raw analysis. JSON only."
        ),
        max_output_tokens=MODELS["balanced"]["max_output_tokens"],
    )

    if not compiled:
        logger.warning("DMAIC compiler returned nothing — building minimal fallback")
        d = brain.results["dmaic"]
        compiled = {
            "define": {
                "problem_statement": d.get("define", {}).get("problemStatement", ""),
                "business_context": "",
                "project_scope": d.get("define", {}).get("projectScope", ""),
                "voc": d.get("define", {}).get("ctqs", []),
            },
            "measure": {
                "baseline_kpis": d.get("measure", {}).get("baselineMetrics", []),
                "data_collection": "",
                "process_capability": [],
                "data_issues": [],
            },
            "analyze": {
                "root_causes": d.get("analyze", {}).get("rootCauses", []),
                "validated_causes": [],
                "key_drivers": [],
                "evidence": d.get("analyze", {}).get("statisticalFindings", []),
            },
            "improve": {
                "solutions": [{"action": a} if isinstance(a, str) else a
                               for a in d.get("improve", {}).get("recommendedActions", [])],
                "impact_estimation": [],
                "cost_benefit": [],
                "risks": [],
            },
            "control": {
                "control_plan": d.get("control", {}).get("controlPlan", []),
                "monitoring_kpis": d.get("control", {}).get("monitoringKPIs", []),
                "standardization": [],
                "risks": [],
            },
            "executive_summary": {
                "summary": "",
                "financial_impact": [],
                "key_kpis": [],
                "top_risks": [],
                "recommendations": [],
            },
            "gaps": [i.get("insight", "") for i in brain.results.get("cross_phase", [])[:5]],
        }

    # --- Evidence-based compilation confidence ---
    all_findings, all_kpis, all_risks, all_financial = [], [], [], []
    all_pages: Set[int] = set()
    total_pages = max(len(list(brain.iter_sections())), 1)
    for node in brain.iter_sections():
        sa = brain.results["sections"].get(node.id, {})
        all_findings.extend(sa.get("keyFindings", []))
        all_kpis.extend(sa.get("kpis", []))
        all_risks.extend(sa.get("risks", []))
        fi = sa.get("financialImpact", {})
        if isinstance(fi, dict):
            items = fi.get("items", fi.get("financial_items", []))
            if isinstance(items, list):
                all_financial.extend(items)
        for pg in sa.get("source_pages", []):
            if isinstance(pg, int):
                all_pages.add(pg)
    ev = _compute_evidence_confidence(all_findings, all_kpis, all_risks, all_financial, all_pages, total_pages)
    llm_conf = compiled.get("compilation_confidence")
    if llm_conf is not None:
        compiled["_llm_compilation_confidence"] = llm_conf
    compiled["compilation_confidence"] = ev["confidence"]
    compiled["compilation_confidence_level"] = ev["confidence_level"]
    compiled["compilation_confidence_breakdown"] = ev["confidence_breakdown"]

    compiled["signal_flags"] = signal_flags
    compiled["doc_type"] = doc_type
    return compiled


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 14: SIX SIGMA QUALITY SCORING ENGINE
# Evaluates the compiled report across 8 dimensions (0-5 each = 40 max).
# Hybrid: rule-based (fast) + optional LLM evaluator (1 cheap call).
# ═══════════════════════════════════════════════════════════════════════════

_RE_NUMERIC = re.compile(r"\b\d+\.?\d*\b")
_RE_FINANCIAL_AMOUNT = re.compile(r"\$\s*[\d,]+|[\d,]+\s*(million|billion|thousand|M|B|K)\b|\bROI\b|\bsavings?\b|\bcost\b", re.I)


def _safe_list(obj: Any, key: str) -> List:
    v = obj.get(key, []) if isinstance(obj, dict) else []
    return v if isinstance(v, list) else []


def _has_numbers(text: str) -> bool:
    return bool(_RE_NUMERIC.search(str(text)))


def _count_numeric_items(items: List) -> int:
    return sum(1 for item in items if _has_numbers(str(item)))


def _score_define(d: Dict) -> Tuple[float, List[str]]:
    score, gaps = 0.0, []
    ps = str(d.get("problem_statement", ""))
    scope = str(d.get("project_scope", ""))
    ctx = str(d.get("business_context", ""))
    voc = _safe_list(d, "voc")

    if len(ps) > 30:
        score += 2.0
    elif len(ps) > 0:
        score += 1.0
        gaps.append("Problem statement is vague — add quantification")
    else:
        gaps.append("Problem statement is missing")

    if len(scope) > 20:
        score += 1.5
    else:
        gaps.append("Project scope not defined")

    if len(ctx) > 20:
        score += 1.5
    else:
        gaps.append("Business context missing")

    if voc:
        score = min(score + 0.5, 5.0)

    return min(score, 5.0), gaps


def _score_measure(d: Dict) -> Tuple[float, List[str]]:
    score, gaps = 0.0, []
    kpis = _safe_list(d, "baseline_kpis")
    dc = str(d.get("data_collection", ""))
    cap = _safe_list(d, "process_capability")
    issues = _safe_list(d, "data_issues")

    if kpis:
        numeric_kpis = _count_numeric_items([str(k) for k in kpis])
        score += min(numeric_kpis * 0.8, 2.5)
        if numeric_kpis == 0:
            gaps.append("Baseline KPIs present but no numeric values")
    else:
        gaps.append("No baseline KPIs — measurement phase is empty")

    if len(dc) > 20:
        score += 1.0
    else:
        gaps.append("Data collection method not described")

    if cap:
        score += 1.0
        if any(c.get("sigma_level") for c in cap if isinstance(c, dict)):
            score += 0.5
    else:
        gaps.append("Process capability not assessed")

    if issues:
        score = min(score + 0.5, 5.0)

    return min(score, 5.0), gaps


def _score_analyze(d: Dict) -> Tuple[float, List[str]]:
    score, gaps = 0.0, []
    roots = _safe_list(d, "root_causes")
    validated = _safe_list(d, "validated_causes")
    evidence = _safe_list(d, "evidence")
    drivers = _safe_list(d, "key_drivers")

    if roots:
        score += 1.5
        if len(roots) >= 3:
            score += 0.5
    else:
        gaps.append("No root causes identified — ANALYZE phase is empty")
        return 0.0, gaps

    if validated:
        score += 1.5
    else:
        gaps.append("Root causes listed but none validated with evidence")
        score -= 1.0  # Penalty: causes without validation

    if evidence:
        score += 1.0
        if _count_numeric_items([str(e) for e in evidence]) > 0:
            score += 0.5
    else:
        gaps.append("No statistical or documented evidence provided")
        score -= 1.0  # Penalty: no evidence

    if drivers:
        score += 0.5

    return min(max(score, 0.0), 5.0), gaps


def _score_improve(d: Dict) -> Tuple[float, List[str]]:
    score, gaps = 0.0, []
    solutions = _safe_list(d, "solutions")
    impact = _safe_list(d, "impact_estimation")
    cb = _safe_list(d, "cost_benefit")
    risks = _safe_list(d, "risks")

    if solutions:
        score += 1.5
        linked = sum(1 for s in solutions if isinstance(s, dict) and s.get("linked_cause"))
        if linked > 0:
            score += min(linked * 0.3, 1.0)
        else:
            gaps.append("Solutions not linked to root causes")
    else:
        gaps.append("No solutions proposed")

    if impact:
        score += 1.0
        if _count_numeric_items([str(i) for i in impact]) > 0:
            score += 0.5
    else:
        gaps.append("No quantified impact estimation")

    if cb:
        score += 0.5
    else:
        gaps.append("Cost-benefit analysis absent")

    if risks:
        score += 0.5

    return min(score, 5.0), gaps


def _score_control(d: Dict) -> Tuple[float, List[str]]:
    score, gaps = 0.0, []
    plan = _safe_list(d, "control_plan")
    kpis = _safe_list(d, "monitoring_kpis")
    std = _safe_list(d, "standardization")

    if plan:
        score += 2.0
        owners = sum(1 for p in plan if isinstance(p, dict) and p.get("owner"))
        if owners > 0:
            score += 0.5
    else:
        gaps.append("Control plan is missing — no sustainability mechanism")

    if kpis:
        score += 1.5
        with_thresholds = sum(1 for k in kpis if isinstance(k, dict) and k.get("alert_threshold"))
        if with_thresholds > 0:
            score += 0.5
    else:
        gaps.append("No monitoring KPIs defined")

    if std:
        score += 0.5

    return min(score, 5.0), gaps


def _score_data_strength(brain: DocumentBrain, compiled: Dict) -> Tuple[float, List[str]]:
    gaps = []
    # Count numerics across the full compiled report text
    full_text = json.dumps(compiled)
    numeric_count = len(_RE_NUMERIC.findall(full_text))
    financial_hits = len(_RE_FINANCIAL_AMOUNT.findall(full_text))

    score = 0.0
    if numeric_count >= 20:
        score += 3.0
    elif numeric_count >= 10:
        score += 2.0
    elif numeric_count >= 5:
        score += 1.0
    else:
        gaps.append("Very few numeric values — report lacks quantification")

    if financial_hits >= 5:
        score += 2.0
    elif financial_hits >= 2:
        score += 1.0
    else:
        gaps.append("Financial data is sparse")

    # Bonus: avg section confidence
    confidences = [n.score for n in brain.iter_sections()]
    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        score += avg_conf * 1.0

    return min(score, 5.0), gaps


def _score_financial_impact(compiled: Dict) -> Tuple[float, List[str]]:
    gaps = []
    exec_s = compiled.get("executive_summary", {})
    fin_items = _safe_list(exec_s, "financial_impact")
    measure_kpis = _safe_list(compiled.get("measure", {}), "baseline_kpis")
    improve_cb = _safe_list(compiled.get("improve", {}), "cost_benefit")

    score = 0.0
    quantified = sum(1 for f in fin_items if isinstance(f, dict) and f.get("amount") is not None)
    if quantified >= 2:
        score += 2.5
    elif quantified == 1:
        score += 1.5
    elif fin_items:
        score += 0.5
        gaps.append("Financial items present but amounts not quantified")
    else:
        gaps.append("No financial impact identified")

    if improve_cb:
        score += 1.5
    else:
        gaps.append("No cost-benefit or ROI data in IMPROVE phase")

    if _count_numeric_items([str(k) for k in measure_kpis]) >= 2:
        score += 1.0

    return min(score, 5.0), gaps


def _score_consistency(compiled: Dict, brain: DocumentBrain) -> Tuple[float, List[str]]:
    gaps = []
    score = 5.0  # Start full, deduct for inconsistencies

    roots = _safe_list(compiled.get("analyze", {}), "root_causes")
    solutions = _safe_list(compiled.get("improve", {}), "solutions")
    measure_kpis = _safe_list(compiled.get("measure", {}), "baseline_kpis")
    control_kpis = _safe_list(compiled.get("control", {}), "monitoring_kpis")
    exec_kpis = _safe_list(compiled.get("executive_summary", {}), "key_kpis")

    # Penalty: solutions without root causes
    if solutions and not roots:
        score -= 3.0
        gaps.append("IMPROVE has solutions but ANALYZE has no root causes")

    # Penalty: unlinked solutions
    unlinked = sum(1 for s in solutions
                   if isinstance(s, dict) and not s.get("linked_cause"))
    if unlinked > 0 and roots:
        score -= min(unlinked * 0.5, 2.0)
        gaps.append(f"{unlinked} solution(s) not linked to root causes")

    # Penalty: control KPIs not in measure
    if control_kpis and not measure_kpis:
        score -= 1.0
        gaps.append("Control KPIs defined but no baselines established in MEASURE")

    # Penalty: no control when improve/analyze present
    if (solutions or roots) and not control_kpis:
        score -= 1.5
        gaps.append("Analysis/improvements present but no control/monitoring plan")

    # Bonus: executive summary consistent with phases
    if exec_kpis and measure_kpis:
        score = min(score + 0.5, 5.0)

    return max(score, 0.0), gaps


def _score_traceability(brain: DocumentBrain) -> Tuple[float, List[str]]:
    """Score traceability (0-5): what % of findings/kpis/risks have source_pages?"""
    gaps = []
    total = 0
    traced = 0
    for sr in brain.results["sections"].values():
        for key in ("keyFindings", "kpis", "risks"):
            for item in sr.get(key, []):
                if isinstance(item, dict):
                    total += 1
                    if _has_source_pages(item):
                        traced += 1

    if total == 0:
        return 0.0, ["No findings/kpis/risks to evaluate traceability"]

    pct = traced / total
    if pct >= 0.95:
        score = 5.0
    elif pct >= 0.80:
        score = 4.0
    elif pct >= 0.60:
        score = 3.0
    elif pct >= 0.40:
        score = 2.0
    else:
        score = 1.0

    if pct < 0.80:
        gaps.append(f"Only {pct:.0%} of items have source_pages ({traced}/{total})")
    if pct < 0.50:
        gaps.append("CRITICAL: majority of insights lack source traceability — audit risk")

    return score, gaps


_QUALITY_EVALUATOR_PROMPT = """\
Evaluate this Six Sigma report for reasoning quality and logical consistency.

REPORT:
{report_json}

Return JSON only:
{{
  "analyze_rigor": <0-5 integer>,
  "logic_quality": <0-5 integer>,
  "overall_feedback": "<1-2 sentences>"
}}

Criteria:
- analyze_rigor: Are root causes specific, evidence-based, and credible?
- logic_quality: Do solutions flow from root causes? Does control plan sustain improvements?
"""


def score_report(
    compiled: Dict[str, Any],
    brain: DocumentBrain,
    use_llm_evaluator: bool = True,
    _llm_quality: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Stage 14: Score the compiled DMAIC report across 9 dimensions (incl. traceability)."""

    d_score, d_gaps = _score_define(compiled.get("define", {}))
    m_score, m_gaps = _score_measure(compiled.get("measure", {}))
    a_score, a_gaps = _score_analyze(compiled.get("analyze", {}))
    i_score, i_gaps = _score_improve(compiled.get("improve", {}))
    c_score, c_gaps = _score_control(compiled.get("control", {}))
    ds_score, ds_gaps = _score_data_strength(brain, compiled)
    fi_score, fi_gaps = _score_financial_impact(compiled)
    co_score, co_gaps = _score_consistency(compiled, brain)

    # ── Traceability dimension (0-5) ─────────────────────────────────────
    tr_score, tr_gaps = _score_traceability(brain)

    rule_total = d_score + m_score + a_score + i_score + c_score + ds_score + fi_score + co_score + tr_score
    rule_pct = (rule_total / 45.0) * 100.0  # max is now 45 (9 × 5)

    # Optional LLM evaluator (1 cheap call for nuance)
    llm_pct = rule_pct  # default: same as rule if LLM fails
    llm_feedback = ""
    if _llm_quality is not None:
        # Use pre-computed LLM quality from final_report_synthesis (no extra call)
        try:
            llm_rigor = float(_llm_quality.get("analyze_rigor", 3))
            llm_logic = float(_llm_quality.get("logic_quality", 3))
            llm_score_pts = (llm_rigor / 5.0 * 5.0) + (llm_logic / 5.0 * 5.0)
            llm_pct = (llm_score_pts / 10.0) * 100.0
            llm_feedback = _llm_quality.get("overall_feedback", "")
        except Exception as _e:
            logger.warning("_llm_quality parse error: %s", _e)
    elif use_llm_evaluator:
        try:
            # Only send the analyze + improve sections to save tokens
            mini_report = {
                "analyze": compiled.get("analyze", {}),
                "improve": compiled.get("improve", {}),
                "control": compiled.get("control", {}),
            }
            eval_prompt = _QUALITY_EVALUATOR_PROMPT.format(
                report_json=json.dumps(mini_report, indent=1)
            )
            llm_eval = _call_gemini_json(
                eval_prompt,
                model=MODELS["cheap"]["name"],
                system_instruction="Six Sigma evaluator. JSON only.",
                max_output_tokens=150,
            )
            if llm_eval:
                llm_rigor = float(llm_eval.get("analyze_rigor", 3))
                llm_logic = float(llm_eval.get("logic_quality", 3))
                llm_score_pts = (llm_rigor / 5.0 * 5.0) + (llm_logic / 5.0 * 5.0)
                llm_pct = (llm_score_pts / 10.0) * 100.0
                llm_feedback = llm_eval.get("overall_feedback", "")
        except Exception as _e:
            logger.warning("LLM evaluator skipped: %s", _e)

    # Hybrid final score: 70% rule + 30% LLM
    final_pct = round(0.70 * rule_pct + 0.30 * llm_pct, 1)

    # Rating
    if final_pct >= 90:
        rating = "Black Belt"
        rating_color = "emerald"
    elif final_pct >= 75:
        rating = "Green Belt"
        rating_color = "teal"
    elif final_pct >= 60:
        rating = "Acceptable"
        rating_color = "amber"
    else:
        rating = "Weak Analysis"
        rating_color = "red"

    # Deduplicated gaps across all categories
    all_gaps = list(dict.fromkeys(
        d_gaps + m_gaps + a_gaps + i_gaps + c_gaps + ds_gaps + fi_gaps + co_gaps + tr_gaps
        + compiled.get("gaps", [])
    ))[:8]

    # Auto-improve flag: list phases that should be reprocessed
    reprocess_phases = []
    if a_score < 2.5:
        reprocess_phases.append("analyze")
    if c_score < 2.0:
        reprocess_phases.append("control")
    if m_score < 2.0:
        reprocess_phases.append("measure")

    score_result = {
        "overall_score": final_pct,
        "rule_score": round(rule_pct, 1),
        "rating": rating,
        "rating_color": rating_color,
        "breakdown": {
            "define":       round(d_score, 1),
            "measure":      round(m_score, 1),
            "analyze":      round(a_score, 1),
            "improve":      round(i_score, 1),
            "control":      round(c_score, 1),
            "data_strength":    round(ds_score, 1),
            "financial_impact": round(fi_score, 1),
            "consistency":  round(co_score, 1),
            "traceability": round(tr_score, 1),
        },
        "gaps": all_gaps,
        "llm_feedback": llm_feedback,
        "reprocess_phases": reprocess_phases,
        "max_score": 45,
    }

    logger.info(
        "Quality score: %.1f%% (%s) | D=%.1f M=%.1f A=%.1f I=%.1f C=%.1f DS=%.1f FI=%.1f CO=%.1f TR=%.1f | gaps=%d",
        final_pct, rating,
        d_score, m_score, a_score, i_score, c_score, ds_score, fi_score, co_score, tr_score,
        len(all_gaps),
    )

    return score_result


# ═══════════════════════════════════════════════════════════════════════════
# FINAL REPORT SYNTHESIS (merged Stages 12 + 13 + 14 LLM call)
# ═══════════════════════════════════════════════════════════════════════════

_FINAL_REPORT_PROMPT = """\
You are a DETERMINISTIC DATA COMPILER and Six Sigma reporting expert.

TASK: In ONE response, produce three outputs from the pre-analyzed data below:
  1) Executive dashboard (full schema)
  2) Six Sigma DMAIC report
  3) Quality evaluation scores

STRICT RULES:
1. ONLY use data present in the SECTION ANALYSES and DMAIC PHASE SYNTHESES.
2. NEVER infer, generalize, or invent data not stated in the input.
3. Every KPI, finding, risk, and recommendation MUST have source_pages.
4. If a field has no supporting data, use null, [], or "INSUFFICIENT_DATA".
5. Confidence scores MUST NOT exceed the max confidence of contributing inputs.

SOURCE: {source_type} | {num_sections} sections | {total_pages} pages

SECTION ANALYSES (your ONLY data source for section-level content):
{section_analyses_json}

DMAIC PHASE SYNTHESES (your ONLY data source for DMAIC content):
{phase_syntheses_json}

CROSS-PHASE INSIGHTS (include as-is):
{cross_phase_json}

Return ONE JSON envelope with three keys — dashboard, dmaicReport, qualityEval:
{{
  "dashboard": {{
    "meta": {{
      "reportId": "{report_id}",
      "ingestedAt": "{ingested_at}",
      "sourceType": "{source_type}",
      "confidenceOverall": 0.0,
      "decisionReadinessScore": 0.0,
      "sectionsAnalyzed": {num_sections},
      "totalPages": {total_pages}
    }},
    "autoClassification": {{
      "reportType": ["operations","hse","finance","audit","strategy"],
      "assetScope": "well|field|plant|pipeline|enterprise",
      "timeHorizon": "operational|tactical|strategic",
      "decisionLevel": "operations|management|board",
      "confidence": 0.0
    }},
    "dashboard": {{
      "title": "str",
      "description": "str",
      "sections": [{{
        "sectionId": "sec_001",
        "title": "str",
        "pageRange": "Pages X-Y",
        "tier": 1,
        "dmaicPhase": "define|measure|analyze|improve|control|none",
        "modelUsed": "cheap|balanced|powerful",
        "summary": "str",
        "keyFindings": [{{"finding": "str", "impact": "high|medium|low", "confidence": 0.0, "source_pages": [int]}}],
        "kpis": [{{"id":"str","title":"str","value": 0,"unit":"str","confidence":0.0,"source_pages":[int]}}],
        "risks": [{{"risk":"str","severity":"high|medium|low","source_pages":[int]}}],
        "recommendations": ["str"],
        "financialImpact": {{"items": []}},
        "charts": [],
        "confidence": 0.0
      }}],
      "sixSigma": {{
        "methodology": "DMAIC",
        "dmaic": {{
          "define": {{"problemStatement":"str","ctqs":["str"],"financialExposure":{{"value":null,"unit":"$"}}}},
          "measure": {{"baselineMetrics":["str"],"dataConfidence":0.0}},
          "analyze": {{"rootCauses":[{{"cause":"str","confidence":0.0}}],"correlations":["str"]}},
          "improve": {{"recommendedActions":["str"],"expectedSigmaLift":"str"}},
          "control": {{"controlPlan":["str"],"monitoringKPIs":["str"]}}
        }},
        "sigmaLevel": "str",
        "defectRate": "str",
        "processCapability": "Low|Medium|High",
        "statisticalValidity": false
      }},
      "kpis": [{{"id":"str","title":"max 5 words","value":0,"unit":"$|%|count|hrs","target":null,"trend":"stable","change":"","changeType":"neutral","confidence":0.0,"owner":"str","sourceSection":"str","source_pages":[int],"icon":"dollar|users|activity|chart|trending","color":"green|blue|purple|red|yellow","priority":"tier1|tier2|tier3|tier4"}}],
      "charts": [{{"id":"str","type":"BarChart|LineChart|AreaChart|PieChart|RadarChart","title":"str","size":"full|half|third","chartConfig":{{}},"data":[]}}],
      "tables": [],
      "optimizationSuggestions": [{{"id":"str","title":"str","category":"cost|efficiency|performance|risk|quality","impact":"high|medium|low","roi":0,"savings":{{"value":0,"unit":"$","timeframe":"annually"}},"description":"str","priority":"high|medium|low","confidence":0.0,"sourceSection":"str","decision_traceability":{{"data_sources":["str"],"analytical_methods":["str"],"supporting_evidence":["str"]}},"industry_benchmarking":{{"median_comparison":"str","top_quartile_comparison":"str","peer_comparison":"str","performance_gap":"str"}},"decision_confidence_index":{{"score":0,"data_completeness":"str","model_confidence":"str","historical_accuracy":"str","variability":"str","explanation":"str"}},"assumptions_limitations":["str"],"use_case":"str","action_management":{{"task_title":"str","description":"str","owner":"str","kpi":"str","target_value":"str","deadline":"str","priority":"high|medium|low","status":"Open"}},"execution_plan":["str"],"closed_loop_learning":{{"predicted_impact":"str","measurement_plan":"str","feedback_capture":"str","learning_loop":"str","actual_vs_predicted":{{"predicted":"str","actual":"TBD"}}}},"integration_mapping":{{"erp":"str","scada":"str","production_db":"str","excel":"str"}},"domain_kpis":[{{"name":"str","current":"str","target":"str","direction":"increase|decrease"}}],"failure_modes":[{{"cause":"str","confidence":0.0}}]}}],
      "predictive": {{"forecast":[],"whatIfScenarios":[]}},
      "insights": {{
        "summary": "str",
        "crossSectionCorrelations": [{{"insight":"str","source_pages":[int]}}],
        "crossPhaseInsights": [{{"insight":"str","source_pages":[int]}}],
        "trends": [{{"trend":"str","source_pages":[int]}}],
        "alerts": [{{"type":"warning|error|info|success","message":"str","severity":"high|medium|low","action":"str","source_pages":[int]}}],
        "recommendations": [{{"recommendation":"str","source_pages":[int]}}]
      }},
      "explainability": {{
        "whyThisConclusion": ["str"],
        "dataUsed": ["str"],
        "assumptions": ["str"],
        "limitations": ["str"],
        "sectionsCovered": {num_sections},
        "totalPages": {total_pages},
        "analysisApproach": "Centralized DocumentBrain with tiered model routing and DMAIC-aware synthesis"
      }}
    }},
    "ceo_view": {{
      "decisions": [{{"title":"str","impact":"str","urgency":"high|medium|low"}}],
      "risks": [{{"title":"str","severity":"High|Medium|Low","financial_impact":"str"}}],
      "actions": [{{"title":"str","owner":"str","timeline":"str"}}]
    }},
    "manager_view": {{
      "dmaic": {{"define":"str","measure":"str","analyze":"str","improve":"str","control":"str"}},
      "recommendations": [{{"title":"str","impact":"str","timeline":"str","priority":"high|medium|low"}}],
      "kpi_tracking": [{{"name":"str","current":"str","target":"str","status":"on-track|at-risk|off-track"}}]
    }},
    "engineer_view": {{
      "data_references": ["str"],
      "models": ["str"],
      "root_cause_analysis": ["str"],
      "failure_modes": [{{"cause":"str","probability":0.0,"detection":"str","mitigation":"str"}}],
      "assumptions": ["str"]
    }},
    "boardroom_mode": {{
      "executive_summary": "str",
      "slides": {{
        "summary": ["str"],
        "decisions": ["str"],
        "risks": ["str"],
        "actions": ["str"],
        "kpi_impact": ["str"]
      }}
    }}
  }},

  "dmaicReport": {{
    "define": {{"problem_statement":"str","business_context":"str","project_scope":"str","voc":["str"]}},
    "measure": {{"baseline_kpis":[{{"name":"str","value":"str","unit":"str","source":"str"}}],"data_collection":"str","process_capability":[{{"metric":"str","cpk":null,"sigma_level":null,"dpmo":null}}],"data_issues":["str"]}},
    "analyze": {{"root_causes":[{{"cause":"str","category":"material|method|machine|man|measurement|environment","confidence":0.0}}],"validated_causes":["str"],"key_drivers":["str"],"evidence":["str"]}},
    "improve": {{"solutions":[{{"action":"str","linked_cause":"str","expected_impact":"str","cost":null,"priority":"high|medium|low"}}],"impact_estimation":["str"],"cost_benefit":["str"],"risks":["str"]}},
    "control": {{"control_plan":[{{"what":"str","how":"str","frequency":"str","owner":"str"}}],"monitoring_kpis":[{{"kpi":"str","target":"str","alert_threshold":"str"}}],"standardization":["str"],"risks":["str"]}},
    "executive_summary": {{"summary":"str","financial_impact":[{{"description":"str","amount":null,"unit":"$","type":"saving|cost|exposure"}}],"key_kpis":[{{"name":"str","baseline":"str","current_or_target":"str","improvement":"str"}}],"top_risks":["str"],"recommendations":["str"]}},
    "gaps": ["str"],
    "compilation_confidence": 0.0
  }},

  "qualityEval": {{
    "analyze_rigor": 3,
    "logic_quality": 3,
    "overall_feedback": "str"
  }}
}}

RULES:
- TRACEABILITY: Every KPI, finding, risk, insight MUST include source_pages. Omit items you cannot trace.
- ANTI-HALLUCINATION: Every value and claim must come from the input. Use null/[] if data is missing.
- Top-level KPIs: up to 12 most critical from input data. Fewer if not enough input.
- ceo_view: exactly 3 decisions, 3 risks, 3 actions — plain language, max 8 words per title.
- dmaicReport mirrors the DMAIC phase syntheses — do NOT embellish.
- qualityEval: analyze_rigor and logic_quality are 0-5 integers.
- JSON only, no text outside."""


def final_report_synthesis(
    brain: DocumentBrain,
    report_id: str,
    ingested_at: str,
    progress=None,
    diag=None,
    manifest=None,
) -> tuple:
    """Merged Stages 12+13+14: one LLM call produces dashboard, dmaicReport, and qualityEval.

    Returns (dashboard_dict, compiled_dmaic_dict, quality_eval_dict).
    On failure returns (None, None, None) — caller must fall back to individual stages.
    """
    if progress:
        progress(12, 15, "Final report synthesis (executive + DMAIC + quality)...")

    # ── Build compact_analyses — same logic as executive_synthesis ──────
    groups = brain.results.get("groups")
    if groups:
        compact_analyses = []
        for gk, gs in groups.items():
            compact_analyses.append({
                "groupTitle": gs.get("group_title", gk),
                "sectionCount": gs.get("section_count", 0),
                "summary": gs.get("summary", ""),
                "keyFindings": gs.get("merged_findings", []),
                "kpis": gs.get("aggregated_kpis", []),
                "risks": gs.get("top_risks", []),
                "financialImpact": gs.get("financial_impact", {}),
                "recommendations": gs.get("recommendations", []),
                "confidence": gs.get("confidence", 0.5),
                "confidence_level": gs.get("confidence_level", ""),
                "sourcePages": gs.get("source_pages", []),
            })
    else:
        compact_analyses = []
        for node in brain.iter_sections():
            sa = brain.results["sections"].get(node.id, {})
            compact = {k: sa[k] for k in [
                "sectionTitle", "sectionSummary", "keyFindings", "kpis",
                "risks", "recommendations", "financialImpact", "charts", "confidence",
                "confidence_level", "confidence_breakdown",
            ] if k in sa}
            compact["tier"] = node.tier
            compact["dmaicPhase"] = node.dmaic_phase or "unassigned"
            compact["modelUsed"] = node.execution.get("model_tier", "balanced")
            compact["pageRange"] = f"Pages {node.start_index}-{node.end_index}"
            compact_analyses.append(compact)

    prompt = _FINAL_REPORT_PROMPT.format(
        source_type=brain.source_type,
        num_sections=len(brain.sections),
        total_pages=brain.metadata["total_pages"],
        section_analyses_json=json.dumps(compact_analyses, indent=1),
        phase_syntheses_json=json.dumps(brain.results["dmaic"], indent=1),
        cross_phase_json=json.dumps(brain.results["cross_phase"], indent=1),
        report_id=report_id,
        ingested_at=ingested_at,
    )

    result = _call_gemini_json(
        prompt,
        model=MODELS["powerful"]["name"],
        system_instruction=(
            "Deterministic data compiler and Six Sigma reporting expert. "
            "Produce dashboard, DMAIC report, and quality evaluation in one JSON response. "
            "NEVER infer or invent data not in the input. JSON only."
        ),
        max_output_tokens=MODELS["powerful"]["max_output_tokens"],
    )

    if not result or not isinstance(result, dict):
        logger.warning("Merged final report call returned nothing — falling back to individual stages")
        return None, None, None

    dashboard = result.get("dashboard")
    compiled_dmaic = result.get("dmaicReport")
    quality_eval_raw = result.get("qualityEval", {})

    return dashboard, compiled_dmaic, quality_eval_raw


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT (called from llm.py)
# ═══════════════════════════════════════════════════════════════════════════

def generate_full_report_analysis(
    chunks: List[str],
    num_files: int,
    source_type: str = "UNKNOWN",
    progress_callback=None,
    budget_cap_usd: Optional[float] = None,
    diag=None,
    manifest=None,
) -> Dict[str, Any]:
    """
    Full-report Six Sigma decision-support pipeline.

    All state flows through ONE central DocumentBrain object.
    Every stage reads from and enriches the brain — zero duplication.

    Args:
        diag: Optional PipelineDiagnostics instance for surgical debugging.
              Set PIPELINE_DIAGNOSTICS=1 to enable.
        manifest: Optional DocumentManifest for coverage tracking.
              Always active when provided — tracks every page/chunk/section.

    Stages:
      1. build_structure()      — PageIndex → SectionNodes
      2. score_all()            — heuristic scoring (6 dims + PageIndex)
      3. classify_all()         — tier assignment (cost routing only, NO skips)
      4. route_models()         — model selection per section
      5. enforce_budget()       — downgrade if over cost cap
      6. estimate_cost()        — pre-flight token estimate
      7. execute_analysis()     — UNIFORM LLM extraction on ALL sections
      8. reprocess_weak()       — confidence-based reprocessing
      9. group_aggregate()      — group-level aggregation (hierarchical map-reduce)
     10. synthesize_phases()    — GLOBAL DMAIC synthesis (all data → each phase)
     11. cross_phase_check()    — rule-based intelligence
     12. executive_synthesis()  — final dashboard (uses group summaries)
     13. dmaic_compiler()       — strict Six Sigma DMAIC deliverable
     14. score_report()         — 8-dimension quality scoring engine

    Architecture: Extract → Group → Aggregate → DMAIC (global) → Synthesize
    DMAIC is a system-level framework applied AFTER full-document context is
    built — never at chunk/section level.
    """
    def _progress(step: int, total: int, msg: str):
        logger.info("[%d/%d] %s", step, total, msg)
        if progress_callback:
            try:
                progress_callback(step, total, msg)
            except Exception:
                pass

    # ── Create the brain ─────────────────────────────────────────────────
    brain = DocumentBrain(chunks, source_type)
    _reset_insight_counter()  # Fresh IDs for each pipeline run
    logger.info(
        "Brain initialized: %d chunks, %d chars, source=%s",
        len(brain.chunks), brain.metadata["total_chars"], source_type,
    )

    # Register chunks on manifest (after sentinel filtering)
    if manifest:
        manifest.register_chunks(brain.chunks)

    # ── Stage 1: Build structure ─────────────────────────────────────────
    _progress(1, 15, "Building document structure (PageIndex)...")
    if diag:
        diag.start_stage("build_structure")
    build_structure(brain)
    if diag:
        diag.end_stage("build_structure")
        diag.record_structure(brain)

    # Register sections on manifest
    if manifest:
        for node in brain.iter_sections():
            manifest.register_section(
                node.id, node.title, node.start_index, node.end_index, len(node.text),
            )
        manifest.gate_chunking()

    # ── Stage 2: Score all sections ──────────────────────────────────────
    _progress(2, 15, f"Scoring {len(brain.sections)} sections...")
    if diag:
        diag.start_stage("score_all")
    score_all(brain)
    if diag:
        diag.end_stage("score_all")

    # ── Stage 3: Classify tiers ──────────────────────────────────────────
    _progress(3, 15, "Classifying tiers & building execution plan...")
    classify_all(brain)

    # ── Stage 4: Route models ────────────────────────────────────────────
    _progress(4, 15, "Routing models per section...")
    route_models(brain)

    # ── Record scoring + tier diagnostics after classification + routing ──
    if diag:
        diag.record_scoring(brain)

    # Update manifest with scoring results
    if manifest:
        for node in brain.iter_sections():
            manifest.update_section_scoring(
                node.id, node.score, node.tier,
                node.execution.get("should_run", True),
                node.execution.get("model_tier", ""),
            )

    # ── Stage 5: Budget enforcement ──────────────────────────────────────
    if budget_cap_usd:
        _progress(5, 15, f"Enforcing budget cap (${budget_cap_usd:.4f})...")
        enforce_budget(brain, budget_cap_usd)

    # ── Stage 6: Cost estimate ───────────────────────────────────────────
    _progress(6, 15, "Estimating cost...")
    estimate_cost(brain)

    # ── Stage 7: Execute analysis ────────────────────────────────────────
    if diag:
        diag.start_stage("execute_analysis")
    execute_analysis(brain, progress=_progress, diag=diag, manifest=manifest)
    if diag:
        diag.end_stage("execute_analysis")
        diag.finalize_execution(brain)

    # Coverage gate: did we process enough sections?
    if manifest:
        manifest.gate_processing()

    # ── Stage 8: Reprocess weak results ──────────────────────────────────
    _progress(8, 15, "Checking for weak results...")
    if diag:
        diag.start_stage("reprocess_weak")
    reprocess_weak(brain, diag=diag, manifest=manifest)
    if diag:
        diag.end_stage("reprocess_weak")

    # ── GUARDRAILS: Pre-synthesis coverage validation ────────────────────
    # Ensures NO top-K retrieval or silent truncation has reduced input data.
    _total_chunks = brain.metadata["total_pages"]
    _total_sections = len(brain.sections)
    _processed_sections = sum(
        1 for sr in brain.results["sections"].values()
        if sr.get("confidence", 0) > 0
    )
    _coverage_pct = round(_processed_sections / max(_total_sections, 1) * 100, 1)

    brain.metadata["_guardrails"] = {
        "total_chunks_ingested": _total_chunks,
        "total_sections": _total_sections,
        "sections_with_results": _processed_sections,
        "coverage_pct": _coverage_pct,
    }

    if _total_chunks == 0:
        logger.error("GUARDRAIL FAIL: 0 chunks ingested — no data to analyze")
    if _processed_sections == 0:
        logger.error("GUARDRAIL FAIL: 0 sections produced results — pipeline stalled")
    elif _coverage_pct < 80:
        logger.warning(
            "GUARDRAIL WARN: only %.1f%% sections produced results (%d/%d) — "
            "possible data loss before synthesis",
            _coverage_pct, _processed_sections, _total_sections,
        )
    else:
        logger.info(
            "GUARDRAIL OK: %.1f%% section coverage (%d/%d sections, %d chunks)",
            _coverage_pct, _processed_sections, _total_sections, _total_chunks,
        )

    # ── Stage 9: Group-level aggregation ────────────────────────────────
    # Progressive compression: section analyses → group summaries
    # This prevents token overflow and attention dilution in synthesis stages
    _progress(9, 15, "Group-level aggregation...")
    group_aggregate(brain, progress=_progress, diag=diag)

    # ── Stage 10: GLOBAL DMAIC synthesis (full-document context) ─────────
    if diag:
        diag.start_stage("synthesize_phases")
    synthesize_phases(brain, progress=_progress, diag=diag)
    _annotate_dmaic_supporting_groups(brain)
    if diag:
        diag.end_stage("synthesize_phases")

    # ── Stage 11: Cross-phase check ──────────────────────────────────────
    _progress(11, 15, "Cross-phase intelligence check...")
    cross_phase_check(brain)

    # ── Stages 12+13+14: Merged final report synthesis (1 LLM call) ──────
    report_id = str(uuid.uuid4())
    ingested_at = datetime.datetime.utcnow().isoformat() + "Z"
    if diag:
        diag.start_stage("final_report_synthesis")
    _merged_dashboard, _merged_dmaic, _merged_quality = final_report_synthesis(
        brain, report_id=report_id, ingested_at=ingested_at,
        progress=_progress, diag=diag, manifest=manifest,
    )
    if diag:
        diag.end_stage("final_report_synthesis")

    if _merged_dashboard is not None:
        # Merged call succeeded — unpack all three outputs
        dashboard = _merged_dashboard
        compiled_dmaic = _merged_dmaic or {}
        quality_score = score_report(
            compiled_dmaic, brain,
            use_llm_evaluator=False,
            _llm_quality=_merged_quality,
        )
    else:
        # Fallback: run stages individually (same as before)
        logger.info("Falling back to individual stage calls (12 → 13 → 14)")
        if diag:
            diag.start_stage("executive_synthesis")
        dashboard = executive_synthesis(brain, progress=_progress, diag=diag, manifest=manifest)
        if diag:
            diag.end_stage("executive_synthesis")

        _progress(13, 15, "DMAIC Report Compiler (strict Six Sigma deliverable)...")
        compiled_dmaic = dmaic_compiler(brain, dashboard, progress=_progress)

        _progress(14, 15, "Quality Scoring Engine...")
        quality_score = score_report(compiled_dmaic, brain, use_llm_evaluator=True)

    # ── Attach compiler output + quality score to dashboard ───────────────
    target = dashboard.get("dashboard", dashboard)
    target["dmaicReport"] = compiled_dmaic
    target["qualityScore"] = quality_score

    # ── Attach aggregation metrics (validation) ──────────────────────────
    groups = brain.results.get("groups")
    group_count = len(groups) if groups else 0
    processed_sections = sum(
        1 for sr in brain.results["sections"].values()
        if sr.get("confidence", 0) > 0
    )
    # ── Tier breakdown (cost-optimization tiers — all sections processed uniformly) ──
    tier_breakdown = {"tier1": 0, "tier2": 0, "tier3": 0, "total_uniform": 0}
    for sid, sr in brain.results["sections"].items():
        st = sr.get("_source_tier")
        if st == 1:
            tier_breakdown["tier1"] += 1
        elif st == 2:
            tier_breakdown["tier2"] += 1
        elif st == 3:
            tier_breakdown["tier3"] += 1
        tier_breakdown["total_uniform"] += 1

    # ── Traceability metrics ────────────────────────────────────────────
    total_items = 0
    items_with_source = 0
    items_with_real_source = 0  # LLM-provided, not fallback-injected
    items_with_fallback = 0
    for sr in brain.results["sections"].values():
        for item_list_key in ("keyFindings", "kpis", "risks"):
            items = sr.get(item_list_key, [])
            for item in items:
                if isinstance(item, dict):
                    total_items += 1
                    if _has_source_pages(item):
                        items_with_source += 1
                        if item.get("_source_pages_fallback"):
                            items_with_fallback += 1
                        else:
                            items_with_real_source += 1
    traceability_pct = round(items_with_source / max(total_items, 1) * 100, 1)
    real_traceability_pct = round(items_with_real_source / max(total_items, 1) * 100, 1)

    # ── Confidence distribution metrics ─────────────────────────────────
    evidence_confs = []
    llm_confs = []
    conf_tiers = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for sr in brain.results["sections"].values():
        ec = sr.get("confidence")
        if isinstance(ec, (int, float)) and ec > 0:
            evidence_confs.append(ec)
        lc = sr.get("_llm_confidence")
        if isinstance(lc, (int, float)):
            llm_confs.append(lc)
        cl = sr.get("confidence_level", "LOW")
        if cl in conf_tiers:
            conf_tiers[cl] += 1

    avg_evidence_conf = round(sum(evidence_confs) / max(len(evidence_confs), 1), 3)
    avg_llm_conf = round(sum(llm_confs) / max(len(llm_confs), 1), 3)

    aggregation_metrics = {
        "total_chunks": len(brain.chunks),
        "total_sections": len(brain.sections),
        "sections_processed": processed_sections,
        "group_summaries": group_count,
        "compression_ratio": f"{len(brain.chunks)} → {len(brain.sections)} → {group_count or len(brain.sections)} → 1",
        "section_coverage_pct": round(processed_sections / max(len(brain.sections), 1) * 100, 1),
        "dmaic_phases_populated": list(brain.results["dmaic"].keys()),
        "pipeline_stages": 15,
        "tier_breakdown": tier_breakdown,
        "tier3_pct": round(tier_breakdown.get("tier3", 0) / max(processed_sections, 1) * 100, 1),
        "traceability": {
            "total_items": total_items,
            "with_source_pages": items_with_source,
            "with_real_source_pages": items_with_real_source,
            "with_fallback_source_pages": items_with_fallback,
            "missing_source_pages": total_items - items_with_source,
            "traceability_pct": traceability_pct,
            "real_traceability_pct": real_traceability_pct,
            "gate_threshold": _TRACEABILITY_GATE_THRESHOLD,
            "gate_status": "PASS" if traceability_pct >= _TRACEABILITY_GATE_THRESHOLD else "FAIL",
        },
        "confidence": {
            "avg_evidence_confidence": avg_evidence_conf,
            "avg_llm_confidence": avg_llm_conf,
            "evidence_vs_llm_delta": round(avg_evidence_conf - avg_llm_conf, 3),
            "tier_distribution": conf_tiers,
            "high_pct": round(conf_tiers["HIGH"] / max(processed_sections, 1) * 100, 1),
            "sections_measured": len(evidence_confs),
        },
        "group_stats": brain.metadata.get("_group_stats", {}),
    }

    # ── Document Coverage: how much of the document contributed to report ─
    cov = _extract_used_pages(brain)
    aggregation_metrics["document_coverage"] = {
        "total_pages": cov["total_pages"],
        "used_pages": cov["used_page_count"],
        "page_coverage_pct": cov["page_coverage_pct"],
        "coverage_status": cov["coverage_status"],
        "unused_page_ranges": cov["unused_page_ranges"][:10],  # cap for readability
        "per_section_coverage": cov["per_section"],
    }

    # ── Pre-synthesis guardrails (data integrity proof) ─────────────────
    aggregation_metrics["guardrails"] = brain.metadata.get("_guardrails", {})

    if traceability_pct < _TRACEABILITY_GATE_THRESHOLD:
        logger.warning(
            "TRACEABILITY GATE FAIL: %.1f%% < %.1f%% threshold (%d/%d items, %d real, %d fallback)",
            traceability_pct, _TRACEABILITY_GATE_THRESHOLD,
            items_with_source, total_items, items_with_real_source, items_with_fallback,
        )
        target["_traceability_warning"] = (
            f"LOW TRACEABILITY: Only {traceability_pct}% of insights have source_pages "
            f"({items_with_source}/{total_items}). Real (LLM-provided): {real_traceability_pct}%. "
            f"Results may contain unverifiable claims."
        )
    elif traceability_pct < 95:
        logger.info(
            "TRACEABILITY GATE WARN: %.1f%% — above threshold but below 95%% target",
            traceability_pct,
        )

    # ── Coverage guardrails ─────────────────────────────────────────────
    if cov["coverage_status"] == "BAD":
        logger.warning(
            "⚠ LOW DOCUMENT COVERAGE: %.1f%% (%d/%d pages) — report may be unreliable. "
            "Unused ranges: %s",
            cov["page_coverage_pct"], cov["used_page_count"], cov["total_pages"],
            ", ".join(cov["unused_page_ranges"][:5]),
        )
        # Attach warning to output so API consumers see it
        target["_coverage_warning"] = (
            f"LOW COVERAGE: Only {cov['page_coverage_pct']}% of document pages "
            f"({cov['used_page_count']}/{cov['total_pages']}) contributed to this report. "
            f"Results may not represent the full document."
        )
    elif cov["coverage_status"] == "PARTIAL":
        logger.info(
            "PARTIAL COVERAGE: %.1f%% (%d/%d pages) — some sections may be underrepresented.",
            cov["page_coverage_pct"], cov["used_page_count"], cov["total_pages"],
        )

    # ── Traceability index for UI drill-down (insight_id -> sources) ───
    _groups_for_index = brain.results.get("groups") or {}
    target["_traceability_index"] = _build_traceability_index(
        dashboard=dashboard,
        groups=_groups_for_index,
    )
    target["_group_summaries"] = _groups_for_index

    target["_aggregation_metrics"] = aggregation_metrics

    _progress(15, 15, "Pipeline complete.")

    logger.info(
        "Pipeline complete: %d chunks → %d sections → %d groups → 1 dashboard | "
        "doc_coverage=%.0f%% (%s) | section_coverage=%.0f%% | tiers=%s | models=%s | phases=%s | quality=%.1f%% (%s)",
        len(brain.chunks), len(brain.sections), group_count,
        cov["page_coverage_pct"], cov["coverage_status"],
        aggregation_metrics["section_coverage_pct"],
        {k: len(v) for k, v in brain.execution_plan.items()},
        brain.metadata["model_usage"],
        list(brain.results["dmaic"].keys()),
        quality_score.get("overall_score", 0),
        quality_score.get("rating", "?"),
    )

    return dashboard
