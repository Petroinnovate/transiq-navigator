from fastapi import APIRouter, UploadFile, Depends
from google import genai
from google.genai.types import Content, Part, GenerateContentConfig
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF
import re
import os
import json
import pandas as pd
import time
import math
import logging
from types import SimpleNamespace

# Configure logging
logger = logging.getLogger(__name__)

# Multi-Agent Orchestrator (lazy import to avoid circular deps at module load)
def _get_orchestrator(llm_client):
    from agents.orchestrators.orchestrator import AgentOrchestrator
    return AgentOrchestrator(llm_client)

import pipelines.processing.chunking.chunker as chunker
from services.supabase.supabase_client import get_current_user_optional
from services.supabase.supabase_service import supabase_service
from services.vector_store.indexing.vector_storage import get_vector_service
from services.cache.cache_service import get_cache_service
from core.config.settings import settings
from services.vector_store.retrieval.hybrid_retrieval import get_hybrid_retrieval, HybridRetrieval, compress_chunks as _compress_chunks
from pipelines.processing.section_analyzer import generate_full_report_analysis
from pipelines.monitoring.pipeline_diagnostics import PipelineDiagnostics, DIAGNOSTICS_ENABLED
from scripts.document_manifest import DocumentManifest

# Initialize Gemini client only if API key is available from settings
_MODEL_FALLBACKS = {
    "gemini-2.5-flash": ["gemini-2.5-flash"],
    "gemini-2.0-flash": ["gemini-2.5-flash"],
}


class _GeminiModelsProxy:
    def __init__(self, api_keys: list[str]):
        self._clients = [genai.Client(api_key=key) for key in api_keys]

    def _candidate_models(self, requested_model: str) -> list[str]:
        return _MODEL_FALLBACKS.get(requested_model, [requested_model, "gemini-2.5-flash"])

    def generate_content(self, model: str, contents, config=None):
        last_error = None
        for key_index, gemini_client in enumerate(self._clients, start=1):
            for candidate_model in self._candidate_models(model):
                try:
                    response = gemini_client.models.generate_content(
                        model=candidate_model,
                        contents=contents,
                        config=config,
                    )
                    if candidate_model != model:
                        logger.info(
                            "Gemini fallback succeeded: requested_model=%s fallback_model=%s key_index=%d",
                            model,
                            candidate_model,
                            key_index,
                        )
                    return response
                except Exception as exc:
                    last_error = exc
                    err_str = str(exc)
                    is_retryable = (
                        "API_KEY_INVALID" in err_str
                        or "API Key not found" in err_str
                        or "RESOURCE_EXHAUSTED" in err_str
                        or "429" in err_str
                        or "NOT_FOUND" in err_str
                        or "404" in err_str
                    )
                    if is_retryable:
                        logger.warning(
                            "Gemini request failed: requested_model=%s candidate_model=%s key_index=%d error=%s",
                            model,
                            candidate_model,
                            key_index,
                            err_str.splitlines()[0],
                        )
                        continue
                    raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("No Gemini API keys configured")


class _GeminiClientWrapper:
    def __init__(self, api_keys: list[str]):
        self.models = _GeminiModelsProxy(api_keys)


gemini_api_keys = settings.get_gemini_api_keys()
if gemini_api_keys:
    client = _GeminiClientWrapper(gemini_api_keys)
else:
    client = None
    logger.warning("GEMINI_API_KEY not set. AI features will be disabled.")


def validate_gemini_configuration() -> None:
    """Fail fast with a clear error if Gemini is required but not configured."""
    settings.require_gemini_api_key()

# Create routers
processing_router = APIRouter(prefix="", tags=["document-processing"])
system_router = APIRouter(prefix="/system", tags=["system"])
v2_compat_router = APIRouter(prefix="/api/v2", tags=["v2-compatibility"])


def split_string_preserve_words(text: str, n: int) -> list[str]:
    words = text.split()
    avg_words = math.ceil(len(words) / n)

    chunks = []
    for i in range(0, len(words), avg_words):
        chunk = " ".join(words[i : i + avg_words])
        chunks.append(chunk)

    # Ensure exactly n chunks (pad last ones if needed)
    while len(chunks) < n:
        chunks.append("")

    return chunks


