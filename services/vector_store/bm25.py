"""
BM25 keyword search implementation
"""
from typing import List, Dict, Tuple
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

from core.logging.logger import get_logger

logger = get_logger(__name__)


class BM25Wrapper:
    """BM25 keyword search wrapper"""
    
    def __init__(self, docs: List[str]):
        """
        Initialize BM25 index
        
        Args:
            docs: List of documents to index
        """
        if not BM25_AVAILABLE:
            logger.warning("rank_bm25 not installed. Install with: pip install rank-bm25")
            self.bm25 = None
            return
        
        # Tokenize documents
        self.tokenized = [self._tokenize(doc) for doc in docs]
        self.bm25 = BM25Okapi(self.tokenized)
        self.original_docs = docs
        logger.info(f"Initialized BM25 index with {len(docs)} documents")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text (simple whitespace split)
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        # Simple tokenization - can be enhanced with proper NLP tokenizer
        return text.lower().split()
    
    def query(self, query: str, topk: int = 10) -> List[Tuple[int, float]]:
        """
        Query BM25 index
        
        Args:
            query: Search query
            topk: Number of results
            
        Returns:
            List of (index, score) tuples
        """
        if not self.bm25:
            logger.warning("BM25 not available")
            return []
        
        try:
            query_tokens = self._tokenize(query)
            scores = self.bm25.get_scores(query_tokens)
            
            # Get top-k results
            top_indices = sorted(
                range(len(scores)),
                key=lambda i: scores[i],
                reverse=True
            )[:topk]
            
            results = [(idx, float(scores[idx])) for idx in top_indices if scores[idx] > 0]
            return results
            
        except Exception as e:
            logger.error(f"BM25 query error: {e}")
            return []
    
    def get_doc(self, index: int) -> str:
        """Get document by index"""
        if 0 <= index < len(self.original_docs):
            return self.original_docs[index]
        return ""

