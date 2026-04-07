"""
Gemini-based LLM adapter that replaces PageIndex's OpenAI (ChatGPT_API) calls.

Drop-in replacement:
  ChatGPT_API(...)                      → gemini_call(...)
  ChatGPT_API_with_finish_reason(...)   → gemini_call_with_finish_reason(...)
  ChatGPT_API_async(...)                → gemini_call_async(...)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Tuple

logger = logging.getLogger(__name__)

# Re-use the project-level Gemini client -----------------------------------------
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyCmr50T6O34LM_4WzbAdk554b8zeBbaSq4"
_GEMINI_MODEL   = os.getenv("PAGEINDEX_MODEL", "gemini-2.0-flash")
_MAX_RETRIES    = 5


def _get_client():
    from google import genai
    return genai.Client(api_key=_GEMINI_API_KEY)


# ---------------------------------------------------------------------------
# Token estimation (no tiktoken dependency)
# ---------------------------------------------------------------------------

def count_tokens(text: str, model: str = None) -> int:
    """Rough estimate: 1 token ≈ 4 characters."""
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Synchronous call
# ---------------------------------------------------------------------------

def gemini_call(prompt: str) -> str:
    """Synchronous Gemini call. Returns response text or 'Error'."""
    client = _get_client()
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=_GEMINI_MODEL,
                contents=prompt,
            )
            return response.text or ""
        except Exception as exc:
            logger.warning("gemini_call attempt %d failed: %s", attempt + 1, exc)
            if attempt < _MAX_RETRIES - 1:
                time.sleep(1 + attempt)
    logger.error("gemini_call: max retries reached")
    return "Error"


def gemini_call_with_finish_reason(prompt: str, chat_history=None) -> Tuple[str, str]:
    """
    Returns (text, finish_reason) where finish_reason is
    'finished' or 'max_output_reached'.
    Gemini does not expose finish_reason the same way OpenAI does, so we
    treat any complete response as 'finished'.
    """
    client = _get_client()
    for attempt in range(_MAX_RETRIES):
        try:
            messages = prompt
            if chat_history:
                # Flatten history + new prompt into a single string
                hist_text = "\n".join(
                    f"{m['role'].upper()}: {m['content']}" for m in chat_history
                )
                messages = hist_text + "\nUSER: " + prompt

            response = client.models.generate_content(
                model=_GEMINI_MODEL,
                contents=messages,
            )
            text = response.text or ""
            # Treat responses that look truncated (no closing brace/bracket) as incomplete
            stripped = text.strip()
            if stripped.endswith(("]", "}", '"', "'")):
                return text, "finished"
            else:
                return text, "max_output_reached"
        except Exception as exc:
            logger.warning("gemini_call_with_finish_reason attempt %d failed: %s", attempt + 1, exc)
            if attempt < _MAX_RETRIES - 1:
                time.sleep(1 + attempt)
    return "Error", "finished"


# ---------------------------------------------------------------------------
# Async call
# ---------------------------------------------------------------------------

async def gemini_call_async(prompt: str) -> str:
    """Async Gemini call. Returns response text or 'Error'."""
    client = _get_client()
    for attempt in range(_MAX_RETRIES):
        try:
            response = await client.aio.models.generate_content(
                model=_GEMINI_MODEL,
                contents=prompt,
            )
            return response.text or ""
        except Exception as exc:
            logger.warning("gemini_call_async attempt %d failed: %s", attempt + 1, exc)
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(1 + attempt)
    logger.error("gemini_call_async: max retries reached")
    return "Error"


# ---------------------------------------------------------------------------
# JSON extraction helper (identical to PageIndex utils.extract_json)
# ---------------------------------------------------------------------------

def extract_json(content: str):
    """Extract and parse JSON from LLM response text."""
    try:
        start_idx = content.find("```json")
        if start_idx != -1:
            start_idx += 7
            end_idx = content.rfind("```")
            json_content = content[start_idx:end_idx].strip()
        else:
            json_content = content.strip()

        json_content = json_content.replace("None", "null")
        json_content = json_content.replace("\n", " ").replace("\r", " ")
        json_content = " ".join(json_content.split())

        return json.loads(json_content)
    except json.JSONDecodeError:
        try:
            json_content = json_content.replace(",]", "]").replace(",}", "}")
            return json.loads(json_content)
        except Exception:
            logger.error("extract_json: failed to parse JSON from: %s", content[:200])
            return {}
    except Exception as exc:
        logger.error("extract_json unexpected error: %s", exc)
        return {}


def get_json_content(response: str) -> str:
    """Strip ```json ... ``` fences."""
    start = response.find("```json")
    if start != -1:
        response = response[start + 7:]
    end = response.rfind("```")
    if end != -1:
        response = response[:end]
    return response.strip()
