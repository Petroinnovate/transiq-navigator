#!/usr/bin/env python3
"""
Check the status of document processing and show timing information
"""
import sys
import time
from datetime import datetime
from app.storage.qdrant_storage import QdrantStorage
from core.config.settings import settings

def check_processing_status():
    """Check what's currently being processed"""
    storage = QdrantStorage()
    
    try:
        # Get all documents
        docs = storage.list_documents(limit=10)
        
        if not docs:
            print("❌ No documents found in storage")
            return
        
        print(f"\n📊 Document Processing Status")
        print(f"{'='*60}")
        print(f"Total documents: {len(docs)}\n")
        
        for i, doc_id in enumerate(docs[:3], 1):  # Show top 3
            doc_data = storage.get_document(doc_id)
            if not doc_data:
                continue
                
            status = doc_data.get("status", "unknown")
            created = doc_data.get("created_at", "N/A")
            file_name = doc_data.get("file_name", "N/A")
            file_size = doc_data.get("file_size", 0)
            
            # Check dashboard data
            has_kpis = "kpis" in doc_data or ("dashboard" in doc_data and "kpis" in doc_data["dashboard"])
            has_charts = "charts" in doc_data or ("dashboard" in doc_data and "charts" in doc_data["dashboard"])
            
            kpi_count = 0
            if "kpis" in doc_data:
                kpi_count = len(doc_data.get("kpis", []))
            elif "dashboard" in doc_data:
                kpi_count = len(doc_data["dashboard"].get("kpis", []))
            
            print(f"Document {i}: {doc_id[:12]}...")
            print(f"  File: {file_name} ({file_size:,} bytes)")
            print(f"  Status: {status}")
            print(f"  Created: {created}")
            print(f"  KPIs: {kpi_count if has_kpis else '❌ Not yet'}")
            print(f"  Charts: {'✅ Yes' if has_charts else '❌ Not yet'}")
            
            # Estimate time
            if status == "completed" and has_kpis:
                print(f"  ✅ READY FOR DASHBOARD")
            elif status == "processing":
                print(f"  ⏳ STILL PROCESSING...")
                print(f"     (Generating KPIs and dashboard...)")
            else:
                print(f"  ⚠️  Status: {status}")
            print()
        
        print(f"{'='*60}")
        print("\n💡 Tips:")
        print("  • Gemini API: ~30-60 seconds for 800 pages")
        print("  • Check backend logs: logs/app.log")
        print("  • Refresh browser if stuck on 'Finalizing' >5 min")
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_processing_status()
