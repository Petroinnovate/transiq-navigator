"""
Data-Driven DMAIC Agent

Replaces the old DMAICAgent which generated DMAIC from any data.

NEW approach:
1. Takes ONLY validated extracted data
2. Explicitly marks what data IS available vs gaps
3. Only generates DMAIC for metrics we ACTUALLY have
4. Refuses to hallucinate root causes or statistics
5. Returns honest analysis: "Incomplete data prevents full DMAIC"
"""

import json
from typing import Any, Dict, List
from .base_agent import BaseAgent


class DataDrivenDMAICAgent(BaseAgent):
    """
    Six Sigma DMAIC based on ACTUAL data, not hallucinations.
    
    Principle: Better to admit incomplete data than fabricate insights.
    """
    
    @property
    def name(self) -> str:
        return "DataDrivenDMAICAgent"

    def build_prompt(self, ctx: Dict[str, Any]) -> str:
        """
        NEW approach: Use validated extraction data explicitly
        """
        
        validated_data = ctx.get("validated_extraction", {})
        extracted_metrics = validated_data.get("extracted_data", [])
        data_gaps = validated_data.get("gaps", {})
        validation_summary = validated_data.get("validation_summary", {})
        
        # Build metric summary
        metrics_summary = "\\n".join([
            f"- {m.get('name')}: {m.get('value')} {m.get('unit', '')} " +
            f"(confidence: {m.get('confidence', 0):.0%}, source: {m.get('source', 'unknown')})"
            for m in extracted_metrics
        ])
        
        gaps_summary = "\\n".join(data_gaps.get("unavailable_information", []))
        
        return f"""
You are a Six Sigma DMAIC analyst for industrial operations.

IMPORTANT INSTRUCTION:
======================
You are analyzing a report with PARTIALLY available data.
Generate DMAIC ONLY based on what is actually documented.
DO NOT INVENT metrics, statistics, or root causes.
CLEARLY MARK what cannot be analyzed due to missing data.

VALIDATED DATA AVAILABLE:
{metrics_summary}

DATA GAPS (NOT IN DOCUMENT):
{gaps_summary}

QUALITY METRICS:
- High confidence extractions: {validation_summary.get("high_confidence", 0)}
- Medium confidence: {validation_summary.get("medium_confidence", 0)}
- Hallucinated (rejected): {validation_summary.get("hallucinated", 0)}

YOUR TASK:
Generate a PARTIAL DMAIC that:
1. Define: Problem statement based on what we KNOW
2. Measure: Only use metrics we actually have
3. Analyze: Correlations only where we have data
4. Improve: Recommendations only for documented issues
5. Control: Based on available metrics

Return ONLY this JSON (no hallucinations):
{{
  "methodology": "DMAIC (Partial - data limited)",
  "data_completeness": 0.0-1.0,
  "data_quality_score": {validation_summary.get("high_confidence", 0)} / {validation_summary.get("total_fields_extracted", 1)},
  "analysis_validity": "Partially Valid|Valid|Limited|Incomplete",
  "dmaic": {{
    "define": {{
      "problem_statement": "string — based ONLY on extracted data",
      "data_limitations": ["string — what we DON'T know"],
      "ctqs": ["string — Critical to Quality parameters we can measure"]
    }},
    "measure": {{
      "available_metrics": [
        {{"metric": "string", "value": 0, "unit": "string", "confidence": 0.0}}
      ],
      "unavailable_metrics": {json.dumps(data_gaps.get("unavailable_information", []))},
      "data_confidence": {validation_summary.get("high_confidence", 0) / max(1, validation_summary.get("total_fields_extracted", 1)):.2f}
    }},
    "analyze": {{
      "root_causes": [
        {{"cause": "string", "evidence": "string", "confidence": 0.0, "note": "Only if documented in report"}}
      ],
      "note": "Root cause analysis limited by available data"
    }},
    "improve": {{
      "recommended_actions": [
        {{"action": "string", "based_on": "metric name", "evidence": "string"}}
      ],
      "note": "Recommendations limited to documented issues"
    }},
    "control": {{
      "control_plan": ["string — for metrics we CAN measure"],
      "monitoring_kpis": ["string — from extracted metrics"]
    }}
  }},
  "key_limitations": [
    "Production volumes not documented - cannot analyze efficiency",
    "Total workforce size not documented - cannot analyze staffing",
    "Safety incidents not documented - cannot analyze HSE trends",
    "Historical data not available - cannot perform trend analysis"
  ],
  "data_quality_note": "This analysis is PARTIAL due to limited source data. Full DMAIC requires complete operational metrics."
}}
"""

    def _fallback(self):
        """Fallback when data is too incomplete"""
        return {
            "methodology": "DMAIC (Analysis Not Possible)",
            "data_completeness": 0.1,
            "analysis_validity": "Incomplete",
            "dmaic": {
                "define": {
                    "problem_statement": "Insufficient data for analysis",
                    "data_limitations": ["Document does not contain adequate operational metrics"],
                    "ctqs": []
                },
                "measure": {
                    "available_metrics": [],
                    "unavailable_metrics": ["All major operational metrics"],
                    "data_confidence": 0.0
                },
                "analyze": {
                    "root_causes": [],
                    "note": "Cannot perform analysis with insufficient data"
                },
                "improve": {
                    "recommended_actions": [
                        {
                            "action": "Provide additional operational data",
                            "based_on": "current document is incomplete",
                            "evidence": "Missing: production metrics, personnel counts, historical trends"
                        }
                    ]
                },
                "control": {
                    "control_plan": [],
                    "monitoring_kpis": []
                }
            },
            "key_limitations": [
                "Source document lacks operational metrics required for DMAIC analysis",
                "Cannot generate reliable intelligence from incomplete data",
                "Recommend uploading comprehensive operational reports"
            ],
            "data_quality_note": "NO DMAIC generated. Data quality insufficient."
        }
