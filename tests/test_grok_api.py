"""
Test Grok API Connection
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from openai import OpenAI

def test_grok_api():
    """Test Grok API with simple prompt"""
    api_key = "xai-okl8LaPq157s4ZApxvv0vUj8I5oKdAWO8iKtguO0YpQdp0ZJ3XPf44UjdyrjAQwp8nw7beTXKeAXVSNQ"
    
    print("Testing Grok API...")
    print(f"API Key: {api_key[:20]}...")
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        
        print("\nSending test request...")
        response = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": "Say 'Hello from Grok!' in exactly 5 words."}
            ],
            max_tokens=50,
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        print(f"\n✅ SUCCESS!")
        print(f"Response: {result}")
        print(f"Model: {response.model}")
        print(f"Tokens used: {response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_grok_api()
    sys.exit(0 if success else 1)
