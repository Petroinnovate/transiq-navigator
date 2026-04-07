"""
Test what the API actually returns
"""
import requests
import json

# Test file
files = {
    'file': ('test.txt', b'Sales data:\nQ1: $100,000\nQ2: $150,000\nQ3: $200,000\nQ4: $250,000', 'text/plain')
}

print("Sending POST request to http://localhost:8001/api/v2/generate...")
response = requests.post(
    'http://localhost:8001/api/v2/generate?provider=gemini&enable_deduction=true&enable_patterns=true',
    files=files
)

print(f"\nStatus Code: {response.status_code}")
print(f"\nResponse Headers:")
for key, value in response.headers.items():
    print(f"  {key}: {value}")

print(f"\nResponse JSON:")
print(json.dumps(response.json(), indent=2))

# Check structure
data = response.json()
print(f"\n=== STRUCTURE ANALYSIS ===")
print(f"Top-level keys: {list(data.keys())}")
if 'dashboard' in data:
    print(f"Dashboard type: {type(data['dashboard'])}")
    if isinstance(data['dashboard'], dict):
        print(f"Dashboard keys: {list(data['dashboard'].keys())}")
