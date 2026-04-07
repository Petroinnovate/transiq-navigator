"""
Adaptive chunker with hierarchical and table-aware support
"""
import re
from typing import List, Dict, Any, Optional
from app.processors.chunker.base import BaseChunker
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AdaptiveChunker(BaseChunker):
    """
    Adaptive chunker that intelligently splits text while preserving
    semantic boundaries, hierarchical structure, and table formatting.
    Optimised for speed: O(n) single-pass, no quadratic regex rescans.
    """

    def __init__(self, max_chars: int = None, overlap: int = None):
        self.max_chars = max_chars or settings.DEFAULT_CHUNK_SIZE
        self.overlap = overlap or settings.DEFAULT_CHUNK_OVERLAP

        self.heading_pattern   = re.compile(r'^(#{1,6}|\d+\.|\*\*|__)\s+.+$', re.MULTILINE)
        self.paragraph_pattern = re.compile(r'\n\s*\n')
        self.sentence_pattern  = re.compile(r'(?<=[.!?])\s+')
        self.list_pattern      = re.compile(r'^\s*[-*+]\s+', re.MULTILINE)

    def _identify_boundaries(self, text: str) -> List[tuple]:
        boundaries = []
        for m in self.heading_pattern.finditer(text):
            boundaries.append((m.start(), 1))
        for m in self.paragraph_pattern.finditer(text):
            boundaries.append((m.start(), 2))
        for m in self.list_pattern.finditer(text):
            if m.start() > 0 and text[m.start() - 1] == '\n':
                boundaries.append((m.start(), 3))
        for m in re.finditer(r'[.!?]\s+[A-Z]', text):
            boundaries.append((m.end() - 1, 4))
        boundaries.sort(key=lambda x: x[0])
        return boundaries

    def _has_table(self, segment: str) -> bool:
        return sum(1 for line in segment.splitlines() if '|' in line) >= 2

    def _extract_table(self, segment: str) -> Optional[str]:
        lines = segment.splitlines()
        t_start = t_end = None
        for i, line in enumerate(lines):
            if '|' in line:
                if t_start is None:
                    t_start = i
                t_end = i
        return '\n'.join(lines[t_start:t_end + 1]) if t_start is not None else None

    def chunk(self, text: str, **kwargs) -> List[str]:
        max_chars = kwargs.get('max_chars', self.max_chars)
        overlap   = kwargs.get('overlap',   self.overlap)

        if not text or len(text) <= max_chars:
            return [text.strip()] if text and text.strip() else []

        chunks = []
        boundaries = self._identify_boundaries(text)
        b_idx = 0
        start_pos = 0

        while start_pos < len(text):
            target_end = start_pos + max_chars

            while b_idx < len(boundaries) and boundaries[b_idx][0] <= start_pos:
                b_idx += 1

            best_break = None
            best_priority = float('inf')
            for i in range(b_idx, len(boundaries)):
                pos, priority = boundaries[i]
                if pos > target_end:
                    break
                if priority < best_priority:
                    best_priority = priority
                    best_break = pos

            end_pos = best_break if best_break else min(target_end, len(text))
            segment = text[start_pos:end_pos].strip()

            if segment and self._has_table(segment):
                table = self._extract_table(segment)
                if table and len(table) <= max_chars:
                    segment = table

            if segment:
                chunks.append(segment)

            if end_pos >= len(text):
                break

            # Move start back by overlap, then skip to next sentence boundary.
            # If no sentence boundary exists (e.g. tables/numbers), jump straight
            # to end_pos so we always make forward progress and never infinite-loop.
            overlap_start = max(start_pos, end_pos - overlap)
            m = self.sentence_pattern.search(text[overlap_start:])
            if m:
                start_pos = overlap_start + m.end()
            else:
                start_pos = end_pos  # no sentence boundary — skip overlap entirely

        return chunks

    def chunk_with_metadata(self, text: str, **kwargs) -> List[Dict[str, Any]]:
        chunks = self.chunk(text, **kwargs)
        result = []
        cursor = 0
        for idx, chunk_text in enumerate(chunks):
            pos = text.find(chunk_text, cursor)
            if pos == -1:
                pos = cursor
            end_pos = pos + len(chunk_text)
            chunk_type = "table" if self._has_table(chunk_text) else (
                         "heading" if self.heading_pattern.search(chunk_text) else "text")
            result.append({
                'text':      chunk_text,
                'index':     idx,
                'start_pos': pos,
                'end_pos':   end_pos,
                'type':      chunk_type,
                'length':    len(chunk_text),
            })
            cursor = end_pos
        return result
