"""
Hybrid search combining semantic (FAISS) and keyword (BM25) search
"""
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from services.vector_store.faiss_index import FaissIndex
from services.vector_store.bm25 import BM25Wrapper
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)


class HybridSearch:
    """Hybrid search combining semantic and keyword search"""
    
    def __init__(
        self,
        texts: List[str],
        embeddings: Optional[np.ndarray] = None,
        semantic_weight: float = None,
        bm25_weight: float = None
    ):
        """
        Initialize hybrid search
        
        Args:
            texts: List of texts to search
            embeddings: Optional pre-computed embeddings
            semantic_weight: Weight for semantic search (default 0.7)
            bm25_weight: Weight for BM25 search (default 0.3)
        """
        self.texts = texts
        self.semantic_weight = semantic_weight or settings.SEMANTIC_WEIGHT
        self.bm25_weight = bm25_weight or settings.BM25_WEIGHT
        
        # Normalize weights
        total_weight = self.semantic_weight + self.bm25_weight
        if total_weight > 0:
            self.semantic_weight /= total_weight
            self.bm25_weight /= total_weight
        
        # Initialize BM25
        self.bm25 = BM25Wrapper(texts)
        
        # Initialize FAISS if embeddings provided
        self.faiss_index = None
        if embeddings is not None and len(embeddings) > 0:
            self.faiss_index = FaissIndex(dim=len(embeddings[0]))
            self.faiss_index.add(embeddings, chunk_ids=[f"chunk_{i}" for i in range(len(texts))])
            logger.info("Initialized hybrid search with semantic and keyword search")
        else:
            logger.info("Initialized hybrid search with keyword search only")
    
    def query(
        self,
        query: str,
        query_embedding: Optional[np.ndarray] = None,
        topk: int = 10,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search
        
        Args:
            query: Search query text
            query_embedding: Optional pre-computed query embedding
            topk: Number of results
            min_score: Minimum score threshold
            
        Returns:
            List of result dictionaries with index, text, scores, and combined_score
        """
        results = {}
        
        # BM25 search
        bm25_results = self.bm25.query(query, topk=topk * 2)
        max_bm25_score = max([score for _, score in bm25_results], default=1.0)
        
        for idx, score in bm25_results:
            if idx not in results:
                results[idx] = {
                    "index": idx,
                    "text": self.texts[idx],
                    "bm25_score": score / max_bm25_score if max_bm25_score > 0 else 0.0,
                    "semantic_score": 0.0,
                    "combined_score": 0.0
                }
        
        # Semantic search
        if self.faiss_index and query_embedding is not None:
            semantic_indices, semantic_scores = self.faiss_index.query(query_embedding, topk=topk * 2)
            max_semantic_score = max(semantic_scores, default=1.0)
            
            for idx, score in zip(semantic_indices, semantic_scores):
                # Get original text index from FAISS index
                chunk_id = self.faiss_index.get_chunk_id(idx)
                if chunk_id:
                    try:
                        text_idx = int(chunk_id.replace("chunk_", ""))
                        if text_idx < len(self.texts):
                            if text_idx not in results:
                                results[text_idx] = {
                                    "index": text_idx,
                                    "text": self.texts[text_idx],
                                    "bm25_score": 0.0,
                                    "semantic_score": score / max_semantic_score if max_semantic_score > 0 else 0.0,
                                    "combined_score": 0.0
                                }
                            else:
                                results[text_idx]["semantic_score"] = score / max_semantic_score if max_semantic_score > 0 else 0.0
                    except ValueError:
                        pass
        
        # Calculate combined scores
        for idx in results:
            result = results[idx]
            combined = (
                result["bm25_score"] * self.bm25_weight +
                result["semantic_score"] * self.semantic_weight
            )
            result["combined_score"] = combined
        
        # Sort by combined score and filter
        sorted_results = sorted(
            [r for r in results.values() if r["combined_score"] >= min_score],
            key=lambda x: x["combined_score"],
            reverse=True
        )[:topk]
        
        logger.info(f"Hybrid search returned {len(sorted_results)} results")
        return sorted_results
    
    def add_documents(self, texts: List[str], embeddings: Optional[np.ndarray] = None):
        """
        Add new documents to search index
        
        Args:
            texts: New texts to add
            embeddings: Optional embeddings for new texts
        """
        start_idx = len(self.texts)
        self.texts.extend(texts)
        
        # Update BM25
        self.bm25 = BM25Wrapper(self.texts)
        
        # Update FAISS if embeddings provided
        if embeddings is not None and self.faiss_index:
            chunk_ids = [f"chunk_{start_idx + i}" for i in range(len(texts))]
            self.faiss_index.add(embeddings, chunk_ids=chunk_ids)
        
        logger.info(f"Added {len(texts)} documents to search index")


class ReRanker:
    """Re-ranker for search results using cross-encoder"""
    
    def __init__(self):
        """Initialize re-ranker"""
        # For v2, we'll use a simple scoring approach
        # In production, consider using a cross-encoder model
        self.use_cross_encoder = False
    
    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        topk: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Re-rank search results
        
        Args:
            query: Search query
            results: Initial search results
            topk: Number of results to return
            
        Returns:
            Re-ranked results
        """
        # Simple re-ranking: boost results with query terms
        query_terms = set(query.lower().split())
        
        for result in results:
            text = result.get("text", "").lower()
            text_terms = set(text.split())
            
            # Calculate term overlap
            overlap = len(query_terms & text_terms)
            overlap_ratio = overlap / len(query_terms) if query_terms else 0
            
            # Boost score
            boost = 1.0 + (overlap_ratio * 0.2)  # Up to 20% boost
            result["reranked_score"] = result.get("combined_score", 0.0) * boost
        
        # Re-sort by reranked score
        reranked = sorted(
            results,
            key=lambda x: x.get("reranked_score", 0.0),
            reverse=True
        )[:topk]
        
        return reranked