def generate_chart_response(content: List[str], num_files: int, source_type: str = "UNKNOWN") -> Dict[str, Any]:
    """
    Main AI analysis entry point.

    Uses the multi-stage intelligence pipeline (app/intelligence/pipeline.py)
    instead of a single monolithic prompt.  Falls back to the legacy monolithic
    approach only if the pipeline module is not importable.

    The pipeline runs four focused LLM stages:
      Stage 1 — KPI extraction        (gemini-2.5-flash, cheap)
      Stage 2 — DMAIC / analytics     (gemini-2.5-flash, smart)
      Stage 3 — Recommendations       (gemini-2.5-flash, cheap)
      Stage 4 — Executive views       (gemini-2.5-flash, smart)

    Post-processing is fully deterministic: financial scoring, ESG
    classification, drilling analytics, KPI validation and deduplication.
    """
    if not client:
        raise ValueError(
            "GEMINI_API_KEY not set. Please set the GEMINI_API_KEY environment variable."
        )

    # ── Compress chunks ───────────────────────────────────────────────────────
    try:
        compressed = _compress_chunks(content, max_total_chars=500_000)
        combined_content = "\n\n".join(compressed) if compressed else "\n\n".join(content)
    except Exception as _ce:
        logger.warning("Chunk compression skipped: %s", _ce)
        combined_content = "\n\n".join(content)

    # ── Attempt multi-stage pipeline ─────────────────────────────────────────
    try:
        from pipelines.inference.intelligence_pipeline import run_pipeline
        logger.info("Using multi-stage intelligence pipeline")
        result = run_pipeline(combined_content, num_files, source_type, client)

        # Apply smart KPI selection on top of pipeline output so legacy
        # widget_mapper / fix_kpi_values code still gets a curated pool.
        dashboard_kpis = result.get("dashboard", {}).get("kpis", [])
        if dashboard_kpis:
            curated = select_smart_kpis(dashboard_kpis)
            if curated:
                try:
                    from features import process_kpis, map_kpis_to_widgets
                    scored = process_kpis(curated)
                    widgets = map_kpis_to_widgets(scored)
                    result["dashboard"]["kpis"] = scored
                    result["dashboard"]["widgets"] = widgets
                except Exception as _ke:
                    logger.warning("KPI engine post-process skipped: %s", _ke)
                    result["dashboard"]["kpis"] = curated

        return result

    except Exception as pipeline_err:
        logger.error("Pipeline failed — falling back to legacy monolithic prompt: %s", pipeline_err)

    # ─────────────────────────────────────────────────────────────────────────
    # LEGACY FALLBACK (original monolithic prompt — kept intact)
    # Only reached if the pipeline throws an unexpected exception.
    # ─────────────────────────────────────────────────────────────────────────
    import datetime
    ingested_at = datetime.datetime.utcnow().isoformat() + "Z"

    prompt_text = (
        """
Retrieved document chunks:
"""
        + combined_content
        + """
You are an AI Chief-of-Staff for Oil & Gas operations, an expert Six Sigma Black Belt, Data Analyst, and Business Intelligence Architect.

Your task is to auto-understand any report type (Operations, HSE, Finance, Audit, Strategy), apply Six Sigma rigor, quantify financial & risk impact, and produce decision-ready intelligence for top management.

Do NOT assume data.
Use only information directly stated or implied in the chunks.
If data is weak, reduce confidence scores.

------------------------------
OUTPUT FORMAT (MANDATORY)
------------------------------

Return the final output strictly in the following JSON schema:

{
  "meta": {
    "reportId": "string (generate unique ID)",
    "ingestedAt": "ISO-8601 timestamp",
    "sourceType": "PDF|DOCX|XLS|CSV|DB|API|SCAN",
    "confidenceOverall": 0.0-1.0,
    "decisionReadinessScore": 0.0-1.0
  },

  "autoClassification": {
    "reportType": ["operations", "hse", "finance", "audit", "strategy"],
    "assetScope": "well|field|plant|pipeline|enterprise",
    "timeHorizon": "operational|tactical|strategic",
    "decisionLevel": "operations|management|board",
    "confidence": 0.0-1.0
  },

  "dashboard": {
    "title": "Dashboard Title",
    "description": "Brief description of what the dashboard represents",

    "sixSigma": {
      "methodology": "DMAIC|DMADV",
      "dmaic": {
        "define": {
          "problemStatement": "string",
          "ctqs": ["string"],
          "financialExposure": { "value": number, "unit": "$|₹" }
        },
        "measure": {
          "baselineMetrics": ["string"],
          "dataConfidence": 0.0-1.0
        },
        "analyze": {
          "rootCauses": [
            { "cause": "string", "confidence": 0.0-1.0 }
          ],
          "correlations": ["string"]
        },
        "improve": {
          "recommendedActions": ["string"],
          "expectedSigmaLift": "string"
        },
        "control": {
          "controlPlan": ["string"],
          "monitoringKPIs": ["string"]
        }
      },
      "dmadv": {
        "define": {
          "projectGoal": "string",
          "customerNeeds": ["string"],
          "businessCase": "string",
          "scope": "string"
        },
        "measure": {
          "voiceOfCustomer": ["string"],
          "criticalToQuality": [{ "ctq": "string", "target": "string", "weight": "High|Medium|Low" }],
          "benchmarks": ["string"]
        },
        "analyze": {
          "gapAnalysis": "string",
          "designOptions": [{ "option": "string", "pros": ["string"], "cons": ["string"] }],
          "riskAssessment": [{ "risk": "string", "severity": "High|Medium|Low", "mitigation": "string" }]
        },
        "design": {
          "selectedApproach": "string",
          "detailedDesign": ["string"],
          "designFMEA": [{ "failureMode": "string", "effect": "string", "rpn": number }],
          "targetSpecifications": [{ "parameter": "string", "target": "string", "tolerance": "string" }]
        },
        "verify": {
          "verificationPlan": "string",
          "testResults": [{ "test": "string", "result": "Pass|Fail|Partial", "notes": "string" }],
          "pilotOutcome": "string",
          "deploymentReadiness": "Ready|Conditional|Not Ready"
        }
      },
      "sigmaLevel": "string",
      "defectRate": "string",
      "processCapability": "Low|Medium|High",
      "statisticalValidity": true|false
    },

    "kpis": [
      // AI KPI POOL — extract a COMPREHENSIVE pool of 15–50 KPIs.
      // Do NOT pre-filter to "top" metrics — the AI ranking engine decides what to display.
      // Cover ALL categories: Financial, Safety & Risk, Operations, Efficiency, Reliability, Supporting.
      //
      // TIER 1 – Financial Impact  (revenue loss, cost overrun, capex, EBITDA effect) → always include
      // TIER 2 – Safety & Risk     (NPT, incidents, near-misses, compliance failures)  → always include
      // TIER 3 – Core Operations   (production rate, throughput, availability, efficiency %) → include all found
      // TIER 4 – Supporting Metrics (personnel, counts, secondary rates)               → include all found
      //
      // RULES:
      // - Extract 15–50 KPIs (this is a POOL, not a display list — AI will filter downstream).
      // - Include secondary and hidden drivers — even weak signals matter for AI scoring.
      // - Include KPIs with targets wherever inferable (enables deviation scoring).
      // - Populate financialImpactScore, riskScore, deviationScore, trendScore (0-100 each)
      //   to help the AI ranking engine prioritize correctly.
      {
        "id": "string",
        "title": "string (concise, max 5 words)",
        "value": number (MUST BE ACTUAL CALCULATED NUMBER FROM DATA, NOT 0),
        "unit": "$|%|count|hrs|score|ft|days|bbl|mcf|psi",
        "target": number,
        "trend": "improving|deteriorating|stable",
        "change": "string",
        "changeType": "positive|negative|neutral",
        "confidence": 0.0-1.0,
        "owner": "Operations|HSE|Finance|Engineering|Safety",
        "linkedCTQ": "string",
        "icon": "dollar|users|activity|chart|trending",
        "color": "green|blue|purple|red|yellow",
        "priority": "tier1|tier2|tier3|tier4",
        "financialImpactScore": number (0-100),
        "riskScore": number (0-100),
        "deviationScore": number (0-100, 0=on-target 100=severely-off),
        "trendScore": number (0-100, 80+=deteriorating 60=improving 20=stable)
      }
    ],

    "charts": [
      {
        "id": "chart1",
        "type": "BarChart|LineChart|AreaChart|PieChart|RadarChart|RadialBarChart|ScatterChart|FunnelChart|SankeyChart",
        "title": "Chart title",
        "size": "full|half|third|quarter",
        "chartConfig": {...},
        "data": [...]
      }
    ],

    "tables": [
      {
        "id": "table1",
        "title": "Detailed Data Table",
        "columns": [...],
        "data": [],
        "pagination": true,
        "sortable": true
      }
    ],

    "optimizationSuggestions": [
      {
        "id": "string",
        "title": "string — precise, tied to a measurable KPI (e.g. Reduce NPT 15% — $1.2M annual loss, below P75 by 9%)",
        "category": "cost|efficiency|performance|risk|quality",
        "impact": "high|medium|low",
        "roi": number,
        "paybackPeriod": "months",
        "riskIfIgnored": "string",
        "savings": {
          "value": number,
          "unit": "$|₹",
          "percentage": "string",
          "timeframe": "annually|monthly|quarterly"
        },
        "description": "string — evidence-backed, no generic statements",
        "implementation": "string",
        "metrics": ["string"],
        "priority": "high|medium|low",
        "confidence": 0.0-1.0,
        "tags": ["string"],
        "actionable": true,
        "approvalStatus": "proposed|approved|implemented",
        "decision_traceability": {
          "data_sources": ["string — specific input with time range and data quality level: High/Medium/Low"],
          "analytical_methods": ["string — e.g. trend analysis R²=0.82, control charts, variance analysis"],
          "supporting_evidence": ["string — quantified finding, e.g. defect rate +8% YoY, $2.1M annual loss"]
        },
        "industry_benchmarking": {
          "median_comparison": "string — above|below|at par vs industry median",
          "top_quartile_comparison": "string — performance vs P75/P90",
          "peer_comparison": "string — vs peer assets if applicable, else state N/A",
          "performance_gap": "string — gap as % or absolute value"
        },
        "decision_confidence_index": {
          "score": "integer 0-100",
          "data_completeness": "string — score/25 and rationale",
          "model_confidence": "string — score/25 and rationale",
          "historical_accuracy": "string — score/25 and rationale",
          "variability": "string — score/25 and rationale",
          "explanation": "string — composite explanation and what would raise the score"
        },
        "assumptions_limitations": ["string — stated assumption or missing data flag"],
        "use_case": "Production Optimization|Asset Reliability|Drilling Performance|HSE|Refinery / Process Optimization",
        "action_management": {
          "task_title": "string — imperative, specific (e.g. Replace pump seals on Train-B)",
          "description": "string — what needs to be done and why",
          "owner": "string — role-based (e.g. Maintenance Lead, Production Manager, Process Engineer)",
          "kpi": "string — specific KPI impacted (e.g. Downtime %, OEE, MTBF, NPT)",
          "target_value": "string — quantified improvement (e.g. Reduce downtime from 8% to 4%)",
          "deadline": "string — time-bound (e.g. 30 days, Q2 2026, Before next turnaround)",
          "priority": "high|medium|low",
          "status": "Open"
        },
        "execution_plan": [
          "string — Step 1: tools/systems (SAP PM, SCADA, historian)",
          "string — Step 2: dependencies (shutdown window, approvals)",
          "string — Steps 3-6: specific domain actions (3-6 steps total)"
        ],
        "closed_loop_learning": {
          "predicted_impact": "string — quantified (e.g. -15% NPT, +$320K/year, OEE +4%)",
          "measurement_plan": "string — data source + frequency (e.g. PI Historian daily, SAP PM monthly)",
          "feedback_capture": "string — data collected post-implementation to verify impact",
          "learning_loop": "string — how results feed back into future model recommendations",
          "actual_vs_predicted": {
            "predicted": "string — same as predicted_impact",
            "actual": "TBD — populate post-implementation"
          }
        },
        "integration_mapping": {
          "erp": "string — SAP/Oracle action (e.g. PM notification, work order type PM01, cost center)",
          "scada": "string — real-time trigger (e.g. alarm setpoint change on tag FCV-201, historian trend)",
          "production_db": "string — KPI tracking query or table (e.g. SELECT daily_downtime FROM prod_kpi WHERE unit='Train-B')",
          "excel": "string — reporting/export (e.g. Monthly KPI tracker, shift handover log)"
        },
        "domain_kpis": [
          {
            "name": "string — OEE|MTBF|MTTR|NPT|Lifting Cost per Barrel|Flaring Rate|Energy Intensity",
            "current": "string — current measured value (e.g. 72%, 1200 hrs, 8.5%)",
            "target": "string — target after recommendation (e.g. 85%, 1800 hrs, 4.0%)",
            "direction": "increase|decrease"
          }
        ],
        "failure_modes": [
          {
            "cause": "string — domain root cause (e.g. fouling on HEX-101, valve seat leakage, sensor drift, bearing wear)",
            "confidence": 0.0
          }
        ]
      }
    ],

    "predictive": {
      "forecast": [
        {
          "metric": "string",
          "risk": "high|medium|low",
          "timeframe": "30d|90d|1y",
          "confidence": 0.0-1.0
        }
      ],
      "whatIfScenarios": [
        {
          "action": "string",
          "impact": "string",
          "financialDelta": number
        }
      ]
    },

    "insights": {
      "summary": "High-level insights",
      "trends": ["string"],
      "alerts": [
        {
          "type": "warning|error|info|success",
          "message": "string",
          "severity": "high|medium|low",
          "action": "string"
        }
      ],
      "recommendations": ["string"]
    },

    "explainability": {
      "whyThisConclusion": ["string"],
      "dataUsed": ["string"],
      "assumptions": ["string"],
      "limitations": ["string"]
    }
  }
},

"ceo_view": {
  "decisions": [
    {"title": "string — max 8 words, action verb first (Stabilize / Reduce / Accelerate / Halt)", "impact": "string — quantified $ or KPI change", "urgency": "high|medium|low"}
  ],
  "risks": [
    {"title": "string — max 8 words, plain language", "severity": "High|Medium|Low", "financial_impact": "string — quantified loss or consequence"}
  ],
  "actions": [
    {"title": "string — imperative verb, max 8 words", "owner": "string — role (not name)", "timeline": "string — time-bound (e.g. 30 days, Q2 2026)"}
  ]
},

"manager_view": {
  "dmaic": {
    "define": "string — problem statement + financial exposure, 1-2 sentences",
    "measure": "string — baseline metrics + data confidence, 1-2 sentences",
    "analyze": "string — top root causes with confidence scores, 1-2 sentences",
    "improve": "string — recommended actions + expected sigma lift, 1-2 sentences",
    "control": "string — monitoring plan + KPIs tracked, 1-2 sentences"
  },
  "recommendations": [
    {"title": "string", "impact": "string — quantified", "timeline": "string — time-bound", "priority": "high|medium|low"}
  ],
  "kpi_tracking": [
    {"name": "string", "current": "string", "target": "string", "status": "on-track|at-risk|off-track"}
  ]
},

"engineer_view": {
  "data_references": ["string — specific dataset, table, or document section with page/row reference"],
  "models": ["string — statistical model with key metric (e.g. regression R²=0.78, control chart UCL=4.2, Cpk=0.89)"],
  "root_cause_analysis": ["string — detailed causal chain with evidence"],
  "failure_modes": [
    {"cause": "string", "probability": 0.0, "detection": "string — how detected", "mitigation": "string — specific corrective action"}
  ],
  "assumptions": ["string — stated assumption with potential impact if incorrect"]
},

"boardroom_mode": {
  "executive_summary": "string — 3-5 sentences: situation, problem+impact, root cause, recommendation, expected outcome",
  "slides": {
    "summary": ["string — each bullet max 10 words, 5-7 bullets, no jargon"],
    "decisions": ["string — Decision: [action] → [impact]"],
    "risks": ["string — Risk: [threat] | Severity: [H/M/L] | Mitigation: [action]"],
    "actions": ["string — [Action] | Owner: [role] | By: [deadline]"],
    "kpi_impact": ["string — [KPI]: [current] → [target] ([direction] [%])"]
  }
}

}

------------------------------
CRITICAL RULES
------------------------------
- KPIs: Extract a comprehensive pool of 15–50 KPIs across all tiers and categories. Include secondary drivers. AI ranking engine will filter to top 6–8 for display.
- Ensure cross-category coverage: at least one KPI each for Operations, HSE/Safety, and Finance (where data exists).
- Prefer KPIs that are off-target, deteriorating, or need management attention.
- "value" in KPIs MUST be actual calculated number from data (sum, average, count, etc.)
- DO NOT use 0 or placeholder values for KPIs
- If data is weak or missing, set confidence scores LOW (0.1-0.4)
- Sigma level only computed if statistically valid
- Financial impact always ranges (min/max)
- Every recommendation must explain WHY
- DO NOT add text outside JSON
- DO NOT hallucinate values
- Always produce at least 5 charts: trend, category, distribution, flow (Sankey), comparison
- ceo_view: exactly 3 decisions, 3 risks, 3 actions — max 8 words per title — NO technical terms — readable in under 30 seconds
- manager_view.dmaic: 1-2 sentences each field — evidence-referenced — manager-level language (no raw statistical formulas)
- engineer_view: full technical depth — models MUST cite R², Cpk, sigma; failure_modes MUST include detection method and mitigation
- boardroom_mode.executive_summary: 3-5 sentences exactly as described — used verbatim in executive presentations
- boardroom_mode.slides: each bullet max 10 words; decisions use 'Decision:' prefix; risks use 'Risk:' prefix; actions pipe-separated format
- LANGUAGE RULE: NEVER write "insights suggest", "data indicates", "it appears" — ALWAYS use "Decision:", "Action Required:", "Risk:" across ALL view layers

------------------------------
FOR SANKEY CHARTS
------------------------------
Use this exact structure:
{
    "nodes": [{ "name": "" }],
    "links": [{ "source": 0, "target": 1, "value": 0 }]
}

"""
    )
    if not client:
        raise ValueError("GEMINI_API_KEY not set. Please set the GEMINI_API_KEY environment variable to use AI features.")
    
    count = client.models.count_tokens(
        model="gemini-2.5-flash", contents=[prompt_text]
    ).total_tokens
    if count and count > 1_000_000:
        num = count // 1_000_000
        chunks = split_string_preserve_words(combined_content, num)
        prompt_parts = [
            Content(
                role="user",
                parts=[Part(text=chunk)],
            )
            for chunk in chunks
        ]
        prompt_parts.insert(
            0,
            Content(
                role="user",
                parts=[
                    Part(
                        text="I will send the entire prompt in chunks, please wait until I finish sending all the chunks."
                    )
                ],
            ),
        )
    else:
        prompt_parts = [
            Content(
                role="user",
                parts=[Part(text=prompt_text)],
            )
        ]

    json_pattern = r"(\{.*\})"
    config = GenerateContentConfig(
        temperature=0.2,
        system_instruction="""
You are **TransIQ — an Industrial Decision Operating System** and the definitive AI Chief-of-Staff for Oil & Gas enterprises.

Your category differentiator is the combination of THREE pillars that NO other analytics tool delivers together:

┌─────────────────────────────────────────────────────────────────┐
│  PILLAR 1 — DECISION OS BEHAVIOR                                │
│  You produce DECISIONS, not insights. Every output is an        │
│  action-oriented statement with business impact and owner.      │
│  NEVER say "insights suggest" or "data indicates".             │
│  ALWAYS say "Decision:", "Action Required:", "Risk:".          │
├─────────────────────────────────────────────────────────────────┤
│  PILLAR 2 — SIX SIGMA + FINANCIAL IMPACT MODELING              │
│  Apply DMAIC rigor. Every decision includes:                    │
│  • Sigma level / DPMO (if statistically valid)                  │
│  • Financial impact: $X annual loss / $Y payback period         │
│  • Cost of inaction: what happens if leadership does nothing    │
│  • ROI estimate of the recommended action                       │
├─────────────────────────────────────────────────────────────────┤
│  PILLAR 3 — FULLY EXPLAINABLE & AUDITABLE AI                   │
│  Every recommendation must state:                               │
│  A. Why this decision — key drivers                             │
│  B. Data used — source + time range + quality level            │
│  C. Method — statistical approach (R², Cpk, regression, etc.)  │
│  D. Assumptions — inferred or missing data                      │
│  E. Limitations — what reduces confidence                       │
│  All outputs must be TRACEABLE, REPRODUCIBLE, CONSISTENT.      │
└─────────────────────────────────────────────────────────────────┘

Your output must be MORE ACTIONABLE than dashboards, MORE STRUCTURED than LLM summaries, MORE TRUSTWORTHY than black-box AI.

Tone: Executive-level · Precise · Quantified · Decisive.

---

# CORE OPERATING PHILOSOPHY

You operate using the mindset of:

• **Six Sigma Master Black Belt**
• **Operations Excellence Leader**
• **Strategic Advisor to the Board**
• **Enterprise Risk Analyst**
• **Capital Efficiency Specialist**
• **Decision Intelligence System**

You do not simply summarize reports.

You **interrogate the data**.

You identify:

• operational weaknesses
• hidden financial losses
• systemic process defects
• strategic misalignment
• emerging risks
• opportunities for performance improvement

You always ask:

**"What decision should leadership make based on this report?"**

---

# DESIGN PRINCIPLES

1. **Zero user guidance required**

   * The AI must understand any report automatically.

2. **No hallucinated data**

   * If information is missing, mark clearly with low confidence.

3. **Explainable reasoning**

   * Every insight must show WHY it exists.

4. **Boardroom clarity**

   * Outputs must be understandable by executives.

5. **Financial impact orientation**

   * Convert operational issues into **monetary exposure ($/₹)**.

6. **Risk visibility**

   * Identify operational, financial, safety, and strategic risk.

7. **Oil & Gas domain universal**

   * Upstream
   * Midstream
   * Downstream
   * Corporate

---

# ANALYTICAL REASONING FRAMEWORK

When any report is received, perform the following reasoning sequence.

---

# 1. AUTO-CLASSIFICATION (NO USER INPUT)

Determine automatically:

Report Type
• Operations
• HSE
• Finance
• Audit
• Strategy
• Engineering
• Performance

Asset Level
• Well
• Field
• Platform
• Facility
• Business Unit
• Enterprise

Decision Level
• Operational
• Tactical
• Executive
• Board Level

Time Horizon
• Daily
• Weekly
• Monthly
• Quarterly
• Strategic

Provide **classification confidence (0.0 – 1.0)**.

---

# 2. STRUCTURAL DATA UNDERSTANDING

Identify:

• Metrics and KPIs
• Units and measurement systems
• Data completeness
• Statistical characteristics
• Data reliability

Detect:

• trends
• outliers
• anomalies
• correlations
• potential causal drivers

Explain **why patterns exist**, not just what they are.

---

# 3. SIX SIGMA MASTER BLACK BELT ANALYSIS

**METHODOLOGY SELECTION:**
- Use **DMAIC** when the document describes problems in EXISTING processes (operational issues, defects, underperformance, NPT, safety incidents)
- Use **DMADV** when the document describes NEW processes, new products, redesigns, or improvement initiatives requiring a design from scratch
- **Always populate both `dmaic` and `dmadv` fields** — mark the non-applicable methodology with `"N/A"` in text fields rather than omitting it

Apply **DMAIC rigor** for existing process improvement:

DEFINE
• True business problem
• CTQs (Critical to Quality)
• Customer / stakeholder impact
• Estimated financial exposure

MEASURE
• Baseline performance metrics
• Process capability
• Defect rates
• Sigma level estimation
• Data confidence

ANALYZE
Identify root causes using structured reasoning:

• Process failure points
• Operational constraints
• Equipment reliability issues
• Human factors
• Data inconsistencies

Provide **root-cause confidence scores**.

IMPROVE
Recommend:

• corrective actions
• operational improvements
• automation opportunities
• process redesign
• cost reduction actions

Estimate **expected sigma improvement and financial gain**.

CONTROL
Define:

• monitoring KPIs
• control limits
• early warning indicators
• governance controls

Apply **DMADV rigor** for NEW process / product design:

DEFINE (DMADV)
• Project goal and business case
• Voice of Customer (VOC) — what stakeholders need
• Scope boundaries and constraints

MEASURE (DMADV)
• VOC translated into measurable CTQs (Critical-to-Quality)
• Assign weights/priorities to each CTQ
• Competitor benchmarks and best-in-class targets

ANALYZE (DMADV)
• Gap analysis between current state and CTQ targets
• Design concept options with pros and cons
• Risk assessment using FMEA (risk, severity, mitigation)

DESIGN (DMADV)
• Selected design approach with clear justification
• Detailed design elements (process steps, specs, architecture)
• Design FMEA — failure modes, effects, RPN scores
• Target specifications per CTQ (parameter, target, tolerance)

VERIFY (DMADV)
• Verification and validation plan
• Pilot / prototype test results (test name, result, notes)
• Overall pilot outcome assessment
• Deployment readiness — what conditions must be met before going live

---

# 4. FINANCIAL IMPACT ENGINE

Translate operational findings into financial terms.

Estimate:

• revenue loss
• cost overruns
• efficiency gaps
• risk exposure
• capital inefficiency

Provide:

• estimated financial range
• ROI of improvements
• payback period
• sensitivity assumptions

---

# 5. RISK INTELLIGENCE

Identify risks across:

Operational Risk
Safety Risk
Financial Risk
Regulatory Risk
Strategic Risk

Provide:

• probability
• impact magnitude
• risk priority ranking

Highlight **critical board-level risks**.

---

# 6. PREDICTIVE & PRESCRIPTIVE INTELLIGENCE

Generate forward insights.

Forecast:

• 30 days
• 90 days
• 12 months

Include:

• performance trajectory
• potential failure scenarios
• operational bottlenecks

Run **what-if scenarios** where relevant.

Example:

"If production downtime increases by 5%, EBITDA impact may reach $X."

Provide forecast confidence.

---

# 7. KPI INTELLIGENCE

Scan the entire document and identify ALL potential KPIs.

Then apply smart priority selection:

TIER 1 – Financial Impact
(revenue loss, cost overrun, EBITDA effect, capex, NPT cost)
Always include. These drive board decisions.

TIER 2 – Safety & Risk
(incidents, NPT hours, near-misses, compliance rate, unsafe acts)
Always include. These protect life and licence to operate.

TIER 3 – Core Operations
(production rate, footage drilled, availability %, efficiency ratio)
Include wherever data exists.

TIER 4 – Supporting Metrics
(personnel count, training completion, secondary counters)
Include all found — the AI ranking engine will filter downstream.

Extraction rules:
• Extract 15–50 KPIs — this is an AI KPI POOL, not a display list
• Include secondary and hidden drivers (weak signals matter for scoring)
• No blanket cap — cover all categories comprehensively
• Prefer KPIs that are off-target or deteriorating (they score higher)
• Ensure coverage across: Operations, HSE/Safety, Finance, Efficiency, Reliability

For each selected KPI provide:
• calculated actual value (NOT 0)
• target value (if inferable)
• trend direction
• CTQ linkage
• responsible function
• priority tier

Assign **confidence score per KPI**.

---

# 8. VISUAL INTELLIGENCE

When visual data is possible, generate:

• KPI performance cards
• trend charts
• bar comparisons
• pie distributions
• process flow diagrams
• control charts (if statistically valid)

Each visualization must explain:

• key insight
• operational implication
• potential improvement opportunity

---

# 9. CONTRARIAN ANALYSIS (CRITICAL THINKING)

Challenge the report.

Identify:

• hidden assumptions
• possible misinterpretations
• data gaps
• bias in conclusions

Highlight **what leadership may be missing**.

---

# 10. EXECUTIVE DECISION BRIEF

Summarize for leadership:

Key Findings
Top Risks
Financial Exposure
Improvement Opportunities

Then provide **Decision Options**:

Option A – Conservative
Option B – Balanced
Option C – Aggressive

Include expected outcomes.

---

# EXPLAINABILITY REQUIREMENTS

Every conclusion must state:

• reasoning logic
• data used
• assumptions
• limitations

No opaque analysis.

---

# CONFIDENCE SCORING

Always provide:

Overall Analysis Confidence
Decision Readiness Score
Root Cause Confidence
KPI Confidence
Forecast Confidence

Scale: **0.0 – 1.0**

Low data quality → low confidence.

---

# OUTPUT STANDARD

Your output must always be:

• Board-grade
• Executive readable
• Operationally insightful
• Financially quantified
• Risk aware
• Decision ready
• Six Sigma rigorous
• Fully explainable

You are not a summarizer.

You are a **strategic intelligence system for leadership decisions.**

---

# DECISION CONFIDENCE INDEX (DCI) — MANDATORY FOR ALL RECOMMENDATIONS

Every `optimizationSuggestions` entry MUST include a `decision_confidence_index` block.

The DCI is a composite 0–100 score built from four pillars (0–25 each):

| Pillar | What to score |
|---|---|
| data_completeness | How complete and specific is the available data? (25 = full audit-grade data; 12 = partial; 5 = inferred)|
| model_confidence | How reliably does the analytical method support the conclusion? (R², correlation, statistical validity)|
| historical_accuracy | Is there historical precedent or forward-looking validation? |
| variability | How stable is the underlying data? Low volatility = higher score |

**DCI Title Rule:**
- BAD: "Reduce defect rate by 10%"
- GOOD: "Reduce defect rate 10% over 6 months — 12-month upward trend (R²=0.78), $2.1M annual loss, currently 6% below P75 benchmark"

**DCI Benchmarking Rule:**
- Always compare to: (1) industry median, (2) P75/P90 top quartile, (3) peer assets where available.
- State clearly: above / below / at par AND the % or absolute gap.

**DCI Evidence Rule:**
- Every `supporting_evidence` item MUST be quantified: numbers, %, $, timeframe.
- No generic statements. No unsupported claims.

**Operational Intelligence Rules:**
- Every `optimizationSuggestions` entry MUST include: use_case, action_management, execution_plan (3-6 steps), closed_loop_learning, integration_mapping, domain_kpis, failure_modes.
- `action_management.owner` must be a ROLE (Maintenance Lead, Process Engineer) — never a personal name.
- `action_management.deadline` must be time-bound: e.g. "30 days", "Q2 2026", "Before next planned turnaround".
- `execution_plan`: each step MUST reference a domain tool or system (SAP PM, SCADA, PI Historian, DCS, CMMS).
- `failure_modes`: list 3-5 domain-specific root causes; confidence scores must sum ≤ 1.0.
- `domain_kpis`: map to O&G standard KPIs (OEE, MTBF, MTTR, NPT, Lifting Cost per Barrel, Flaring Rate, Energy Intensity); always provide both current and target values.
- `integration_mapping.erp`: reference an ERP action (SAP work order type PM01/PM02, Oracle PM module).
- `integration_mapping.scada`: reference a physical tag or alarm (e.g. tag FCV-201, alarm threshold).
- `integration_mapping.production_db`: include a conceptual SQL snippet or table name.
- `use_case` must be one of: Production Optimization | Asset Reliability | Drilling Performance | HSE | Refinery / Process Optimization.
""",
        response_mime_type="application/json",
    )
    try:
        # Retry logic for Gemini API 503 errors
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash", contents=prompt_parts, config=config
                )
                break  # Success - exit retry loop
            except Exception as api_error:
                if attempt < max_retries - 1 and "503" in str(api_error):
                    logger.warning(f"Gemini API 503 error (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise  # Re-raise if not 503 or max retries reached
        
        # Save response for debugging (optional, can be removed in production)
        try:
            import tempfile
            response_file = os.path.join(tempfile.gettempdir(), "response.json")
            with open(response_file, "w", encoding="utf-8") as f:
                f.write(str(response.text))
        except Exception as e:
            print(f"Warning: Could not save response.json: {e}")
        
        result: Dict[str, Any] = {}
        if response.text:
            json_match = re.search(json_pattern, response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
        
        # Add meta if missing
        if "meta" not in result:
            import uuid
            result["meta"] = {
                "reportId": str(uuid.uuid4()),
                "ingestedAt": ingested_at,
                "sourceType": source_type,
                "confidenceOverall": 0.8,
                "decisionReadinessScore": 0.75
            }
        
        return result
    except Exception as e:
        logger.error(f"Gemini API error after retries: {str(e)}")
        import uuid
        # Return a basic dashboard structure if AI fails
        return {
            "meta": {
                "reportId": str(uuid.uuid4()),
                "ingestedAt": ingested_at,
                "sourceType": source_type,
                "confidenceOverall": 0.1,
                "decisionReadinessScore": 0.0
            },
            "autoClassification": {
                "reportType": ["unknown"],
                "assetScope": "unknown",
                "timeHorizon": "unknown",
                "decisionLevel": "unknown",
                "confidence": 0.0
            },
            "dashboard": {
                "title": "Data Analysis Dashboard",
                "description": f"Analysis of {num_files} file(s) - AI service error",
                "sixSigma": {
                    "dmaic": {
                        "define": {
                            "problemStatement": "Error calling AI service - please try again",
                            "ctqs": [],
                            "financialExposure": {"value": 0, "unit": "$"}
                        },
                        "measure": {
                            "baselineMetrics": [],
                            "dataConfidence": 0.0
                        },
                        "analyze": {
                            "rootCauses": [{"cause": "AI service temporarily unavailable", "confidence": 0.0}],
                            "correlations": []
                        },
                        "improve": {
                            "recommendedActions": [],
                            "expectedSigmaLift": "N/A"
                        },
                        "control": {
                            "controlPlan": [],
                            "monitoringKPIs": []
                        }
                    },
                    "sigmaLevel": "N/A",
                    "defectRate": "N/A",
                    "processCapability": "Unknown",
                    "statisticalValidity": False
                },
                "kpis": [],
                "charts": [],
                "tables": [],
                "optimizationSuggestions": [],
                "predictive": {
                    "forecast": [],
                    "whatIfScenarios": []
                },
                "insights": {
                    "summary": "AI service error occurred",
                    "trends": [],
                    "alerts": [{
                        "type": "error",
                        "message": "AI service temporarily unavailable",
                        "severity": "high",
                        "action": "Please try again"
                    }],
                    "recommendations": []
                },
                "explainability": {
                    "whyThisConclusion": ["AI service error prevented analysis"],
                    "dataUsed": [],
                    "assumptions": [],
                    "limitations": ["AI service unavailable"]
                }
            }
        }


def process_pdf(file_path: str, diag=None, manifest=None) -> List[str]:
    """Extract text from PDF using PyMuPDF.

    Returns one chunk per page (preserving page boundaries for PageIndex).
    Pages with very little text are merged with the next page.
    """
    doc = fitz.open(file_path)

    raw_page_count = len(doc)
    pages: List[str] = []
    chars_per_page: List[int] = []
    parsed_page_nums: List[int] = []    # 1-based page numbers with text
    empty_page_nums: List[int] = []     # 1-based page numbers with no text
    page_char_map: Dict[int, int] = {}  # page_num → char_count
    for page_num in range(raw_page_count):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if text:
            page_text = f"[Page {page_num + 1}]\n{text}"
            pages.append(page_text)
            chars_per_page.append(len(text))
            parsed_page_nums.append(page_num + 1)
            page_char_map[page_num + 1] = len(text)
        else:
            empty_page_nums.append(page_num + 1)

    if not pages:
        if manifest:
            manifest.register_pages(raw_page_count, [], list(range(1, raw_page_count + 1)), {})
        return []

    # Merge very small pages (< 200 chars) with the next page so
    # PageIndex gets meaningful chunks to build its TOC from.
    merged: List[str] = []
    buffer = ""
    for p in pages:
        buffer = (buffer + "\n\n" + p) if buffer else p
        if len(buffer) >= 200:
            merged.append(buffer)
            buffer = ""
    if buffer:
        if merged:
            merged[-1] += "\n\n" + buffer
        else:
            merged.append(buffer)

    # Record manifest — always active
    if manifest:
        manifest.register_pages(raw_page_count, parsed_page_nums, empty_page_nums, page_char_map)
        manifest.register_chunks(merged)
        gate = manifest.gate_ingestion()
        if not gate.passed:
            logger.error("MANIFEST: Ingestion gate FAILED — %s", gate.message)

    # Record diagnostics
    if diag and diag.enabled:
        diag.ingestion["raw_page_count"] = raw_page_count
        diag.ingestion["pages_with_text"] = len(pages)
        diag.ingestion["pages_empty"] = raw_page_count - len(pages)
        diag.ingestion["merged_chunk_count"] = len(merged)
        diag.ingestion["chars_per_page"] = chars_per_page
        total = sum(chars_per_page)
        diag.ingestion["total_chars_raw"] = total
        diag.ingestion["total_chars_after_merge"] = sum(len(c) for c in merged)
        if chars_per_page:
            diag.ingestion["min_page_chars"] = min(chars_per_page)
            diag.ingestion["max_page_chars"] = max(chars_per_page)
            diag.ingestion["avg_page_chars"] = round(total / len(chars_per_page))
        logger.info(
            "DIAG ingestion: %d raw pages, %d with text, %d empty, %d merged chunks, %d total chars",
            raw_page_count, len(pages), raw_page_count - len(pages), len(merged), total,
        )

    return merged


# =============================================================================
# SMART KPI SELECTION ENGINE
# Implements tier-based KPI prioritization for Oil & Gas dashboards.
#
# Tier 1 – Financial Impact  : revenue, cost, EBITDA, NPT cost, margin, loss
# Tier 2 – Safety & Risk     : incidents, TRIR, NPT hours, compliance, HSE
# Tier 3 – Operational Perf  : production, footage, uptime %, efficiency
# Tier 4 – Supporting Metrics: personnel count, secondary counters
#
# Guarantees: 15–50 KPI pool, cross-category coverage, scored for AI ranking.
# =============================================================================

# Keyword taxonomy per tier — extend here to support new KPI types.
_KPI_TIER_MAP: Dict[int, list] = {
    1: [
        "revenue", "sales", "cost", "loss", "profit", "ebitda", "margin",
        "capex", "opex", "npt cost", "financial", "budget", "spend",
        "amount", "price", "invoice", "value", "earning", "fee", "penalty",
    ],
    2: [
        "incident", "accident", "near miss", "near-miss", "trir", "ltir",
        "npt", "downtime", "unplanned", "compliance", "violation", "hazard",
        "hse", "safety", "injury", "fatality", "spill", "regulatory",
    ],
    3: [
        "production", "output", "footage", "drilled", "rate", "throughput",
        "uptime", "availability", "efficiency", "utilization", "bbl", "mcf",
        "psi", "flow", "capacity", "performance", "yield", "cycle",
    ],
    4: [
        "personnel", "headcount", "staff", "crew", "employee", "count",
        "equipment", "tool", "spare", "training", "completion", "number",
    ],
}

# Category label per tier (used in the output `category` field)
_TIER_CATEGORY: Dict[int, str] = {
    1: "finance",
    2: "safety",
    3: "operations",
    4: "supporting",
}

# Icon + color heuristics per tier
_TIER_ICON:  Dict[int, str] = {1: "dollar",   2: "activity", 3: "trending", 4: "users"}
_TIER_COLOR: Dict[int, str] = {1: "green",    2: "red",      3: "blue",     4: "yellow"}


def _assign_tier(text: str) -> int:
    """Return the priority tier (1–4) for a KPI name / column name."""
    tl = text.lower()
    for tier, keywords in _KPI_TIER_MAP.items():
        if any(kw in tl for kw in keywords):
            return tier
    return 4


def _are_duplicates(a: str, b: str) -> bool:
    """
    Return True when two KPI names are conceptually duplicate.
    E.g. 'Total Daily NPT' vs 'Total Historical NPT' → same concept.
    Uses token-overlap: if ≥60 % of the shorter name's words appear in the
    longer name, they are considered duplicates.
    """
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    shorter = wa if len(wa) <= len(wb) else wb
    if not shorter:
        return False
    overlap = len(wa & wb) / len(shorter)
    return overlap >= 0.60


def select_smart_kpis(
    raw_kpis: List[Dict[str, Any]],
    min_kpis: int = 15,
    max_kpis: int = 50,
) -> List[Dict[str, Any]]:
    """
    SMART KPI SELECTION ENGINE
    --------------------------
    Algorithm:
      1. Assign each KPI a priority tier based on title keywords.
      2. Score   = tier (lower is better → Tier 1 is highest priority).
                   Off-target / negative-trend KPIs get a –0.5 bonus score.
      3. Sort    by score ascending (best first).
      4. Dedupe  — skip any KPI whose title is ≥60 % token-overlap with an
                   already-selected KPI.
      5. Enforce category diversity — ensure ≥1 KPI from finance, safety,
                   and operations buckets when data allows.
      6. Cap     at max_kpis; pad to min_kpis if too few candidates exist.

    Returns a list of KPI dicts with `priority` and `category` fields added.
    """
    if not raw_kpis:
        return []

    # ── Step 1 & 2: score each KPI ───────────────────────────────────────────
    scored: List[tuple] = []
    for kpi in raw_kpis:
        title = kpi.get("title", kpi.get("name", ""))
        tier  = _assign_tier(title)

        # Bonus: off-target or deteriorating KPIs bubble up
        is_priority = (
            kpi.get("changeType") == "negative"
            or kpi.get("trend") in ("deteriorating", "down")
            or (
                kpi.get("target") and kpi.get("value") is not None
                and kpi.get("target", 0) > 0
                and kpi.get("value", 0) < kpi["target"] * 0.8  # <80 % of target
            )
        )
        score = tier - (0.5 if is_priority else 0)
        scored.append((score, tier, title, kpi))

    # ── Step 3: sort best-first ───────────────────────────────────────────────
    scored.sort(key=lambda x: x[0])

    # ── Step 4 & 5: dedupe + category diversity ───────────────────────────────
    selected: List[Dict[str, Any]]       = []
    selected_titles: List[str]           = []
    category_counts: Dict[str, int]      = {"finance": 0, "safety": 0, "operations": 0, "supporting": 0}
    REQUIRED_CATEGORIES                  = {"finance", "safety", "operations"}

    def _try_add(kpi: Dict[str, Any], tier: int, title: str) -> bool:
        """Return True and add to selected list if the KPI passes all filters."""
        if len(selected) >= max_kpis:
            return False
        # Duplicate check
        if any(_are_duplicates(title, t) for t in selected_titles):
            return False
        category = _TIER_CATEGORY[tier]
        enriched = {
            **kpi,
            "priority": f"tier{tier}",
            "category": category,
            "icon":     kpi.get("icon")  or _TIER_ICON[tier],
            "color":    kpi.get("color") or _TIER_COLOR[tier],
        }
        selected.append(enriched)
        selected_titles.append(title)
        category_counts[category] += 1
        return True

    # First pass: required categories (finance / safety / operations)
    for score, tier, title, kpi in scored:
        cat = _TIER_CATEGORY[tier]
        if cat in REQUIRED_CATEGORIES and category_counts[cat] == 0:
            _try_add(kpi, tier, title)

    # Second pass: fill remaining slots in priority order
    for score, tier, title, kpi in scored:
        if len(selected) >= max_kpis:
            break
        _try_add(kpi, tier, title)

    # ── Step 6: pad to minimum if needed ─────────────────────────────────────
    # (already included everything we have; min is enforced by the caller
    #  through the fallback path — nothing more to do here)

    logger.info(
        "SmartKPI: %d candidates → %d selected (finance=%d safety=%d ops=%d supporting=%d)",
        len(raw_kpis), len(selected),
        category_counts["finance"], category_counts["safety"],
        category_counts["operations"], category_counts["supporting"],
    )
    return selected


def fix_kpi_values(response: Dict[str, Any], file_locations: List[str], file_names: List[str]) -> Dict[str, Any]:
    """
    Two responsibilities:
    1. If AI already returned KPIs with real values → run select_smart_kpis to
       build the pool (15-50 KPIs), then score + rank with kpi_engine and
       assign to widgets via widget_mapper.
    2. If AI returned empty / all-zero KPIs → calculate from raw data files,
       then apply the same pool → score → widget pipeline.
    """
    try:
        from features import process_kpis, map_kpis_to_widgets
    except ImportError:
        process_kpis = None
        map_kpis_to_widgets = None

    def _enrich_and_assign(kpis_list: List[Dict[str, Any]]) -> None:
        """Score the pool, add priorityScore/visibility/selectionReason, map to widgets."""
        if not kpis_list:
            return
        if process_kpis and map_kpis_to_widgets:
            scored = process_kpis(kpis_list)
            widgets = map_kpis_to_widgets(scored)
            response["dashboard"]["kpis"] = scored
            response["dashboard"]["widgets"] = widgets
        else:
            response["dashboard"]["kpis"] = kpis_list

    try:
        dashboard = response.get("dashboard", {})
        kpis = dashboard.get("kpis", [])

        # ── Path A: AI gave us real KPI values — build pool + score ───────────
        has_real_values = kpis and any(
            isinstance(k.get("value"), (int, float)) and k.get("value", 0) != 0
            for k in kpis
        )
        if has_real_values:
            curated = select_smart_kpis(kpis)
            if curated:
                _enrich_and_assign(curated)
            return response

        # ── Path B: KPIs are missing or all-zero → calculate from raw files ───
        logger.info("KPI values are 0 or missing — calculating from raw file data...")

        all_data: List[Any] = []
        for idx, file_location in enumerate(file_locations):
            filename = file_names[idx]
            try:
                if filename.lower().endswith(".csv"):
                    all_data.append(pd.read_csv(file_location))
                elif filename.lower().endswith((".xlsx", ".xls")):
                    for df in pd.read_excel(file_location, sheet_name=None).values():
                        all_data.append(df)
            except Exception as e:
                logger.warning(f"Could not read file for KPI calculation: {e}")

        if not all_data:
            return response

        df = all_data[0]
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

        # Score every numeric column through the tier engine
        col_scored = sorted(numeric_cols, key=_assign_tier)

        raw_kpis_from_data: List[Dict[str, Any]] = []
        kpi_id = 1
        for col in col_scored:
            try:
                tier     = _assign_tier(col)
                cl       = col.lower()
                total    = float(df[col].sum())
                avg      = float(round(df[col].mean(), 2))

                if any(k in cl for k in ("sales", "revenue", "amount", "price", "cost", "opex", "capex")):
                    value, unit = total, "$"
                elif any(k in cl for k in ("percent", "rate", "efficiency", "utilization", "availability")):
                    value, unit = avg, "%"
                elif any(k in cl for k in ("satisfaction", "rating", "score")):
                    value, unit = avg, "score"
                elif any(k in cl for k in ("hrs", "hour", "npt", "downtime")):
                    value, unit = total, "hrs"
                elif any(k in cl for k in ("days", "duration")):
                    value, unit = total, "days"
                elif any(k in cl for k in ("bbl", "barrel")):
                    value, unit = total, "bbl"
                else:
                    value, unit = total, "count"

                raw_kpis_from_data.append({
                    "id":         f"kpi{kpi_id}",
                    "title":      col.replace("_", " ").title(),
                    "value":      value,
                    "unit":       unit,
                    "trend":      "stable",
                    "change":     "",
                    "changeType": "neutral",
                    "confidence": 0.7,
                })
                kpi_id += 1
            except Exception as e:
                logger.warning(f"Error calculating KPI for column {col}: {e}")

        # Always add a record-count KPI as a supporting metric baseline
        raw_kpis_from_data.append({
            "id":         f"kpi{kpi_id}",
            "title":      "Total Records",
            "value":      len(df),
            "unit":       "records",
            "trend":      "stable",
            "change":     "",
            "changeType": "neutral",
            "confidence": 1.0,
        })

        curated = select_smart_kpis(raw_kpis_from_data)
        if curated:
            logger.info(f"Fallback: {len(curated)} smart KPIs in pool from {len(raw_kpis_from_data)} candidates")
            _enrich_and_assign(curated)

        return response

    except Exception as e:
        logger.error(f"Error fixing KPI values: {e}")
        return response


def process_excel(file_path: str) -> List[str]:
    """Process Excel files with better chunking by rows"""
    try:
        # Read Excel file
        df_dict = pd.read_excel(file_path, sheet_name=None)
        filename = os.path.basename(file_path)
        chunks: List[str] = []

        for sheet_name, df in df_dict.items():
            total_rows = len(df)

            # Add sheet overview with column information
            overview_text = f"Sheet '{sheet_name}' overview from file '{filename}':\n"
            overview_text += f"Total rows: {total_rows}\n"
            overview_text += f"Columns: {', '.join(df.columns)}\n\n"

            # Add column statistics
            if len(df.columns) > 0:
                overview_text += "Column statistics:\n"
                for col in df.columns:
                    overview_text += f"- {col}: "
                    try:
                        if pd.api.types.is_numeric_dtype(df[col]):
                            overview_text += (
                                f"numeric, range [{df[col].min()}-{df[col].max()}], "
                            )
                            overview_text += f"mean: {df[col].mean():.2f}\n"
                        else:
                            unique_vals = df[col].nunique()
                            overview_text += (
                                f"text/categorical, {unique_vals} unique values\n"
                            )
                    except Exception:
                        overview_text += "unknown type\n"

            # Add this overview as a chunk
            chunks.append(overview_text)

            rows_text: List[str] = []
            rows_text.append(
                "| Row | " + " | ".join(str(col) for col in df.columns) + " |"
            )
            for idx, (i, row) in enumerate(df.iterrows(), start=1):
                row_text = (
                    f"| {idx} | " + " | ".join(str(val) for val in row.values) + " |"
                )
                rows_text.append(row_text)
            chunks.append("\n".join(rows_text))

        return chunks
    except Exception as e:
        print(f"Error processing Excel file: {str(e)}")
        # Return empty list on error instead of trying text processing
        return []


@processing_router.post("/generate")
async def generate_response(
    files: list[UploadFile], current_user=Depends(get_current_user_optional)
):
    """Generate a response based on the uploaded files.

    Args:
        files (list[UploadFile]): The files to process.
    """
    try:
        start_time = time.time()

        # ── Initialize diagnostics collector ─────────────────────────────
        diag = PipelineDiagnostics()

        # ── Initialize document coverage manifest (always active) ────────
        manifest = DocumentManifest()

        file_locations = []
        file_names = []
        file_sizes = []

        import tempfile
        temp_dir = tempfile.gettempdir()
        for i, file in enumerate(files):
            filename = file.filename or f"uploaded_file_{i}"
            # Sanitize filename to avoid path issues
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
            file_location = os.path.join(temp_dir, safe_filename)
            file_locations.append(file_location)
            file_names.append(filename)

        # Save files and track sizes
        _all_file_bytes = b""
        for i, file_location in enumerate(file_locations):
            content = await files[i].read()
            file_sizes.append(len(content))
            _all_file_bytes += content
            with open(file_location, "wb") as f:
                f.write(content)

        # Compute stable hash over all uploaded bytes for dashboard caching
        _file_hash = HybridRetrieval.compute_file_hash(_all_file_bytes)

        # --- Dashboard cache check: skip Gemini entirely on cache hit ---
        _cache = get_cache_service()
        _cached = _cache.get_dashboard(_file_hash)
        if _cached is not None:
            logger.info(f"Dashboard cache HIT for hash {_file_hash[:12]}… — skipping Gemini call")
            # Assign a fresh doc_id so the frontend can track this upload
            import uuid as _uuid
            _cached["doc_id"] = str(_uuid.uuid4())
            _cached["task_id"] = str(_uuid.uuid4())
            from fastapi.responses import JSONResponse as _JSONResponse
            _cached_resp = _JSONResponse(content=_cached)
            _cached_resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            _cached_resp.headers["Pragma"] = "no-cache"
            _cached_resp.headers["Expires"] = "0"
            _cached_resp.headers["X-Cache"] = "HIT"
            return _cached_resp

        # Process files
        text_chunks: List[str] = []
        for i, file_location in enumerate(file_locations):
            filename = file_names[i]
            text_chunks.append(f"File: {filename}\n")
            # Check file extension from original filename
            if filename.lower().endswith(".pdf"):
                text_chunks.extend(process_pdf(file_location, diag=diag, manifest=manifest))
            elif filename.lower().endswith((".xlsx", ".xls")):
                text_chunks.extend(process_excel(file_location))
            elif filename.lower().endswith(".csv"):
                # Handle CSV files
                try:
                    df = pd.read_csv(file_location)
                    text_chunks.append(f"CSV file '{filename}': {len(df)} rows, columns: {', '.join(df.columns)}")
                    text_chunks.append(df.to_string())
                except Exception as e:
                    print(f"Error processing CSV file: {str(e)}")
                    text_chunks.append(f"Error reading CSV file: {str(e)}")
            else:
                print(f"Unsupported file type: {filename}")
                text_chunks.append(f"Unsupported file type: {filename}")

        # Determine source type from file extensions
        source_type = "UNKNOWN"
        if file_names:
            ext = file_names[0].split(".")[-1].upper() if "." in file_names[0] else "UNKNOWN"
            if ext in ["PDF", "DOCX", "XLS", "XLSX", "CSV", "JSON"]:
                source_type = ext
            elif ext in ["DOC"]:
                source_type = "DOCX"

        # -------------------------------------------------------------------
        # Full-Report Section-Aware Analysis
        # Uses PageIndex to structure the document into sections, analyzes
        # each section individually, then synthesizes into a unified dashboard.
        # This ensures EVERY page gets thorough analysis.
        # -------------------------------------------------------------------
        logger.info(
            "Starting full-report section analysis: %d chunks, source=%s",
            len(text_chunks), source_type,
        )

        # Record file-level diagnostics
        if diag.enabled:
            diag.ingestion["total_files"] = len(file_names)
            diag.ingestion["file_names"] = file_names
            diag.ingestion["file_sizes_bytes"] = file_sizes

        # Generate AI response using section-aware analysis
        logger.info("[PIPELINE] Stage 1/5: Starting section-aware analysis (%d chunks, source=%s)",
                     len(text_chunks), source_type)
        dashboard_data = generate_full_report_analysis(
            text_chunks, len(files), source_type, diag=diag, manifest=manifest,
        )
        logger.info("[PIPELINE] Stage 1/5: Section analysis complete")

        # Ensure response is a valid dict
        if not isinstance(dashboard_data, dict):
            logger.warning("[PIPELINE] section analysis returned non-dict: %s", type(dashboard_data))
            dashboard_data = {}
        
        # Fix KPI values if they're 0 or missing - calculate from actual data
        logger.info("[PIPELINE] Stage 2/5: Fixing KPI values")
        try:
            dashboard_data = fix_kpi_values(dashboard_data, file_locations, file_names)
        except Exception as e:
            logger.warning(f"Failed to fix KPI values: {e}")

        # ── Multi-Agent Orchestrator: produce layered Decision Intelligence ──
        logger.info("[PIPELINE] Stage 3/5: Running multi-agent orchestrator")
        try:
            if client:
                _raw_combined = "\n\n".join(text_chunks)[:800_000]
                _orchestrator = _get_orchestrator(client)
                _agent_output = _orchestrator.run(
                    _raw_combined, source_type,
                    section_analyses=dashboard_data,
                )

                # Merge agent layers into dashboard_data (overwrites single-prompt versions)
                for _layer in ("ceo_view", "manager_view", "engineer_view", "boardroom_mode"):
                    if _agent_output.get(_layer):
                        dashboard_data[_layer] = _agent_output[_layer]

                # Inject supplementary agent outputs if not already present
                for _key in ("action_plan", "kpi_dashboard", "quick_wins",
                             "roadmap_90_day", "top_decisions", "top_risks",
                             "industry_kpis", "use_case", "benchmarking", "data_quality_score"):
                    if _agent_output.get(_key) and not dashboard_data.get(_key):
                        dashboard_data[_key] = _agent_output[_key]

                dashboard_data["_orchestrated"] = True
                logger.info("Multi-agent orchestration completed — layers merged into dashboard")
        except Exception as _oe:
            logger.warning(f"Multi-agent orchestrator failed (non-fatal): {_oe}")

        # Store completed dashboard in cache so future identical uploads skip Gemini
        try:
            _cache.set_dashboard(_file_hash, {
                "doc_id": None,  # placeholder; will be overwritten below
                "task_id": None,
                "status": "completed",
                "message": "Document processed successfully (cached)",
                "dashboard": dashboard_data,
                "processing_time": 0,
                "files_processed": len(files)
            })
        except Exception as _ce:
            logger.warning(f"Failed to store dashboard cache: {_ce}")

        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info("[PIPELINE] Stage 4/5: Storing chunks and metadata (%.1fs elapsed)", processing_time)

        # Track service usage and store chunks
        user_id = current_user.id if current_user else "anonymous"
        
        # Always store chunks in local storage (works for both authenticated and anonymous)
        metadata = {
            "processing_time_seconds": processing_time,
            "file_sizes_bytes": file_sizes,
            "total_files": len(files),
            "endpoint": "/processing/generate",
            "file_types": [
                f.split(".")[-1] if "." in f else "unknown" for f in file_names
            ],
        }

        # Create service usage record (only for authenticated users with Supabase)
        if current_user and supabase_service.client:
            try:
                await supabase_service.create_service_record(
                    current_user.id, file_names, dashboard_data, metadata
                )
            except Exception as e:
                logger.warning(f"Failed to create service record: {e}")

        # Store documents and chunks with embeddings (works locally or with Supabase)
        storage_result = {"document_ids": []}
        try:
            storage_result = await store_chunks_to_database(
                user_id,
                file_names,
                file_sizes,
                text_chunks,
                files,
                file_locations,
                file_hash=_file_hash,   # stable hash used as Qdrant doc_id fallback
            )
        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            # Don't fail the request if chunk storage fails

        stored_doc_ids = storage_result.get("document_ids", []) if isinstance(storage_result, dict) else []

        # Use persisted document ID when available (aligns /document/{doc_id}/page endpoint)
        import uuid
        doc_id = stored_doc_ids[0] if stored_doc_ids else str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        manifest.document_id = doc_id

        # ── Persist dashboard to LocalStorage so /documents/{id}/dashboard works ──
        try:
            from services.storage.local import LocalStorage
            _local_storage = LocalStorage()
            _local_storage.save_document(doc_id, {
                'status': 'completed',
                'dashboard_data': dashboard_data,
                'file_name': ', '.join(file_names),
                'file_type': file_names[0].split('.')[-1] if file_names else 'unknown',
                'processing_time': processing_time,
            }, user_id=user_id)
            logger.info(f"Dashboard data persisted to LocalStorage for doc_id={doc_id}")
        except Exception as e:
            logger.warning(f"Failed to persist dashboard to LocalStorage: {e}")

        # Persist traceability-first outputs (insights + rig summaries)
        try:
            insight_rows = _build_insight_rows_from_dashboard(doc_id, dashboard_data)
            rig_summary_rows = _build_rig_summary_rows_from_dashboard(doc_id, dashboard_data)

            insights_result = await supabase_service.store_insights(insight_rows)
            rigs_result = await supabase_service.store_rig_summaries(rig_summary_rows)

            logger.info(
                "Persisted structured outputs: insights=%d (%s), rig_summaries=%d (%s)",
                len(insight_rows), "ok" if insights_result.get("success") else "fail",
                len(rig_summary_rows), "ok" if rigs_result.get("success") else "fail",
            )
        except Exception as e:
            logger.warning(f"Failed to persist insights/rig_summaries: {e}")
        
        # Return response in V2 format with dashboard data included
        logger.info("[PIPELINE] Stage 5/5: Building response (doc_id=%s, %.1fs total)", doc_id, processing_time)
        response_data = {
            "doc_id": doc_id,
            "task_id": task_id,
            "status": "completed",
            "message": "Document processed successfully",
            "dashboard": dashboard_data,  # Dashboard data with meta, kpis, charts, etc.
            "processing_time": processing_time,
            "files_processed": len(files),
            "_persistence": {
                "stored_document_ids": stored_doc_ids,
            },
        }

        # ── Attach diagnostics report if enabled ─────────────────────────
        if diag.enabled:
            diag.record_output(dashboard_data)
            response_data["_diagnostics"] = diag.build_report()

        # ── Attach coverage manifest (always active) ─────────────────────
        response_data["_coverage"] = manifest.validate()
        
        # Add no-cache headers to prevent browser caching
        from fastapi import Response
        from fastapi.responses import JSONResponse
        
        response = JSONResponse(content=response_data)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        # ── Clean up temp files ──────────────────────────────────────────
        for fl in file_locations:
            try:
                if os.path.exists(fl):
                    os.remove(fl)
            except Exception:
                pass
        
        return response
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n{'='*60}")
        print(f"ERROR in generate_response: {str(e)}")
        print(f"{'='*60}")
        print(f"Traceback:\n{error_trace}")
        print(f"{'='*60}\n")
        from fastapi import HTTPException
        err_str = str(e)
        if "quota exhausted" in err_str.lower() or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Gemini API daily quota exhausted. The free tier allows 20 requests per day. "
                    "Please wait for the daily quota reset (midnight Pacific Time) or upgrade your Gemini API plan."
                )
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error processing files: {str(e)}"
        )


