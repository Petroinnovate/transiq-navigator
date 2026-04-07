"""
Agent 7 — Outcome Intelligence Agent
======================================
Transforms decisions + action plans → measurable outcome-driven structures.

The Closed-Loop Accountability Layer:
  Decision → Expected KPI → Financial Impact → Tracking → Benchmark → Actual vs Expected

This agent answers ALL 5 executive questions:
  1. Can we trust this?   → Outcome Confidence Score
  2. How do we execute?   → Action-to-KPI linkage
  3. What happens after?  → Tracking Framework + Actual vs Expected
  4. How vs peers?        → Benchmark Impact
  5. Cost of doing nothing? → Cost of Inaction (mandatory, quantified)
"""
import json
from typing import Any, Dict
from agents.base_agent import BaseAgent


class OutcomeIntelligenceAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "OutcomeIntelligenceAgent"

    def _system_instruction(self) -> str:
        return (
            "You are TransIQ's Outcome Intelligence Agent — the closed-loop accountability layer "
            "of an Industrial Decision OS. You do NOT generate recommendations. "
            "You map DECISIONS → ACTIONS → OUTCOMES → FINANCIAL IMPACT. "
            "FIVE MANDATORY LAWS:\n"
            "LAW 1 — KPI LINKAGE: Every decision must name a specific measurable KPI "
            "with current value, target value, unit, and timeline. "
            "NEVER write 'improve efficiency' — ALWAYS 'Reduce downtime from 12% → 9% in 60 days'.\n"
            "LAW 2 — FINANCIAL QUANTIFICATION: Every KPI must translate to $ revenue gain, "
            "cost saving, or loss avoidance. Include a confidence level (High/Medium/Low).\n"
            "LAW 3 — OUTCOME TRACKING: Define WHO tracks it (role), HOW OFTEN (frequency), "
            "and from WHAT system (SCADA/ERP/Manual).\n"
            "LAW 4 — COST OF INACTION: State the specific financial or operational consequence "
            "if this decision is NOT acted upon. Quantify in $ or operational KPI terms.\n"
            "LAW 5 — BENCHMARK POSITION: Show where the asset sits vs industry P50/P75 "
            "and what achieving the target means in percentile terms.\n"
            "Respond ONLY in valid JSON."
        )

    def build_prompt(self, ctx: Dict[str, Any]) -> str:
        decisions = ctx.get("decision_intelligence", {}).get("top_decisions", [])
        action_plan = ctx.get("operationalization", {}).get("action_plan", [])
        kpi_dashboard = ctx.get("operationalization", {}).get("kpi_dashboard", [])
        benchmarking = ctx.get("domain_intelligence", {}).get("benchmarking", {})
        dmaic_sigma = ctx.get("dmaic_analysis", {}).get("sigma_level", "")
        data_quality = ctx.get("data_interpretation", {}).get("data_quality_score", 0.5)

        return f"""
You are the Outcome Intelligence Agent for TransIQ.
Transform the decisions and action plan below into a CLOSED-LOOP outcome-driven structure.

TOP DECISIONS (from Decision Intelligence Agent):
{json.dumps(decisions, indent=2)[:4000]}

ACTION PLAN (from Operationalization Agent):
{json.dumps(action_plan, indent=2)[:3000]}

KPI DASHBOARD:
{json.dumps(kpi_dashboard, indent=2)[:2000]}

BENCHMARKING DATA:
{json.dumps(benchmarking, indent=2)[:1500]}

SIGMA LEVEL: {dmaic_sigma}
DATA QUALITY SCORE: {data_quality} (0–1 scale)

For each top decision, generate a full outcome-driven entry.
Return ONLY this JSON (no markdown, no preamble):
{{
  "outcome_decisions": [
    {{
      "decision": "string — imperative verb, specific and quantified, max 14 words",
      "expected_outcome": {{
        "kpi": "string — exact KPI name (e.g. Equipment Downtime %, OEE, MTBF hours)",
        "current": "string — current measured value + unit (e.g. 12%)",
        "target": "string — target value + unit (e.g. 9%)",
        "timeline": "string — specific timeframe (e.g. 60 days, by Q2 2026)"
      }},
      "business_impact": {{
        "type": "revenue_gain|cost_saving|loss_avoidance",
        "value": "string — $ amount or % with context (e.g. $1.4M annual cost saving)",
        "confidence": "High|Medium|Low"
      }},
      "actions": [
        {{
          "task": "string — imperative verb, specific action (what + where)",
          "owner": "string — role-based (e.g. Maintenance Lead)",
          "kpi_link": "string — specific KPI this action moves",
          "deadline": "string — time-bound (e.g. 30 days)"
        }}
      ],
      "tracking_framework": {{
        "metrics": ["string — KPI name to monitor"],
        "data_source": ["string — SCADA|ERP|Manual|DCS"],
        "frequency": "Daily|Weekly|Monthly",
        "owner": "string — responsible role"
      }},
      "cost_of_inaction": "string — specific quantified consequence if nothing is done (e.g. Continued $120K/month losses; risk of unplanned shutdown within 90 days)",
      "actual_vs_expected": {{
        "expected": "string — quantified target statement",
        "actual": "Pending",
        "variance": "TBD"
      }},
      "outcome_confidence_score": {{
        "score": 0,
        "explanation": "string — cite data quality ({data_quality:.0%}), execution feasibility, and historical O&G success rates for this type of action"
      }},
      "benchmark_impact": {{
        "current_position": "string — e.g. P35 (Below industry median)",
        "target_position": "string — e.g. P72 (Top Quartile entry)",
        "improvement": "string — what achieving target means in plain language"
      }}
    }}
  ],
  "portfolio_summary": {{
    "total_value_at_stake": "string — aggregate $ across all decisions",
    "decisions_count": 0,
    "highest_confidence_decision": "string — title of highest-scored decision",
    "fastest_win": "string — title of decision with shortest timeline to value"
  }}
}}
"""

    def _fallback(self) -> Dict[str, Any]:
        return {
            "outcome_decisions": [],
            "portfolio_summary": {
                "total_value_at_stake": "N/A",
                "decisions_count": 0,
                "highest_confidence_decision": "",
                "fastest_win": "",
            },
        }
