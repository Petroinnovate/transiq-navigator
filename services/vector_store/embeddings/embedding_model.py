"""
Embedding model management — hardware-aware, dynamic batching, OOM-safe.
"""
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)


def _resolve_device() -> str:
    """Resolve device from settings; fallback to CPU."""
    override = getattr(settings, "EMBEDDING_DEVICE", "auto")
    if override and override.lower() not in ("auto", ""):
        return override.lower()
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def _resolve_batch_size(device: str) -> int:
    """Resolve batch size from settings or hardware defaults."""
    override = getattr(settings, "EMBEDDING_BATCH_SIZE", 0)
    if override and override > 0:
        return override
    return 256 if device == "cuda" else 128


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
            EmbeddingModel._device = _resolve_device()
            EmbeddingModel._batch_size = _resolve_batch_size(EmbeddingModel._device)
            logger.info(f"Loading embedding model: {model_name} (device={EmbeddingModel._device}, batch_size={EmbeddingModel._batch_size})")
            try:
                EmbeddingModel._model = SentenceTransformer(model_name, device=EmbeddingModel._device)
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
                normalize_embeddings=True,
                device=EmbeddingModel._device,
            )
            return embeddings
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise
    
    def embed_batch(self, texts: List[str], batch_size: int = 0, show_progress: bool = False) -> np.ndarray:
        """
        Generate embeddings in batches with OOM auto-fallback.
        
        Args:
            texts: List of texts
            batch_size: 0 = use hardware-optimal default
            show_progress: Show progress bar
            
        Returns:
            Numpy array of embeddings
        """
        effective_bs = batch_size if batch_size > 0 else EmbeddingModel._batch_size
        return self._encode_with_fallback(texts, effective_bs, show_progress)

    def _encode_with_fallback(
        self, texts: List[str], batch_size: int, show_progress: bool, min_batch: int = 16
    ) -> np.ndarray:
        """Encode with automatic batch-size halving on OOM."""
        try:
            return self._model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True,
                device=EmbeddingModel._device,
            )
        except RuntimeError as exc:
            if batch_size <= min_batch:
                raise
            new_bs = max(min_batch, batch_size // 2)
            logger.warning(f"OOM at batch_size={batch_size} — retrying with {new_bs}")
            return self._encode_with_fallback(texts, new_bs, show_progress, min_batch)
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.dimension
    
    def get_model_name(self) -> str:
        """Get model name"""
        return self.model_name