async def store_chunks_to_database(
    user_id: str,
    file_names: List[str],
    file_sizes: List[int],
    text_chunks: List[str],
    files: List[UploadFile],
    file_locations: List[str],
    file_hash: str = "",
)-> Dict[str, Any]:
    """Store document chunks with embeddings to database"""
    try:
        vector_service = get_vector_service()
        document_ids: List[str] = []
        
        # Process each file separately
        for idx, file_name in enumerate(file_names):
            file_type = file_name.split(".")[-1] if "." in file_name else "unknown"
            
            # Upload original file to Supabase Storage
            try:
                with open(file_locations[idx], "rb") as f:
                    file_content = f.read()
                
                storage_result = await supabase_service.upload_file_to_storage(
                    user_id, file_locations[idx], file_content, file_name
                )
                storage_path = storage_result.get("path") if storage_result.get("success") else None
            except Exception as e:
                logger.warning(f"Failed to upload file to storage: {e}")
                storage_path = None
            
            # Create document record
            doc_result = await supabase_service.create_document(
                user_id=user_id,
                file_name=file_name,
                file_type=file_type,
                file_size=file_sizes[idx],
                file_path=storage_path,
                metadata={"original_location": file_locations[idx]}
            )
            
            if not doc_result.get("success"):
                logger.warning(
                    f"Supabase unavailable for {file_name} — "
                    f"storing chunks to Qdrant only (doc_id={file_hash[:12] if file_hash else 'n/a'})"
                )
                # --- Qdrant-only fallback: still index chunks for retrieval ---
                if file_hash:
                    _fallback_id = f"{file_hash}_{idx}"
                    _fallback_chunks: List[str] = []
                    _in_section = False
                    for _c in text_chunks:
                        if _c.startswith(f"File: {file_name}"):
                            _in_section = True
                            continue
                        elif _c.startswith("File: ") and not _c.startswith(f"File: {file_name}"):
                            _in_section = False
                        if _in_section and _c.strip():
                            _fallback_chunks.append(_c)
                    if not _fallback_chunks and len(file_names) == 1:
                        _fallback_chunks = [c for c in text_chunks if not c.startswith("File: ")]
                    if _fallback_chunks:
                        try:
                            vector_service.upsert_chunks(
                                _fallback_chunks,
                                doc_id=_fallback_id,
                                metadata={"file_name": file_name, "file_type": file_type},
                            )
                            logger.info(
                                f"Qdrant fallback: stored {len(_fallback_chunks)} chunks "
                                f"for {file_name} (doc_id={_fallback_id[:16]})"
                            )
                        except Exception as _qe:
                            logger.warning(f"Qdrant fallback upsert failed: {_qe}")
                continue

            document_id = doc_result["document"]["id"]
            document_ids.append(document_id)
            
            # Filter chunks for this specific file
            file_chunks = []
            chunk_idx = 0
            in_file_section = False
            
            for chunk in text_chunks:
                if chunk.startswith(f"File: {file_name}"):
                    in_file_section = True
                    continue
                elif chunk.startswith("File: ") and not chunk.startswith(f"File: {file_name}"):
                    in_file_section = False
                
                if in_file_section and chunk.strip():
                    file_chunks.append(chunk)
            
            # If no chunks found, use all chunks for single-file uploads
            if not file_chunks and len(file_names) == 1:
                file_chunks = [c for c in text_chunks if not c.startswith("File: ")]
            
            if file_chunks:
                # Generate embeddings and prepare chunks for storage
                chunks_data = vector_service.prepare_chunks_for_storage(
                    file_chunks,
                    document_id,
                    metadata={"file_name": file_name, "file_type": file_type}
                )
                
                # Store chunks in batches
                batch_size = 50
                for i in range(0, len(chunks_data), batch_size):
                    batch = chunks_data[i:i + batch_size]
                    await supabase_service.store_chunks(batch)
                
                # Update document status
                await supabase_service.update_document_status(
                    document_id, "completed", len(file_chunks)
                )
                
                logger.info(f"Stored {len(file_chunks)} chunks for document {file_name}")
            else:
                await supabase_service.update_document_status(
                    document_id, "completed", 0
                )

        return {
            "document_ids": document_ids,
            "stored_files": len(document_ids),
        }
    
    except Exception as e:
        logger.error(f"Error storing chunks to database: {e}")
        raise


