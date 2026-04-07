"""
LLM Provider Factory — with multi-provider fallback and retry logic
"""
import time
from typing import Any, Dict, List, Optional

from services.llm.providers.base import LLMProvider
from services.llm.providers.gemini import GeminiProvider
from services.llm.providers.openai import OpenAIProvider
from services.llm.providers.grok import GrokProvider
from services.llm.providers.anthropic import AnthropicProvider
from core.config.settings import settings
from core.errors import LLMProviderError
from core.logging.logger import get_logger

logger = get_logger(__name__)


class LLMFactory:
    """Factory for creating LLM provider instances"""
    
    _providers = {
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "grok": GrokProvider,
        "anthropic": AnthropicProvider,
    }
    
    @classmethod
    def get_provider(cls, name: Optional[str] = None, **kwargs) -> LLMProvider:
        """
        Get an LLM provider instance
        
        Args:
            name: Provider name (gemini, openai). Defaults to gemini if available
            **kwargs: Provider-specific configuration
            
        Returns:
            LLMProvider instance
            
        Raises:
            LLMProviderError: If provider is not available or misconfigured
        """
        # Use DEFAULT_LLM_PROVIDER if set, otherwise auto-detect
        if not name:
            if settings.DEFAULT_LLM_PROVIDER:
                name = settings.DEFAULT_LLM_PROVIDER.lower()
            elif settings.GROK_API_KEY:
                name = "grok"
            elif settings.OPENAI_API_KEY:
                name = "openai"
            elif settings.ANTHROPIC_API_KEY:
                name = "anthropic"
            elif settings.GEMINI_API_KEY:
                name = "gemini"
            else:
                raise LLMProviderError(
                    "No LLM provider configured. Set GROK_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY",
                    provider="none"
                )
        
        name = name.lower()
        
        if name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise LLMProviderError(
                f"Unknown provider: {name}. Available: {available}",
                provider=name
            )
        
        provider_class = cls._providers[name]
        
        try:
            # Check if provider is available and pass key explicitly from settings
            if name == "gemini":
                if not settings.GEMINI_API_KEY:
                    raise LLMProviderError("GEMINI_API_KEY not set", provider=name)
                kwargs.setdefault("api_key", settings.GEMINI_API_KEY)
            elif name == "openai":
                if not settings.OPENAI_API_KEY:
                    raise LLMProviderError("OPENAI_API_KEY not set", provider=name)
                kwargs.setdefault("api_key", settings.OPENAI_API_KEY)
            elif name == "grok":
                if not settings.GROK_API_KEY:
                    raise LLMProviderError("GROK_API_KEY not set", provider=name)
                kwargs.setdefault("api_key", settings.GROK_API_KEY)
            elif name == "anthropic":
                if not settings.ANTHROPIC_API_KEY:
                    raise LLMProviderError("ANTHROPIC_API_KEY not set", provider=name)
                kwargs.setdefault("api_key", settings.ANTHROPIC_API_KEY)
            
            provider = provider_class(**kwargs)
            logger.info(f"Created {name} provider instance")
            return provider
            
        except Exception as e:
            logger.error(f"Failed to create {name} provider: {e}")
            raise LLMProviderError(
                f"Failed to initialize {name} provider: {str(e)}",
                provider=name
            )
    
    @classmethod
    def list_available_providers(cls) -> list[str]:
        """List available provider names"""
        return list(cls._providers.keys())
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type[LLMProvider]):
        """
        Register a custom provider
        
        Args:
            name: Provider name
            provider_class: Provider class (must inherit from LLMProvider)
        """
        if not issubclass(provider_class, LLMProvider):
            raise ValueError(f"Provider class must inherit from LLMProvider")
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered custom provider: {name}")

    # ------------------------------------------------------------------
    # Provider priority chain (configurable)
    # ------------------------------------------------------------------

    DEFAULT_PRIORITY: List[str] = ["gemini", "openai", "grok", "anthropic"]

    @classmethod
    def _available_chain(cls, priority: Optional[List[str]] = None) -> List[str]:
        """Return ordered list of providers that have API keys configured."""
        order = priority or cls.DEFAULT_PRIORITY
        key_map = {
            "gemini": settings.GEMINI_API_KEY,
            "openai": settings.OPENAI_API_KEY,
            "grok": settings.GROK_API_KEY,
            "anthropic": settings.ANTHROPIC_API_KEY,
        }
        return [p for p in order if key_map.get(p)]

    # ------------------------------------------------------------------
    # Fallback-aware generation
    # ------------------------------------------------------------------

    @classmethod
    def generate_with_fallback(
        cls,
        prompt: str,
        *,
        priority: Optional[List[str]] = None,
        max_retries: int = 2,
        backoff_base: float = 1.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate text with automatic multi-provider fallback.

        Tries each provider in priority order. On failure retries with
        exponential backoff before moving to the next provider.

        Returns:
            {
                "provider_used": str,
                "fallback_used": bool,
                "response": str,
                "error": str | None,
                "attempts": int,
            }
        """
        chain = cls._available_chain(priority)
        if not chain:
            raise LLMProviderError("No LLM providers configured", provider="none")

        attempts = 0
        last_error = ""

        for idx, provider_name in enumerate(chain):
            for retry in range(max_retries):
                attempts += 1
                try:
                    provider = cls.get_provider(provider_name)
                    response = provider.generate(prompt, **kwargs)
                    if response and response.strip():
                        return {
                            "provider_used": provider_name,
                            "fallback_used": idx > 0,
                            "response": response,
                            "error": None,
                            "attempts": attempts,
                        }
                    last_error = f"{provider_name}: empty response"
                    logger.warning(f"Empty response from {provider_name} (attempt {retry + 1})")
                except Exception as e:
                    last_error = f"{provider_name}: {str(e)}"
                    logger.warning(
                        f"Provider {provider_name} failed (attempt {retry + 1}/{max_retries}): {e}"
                    )

                # Exponential backoff before retry
                if retry < max_retries - 1:
                    delay = backoff_base * (2 ** retry)
                    time.sleep(delay)

            logger.info(f"Provider {provider_name} exhausted — trying next fallback")

        # All providers failed
        return {
            "provider_used": None,
            "fallback_used": True,
            "response": "",
            "error": last_error,
            "attempts": attempts,
        }

    @classmethod
    def generate_json_with_fallback(
        cls,
        prompt: str,
        *,
        schema: Optional[Dict] = None,
        priority: Optional[List[str]] = None,
        max_retries: int = 2,
        backoff_base: float = 1.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """Same as generate_with_fallback but for structured JSON output."""
        chain = cls._available_chain(priority)
        if not chain:
            raise LLMProviderError("No LLM providers configured", provider="none")

        attempts = 0
        last_error = ""

        for idx, provider_name in enumerate(chain):
            for retry in range(max_retries):
                attempts += 1
                try:
                    provider = cls.get_provider(provider_name)
                    response = provider.generate_json(prompt, schema=schema, **kwargs)
                    if response:
                        return {
                            "provider_used": provider_name,
                            "fallback_used": idx > 0,
                            "response": response,
                            "error": None,
                            "attempts": attempts,
                        }
                    last_error = f"{provider_name}: empty JSON response"
                except Exception as e:
                    last_error = f"{provider_name}: {str(e)}"
                    logger.warning(f"JSON provider {provider_name} failed (attempt {retry + 1}): {e}")

                if retry < max_retries - 1:
                    delay = backoff_base * (2 ** retry)
                    time.sleep(delay)

        return {
            "provider_used": None,
            "fallback_used": True,
            "response": {},
            "error": last_error,
            "attempts": attempts,
        }

