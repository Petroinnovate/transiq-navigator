"""
Anthropic (Claude) LLM Provider

Implements the same LLMProvider interface as OpenAI/Gemini/Grok providers
so it can be used interchangeably via LLMFactory.
"""
import json
import os
from typing import Any, Dict, Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from services.llm.providers.base import LLMProvider
from core.errors import LLMProviderError
from core.logging.logger import get_logger

logger = get_logger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        **kwargs,
    ):
        if not ANTHROPIC_AVAILABLE:
            raise LLMProviderError(
                "anthropic package not installed. Install with: pip install anthropic",
                provider="anthropic",
            )

        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMProviderError("ANTHROPIC_API_KEY not provided", provider="anthropic")

        super().__init__(api_key, **kwargs)
        self.model_name = model
        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info(f"Initialized Anthropic provider with model: {model}")

    # ------------------------------------------------------------------
    # Synchronous generation
    # ------------------------------------------------------------------

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text synchronously."""
        try:
            temperature = kwargs.get("temperature", 0.2)
            max_tokens = kwargs.get("max_tokens", 4096)

            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            if message.content and len(message.content) > 0:
                return message.content[0].text
            raise LLMProviderError("Empty response from Anthropic", provider="anthropic")

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise LLMProviderError(f"Anthropic API error: {str(e)}", provider="anthropic")
        except Exception as e:
            logger.error(f"Anthropic generation error: {e}")
            raise LLMProviderError(f"Anthropic generation failed: {str(e)}", provider="anthropic")

    # ------------------------------------------------------------------
    # Async generation
    # ------------------------------------------------------------------

    async def agenerate(self, prompt: str, **kwargs) -> str:
        """Generate text asynchronously."""
        try:
            temperature = kwargs.get("temperature", 0.2)
            max_tokens = kwargs.get("max_tokens", 4096)

            async_client = anthropic.AsyncAnthropic(api_key=self.api_key)
            message = await async_client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            if message.content and len(message.content) > 0:
                return message.content[0].text
            raise LLMProviderError("Empty async response from Anthropic", provider="anthropic")

        except anthropic.APIError as e:
            logger.error(f"Anthropic async API error: {e}")
            raise LLMProviderError(f"Anthropic async API error: {str(e)}", provider="anthropic")
        except Exception as e:
            logger.error(f"Anthropic async generation error: {e}")
            raise LLMProviderError(f"Anthropic async generation failed: {str(e)}", provider="anthropic")

    # ------------------------------------------------------------------
    # Structured JSON generation
    # ------------------------------------------------------------------

    def generate_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict:
        """Generate structured JSON response."""
        try:
            temperature = kwargs.get("temperature", 0.2)
            max_tokens = kwargs.get("max_tokens", 4096)

            # Instruct Claude to return JSON via system message
            system_msg = "You are a helpful assistant. Always respond with valid JSON only, no markdown."
            if schema:
                system_msg += f"\n\nRespond according to this JSON schema:\n{json.dumps(schema)}"

            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_msg,
                messages=[{"role": "user", "content": prompt}],
            )

            if message.content and len(message.content) > 0:
                content = message.content[0].text.strip()
                # Strip markdown code fences if present
                if content.startswith("```"):
                    lines = content.split("\n")
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    content = "\n".join(lines).strip()
                return json.loads(content)
            raise LLMProviderError("Empty JSON response from Anthropic", provider="anthropic")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error from Anthropic: {e}")
            raise LLMProviderError(f"Failed to parse JSON response: {str(e)}", provider="anthropic")
        except Exception as e:
            logger.error(f"Anthropic JSON generation error: {e}")
            raise LLMProviderError(f"Anthropic JSON generation failed: {str(e)}", provider="anthropic")

    # ------------------------------------------------------------------
    # Model info
    # ------------------------------------------------------------------

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "anthropic",
            "model": self.model_name,
            "supports_streaming": True,
            "supports_json": True,
        }
