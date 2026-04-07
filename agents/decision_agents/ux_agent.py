"""
Agent 6 — UX Simplification Agent
Converts all upstream agent outputs into the three progressive disclosure layers:
CEO View, Manager View, Engineer View, and Boardroom Mode slides.
"""
import json
from typing import Any, Dict
from agents.base_agent import BaseAgent


class UXSimplificationAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "UXSimplificationAgent"

    def _system_instruction(self) -> str:
        return (
            "You are the UX Layer of TransIQ \u2014 an Industrial Decision OS. "
            "Your ONLY job is converting multi-agent analysis into four audience-optimised views. "
            "THREE LAWS:\n"
            "LAW 1 \u2014 DECISION-CENTRIC: Every item starts with an action verb or one of: "
            "'Decision:', 'Risk:', 'Action Required:'. NEVER 'insights suggest'. \n"
            "LAW 2 \u2014 FINANCIALLY QUANTIFIED: Every CEO/Manager item must include "
            "a $ or % impact. Every risk must include 'Cost of inaction: $X'. \n"
            "LAW 3 \u2014 EXPLAINABLE: Every engineering recommendation must include "
            "the WHY (driver), DATA (source), and METHOD used. "
            "Boardroom slides must state the financial headline first. \n"
            "Audience layers: CEO=30s/no jargon, Manager=DMAIC/weekly ops, "
            "Engineer=sigma/Cpk/FMEA, Boardroom=board-grade narrative slides. "
            "Respond ONLY in valid JSON."
        )

    def build_prompt(self, ctx: Dict[str, Any]) -> str:
        decisions = ctx.get("decision_intelligence", {})
        dmaic = ctx.get("dmaic_analysis", {})
        ops = ctx.get("operationalization", {})
        domain = ctx.get("domain_intelligence", {})
        interp = ctx.get("data_interpretation", {})
        return f"""
You are the UX Simplification Agent. Synthesize all agent outputs into three progressive disclosure layers.

DECISION INTELLIGENCE: {json.dumps(decisions, indent=2)[:4000]}
DMAIC ANALYSIS: {json.dumps(dmaic.get("dmaic", {}), indent=2)[:3000]}
OPERATIONALIZATION: {json.dumps(ops, indent=2)[:3000]}
DOMAIN CONTEXT: {json.dumps(domain, indent=2)[:2000]}

Return ONLY this JSON with all four layers:
{{
  "ceo_view": {{
    "decisions": [
      {{
        "title": "string — ACTION VERB first, max 8 words, ZERO jargon",
        "impact": "string — quantified $ or KPI, max 1 line",
        "urgency": "High|Medium|Low"
      }}
    ],
    "risks": [
      {{
        "title": "string — plain-English threat, max 8 words",
        "severity": "High|Medium|Low",
        "financial_impact": "string — quantified loss or consequence, 1 line"
      }}
    ],
    "actions": [
      {{
        "title": "string — imperative verb, max 8 words",
        "owner": "string — role (e.g., Operations Manager, COO)",
        "timeline": "string — time-bound (e.g., 30 days, Before Q2)"
      }}
    ]
  }},
  "manager_view": {{
    "dmaic": {{
      "define": "string — problem statement + financial exposure, 1-2 sentences, manager-language",
      "measure": "string — baseline metrics + data confidence, 1-2 sentences",
      "analyze": "string — top root causes with confidence %, 1-2 sentences",
      "improve": "string — recommended actions + expected sigma lift, 1-2 sentences",
      "control": "string — monitoring plan + KPIs tracked, 1-2 sentences"
    }},
    "recommendations": [
      {{
        "title": "string",
        "impact": "string — quantified expected improvement",
        "timeline": "string — time-bound",
        "priority": "high|medium|low",
        "owner": "string — role"
      }}
    ],
    "kpi_tracking": [
      {{
        "name": "string",
        "current": "string",
        "target": "string",
        "gap": "string",
        "status": "on-track|at-risk|off-track",
        "trend": "improving|deteriorating|stable"
      }}
    ]
  }},
  "engineer_view": {{
    "data_references": [
      "string — specific dataset/table/section with page or row reference"
    ],
    "models": [
      "string — statistical model with key metric (e.g. regression R²=0.78, Cpk=0.89)"
    ],
    "root_cause_analysis": [
      "string — detailed causal chain with quantified evidence"
    ],
    "failure_modes": [
      {{
        "cause": "string — specific technical failure mode",
        "probability": 0.0,
        "detection": "string — how it is detected",
        "mitigation": "string — specific corrective action",
        "rpn": 0
      }}
    ],
    "assumptions": [
      "string — stated assumption with impact if incorrect"
    ],
    "statistical_summary": {{
      "sigma_level": "string",
      "cpk": 0.0,
      "r_squared": 0.0,
      "confidence_interval": "string"
    }}
  }},
  "boardroom_mode": {{
    "executive_summary": "string — exactly 3-5 sentences: [Situation]. [Key problem + financial impact]. [Root cause]. [Recommended decision]. [Expected outcome if acted upon].",
    "slides": {{
      "summary": [
        "string — each bullet max 10 words, 5-7 bullets, no jargon"
      ],
      "decisions": [
        "string — Decision: [action] → Impact: [quantified]"
      ],
      "risks": [
        "string — Risk: [threat] | Severity: [H/M/L] | Loss: [$X] | Action: [mitigation]"
      ],
      "actions": [
        "string — [Action] | Owner: [role] | By: [deadline] | KPI: [metric]"
      ],
      "kpi_impact": [
        "string — [KPI Name]: [current] → [target] ([direction] [%], [timeframe])"
      ]
    }}
  }}
}}

MANDATORY CONSTRAINTS:
- CEO View: exactly 3 decisions, 3 risks, 3 actions
- Each CEO item: max 8 words title, max 1-2 lines — readable in under 30 seconds
- NO technical jargon in CEO View (no sigma, no Cpk, no DPMO)
- Manager View dmaic: 1-2 sentences each, evidence-referenced
- Engineer View: full technical depth with actual statistics
- Boardroom slides: exactly 5-7 bullets in summary, decisions/risks/actions/kpi_impact: 3-5 items each
- All language: Decision-Centric — never "insights suggest" — always "Decision:", "Risk:", "Action Required:"
"""

    def _fallback(self):
        return {
            "ceo_view": {
                "decisions": [{"title": "Decision: Review operational performance now", "impact": "Financial exposure identified", "urgency": "High"}],
                "risks": [{"title": "Risk: Continued losses without action", "severity": "High", "financial_impact": "TBD"}],
                "actions": [{"title": "Initiate performance review immediately", "owner": "Operations Manager", "timeline": "7 days"}]
            },
            "manager_view": {
                "dmaic": {"define": "Analysis incomplete.", "measure": "N/A", "analyze": "N/A", "improve": "N/A", "control": "N/A"},
                "recommendations": [],
                "kpi_tracking": []
            },
            "engineer_view": {
                "data_references": [], "models": [], "root_cause_analysis": [],
                "failure_modes": [], "assumptions": []
            },
            "boardroom_mode": {
                "executive_summary": "Analysis requires review.",
                "slides": {"summary": [], "decisions": [], "risks": [], "actions": [], "kpi_impact": []}
            }
        }
