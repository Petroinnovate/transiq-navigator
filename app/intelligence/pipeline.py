"""
Multi-Stage Intelligence Pipeline
==================================

Replaces the monolithic LLM prompt with 4 focused stages:

  Stage 1 — KPI Extraction
    Dedicated compact prompt; returns structured KPI pool (up to 50).

  Stage 2 — DMAIC + Six Sigma Reasoning
    Uses pre-extracted KPIs as context; focused on root-cause and process.

  Stage 3 — Recommendations
    KPI-anchored; each rec must reference a KPI and include financial impact.

  Stage 4 — Final Assembly
    Combines all stages; produces the top-level views (CEO/Manager/Boardroom).

Each stage uses safe_llm_call():
    - Up to 3 retries
    - JSON reinforcement message on failure
    - Automatic JSON extraction from raw text

Post-processing (deterministic):
    - validate_kpis()              — drop low-confidence + duplicates
    - compute_kpi_financial_scores() — deterministic $ impact
    - build_esg_view()             — ESG classification and scoring
    - build_drilling_view()        — drilling analytics

Usage (from llm.py):
    from app.intelligence.pipeline import run_pipeline
    result = run_pipeline(combined_content, num_files, source_type, client)
"""
from __future__ import annotations

import json
import logging
import re
import uuid
import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Glossary pre-filtering (built once at import time)
# ---------------------------------------------------------------------------
try:
    from app.intelligence.context_builder import build_context
    from app.intelligence.domain_glossary import DOMAIN_GLOSSARY
    from app.intelligence.glossary_filter import build_term_index, filter_glossary, format_for_prompt
    _TERM_INDEX = build_term_index(DOMAIN_GLOSSARY)
    logger.info("Glossary pre-filter loaded: %d terms", len(DOMAIN_GLOSSARY))
except Exception as _gloss_err:
    def build_context(content: str, max_output_chars: int = 150000) -> str:
        return content[:max_output_chars]

    DOMAIN_GLOSSARY = {}
    _TERM_INDEX = {}
    def filter_glossary(text, glossary, term_index, **kw): return []  # noqa: E731
    def format_for_prompt(terms): return ""  # noqa: E731
    logger.warning("Glossary pre-filter unavailable: %s", _gloss_err)


# ---------------------------------------------------------------------------
# Gemini model names
# ---------------------------------------------------------------------------
_CHEAP_MODEL = "gemini-2.0-flash"      # Stage 1 & 3 — fast / cheap
_SMART_MODEL = "gemini-2.5-flash"      # Stage 2 & 4 — requires reasoning


# ---------------------------------------------------------------------------
# Stage 1 — KPI Extraction prompt
# ---------------------------------------------------------------------------

_S1_SYSTEM = """\
You are a KPI extraction specialist for Oil & Gas operations.
Your ONLY job: read the document chunks and extract a comprehensive KPI pool.
Return STRICT JSON — no markdown, no explanation, no extra text.
"""

_S1_PROMPT_TEMPLATE = """\
DOCUMENT:
{content}

TASK: Extract 15–50 KPIs. Return this exact JSON structure — nothing else.

{{
  "kpis": [
    {{
      "id": "kpi_001",
      "title": "concise title max 5 words",
      "value": <actual number from the document — never 0 unless genuinely zero>,
      "unit": "$|%|count|hrs|days|bbl|mcf|psi|ft|score",
      "target": <number or null>,
      "trend": "improving|deteriorating|stable",
      "changeType": "positive|negative|neutral",
      "confidence": 0.75,
      "category": "financial|safety|operations|efficiency|reliability|quality",
      "priority": "tier1|tier2|tier3|tier4",
      "owner": "Operations|HSE|Finance|Engineering|Safety",
      "source_reference": {{
        "rig_name": "exact rig/well/asset name extracted from document (e.g. PARAGON MSS1, RIG-101, Well-A3) or null",
        "report_date": "date found near this value (YYYY-MM-DD) or null",
        "source_section": "section or report area where found",
        "raw_evidence": "exact quoted sentence from the document (max 40 words) that contains this number",
        "calculation_method": "direct_extract|sum|average|derived|inferred"
      }},
      "deviationScore": 0,
      "financialImpactScore": 0,
      "riskScore": 0,
      "trendScore": 50,
      "icon": "dollar|activity|trending|users|chart",
      "color": "green|red|blue|yellow|purple"
    }}
  ]
}}

RULES:
- value MUST be an actual number extracted from the document (not 0 unless it IS zero)
- Extract across ALL categories: financial, safety, operations, efficiency, reliability
- Extract KPIs from ALL entities (rigs, wells, assets) mentioned in the document — do NOT stop at the first few
- For each KPI, identify the specific rig/well/asset name from context and set source_reference.rig_name
- Set source_reference.raw_evidence to the EXACT sentence containing the number — this is mandatory for auditability
- Lower confidence to 0.3-0.5 when data is weak or inferred
- Do NOT pre-filter — extract ALL KPIs found; AI ranking engine filters later
- Return ONLY valid JSON, nothing else
{domain_terms_section}"""


