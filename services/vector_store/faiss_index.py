"""
Semantic search using FAISS
"""
import os
import pickle
import numpy as np
import faiss
from typing import List, Tuple, Optional
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)


class FaissIndex:
    """FAISS vector index for semantic search"""
    
    def __init__(self, dim: int = None, path: str = None):
        """
        Initialize FAISS index
        
        Args:
            dim: Embedding dimension
            path: Path to index file
        """
        self.dim = dim or settings.EMBEDDING_DIMENSION
        self.path = path or settings.FAISS_INDEX_PATH
        self.index = None
        self.id_map = []  # Maps FAISS indices to chunk IDs
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.path) if os.path.dirname(self.path) else '.', exist_ok=True)
        
        self._load()
    
    def _load(self):
        """Load existing index or create new one"""
        index_file = self.path
        map_file = self.path + ".map"
        
        if os.path.exists(index_file) and os.path.exists(map_file):
            try:
                self.index = faiss.read_index(index_file)
                with open(map_file, 'rb') as f:
                    self.id_map = pickle.load(f)
                logger.info(f"Loaded FAISS index with {len(self.id_map)} vectors")
            except Exception as e:
                logger.warning(f"Failed to load index: {e}. Creating new one.")
                self._create_new()
        else:
            self._create_new()
    
    def _create_new(self):
        """Create new FAISS index"""
        # Use Inner Product for cosine similarity (after normalization)
        self.index = faiss.IndexFlatIP(self.dim)
        self.id_map = []
        logger.info(f"Created new FAISS index with dimension {self.dim}")
    
    def _save(self):
        """Save index to disk"""
        try:
            faiss.write_index(self.index, self.path)
            with open(self.path + ".map", 'wb') as f:
                pickle.dump(self.id_map, f)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def add(self, vectors: np.ndarray, chunk_ids: List[str] = None):
        """
        Add vectors to index
        
        Args:
            vectors: Numpy array of embeddings
            chunk_ids: List of chunk IDs (optional)
        """
        if len(vectors) == 0:
            return
        
        # Ensure vectors are float32 and normalized
        vectors = np.array(vectors, dtype=np.float32)
        faiss.normalize_L2(vectors)
        
        # Add to index
        self.index.add(vectors)
        
        # Update ID map
        if chunk_ids:
            self.id_map.extend(chunk_ids)
        else:
            # Generate IDs if not provided
            start_idx = len(self.id_map)
            self.id_map.extend([f"chunk_{start_idx + i}" for i in range(len(vectors))])
        
        # Save index
        self._save()
        logger.info(f"Added {len(vectors)} vectors to index. Total: {len(self.id_map)}")
    
    def query(self, vector: np.ndarray, topk: int = 10) -> Tuple[List[int], List[float]]:
        """
        Query index for similar vectors
        
        Args:
            vector: Query vector
            topk: Number of results to return
            
        Returns:
            Tuple of (indices, scores)
        """
        if self.index.ntotal == 0:
            return [], []
        
        # Ensure vector is float32 and normalized
        vector = np.array([vector], dtype=np.float32)
        faiss.normalize_L2(vector)
        
        # Search
        scores, indices = self.index.search(vector, min(topk, self.index.ntotal))
        
        # Convert to lists
        result_indices = indices[0].tolist()
        result_scores = scores[0].tolist()
        
        # Filter out invalid indices (-1)
        valid_results = [(idx, score) for idx, score in zip(result_indices, result_scores) if idx >= 0]
        
        if valid_results:
            indices_list, scores_list = zip(*valid_results)
            return list(indices_list), list(scores_list)
        
        return [], []
    
    def get_chunk_id(self, index: int) -> Optional[str]:
        """Get chunk ID from FAISS index"""
        if 0 <= index < len(self.id_map):
            return self.id_map[index]
        return None
    
    def remove_chunks(self, chunk_ids: List[str]):
        """
        Remove chunks from index (rebuilds index)
        
        Args:
            chunk_ids: List of chunk IDs to remove
        """
        # FAISS doesn't support removal, so we need to rebuild
        # This is expensive, so use sparingly
        logger.warning("FAISS doesn't support removal. Index rebuild required.")
        # For now, just log - full rebuild would require storing all vectors
        # In production, consider using a different index type or maintaining a separate mapping

