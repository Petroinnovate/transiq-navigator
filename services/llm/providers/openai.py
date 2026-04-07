"""
OpenAI LLM Provider
"""
import os
import json
from typing import Optional, Dict, Any
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from app.llm.providers.base import LLMProvider
from core.errors import LLMProviderError
from core.logging.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", **kwargs):
        """
        Initialize OpenAI provider
        
        Args:
            api_key: OpenAI API key (defaults to env var)
            model: Model name to use
            **kwargs: Additional configuration
        """
        if not OPENAI_AVAILABLE:
            raise LLMProviderError("openai package not installed. Install with: pip install openai", provider="openai")
        
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMProviderError("OPENAI_API_KEY not provided", provider="openai")
        
        super().__init__(api_key, **kwargs)
        self.model_name = model
        self.client = OpenAI(api_key=api_key)
        logger.info(f"Initialized OpenAI provider with model: {model}")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text synchronously"""
        try:
            temperature = kwargs.get("temperature", 0.2)
            max_tokens = kwargs.get("max_tokens")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                raise LLMProviderError("Empty response from OpenAI", provider="openai")
                
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise LLMProviderError(f"OpenAI generation failed: {str(e)}", provider="openai")
    
    async def agenerate(self, prompt: str, **kwargs) -> str:
        """Generate text asynchronously"""
        try:
            temperature = kwargs.get("temperature", 0.2)
            max_tokens = kwargs.get("max_tokens")
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                raise LLMProviderError("Empty response from OpenAI", provider="openai")
                
        except Exception as e:
            logger.error(f"OpenAI async generation error: {e}")
            raise LLMProviderError(f"OpenAI async generation failed: {str(e)}", provider="openai")
    
    def generate_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict:
        """Generate structured JSON response"""
        try:
            temperature = kwargs.get("temperature", 0.2)
            max_tokens = kwargs.get("max_tokens")
            
            # OpenAI supports structured outputs via response_format
            response_format = {"type": "json_object"} if schema else None
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that returns JSON responses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                return json.loads(content)
            else:
                raise LLMProviderError("Empty JSON response from OpenAI", provider="openai")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            raise LLMProviderError(f"Failed to parse JSON response: {str(e)}", provider="openai")
        except Exception as e:
            logger.error(f"OpenAI JSON generation error: {e}")
            raise LLMProviderError(f"OpenAI JSON generation failed: {str(e)}", provider="openai")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information"""
        return {
            "provider": "openai",
            "model": self.model_name,
            "supports_streaming": True,
            "supports_json": True
        }