# ---------------------------------------------------------------------------
# Stage 2 — DMAIC + Root Cause Analysis
# ---------------------------------------------------------------------------

_S2_SYSTEM = """\
You are a Six Sigma Master Black Belt and Oil & Gas domain expert.
Your job: given extracted KPIs + document context, perform structured DMAIC
and executive analysis. Return STRICT JSON only.
"""

_S2_PROMPT_TEMPLATE = """\
DOCUMENT CONTEXT (excerpt):
{content}

EXTRACTED KPIs (use these — do not re-extract):
{kpis_json}

TASK: Perform DMAIC analysis and build the analytics views.
Return this exact JSON structure — nothing else.

{{
  "autoClassification": {{
    "reportType": ["operations"],
    "assetScope": "well|field|plant|pipeline|enterprise",
    "timeHorizon": "operational|tactical|strategic",
    "decisionLevel": "operations|management|board",
    "confidence": 0.8
  }},

  "dashboard": {{
    "title": "string",
    "description": "string",

    "sixSigma": {{
      "methodology": "DMAIC",
      "sigmaLevel": "string or N/A",
      "defectRate": "string or N/A",
      "processCapability": "Low|Medium|High",
      "statisticalValidity": false,
      "dmaic": {{
        "define": {{
          "problemStatement": "string — max 2 sentences, evidence-based",
          "ctqs": ["string"],
          "financialExposure": {{"value": 0, "unit": "$"}}
        }},
        "measure": {{
          "baselineMetrics": ["string"],
          "dataConfidence": 0.7
        }},
        "analyze": {{
          "rootCauses": [{{"cause": "string", "confidence": 0.7}}],
          "correlations": ["string"]
        }},
        "improve": {{
          "recommendedActions": ["string"],
          "expectedSigmaLift": "string"
        }},
        "control": {{
          "controlPlan": ["string"],
          "monitoringKPIs": ["string"]
        }}
      }}
    }},

    "findings": [
      {{
        "finding": "string — specific, quantified finding from the document",
        "severity": "high|medium|low",
        "source_reference": "section/page reference",
        "financial_impact": "string or null",
        "recommended_action": "string"
      }}
    ],

    "risks": [
      {{
        "risk": "string",
        "severity": "High|Medium|Low",
        "probability": "High|Medium|Low",
        "financial_impact": "string",
        "mitigation": "string"
      }}
    ],

    "predictive": {{
      "forecast": [
        {{
          "metric": "string",
          "risk": "high|medium|low",
          "timeframe": "30d|90d|1y",
          "confidence": 0.6
        }}
      ],
      "whatIfScenarios": [
        {{
          "action": "string",
          "impact": "string",
          "financialDelta": 0
        }}
      ]
    }},

    "insights": {{
      "summary": "string",
      "trends": ["string"],
      "alerts": [
        {{
          "type": "warning|error|info|success",
          "message": "string",
          "severity": "high|medium|low",
          "action": "string"
        }}
      ]
    }},

    "explainability": {{
      "whyThisConclusion": ["string"],
      "dataUsed": ["string"],
      "assumptions": ["string"],
      "limitations": ["string"]
    }}
  }},

  "meta": {{
    "confidenceOverall": 0.75,
    "decisionReadinessScore": 0.7
  }}
}}

RULES:
- Use KPI values already extracted in stage 1 — do NOT re-invent numbers
- Every finding/risk must reference a specific data point from the document
- DMAIC must be evidence-based — cite KPIs, not generic advice
- Return ONLY valid JSON
"""


# ---------------------------------------------------------------------------
# Stage 3 — Recommendations
# ---------------------------------------------------------------------------

_S3_SYSTEM = """\
You are an Operations Excellence advisor for Oil & Gas.
Your job: produce KPI-anchored, financially-quantified recommendations.
Return STRICT JSON only.
"""

