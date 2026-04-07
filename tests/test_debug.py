"""Debug script to find the exact error"""
import requests
import os
import tempfile
import traceback

# Create a test CSV file
test_data = """Name,Value,Category
Item1,100,TypeA
Item2,200,TypeB
Item3,150,TypeA
Item4,300,TypeB
"""

# Create temporary CSV file
temp_dir = tempfile.gettempdir()
test_csv_path = os.path.join(temp_dir, "test_data.csv")
with open(test_csv_path, "w") as f:
    f.write(test_data)

print(f"Test file created: {test_csv_path}")
print(f"File exists: {os.path.exists(test_csv_path)}")
print(f"File size: {os.path.getsize(test_csv_path)} bytes")

try:
    with open(test_csv_path, "rb") as f:
        files = {"files": ("test_data.csv", f, "text/csv")}
        print(f"\nSending request to http://localhost:8001/generate...")
        response = requests.post(
            "http://localhost:8001/generate",
            files=files,
            timeout=120
        )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        print("\n✅ SUCCESS!")
        result = response.json()
        print(f"Response keys: {list(result.keys())}")
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        print(f"Response: {response.text}")
        try:
            error_data = response.json()
            print(f"Error detail: {error_data.get('detail', 'N/A')}")
            print(f"Error message: {error_data.get('error', 'N/A')}")
        except:
            pass
        
except requests.exceptions.ConnectionError:
    print("❌ ERROR: Cannot connect to backend. Is it running?")
except requests.exceptions.Timeout:
    print("❌ ERROR: Request timed out (>120s)")
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
    traceback.print_exc()

