"""
Chunk Processor Module

Processes individual PDF chunks through the LLM pipeline.
Extracts structured data from each chunk and handles retry logic.

Features:
- Process single chunk through LLM
- Extract RIGs, well data, metrics, events
- Structured JSON output per chunk
- Retry logic with exponential backoff
- Error handling and recovery
"""

import json
import logging
from typing import Dict, Any, List, Optional
import time
import re

logger = logging.getLogger(__name__)


class ChunkProcessor:
    """
    Processes a single PDF chunk through the extraction pipeline.
    """
    
    def __init__(self, llm_provider=None, max_retries: int = 3):
        """
        Initialize chunk processor.
        
        Args:
            llm_provider: LLM provider instance (e.g., Grok)
            max_retries: Maximum retry attempts per chunk
        """
        self.llm_provider = llm_provider
        self.max_retries = max_retries
    
    def process_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single PDF chunk and extract structured data.
        
        Args:
            chunk: Chunk dictionary from PDFChunker
            
        Returns:
            Structured extraction result including RIGs, metrics, events
        """
        chunk_id = chunk.get('chunk_id', -1)
        start_page = chunk.get('start_page', 0)
        end_page = chunk.get('end_page', 0)
        text = chunk.get('text', '')
        
        logger.info(f"Processing chunk {chunk_id} (pages {start_page}-{end_page}"
                   f", {len(text):,} chars)")
        
        result = {
            "chunk_id": chunk_id,
            "start_page": start_page,
            "end_page": end_page,
            "status": "processing",
            "rigs": [],
            "metrics": {},
            "events": [],
            "extraction_metadata": {
                "chars_processed": len(text),
                "pages_covered": end_page - start_page + 1
            }
        }
        
        try:
            # Extract via LLM if provider available
            if self.llm_provider:
                extraction = self._extract_via_llm(text, chunk_id)
                if extraction:
                    result["rigs"] = extraction.get("rigs", [])
                    result["metrics"] = extraction.get("metrics", {})
                    result["events"] = extraction.get("events", [])
            
            # Fallback: extract via patterns if LLM fails or unavailable
            if not result["rigs"]:
                pattern_extraction = self._extract_via_patterns(text)
                result["rigs"] = pattern_extraction.get("rigs", [])
                result["metrics"] = pattern_extraction.get("metrics", {})
                result["events"] = pattern_extraction.get("events", [])
            
            result["status"] = "completed"
            logger.info(f"Chunk {chunk_id} processing complete: "
                       f"{len(result['rigs'])} RIGs extracted")
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_id}: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result
    
    def _extract_via_llm(self, text: str, chunk_id: int) -> Optional[Dict[str, Any]]:
        """
        Extract structured data using LLM.
        Includes retry logic with exponential backoff.
        """
        if not self.llm_provider:
            return None
        
        prompt = self._build_extraction_prompt(text, chunk_id)
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"LLM extraction attempt {attempt + 1}/{self.max_retries}")
                
                response = self.llm_provider.generate_json(prompt)
                
                # Validate and structure response
                if isinstance(response, dict):
                    return self._structure_llm_response(response)
                
                logger.warning(f"Invalid LLM response type: {type(response)}")
                
            except Exception as e:
                logger.warning(f"LLM extraction attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"LLM extraction failed after {self.max_retries} attempts")
        
        return None
    
    def _extract_via_patterns(self, text: str) -> Dict[str, Any]:
        """
        Extract structured data using regex patterns.
        Fallback when LLM is unavailable.
        """
        result = {
            "rigs": [],
            "metrics": {},
            "events": []
        }
        
        # Extract RIG identifiers (e.g., QTIF-790, MNIF-100, 088TE, 095TE)
        rig_patterns = [
            r'(?:RIG|Rig|rig)\s+(\w+-\w+)',  # RIG QTIF-790 format
            r'(?:Rig|rig)\s+(\w+)',  # Rig 088TE format
            r'(\w{2,4}[I|i][F|f]-\w+)',  # QTIF-790 format
        ]
        
        rigs_found = {}
        for pattern in rig_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                rig_id = match.group(1).upper()
                if rig_id not in rigs_found:
                    rigs_found[rig_id] = {
                        "rig_id": rig_id,
                        "mentions": 1,
                        "context": text[max(0, match.start()-50):match.end()+50]
                    }
                else:
                    rigs_found[rig_id]["mentions"] += 1
        
        result["rigs"] = list(rigs_found.values())
        
        # Extract dates
        date_pattern = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}'
        dates = re.findall(date_pattern, text)
        if dates:
            result["metrics"]["dates_found"] = dates
        
        # Extract depths (e.g., "23,695 ft MD")
        depth_pattern = r'([\d,]+)\s*ft\s+(?:MD|TVD)'
        depths = re.findall(depth_pattern, text, re.IGNORECASE)
        if depths:
            result["metrics"]["depths_found"] = depths
        
        # Extract well types
        well_types = re.findall(
            r'(?:disposal|oil|gas|producer|injector)(?:\s+well)?',
            text,
            re.IGNORECASE
        )
        if well_types:
            result["metrics"]["well_types"] = list(set(well_types))
        
        # Extract key events
        event_keywords = [
            'stuck pipe', 'lost in hole', 'sidetrack', 'cement', 
            'injectivity', 'squeeze job', 'drilling'
        ]
        events = []
        for keyword in event_keywords:
            if keyword.lower() in text.lower():
                events.append(keyword)
        
        if events:
            result["events"] = events
        
        return result
    
    def _build_extraction_prompt(self, chunk_text: str, chunk_id: int) -> str:
        """Build LLM prompt for structured extraction from chunk"""
        prompt = f"""
