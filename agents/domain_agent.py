"""
Agent 3 — Domain Intelligence Agent (Oil & Gas Brain)
Injects industry expertise: KPI mapping, failure modes, use-case classification.
"""
import json
from typing import Any, Dict
from .base_agent import BaseAgent


class DomainIntelligenceAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "DomainIntelligenceAgent"

    def build_prompt(self, ctx: Dict[str, Any]) -> str:
        interp = ctx.get("data_interpretation", {})
        dmaic = ctx.get("dmaic_analysis", {})
        return f"""
You are the Domain Intelligence Agent — an Oil & Gas subject matter expert with 25+ years in upstream, midstream, and downstream operations.

DATA INTERPRETATION:
{json.dumps(interp, indent=2)[:4000]}

DMAIC ANALYSIS:
{json.dumps(dmaic, indent=2)[:4000]}

Enrich this analysis with Oil & Gas domain expertise. Return ONLY this JSON:
{{
  "use_case_classification": "Production Optimization|Asset Reliability|Drilling Performance|HSE|Refinery / Process Optimization|Pipeline Integrity|Well Intervention|Energy Management",
  "industry_kpis": [
    {{
      "name": "OEE|MTBF|MTTR|NPT|Lifting Cost per Barrel|Flaring Rate|Energy Intensity|ROP|Well Availability|Process Utilization",
      "current_value": "string",
      "industry_median": "string",
      "p75_benchmark": "string",
      "performance_gap": "string",
      "direction": "increase|decrease",
      "unit": "string"
    }}
  ],
  "failure_mode_library": [
    {{
      "failure_mode": "string — specific technical failure (e.g. pump cavitation, heat exchanger fouling)",
      "probability": 0.0,
      "severity": "High|Medium|Low",
      "detectability": "Easy|Moderate|Difficult",
      "rpn": 0,
      "typical_cause": "string",
      "industry_best_practice": "string"
    }}
  ],
  "regulatory_flags": ["string — API, ISO, OSHA, EPA standards relevant to findings"],
  "benchmarking": {{
    "vs_industry_median": "Above|Below|At Par",
    "vs_top_quartile": "Above|Below|Near",
    "peer_gap": "string — quantified performance gap"
  }},
  "domain_context": "string — 2-3 sentences of O&G context that explains why these findings matter"
}}
"""

    def _fallback(self):
        return {
            "use_case_classification": "Production Optimization",
            "industry_kpis": [],
            "failure_mode_library": [],
            "regulatory_flags": [],
            "benchmarking": {"vs_industry_median": "Below", "vs_top_quartile": "Below"},
            "domain_context": "Domain enrichment unavailable."
        }