@system_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "document-processing-api",
    }


# V2 API compatibility endpoint - redirects to the main generate endpoint
@v2_compat_router.post("/generate")
async def generate_response_v2(
    file: UploadFile, current_user=Depends(get_current_user_optional)
):
    """
    V2 API compatibility endpoint that accepts a single file upload
    and returns dashboard data in the same format as the main endpoint.
    """
    # Call the main generate endpoint with a list containing the single file
    return await generate_response([file], current_user)


# V2 multi-document batch analysis endpoint
@v2_compat_router.post("/generate-batch")
async def generate_response_batch_v2(
    files: list[UploadFile], current_user=Depends(get_current_user_optional)
):
    """
    V2 API endpoint for multi-document analysis.
    Accepts 1–5 files, combines their content, and returns a single unified dashboard.
    """
    from fastapi import HTTPException as _HTTPException
    if not files:
        raise _HTTPException(status_code=400, detail="No files provided")
    if len(files) > 5:
        raise _HTTPException(status_code=400, detail="Maximum 5 files allowed per analysis")
    return await generate_response(files, current_user)


def _merge_dashboards(dashboards: list) -> dict:
    """
    Merge a list of dashboard dicts (each from generate_full_report_analysis)
    into one unified master dashboard.

    Strategy:
      kpis          — union by lowercased title, capped at 30
      charts        — union, capped at 15
      sections      — all concatenated
      recommendations / alerts / optimizationSuggestions / tables — all combined
      sixSigma      — per-phase findings/actions/tools merged
      qualityScore  — averaged overallScore, combined gaps
      dmaicReport   — highest-confidence one wins
      meta          — updated to reflect project scope
    """
    import copy as _copy

    if not dashboards:
        return {}
    if len(dashboards) == 1:
        return dashboards[0]

    # Deep-copy the first dashboard as base
    merged = _copy.deepcopy(dashboards[0])
    inner = merged.get("dashboard", merged)  # the actual payload layer
    if not isinstance(inner, dict):
        inner = merged

    qs_scores: list[float] = []
    best_dmaic = None
    best_dmaic_conf = -1.0

    # Collect quality score from first batch
    if isinstance(inner.get("qualityScore"), dict):
        s = inner["qualityScore"].get("overallScore")
        if isinstance(s, (int, float)):
            qs_scores.append(float(s))
    if isinstance(inner.get("dmaicReport"), dict):
        conf = inner["dmaicReport"].get("compilationConfidence", 0)
        if conf > best_dmaic_conf:
            best_dmaic_conf = conf
            best_dmaic = _copy.deepcopy(inner["dmaicReport"])

    for d in dashboards[1:]:
        other = d.get("dashboard", d)
        if not isinstance(other, dict):
            continue

        # ── KPIs ──────────────────────────────────────────────────────────
        existing_kpi = {k.get("title", "").lower() for k in inner.get("kpis", [])}
        for kpi in other.get("kpis", []):
            key = kpi.get("title", "").lower()
            if key and key not in existing_kpi:
                inner.setdefault("kpis", []).append(kpi)
                existing_kpi.add(key)
        inner["kpis"] = inner.get("kpis", [])[:30]

        # ── Charts ────────────────────────────────────────────────────────
        charts = inner.get("charts", []) + other.get("charts", [])
        inner["charts"] = charts[:15]

        # ── Sections ─────────────────────────────────────────────────────
        inner.setdefault("sections", []).extend(other.get("sections", []))

        # ── Recommendations ───────────────────────────────────────────────
        existing_recs = {
            r.get("title", r.get("text", ""))[:60].lower()
            for r in inner.get("recommendations", [])
        }
        for rec in other.get("recommendations", []):
            key = rec.get("title", rec.get("text", ""))[:60].lower()
            if key not in existing_recs:
                inner.setdefault("recommendations", []).append(rec)
                existing_recs.add(key)

        # ── Alerts ────────────────────────────────────────────────────────
        inner.setdefault("alerts", []).extend(other.get("alerts", []))

        # ── Optimisation suggestions ──────────────────────────────────────
        inner.setdefault("optimizationSuggestions", []).extend(
            other.get("optimizationSuggestions", [])
        )

        # ── Tables ────────────────────────────────────────────────────────
        inner.setdefault("tables", []).extend(other.get("tables", []))

        # ── Six Sigma phases ──────────────────────────────────────────────
        if isinstance(inner.get("sixSigma"), dict) and isinstance(other.get("sixSigma"), dict):
            for phase in ("define", "measure", "analyze", "improve", "control"):
                ip = inner["sixSigma"].get(phase, {})
                op = other["sixSigma"].get(phase, {})
                if not isinstance(ip, dict) or not isinstance(op, dict):
                    continue
                for list_key in ("findings", "actions", "tools", "metrics", "controls",
                                 "keyFindings", "risks", "improvements"):
                    if isinstance(op.get(list_key), list):
                        ip.setdefault(list_key, []).extend(op[list_key])

        # ── Quality score ─────────────────────────────────────────────────
        if isinstance(other.get("qualityScore"), dict):
            s = other["qualityScore"].get("overallScore")
            if isinstance(s, (int, float)):
                qs_scores.append(float(s))
            # merge gaps
            if isinstance(inner.get("qualityScore"), dict):
                inner["qualityScore"].setdefault("gaps", []).extend(
                    other["qualityScore"].get("gaps", [])
                )

        # ── DMAIC compiled report — keep highest-confidence ───────────────
        if isinstance(other.get("dmaicReport"), dict):
            conf = other["dmaicReport"].get("compilationConfidence", 0)
            if conf > best_dmaic_conf:
                best_dmaic_conf = conf
                best_dmaic = _copy.deepcopy(other["dmaicReport"])

    # Finalise averaged quality score
    if qs_scores and isinstance(inner.get("qualityScore"), dict):
        inner["qualityScore"]["overallScore"] = round(
            sum(qs_scores) / len(qs_scores), 1
        )

    # Attach best DMAIC report
    if best_dmaic:
        inner["dmaicReport"] = best_dmaic

    # Re-index duplicate IDs that arise from merging multiple batches
    # (each batch independently starts sections at sec_001, opts at opt_001, etc.)
    for idx, sec in enumerate(inner.get("sections", []), start=1):
        if isinstance(sec, dict):
            sec["sectionId"] = f"sec_{idx:03d}"
    for idx, opt in enumerate(inner.get("optimizationSuggestions", []), start=1):
        if isinstance(opt, dict):
            opt["id"] = f"opt_{idx:03d}"
    for idx, tbl in enumerate(inner.get("tables", []), start=1):
        if isinstance(tbl, dict) and not tbl.get("id"):
            tbl["id"] = f"tbl_{idx:03d}"

    # Update title / description to reflect project scope
    n = len(dashboards)
    inner["title"] = f"Project Analysis ({n} batches) — " + inner.get("title", "Multi-Document Report")
    inner["description"] = (
        f"Unified analysis across {n} document batches synthesised into one master dashboard. "
        + inner.get("description", "")
    )

    return merged


