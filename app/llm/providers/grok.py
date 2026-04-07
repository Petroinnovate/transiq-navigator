"""
Grok (xAI) LLM Provider
Uses OpenAI-compatible API
"""
import json
import re
from typing import Dict, Any, Optional, List
from app.llm.providers.base import LLMProvider
from app.config.settings import settings
from app.utils.logger import get_logger
from app.utils.errors import LLMProviderError

logger = get_logger(__name__)

try:
    from openai import OpenAI
    GROK_AVAILABLE = True
except ImportError:
    GROK_AVAILABLE = False
    logger.warning("OpenAI package not installed. Grok provider unavailable.")


class GrokProvider(LLMProvider):
    """Grok (xAI) LLM Provider using OpenAI-compatible API"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "grok-3-mini-fast"):
        """
        Initialize Grok provider
        
        Args:
            api_key: Grok API key (from xAI)
            model: Model name (default: grok-3-mini-fast)
        """
        if not GROK_AVAILABLE:
            raise RuntimeError("OpenAI package required for Grok provider")
        
        self.api_key = api_key or settings.GROK_API_KEY
        if not self.api_key:
            raise ValueError("GROK_API_KEY not set")
        
        self.model = model
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )
        logger.info(f"Initialized Grok provider with model: {model}")
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Generate text using Grok
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            response_format: Response format (e.g., {"type": "json_object"})
            **kwargs: Additional model parameters
            
        Returns:
            Generated text
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            # Add response format if specified
            if response_format:
                request_params["response_format"] = response_format
            
            # Add any additional parameters
            request_params.update(kwargs)
            
            logger.debug(f"Calling Grok API with model: {self.model}")
            response = self.client.chat.completions.create(**request_params)
            
            result = response.choices[0].message.content
            logger.info(f"Generated {len(result)} characters from Grok")
            return result
            
        except Exception as e:
            logger.error(f"Grok API error: {e}")
            raise
    
    def generate_with_context(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        Generate with system prompt and optional conversation context
        
        Args:
            system_prompt: System instructions
            user_prompt: User message
            context: Previous conversation messages
            **kwargs: Additional parameters
            
        Returns:
            Generated text
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        if context:
            messages.extend(context)
        
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Grok API error: {e}")
            raise
    
    @property
    def name(self) -> str:
        """Provider name"""
        return "grok"
    
    @property
    def model_name(self) -> str:
        """Current model name"""
        return self.model
    
    async def agenerate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Async generate text using Grok
        Note: Grok OpenAI client doesn't have native async, using sync in executor
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional model parameters
            
        Returns:
            Generated text
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.generate(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
        )
    
    def generate_json(
        self,
        prompt: str,
        schema: Optional[Dict] = None,
        **kwargs
    ) -> Dict:
        """
        Generate structured JSON response using Grok
        
        Args:
            prompt: Input prompt
            schema: Optional JSON schema for structured output
            **kwargs: Additional generation parameters
            
        Returns:
            Parsed JSON dictionary
        """
        # Prepare JSON prompt
        if schema:
            json_prompt = f"{prompt}\n\nReturn the response as valid JSON matching this schema: {json.dumps(schema)}"
        else:
            json_prompt = f"{prompt}\n\nReturn the response as valid JSON."
        
        try:
            # Request JSON response format from Grok
            messages = [{"role": "user", "content": json_prompt}]
            
            request_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.2),
                "response_format": {"type": "json_object"}
            }
            
            # Add any additional parameters
            request_params.update({k: v for k, v in kwargs.items() 
                                 if k not in ["max_tokens", "temperature"]})
            
            logger.debug("Calling Grok API for JSON generation")
            response = self.client.chat.completions.create(**request_params)
            
            result_text = response.choices[0].message.content
            logger.info(f"Generated JSON response from Grok ({len(result_text)} chars)")
            
            # Parse JSON from response
            try:
                # Try parsing the entire response as JSON first
                return json.loads(result_text)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the text
                json_match = re.search(r'(\{.*\})', result_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                # Last resort: return error structure
                raise LLMProviderError(
                    f"Failed to parse JSON from Grok response",
                    provider="grok"
                )
                
        except Exception as e:
            logger.error(f"Grok JSON generation error: {e}")
            raise LLMProviderError(
                f"Grok JSON generation failed: {str(e)}",
                provider="grok"
            )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Grok model information"""
        return {
            "provider": "grok",
            "model": self.model,
            "supports_streaming": False,
            "supports_json": True
        }
