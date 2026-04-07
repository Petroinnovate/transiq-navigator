"""
Deduction Engine - LLM-powered fact extraction and knowledge graph builder
"""
import json
import re
from typing import List, Dict, Any, Optional
from services.llm.factory import LLMFactory
from core.config.settings import settings
from core.logging.logger import get_logger
from core.errors import ProcessingError

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Chunking helpers for large DDR inputs (50K+ chars)
# ---------------------------------------------------------------------------
_CHUNK_SIZE = 12_000          # chars per LLM call
_CHUNK_OVERLAP = 500          # overlap to avoid cutting mid-sentence
_MAX_CHUNKS = 8               # safety cap on LLM calls per document


def _split_text_into_chunks(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks, breaking at sentence boundaries."""
    if len(text) <= chunk_size:
        return [text]
    chunks: List[str] = []
    start = 0
    while start < len(text) and len(chunks) < _MAX_CHUNKS:
        end = start + chunk_size
        if end < len(text):
            # Try to break at a sentence boundary
            boundary = text.rfind('. ', start + chunk_size - overlap, end)
            if boundary > start:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        start = end - overlap if end < len(text) else end
    return chunks


def _merge_facts(all_facts: List[Dict[str, Any]], max_facts: int) -> List[Dict[str, Any]]:
    """Merge facts from multiple chunks, dedup by (subject, predicate, object)."""
    seen: set = set()
    merged: List[Dict[str, Any]] = []
    for fact in all_facts:
        key = (
            fact.get("subject", "").lower().strip(),
            fact.get("predicate", "").lower().strip(),
            fact.get("object", "").lower().strip(),
        )
        if key not in seen:
            seen.add(key)
            merged.append(fact)
        if len(merged) >= max_facts:
            break
    # Sort by confidence descending
    merged.sort(key=lambda f: f.get("confidence", 0), reverse=True)
    return merged[:max_facts]


class DeductionEngine:
    """
    Deduction Engine for extracting facts and building knowledge graphs
    """
    
    def __init__(self, provider_name: Optional[str] = None):
        """
        Initialize deduction engine
        
        Args:
            provider_name: LLM provider name (defaults to configured provider)
        """
        self.llm = LLMFactory.get_provider(provider_name)
        logger.info(f"Initialized DeductionEngine with provider: {self.llm.get_model_info()['provider']}")
    
    def extract_facts(self, text: str, max_facts: int = 50) -> List[Dict[str, Any]]:
        """
        Extract atomic facts from text.  For large inputs (>12K chars),
        text is split into overlapping chunks and facts are merged with dedup.
        
        Args:
            text: Input text (supports 50K+ chars via chunking)
            max_facts: Maximum number of facts to extract
            
        Returns:
            List of fact dictionaries with subject, predicate, object
        """
        try:
            chunks = _split_text_into_chunks(text)
            all_facts: List[Dict[str, Any]] = []

            for i, chunk in enumerate(chunks):
                per_chunk_limit = max(max_facts // len(chunks), 10)
                prompt = f"""Extract atomic facts from the following text (chunk {i+1}/{len(chunks)}).
Each fact should be a triple: (subject, predicate, object).

Return ONLY a valid JSON array of objects, each with:
- "subject": the entity or concept
- "predicate": the relationship or attribute
- "object": the value or target entity
- "confidence": float between 0 and 1

Text to analyze:
{chunk}

Return up to {per_chunk_limit} facts. Focus on concrete, factual statements."""

                response = self.llm.generate_json(prompt)

                # Handle different response formats
                if isinstance(response, list):
                    facts = response
                elif isinstance(response, dict) and "facts" in response:
                    facts = response["facts"]
                elif isinstance(response, dict):
                    facts = [response]
                else:
                    facts = []

                # Validate and clean facts
                for fact in facts:
                    if isinstance(fact, dict):
                        validated_fact = {
                            "subject": str(fact.get("subject", "")),
                            "predicate": str(fact.get("predicate", "")),
                            "object": str(fact.get("object", "")),
                            "confidence": float(fact.get("confidence", 0.5))
                        }
                        if validated_fact["subject"] and validated_fact["predicate"]:
                            all_facts.append(validated_fact)

            # Merge and dedup across chunks
            validated_facts = _merge_facts(all_facts, max_facts)
            logger.info(f"Extracted {len(validated_facts)} facts from {len(chunks)} chunk(s)")
            return validated_facts
            
        except Exception as e:
            logger.error(f"Fact extraction error: {e}")
            # Fallback: simple heuristic extraction
            return self._fallback_extract_facts(text)
    
    def _fallback_extract_facts(self, text: str) -> List[Dict[str, Any]]:
        """Fallback fact extraction using simple heuristics"""
        facts = []
        sentences = re.split(r'[.!?]\s+', text)
        
        for sentence in sentences[:20]:  # Limit to 20 sentences
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # Simple pattern matching
            # Look for "X is Y" patterns
            is_match = re.search(r'(\w+(?:\s+\w+)*)\s+is\s+(\w+(?:\s+\w+)*)', sentence, re.IGNORECASE)
            if is_match:
                facts.append({
                    "subject": is_match.group(1),
                    "predicate": "is",
                    "object": is_match.group(2),
                    "confidence": 0.3
                })
        
        return facts
    
    def build_knowledge_graph(self, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build knowledge graph from extracted facts
        
        Args:
            facts: List of fact dictionaries
            
        Returns:
            Knowledge graph structure with nodes and edges
        """
        nodes = {}
        edges = []
        
        for fact in facts:
            subject = fact.get("subject", "").strip()
            predicate = fact.get("predicate", "").strip()
            obj = fact.get("object", "").strip()
            confidence = fact.get("confidence", 0.5)
            
            if not subject or not predicate:
                continue
            
            # Add nodes
            if subject not in nodes:
                nodes[subject] = {
                    "id": subject,
                    "label": subject,
                    "type": "entity",
                    "count": 0
                }
            nodes[subject]["count"] += 1
            
            if obj and obj not in nodes:
                nodes[obj] = {
                    "id": obj,
                    "label": obj,
                    "type": "entity",
                    "count": 0
                }
            if obj:
                nodes[obj]["count"] += 1
            
            # Add edge
            edge = {
                "source": subject,
                "target": obj if obj else "unknown",
                "predicate": predicate,
                "confidence": confidence,
                "type": "fact"
            }
            edges.append(edge)
        
        # Calculate node importance (degree centrality)
        for node_id in nodes:
            degree = sum(1 for e in edges if e["source"] == node_id or e["target"] == node_id)
            nodes[node_id]["degree"] = degree
        
        graph = {
            "nodes": list(nodes.values()),
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "avg_confidence": sum(e["confidence"] for e in edges) / len(edges) if edges else 0
            }
        }
        
        logger.info(f"Built knowledge graph with {len(nodes)} nodes and {len(edges)} edges")
        return graph
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities from text
        
        Args:
            text: Input text
            
        Returns:
            List of entity dictionaries
        """
        try:
            prompt = f"""Extract named entities (people, organizations, locations, dates, etc.) from the text.

