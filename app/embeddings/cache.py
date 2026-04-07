"""
Embedding cache using Redis (optional) or in-memory
"""
import hashlib
import json
from typing import List, Optional
import numpy as np
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class EmbeddingCache:
    """Cache for embeddings to avoid recomputation"""
    
    def __init__(self, use_redis: bool = None):
        """
        Initialize embedding cache
        
        Args:
            use_redis: Use Redis cache (defaults to checking REDIS_URL)
        """
        self.use_redis = use_redis if use_redis is not None else bool(settings.REDIS_URL and REDIS_AVAILABLE)
        self.memory_cache = {}  # Fallback in-memory cache
        
        if self.use_redis and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=False)
                logger.info("Using Redis for embedding cache")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using in-memory cache.")
                self.use_redis = False
        else:
            self.use_redis = False
            logger.info("Using in-memory embedding cache")
    
    def _get_key(self, text: str) -> str:
        """Generate cache key from text"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def get(self, text: str) -> Optional[np.ndarray]:
        """
        Get cached embedding
        
        Args:
            text: Input text
            
        Returns:
            Cached embedding or None
        """
        key = self._get_key(text)
        
        if self.use_redis:
            try:
                cached = self.redis_client.get(f"embedding:{key}")
                if cached:
                    return np.frombuffer(cached, dtype=np.float32)
            except Exception as e:
                logger.warning(f"Redis cache get error: {e}")
        
        # Check memory cache
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        return None
    
    def set(self, text: str, embedding: np.ndarray, ttl: int = 86400):
        """
        Cache embedding
        
        Args:
            text: Input text
            embedding: Embedding vector
            ttl: Time to live in seconds (default 24 hours)
        """
        key = self._get_key(text)
        
        if self.use_redis:
            try:
                self.redis_client.setex(
                    f"embedding:{key}",
                    ttl,
                    embedding.tobytes()
                )
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
        
        # Also store in memory cache (limited size)
        if len(self.memory_cache) < 1000:  # Limit memory cache size
            self.memory_cache[key] = embedding
    
    def get_batch(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """Get cached embeddings for multiple texts"""
        return [self.get(text) for text in texts]
    
    def clear(self):
        """Clear cache"""
        if self.use_redis:
            try:
                # Clear only embedding keys
                keys = self.redis_client.keys("embedding:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis cache clear error: {e}")
        
        self.memory_cache.clear()
        logger.info("Embedding cache cleared")

