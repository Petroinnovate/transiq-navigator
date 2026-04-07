"""
Result Aggregation Module

Merges and deduplicates extraction results from multiple PDF chunks.
Creates a unified final dataset representing the complete document.

Features:
- Aggregate results across all chunks
- Deduplicate RIGs and metrics
- Preserve chunk traceability
- Generate summary statistics
- Handle conflicts/inconsistencies
"""

import logging
from typing import Dict, List, Any, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class ResultAggregator:
    """
    Aggregates extraction results from multiple chunks into a unified result.
    """
    
    def __init__(self):
        self.rigs_by_id: Dict[str, Dict[str, Any]] = {}
        self.all_events: List[str] = []
        self.metrics: Dict[str, Any] = {}
        self.chunk_results: List[Dict[str, Any]] = []
    
    def aggregate(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from all chunks.
        
        Args:
            chunk_results: List of extraction results from each chunk
            
        Returns:
            Unified result dict with aggregated data
        """
        self.chunk_results = chunk_results
        
        if not chunk_results:
            logger.warning("No chunk results to aggregate")
            return self._empty_result()
        
        # Process each chunk
        for result in chunk_results:
            self._merge_chunk_result(result)
        
        # Generate final aggregation
        final_result = {
            "status": "completed",
            "summary": self._generate_summary(chunk_results),
            "rigs": list(self.rigs_by_id.values()),
            "unique_rigs_count": len(self.rigs_by_id),
            "events": list(set(self.all_events)),  # Deduplicate events
            "metrics": self.metrics,
            "chunk_details": chunk_results,
            "processing_info": {
                "total_chunks": len(chunk_results),
                "successful_chunks": sum(1 for r in chunk_results if r.get("status") == "completed"),
                "failed_chunks": sum(1 for r in chunk_results if r.get("status") == "failed")
            }
        }
        
        logger.info(
            f"Aggregation complete: {len(self.rigs_by_id)} unique RIGs, "
            f"{len(set(self.all_events))} events, {len(chunk_results)} chunks"
        )
        
        return final_result
    
    def _merge_chunk_result(self, chunk_result: Dict[str, Any]):
        """Merge a single chunk result into aggregated state"""
        chunk_id = chunk_result.get('chunk_id')
        
        # Merge RIGs
        rigs = chunk_result.get('rigs', [])
        for rig in rigs:
            rig_id = rig.get('rig_id') or rig.get('well_name')
            
            if not rig_id:
                logger.warning(f"RIG in chunk {chunk_id} missing ID, skipping")
                continue
            
            if rig_id not in self.rigs_by_id:
                # First mention of this RIG
                self.rigs_by_id[rig_id] = {
                    **rig,
                    "chunk_ids": [chunk_id],
                    "mention_count": 1
                }
            else:
                # Update existing RIG with new occurrence
                existing = self.rigs_by_id[rig_id]
                existing["chunk_ids"].append(chunk_id)
                existing["mention_count"] = existing.get("mention_count", 1) + 1
                
                # Merge additional fields
                for key in ['well_type', 'depth_md', 'depth_tvd', 'rig_name']:
                    if key in rig and key not in existing:
                        existing[key] = rig[key]
                
                # Merge operations if present
                if 'operations' in rig:
                    if 'operations' not in existing:
                        existing['operations'] = []
                    for op in rig['operations']:
                        if op not in existing['operations']:
                            existing['operations'].append(op)
        
        # Merge events
        events = chunk_result.get('events', [])
        self.all_events.extend(events)
        
        # Merge metrics
        chunk_metrics = chunk_result.get('metrics', {})
        for key, value in chunk_metrics.items():
            if key not in self.metrics:
                self.metrics[key] = value
            else:
                # Try to aggregate numeric values
                if isinstance(value, (int, float)) and isinstance(self.metrics[key], (int, float)):
                    self.metrics[key] += value
    
    def _generate_summary(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from aggregation"""
        total_rigs = len(self.rigs_by_id)
        total_events = len(set(self.all_events))
        
        # Calculate pages covered
        total_pages = 0
        total_chars = 0
        for result in chunk_results:
            extraction_meta = result.get('extraction_metadata', {})
            total_pages += extraction_meta.get('pages_covered', 0)
            total_chars += extraction_meta.get('chars_processed', 0)
        
        # Get RIG details for summary
        rig_summary = []
        for rig_id, rig_data in self.rigs_by_id.items():
            rig_summary.append({
                "rig_id": rig_id,
                "well_name": rig_data.get('well_name'),
                "well_type": rig_data.get('well_type'),
                "depth_md": rig_data.get('depth_md'),
                "mention_count": rig_data.get('mention_count', 1),
                "chunk_ids": rig_data.get('chunk_ids', [])
            })
        
        return {
            "total_pages_processed": total_pages,
            "total_chars_processed": total_chars,
            "total_chunks": len(chunk_results),
            "total_rigs_detected": total_rigs,
            "total_unique_events": total_events,
            "rigs_by_type": self._group_rigs_by_type(),
            "top_rigs": sorted(
                rig_summary,
                key=lambda x: x['mention_count'],
                reverse=True
            )[:10]
        }
    
    def _group_rigs_by_type(self) -> Dict[str, int]:
        """Group RIGs by well type"""
        by_type = defaultdict(int)
        for rig_data in self.rigs_by_id.values():
            well_type = rig_data.get('well_type', 'unknown')
            by_type[well_type] += 1
        return dict(by_type)
    
    def _empty_result(self) -> Dict[str, Any]:
        """Create empty result structure"""
        return {
            "status": "no_data",
            "summary": {
                "total_pages_processed": 0,
                "total_chunks": 0,
                "total_rigs_detected": 0,
                "total_unique_events": 0
            },
            "rigs": [],
            "events": [],
            "metrics": {},
            "chunk_details": []
        }


def aggregate_chunk_results(
    chunk_results: List[Dict[str, Any]],
    total_pages: int = None
) -> Dict[str, Any]:
    """
    Convenience function to aggregate chunk results.
    
    Args:
        chunk_results: List of results from chunk_processor.process_pdf_chunks()
        total_pages: Total pages in original document (optional, for context)
        
    Returns:
        Unified result dictionary
    """
    aggregator = ResultAggregator()
    result = aggregator.aggregate(chunk_results)
    
    # Add total pages context if provided
    if total_pages:
        result["summary"]["total_pages_in_document"] = total_pages
        if result["summary"]["total_pages_processed"] > 0:
            coverage_pct = (result["summary"]["total_pages_processed"] / total_pages) * 100
            result["summary"]["coverage_percentage"] = round(coverage_pct, 1)
    
    logger.info(
        f"Final aggregation: {result['unique_rigs_count']} RIGs, "
        f"{len(result['events'])} events across {len(chunk_results)} chunks"
    )
    
    return result


def deduplicate_rigs(rigs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate RIGs using multiple matching strategies.
    
    Handles:
    - Exact ID match
    - Similar names (e.g., QTIF-790 vs QTIF790)
    - Variations in formatting
    """
    seen: Set[str] = set()
    unique_rigs = []
    
    for rig in rigs:
        rig_id = rig.get('rig_id', '').upper()
        
        # Normalize ID (remove dashes, spaces)
        normalized = re.sub(r'[-\s]', '', rig_id)
        
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique_rigs.append(rig)
    
    logger.info(f"Deduplicated {len(rigs)} RIGs to {len(unique_rigs)} unique")
    return unique_rigs


import re  # Import at module level