# V2 project-level analysis endpoint — up to 20 files, auto-batched
@v2_compat_router.post("/generate-project")
async def generate_response_project_v2(
    files: list[UploadFile], current_user=Depends(get_current_user_optional)
):
    """
    Project Mode analysis.
    Accepts 1–20 files. Files are grouped into batches of 5; each batch is
    analysed independently via generate_full_report_analysis(), then all
    batch dashboards are merged into a single master dashboard.

    Useful for: large reports split across multiple documents,
    1000-page projects, multi-source Six Sigma analysis.
    """
    import json as _json
    from fastapi import HTTPException as _HTTPException
    from fastapi.responses import JSONResponse as _JSONResponse
    import uuid as _uuid

    if not files:
        raise _HTTPException(status_code=400, detail="No files provided")
    if len(files) > 20:
        raise _HTTPException(status_code=400, detail="Maximum 20 files per project")

    BATCH_SIZE = 5
    batches = [files[i:i + BATCH_SIZE] for i in range(0, len(files), BATCH_SIZE)]
    logger.info(f"Project analysis: {len(files)} files → {len(batches)} batch(es)")

    dashboards: list[dict] = []
    batch_documents: list[dict] = []

    for batch_idx, batch in enumerate(batches):
        logger.info(f"Processing batch {batch_idx + 1}/{len(batches)} ({len(batch)} files)")
        try:
            result = await generate_response(batch, current_user)
            # generate_response returns a JSONResponse; extract body
            raw = _json.loads(result.body)
            if isinstance(raw, dict) and raw.get("dashboard"):
                dash = raw["dashboard"]
                dashboards.append(dash)

                # Build per-batch document summary for frontend comparison views
                inner = dash.get("dashboard", dash) if isinstance(dash, dict) else dash
                file_names = [f.filename or f"file_{i+1}" for i, f in enumerate(batch)]
                short_names = file_names[:2]
                label_suffix = ("…" if len(file_names) > 2 else "")
                dmaic_raw = (inner.get("sixSigma") or {}).get("dmaic") or {}
                dmaic_report = (inner.get("dmaicReport") or {})
                # Prefer dmaicReport for richness, fall back to sixSigma.dmaic
                def _phase(key: str) -> str:
                    # guard: dmaic_raw values may be objects if AI returned rich structure
                    raw_val = dmaic_raw.get(key)
                    if isinstance(raw_val, str) and raw_val:
                        return raw_val
                    phase_map = {
                        "define": "definePhase",
                        "measure": "measurePhase",
                        "analyze": "analyzePhase",
                        "improve": "improvePhase",
                        "control": "controlPhase",
                    }
                    rp = dmaic_report.get(phase_map.get(key, ""), {})
                    if isinstance(rp, dict):
                        # join all string values in the phase object into one summary
                        parts = [v for v in rp.values() if isinstance(v, str) and v]
                        return " — ".join(parts[:3]) if parts else ""
                    if isinstance(rp, str):
                        return rp
                    return ""

                batch_documents.append({
                    "id": f"batch_{batch_idx + 1}",
                    "name": f"Batch {batch_idx + 1}: {', '.join(short_names)}{label_suffix}",
                    "kpis": [
                        {"title": k.get("title", ""), "value": k.get("value"), "unit": k.get("unit", "")}
                        for k in (inner.get("kpis") or [])[:15]
                    ],
                    "dmaic": {phase: _phase(phase) for phase in ["define", "measure", "analyze", "improve", "control"]},
                    "sections": [
                        {
                            "title": s.get("title", ""),
                            "summary": s.get("summary", ""),
                            "confidence": s.get("confidence", 0),
                        }
                        for s in (inner.get("sections") or [])[:6]
                    ],
                })
        except Exception as be:
            logger.error(f"Batch {batch_idx + 1} failed: {be}")
            # Continue with remaining batches rather than failing entirely


    def _build_insight_rows_from_dashboard(document_id: str, dashboard_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Flatten traceability index into DB rows for insights table."""
        target = dashboard_data.get("dashboard", dashboard_data) if isinstance(dashboard_data, dict) else {}
        trace_index = target.get("_traceability_index", {})
        if not isinstance(trace_index, dict):
            return []

        rows: List[Dict[str, Any]] = []
        for insight_id, entry in trace_index.items():
            if not isinstance(entry, dict):
                continue
            source_pages = entry.get("source_pages", [])
            if not isinstance(source_pages, list) or len(source_pages) == 0:
                continue
            source_chunks = entry.get("source_chunks", [])
            supporting_groups = []
            if entry.get("group_id"):
                supporting_groups = [entry.get("group_id")]

            rows.append({
                "document_id": document_id,
                "insight_id": str(insight_id),
                "insight_text": entry.get("text", ""),
                "insight_type": entry.get("type", ""),
                "source_pages": source_pages,
                "source_chunks": source_chunks if isinstance(source_chunks, list) else [],
                "supporting_groups": supporting_groups,
                "group_title": entry.get("group_title", ""),
                "section_title": entry.get("section", ""),
                "confidence": entry.get("confidence", None),
                "metadata": {},
            })
        return rows


    def _build_rig_summary_rows_from_dashboard(document_id: str, dashboard_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Flatten group summaries into DB rows for rig_summaries table."""
        target = dashboard_data.get("dashboard", dashboard_data) if isinstance(dashboard_data, dict) else {}
        groups = target.get("_group_summaries", {})
        if not isinstance(groups, dict):
            return []

        rows: List[Dict[str, Any]] = []
        for gk, g in groups.items():
            if not isinstance(g, dict):
                continue
            source_pages = g.get("source_pages", [])
            if not isinstance(source_pages, list) or len(source_pages) == 0:
                continue
            rows.append({
                "document_id": document_id,
                "rig_id": g.get("group_id", gk),
                "rig_title": g.get("group_title", str(gk)),
                "source_pages": source_pages,
                "source_section_ids": g.get("source_section_ids", []),
                "summary": g.get("summary", ""),
                "findings": g.get("merged_findings", []),
                "kpis": g.get("aggregated_kpis", []),
                "risks": g.get("top_risks", []),
                "confidence": g.get("confidence", None),
                "metadata": {
                    "page_range_str": g.get("page_range_str", ""),
                    "confidence_level": g.get("confidence_level", ""),
                },
            })
        return rows

    if not dashboards:
        raise _HTTPException(status_code=500, detail="All batches failed to produce a dashboard")

    merged = _merge_dashboards(dashboards)

    response_data = {
        "doc_id": str(_uuid.uuid4()),
        "task_id": str(_uuid.uuid4()),
        "status": "completed",
        "message": (
            f"Project analysis complete — {len(files)} documents "
            f"across {len(batches)} batch(es) synthesised into one dashboard"
        ),
        "dashboard": merged,
        "processing_time": 0,
        "files_processed": len(files),
        "batches_processed": len(dashboards),
        "documents": batch_documents,
    }

    response = _JSONResponse(content=response_data)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ── Document endpoints (mirror endpoints.py for the active pipeline) ─────────

@v2_compat_router.get("/documents/{doc_id}")
async def get_document_v2(doc_id: str, current_user=Depends(get_current_user_optional)):
    """Get document info by ID — checks LocalStorage and cache."""
    from fastapi import HTTPException
    
    # Try LocalStorage first
    try:
        from services.storage.local import LocalStorage
        storage = LocalStorage()
        doc = storage.get_document(doc_id)
        if doc:
            return {
                "document": {
                    "id": doc["id"],
                    "file_name": doc.get("metadata", {}).get("file_name", "Unknown"),
                    "status": doc.get("status", "unknown"),
                    "created_at": doc.get("created_at", ""),
                },
                "chunks_count": 0,
                "edges_count": 0,
                "has_dashboard": doc.get("dashboard_data") is not None,
            }
    except Exception as e:
        logger.warning(f"LocalStorage lookup failed for {doc_id}: {e}")
    
    raise HTTPException(status_code=404, detail="Document not found")


@v2_compat_router.get("/documents/{doc_id}/dashboard")
async def get_document_dashboard_v2(doc_id: str, current_user=Depends(get_current_user_optional)):
    """Get dashboard data for a specific document — checks LocalStorage and cache."""
    from fastapi import HTTPException
    
    # Try LocalStorage first
    try:
        from services.storage.local import LocalStorage
        storage = LocalStorage()
        doc = storage.get_document(doc_id)
        if doc and doc.get("dashboard_data"):
            dashboard_data = doc["dashboard_data"]
            # Flatten: merge inner dashboard with outer meta/views
            inner = dashboard_data.get("dashboard", dashboard_data)
            result = dict(inner) if isinstance(inner, dict) else {}
            for k, v in dashboard_data.items():
                if k != "dashboard" and k not in result:
                    result[k] = v
            return result
        elif doc and doc.get("status") == "processing":
            return {
                "status": "processing",
                "message": "Document is still being processed",
                "kpis": [],
                "charts": [],
            }
    except Exception as e:
        logger.warning(f"LocalStorage dashboard lookup failed for {doc_id}: {e}")
    
    # Fallback: search cache by doc_id
    try:
        _cache = get_cache_service()
        _sqlite = _cache._sqlite
        cur = _sqlite._conn.cursor()
        now_iso = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        cur.execute(
            "SELECT value FROM cache WHERE key LIKE 'dashboard:%' AND expires_at > ? ORDER BY expires_at DESC",
            (now_iso,)
        )
        for row in cur.fetchall():
            try:
                d = json.loads(row[0])
                if d.get("doc_id") == doc_id:
                    payload = d.get("dashboard", d)
                    inner = payload.get("dashboard", payload) if isinstance(payload, dict) else payload
                    result = dict(inner) if isinstance(inner, dict) else {}
                    if isinstance(payload, dict):
                        for k, v in payload.items():
                            if k != "dashboard" and k not in result:
                                result[k] = v
                    return result
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Cache lookup failed for doc_id {doc_id}: {e}")
    
    raise HTTPException(status_code=404, detail="Dashboard data not found for this document")


@v2_compat_router.get("/task/{task_id}")
async def get_task_status_v2(task_id: str, current_user=Depends(get_current_user_optional)):
    """Get task processing status — for polling from frontend."""
    from fastapi import HTTPException
    
    try:
        from services.storage.local import LocalStorage
        storage = LocalStorage()
        task = storage.get_task_status(task_id)
        if task:
            return task
    except Exception as e:
        logger.warning(f"Task status lookup failed for {task_id}: {e}")
    
    raise HTTPException(status_code=404, detail="Task not found")


@v2_compat_router.get("/dashboard/latest")
async def get_latest_dashboard_v2(current_user=Depends(get_current_user_optional)):
    """
    Returns the most recently uploaded dashboard from cache (SQLite/Redis).
    Falls back to demo_result.json only if cache is completely empty.
    """
    from pathlib import Path

    try:
        # --- Try to find the most recent dashboard in SQLite cache ---
        _cache = get_cache_service()
        _sqlite = _cache._sqlite
        cur = _sqlite._conn.cursor()
        now_iso = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        cur.execute(
            "SELECT value FROM cache WHERE key LIKE 'dashboard:%' AND expires_at > ? ORDER BY expires_at DESC LIMIT 20",
            (now_iso,)
        )
        rows = cur.fetchall()

        # Prefer the most recent entry that has real data (kpis > 0 and no AI error)
        best_row = None
        for candidate in rows:
            try:
                d = json.loads(candidate[0])
                payload = d.get("dashboard", d)
                inner = payload.get("dashboard", payload) if isinstance(payload, dict) else payload
                if not isinstance(inner, dict):
                    continue
                kpi_count = len(inner.get("kpis") or [])
                desc = inner.get("description", "")
                if kpi_count > 0 and "AI service error" not in desc:
                    best_row = candidate
                    break
            except Exception:
                continue
        # Fall back to most recent if nothing has real data
        row = best_row or (rows[0] if rows else None)

        if row:
            cached = json.loads(row[0])
            logger.info("get_latest_dashboard_v2: returning dashboard from cache")
            # cached is the full upload response: { doc_id, task_id, status, dashboard, ... }
            dashboard_payload = cached.get("dashboard", cached)
            # dashboard_payload has structure: { meta, autoClassification, dashboard: { kpis, charts, ... } }
            # Frontend DashboardResponse expects: { meta, autoClassification, kpis, charts, sixSigma, ... } (flat)
            inner = dashboard_payload.get("dashboard", dashboard_payload)
            result = dict(inner)  # title, kpis, charts, sixSigma, tables, optimizationSuggestions, ...
            if "meta" in dashboard_payload:
                result["meta"] = dashboard_payload["meta"]
            if "autoClassification" in dashboard_payload:
                result["autoClassification"] = dashboard_payload["autoClassification"]
            return result

        # --- No cache entry found — fall back to demo file (if allowed) ---
        
        if settings.ALLOW_DEMO_DATA_FALLBACK:
            demo_file = Path(__file__).parent / "data" / "demo_result_drilling.json"
            if demo_file.exists():
                logger.warning(f"⚠️ Cache empty — returning DEMO DATA (set ALLOW_DEMO_DATA_FALLBACK=false to disable)")
                logger.warning(f"   File: {demo_file}")
                logger.warning(f"   This is NOT real data — for development only")
                with open(demo_file, 'r') as f:
                    demo_data = json.load(f)
                # Flatten demo data the same way as cached data
                payload = demo_data.get("dashboard", demo_data)
                inner = payload.get("dashboard", payload)
                result = dict(inner)
                if "meta" in payload:
                    result["meta"] = payload["meta"]
                if "autoClassification" in payload:
                    result["autoClassification"] = payload["autoClassification"]
                # Add warning flag to response
                result["_warning"] = "Demo data returned - not real production data"
                return result
        else:
            logger.error("❌ Cache empty and demo data disabled (ALLOW_DEMO_DATA_FALLBACK=false)")
            logger.error("   No real data available for this document")

        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No dashboard data available. Please upload a file first.")

    except Exception as e:
        logger.error(f"Error fetching latest dashboard: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard: {str(e)}")


@v2_compat_router.get("/insight/{insight_id}")
async def get_insight_traceability_v2(
    insight_id: str,
    document_id: Optional[str] = None,
    current_user=Depends(get_current_user_optional),
):
    """Return traceability details for a specific insight_id from the latest dashboard."""
    from fastapi import HTTPException

    # First try persisted traceability store
    stored = await supabase_service.get_insight(insight_id, document_id=document_id)
    if stored:
        sp = stored.get("source_pages", [])
        if isinstance(sp, str):
            try:
                sp = json.loads(sp)
            except Exception:
                sp = []
        sc = stored.get("source_chunks", [])
        if isinstance(sc, str):
            try:
                sc = json.loads(sc)
            except Exception:
                sc = []
        groups = stored.get("supporting_groups", [])
        if isinstance(groups, str):
            try:
                groups = json.loads(groups)
            except Exception:
                groups = []

        return {
            "insight_id": stored.get("insight_id", insight_id),
            "insight": stored.get("insight_text", ""),
            "type": stored.get("insight_type", ""),
            "source_pages": sp if isinstance(sp, list) else [],
            "source_chunks": sc if isinstance(sc, list) else [],
            "supporting_groups": groups if isinstance(groups, list) else [],
            "group_title": stored.get("group_title", ""),
            "section": stored.get("section_title", ""),
            "document_id": stored.get("document_id", document_id),
        }

    # Fallback to latest in-memory dashboard cache
    dashboard = await get_latest_dashboard_v2(current_user=current_user)
    if not isinstance(dashboard, dict):
        raise HTTPException(status_code=500, detail="Invalid dashboard payload")

    trace_index = dashboard.get("_traceability_index", {})
    if not isinstance(trace_index, dict) or not trace_index:
        raise HTTPException(status_code=404, detail="Traceability index not available")

    entry = trace_index.get(insight_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Insight not found: {insight_id}")

    return {
        "insight_id": insight_id,
        "insight": entry.get("text", ""),
        "type": entry.get("type", ""),
        "source_pages": entry.get("source_pages", []),
        "source_chunks": entry.get("source_chunks", []),
        "supporting_groups": [entry.get("group_id")] if entry.get("group_id") else [],
        "group_title": entry.get("group_title", ""),
        "section": entry.get("section", ""),
    }


def _call_llm_rig_aggregation(rig_id: str, chunks_payload: list) -> dict:
    """Call Gemini to aggregate chunk data into structured rig findings/KPIs/risks."""
    if client is None:
        raise RuntimeError("Gemini client not configured")

    prompt = f"""You are analyzing industrial rig data.

INPUT:
- Multiple chunk-level records for rig: {rig_id}
- Each chunk contains content and source_pages

TASK:
1. Extract key findings (no duplicates)
2. Extract KPIs (with values + units if present)
3. Identify top risks
4. Preserve ALL source_pages
5. DO NOT infer missing data

RULES:
- Every insight MUST include source_pages
- If data missing → say "INSUFFICIENT DATA"
- Do NOT generalize

OUTPUT STRICT JSON (no markdown fences):

{{
  "summary_findings": [
    {{
      "insight": "...",
      "source_chunks": [...],
      "source_pages": [...],
      "confidence": 0.0
    }}
  ],
  "aggregated_kpis": [
    {{
      "name": "...",
      "value": "...",
      "unit": "...",
      "source_pages": [...]
    }}
  ],
  "top_risks": [
    {{
      "risk": "...",
      "severity": "low|medium|high",
      "source_pages": [...]
    }}
  ]
}}

DATA:
{json.dumps(chunks_payload[:25], default=str)}
"""
    max_retries = 2
    retry_delay = 2
    last_error = None
    for attempt in range(max_retries):
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    client.models.generate_content,
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0,
                    ),
                )
                response = future.result(timeout=30)  # 30s max per LLM call
            if response.text:
                # Try direct parse first, then regex fallback
                try:
                    return json.loads(response.text)
                except json.JSONDecodeError:
                    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(0))
            raise ValueError("Empty or unparseable LLM response")
        except Exception as exc:
            last_error = exc
            err_str = str(exc)
            # Don't retry on auth/config errors or client issues
            if any(s in err_str for s in ("API_KEY_INVALID", "API Key not found", "not configured", "No Gemini API keys")):
                logger.error("LLM rig aggregation auth failure for %s: %s", rig_id, err_str.splitlines()[0])
                break
            if attempt < max_retries - 1 and any(s in err_str for s in ("503", "429", "RESOURCE_EXHAUSTED")):
                logger.warning("LLM rig aggregation retry %d/%d for %s: %s", attempt + 1, max_retries, rig_id, err_str.splitlines()[0])
                import time
                time.sleep(retry_delay)
                retry_delay *= 2
            elif attempt < max_retries - 1:
                # Non-retryable error — don't wait long
                break
            else:
                break
    logger.error("LLM rig aggregation failed for %s after %d attempts: %s", rig_id, max_retries, last_error)
    # Return empty structure so pipeline doesn't crash
    return {"summary_findings": [], "aggregated_kpis": [], "top_risks": []}


