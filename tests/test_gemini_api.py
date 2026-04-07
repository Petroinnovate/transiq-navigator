"""
Quick test to verify Gemini API key is working
"""
import os
import sys

# Set API key
os.environ['GEMINI_API_KEY'] = 'AIzaSyCS0pWbCGmpBscDdaMn0GWKPZD9cPRhChc'

try:
    from app.llm.factory import LLMFactory
    from app.config.settings import settings
    
    print("=" * 60)
    print("Testing Gemini API Configuration")
    print("=" * 60)
    print()
    
    # Check settings
    print(f"API Key in settings: {'Set' if settings.GEMINI_API_KEY else 'Not Set'}")
    if settings.GEMINI_API_KEY:
        print(f"API Key preview: {settings.GEMINI_API_KEY[:20]}...")
    print()
    
    # Try to create provider
    print("Creating Gemini provider...")
    try:
        provider = LLMFactory.get_provider("gemini")
        print(f"[OK] Provider created: {provider.get_model_info()['provider']}")
        print(f"     Model: {provider.get_model_info()['model']}")
        print()
        
        # Test a simple generation
        print("Testing API call...")
        response = provider.generate("Say 'Hello' in one word.")
        print(f"[OK] API Response: {response}")
        print()
        print("=" * 60)
        print("[SUCCESS] Gemini API is working!")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Failed to create provider: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
except Exception as e:
    print(f"[ERROR] Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

