import requests
import json
import os
import sys

# Set API key
os.environ['GEMINI_API_KEY'] = 'AIzaSyCmr50T6O34LM_4WzbAdk554b8zeBbaSq4'

# Import the backend
sys.path.insert(0, r'C:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master')
from llm import generate_response
from fastapi import UploadFile
import asyncio

# Upload the PDF file
file_path = r"C:\Users\Akshay\Downloads\World-Energy-Scenarios_Composing-energy-futures-to-2050_Executive-summary.pdf"

print(f"Processing: {file_path}")
print("-" * 60)

async def test_upload():
    try:
        # Create UploadFile object
        with open(file_path, 'rb') as f:
            content = f.read()
        
        class MockUploadFile:
            def __init__(self, filename, content):
                self.filename = filename
                self.content = content
                self._pos = 0
            
            async def read(self):
                return self.content
        
        file = MockUploadFile(os.path.basename(file_path), content)
        
        print("Calling generate_response...")
        result = await generate_response([file], None)
        
        if hasattr(result, 'body'):
            import json
            result = json.loads(result.body)
        
        print("SUCCESS! Dashboard generated:")
        print(json.dumps(result, indent=2))
        
        # Save to file for review
        with open('dashboard_output.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("\nFull output saved to: dashboard_output.json")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

# Run the async function
asyncio.run(test_upload())
