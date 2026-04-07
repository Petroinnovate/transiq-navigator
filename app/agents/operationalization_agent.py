"""
Agent 5 — Operationalization Agent
Converts decisions → execution: tasks, owners, KPIs, deadlines, integration hooks.
"""
import json
from typing import Any, Dict
from .base_agent import BaseAgent


class OperationalizationAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "OperationalizationAgent"

    def build_prompt(self, ctx: Dict[str, Any]) -> str:
        decisions = ctx.get("decision_intelligence", {})
        dmaic = ctx.get("dmaic_analysis", {})
        domain = ctx.get("domain_intelligence", {})
        return f"""
You are the Operationalization Agent for TransIQ — you convert boardroom decisions into executable field actions.

DECISIONS:
{json.dumps(decisions.get("top_decisions", []), indent=2)[:4000]}

DMAIC IMPROVE PHASE:
{json.dumps(dmaic.get("dmaic", {}).get("improve", {}), indent=2)[:2000]}

DOMAIN KPIs:
{json.dumps(domain.get("industry_kpis", []), indent=2)[:2000]}

Convert every decision into actionable tasks. Return ONLY this JSON:
{{
  "action_plan": [
    {{
      "id": "A1",
      "task_title": "string — imperative verb, specific (e.g. Replace pump seals on Train-B)",
      "linked_decision": "D1",
      "description": "string — what to do and why",
      "owner": "string — role-based (e.g. Maintenance Lead, Production Manager)",
      "kpi_impacted": "string — specific KPI (e.g. Downtime %, OEE, MTBF)",
      "target_value": "string — quantified (e.g. Reduce downtime from 8% to 4%)",
      "deadline": "string — time-bound (e.g. 30 days, Q2 2026)",
      "priority": "high|medium|low",
      "status": "Open",
      "execution_steps": [
        "string — Step N: specific action with tools/systems mentioned"
      ],
      "integration": {{
        "erp": "string — SAP/Oracle action or N/A",
        "scada": "string — real-time trigger or N/A",
        "production_db": "string — KPI query or N/A"
      }},
      "closed_loop": {{
        "predicted_impact": "string — quantified benefit",
        "measurement_plan": "string — data source + frequency",
        "feedback_trigger": "string — what metric confirms success"
      }}
    }}
  ],
  "kpi_dashboard": [
    {{
      "name": "string",
      "current": "string",
      "target": "string",
      "status": "on-track|at-risk|off-track",
      "owner": "string",
      "review_frequency": "Daily|Weekly|Monthly"
    }}
  ],
  "quick_wins": [
    "string — [owner] → [action] → [impact] → within 30 days"
  ],
  "90_day_roadmap": [
    {{"week": "1-2|3-4|5-8|9-12", "milestone": "string", "owner": "string"}}
  ]
}}
"""

    def _fallback(self):
        return {
            "action_plan": [],
            "kpi_dashboard": [],
            "quick_wins": [],
            "90_day_roadmap": []
        }
