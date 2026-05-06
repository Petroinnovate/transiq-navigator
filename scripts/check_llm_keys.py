"""Check LLM API key configuration."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config.settings import settings

print("LLM Keys configured:")
keys = {
    "GEMINI_API_KEY": settings.GEMINI_API_KEY,
    "GEMINI_API_KEY_2": settings.GEMINI_API_KEY_2,
    "GEMINI_API_KEY_3": settings.GEMINI_API_KEY_3,
    "OPENAI_API_KEY": settings.OPENAI_API_KEY,
    "GROK_API_KEY": settings.GROK_API_KEY,
    "ANTHROPIC_API_KEY": settings.ANTHROPIC_API_KEY,
}
for name, val in keys.items():
    if val:
        masked = val[:6] + "..." + val[-4:]
        print(f"  {name}: YES ({masked})")
    else:
        print(f"  {name}: NO")

print(f"\nDEFAULT_LLM_PROVIDER: {settings.DEFAULT_LLM_PROVIDER or 'auto'}")

from services.llm.factory import LLMFactory
p = LLMFactory.get_provider()
info = p.get_model_info()
print(f"Active provider: {info}")

# Quick test: try to generate
print("\nTesting LLM call...")
try:
    result = p.generate_json("Return a JSON object with key 'status' and value 'ok'.")
    print(f"  LLM response: {result}")
    print("  [OK] LLM is working!")
except Exception as e:
    print(f"  [FAIL] LLM error: {e}")
    print("\n  --> Your API key may be invalid or expired.")
    print("  --> Check .env file and update the key.")
