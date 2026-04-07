"""
Google Gemini LLM Provider
Supports multiple API keys for automatic rotation when quota is exhausted.

Environment variables (add to your .env file):
    GEMINI_API_KEY     - Primary key (required)
    GEMINI_API_KEY_2   - Second key  (optional)
    GEMINI_API_KEY_3   - Third key   (optional)
    GEMINI_API_KEY_4   - Fourth key  (optional)

Rotation order: key1 → key2 → key3 → key4, each trying all models before moving on.
"""
import json
import re
import time
from typing import Optional, Dict, Any, List, Tuple
from google import genai
from google.genai.types import Content, Part, GenerateContentConfig
from core.config.settings import settings
from app.llm.providers.base import LLMProvider
from core.errors import LLMProviderError
from core.logging.logger import get_logger

logger = get_logger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini provider with multi-key rotation and model fallback."""

    # Model fallback order within each key
    _FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash", **kwargs):
        """
        Initialize Gemini provider.

        Loads all configured API keys from environment variables:
            GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, GEMINI_API_KEY_4
        The `api_key` argument (or GEMINI_API_KEY) is always Key #1.
        """
        primary_key = api_key or settings.GEMINI_API_KEY
        if not primary_key:
            raise LLMProviderError("GEMINI_API_KEY not provided", provider="gemini")

        super().__init__(primary_key, **kwargs)
        self.model_name = model

        # Build ordered list of (label, client) pairs — one client per unique key
        self._clients: List[Tuple[str, genai.Client]] = []
        seen: set = set()
        configured_keys = settings.get_gemini_api_keys()
        extra_keys = configured_keys[1:] if configured_keys else []
        key_vars = [("Key-1", primary_key)] + [
            (f"Key-{index}", key)
            for index, key in enumerate(extra_keys, start=2)
        ]
        for label, key in key_vars:
            key = key.strip()
            if key and key not in seen:
                seen.add(key)
                self._clients.append((label, genai.Client(api_key=key)))

        logger.info(
            f"Initialized Gemini provider: model={model}, "
            f"{len(self._clients)} API key(s) loaded"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_daily_quota_exhausted(self, err_str: str) -> bool:
        """True only for hard per-day limits, not per-minute rate limits."""
        return "PerDay" in err_str or "per_day" in err_str.lower()

    def _models_to_try(self) -> List[str]:
        """Primary model first, then fallback models."""
        fallbacks = [m for m in self._FALLBACK_MODELS if m != self.model_name]
        return [self.model_name] + fallbacks

    def _call_with_rotation(self, contents: list, config: GenerateContentConfig) -> str:
        """
        Core request dispatcher with two-level fallback:
          Outer loop → API keys (rotated when daily quota is exhausted)
          Inner loop → models (rotated on daily quota OR after per-minute retries)
          Innermost  → exponential backoff on per-minute 429s

        Returns the raw response.text string.
        """
        all_exhausted: List[str] = []  # collect failure info for final error

        for key_label, client in self._clients:
            key_daily_exhausted = False

            for model in self._models_to_try():
                for attempt in range(3):
                    try:
                        response = client.models.generate_content(
                            model=model,
                            contents=contents,
                            config=config,
                        )
                        if response.text:
                            if key_label != "Key-1" or model != self.model_name:
                                logger.info(
                                    f"Gemini: succeeded on {key_label} / {model}"
                                )
                            return response.text
                        raise LLMProviderError(
                            "Empty response from Gemini", provider="gemini"
                        )

                    except LLMProviderError:
                        raise  # propagate our own errors immediately
                    except Exception as e:
                        err_str = str(e)
                        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                            if self._is_daily_quota_exhausted(err_str):
                                logger.warning(
                                    f"Gemini daily quota exhausted: "
                                    f"{key_label} / {model} — trying next model/key"
                                )
                                break  # break attempt loop → try next model
                            # Per-minute rate limit — back off and retry
                            wait = 10 * (2 ** attempt)  # 10s, 20s, 40s
                            logger.warning(
                                f"Gemini per-minute 429 on {key_label}/{model} "
                                f"(attempt {attempt+1}/3), waiting {wait}s..."
                            )
                            time.sleep(wait)
                            continue
                        # Non-quota error — don't rotate, raise immediately
                        logger.error(f"Gemini error ({key_label}/{model}): {e}")
                        raise LLMProviderError(
                            f"Gemini failed: {str(e)}", provider="gemini"
                        )
                else:
                    # Per-minute retries exhausted without a break → log and try next model
                    msg = f"{key_label}/{model}: per-minute retries exhausted"
                    logger.warning(f"Gemini: {msg}")
                    all_exhausted.append(msg)
                    continue

                # Reached here via break (daily quota on this model) → try next model
                msg = f"{key_label}/{model}: daily quota"
                all_exhausted.append(msg)

            # All models for this key failed — move to next key
            logger.warning(
                f"Gemini: all models exhausted for {key_label}, "
                f"rotating to next API key..."
            )

        raise LLMProviderError(
            f"Gemini failed: all {len(self._clients)} API key(s) and all models are "
            f"quota-exhausted. Details: {'; '.join(all_exhausted)}. "
            "Free-tier daily quota is used up — add more keys or wait until midnight PT.",
            provider="gemini",
        )
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text with automatic key rotation and model fallback."""
        config = GenerateContentConfig(
            temperature=kwargs.get("temperature", 0.2),
            max_output_tokens=kwargs.get("max_tokens"),
        )
        contents = [Content(role="user", parts=[Part(text=prompt)])]
        return self._call_with_rotation(contents, config)
    
    async def agenerate(self, prompt: str, **kwargs) -> str:
        """Generate text asynchronously (Gemini client is sync, but we wrap it)"""
        # Gemini client is synchronous, but we make it async-compatible
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate, prompt, **kwargs)
    
    def generate_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict:
        """Generate structured JSON with automatic key rotation and model fallback."""
        if schema:
            json_prompt = f"{prompt}\n\nReturn the response as valid JSON matching this schema: {json.dumps(schema)}"
        else:
            json_prompt = f"{prompt}\n\nReturn the response as valid JSON."

        config = GenerateContentConfig(
            temperature=kwargs.get("temperature", 0.2),
            response_mime_type="application/json",
        )
        contents = [Content(role="user", parts=[Part(text=json_prompt)])]
        raw = self._call_with_rotation(contents, config)

        try:
            json_match = re.search(r'(\{.*\})', raw, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            raise LLMProviderError(f"Failed to parse JSON response: {str(e)}", provider="gemini")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Gemini model information"""
        return {
            "provider": "gemini",
            "model": self.model_name,
            "supports_streaming": True,
            "supports_json": True
        }

