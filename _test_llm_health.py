"""Quick LLM API health check."""
import sys, time
sys.path.insert(0, '.')
from services.llm.factory import LLMFactory

provider = LLMFactory.get_provider()
info = provider.get_model_info()
print(f"Provider: {info}")

print("\nTest 1: generate_json (simple)")
t0 = time.time()
try:
    result = provider.generate_json('Return a JSON object: {"status": "ok", "message": "hello"}')
    elapsed = int((time.time() - t0) * 1000)
    print(f"  Response ({elapsed}ms): {result}")
    if isinstance(result, dict) and result.get("status"):
        print("  Result: PASS")
    else:
        print("  Result: UNEXPECTED FORMAT")
except Exception as e:
    elapsed = int((time.time() - t0) * 1000)
    print(f"  ERROR ({elapsed}ms): {type(e).__name__}: {e}")
    print("  Result: FAIL")

print("\nTest 2: generate (plain text)")
t0 = time.time()
try:
    result = provider.generate("Say 'API working' in exactly two words.")
    elapsed = int((time.time() - t0) * 1000)
    print(f"  Response ({elapsed}ms): {repr(result[:200])}")
    print("  Result: PASS")
except Exception as e:
    elapsed = int((time.time() - t0) * 1000)
    print(f"  ERROR ({elapsed}ms): {type(e).__name__}: {e}")
    print("  Result: FAIL")
