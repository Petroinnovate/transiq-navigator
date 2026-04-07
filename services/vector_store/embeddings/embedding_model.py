"""
Embedding model management
"""
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)


class EmbeddingModel:
    """Wrapper for sentence transformer models"""
    
    _instance = None
    _model = None
    
    def __new__(cls, model_name: str = None):
        """Singleton pattern to avoid loading model multiple times"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: str = None):
        """Initialize embedding model"""
        if EmbeddingModel._model is None:
            model_name = model_name or settings.EMBEDDING_MODEL
            logger.info(f"Loading embedding model: {model_name}")
            try:
                EmbeddingModel._model = SentenceTransformer(model_name)
                EmbeddingModel.model_name = model_name
                EmbeddingModel.dimension = EmbeddingModel._model.get_sentence_embedding_dimension()
                logger.info(f"Loaded model {model_name} with dimension {EmbeddingModel.dimension}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        # Always set instance attributes to class attributes
        self._model = EmbeddingModel._model
        self.model_name = EmbeddingModel.model_name
        self.dimension = EmbeddingModel.dimension
    
    def embed(self, texts: Union[str, List[str]], show_progress: bool = False) -> np.ndarray:
        """
        Generate embeddings for text(s)
        
        Args:
            texts: Single text string or list of texts
            show_progress: Show progress bar
            
        Returns:
            Numpy array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            embeddings = self._model.encode(
                texts,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return embeddings
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise
    
    def embed_batch(self, texts: List[str], batch_size: int = 32, show_progress: bool = False) -> np.ndarray:
        """
        Generate embeddings in batches
        
        Args:
            texts: List of texts
            batch_size: Batch size for processing
            show_progress: Show progress bar
            
        Returns:
            Numpy array of embeddings
        """
        return self.embed(texts, show_progress=show_progress)
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.dimension
    
    def get_model_name(self) -> str:
        """Get model name"""
        return self.model_name

