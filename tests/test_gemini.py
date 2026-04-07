import os
from google import genai

# Test Gemini API connection
api_key = "AIzaSyCmr50T6O34LM_4WzbAdk554b8zeBbaSq4"

print("Testing Gemini API...")
print(f"API Key: {api_key[:20]}...")

try:
    client = genai.Client(api_key=api_key)
    
    # List available models
    print("\nAvailable models:")
    for model in client.models.list():
        print(f"  - {model.name}")
    
    # Try a simple request with gemini-pro
    print("\nTesting generation...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='Say "Hello, API is working!"'
    )
    
    print("✓ SUCCESS! Gemini API is working")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"✗ ERROR: {e}")
    print(f"Error type: {type(e).__name__}")
