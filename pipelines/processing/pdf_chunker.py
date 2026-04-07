"""
PDF Chunking Module

Intelligently splits large PDFs into manageable chunks for processing.
Each chunk respects page boundaries and is sized to fit within LLM context limits.

Features:
- Remove hard page limits
- Intelligent page-aware chunking
- Configurable chunk size (pages per chunk)
- Preserve page numbering and traceability
- Character-based sizing for context limit enforcement
- Detailed logging
"""

import logging
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)


class PDFChunk:
    """Represents a single chunk of a PDF document"""
    
    def __init__(
        self, 
        chunk_id: int,
        start_page: int,
        end_page: int,
        text: str,
        char_count: int,
        page_count: int
    ):
        self.chunk_id = chunk_id
        self.start_page = start_page
        self.end_page = end_page
        self.text = text
        self.char_count = char_count
        self.page_count = page_count
    
    def to_dict(self) -> dict:
        """Convert chunk to dictionary representation"""
        return {
            "chunk_id": self.chunk_id,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "page_count": self.page_count,
            "char_count": self.char_count,
            "text": self.text
        }


class PDFChunker:
    """
    Splits large PDF text into manageable chunks.
    
    Configuration:
    - target_pages_per_chunk: Target number of pages per chunk (default 150)
    - max_chunk_chars: Hard limit on chunk size in characters (default 250K)
    """
    
    def __init__(
        self,
        target_pages_per_chunk: int = 150,
        max_chunk_chars: int = 250_000
    ):
        self.target_pages_per_chunk = target_pages_per_chunk
        self.max_chunk_chars = max_chunk_chars
    
    def chunk_by_page_separators(
        self,
        pdf_text: str,
        total_pages: int
    ) -> List[PDFChunk]:
        """
        Split PDF text into chunks using page boundary detection.
        
        Args:
            pdf_text: Full text extracted from PDF (pages joined by "\n\n")
            total_pages: Total number of pages in original PDF
            
        Returns:
            List of PDFChunk objects
        """
        if not pdf_text or total_pages <= 0:
            logger.warning("Invalid input to chunk_by_page_separators")
            return []
        
        # Calculate pages per chunk
        pages_per_chunk = max(1, self.target_pages_per_chunk)
        
        # If document fits in one chunk, return as-is
        if total_pages <= pages_per_chunk:
            chunk = PDFChunk(
                chunk_id=1,
                start_page=1,
                end_page=total_pages,
                text=pdf_text,
                char_count=len(pdf_text),
                page_count=total_pages
            )
            logger.info(f"Single chunk created: pages 1-{total_pages} ({len(pdf_text):,} chars)")
            return [chunk]
        
        # Split into multiple chunks
        chunks = []
        chunk_id = 1
        
        # Estimate chars per page
        chars_per_page = len(pdf_text) / total_pages
        estimated_chunk_chars = int(chars_per_page * pages_per_chunk)
        
        # Split by approximate page boundaries
        current_pos = 0
        chunk_start_page = 1
        
        while current_pos < len(pdf_text) and chunk_start_page <= total_pages:
            # Calculate chunk end position
            chunk_end_pos = min(
                current_pos + estimated_chunk_chars,
                len(pdf_text)
            )
            
            # Find a good break point (paragraph boundary or page boundary)
            break_pos = self._find_break_point(pdf_text, chunk_end_pos)
            if break_pos <= current_pos:
                break_pos = chunk_end_pos
            
            chunk_text = pdf_text[current_pos:break_pos].strip()
            
            # Calculate actual page range
            pages_before = len(re.findall(r'\n\n', pdf_text[:current_pos]))
            pages_in_chunk = len(re.findall(r'\n\n', chunk_text))
            chunk_end_page = min(chunk_start_page + pages_in_chunk, total_pages)
            
            # Ensure page range is valid
            if chunk_end_page < chunk_start_page:
                chunk_end_page = chunk_start_page
            
            # Create chunk
            chunk = PDFChunk(
                chunk_id=chunk_id,
                start_page=chunk_start_page,
                end_page=chunk_end_page,
                text=chunk_text,
                char_count=len(chunk_text),
                page_count=chunk_end_page - chunk_start_page + 1
            )
            
            # Enforce max character limit if needed
            if len(chunk.text) > self.max_chunk_chars:
                logger.warning(
                    f"Chunk {chunk_id} exceeds max chars "
                    f"({len(chunk.text):,} > {self.max_chunk_chars:,}), truncating"
                )
                chunk.text = chunk.text[:self.max_chunk_chars]
            
            chunks.append(chunk)
            logger.info(
                f"Chunk {chunk_id} created: "
                f"pages {chunk.start_page}-{chunk.end_page} "
                f"({chunk.char_count:,} chars)"
            )
            
            # Move to next chunk
            current_pos = break_pos
            chunk_start_page = chunk_end_page + 1
            chunk_id += 1
            
            # Safety check to avoid infinite loops
            if chunk_id > 100:
                logger.error("Too many chunks created, stopping at chunk 100")
                break
        
        logger.info(
            f"PDF chunking complete: {len(chunks)} chunks from {total_pages} pages, "
            f"total {len(pdf_text):,} characters"
        )
        
        return chunks
    
    def _find_break_point(self, text: str, preferred_pos: int, window: int = 5000) -> int:
        """
        Find a good break point (paragraph boundary) near the preferred position.
        
        Searches within a window around preferred_pos for paragraph boundaries (\n\n).
        Falls back to preferred_pos if no boundary found.
        """
        # Search for paragraph break within window
        search_start = max(0, preferred_pos - window)
        search_end = min(len(text), preferred_pos + window)
        
        # Look for last \n\n before preferred_pos
        search_region = text[search_start:preferred_pos]
        last_break = search_region.rfind('\n\n')
        
        if last_break >= 0:
            return search_start + last_break + 2
        
        # Look for sentence ending
        for pattern in ['. ', '! ', '? ']:
            last_sentence = search_region.rfind(pattern)
            if last_sentence >= 0:
                return search_start + last_sentence + len(pattern)
        
        # Fallback to preferred position
        return preferred_pos


def create_pdf_chunks(
    pdf_text: str,
    total_pages: int,
    target_pages_per_chunk: int = 150,
    max_chunk_chars: int = 250_000
) -> List[Dict[str, Any]]:
    """
    Convenience function to chunk a PDF.
    
    Args:
        pdf_text: Full extracted PDF text
        total_pages: Total pages in PDF
        target_pages_per_chunk: Target pages per chunk
        max_chunk_chars: Maximum characters per chunk
        
    Returns:
        List of chunk dictionaries ready for processing
    """
    chunker = PDFChunker(
        target_pages_per_chunk=target_pages_per_chunk,
        max_chunk_chars=max_chunk_chars
    )
    
    chunks = chunker.chunk_by_page_separators(pdf_text, total_pages)
    return [chunk.to_dict() for chunk in chunks]
