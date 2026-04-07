"""
Agent 2 — Analytics & DMAIC Agent
Applies Six Sigma reasoning to produce DMAIC phases, sigma level, root causes.
"""
import json
from typing import Any, Dict
from agents.base_agent import BaseAgent


class DMAICAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "DMAICAgent"

    def build_prompt(self, ctx: Dict[str, Any]) -> str:
        interp = ctx.get("data_interpretation", {})
        content = ctx.get("raw_content", "")[:80_000]

        # ── Use full-coverage section analysis when available ────────
        sa = ctx.get("section_analysis")
        sa_block = ""
        if sa and sa.get("sections"):
            six_sigma = sa.get("six_sigma", {})
            sa_block = f"""

FULL-COVERAGE ANALYSIS (covers 100% of document — {sa.get('sections_analyzed', '?')} sections):
SIX SIGMA DATA: {json.dumps(six_sigma, default=str)[:6000]}
ALL FINDINGS: {json.dumps(sa.get('all_findings', [])[:60], default=str)[:10000]}
ALL RISKS: {json.dumps(sa.get('all_risks', [])[:30], default=str)[:5000]}
KPIs: {json.dumps(sa.get('kpis', [])[:40], default=str)[:8000]}

IMPORTANT: The structured data above covers the ENTIRE document.
Prioritize it over the truncated content excerpt below.
"""

        return f"""
You are the Analytics & DMAIC Agent — a Six Sigma Black Belt for Oil & Gas operations.

INTERPRETED DATA:
{json.dumps(interp, indent=2)[:8000]}
{sa_block}
ORIGINAL CONTENT EXCERPT (may be truncated):
{content[:20000]}

Apply Six Sigma DMAIC methodology. Return ONLY this JSON:
{{
  "methodology": "DMAIC|DMADV",
  "sigma_level": "string",
  "dpmo": 0,
  "process_capability_cpk": 0.0,
  "statistical_validity": true,
  "dmaic": {{
    "define": {{
      "problem_statement": "string — specific, measurable (not generic)",
      "ctqs": ["string — Critical to Quality parameter"],
      "financial_exposure": {{"min": 0, "max": 0, "unit": "$|₹", "confidence": 0.0}},
      "scope": "string",
      "goal_statement": "string"
    }},
    "measure": {{
      "baseline_metrics": [
        {{"kpi": "string", "value": "string", "unit": "string", "target": "string", "gap": "string"}}
      ],
      "data_confidence": 0.0,
      "measurement_system_adequacy": "Adequate|Marginal|Inadequate",
      "primary_metric": "string",
      "secondary_metrics": ["string"]
    }},
    "analyze": {{
      "root_causes": [
        {{"cause": "string", "confidence": 0.0, "evidence": "string", "category": "Machine|Method|Material|Man|Measurement|Environment"}}
      ],
      "correlations": ["string"],
      "pareto_top3": ["string — 80% of the problem attributable to these factors"],
      "fishbone_summary": "string"
    }},
    "improve": {{
      "recommended_actions": [
        {{"action": "string", "expected_impact": "string", "priority": "high|medium|low", "effort": "low|medium|high"}}
      ],
      "expected_sigma_lift": "string",
      "expected_financial_benefit": "string",
      "quick_wins": ["string — implementable within 30 days"]
    }},
    "control": {{
      "control_plan": ["string — specific monitoring action"],
      "monitoring_kpis": ["string"],
      "control_charts_needed": ["string"],
      "escalation_triggers": ["string — threshold that triggers escalation"]
    }}
  }},
  "key_findings": [
    {{"finding": "string", "severity": "High|Medium|Low", "financial_impact": "string"}}
  ]
}}
"""

    def _fallback(self):
        return {
            "methodology": "DMAIC",
            "sigma_level": "3.5σ",
            "statistical_validity": False,
            "dmaic": {
                "define": {"problem_statement": "Analysis incomplete", "ctqs": [], "financial_exposure": {}},
                "measure": {"baseline_metrics": [], "data_confidence": 0.3},
                "analyze": {"root_causes": [], "correlations": []},
                "improve": {"recommended_actions": [], "quick_wins": []},
                "control": {"control_plan": [], "monitoring_kpis": []}
            },
            "key_findings": []
        }