_S3_PROMPT_TEMPLATE = """\
EXTRACTED KPIs:
{kpis_json}

DMAIC SUMMARY:
{dmaic_summary}

TASK: Generate 5–12 specific, actionable recommendations. Each MUST reference
at least one KPI and include financial impact. Return this JSON structure only.

{{
  "recommendations": [
    {{
      "id": "rec_001",
      "title": "string — precise, tied to measurable KPI",
      "category": "cost|efficiency|performance|risk|quality",
      "impact": "high|medium|low",
      "priority": "high|medium|low",
      "confidence": 0.75,
      "kpi_id": "kpi_xxx — must match an extracted KPI id",
      "baseline": "current KPI value with unit",
      "target": "target KPI value with unit",
      "financial_impact": "string — e.g. $500K annual saving",
      "roi": 180,
      "paybackPeriod": "8 months",
      "riskIfIgnored": "string — consequence of inaction",
      "description": "string — evidence-backed, specific",
      "implementation": "string — how to do it",
      "decision_traceability": {{
        "data_sources": ["string — specific source"],
        "analytical_methods": ["string — method used"],
        "supporting_evidence": ["string — quantified evidence"]
      }},
      "action_management": {{
        "task_title": "string — imperative verb, actionable",
        "owner": "string — role (e.g. Maintenance Lead)",
        "kpi": "string — KPI impacted",
        "target_value": "string — quantified target",
        "deadline": "string — time-bound",
        "priority": "high|medium|low",
        "status": "Open"
      }},
      "tags": ["string"],
      "actionable": true,
      "approvalStatus": "proposed",
      "use_case": "Production Optimization|Asset Reliability|Drilling Performance|HSE|Refinery / Process Optimization"
    }}
  ]
}}

RULES:
- Every recommendation MUST have a valid kpi_id from the extracted KPI pool
- financial_impact must be quantified (not vague)
- action_management.owner must be a role, NOT a person's name
- action_management.deadline must be time-bound ("30 days", "Q2 2026")
- Return ONLY valid JSON
"""


# ---------------------------------------------------------------------------
# Stage 4 — Final Assembly (CEO/Manager/Boardroom views)
# ---------------------------------------------------------------------------

_S4_SYSTEM = """\
You are the TransIQ executive intelligence engine for Oil & Gas leadership.
Given the complete analysis, produce decision-ready executive views.
Return STRICT JSON only. Write for C-suite — decisive, quantified, no jargon.
"""

_S4_PROMPT_TEMPLATE = """\
ANALYSIS SUMMARY:
{analysis_summary}

TOP KPIs (for reference):
{top_kpis_json}

TASK: Build executive views. Return this JSON structure only.

{{
  "ceo_view": {{
    "decisions": [
      {{"title": "max 8 words, action verb first", "impact": "quantified $, % or KPI", "urgency": "high|medium|low"}},
      {{"title": "...", "impact": "...", "urgency": "..."}},
      {{"title": "...", "impact": "...", "urgency": "..."}}
    ],
    "risks": [
      {{"title": "max 8 words", "severity": "High|Medium|Low", "financial_impact": "quantified"}},
      {{"title": "...", "severity": "...", "financial_impact": "..."}},
      {{"title": "...", "severity": "...", "financial_impact": "..."}}
    ],
    "actions": [
      {{"title": "imperative verb, max 8 words", "owner": "role", "timeline": "time-bound"}},
      {{"title": "...", "owner": "...", "timeline": "..."}},
      {{"title": "...", "owner": "...", "timeline": "..."}}
    ]
  }},

  "manager_view": {{
    "dmaic": {{
      "define": "problem statement + financial exposure, 1-2 sentences",
      "measure": "baseline metrics + data confidence, 1-2 sentences",
      "analyze": "top root causes with confidence, 1-2 sentences",
      "improve": "recommended actions + sigma lift, 1-2 sentences",
      "control": "monitoring plan + tracked KPIs, 1-2 sentences"
    }},
    "recommendations": [
      {{"title": "string", "impact": "quantified", "timeline": "time-bound", "priority": "high|medium|low"}}
    ],
    "kpi_tracking": [
      {{"name": "string", "current": "string", "target": "string", "status": "on-track|at-risk|off-track"}}
    ]
  }},

  "boardroom_mode": {{
    "executive_summary": "3-5 sentences: situation, problem+impact, root cause, recommendation, expected outcome",
    "slides": {{
      "summary": ["bullet max 10 words"],
      "decisions": ["Decision: [action] → [impact]"],
      "risks": ["Risk: [threat] | Severity: [H/M/L] | Mitigation: [action]"],
      "actions": ["[Action] | Owner: [role] | By: [deadline]"],
      "kpi_impact": ["[KPI]: [current] → [target] ([direction] [%])"]
    }}
  }},

  "engineer_view": {{
    "data_references": ["string — specific dataset or section"],
    "models": ["string — method with metric e.g. Regression R²=0.78"],
    "root_cause_analysis": ["string — detailed causal chain"],
    "failure_modes": [
      {{"cause": "string", "probability": 0.0, "detection": "string", "mitigation": "string"}}
    ],
    "assumptions": ["string"]
  }}
}}

RULES:
- ceo_view: exactly 3 decisions, 3 risks, 3 actions — max 8 words per title
- NEVER write "insights suggest" or "data indicates" — ALWAYS use "Decision:", "Action Required:", "Risk:"
- boardroom executive_summary: exactly 3-5 sentences
- Return ONLY valid JSON
"""


