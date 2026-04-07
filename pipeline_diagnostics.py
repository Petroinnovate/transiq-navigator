"""
Pipeline Diagnostics — Surgical Debugging for the Analysis Pipeline
====================================================================
Collects metrics at EVERY stage of the pipeline so that a single run
can reveal exactly where data is lost, truncated, or hallucinated.

Usage:
    Set PIPELINE_DIAGNOSTICS=1 in your environment to enable.
    The diagnostic report is attached to the dashboard response under
    the key "_diagnostics" when enabled.

    PIPELINE_DIAGNOSTICS=1 uvicorn main:app --reload
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DIAGNOSTICS_ENABLED = os.getenv("PIPELINE_DIAGNOSTICS", "0") == "1"


@dataclass
class SectionDiag:
    """Per-section diagnostic snapshot."""
    id: str = ""
    title: str = ""
    pages: str = ""                 # "5-12"
    text_chars: int = 0
    text_tokens_est: int = 0
    score: float = 0.0
    tier: int = 3
    skipped: bool = False
    model_tier: str = ""
    model_name: str = ""
    text_cap: int = 0
    text_after_cap: int = 0         # chars actually sent to LLM
    truncated_chars: int = 0        # chars lost to text_cap
    truncation_pct: float = 0.0     # % of text lost
    llm_latency_ms: int = 0
    llm_output_tokens_est: int = 0
    confidence: float = 0.0
    kpi_count: int = 0
    finding_count: int = 0
    risk_count: int = 0
    dmaic_phase: str = ""
    # Signal breakdown
    signal_kpi: float = 0.0
    signal_financial: float = 0.0
    signal_dmaic: float = 0.0
    signal_data: float = 0.0
    signal_risk: float = 0.0
    signal_boilerplate: float = 0.0
    signal_pageindex: float = 0.0


class PipelineDiagnostics:
    """Collects diagnostic data at every pipeline stage. Thread-safe for a single run."""

    def __init__(self):
        self.enabled = DIAGNOSTICS_ENABLED
        self._start_time = time.time()
        self._stage_times: Dict[str, float] = {}
        self._stage_starts: Dict[str, float] = {}

        # Stage 0: Ingestion
        self.ingestion = {
            "total_files": 0,
            "file_names": [],
            "file_sizes_bytes": [],
            "raw_page_count": 0,
            "pages_with_text": 0,
            "pages_empty": 0,
            "merged_chunk_count": 0,
            "total_chars_raw": 0,
            "total_chars_after_merge": 0,
            "chars_per_page": [],         # list of int
            "min_page_chars": 0,
            "max_page_chars": 0,
            "avg_page_chars": 0,
        }

        # Stage 1: Structure
        self.structure = {
            "pageindex_success": False,
            "pageindex_error": "",
            "section_count": 0,
            "fallback_used": False,
            "fallback_section_size": 0,
            "sections_before_merge": 0,
            "sections_after_merge": 0,
            "page_coverage": 0.0,         # % of pages covered by sections
            "pages_covered": 0,
            "pages_total": 0,
            "largest_section_pages": 0,
            "smallest_section_pages": 0,
            "avg_section_pages": 0.0,
        }

        # Stage 2-3: Scoring & Classification
        self.scoring = {
            "total_sections": 0,
            "tier1_count": 0,
            "tier2_count": 0,
            "tier3_count": 0,
            "skipped_count": 0,
            "skipped_section_ids": [],
            "skipped_chars_total": 0,     # total chars in skipped sections
            "skipped_pct_of_doc": 0.0,    # % of doc chars that are skipped
            "score_min": 0.0,
            "score_max": 0.0,
            "score_avg": 0.0,
            "score_distribution": {},     # histogram buckets
        }

        # Stage 7: LLM Execution
        self.execution = {
            "total_sections_executed": 0,
            "total_sections_skipped": 0,
            "total_llm_calls": 0,
            "total_llm_time_ms": 0,
            "total_chars_sent_to_llm": 0,
            "total_chars_truncated": 0,
            "truncation_pct_overall": 0.0,
            "total_kpis_extracted": 0,
            "total_findings_extracted": 0,
            "total_risks_extracted": 0,
            "empty_results_count": 0,
            "avg_confidence": 0.0,
            "low_confidence_count": 0,    # confidence < 0.4
            "model_usage": {"cheap": 0, "balanced": 0, "powerful": 0},
        }

        # Stage 8: Reprocessing
        self.reprocessing = {
            "candidates": 0,
            "reprocessed": 0,
            "improved": 0,
        }

        # Stage 9: DMAIC Mapping
        self.dmaic = {
            "define": 0,
            "measure": 0,
            "analyze": 0,
            "improve": 0,
            "control": 0,
            "unassigned": 0,
            "unassigned_pct": 0.0,
            "unassigned_section_ids": [],
        }

        # Stage 10: Phase Synthesis
        self.synthesis = {
            "phases_synthesized": [],
            "phase_input_counts": {},     # phase -> num sections fed in
            "phase_input_chars": {},      # phase -> total chars fed in
        }

        # Stage 12: Executive Synthesis
        self.executive = {
            "prompt_chars": 0,
            "prompt_tokens_est": 0,
            "section_analyses_chars": 0,
            "phase_syntheses_chars": 0,
            "success": False,
            "fallback_used": False,
        }

        # Final Output Validation
        self.output = {
            "total_kpis": 0,
            "kpis_with_source": 0,
            "kpis_with_zero_value": 0,
            "total_findings": 0,
            "total_risks": 0,
            "total_recommendations": 0,
            "total_charts": 0,
            "sections_in_output": 0,
            "dmaic_phases_populated": 0,
            "quality_score": 0.0,
            "quality_rating": "",
            "has_ceo_view": False,
            "has_manager_view": False,
            "has_engineer_view": False,
            "has_boardroom": False,
        }

        # Per-section detail
        self.section_details: List[Dict[str, Any]] = []

    # ── Stage timing helpers ─────────────────────────────────────────────

    def start_stage(self, name: str):
        if not self.enabled:
            return
        self._stage_starts[name] = time.time()

    def end_stage(self, name: str):
        if not self.enabled:
            return
        start = self._stage_starts.pop(name, None)
        if start:
            self._stage_times[name] = round((time.time() - start) * 1000)

    # ── Ingestion ────────────────────────────────────────────────────────

    def record_ingestion(self, file_names: List[str], file_sizes: List[int],
                         raw_pages: int, pages_with_text: int,
                         merged_chunks: int, chars_per_page: List[int]):
        if not self.enabled:
            return
        self.ingestion["total_files"] = len(file_names)
        self.ingestion["file_names"] = file_names
        self.ingestion["file_sizes_bytes"] = file_sizes
        self.ingestion["raw_page_count"] = raw_pages
        self.ingestion["pages_with_text"] = pages_with_text
        self.ingestion["pages_empty"] = raw_pages - pages_with_text
        self.ingestion["merged_chunk_count"] = merged_chunks
        self.ingestion["chars_per_page"] = chars_per_page
        total = sum(chars_per_page) if chars_per_page else 0
        self.ingestion["total_chars_raw"] = total
        self.ingestion["total_chars_after_merge"] = total  # updated later if needed
        if chars_per_page:
            self.ingestion["min_page_chars"] = min(chars_per_page)
            self.ingestion["max_page_chars"] = max(chars_per_page)
            self.ingestion["avg_page_chars"] = round(total / len(chars_per_page))

    # ── Structure ────────────────────────────────────────────────────────

    def record_structure(self, brain) -> None:
        if not self.enabled:
            return
        sections = list(brain.iter_sections())
        total_pages = brain.metadata["total_pages"]
        self.structure["section_count"] = len(sections)
        self.structure["pages_total"] = total_pages
        self.structure["pageindex_success"] = brain.metadata.get("_pageindex_success", False)
        self.structure["pageindex_error"] = brain.metadata.get("_pageindex_error", "")
        self.structure["fallback_used"] = brain.metadata.get("_fallback_used", False)
        self.structure["fallback_section_size"] = brain.metadata.get("_fallback_section_size", 0)
        self.structure["sections_before_merge"] = brain.metadata.get("_sections_before_merge", len(sections))
        self.structure["sections_after_merge"] = len(sections)

        if sections:
            page_spans = [n.end_index - n.start_index + 1 for n in sections]
            covered = sum(page_spans)
            self.structure["pages_covered"] = covered
            self.structure["page_coverage"] = round(covered / max(total_pages, 1) * 100, 1)
            self.structure["largest_section_pages"] = max(page_spans)
            self.structure["smallest_section_pages"] = min(page_spans)
            self.structure["avg_section_pages"] = round(sum(page_spans) / len(page_spans), 1)

    # ── Scoring ──────────────────────────────────────────────────────────

    def record_scoring(self, brain) -> None:
        if not self.enabled:
            return
        sections = list(brain.iter_sections())
        total_chars = brain.metadata["total_chars"]
        scores = [n.score for n in sections]

        self.scoring["total_sections"] = len(sections)
        t1 = len(brain.execution_plan.get("tier1", []))
        t2 = len(brain.execution_plan.get("tier2", []))
        t3 = len(brain.execution_plan.get("tier3", []))
        self.scoring["tier1_count"] = t1
        self.scoring["tier2_count"] = t2
        self.scoring["tier3_count"] = t3

        skipped = [n for n in sections if not n.execution.get("should_run", True)]
        self.scoring["skipped_count"] = len(skipped)
        self.scoring["skipped_section_ids"] = [n.id for n in skipped]
        skip_chars = sum(len(n.text) for n in skipped)
        self.scoring["skipped_chars_total"] = skip_chars
        self.scoring["skipped_pct_of_doc"] = round(skip_chars / max(total_chars, 1) * 100, 1)

        if scores:
            self.scoring["score_min"] = round(min(scores), 3)
            self.scoring["score_max"] = round(max(scores), 3)
            self.scoring["score_avg"] = round(sum(scores) / len(scores), 3)

            # Build histogram
            buckets = {"0.0-0.15": 0, "0.15-0.40": 0, "0.40-0.70": 0, "0.70-1.0": 0}
            for s in scores:
                if s < 0.15:
                    buckets["0.0-0.15"] += 1
                elif s < 0.40:
                    buckets["0.15-0.40"] += 1
                elif s < 0.70:
                    buckets["0.40-0.70"] += 1
                else:
                    buckets["0.70-1.0"] += 1
            self.scoring["score_distribution"] = buckets

    # ── Per-section LLM execution detail ─────────────────────────────────

    def record_section_execution(self, node, text_sent_len: int, latency_ms: int,
                                  result: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        text_total = len(node.text)
        truncated = max(0, text_total - text_sent_len)
        trunc_pct = round(truncated / max(text_total, 1) * 100, 1)

        kpi_count = len(result.get("kpis", []))
        finding_count = len(result.get("keyFindings", []))
        risk_count = len(result.get("risks", []))
        confidence = result.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)):
            confidence = 0.0

        diag = {
            "id": node.id,
            "title": node.title[:60],
            "pages": f"{node.start_index}-{node.end_index}",
            "text_chars": text_total,
            "text_tokens_est": text_total // 4,
            "score": round(node.score, 3),
            "tier": node.tier,
            "skipped": not node.execution.get("should_run", True),
            "model_tier": node.execution.get("model_tier", ""),
            "model_name": node.execution.get("model_name", ""),
            "text_cap": node.execution.get("text_cap", 0),
            "text_after_cap": text_sent_len,
            "truncated_chars": truncated,
            "truncation_pct": trunc_pct,
            "llm_latency_ms": latency_ms,
            "confidence": round(confidence, 3),
            "kpi_count": kpi_count,
            "finding_count": finding_count,
            "risk_count": risk_count,
            "dmaic_phase": node.dmaic_phase or "",
            "signal_kpi": round(node.signals.get("kpi_density", 0), 3),
            "signal_financial": round(node.signals.get("financial", 0), 3),
            "signal_dmaic": round(node.signals.get("dmaic", 0), 3),
            "signal_data": round(node.signals.get("data_density", 0), 3),
            "signal_risk": round(node.signals.get("risk", 0), 3),
            "signal_boilerplate": round(node.signals.get("boilerplate", 0), 3),
            "signal_pageindex": round(node.signals.get("pageindex_boost", 0), 3),
        }
        self.section_details.append(diag)

        # Accumulate execution totals
        self.execution["total_llm_calls"] += 1
        self.execution["total_llm_time_ms"] += latency_ms
        self.execution["total_chars_sent_to_llm"] += text_sent_len
        self.execution["total_chars_truncated"] += truncated
        self.execution["total_kpis_extracted"] += kpi_count
        self.execution["total_findings_extracted"] += finding_count
        self.execution["total_risks_extracted"] += risk_count
        if confidence < 0.4:
            self.execution["low_confidence_count"] += 1
        if kpi_count == 0 and finding_count == 0 and risk_count == 0:
            self.execution["empty_results_count"] += 1

        tier_key = node.execution.get("model_tier", "balanced")
        self.execution["model_usage"][tier_key] = self.execution["model_usage"].get(tier_key, 0) + 1

    def record_section_skipped(self, node) -> None:
        if not self.enabled:
            return
        diag = {
            "id": node.id,
            "title": node.title[:60],
            "pages": f"{node.start_index}-{node.end_index}",
            "text_chars": len(node.text),
            "text_tokens_est": len(node.text) // 4,
            "score": round(node.score, 3),
            "tier": node.tier,
            "skipped": True,
            "model_tier": "N/A",
            "model_name": "N/A",
            "text_cap": 0,
            "text_after_cap": 0,
            "truncated_chars": 0,
            "truncation_pct": 0,
            "llm_latency_ms": 0,
            "confidence": 0,
            "kpi_count": 0,
            "finding_count": 0,
            "risk_count": 0,
            "dmaic_phase": "",
            "signal_kpi": round(node.signals.get("kpi_density", 0), 3),
            "signal_financial": round(node.signals.get("financial", 0), 3),
            "signal_dmaic": round(node.signals.get("dmaic", 0), 3),
            "signal_data": round(node.signals.get("data_density", 0), 3),
            "signal_risk": round(node.signals.get("risk", 0), 3),
            "signal_boilerplate": round(node.signals.get("boilerplate", 0), 3),
            "signal_pageindex": round(node.signals.get("pageindex_boost", 0), 3),
        }
        self.section_details.append(diag)
        self.execution["total_sections_skipped"] += 1

    def finalize_execution(self, brain) -> None:
        if not self.enabled:
            return
        sections = list(brain.iter_sections())
        executed = [n for n in sections if n.execution.get("should_run", True)]
        self.execution["total_sections_executed"] = len(executed)

        total_doc_chars = brain.metadata["total_chars"]
        total_sent = self.execution["total_chars_sent_to_llm"]
        total_truncated = self.execution["total_chars_truncated"]
        self.execution["truncation_pct_overall"] = round(
            total_truncated / max(total_sent + total_truncated, 1) * 100, 1
        )

        confidences = []
        for d in self.section_details:
            if not d["skipped"] and isinstance(d["confidence"], (int, float)):
                confidences.append(d["confidence"])
        if confidences:
            self.execution["avg_confidence"] = round(sum(confidences) / len(confidences), 3)

    # ── Reprocessing ─────────────────────────────────────────────────────

    def record_reprocessing(self, candidates: int, reprocessed: int, improved: int):
        if not self.enabled:
            return
        self.reprocessing["candidates"] = candidates
        self.reprocessing["reprocessed"] = reprocessed
        self.reprocessing["improved"] = improved

    # ── DMAIC ────────────────────────────────────────────────────────────

    def record_dmaic(self, brain) -> None:
        if not self.enabled:
            return
        total = len(brain.sections)
        for phase, ids in brain.dmaic_groups.items():
            self.dmaic[phase] = len(ids)
        unassigned = self.dmaic.get("unassigned", 0)
        self.dmaic["unassigned_pct"] = round(unassigned / max(total, 1) * 100, 1)
        self.dmaic["unassigned_section_ids"] = brain.dmaic_groups.get("unassigned", [])

        # Update section_details with DMAIC phase
        phase_lookup = {}
        for phase, ids in brain.dmaic_groups.items():
            for sid in ids:
                phase_lookup[sid] = phase
        for d in self.section_details:
            d["dmaic_phase"] = phase_lookup.get(d["id"], "")

    # ── Phase Synthesis ──────────────────────────────────────────────────

    def record_synthesis(self, phase: str, section_count: int, input_chars: int):
        if not self.enabled:
            return
        self.synthesis["phases_synthesized"].append(phase)
        self.synthesis["phase_input_counts"][phase] = section_count
        self.synthesis["phase_input_chars"][phase] = input_chars

    # ── Executive Synthesis ──────────────────────────────────────────────

    def record_executive(self, prompt_chars: int, section_analyses_chars: int,
                         phase_syntheses_chars: int, success: bool, fallback: bool):
        if not self.enabled:
            return
        self.executive["prompt_chars"] = prompt_chars
        self.executive["prompt_tokens_est"] = prompt_chars // 4
        self.executive["section_analyses_chars"] = section_analyses_chars
        self.executive["phase_syntheses_chars"] = phase_syntheses_chars
        self.executive["success"] = success
        self.executive["fallback_used"] = fallback

    # ── Output Validation ────────────────────────────────────────────────

    def record_output(self, dashboard: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        dash = dashboard.get("dashboard", dashboard)

        kpis = dash.get("kpis", [])
        self.output["total_kpis"] = len(kpis)
        self.output["kpis_with_source"] = sum(
            1 for k in kpis
            if isinstance(k, dict) and (k.get("sourceSection") or k.get("source_reference"))
        )
        self.output["kpis_with_zero_value"] = sum(
            1 for k in kpis
            if isinstance(k, dict) and k.get("value") in (0, 0.0, None, "0")
        )

        sections = dash.get("sections", [])
        self.output["sections_in_output"] = len(sections)

        all_findings = sum(len(s.get("keyFindings", [])) for s in sections if isinstance(s, dict))
        all_risks = sum(len(s.get("risks", [])) for s in sections if isinstance(s, dict))
        all_recs = sum(len(s.get("recommendations", [])) for s in sections if isinstance(s, dict))
        self.output["total_findings"] = all_findings
        self.output["total_risks"] = all_risks
        self.output["total_recommendations"] = all_recs
        self.output["total_charts"] = len(dash.get("charts", []))

        # DMAIC populated phases
        six_sigma = dash.get("sixSigma", {}).get("dmaic", {})
        populated = sum(1 for p in ["define", "measure", "analyze", "improve", "control"]
                        if six_sigma.get(p))
        self.output["dmaic_phases_populated"] = populated

        qs = dash.get("qualityScore", {})
        self.output["quality_score"] = qs.get("overall_score", 0)
        self.output["quality_rating"] = qs.get("rating", "")

        self.output["has_ceo_view"] = bool(dashboard.get("ceo_view"))
        self.output["has_manager_view"] = bool(dashboard.get("manager_view"))
        self.output["has_engineer_view"] = bool(dashboard.get("engineer_view"))
        self.output["has_boardroom"] = bool(dashboard.get("boardroom_mode"))

    # ── Build Final Report ───────────────────────────────────────────────

    def build_report(self) -> Dict[str, Any]:
        """Build the complete diagnostic report. Call after pipeline completes."""
        if not self.enabled:
            return {}

        total_time_ms = round((time.time() - self._start_time) * 1000)

        # ── Data Retention Analysis (the key metric) ─────────────────────
        doc_chars = self.ingestion.get("total_chars_raw", 0)
        chars_sent = self.execution.get("total_chars_sent_to_llm", 0)
        chars_skipped = self.scoring.get("skipped_chars_total", 0)
        chars_truncated = self.execution.get("total_chars_truncated", 0)

        retention = {
            "document_total_chars": doc_chars,
            "chars_in_sections": sum(d["text_chars"] for d in self.section_details),
            "chars_skipped_by_scoring": chars_skipped,
            "chars_truncated_by_text_cap": chars_truncated,
            "chars_actually_sent_to_llm": chars_sent,
            "pct_of_doc_sent_to_llm": round(chars_sent / max(doc_chars, 1) * 100, 1),
            "pct_of_doc_skipped": round(chars_skipped / max(doc_chars, 1) * 100, 1),
            "pct_of_doc_truncated": round(chars_truncated / max(doc_chars, 1) * 100, 1),
            "pct_of_doc_never_seen_by_llm": round(
                (chars_skipped + chars_truncated) / max(doc_chars, 1) * 100, 1
            ),
        }

        # ── Critical Warnings ────────────────────────────────────────────
        warnings = []
        if retention["pct_of_doc_never_seen_by_llm"] > 30:
            warnings.append(
                f"CRITICAL: {retention['pct_of_doc_never_seen_by_llm']}% of document "
                f"was NEVER seen by any LLM ({chars_skipped + chars_truncated:,} chars lost)"
            )
        if self.scoring["skipped_count"] > 0:
            warnings.append(
                f"WARNING: {self.scoring['skipped_count']} sections SKIPPED entirely "
                f"({self.scoring['skipped_chars_total']:,} chars, "
                f"{self.scoring['skipped_pct_of_doc']}% of doc)"
            )
        if self.execution["empty_results_count"] > 0:
            warnings.append(
                f"WARNING: {self.execution['empty_results_count']} sections returned EMPTY "
                f"results (0 KPIs, 0 findings, 0 risks)"
            )
        if self.execution["low_confidence_count"] > 0:
            n = self.execution["low_confidence_count"]
            total = self.execution["total_llm_calls"]
            warnings.append(
                f"WARNING: {n}/{total} sections have LOW confidence (<0.4)"
            )
        if self.dmaic.get("unassigned", 0) > 0:
            warnings.append(
                f"INFO: {self.dmaic['unassigned']} sections unassigned to DMAIC phases "
                f"({self.dmaic['unassigned_pct']}%)"
            )
        if self.structure.get("largest_section_pages", 0) > 50:
            warnings.append(
                f"WARNING: Largest section spans {self.structure['largest_section_pages']} pages "
                f"— too large for meaningful analysis"
            )
        if self.output.get("kpis_with_zero_value", 0) > 0:
            warnings.append(
                f"WARNING: {self.output['kpis_with_zero_value']} KPIs have value=0 "
                f"(likely hallucinated)"
            )

        # ── Section-level truncation top offenders ───────────────────────
        truncation_offenders = sorted(
            [d for d in self.section_details if d["truncation_pct"] > 0],
            key=lambda x: x["truncation_pct"],
            reverse=True,
        )[:10]

        report = {
            "_diagnostics_version": "1.0",
            "total_pipeline_time_ms": total_time_ms,
            "stage_times_ms": self._stage_times,
            "warnings": warnings,
            "data_retention": retention,
            "ingestion": self.ingestion,
            "structure": self.structure,
            "scoring": self.scoring,
            "execution": self.execution,
            "reprocessing": self.reprocessing,
            "dmaic": self.dmaic,
            "synthesis": self.synthesis,
            "executive": self.executive,
            "output": self.output,
            "truncation_top_offenders": [
                {
                    "id": d["id"],
                    "title": d["title"],
                    "text_chars": d["text_chars"],
                    "text_cap": d["text_cap"],
                    "truncated_chars": d["truncated_chars"],
                    "truncation_pct": d["truncation_pct"],
                }
                for d in truncation_offenders
            ],
            "section_details": self.section_details,
        }

        # ── Log summary to console ───────────────────────────────────────
        logger.info("=" * 80)
        logger.info("PIPELINE DIAGNOSTICS REPORT")
        logger.info("=" * 80)
        for w in warnings:
            logger.warning("  %s", w)
        logger.info("  Data Retention: %.1f%% of doc sent to LLM, %.1f%% never seen",
                     retention["pct_of_doc_sent_to_llm"],
                     retention["pct_of_doc_never_seen_by_llm"])
        logger.info("  Sections: %d total, T1=%d T2=%d T3=%d, skipped=%d",
                     self.scoring["total_sections"],
                     self.scoring["tier1_count"],
                     self.scoring["tier2_count"],
                     self.scoring["tier3_count"],
                     self.scoring["skipped_count"])
        logger.info("  LLM Calls: %d, avg confidence=%.3f, empty=%d",
                     self.execution["total_llm_calls"],
                     self.execution["avg_confidence"],
                     self.execution["empty_results_count"])
        logger.info("  Output: %d KPIs (%d sourced, %d zero-value), %d findings, %d risks",
                     self.output["total_kpis"],
                     self.output["kpis_with_source"],
                     self.output["kpis_with_zero_value"],
                     self.output["total_findings"],
                     self.output["total_risks"])
        logger.info("  Total time: %dms", total_time_ms)
        logger.info("=" * 80)

        return report
