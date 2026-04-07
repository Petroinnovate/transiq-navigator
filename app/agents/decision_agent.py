"""
Agent 4 — Decision Intelligence Agent (Core Brain)
Converts analysis → trusted, traceable, benchmark-backed executive decisions.
Uses DCI scoring, traceability chains, and decision-centric language.
"""
import json
from typing import Any, Dict
from .base_agent import BaseAgent


class DecisionIntelligenceAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "DecisionIntelligenceAgent"

    def _system_instruction(self) -> str:
        return (
            "You are the Decision Intelligence Core of TransIQ — an Industrial Decision OS. "
            "You embody THREE non-negotiable pillars:\n"
            "PILLAR 1 — DECISION OS: Output decisions, not observations. "
            "Every item is action-oriented with an owner and timeline. "
            "NEVER 'insights suggest' — ALWAYS 'Decision:', 'Risk:', 'Action Required:'.\n"
            "PILLAR 2 — SIX SIGMA + FINANCIAL IMPACT: Every decision must include "
            "(a) financial impact in $ or %, (b) cost of inaction, (c) ROI or payback period. "
            "Apply DMAIC. Cite sigma level and R² where statistically valid.\n"
            "PILLAR 3 — EXPLAINABLE & AUDITABLE AI: Every recommendation must state "
            "WHY (key drivers), WHAT DATA (source, time range, quality), "
            "HOW (method + statistic), ASSUMPTIONS, and LIMITATIONS. "
            "All outputs must be traceable, reproducible, and logically consistent."
            "Respond ONLY in valid JSON."
        )

    def build_prompt(self, ctx: Dict[str, Any]) -> str:
        interp = ctx.get("data_interpretation", {})
        dmaic = ctx.get("dmaic_analysis", {})
        domain = ctx.get("domain_intelligence", {})
        return f"""
You are the Decision Intelligence Agent — the core brain of TransIQ.

Inputs from upstream agents:
DATA INTERPRETATION: {json.dumps(interp, indent=2)[:3000]}
DMAIC ANALYSIS: {json.dumps(dmaic, indent=2)[:5000]}
DOMAIN INTELLIGENCE: {json.dumps(domain, indent=2)[:3000]}

Convert this analysis into TRUSTED, TRACEABLE decisions using Decision-Centric Language.

LANGUAGE RULES (MANDATORY):
- NEVER write "insights suggest", "data indicates", "it appears"
- ALWAYS prefix with "Decision:", "Action Required:", "Risk:", "Finding:"
- Every claim must be evidence-backed with a data reference

Return ONLY this JSON:
{{
  "top_decisions": [
    {{
      "id": "D1",
      "title": "Decision: [imperative verb, max 8 words]",
      "rationale": "string — why this decision, backed by specific data",
      "financial_impact": "string — quantified $ or % impact",
      "urgency": "Immediate|30-day|Quarterly",
      "confidence_score": 0,
      "traceability": {{
        "data_sources": ["string — specific source with time range"],
        "analytical_methods": ["string — method + key statistic e.g. R²=0.82"],
        "supporting_evidence": ["string — quantified finding"]
      }},
      "benchmark_position": "string — above|below|at par vs industry P50/P75",
      "decision_confidence_index": {{
        "score": 0,
        "data_completeness": "string — n/25 rationale",
        "model_confidence": "string — n/25 rationale",
        "historical_accuracy": "string — n/25 rationale",
        "variability": "string — n/25 rationale"
      }},
      "risk_if_ignored": "string — specific consequence with financial/operational impact"
    }}
  ],
  "top_risks": [
    {{
      "id": "R1",
      "title": "Risk: [plain-language threat, max 8 words]",
      "severity": "High|Medium|Low",
      "probability": "High|Medium|Low",
      "financial_impact": "string — quantified exposure",
      "operational_impact": "string",
      "time_to_impact": "string",
      "mitigation": "string — specific action"
    }}
  ],
  "strategic_insights": [
    "string — Finding: [fact-based, no hedging language]"
  ]
}}
"""

    def _fallback(self):
        return {
            "top_decisions": [],
            "top_risks": [],
            "strategic_insights": []
        }
