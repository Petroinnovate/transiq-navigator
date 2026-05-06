"""
Application settings and configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # LLM Provider API Keys
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_API_KEY_2: Optional[str] = None
    GEMINI_API_KEY_3: Optional[str] = None
    GEMINI_API_KEY_4: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GROK_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LING_API_KEY: Optional[str] = None
    LING_MODEL: str = "inclusionai/ling-2.6-1t:free"
    DEFAULT_LLM_PROVIDER: Optional[str] = None  # Force specific provider (openai, gemini, grok, ling, etc.)
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Supabase Configuration (Optional)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    ENABLE_SUPABASE: bool = False
    
    # Storage Configuration
    FAISS_INDEX_PATH: str = "./storage/faiss_index.bin"
    DATABASE_URL: str = "sqlite:///./storage/local_storage.db"
    UPLOAD_DIR: str = "./storage/uploads"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Security Configuration
    API_KEY: Optional[str] = None  # Primary API key for authentication
    API_KEY_2: Optional[str] = None  # Backup API key
    API_KEY_3: Optional[str] = None  # Additional API key
    JWT_SECRET: Optional[str] = None  # Dedicated JWT signing secret (MUST differ from API_KEY)
    FRONTEND_URL: str = "http://localhost:5173"  # CORS allowed origin (production: https://yourdomain.com)
    RATE_LIMIT_PER_MINUTE: int = 60  # Requests per minute per API key
    
    # Feature Flags
    ENABLE_WEBSOCKET: bool = True
    ENABLE_DEDUCTION_ENGINE: bool = True
    ENABLE_PATTERN_RECOGNITION: bool = True
    ENABLE_HYBRID_SEARCH: bool = True
    
    # Demo Data Configuration (IMPORTANT: Set to False in production!)
    ALLOW_DEMO_DATA_FALLBACK: bool = True  # Development: allow fallback to demo_result.json
    # In production, set ALLOW_DEMO_DATA_FALLBACK=false in .env to prevent fake data
    REQUIRE_REAL_DATA: bool = False  # Strict mode: reject requests without real data
    
    # Chunking Configuration
    DEFAULT_CHUNK_SIZE: int = 8000
    DEFAULT_CHUNK_OVERLAP: int = 400
    
    # Pipeline Optimization
    PIPELINE_MAX_CONCURRENT_LLM: int = 8       # Max parallel LLM calls in deduction
    PIPELINE_LLM_TIMEOUT: int = 30             # Seconds per LLM call
    PIPELINE_ENABLE_CONTENT_CACHE: bool = True  # Cache results by content hash
    PIPELINE_DASHBOARD_MAX_CONTEXT: int = 20    # Max chunks sent to dashboard LLM
    
    # Worker Concurrency
    WORKER_CONCURRENCY: int = 4                 # Celery worker processes (match CPU cores)
    WORKER_PREFETCH_MULTIPLIER: int = 1         # 1 = fair scheduling, prevents task hogging
    WORKER_MAX_TASKS_PER_CHILD: int = 100       # Recycle workers to prevent memory leaks
    WORKER_POOL: str = "prefork"                # prefork (safe with asyncio.run) or gevent
    WORKER_MAX_MEMORY_PER_CHILD: int = 512000   # 512MB per worker child (KB)
    
    # Embedding Configuration
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 0          # 0 = auto-detect (128 CPU / 256 GPU)
    EMBEDDING_DEVICE: str = "auto"          # auto | cpu | cuda
    
    # Search Configuration
    DEFAULT_SEARCH_TOP_K: int = 10
    SEMANTIC_WEIGHT: float = 0.7
    BM25_WEIGHT: float = 0.3
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env file

    def get_gemini_api_keys(self) -> list[str]:
        """Return configured Gemini API keys in priority order."""
        keys = [
            self.GEMINI_API_KEY,
            self.GEMINI_API_KEY_2,
            self.GEMINI_API_KEY_3,
            self.GEMINI_API_KEY_4,
        ]
        return [key.strip() for key in keys if key and key.strip()]

    def require_gemini_api_key(self) -> str:
        """Return the primary Gemini API key or raise a clear error."""
        keys = self.get_gemini_api_keys()
        if not keys:
            raise ValueError("GEMINI_API_KEY is not configured. Set it in .env or the environment.")
        return keys[0]


# Global settings instance
settings = Settings()

