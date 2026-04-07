"""
Document Coverage Manifest — Strict Accounting for Every Page, Chunk, and Section
==================================================================================
ALWAYS ACTIVE.  This is not a diagnostic tool — it enforces correctness.

Every page extracted → every chunk created → every section built → every LLM call
is tracked with explicit status.  Coverage gates log hard failures when thresholds
are violated, preventing silent data loss.

Usage:
    manifest = DocumentManifest("doc_123")
    manifest.register_pages(total=801, parsed_pages=[1,2,4,...], empty_pages=[3], ...)
    manifest.register_chunks(brain.chunks)          # after DocumentBrain filters sentinels
    manifest.register_section("S001", "Intro", 1, 5, 12000)
    manifest.update_section_scoring("S001", 0.72, 1, True, "powerful")
    manifest.mark_section_processed("S001", text_sent=95000, confidence=0.82, ...)
    manifest.gate_ingestion()
    manifest.gate_processing()
    report = manifest.validate()
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# ENUMS & DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

class ChunkStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"           # assigned to a section
    PROCESSED = "processed"         # section was processed by LLM
    SKIPPED = "skipped"             # section was skipped (low score)
    FAILED = "failed"               # LLM call returned empty/errored


class SectionStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    SKIPPED = "skipped"
    FAILED = "failed"
    REPROCESSED = "reprocessed"


@dataclass
class ChunkEntry:
    chunk_index: int
    source_pages: List[int]         # 1-based page numbers parsed from [Page N]
    char_count: int
    status: ChunkStatus = ChunkStatus.PENDING
    section_id: Optional[str] = None
    text_sent_to_llm: int = 0
    truncated: bool = False


@dataclass
class SectionEntry:
    section_id: str
    title: str
    chunk_indices: List[int]
    page_range: Tuple[int, int]     # (start, end) — 1-based inclusive chunk indices
    status: SectionStatus = SectionStatus.PENDING
    tier: int = 0
    model_tier: str = ""
    score: float = 0.0
    should_run: bool = True
    confidence: float = 0.0
    text_chars: int = 0
    text_sent_to_llm: int = 0
    kpi_count: int = 0
    finding_count: int = 0


@dataclass
class GateResult:
    gate_name: str
    passed: bool
    threshold: str
    actual: str
    message: str


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

_PAGE_RE = re.compile(r"\[Page (\d+)\]")


class DocumentManifest:
    """
    Single source of truth for document coverage.

    Tracks every page → chunk → section → LLM output.
    ALWAYS active — not gated by any feature flag.
    """

    def __init__(self, document_id: str = ""):
        self.document_id = document_id

        # Page tracking
        self.total_pages: int = 0
        self.pages_parsed: int = 0
        self.pages_empty: List[int] = []            # 1-based page numbers with no text
        self.page_chars: Dict[int, int] = {}         # page_num → char_count

        # Chunk tracking (brain.chunks after sentinel filtering)
        self.chunks: List[ChunkEntry] = []

        # Section tracking
        self.sections: Dict[str, SectionEntry] = {}

        # Coverage gates run so far
        self.gates: List[GateResult] = []

        # Page → section mapping (built lazily)
        self._page_to_sections: Dict[int, Set[str]] = {}

    # ──────────────────────────────────────────────────────────────────────
    # REGISTRATION
    # ──────────────────────────────────────────────────────────────────────

    def register_pages(
        self,
        total_pages: int,
        parsed_pages: List[int],
        empty_pages: List[int],
        page_chars: Dict[int, int],
    ):
        """Called from process_pdf() after page extraction."""
        self.total_pages = total_pages
        self.pages_parsed = len(parsed_pages)
        self.pages_empty = empty_pages
        self.page_chars = page_chars

    def register_chunks(self, chunks: List[str]):
        """Called after DocumentBrain creation — registers brain.chunks (sentinel-free)."""
        self.chunks = []
        for idx, chunk_text in enumerate(chunks):
            source_pages = [int(m) for m in _PAGE_RE.findall(chunk_text)]
            self.chunks.append(ChunkEntry(
                chunk_index=idx,
                source_pages=source_pages,
                char_count=len(chunk_text),
            ))

    def register_section(
        self,
        section_id: str,
        title: str,
        start_index: int,
        end_index: int,
        text_chars: int,
    ):
        """Called from build_structure() for each SectionNode created."""
        # Chunk indices covered by this section (0-based in brain.chunks)
        chunk_indices = list(range(
            max(0, start_index - 1),
            min(end_index, len(self.chunks)),
        ))

        entry = SectionEntry(
            section_id=section_id,
            title=title,
            chunk_indices=chunk_indices,
            page_range=(start_index, end_index),
            text_chars=text_chars,
        )
        self.sections[section_id] = entry

        # Mark chunks as assigned
        for ci in chunk_indices:
            if ci < len(self.chunks):
                self.chunks[ci].status = ChunkStatus.ASSIGNED
                self.chunks[ci].section_id = section_id

        # Build page → section mapping
        for ci in chunk_indices:
            if ci < len(self.chunks):
                for pn in self.chunks[ci].source_pages:
                    self._page_to_sections.setdefault(pn, set()).add(section_id)

    def update_section_scoring(
        self,
        section_id: str,
        score: float,
        tier: int,
        should_run: bool,
        model_tier: str,
    ):
        """Called after scoring + classification + routing."""
        entry = self.sections.get(section_id)
        if not entry:
            return
        entry.score = score
        entry.tier = tier
        entry.should_run = should_run
        entry.model_tier = model_tier

        if not should_run:
            entry.status = SectionStatus.SKIPPED
            for ci in entry.chunk_indices:
                if ci < len(self.chunks):
                    self.chunks[ci].status = ChunkStatus.SKIPPED

    # ──────────────────────────────────────────────────────────────────────
    # STATUS UPDATES (called during execution)
    # ──────────────────────────────────────────────────────────────────────

    def mark_section_processed(
        self,
        section_id: str,
        text_sent: int,
        confidence: float,
        kpi_count: int,
        finding_count: int,
    ):
        """Called from execute_analysis() after successful LLM call."""
        entry = self.sections.get(section_id)
        if not entry:
            return
        entry.status = SectionStatus.PROCESSED
        entry.text_sent_to_llm = text_sent
        entry.confidence = confidence
        entry.kpi_count = kpi_count
        entry.finding_count = finding_count

        section_total = entry.text_chars
        for ci in entry.chunk_indices:
            if ci < len(self.chunks):
                self.chunks[ci].status = ChunkStatus.PROCESSED
                # Estimate per-chunk contribution
                c_chars = self.chunks[ci].char_count
                if section_total > 0:
                    ratio = min(1.0, text_sent / section_total)
                    self.chunks[ci].text_sent_to_llm = int(c_chars * ratio)
                    self.chunks[ci].truncated = ratio < 0.95

    def mark_section_failed(self, section_id: str):
        """Called when LLM returns an empty/default result."""
        entry = self.sections.get(section_id)
        if not entry:
            return
        entry.status = SectionStatus.FAILED
        for ci in entry.chunk_indices:
            if ci < len(self.chunks):
                self.chunks[ci].status = ChunkStatus.FAILED

    def mark_section_reprocessed(self, section_id: str, confidence: float):
        """Called from reprocess_weak() after upgrading a weak section."""
        entry = self.sections.get(section_id)
        if not entry:
            return
        entry.status = SectionStatus.REPROCESSED
        entry.confidence = confidence

    # ──────────────────────────────────────────────────────────────────────
    # COVERAGE GATES
    # ──────────────────────────────────────────────────────────────────────

    def gate_ingestion(self, min_parse_pct: float = 0.95) -> GateResult:
        """Gate 1: Did we extract text from enough pages?"""
        if self.total_pages == 0:
            result = GateResult(
                "ingestion", True,
                f">={min_parse_pct * 100:.0f}%", "N/A (no pages)",
                "No pages to check",
            )
            self.gates.append(result)
            return result

        actual_pct = self.pages_parsed / self.total_pages
        passed = actual_pct >= min_parse_pct
        msg = (
            f"{'PASS' if passed else 'FAIL'}: "
            f"{self.pages_parsed}/{self.total_pages} pages extracted "
            f"({actual_pct * 100:.1f}%)"
        )
        if self.pages_empty:
            msg += f" | {len(self.pages_empty)} empty: {self.pages_empty[:20]}"

        result = GateResult(
            gate_name="ingestion",
            passed=passed,
            threshold=f">={min_parse_pct * 100:.0f}% pages parsed",
            actual=f"{actual_pct * 100:.1f}% ({self.pages_parsed}/{self.total_pages})",
            message=msg,
        )
        self.gates.append(result)
        (logger.info if passed else logger.error)(
            "COVERAGE GATE [ingestion]: %s", result.message,
        )
        return result

    def gate_chunking(self) -> GateResult:
        """Gate 2: Are all chunks assigned to sections?"""
        orphan = [c for c in self.chunks if not c.source_pages]
        unassigned = [c for c in self.chunks if c.status == ChunkStatus.PENDING]
        passed = len(orphan) == 0 and len(unassigned) == 0
        msg = (
            f"{'PASS' if passed else 'WARN'}: "
            f"{len(self.chunks)} chunks, "
            f"{len(orphan)} without page mapping, "
            f"{len(unassigned)} not assigned to any section"
        )
        result = GateResult(
            gate_name="chunking",
            passed=passed,
            threshold="0 orphan, 0 unassigned chunks",
            actual=f"{len(orphan)} orphan, {len(unassigned)} unassigned",
            message=msg,
        )
        self.gates.append(result)
        (logger.info if passed else logger.warning)(
            "COVERAGE GATE [chunking]: %s", result.message,
        )
        return result

    def gate_processing(self, min_processed_pct: float = 0.80) -> GateResult:
        """Gate 3: Were enough sections actually processed by an LLM?"""
        total = len(self.sections)
        if total == 0:
            result = GateResult(
                "processing", True,
                f">={min_processed_pct * 100:.0f}%", "N/A (no sections)",
                "No sections to check",
            )
            self.gates.append(result)
            return result

        processed = sum(
            1 for s in self.sections.values()
            if s.status in (SectionStatus.PROCESSED, SectionStatus.REPROCESSED)
        )
        actual_pct = processed / total
        passed = actual_pct >= min_processed_pct

        skipped = [s for s in self.sections.values() if s.status == SectionStatus.SKIPPED]
        failed = [s for s in self.sections.values() if s.status == SectionStatus.FAILED]

        msg = (
            f"{'PASS' if passed else 'FAIL'}: "
            f"{processed}/{total} sections processed ({actual_pct * 100:.1f}%)"
        )
        if skipped:
            msg += f" | {len(skipped)} skipped: {[s.section_id for s in skipped[:10]]}"
        if failed:
            msg += f" | {len(failed)} failed: {[s.section_id for s in failed[:10]]}"

        result = GateResult(
            gate_name="processing",
            passed=passed,
            threshold=f">={min_processed_pct * 100:.0f}% sections processed",
            actual=f"{actual_pct * 100:.1f}% ({processed}/{total})",
            message=msg,
        )
        self.gates.append(result)
        (logger.info if passed else logger.error)(
            "COVERAGE GATE [processing]: %s", result.message,
        )
        return result

    # ──────────────────────────────────────────────────────────────────────
    # PAGE HEATMAP
    # ──────────────────────────────────────────────────────────────────────

    def build_page_heatmap(self) -> Dict[str, Any]:
        """Page-level coverage heatmap: which pages were actually analyzed."""
        pages_analyzed: Set[int] = set()
        pages_skipped: Set[int] = set()

        for sec in self.sections.values():
            page_nums: Set[int] = set()
            for ci in sec.chunk_indices:
                if ci < len(self.chunks):
                    page_nums.update(self.chunks[ci].source_pages)
            if sec.status in (SectionStatus.PROCESSED, SectionStatus.REPROCESSED):
                pages_analyzed.update(page_nums)
            elif sec.status == SectionStatus.SKIPPED:
                pages_skipped.update(page_nums)

        # Pages with text that are NOT in any section
        all_content = set(range(1, self.total_pages + 1)) - set(self.pages_empty)
        pages_assigned = pages_analyzed | pages_skipped
        pages_never_assigned = all_content - pages_assigned
        total_content = len(all_content)

        return {
            "total_pages": self.total_pages,
            "empty_pages": len(self.pages_empty),
            "content_pages": total_content,
            "pages_analyzed": len(pages_analyzed),
            "pages_in_skipped_sections": len(pages_skipped),
            "pages_never_assigned": len(pages_never_assigned),
            "analysis_coverage_pct": round(
                len(pages_analyzed) / max(total_content, 1) * 100, 1,
            ),
            "never_assigned_page_numbers": sorted(pages_never_assigned)[:50],
            "skipped_section_page_numbers": sorted(pages_skipped)[:50],
        }

    # ──────────────────────────────────────────────────────────────────────
    # FINAL VALIDATION
    # ──────────────────────────────────────────────────────────────────────

    def validate(self) -> Dict[str, Any]:
        """
        Run after pipeline completes.  Returns a comprehensive validation
        report and logs results prominently.
        """
        heatmap = self.build_page_heatmap()

        # Chunk status counts
        chunk_statuses: Dict[str, int] = {}
        for c in self.chunks:
            chunk_statuses[c.status.value] = chunk_statuses.get(c.status.value, 0) + 1

        # Section status counts
        section_statuses: Dict[str, int] = {}
        for s in self.sections.values():
            section_statuses[s.status.value] = section_statuses.get(s.status.value, 0) + 1

        pending_chunks = [c.chunk_index for c in self.chunks if c.status == ChunkStatus.PENDING]
        failed_chunks = [c.chunk_index for c in self.chunks if c.status == ChunkStatus.FAILED]

        problem_sections = []
        for s in self.sections.values():
            if s.status in (SectionStatus.SKIPPED, SectionStatus.FAILED):
                pages: Set[int] = set()
                for ci in s.chunk_indices:
                    if ci < len(self.chunks):
                        pages.update(self.chunks[ci].source_pages)
                problem_sections.append({
                    "section_id": s.section_id,
                    "title": s.title[:60],
                    "status": s.status.value,
                    "score": round(s.score, 3),
                    "pages": sorted(pages)[:20],
                    "page_count": len(pages),
                    "chars": s.text_chars,
                })

        all_passed = all(g.passed for g in self.gates)

        report = {
            "document_id": self.document_id,
            "all_gates_passed": all_passed,
            "gates": [
                {
                    "name": g.gate_name,
                    "passed": g.passed,
                    "threshold": g.threshold,
                    "actual": g.actual,
                    "message": g.message,
                }
                for g in self.gates
            ],
            "page_coverage": heatmap,
            "chunk_summary": {
                "total": len(self.chunks),
                "statuses": chunk_statuses,
                "pending_indices": pending_chunks[:50],
                "failed_indices": failed_chunks[:50],
            },
            "section_summary": {
                "total": len(self.sections),
                "statuses": section_statuses,
                "problem_sections": problem_sections[:20],
            },
        }

        # ── Prominent console output ─────────────────────────────────────
        logger.info("=" * 80)
        logger.info("DOCUMENT COVERAGE MANIFEST — VALIDATION REPORT")
        logger.info("=" * 80)
        logger.info("  Document: %s", self.document_id)
        logger.info(
            "  Pages: %d total, %d parsed, %d empty",
            self.total_pages, self.pages_parsed, len(self.pages_empty),
        )
        logger.info("  Chunks: %d total | %s", len(self.chunks), chunk_statuses)
        logger.info("  Sections: %d total | %s", len(self.sections), section_statuses)
        logger.info(
            "  Page Heatmap: %d/%d content pages analyzed (%.1f%%)",
            heatmap["pages_analyzed"],
            heatmap["content_pages"],
            heatmap["analysis_coverage_pct"],
        )
        if heatmap["pages_never_assigned"]:
            logger.warning(
                "  MISSING: %d pages never assigned to any section: %s",
                heatmap["pages_never_assigned"],
                heatmap["never_assigned_page_numbers"][:20],
            )
        for g in self.gates:
            log_fn = logger.info if g.passed else logger.error
            log_fn(
                "  Gate [%s]: %s — %s",
                g.gate_name, "PASS" if g.passed else "FAIL", g.message,
            )
        if problem_sections:
            logger.warning("  Problem sections (%d):", len(problem_sections))
            for ps in problem_sections[:10]:
                logger.warning(
                    "    %s (%s) — score=%.3f, %d pages, %d chars",
                    ps["section_id"], ps["status"], ps["score"],
                    ps["page_count"], ps["chars"],
                )
        logger.info("  ALL GATES PASSED: %s", all_passed)
        logger.info("=" * 80)

        return report
