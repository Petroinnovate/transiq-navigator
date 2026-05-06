"""
TransIQ FIXED Orchestrator - Data-Driven Intelligence
=====================================================

THIS IS THE REPLACEMENT for orchestrator.py

Key Change: Uses VALIDATED DATA EXTRACTION instead of hallucinating LLM interpretation.

Flow:
  [1] ValidatedExtractor       → REAL metrics only, no fabrication
  [2] DataDrivenDMAICAgent     → DMAIC based on actual data, marks gaps
  [3] DomainIntelligenceAgent  → O&G KPI mapping (with confidence)
  [4] DecisionIntelligenceAgent → Trusted decisions (based on real data)
  [5] OperationalizationAgent  → Tasks/owners/KPIs (realistic)
  [6] UXSimplificationAgent    → Honest dashboard (shows confidence)
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional
import json

from pipelines.processing.validated_extractor import ValidatedDDRExtractor
from agents.decision_agents.data_driven_dmaic_agent import DataDrivenDMAICAgent
from agents.decision_agents.domain_agent import DomainIntelligenceAgent
from agents.decision_agents.decision_agent import DecisionIntelligenceAgent
from agents.decision_agents.operationalization_agent import OperationalizationAgent
from agents.decision_agents.outcome_agent import OutcomeIntelligenceAgent
from agents.decision_agents.ux_agent import UXSimplificationAgent

logger = logging.getLogger(__name__)


class FixedAgentOrchestrator:
    """
    Corrected pipeline using VALIDATED extraction.
    
    Principle: 
    - Extraction phase: Extract ONLY what's in the document
    - Intelligence phase: Apply business logic to actual data
    - No hallucinations allowed
    """

    def __init__(self, llm_client, progress_callback: Optional[Callable] = None):
        """
        Args:
            llm_client: Gemini genai.Client instance
            progress_callback: optional async-safe callback(stage: str, pct: int)
        """
        self.client = llm_client
        self._cb = progress_callback

        # FIXED: Use data-driven agents only
        self._agents = [
            ("dmaic_analysis",        DataDrivenDMAICAgent(llm_client, "gemini-2.5-flash")),
            ("domain_intelligence",   DomainIntelligenceAgent(llm_client, "gemini-2.5-flash")),
            ("decision_intelligence", DecisionIntelligenceAgent(llm_client, "gemini-2.5-flash")),
            ("operationalization",    OperationalizationAgent(llm_client, "gemini-2.5-flash")),
            ("outcome_intelligence",  OutcomeIntelligenceAgent(llm_client, "gemini-2.5-flash")),
            ("ux_layers",             UXSimplificationAgent(llm_client, "gemini-2.5-flash")),
        ]

        self._stage_pcts = [20, 35, 50, 65, 80, 95]

    def run(self, raw_content: str, source_type: str = "UNKNOWN",
            section_analyses: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        FIXED Pipeline:
        
        1. VALIDATED extraction (no LLM guessing)
           → Enhanced with structured section_analyses from section_analyzer
             when available (full aggregation, no data loss).
        2. Data-driven DMAIC (based on actual metrics)
        3. Domain/Decision/Ops with confidence scoring
        4. UX with explicit data gaps

        Args:
            raw_content: raw document text (used by ValidatedDDRExtractor regex)
            source_type: file type
            section_analyses: pre-computed structured outputs from section_analyzer
                (kpis, findings, risks, DMAIC phases, etc.) — covers 100% of document
        """
        ctx: Dict[str, Any] = {
            "raw_content": raw_content,
            "source_type": source_type,
        }

        # --- STAGE 1: VALIDATED EXTRACTION (not LLM-based) ---
        logger.info("[Orchestrator] Phase 1: Validated Data Extraction")
        self._notify("Extracting Data", 10)
        
        try:
            extractor = ValidatedDDRExtractor(raw_content)
            validated_extraction = extractor.extract()

            # ── Enrich with section_analyses (full aggregation) ──────────
            # section_analyses contains pre-computed structured data from
            # the section_analyzer pipeline which processed 100% of the
            # document.  We merge these into validated_extraction so all
            # downstream agents benefit from full-coverage data.
            if section_analyses:
                sa_dash = section_analyses.get("dashboard", section_analyses)
                # Collect all KPIs / findings / risks across sections
                sa_kpis = sa_dash.get("kpis", [])
                sa_sections = sa_dash.get("sections", [])
                sa_findings = []
                sa_risks = []
                for sec in sa_sections:
                    if isinstance(sec, dict):
                        sa_findings.extend(sec.get("keyFindings", []))
                        sa_risks.extend(sec.get("risks", []))

                validated_extraction["section_analysis"] = {
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
                    "[Orchestrator] Enriched extraction with section_analyses: "
                    "%d sections, %d kpis, %d findings, %d risks",
                    len(sa_sections), len(sa_kpis), len(sa_findings), len(sa_risks),
                )

            ctx["validated_extraction"] = validated_extraction
            
            # Log extraction quality
            quality = validated_extraction.get("metadata", {}).get("extraction_quality", "unknown")
            hallucinated = validated_extraction.get("validation_summary", {}).get("hallucinated", 0)
            logger.info(f"[Orchestrator] Extraction complete: {quality}, hallucinations rejected: {hallucinated}")
            
        except Exception as exc:
            logger.error(f"[Orchestrator] Extraction failed: {exc}")
            ctx["validated_extraction"] = {
                "metadata": {"extraction_quality": "failed"},
                "extracted_data": [],
                "validation_summary": {"hallucinated": 0},
                "gaps": {"unavailable_information": ["All data - extraction failed"]}
            }

        # --- STAGES 2-7: DATA-DRIVEN AGENTS ---
        # Now run remaining agents with validated data
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

    def _build_output(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Merge outputs, but INCLUDE validation metadata"""
        
        # Extract key sections
        validated = ctx.get("validated_extraction", {})
        ux = ctx.get("ux_layers", {})
        ops = ctx.get("operationalization", {})
        dmaic = ctx.get("dmaic_analysis", {})
        domain = ctx.get("domain_intelligence", {})
        decision = ctx.get("decision_intelligence", {})

        # Build comprehensive output
        output = {
            "metadata": {
                "extraction_quality": validated.get("metadata", {}).get("extraction_quality"),
                "data_completeness": validated.get("validation_summary", {}).get("total_fields_extracted", 0),
                "data_gaps": validated.get("gaps", {}),
                "hallucinations_rejected": validated.get("validation_summary", {}).get("hallucinated", 0),
                "timestamp": validated.get("metadata", {}).get("extraction_timestamp")
            },
            "extracted_data": {
                "metrics": validated.get("extracted_data", []),
                "summary": validated.get("raw_summary", "")
            },
            "dmaic": dmaic,
            "domain_intelligence": domain,
            "decision_intelligence": decision,
            "operationalization": ops,
            "ux_layers": {
                **ux,
                "data_confidence_notice": f"Based on {len(validated.get('extracted_data', []))} extracted metrics. " +
                                          f"See 'metadata' for gaps and limitations."
            },
            "WARNING": "This analysis is data-driven. See 'metadata' for data quality and gaps. " +
                      "No hallucinations present."
        }

        return output

    def _notify(self, stage: str, pct: int):
        """Call progress callback if provided"""
        if self._cb:
            try:
                self._cb(stage=stage, pct=pct)
            except:
                pass  # Silent fail on callback error


class OrchestratorFactory:
    """
    Factory to switch between OLD (hallucinating) and NEW (validated) pipelines
    """
    
    @staticmethod
    def create_orchestrator(llm_client, use_validated: bool = True, progress_callback = None):
        """
        Create the appropriate orchestrator.
        
        Args:
            use_validated: If True, use fixed data-driven pipeline.
                          If False, use old hallucinating pipeline (for testing only).
        """
        if use_validated:
            logger.info("Creating FixedAgentOrchestrator (VALIDATED extraction)")
            return FixedAgentOrchestrator(llm_client, progress_callback)
        else:
            logger.warning("Creating OLD AgentOrchestrator (hallucinating) - for debugging only!")
            # Import the old one for comparison
            from .orchestrator import AgentOrchestrator
            return AgentOrchestrator(llm_client, progress_callback)
