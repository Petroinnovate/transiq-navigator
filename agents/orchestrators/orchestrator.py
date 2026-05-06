"""
TransIQ Master Orchestrator
============================
Coordinates 6 specialized agents in sequence, passing each output as
context to the next. Produces the full structured Decision Intelligence output.

Flow:
  [1] DataInterpreterAgent     → cleaned metrics, data quality
  [2] DMAICAgent               → Six Sigma analysis, root causes
  [3] DomainIntelligenceAgent  → O&G KPI mapping, failure modes
  [4] DecisionIntelligenceAgent → trusted decisions, DCI scoring
  [5] OperationalizationAgent  → tasks, owners, KPIs, 90-day roadmap
  [6] UXSimplificationAgent    → CEO / Manager / Engineer / Boardroom layers
"""
from __future__ import annotations
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from agents.decision_agents.data_interpreter import DataInterpreterAgent
from agents.decision_agents.dmaic_agent import DMAICAgent
from agents.decision_agents.domain_agent import DomainIntelligenceAgent
from agents.decision_agents.decision_agent import DecisionIntelligenceAgent
from agents.decision_agents.operationalization_agent import OperationalizationAgent
from agents.decision_agents.outcome_agent import OutcomeIntelligenceAgent
from agents.decision_agents.ux_agent import UXSimplificationAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Run all 6 agents sequentially, accumulating context.
    Each agent receives the full ctx dict — agents pick what they need.
    """

    def __init__(self, llm_client, progress_callback: Optional[Callable] = None):
        """
        Args:
            llm_client: Gemini genai.Client instance
            progress_callback: optional async-safe callback(stage: str, pct: int)
        """
        self.client = llm_client
        self._cb = progress_callback

        # Agent registry — ordered execution pipeline
        self._agents = [
            ("data_interpretation",   DataInterpreterAgent(llm_client, "gemini-2.5-flash")),
            ("dmaic_analysis",        DMAICAgent(llm_client, "gemini-2.5-flash")),
            ("domain_intelligence",   DomainIntelligenceAgent(llm_client, "gemini-2.5-flash")),
            ("decision_intelligence", DecisionIntelligenceAgent(llm_client, "gemini-2.5-flash")),
            ("operationalization",    OperationalizationAgent(llm_client, "gemini-2.5-flash")),
            ("outcome_intelligence",  OutcomeIntelligenceAgent(llm_client, "gemini-2.5-flash")),
            ("ux_layers",             UXSimplificationAgent(llm_client, "gemini-2.5-flash")),
        ]

        # Progress percentages for each stage
        self._stage_pcts = [10, 25, 40, 55, 70, 83, 95]

    # ── Public entry point ─────────────────────────────────────────────
    def run(self, raw_content: str, source_type: str = "UNKNOWN",
            section_analyses: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute all agents and return the merged output context.

        Args:
            raw_content: raw document text
            source_type: file type
            section_analyses: pre-computed structured outputs from section_analyzer
                (kpis, findings, risks, DMAIC phases, etc.) — covers 100% of document.
                When provided, injected into ctx so agents have full-coverage data.

        Keys returned:
          data_interpretation, dmaic_analysis, domain_intelligence,
          decision_intelligence, operationalization, ux_layers
        """
        ctx: Dict[str, Any] = {
            "raw_content": raw_content,
            "source_type": source_type,
        }

        # ── Inject structured section data if available ──────────────────
        if section_analyses:
            sa_dash = section_analyses.get("dashboard", section_analyses)
            sa_sections = sa_dash.get("sections", [])
            sa_kpis = sa_dash.get("kpis", [])
            sa_findings = []
            sa_risks = []
            for sec in sa_sections:
                if isinstance(sec, dict):
                    sa_findings.extend(sec.get("keyFindings", []))
                    sa_risks.extend(sec.get("risks", []))

            ctx["section_analysis"] = {
                "kpis": sa_kpis,
                "sections": sa_sections,
                "all_findings": sa_findings[:100],
                "all_risks": sa_risks[:50],
                "six_sigma": sa_dash.get("sixSigma", {}),
                "insights": sa_dash.get("insights", {}),
                "optimization_suggestions": sa_dash.get("optimizationSuggestions", []),
                "quality_score": sa_dash.get("qualityScore", {}),
                "sections_analyzed": len(sa_sections),
                "source": "section_analyzer_full_coverage",
            }
            logger.info(
                "[Orchestrator] Injected section_analyses: %d sections, %d kpis, %d findings",
                len(sa_sections), len(sa_kpis), len(sa_findings),
            )

        t0 = time.time()
        for idx, (key, agent) in enumerate(self._agents):
            stage_label = agent.name
            pct = self._stage_pcts[idx]
            self._notify(stage_label, pct)

            t_agent = time.time()
            try:
                result = agent.run(ctx)
                ctx[key] = result
                elapsed = round(time.time() - t_agent, 2)
                logger.info(f"[Orchestrator] {stage_label} done in {elapsed}s")
            except Exception as exc:
                logger.error(f"[Orchestrator] {stage_label} failed: {exc}")
                ctx[key] = agent._fallback()

        self._notify("Complete", 100)
        total = round(time.time() - t0, 2)
        logger.info(f"[Orchestrator] All agents completed in {total}s")

        return self._build_output(ctx)

    # ── Merge all agent outputs into final structured response ─────────
    def _build_output(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        ux = ctx.get("ux_layers", {})
        ops = ctx.get("operationalization", {})
        dmaic = ctx.get("dmaic_analysis", {})
        domain = ctx.get("domain_intelligence", {})
        decisions = ctx.get("decision_intelligence", {})
        interp = ctx.get("data_interpretation", {})
        outcome = ctx.get("outcome_intelligence", {})

        # Derive audit_trail from decision traceability for ExplainabilityAuditTrail component
        audit_entries = [
            {
                "decision_title": d.get("title", ""),
                "why": d.get("rationale", ""),
                "data_sources": d.get("traceability", {}).get("data_sources", []),
                "method": " | ".join(d.get("traceability", {}).get("analytical_methods", [])),
                "assumptions": d.get("traceability", {}).get("supporting_evidence", []),
                "limitations": [d.get("risk_if_ignored", "")] if d.get("risk_if_ignored") else [],
                "confidence": str(d.get("confidence_score", "")),
            }
            for d in decisions.get("top_decisions", [])
        ]

        return {
            # ── Outcome Intelligence Layer ──────────────────────────────
            "outcome_driven_decisions": outcome.get("outcome_decisions", []),
            "portfolio_summary": outcome.get("portfolio_summary", {}),

            # ── Explainability / Audit Trail (derived from decision traceability) ──
            "audit_trail": {"audit_trail": audit_entries},

            # ── Progressive Disclosure Layers ──────────────────────────
            "ceo_view": ux.get("ceo_view", {}),
            "manager_view": ux.get("manager_view", {}),
            "engineer_view": ux.get("engineer_view", {}),
            "boardroom_mode": ux.get("boardroom_mode", {}),

            # ── Operational Layer ──────────────────────────────────────
            "action_plan": ops.get("action_plan", []),
            "kpi_dashboard": ops.get("kpi_dashboard", []),
            "quick_wins": ops.get("quick_wins", []),
            "roadmap_90_day": ops.get("90_day_roadmap", []),

            # ── Decision Layer ─────────────────────────────────────────
            "top_decisions": decisions.get("top_decisions", []),
            "top_risks": decisions.get("top_risks", []),

            # ── DMAIC Layer ────────────────────────────────────────────
            "dmaic": dmaic.get("dmaic", {}),
            "sigma_level": dmaic.get("sigma_level", ""),
            "key_findings": dmaic.get("key_findings", []),

            # ── Domain Layer ───────────────────────────────────────────
            "industry_kpis": domain.get("industry_kpis", []),
            "failure_modes": domain.get("failure_mode_library", []),
            "use_case": domain.get("use_case_classification", ""),
            "benchmarking": domain.get("benchmarking", {}),

            # ── Data Quality ───────────────────────────────────────────
            "data_quality_score": interp.get("data_quality_score", 0.5),
            "document_type": interp.get("document_type", ""),
            "raw_summary": interp.get("raw_summary", ""),

            # ── Agent metadata ─────────────────────────────────────────
            "_agent_pipeline": [k for k, _ in self._agents],
            "_orchestrated": True,
        }

    def _notify(self, stage: str, pct: int) -> None:
        if self._cb:
            try:
                self._cb(stage, pct)
            except Exception:
                pass
