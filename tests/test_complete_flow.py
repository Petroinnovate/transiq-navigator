"""
Direct API test with CSV data
"""
import requests
import json
import io

# Create a simple CSV file in memory
csv_content = """Month,Sales,Expenses,Profit
January,50000,30000,20000
February,55000,32000,23000
March,60000,35000,25000
April,58000,33000,25000"""

files = {
    'file': ('sales_data.csv', csv_content.encode(), 'text/csv')
}

print("Testing /api/v2/generate endpoint...")
print(f"URL: http://localhost:8001/api/v2/generate?provider=gemini&enable_deduction=true&enable_patterns=true")
print("\nUploading CSV file with sales data...")

try:
    response = requests.post(
        'http://localhost:8001/api/v2/generate?provider=gemini&enable_deduction=true&enable_patterns=true',
        files=files,
        timeout=120
    )
    
    print(f"\n✅ Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n📊 RESPONSE STRUCTURE:")
        print(f"  - doc_id: {data.get('doc_id', 'MISSING')}")
        print(f"  - task_id: {data.get('task_id', 'MISSING')}")
        print(f"  - status: {data.get('status', 'MISSING')}")
        print(f"  - message: {data.get('message', 'MISSING')}")
        print(f"  - dashboard present: {'dashboard' in data}")
        
        if 'dashboard' in data:
            dashboard = data['dashboard']
            print(f"\n📈 DASHBOARD CONTENT:")
            print(f"  - meta: {'meta' in dashboard}")
            print(f"  - kpis: {len(dashboard.get('kpis', []))} KPIs")
            print(f"  - charts: {len(dashboard.get('charts', []))} charts")
            print(f"  - sixSigma: {'sixSigma' in dashboard}")
            
            if dashboard.get('kpis'):
                print(f"\n  First KPI: {dashboard['kpis'][0]}")
        else:
            print("\n❌ NO DASHBOARD DATA IN RESPONSE!")
            print(f"Response keys: {list(data.keys())}")
    else:
        print(f"\n❌ ERROR Response:")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")
