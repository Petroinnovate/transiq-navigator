"""
Pydantic schemas for configuration validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class LLMConfig(BaseModel):
    """LLM provider configuration"""
    provider: str = Field(default="gemini", description="LLM provider name")
    model: Optional[str] = Field(default=None, description="Model name")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)


class ChunkingConfig(BaseModel):
    """Chunking configuration"""
    max_chars: int = Field(default=8000, ge=100, le=50000)
    overlap: int = Field(default=400, ge=0, le=2000)
    strategy: str = Field(default="adaptive", description="Chunking strategy")


class SearchConfig(BaseModel):
    """Search configuration"""
    top_k: int = Field(default=10, ge=1, le=100)
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    bm25_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ProcessingRequest(BaseModel):
    """Document processing request"""
    provider: Optional[str] = Field(default=None, description="LLM provider override")
    enable_deduction: bool = Field(default=True, description="Enable deduction engine")
    enable_patterns: bool = Field(default=True, description="Enable pattern recognition")
    chunk_config: Optional[ChunkingConfig] = None


class SearchRequest(BaseModel):
    """Search request"""
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=10, ge=1, le=100)
    use_hybrid: bool = Field(default=True, description="Use hybrid search")
    filters: Optional[Dict[str, Any]] = None

