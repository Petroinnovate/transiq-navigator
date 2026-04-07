"""
Simple Interactive Demo - Upload and View Results
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8001"

def main():
    print("\n" + "="*80)
    print("  TransIQ Backend - Interactive Demo")
    print("="*80 + "\n")
    
    # Check if server is running
    print("🔍 Checking server status...")
    try:
        response = requests.get(f"{BASE_URL}/system/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is RUNNING on http://localhost:8001\n")
        else:
            print("❌ Server responded but with error status\n")
            return
    except:
        print("❌ Cannot connect to server!")
        print("Please make sure the backend is running (check the PowerShell window)\n")
        return
    
    # Show available file
    test_file = Path("test_sales_data.csv")
    if not test_file.exists():
        print("❌ Test file not found: test_sales_data.csv")
        return
    
    print(f"📁 Found test file: {test_file.name}")
    print(f"📏 File size: {test_file.stat().st_size} bytes")
    print("\n" + "-"*80)
    print("📄 File Preview (first 5 lines):")
    print("-"*80)
    lines = test_file.read_text().split('\n')
    for i, line in enumerate(lines[:5], 1):
        print(f"{i}. {line}")
    print(f"... ({len(lines)} total lines)\n")
    
    # Ask user to confirm
    print("="*80)
    print("🚀 Ready to upload and process this file!")
    print("="*80)
    print("\nThe AI will:")
    print("  1. Analyze the sales data")
    print("  2. Generate a dashboard with KPIs")
    print("  3. Create charts and visualizations")
    print("  4. Provide insights and recommendations")
    print("  5. Store the document with vector embeddings")
    print()
    
    input("Press ENTER to start processing (or Ctrl+C to cancel)...")
    
    print("\n⏳ Processing... (this may take 10-30 seconds)")
    print("   The AI is analyzing your data...\n")
    
    # Upload and process
    with open(test_file, 'rb') as f:
        files = {'files': (test_file.name, f, 'text/csv')}
        
        try:
            response = requests.post(
                f"{BASE_URL}/generate",
                files=files,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print("\n" + "="*80)
                print("✅ SUCCESS! Document processed")
                print("="*80 + "\n")
                
                # Save full response
                output_file = Path("demo_result.json")
                output_file.write_text(json.dumps(result, indent=2))
                print(f"💾 Full response saved to: {output_file}\n")
                
                # Display key results
                if 'dashboard' in result:
                    dashboard = result['dashboard']
                    
                    # Title and Description
                    print("="*80)
                    print("📊 DASHBOARD RESULTS")
                    print("="*80 + "\n")
                    
                    print(f"📋 Title: {dashboard.get('title', 'N/A')}\n")
                    
                    desc = dashboard.get('description', 'N/A')
                    print(f"📝 Description:\n{desc}\n")
                    
                    # KPIs
                    if 'kpis' in dashboard and dashboard['kpis']:
                        print("\n" + "-"*80)
                        print("🎯 KEY PERFORMANCE INDICATORS")
                        print("-"*80 + "\n")
                        
                        for i, kpi in enumerate(dashboard['kpis'], 1):
                            label = kpi.get('label', 'N/A')
                            value = kpi.get('value', 'N/A')
                            print(f"{i}. {label}: {value}")
                            
                            if 'change' in kpi:
                                change = kpi['change']
                                trend = kpi.get('trend', '')
                                emoji = "📈" if trend == 'up' else "📉" if trend == 'down' else "➡️"
                                print(f"   {emoji} Change: {change}")
                            
                            if 'description' in kpi:
                                print(f"   → {kpi['description']}")
                            print()
                    
                    # Charts
                    if 'charts' in dashboard and dashboard['charts']:
                        print("\n" + "-"*80)
                        print("📈 CHARTS & VISUALIZATIONS")
                        print("-"*80 + "\n")
                        
                        for i, chart in enumerate(dashboard['charts'], 1):
                            title = chart.get('title', 'N/A')
                            chart_type = chart.get('type', 'N/A')
                            print(f"{i}. {title}")
                            print(f"   Type: {chart_type}")
                            
                            if 'data' in chart:
                                data_count = len(chart['data']) if isinstance(chart['data'], list) else 'N/A'
                                print(f"   Data points: {data_count}")
                            
                            if 'description' in chart:
                                print(f"   → {chart['description']}")
                            print()
                    
                    # Tables
                    if 'tables' in dashboard and dashboard['tables']:
                        print("\n" + "-"*80)
                        print("📋 DATA TABLES")
                        print("-"*80 + "\n")
                        
                        for i, table in enumerate(dashboard['tables'], 1):
                            title = table.get('title', 'N/A')
                            print(f"{i}. {title}")
                            
                            if 'data' in table:
                                data_count = len(table['data']) if isinstance(table['data'], list) else 'N/A'
                                print(f"   Rows: {data_count}")
                            print()
                    
                    # Insights
                    if 'insights' in dashboard and dashboard['insights']:
                        print("\n" + "-"*80)
                        print("💡 KEY INSIGHTS")
                        print("-"*80 + "\n")
                        
                        for i, insight in enumerate(dashboard['insights'], 1):
                            print(f"{i}. {insight}\n")
                    
                    # Optimization Suggestions
                    if 'optimizationSuggestions' in dashboard and dashboard['optimizationSuggestions']:
                        print("\n" + "-"*80)
                        print("🔧 OPTIMIZATION SUGGESTIONS")
                        print("-"*80 + "\n")
                        
                        for i, suggestion in enumerate(dashboard['optimizationSuggestions'], 1):
                            print(f"{i}. {suggestion}\n")
                    
                    # Six Sigma
                    if 'sixSigma' in dashboard and dashboard['sixSigma']:
                        print("\n" + "-"*80)
                        print("📊 SIX SIGMA ANALYSIS")
                        print("-"*80 + "\n")
                        
                        six_sigma = dashboard['sixSigma']
                        if isinstance(six_sigma, dict):
                            for key, value in six_sigma.items():
                                print(f"{key}: {value}")
                        else:
                            print(six_sigma)
                        print()
                
                print("\n" + "="*80)
                print("✨ DEMO COMPLETE!")
                print("="*80 + "\n")
                
                print("📌 What happened:")
                print("  ✅ File uploaded to backend")
                print("  ✅ AI analyzed the data")
                print("  ✅ Dashboard generated with insights")
                print("  ✅ Document stored with embeddings")
                print("  ✅ Now searchable via vector similarity")
                print()
                print("📊 View interactive API docs: http://localhost:8001/docs")
                print(f"📄 Full JSON result: {output_file}")
                print()
                
            else:
                print(f"\n❌ Upload failed!")
                print(f"Status code: {response.status_code}")
                print(f"Response: {response.text}\n")
                
        except requests.exceptions.Timeout:
            print("\n❌ Request timed out!")
            print("The AI processing took too long. Try again with a smaller file.\n")
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo cancelled by user\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
