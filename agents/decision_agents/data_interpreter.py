"""
Agent 1 — Data Interpreter Agent
Cleans raw document chunks → structured metrics, trends, data quality score.
"""
import json
from typing import Any, Dict
from agents.base_agent import BaseAgent


class DataInterpreterAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "DataInterpreterAgent"

    def build_prompt(self, ctx: Dict[str, Any]) -> str:
        content = ctx.get("raw_content", "")[:120_000]  # cap at 120K chars
        source_type = ctx.get("source_type", "UNKNOWN")

        # ── Use full-coverage section analysis when available ────────
        sa = ctx.get("section_analysis")
        sa_block = ""
        if sa and sa.get("sections"):
            sa_block = f"""

PRE-ANALYZED STRUCTURED DATA (covers 100% of document — {sa.get('sections_analyzed', '?')} sections):
KPIs FOUND: {json.dumps(sa.get('kpis', [])[:60], default=str)[:12000]}
KEY FINDINGS: {json.dumps(sa.get('all_findings', [])[:40], default=str)[:8000]}
RISKS: {json.dumps(sa.get('all_risks', [])[:20], default=str)[:4000]}
QUALITY SCORE: {json.dumps(sa.get('quality_score', {}), default=str)[:2000]}

IMPORTANT: The structured data above covers the ENTIRE document.
Use it as the primary source of metrics and findings.
The raw content below is truncated and may miss data.
"""

        return f"""
You are the Data Interpreter Agent for TransIQ — an industrial AI platform.

SOURCE TYPE: {source_type}
{sa_block}
DOCUMENT CONTENT (may be truncated):
{content}

Your job: extract and structure the raw data into a clean analytical foundation.

Return ONLY this JSON (no markdown, no text outside JSON):
{{
  "document_type": "operations|hse|finance|audit|strategy|engineering",
  "asset_scope": "well|field|plant|pipeline|enterprise",
  "time_horizon": "operational|tactical|strategic",
  "data_quality_score": 0.0,
  "completeness": 0.0,
  "key_metrics": [
    {{"name": "string", "value": "string", "unit": "string", "period": "string", "source_ref": "string"}}
  ],
  "time_series": [
    {{"metric": "string", "trend": "increasing|decreasing|stable|volatile", "data_points": 0}}
  ],
  "identified_gaps": ["string"],
  "raw_summary": "string — 3-4 sentences summarizing what the document is about"
}}
"""

    def _fallback(self):
        return {
            "document_type": "operations",
            "asset_scope": "enterprise",
            "data_quality_score": 0.5,
            "completeness": 0.5,
            "key_metrics": [],
            "time_series": [],
            "identified_gaps": ["Unable to interpret data"],
            "raw_summary": "Data interpretation failed — proceeding with available content.",
        }
