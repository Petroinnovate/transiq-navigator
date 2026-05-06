"""
Ling LLM Provider — via OpenRouter (OpenAI-compatible API)
Model: inclusionai/ling-2.6-1t
"""
import os
import json
from typing import Optional, Dict, Any

try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from services.llm.providers.base import LLMProvider
from core.errors import LLMProviderError
from core.logging.logger import get_logger

logger = get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class LingProvider(LLMProvider):
    """Ling provider via OpenRouter's OpenAI-compatible API"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, **kwargs):
        api_key = api_key or os.getenv("LING_API_KEY")
        if not OPENAI_AVAILABLE:
            raise LLMProviderError(
                "openai package not installed. Install with: pip install openai",
                provider="ling",
            )
        if not api_key:
            raise LLMProviderError("LING_API_KEY not provided", provider="ling")

        super().__init__(api_key, **kwargs)
        self.model_name = model or os.getenv("LING_MODEL", "inclusionai/ling-2.6-1t:free")
        self.client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
        self.async_client = AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
        logger.info(f"Initialized Ling provider with model: {self.model_name}")

    # ── sync ──────────────────────────────────────────────────────────

    def generate(self, prompt: str, **kwargs) -> str:
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
            raise LLMProviderError("Empty response from Ling", provider="ling")
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error(f"Ling generation error: {e}")
            raise LLMProviderError(f"Ling generation failed: {str(e)}", provider="ling")

    # ── async ─────────────────────────────────────────────────────────

    async def agenerate(self, prompt: str, **kwargs) -> str:
        try:
            temperature = kwargs.get("temperature", 0.2)
            max_tokens = kwargs.get("max_tokens")

            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            raise LLMProviderError("Empty async response from Ling", provider="ling")
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error(f"Ling async generation error: {e}")
            raise LLMProviderError(f"Ling async generation failed: {str(e)}", provider="ling")

    # ── JSON ──────────────────────────────────────────────────────────

    def generate_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict:
        try:
            temperature = kwargs.get("temperature", 0.2)
            max_tokens = kwargs.get("max_tokens")

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that returns JSON responses."},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                return json.loads(content)
            raise LLMProviderError("Empty JSON response from Ling", provider="ling")
        except json.JSONDecodeError as e:
            logger.error(f"Ling JSON parsing error: {e}")
            raise LLMProviderError(f"Failed to parse JSON response: {str(e)}", provider="ling")
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error(f"Ling JSON generation error: {e}")
            raise LLMProviderError(f"Ling JSON generation failed: {str(e)}", provider="ling")

    # ── info ──────────────────────────────────────────────────────────

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "ling",
            "model": self.model_name,
            "base_url": OPENROUTER_BASE_URL,
            "supports_streaming": True,
            "supports_json": True,
        }