# ---------------------------------------------------------------------------
# Stage 5 — Multi-Rig Final Report Validation
# ---------------------------------------------------------------------------

_S5_SYSTEM = """\
You are validating a structured industrial report generated from a large document.
You MUST ONLY use provided data. DO NOT infer or generalize missing information.
Return STRICT JSON only — no markdown, no explanation.
"""

_S5_PROMPT_TEMPLATE = """\
RIG-LEVEL SUMMARIES (each includes findings, KPIs, risks with source_pages):
{rig_summaries_json}

TASK: Generate a FINAL VALIDATED REPORT with STRICT constraints.

RULES (MANDATORY):
1. You MUST ONLY use provided data
2. DO NOT infer or generalize missing information
3. EVERY insight MUST include source_pages and supporting_rigs
4. If data is insufficient, explicitly say: "INSUFFICIENT DATA"
5. DO NOT merge unrelated insights
6. DO NOT summarize without evidence
7. Preserve quantitative values exactly (no rounding unless given)

Return this exact JSON structure — nothing else:

{{
  "executive_summary": [
    {{
      "insight": "string — evidence-backed, specific",
      "supporting_rigs": ["rig_id or rig_name"],
      "source_pages": [1, 2]
    }}
  ],
  "kpis": [
    {{
      "name": "string — exact KPI name from source",
      "value": 0,
      "unit": "string",
      "supporting_rigs": ["rig_id or rig_name"],
      "source_pages": [1]
    }}
  ],
  "risks": [
    {{
      "risk": "string — specific risk from source data",
      "severity": "High|Medium|Low",
      "supporting_rigs": ["rig_id or rig_name"],
      "source_pages": [1]
    }}
  ],
  "data_quality": {{
    "missing_data_sections": ["string — sections with insufficient data"],
    "conflicts_detected": ["string — conflicting values across rigs"]
  }}
}}

RULES:
- EVERY item in executive_summary, kpis, and risks MUST have non-empty supporting_rigs AND source_pages
- If a KPI value cannot be traced to source_pages, mark it in missing_data_sections instead
- If two rigs report conflicting values for the same metric, list in conflicts_detected
- Return ONLY valid JSON
"""


# ---------------------------------------------------------------------------
# JSON safety wrapper
# ---------------------------------------------------------------------------

