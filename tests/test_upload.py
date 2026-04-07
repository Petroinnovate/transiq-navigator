"""Test script to simulate file upload and identify errors"""
import requests
import os
import tempfile

# Create a test Excel file
test_data = """Name,Value,Category
Item1,100,TypeA
Item2,200,TypeB
Item3,150,TypeA
Item4,300,TypeB
"""

# Create temporary Excel file
temp_dir = tempfile.gettempdir()
test_file_path = os.path.join(temp_dir, "test_data.xlsx")

# For testing, we'll use CSV and convert or just test with CSV
test_csv_path = os.path.join(temp_dir, "test_data.csv")
with open(test_csv_path, "w") as f:
    f.write(test_data)

print(f"Testing backend /generate endpoint...")
print(f"Backend URL: http://localhost:8001/generate")
print(f"Test file: {test_csv_path}")

try:
    with open(test_csv_path, "rb") as f:
        files = {"files": ("test_data.csv", f, "text/csv")}
        response = requests.post(
            "http://localhost:8001/generate",
            files=files,
            timeout=120
        )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("\n✅ SUCCESS!")
        result = response.json()
        print(f"Response keys: {list(result.keys())}")
        if "dashboard" in result:
            print(f"Dashboard keys: {list(result['dashboard'].keys())}")
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ ERROR: Cannot connect to backend. Is it running?")
except requests.exceptions.Timeout:
    print("❌ ERROR: Request timed out (>120s)")
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()