Return ONLY a valid JSON array of objects, each with:
- "text": the entity text
- "type": entity type (PERSON, ORGANIZATION, LOCATION, DATE, etc.)
- "start": character position (approximate)
- "confidence": float between 0 and 1

Text:
{text[:12000]}

Return entities as JSON array."""

            response = self.llm.generate_json(prompt)
            
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and "entities" in response:
                return response["entities"]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return []
    
    def infer_relationships(self, entities: List[Dict[str, Any]], context: str) -> List[Dict[str, Any]]:
        """
        Infer relationships between entities
        
        Args:
            entities: List of extracted entities
            context: Original text context
            
        Returns:
            List of relationship dictionaries
        """
        try:
            entity_list = ", ".join([e.get("text", "") for e in entities[:10]])
            
            prompt = f"""Given these entities: {entity_list}

And this context: {context[:2000]}

Infer relationships between these entities. Return a JSON array of objects with:
- "source": source entity
- "target": target entity  
- "relationship": type of relationship
- "confidence": float between 0 and 1

Return relationships as JSON array."""

            response = self.llm.generate_json(prompt)
            
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and "relationships" in response:
                return response["relationships"]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Relationship inference error: {e}")
            return []
    
    # ========================================================================
    # GraphRAG Integration
    # ========================================================================
    
    def publish_facts_to_graph(self, facts: List[Dict[str, Any]], doc_id: str,
                              user_id: Optional[str] = None) -> Optional[str]:
        """
        Publish extracted facts to GraphRAG for knowledge graph building
        
        This is the integration point between deduction engine and GraphRAG.
        Triggers asynchronous graph building in background.
        
        Args:
            facts: List of extracted facts
            doc_id: Document ID for tracking
            user_id: User ID for multi-tenancy
            
        Returns:
            Task ID (if async) or None (if sync)
        """
        try:
            from pipelines.workers.graph_processing import enqueue_graph_building
            
            task_id = enqueue_graph_building(doc_id, facts, user_id)
            
            if task_id:
                logger.info(f"Enqueued GraphRAG task {task_id} for doc {doc_id}")
            else:
                logger.info(f"Started synchronous GraphRAG processing for doc {doc_id}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to publish facts to GraphRAG: {e}")
            logger.warning("Proceeding without GraphRAG knowledge graph")
            return None
    
    def integrate_with_graphrag(self, facts: List[Dict[str, Any]], doc_id: str,
                               user_id: Optional[str] = None, async_mode: bool = True) -> Dict[str, Any]:
        """
        Full integration with GraphRAG (blocking or async)
        
        Args:
            facts: List of extracted facts
            doc_id: Document ID
            user_id: User ID
            async_mode: If True, queue task; if False, process synchronously
            
        Returns:
            Integration result dict
        """
        logger.info(f"Integrating GraphRAG for doc {doc_id} (async_mode={async_mode})")
        
        if async_mode:
            # Queue async task
            task_id = self.publish_facts_to_graph(facts, doc_id, user_id)
            return {
                "status": "queued",
                "task_id": task_id,
                "doc_id": doc_id
            }
        else:
            # Synchronous processing
            try:
                from pipelines.workers.graph_processing import build_knowledge_graph_sync
                result = build_knowledge_graph_sync(doc_id, facts, user_id)
                return {
                    "status": "complete",
                    "result": result,
                    "doc_id": doc_id
                }
            except Exception as e:
                logger.error(f"Synchronous GraphRAG integration failed: {e}")
                return {
                    "status": "failed",
                    "error": str(e),
                    "doc_id": doc_id
                }