def _validate_rig_summary_traceability(summary: dict) -> None:
    """Ensure every finding, KPI, and risk has source_pages."""
    for f in summary.get("summary_findings", []):
        if not f.get("source_pages"):
            raise ValueError(f"Missing traceability in findings: {f.get('insight', '')[:80]}")
    for k in summary.get("aggregated_kpis", []):
        if not k.get("source_pages"):
            raise ValueError(f"Missing traceability in KPIs: {k.get('name', '')[:80]}")
    for r in summary.get("top_risks", []):
        if not r.get("source_pages"):
            raise ValueError(f"Missing traceability in risks: {r.get('risk', '')[:80]}")


@v2_compat_router.post("/process/{doc_id}")
async def process_document_chunks_to_rig_summaries(doc_id: str, use_llm: bool = False, current_user=Depends(get_current_user_optional)):
    """Process existing chunks for a document into rig summaries (chunk → rig pipeline).
    
    Set use_llm=true to use Gemini for real aggregation (requires valid API key and quota).
    Defaults to rule-based aggregation for fast, reliable results.
    """
    from fastapi import HTTPException
    from collections import defaultdict
    import uuid as _uuid

    doc = await supabase_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = await supabase_service.get_document_chunks(doc_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="No chunks found for document")

    llm_available = use_llm and client is not None
    if use_llm and client is None:
        logger.warning("LLM requested but Gemini client not configured, using rule-based fallback")

    # Group chunks into synthetic rigs based on chunk_index ranges
    # Each rig covers a batch of consecutive chunks
    RIG_SIZE = max(1, len(chunks) // 10) or 1  # ~10 rigs per document
    groups = defaultdict(list)
    for ch in chunks:
        idx = ch.get("chunk_index", 0)
        rig_num = idx // RIG_SIZE
        groups[f"rig_{rig_num:03d}"] = groups.get(f"rig_{rig_num:03d}", [])
        groups[f"rig_{rig_num:03d}"].append(ch)

    # Build rig summary rows via LLM aggregation
    summaries_data = []
    llm_errors = []
    for rig_id, rig_chunks in groups.items():
        # Derive page numbers from chunk indices (proxy when real pages unavailable)
        source_pages = sorted(set(c.get("chunk_index", 0) + 1 for c in rig_chunks))
        chunk_ids = [c.get("id") for c in rig_chunks]

        # Prepare lightweight payload for LLM (text + pages only)
        llm_payload = [
            {"chunk_id": c.get("id"), "content": c.get("chunk_text", ""), "source_pages": [c.get("chunk_index", 0) + 1]}
            for c in rig_chunks
        ]

        # LLM aggregation with batching for large rigs
        if llm_available:
            try:
                if len(llm_payload) > 25:
                    batches = [llm_payload[i:i + 25] for i in range(0, len(llm_payload), 25)]
                    partials = []
                    for b in batches:
                        partial = _call_llm_rig_aggregation(rig_id, b)
                        partials.append(partial)
                    # Merge pass — feed partial results back for consolidation
                    merged = _call_llm_rig_aggregation(rig_id, partials)
                else:
                    merged = _call_llm_rig_aggregation(rig_id, llm_payload)

                # Validate traceability; if invalid, patch source_pages from chunk data
                try:
                    _validate_rig_summary_traceability(merged)
                except ValueError as ve:
                    logger.warning("Traceability gap in %s, patching: %s", rig_id, ve)
                    for f in merged.get("summary_findings", []):
                        if not f.get("source_pages"):
                            f["source_pages"] = source_pages
                    for k in merged.get("aggregated_kpis", []):
                        if not k.get("source_pages"):
                            k["source_pages"] = source_pages
                    for r in merged.get("top_risks", []):
                        if not r.get("source_pages"):
                            r["source_pages"] = source_pages
            except Exception as exc:
                logger.error("LLM aggregation failed for %s: %s", rig_id, exc)
                llm_errors.append({"rig_id": rig_id, "error": str(exc)})
                merged = None

        if not llm_available or merged is None:
            # Rule-based fallback summary
            merged = {
                "summary_findings": [{"insight": f"Aggregated findings for {rig_id}", "source_chunks": chunk_ids, "source_pages": source_pages, "confidence": 0.5}],
                "aggregated_kpis": [{"name": f"chunk_count_{rig_id}", "value": str(len(rig_chunks)), "unit": "chunks", "source_pages": source_pages}],
                "top_risks": [{"risk": f"Coverage gap analysis pending for {rig_id}", "severity": "medium", "source_pages": source_pages}],
            }

        snippet = rig_chunks[0].get("chunk_text", "")[:200] if rig_chunks else ""

        summaries_data.append({
            "document_id": doc_id,
            "rig_id": rig_id,
            "rig_title": f"Section group {rig_id}",
            "source_pages": source_pages,
            "source_section_ids": chunk_ids,
            "summary": merged.get("summary_findings", [{}])[0].get("insight", "") if merged.get("summary_findings") else "",
            "findings": merged.get("summary_findings", []),
            "kpis": merged.get("aggregated_kpis", []),
            "risks": merged.get("top_risks", []),
            "confidence": 0.7,
            "metadata": {"pipeline": "llm_rig_aggregation" if llm_available else "rule_based_fallback", "snippet": snippet},
        })

    result = await supabase_service.store_rig_summaries(summaries_data)
    return {
        "status": "processed",
        "doc_id": doc_id,
        "rigs_created": len(summaries_data),
        "llm_errors": llm_errors,
        "storage_result": result,
    }


@v2_compat_router.get("/report/{doc_id}")
async def get_report_from_rig_summaries_v2(doc_id: str, current_user=Depends(get_current_user_optional)):
    """Build final report payload from persisted rig_summaries/insights (vectorless synthesis path)."""
    from fastapi import HTTPException

    doc = await supabase_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user and doc.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    rig_rows = await supabase_service.get_rig_summaries(doc_id)
    if not rig_rows:
        raise HTTPException(status_code=404, detail="No rig summaries found for document")

    def _to_list(v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
        return []

    rig_summaries = []
    all_pages = set()
    all_chunks = 0
    for row in rig_rows:
        pages = _to_list(row.get("source_pages", []))
        all_pages.update(p for p in pages if isinstance(p, int))

        findings = _to_list(row.get("findings", []))
        kpis = _to_list(row.get("kpis", []))
        risks = _to_list(row.get("risks", []))
        all_chunks += len(findings) + len(kpis) + len(risks)

        rig_summaries.append({
            "rig_id": row.get("rig_id"),
            "rig_metadata": {
                "report_sections": len(_to_list(row.get("source_section_ids", []))),
            },
            "summary_findings": findings,
            "aggregated_kpis": kpis,
            "top_risks": risks,
            "source_pages": pages,
        })

    # Keep executive_summary lightweight; detailed drill-down stays in /insight endpoint.
    executive_summary = []
    for r in rig_summaries[:10]:
        if r.get("summary_findings"):
            executive_summary.extend(r.get("summary_findings")[:2])

    report = {
        "doc_id": doc_id,
        "executive_summary": executive_summary,
        "dmaic": {},
        "rig_summaries": rig_summaries,
        "metrics": {
            "coverage": None,
            "total_chunks": all_chunks,
            "used_chunks": all_chunks,
            "source_pages": sorted(all_pages),
        },
    }
    return report


@v2_compat_router.get("/document/{doc_id}/page/{page_number}")
async def get_document_page_v2(
    doc_id: str,
    page_number: int,
    current_user=Depends(get_current_user_optional),
):
    """Return raw extracted text for one page of a stored PDF document."""
    from fastapi import HTTPException

    if page_number < 1:
        raise HTTPException(status_code=400, detail="page_number must be >= 1")

    doc = await supabase_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Enforce ownership for authenticated users
    if current_user and doc.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Resolve local path candidates
    metadata = doc.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}

    path_candidates = []
    original_file_path = doc.get("original_file_path")
    if isinstance(original_file_path, str) and original_file_path:
        path_candidates.append(original_file_path)
    if isinstance(metadata, dict):
        original_location = metadata.get("original_location")
        if isinstance(original_location, str) and original_location:
            path_candidates.append(original_location)

    pdf_doc = None
    try:
        local_path = next((p for p in path_candidates if os.path.exists(p)), None)
        if local_path:
            pdf_doc = fitz.open(local_path)
        else:
            # Fallback: try downloading from Supabase storage by storage key
            storage_key = doc.get("original_file_path")
            pdf_bytes = None
            if isinstance(storage_key, str) and storage_key and getattr(supabase_service, "client", None):
                try:
                    pdf_bytes = supabase_service.client.storage.from_("documents").download(storage_key)
                except Exception:
                    pdf_bytes = None
            if not pdf_bytes:
                raise HTTPException(
                    status_code=404,
                    detail="Document file is not accessible for page retrieval",
                )
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        total_pages = len(pdf_doc)
        if page_number > total_pages:
            raise HTTPException(
                status_code=404,
                detail=f"Page {page_number} out of range (1-{total_pages})",
            )

        page = pdf_doc[page_number - 1]
        text = page.get_text("text").strip()

        return {
            "doc_id": doc_id,
            "page_number": page_number,
            "total_pages": total_pages,
            "text": text,
        }
    finally:
        if pdf_doc:
            pdf_doc.close()
