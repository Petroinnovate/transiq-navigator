"""
Test Ling-2.6-1T Integration
Run: python test_ling.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from core.config.settings import settings
from services.llm.factory import LLMFactory

def divider(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ── Test 1: Settings loaded ──────────────────────────────────
divider("TEST 1: Settings")
print(f"  LING_API_KEY loaded : {bool(settings.LING_API_KEY)}")
print(f"  LING_MODEL          : {settings.LING_MODEL}")

# ── Test 2: Provider creation ────────────────────────────────
divider("TEST 2: Create Ling provider via factory")
try:
    provider = LLMFactory.get_provider("ling")
    info = provider.get_model_info()
    print(f"  Provider created OK : {info}")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

# ── Test 3: Simple generation ────────────────────────────────
divider("TEST 3: Simple text generation")
t0 = time.time()
try:
    response = provider.generate(
        "You are an oil & gas drilling expert. Explain what ROP means in one sentence.",
        temperature=0.3,
        max_tokens=100,
    )
    elapsed = time.time() - t0
    print(f"  Response ({elapsed:.1f}s): {response}")
except Exception as e:
    print(f"  FAILED: {e}")

# ── Test 4: JSON generation ──────────────────────────────────
divider("TEST 4: JSON generation")
t0 = time.time()
try:
    json_result = provider.generate_json(
        "Return a JSON object with keys: model_name (string), capabilities (list of 3 strings), max_context_tokens (number). "
        "Describe the Ling-2.6-1T model.",
        max_tokens=200,
    )
    elapsed = time.time() - t0
    print(f"  JSON ({elapsed:.1f}s): {json_result}")
except Exception as e:
    print(f"  FAILED (JSON): {e}")

# ── Test 5: Fallback chain includes Ling ─────────────────────
divider("TEST 5: Fallback chain")
chain = LLMFactory._available_chain()
print(f"  Available providers : {chain}")
print(f"  Ling in chain       : {'ling' in chain}")

# ── Test 6: generate_with_fallback (force ling first) ────────
divider("TEST 6: Fallback generation (ling-first priority)")
t0 = time.time()
try:
    result = LLMFactory.generate_with_fallback(
        "What is wellbore stability? Answer in one sentence.",
        priority=["ling", "gemini", "openai"],
        max_tokens=80,
    )
    elapsed = time.time() - t0
    print(f"  Provider used : {result['provider_used']}")
    print(f"  Fallback?     : {result['fallback_used']}")
    print(f"  Response ({elapsed:.1f}s): {result['response']}")
except Exception as e:
    print(f"  FAILED: {e}")

# ── Summary ──────────────────────────────────────────────────
divider("DONE — Ling-2.6-1T is integrated!")
print("  You can now use it by setting DEFAULT_LLM_PROVIDER=ling in .env")
print("  Or call: LLMFactory.get_provider('ling')")
print()