Extract structured data from this drilling operations report (Chunk {chunk_id}).

DOCUMENT EXCERPT:
---
{chunk_text[:5000]}  # First 5K chars for context
---

Extract and return JSON with:
1. "rigs": List of RIG objects {{
   "rig_id": "e.g. QTIF-790 or 088TE",
   "rig_name": "Full name if available",
   "well_name": "e.g. QTIF-790",
   "well_type": "disposal/oil/gas/producer/injector",
   "depth_md": "e.g. 23695 ft MD",
   "depth_tvd": "if available",
   "operations": ["list of main operations"],
   "status": "current status",
   "date": "operation date if mentioned"
}}

2. "metrics": {{
   "total_rigs": count,
   "total_wells": count,
   "avg_depth": "average depth",
   "operations_count": count
}}

3. "events": ["major events mentioned", "stuck drill pipe", "cement squeeze"]

Return ONLY valid JSON, no other text.
"""
        return prompt.strip()
    
    def _structure_llm_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and structure LLM response"""
        try:
            result = {
                "rigs": response.get("rigs", []),
                "metrics": response.get("metrics", {}),
                "events": response.get("events", [])
            }
            
            # Ensure rigs is a list
            if not isinstance(result["rigs"], list):
                result["rigs"] = []
            
            # Ensure metrics is a dict
            if not isinstance(result["metrics"], dict):
                result["metrics"] = {}
            
            # Ensure events is a list
            if not isinstance(result["events"], list):
                result["events"] = []
            
            return result
        except Exception as e:
            logger.error(f"Error structuring LLM response: {e}")
            return None


def process_pdf_chunks(
    chunks: List[Dict[str, Any]],
    llm_provider=None,
    batch_size: int = 1,
    parallel: bool = False
) -> List[Dict[str, Any]]:
    """
    Process multiple PDF chunks in sequence or parallel.
    
    Args:
        chunks: List of chunk dictionaries from PDFChunker
        llm_provider: LLM provider instance
        batch_size: Number of chunks to process in parallel (if parallel=True)
        parallel: Whether to use parallel processing
        
    Returns:
        List of extraction results, one per chunk
    """
    processor = ChunkProcessor(llm_provider=llm_provider)
    results = []
    
    total_chunks = len(chunks)
    for idx, chunk in enumerate(chunks, 1):
        logger.info(f"Processing chunk {idx}/{total_chunks}")
        result = processor.process_chunk(chunk)
        results.append(result)
    
    logger.info(f"All {len(results)} chunks processed")
    return results
