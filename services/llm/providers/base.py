"""
Base LLM provider interface
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize LLM provider
        
        Args:
            api_key: API key for the provider
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.config = kwargs
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text synchronously
        
        Args:
            prompt: Input prompt
            **kwargs: Generation parameters (temperature, max_tokens, etc.)
            
        Returns:
            Generated text
        """
        pass
    
    @abstractmethod
    async def agenerate(self, prompt: str, **kwargs) -> str:
        """
        Generate text asynchronously
        
        Args:
            prompt: Input prompt
            **kwargs: Generation parameters
            
        Returns:
            Generated text
        """
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict:
        """
        Generate structured JSON response
        
        Args:
            prompt: Input prompt
            schema: Optional JSON schema for structured output
            **kwargs: Generation parameters
            
        Returns:
            Parsed JSON dictionary
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the provider and model
        
        Returns:
            Dictionary with provider information
        """
        return {
            "provider": self.__class__.__name__,
            "supports_streaming": False,
            "supports_json": False
        }

