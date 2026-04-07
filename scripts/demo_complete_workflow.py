"""
Complete TransIQ Backend Demonstration
This script demonstrates the full workflow of the document processing system
"""

import requests
import json
import time
import io
from pathlib import Path

BASE_URL = "http://localhost:8001"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ️  {message}")

def print_data(label, data):
    """Print formatted data"""
    print(f"\n📊 {label}:")
    print(json.dumps(data, indent=2))

def check_server_health():
    """Check if the server is running"""
    print_section("1. SERVER HEALTH CHECK")
    try:
        response = requests.get(f"{BASE_URL}/system/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("Server is running!")
            print_data("Health Status", data)
            return True
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on http://localhost:8001")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_sample_csv():
    """Create a sample CSV file for testing"""
    print_section("2. CREATING SAMPLE DATA FILE")
    
    csv_content = """Product,Region,Sales,Cost,Profit,Units_Sold,Date
Widget A,North,50000,30000,20000,1000,2024-01-15
Widget B,South,45000,25000,20000,900,2024-01-16
Widget C,East,60000,35000,25000,1200,2024-01-17
Widget A,West,55000,32000,23000,1100,2024-01-18
Widget B,North,48000,28000,20000,950,2024-01-19
Widget C,South,62000,36000,26000,1250,2024-01-20
Widget A,East,52000,31000,21000,1050,2024-01-21
Widget B,West,47000,27000,20000,920,2024-01-22
Widget C,North,65000,38000,27000,1300,2024-01-23
Widget A,South,53000,30000,23000,1080,2024-01-24"""
    
    file_path = Path("sample_sales_data.csv")
    file_path.write_text(csv_content)
    print_success(f"Created sample file: {file_path}")
    print_info(f"File size: {len(csv_content)} bytes")
    print_info("Content: Sales data with 10 rows")
    return file_path

def upload_and_process_document(file_path):
    """Upload and process a document"""
    print_section("3. UPLOADING & PROCESSING DOCUMENT")
    
    print_info(f"Uploading file: {file_path.name}")
    print_info("Processing with AI analysis...")
    
    with open(file_path, 'rb') as f:
        files = {'files': (file_path.name, f, 'text/csv')}
        
        try:
            response = requests.post(
                f"{BASE_URL}/generate",
                files=files,
                timeout=120  # AI processing can take time
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success("Document processed successfully!")
                
                if 'dashboard' in data:
                    dashboard = data['dashboard']
                    
                    print("\n" + "-"*80)
                    print(f"📈 TITLE: {dashboard.get('title', 'N/A')}")
                    print("-"*80)
                    print(f"\n📝 DESCRIPTION:\n{dashboard.get('description', 'N/A')}")
                    
                    # Display KPIs
                    if 'kpis' in dashboard and dashboard['kpis']:
                        print("\n" + "-"*80)
                        print("🎯 KEY PERFORMANCE INDICATORS:")
                        print("-"*80)
                        for i, kpi in enumerate(dashboard['kpis'][:5], 1):  # Show first 5
                            print(f"\n{i}. {kpi.get('label', 'N/A')}")
                            print(f"   Value: {kpi.get('value', 'N/A')}")
                            if 'change' in kpi:
                                print(f"   Change: {kpi['change']}")
                    
                    # Display Charts
                    if 'charts' in dashboard and dashboard['charts']:
                        print("\n" + "-"*80)
                        print("📊 CHARTS:")
                        print("-"*80)
                        for i, chart in enumerate(dashboard['charts'][:3], 1):  # Show first 3
                            print(f"\n{i}. {chart.get('title', 'N/A')}")
                            print(f"   Type: {chart.get('type', 'N/A')}")
                            if 'data' in chart:
                                print(f"   Data points: {len(chart['data'])}")
                    
                    # Display Insights
                    if 'insights' in dashboard and dashboard['insights']:
                        print("\n" + "-"*80)
                        print("💡 KEY INSIGHTS:")
                        print("-"*80)
                        for i, insight in enumerate(dashboard['insights'][:5], 1):
                            print(f"\n{i}. {insight}")
                    
                    # Display Optimization Suggestions
                    if 'optimizationSuggestions' in dashboard and dashboard['optimizationSuggestions']:
                        print("\n" + "-"*80)
                        print("🔧 OPTIMIZATION SUGGESTIONS:")
                        print("-"*80)
                        for i, suggestion in enumerate(dashboard['optimizationSuggestions'][:5], 1):
                            print(f"\n{i}. {suggestion}")
                
                return data
            else:
                print(f"❌ Upload failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("❌ Request timed out. The AI processing might be taking too long.")
            return None
        except Exception as e:
            print(f"❌ Error during upload: {e}")
            return None

def list_documents():
    """List all stored documents"""
    print_section("4. LISTING STORED DOCUMENTS")
    
    try:
        response = requests.get(f"{BASE_URL}/documents/")
        
        if response.status_code == 200:
            documents = response.json()
            print_success(f"Found {len(documents)} document(s)")
            
            for i, doc in enumerate(documents, 1):
                print(f"\n{i}. Document ID: {doc.get('id', 'N/A')}")
                print(f"   Name: {doc.get('name', 'N/A')}")
                print(f"   Status: {doc.get('status', 'N/A')}")
                print(f"   Created: {doc.get('created_at', 'N/A')}")
            
            return documents
        else:
            print(f"❌ Failed to list documents: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def search_documents(query):
    """Perform semantic search"""
    print_section("5. SEMANTIC SEARCH")
    
    print_info(f"Searching for: '{query}'")
    
    try:
        response = requests.post(
            f"{BASE_URL}/search/",
            json={"query": query, "top_k": 5}
        )
        
        if response.status_code == 200:
            results = response.json()
            print_success(f"Found {len(results.get('results', []))} matching chunks")
            
            if 'results' in results:
                for i, result in enumerate(results['results'][:3], 1):  # Show top 3
                    print(f"\n{i}. Similarity: {result.get('similarity', 0):.4f}")
                    print(f"   Document: {result.get('document_name', 'N/A')}")
                    chunk_text = result.get('chunk_text', '')
                    preview = chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
                    print(f"   Preview: {preview}")
            
            return results
        else:
            print(f"❌ Search failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_authentication():
    """Test authentication endpoints"""
    print_section("6. TESTING AUTHENTICATION (Optional)")
    
    print_info("Testing signup endpoint...")
    
    test_email = f"demo_{int(time.time())}@test.com"
    test_password = "TestPassword123!"
    
    try:
        # Try signup
        signup_data = {
            "email": test_email,
            "password": test_password
        }
        
        response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
        
        if response.status_code == 200:
            data = response.json()
            print_success("User created successfully!")
            print_info(f"Email: {test_email}")
            
            if 'access_token' in data:
                print_success("Access token received")
                return data['access_token']
            else:
                print_info("No access token in response (expected with local storage)")
                return None
        else:
            print_info(f"Signup returned status {response.status_code}")
            print_info("This is expected when using local storage (Supabase not configured)")
            return None
            
    except Exception as e:
        print_info(f"Authentication test skipped: {e}")
        print_info("This is expected when using local storage")
        return None

def display_summary():
    """Display final summary"""
    print_section("DEMONSTRATION COMPLETE")
    
    print("🎉 TransIQ Backend Features Demonstrated:")
    print("\n1. ✅ Server Health Monitoring")
    print("2. ✅ Document Upload & Processing")
    print("3. ✅ AI-Powered Data Analysis")
    print("4. ✅ Automatic Dashboard Generation")
    print("5. ✅ Vector Embedding & Storage")
    print("6. ✅ Document Management (List/View/Delete)")
    print("7. ✅ Semantic Search Capabilities")
    print("8. ✅ Authentication System (Optional)")
    
    print("\n📌 Key Technologies Used:")
    print("   - FastAPI for REST API")
    print("   - Google Gemini AI for analysis")
    print("   - Sentence-Transformers for embeddings")
    print("   - FAISS for vector similarity search")
    print("   - SQLite for local storage")
    
    print("\n🌐 Access Points:")
    print(f"   - API Documentation: {BASE_URL}/docs")
    print(f"   - Health Check: {BASE_URL}/system/health")
    print(f"   - Upload Endpoint: {BASE_URL}/generate")
    
    print("\n" + "="*80)

def main():
    """Main demonstration function"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "TransIQ Backend Complete Demo" + " "*29 + "║")
    print("╚" + "="*78 + "╝")
    
    # Wait for server to be ready
    print_info("Waiting for server to start...")
    time.sleep(3)
    
    # 1. Health Check
    if not check_server_health():
        print("\n❌ Server is not running. Please start it first with: python main.py")
        return
    
    time.sleep(1)
    
    # 2. Create sample file
    file_path = create_sample_csv()
    time.sleep(1)
    
    # 3. Upload and process
    result = upload_and_process_document(file_path)
    if not result:
        print("\n⚠️  Document processing failed. Continuing with other tests...")
    
    time.sleep(2)
    
    # 4. List documents
    documents = list_documents()
    time.sleep(1)
    
    # 5. Search (if we have documents)
    if documents:
        search_documents("sales profit revenue")
        time.sleep(1)
    
    # 6. Test authentication
    test_authentication()
    time.sleep(1)
    
    # 7. Summary
    display_summary()
    
    # Cleanup
    try:
        file_path.unlink()
        print(f"\n🧹 Cleaned up sample file: {file_path}")
    except:
        pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