def _safe_llm_call(
    client: Any,
    model: str,
    system_instruction: str,
    prompt: str,
    stage_name: str,
    max_retries: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    Call Gemini with retry + JSON reinforcement.
    Returns parsed dict or None on failure.
    """
    from google.genai.types import Content, Part, GenerateContentConfig

    json_reinforcement = (
        "\n\nCRITICAL: Your ENTIRE response must be a single valid JSON object. "
        "No markdown, no code fences, no explanation. ONLY the JSON."
    )

    for attempt in range(1, max_retries + 1):
        retry_prompt = prompt if attempt == 1 else prompt + json_reinforcement
        try:
            config = GenerateContentConfig(
                temperature=0.15,
                system_instruction=system_instruction,
                response_mime_type="application/json",
            )
            contents = [Content(role="user", parts=[Part(text=retry_prompt)])]
            resp = client.models.generate_content(model=model, contents=contents, config=config)
            raw = (resp.text or "").strip()

            if not raw:
                logger.warning("%s stage: empty response (attempt %d)", stage_name, attempt)
                continue

            # Try direct parse
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass

            # Fallback: extract outermost JSON object
            m = re.search(r"(\{.*\})", raw, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    logger.warning("%s stage: JSON parse failed (attempt %d)", stage_name, attempt)

        except Exception as exc:
            err_str = str(exc)
            if "503" in err_str and attempt < max_retries:
                import time
                wait = 2 ** attempt
                logger.warning("%s stage: 503 error — retrying in %ds", stage_name, wait)
                time.sleep(wait)
            else:
                logger.error("%s stage error (attempt %d): %s", stage_name, attempt, exc)

    logger.error("%s stage: all %d attempts failed", stage_name, max_retries)
    return None


# ---------------------------------------------------------------------------
# Chart generator (deterministic, no LLM)
# ---------------------------------------------------------------------------

def _generate_charts_from_kpis(kpis: List[Dict]) -> List[Dict]:
    """Build 5 charts deterministically from the KPI pool."""
    if not kpis:
        return []

    charts: List[Dict] = []

    # Chart 1 — KPI Performance Bar Chart
    top = kpis[:10]
    charts.append({
        "id": "chart_kpi_bar",
        "type": "BarChart",
        "title": "KPI Performance Overview",
        "size": "full",
        "chartConfig": {
            "value": {"label": "Actual", "color": "#3b82f6"},
            "target": {"label": "Target", "color": "#10b981"},
        },
        "data": [
            {
                "name": k.get("title", "")[:20],
                "value": k.get("value", 0),
                "target": k.get("target", 0),
            }
            for k in top
        ],
    })

    # Chart 2 — Category Distribution Pie
    cat_counts: Dict[str, int] = {}
    for k in kpis:
        cat = (k.get("category") or "other").lower()
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    if cat_counts:
        COLOR_MAP = {
            "financial": "#10b981", "safety": "#ef4444",
            "operations": "#3b82f6", "efficiency": "#8b5cf6",
            "reliability": "#f59e0b", "quality": "#06b6d4",
        }
        charts.append({
            "id": "chart_category_pie",
            "type": "PieChart",
            "title": "KPI Distribution by Category",
            "size": "half",
            "chartConfig": {cat: {"label": cat.capitalize(), "color": COLOR_MAP.get(cat, "#6b7280")} for cat in cat_counts},
            "data": [{"name": cat.capitalize(), "value": cnt} for cat, cnt in cat_counts.items()],
        })

    # Chart 3 — Trend Distribution Radar
    trend_data: Dict[str, int] = {"Improving": 0, "Stable": 0, "Deteriorating": 0}
    for k in kpis:
        t = (k.get("trend") or "stable").lower()
        if t == "improving":
            trend_data["Improving"] += 1
        elif t in ("deteriorating", "down"):
            trend_data["Deteriorating"] += 1
        else:
            trend_data["Stable"] += 1
    charts.append({
        "id": "chart_trend_radar",
        "type": "RadarChart",
        "title": "KPI Trend Distribution",
        "size": "half",
        "chartConfig": {
            "count": {"label": "Count", "color": "#3b82f6"},
        },
        "data": [{"subject": k, "count": v} for k, v in trend_data.items()],
    })

    # Chart 4 — Risk Score Bar (top 8 by risk)
    risk_kpis = sorted(
        [k for k in kpis if k.get("riskScore")],
        key=lambda x: float(x.get("riskScore", 0)),
        reverse=True,
    )[:8]
    if risk_kpis:
        charts.append({
            "id": "chart_risk_bar",
            "type": "BarChart",
            "title": "KPI Risk Score Ranking",
            "size": "full",
            "chartConfig": {
                "riskScore": {"label": "Risk Score", "color": "#ef4444"},
            },
            "data": [
                {"name": k.get("title", "")[:20], "riskScore": k.get("riskScore", 0)}
                for k in risk_kpis
            ],
        })

    # Chart 5 — Financial Impact Area Chart
    fin_kpis = sorted(
        [k for k in kpis if k.get("financialImpactScore")],
        key=lambda x: float(x.get("financialImpactScore", 0)),
        reverse=True,
    )[:8]
    if fin_kpis:
        charts.append({
            "id": "chart_financial_area",
            "type": "AreaChart",
            "title": "Financial Impact Score by KPI",
            "size": "full",
            "chartConfig": {
                "financialImpactScore": {"label": "Financial Impact", "color": "#10b981"},
            },
            "data": [
                {"name": k.get("title", "")[:20], "financialImpactScore": k.get("financialImpactScore", 0)}
                for k in fin_kpis
            ],
        })

    return charts


# ---------------------------------------------------------------------------
# Rig-summary builder (aggregates KPIs/findings/risks by rig for Stage 5)
# ---------------------------------------------------------------------------

def _build_rig_summaries_for_validation(
    kpis: List[Dict],
    findings: List[Dict],
    risks: List[Dict],
) -> List[Dict]:
    """Group KPIs, findings, and risks by rig_name for Stage 5 validation."""
    rigs: Dict[str, Dict] = {}

    for kpi in kpis:
        src = kpi.get("source_reference") or {}
        rig = src.get("rig_name") or "unknown"
        pages = src.get("source_pages") or []
        if rig not in rigs:
            rigs[rig] = {"rig_name": rig, "kpis": [], "findings": [], "risks": [], "source_pages": set()}
        rigs[rig]["kpis"].append({
            "name": kpi.get("title", ""),
            "value": kpi.get("value"),
            "unit": kpi.get("unit", ""),
            "source_pages": pages,
        })
        if isinstance(pages, list):
            rigs[rig]["source_pages"].update(pages)

    for finding in findings:
        rig = finding.get("source_reference") or "unknown"
        pages = finding.get("source_pages") or []
        # Try to match to an existing rig key
        matched = rig if rig in rigs else "unknown"
        if matched not in rigs:
            rigs[matched] = {"rig_name": matched, "kpis": [], "findings": [], "risks": [], "source_pages": set()}
        rigs[matched]["findings"].append({
            "finding": finding.get("finding", ""),
            "severity": finding.get("severity", ""),
            "source_pages": pages,
        })
        if isinstance(pages, list):
            rigs[matched]["source_pages"].update(pages)

    for risk in risks:
        pages = risk.get("source_pages") or []
        rig = risk.get("rig_name") or "unknown"
        matched = rig if rig in rigs else "unknown"
        if matched not in rigs:
            rigs[matched] = {"rig_name": matched, "kpis": [], "findings": [], "risks": [], "source_pages": set()}
        rigs[matched]["risks"].append({
            "risk": risk.get("risk", ""),
            "severity": risk.get("severity", ""),
            "source_pages": pages,
        })
        if isinstance(pages, list):
            rigs[matched]["source_pages"].update(pages)

    # Convert sets to sorted lists for JSON serialisation
    result = []
    for data in rigs.values():
        data["source_pages"] = sorted(data["source_pages"])
        result.append(data)
    return result


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

def run_pipeline(
    combined_content: str,
    num_files: int,
    source_type: str,
    client: Any,
    *,
    content_limit: int = 500_000,
) -> Dict[str, Any]:
    """
    Run the 4-stage intelligence pipeline and return the final assembled result.

    Parameters
    ----------
    combined_content : str
        Full document text (already compressed/chunked by caller).
    num_files : int
        Number of source files (for meta).
    source_type : str
        "PDF", "CSV", "XLS", etc.
    client : google.genai.Client
        Initialized Gemini client.
    content_limit : int
        Maximum chars to send per stage (reduces token cost).
    """
    from app.intelligence.financial_engine import compute_kpi_financial_scores, compute_portfolio_summary
    from app.intelligence.validation import validate_kpis, validate_recommendations, validate_findings
    from app.intelligence.esg_engine import build_esg_view
    from app.intelligence.drilling_engine import build_drilling_view

    ingested_at = datetime.datetime.utcnow().isoformat() + "Z"
    report_id = str(uuid.uuid4())

    # Trim content per stage to control token cost
    ctx_for_stage = combined_content[:content_limit]
    stage1_context = build_context(ctx_for_stage, max_output_chars=150_000)
    reduction_ratio = (
      1 - (len(stage1_context) / len(ctx_for_stage))
      if len(ctx_for_stage) > 0 else 0.0
    )
    logger.info(
      "Context builder effectiveness: original_chars=%d reduced_chars=%d reduction_ratio=%.4f",
      len(ctx_for_stage),
      len(stage1_context),
      reduction_ratio,
    )

    # ── STAGE 1: KPI Extraction ──────────────────────────────────────────────
    logger.info("Pipeline Stage 1: KPI Extraction")
    _filtered_terms = filter_glossary(stage1_context, DOMAIN_GLOSSARY, _TERM_INDEX)
    domain_terms = format_for_prompt(_filtered_terms)
    domain_terms_section = (
        f"\nDOMAIN TERMINOLOGY (use these exact names in output fields):\n{domain_terms}\n"
        if domain_terms else ""
    )
    prompt_without_glossary = _S1_PROMPT_TEMPLATE.format(content=stage1_context, domain_terms_section="")
    prompt_with_glossary = _S1_PROMPT_TEMPLATE.format(
      content=stage1_context,
      domain_terms_section=domain_terms_section,
    )
    logger.info(
      "Stage 1 instrumentation: original_content_chars=%d stage1_context_chars=%d selected_terms=%d domain_terms_chars=%d prompt_chars_before=%d prompt_chars_after=%d est_tokens_before=%d est_tokens_after=%d",
      len(ctx_for_stage),
      len(stage1_context),
      len(_filtered_terms),
      len(domain_terms),
      len(prompt_without_glossary),
      len(prompt_with_glossary),
      len(prompt_without_glossary) // 4,
      len(prompt_with_glossary) // 4,
    )
    logger.info("Glossary pre-filter: %d terms injected into Stage 1", len(_filtered_terms))
    s1_prompt = prompt_with_glossary
    s1_result = _safe_llm_call(client, _CHEAP_MODEL, _S1_SYSTEM, s1_prompt, "Stage1-KPI")

    raw_kpis: List[Dict] = []
    if s1_result and "kpis" in s1_result:
        raw_kpis = s1_result["kpis"]
        logger.info("Stage 1: extracted %d raw KPIs", len(raw_kpis))
    else:
        logger.warning("Stage 1: KPI extraction returned no results")

    # Validate + deduplicate
    validated_kpis = validate_kpis(raw_kpis)

    # Apply deterministic financial scoring
    enriched_kpis = compute_kpi_financial_scores(validated_kpis)

    # Apply KPI engine ranking
    try:
        from app.kpi_engine import process_kpis
        enriched_kpis = process_kpis(enriched_kpis)
    except Exception as e:
        logger.warning("KPI engine scoring skipped: %s", e)

    kpis_json = json.dumps(enriched_kpis[:20], indent=2)  # send top 20 to Stage 2

    # ── STAGE 2: DMAIC + Analytics ───────────────────────────────────────────
    logger.info("Pipeline Stage 2: DMAIC Analysis")
    s2_prompt = _S2_PROMPT_TEMPLATE.format(
        content=ctx_for_stage[:40_000],  # shorter for the smart model
        kpis_json=kpis_json,
    )
    s2_result = _safe_llm_call(client, _SMART_MODEL, _S2_SYSTEM, s2_prompt, "Stage2-DMAIC")

    dashboard_base: Dict = {}
    auto_classification: Dict = {}
    meta_from_stage2: Dict = {}

    if s2_result:
        dashboard_base = s2_result.get("dashboard", {})
        auto_classification = s2_result.get("autoClassification", {})
        meta_from_stage2 = s2_result.get("meta", {})
        logger.info("Stage 2: DMAIC analysis complete")
    else:
        logger.warning("Stage 2: DMAIC returned no results — using empty skeleton")

    # Extract and validate findings
    raw_findings = dashboard_base.get("findings", [])
    findings = validate_findings(raw_findings)

    # Build DMAIC summary for Stage 3
    dmaic = dashboard_base.get("sixSigma", {}).get("dmaic", {})
    dmaic_summary = (
        f"Problem: {dmaic.get('define', {}).get('problemStatement', 'N/A')}\n"
        f"Root causes: {dmaic.get('analyze', {}).get('rootCauses', [])}\n"
        f"Improve: {dmaic.get('improve', {}).get('recommendedActions', [])}\n"
        f"Risks: {[r.get('risk') for r in dashboard_base.get('risks', [])[:3]]}"
    )

    # ── STAGE 3: Recommendations ─────────────────────────────────────────────
    logger.info("Pipeline Stage 3: Recommendations")
    s3_prompt = _S3_PROMPT_TEMPLATE.format(
        kpis_json=kpis_json,
        dmaic_summary=dmaic_summary,
    )
    s3_result = _safe_llm_call(client, _CHEAP_MODEL, _S3_SYSTEM, s3_prompt, "Stage3-Recs")

    raw_recs: List[Dict] = []
    if s3_result and "recommendations" in s3_result:
        raw_recs = s3_result["recommendations"]
        logger.info("Stage 3: generated %d recommendations", len(raw_recs))

    validated_recs = validate_recommendations(raw_recs, enriched_kpis)

    # ── STAGE 4: Executive Views ─────────────────────────────────────────────
    logger.info("Pipeline Stage 4: Executive Assembly")
    analysis_summary = (
        f"Report type: {auto_classification.get('reportType', [])}\n"
        f"Overall confidence: {meta_from_stage2.get('confidenceOverall', 0.7)}\n"
        + dmaic_summary
        + f"\nTop recommendations: {[r.get('title') for r in validated_recs[:5]]}\n"
        f"Alerts: {[a.get('message') for a in dashboard_base.get('insights', {}).get('alerts', [])[:3]]}"
    )

    top_kpis_for_s4 = json.dumps(enriched_kpis[:10], indent=2)
    s4_prompt = _S4_PROMPT_TEMPLATE.format(
        analysis_summary=analysis_summary,
        top_kpis_json=top_kpis_for_s4,
    )
    s4_result = _safe_llm_call(client, _SMART_MODEL, _S4_SYSTEM, s4_prompt, "Stage4-Exec")

    ceo_view: Dict = {}
    manager_view: Dict = {}
    boardroom_mode: Dict = {}
    engineer_view: Dict = {}

    if s4_result:
        ceo_view = s4_result.get("ceo_view", {})
        manager_view = s4_result.get("manager_view", {})
        boardroom_mode = s4_result.get("boardroom_mode", {})
        engineer_view = s4_result.get("engineer_view", {})

    # ── STAGE 5: Multi-Rig Final Report Validation ───────────────────────────
    logger.info("Pipeline Stage 5: Multi-Rig Validation")
    rig_summaries = _build_rig_summaries_for_validation(
        enriched_kpis, findings, dashboard_base.get("risks", []),
    )
    validated_report: Dict = {}
    if rig_summaries:
        s5_prompt = _S5_PROMPT_TEMPLATE.format(
            rig_summaries_json=json.dumps(rig_summaries, indent=2)[:80_000],
        )
        s5_result = _safe_llm_call(client, _CHEAP_MODEL, _S5_SYSTEM, s5_prompt, "Stage5-Validation")
        if s5_result:
            validated_report = s5_result
            logger.info(
                "Stage 5: validated report — %d insights, %d kpis, %d risks",
                len(validated_report.get("executive_summary", [])),
                len(validated_report.get("kpis", [])),
                len(validated_report.get("risks", [])),
            )
        else:
            logger.warning("Stage 5: validation returned no results")
    else:
        logger.info("Stage 5: skipped — no rig-level data to validate")

    # ── Post-processing: ESG & Drilling ─────────────────────────────────────
    logger.info("Post-processing: ESG + Drilling analytics")
    esg_view = build_esg_view(enriched_kpis)
    drilling_view = build_drilling_view(enriched_kpis)
    portfolio_summary = compute_portfolio_summary(enriched_kpis)

    # ── Six Sigma Engine (deterministic — replaces LLM-generated sixSigma) ─
    logger.info("Post-processing: Six Sigma deterministic engine")
    try:
        from app.six_sigma import run_six_sigma
        six_sigma_result = run_six_sigma(enriched_kpis)
        logger.info(
            "Six Sigma engine: sigma=%s, %d CTQs, %d root causes",
            six_sigma_result.get("sigmaNumeric"),
            len(six_sigma_result.get("ctq", [])),
            len(six_sigma_result.get("rootCauses", [])),
        )
    except Exception as ss_err:
        logger.warning("Six Sigma engine skipped: %s", ss_err)
        six_sigma_result = dashboard_base.get("sixSigma", {})

    # ── Charts (deterministic) ───────────────────────────────────────────────
    charts = _generate_charts_from_kpis(enriched_kpis)

    # ── Final Assembly ───────────────────────────────────────────────────────
    result: Dict[str, Any] = {
        "meta": {
            "reportId": report_id,
            "ingestedAt": ingested_at,
            "sourceType": source_type,
            "numFiles": num_files,
            "confidenceOverall": meta_from_stage2.get("confidenceOverall", 0.75),
            "decisionReadinessScore": meta_from_stage2.get("decisionReadinessScore", 0.70),
            "pipelineVersion": "2.0-multi-stage",
        },

        "autoClassification": auto_classification or {
            "reportType": ["unknown"],
            "assetScope": "unknown",
            "timeHorizon": "unknown",
            "decisionLevel": "unknown",
            "confidence": 0.5,
        },

        "dashboard": {
            "title": dashboard_base.get("title", f"Operations Analysis — {num_files} file(s)"),
            "description": dashboard_base.get("description", "TransIQ multi-stage intelligence analysis"),
            "sixSigma": six_sigma_result,
            "kpis": enriched_kpis,
            "charts": charts,
            "tables": [],
            "findings": findings,
            "risks": dashboard_base.get("risks", []),
            "optimizationSuggestions": validated_recs,
            "predictive": dashboard_base.get("predictive", {"forecast": [], "whatIfScenarios": []}),
            "insights": dashboard_base.get("insights", {"summary": "", "trends": [], "alerts": []}),
            "explainability": dashboard_base.get("explainability", {
                "whyThisConclusion": [], "dataUsed": [], "assumptions": [], "limitations": []
            }),
        },

        "ceo_view": ceo_view,
        "manager_view": manager_view,
        "boardroom_mode": boardroom_mode,
        "engineer_view": engineer_view,

        "intelligence": {
            "portfolio_summary": portfolio_summary,
            "esg": esg_view,
            "drilling": drilling_view,
        },

        "validated_report": validated_report,
    }

    logger.info(
        "Pipeline complete: %d KPIs, %d recs, %d charts, %d findings, validated=%s",
        len(enriched_kpis), len(validated_recs), len(charts), len(findings),
        bool(validated_report),
    )
    return result
