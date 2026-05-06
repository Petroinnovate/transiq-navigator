"""Test each LLM provider to find one that works."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm.factory import LLMFactory

providers_to_try = ["gemini", "openai", "grok"]

for name in providers_to_try:
    print(f"\nTesting {name}...")
    try:
        p = LLMFactory.get_provider(name)
        info = p.get_model_info()
        print(f"  Model: {info.get('model', '?')}")
        result = p.generate_json("Return a JSON object: {\"status\": \"ok\", \"provider\": \"" + name + "\"}")
        print(f"  Response: {result}")
        print(f"  [OK] {name} WORKS!")
    except Exception as e:
        err = str(e)[:200]
        print(f"  [FAIL] {err}")
