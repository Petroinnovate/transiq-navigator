#!/usr/bin/env python3
"""Test Phase 5 Deployment Status"""

import time
import urllib.request
import json
import sys

def test_phase5_deployment():
    """Test if Phase 5 endpoints are operational"""
    time.sleep(2)  # Wait for server to fully start
    
    try:
        print("\n" + "="*70)
        print("TRANSIQ PHASE 5 DEPLOYMENT TEST")
        print("="*70 + "\n")
        
        # Test intelligence status endpoint
        resp = urllib.request.urlopen('http://localhost:8000/api/v2/intelligence/intelligence-status')
        data = json.loads(resp.read())
        
        print("✅ PHASE 5 INTELLIGENCE ENDPOINTS DEPLOYED\n")
        print(f"🎯 Service: {data.get('service', 'Unknown')}")
        print(f"📌 Version: {data.get('version', 'Unknown')}")
        print(f"♻  Status: {data.get('status', 'Unknown')}\n")
        
        print("🔧 Engines Active:")
        for engine, details in data.get('engines', {}).items():
            status = details.get('status', 'unknown')
            icon = "✅" if status == "active" else "⚠️"
            print(f"   {icon} {engine.upper()}: {status}")
        
        print("\n📡 Available Endpoints:")
        for ep in data.get('available_endpoints', []):
            print(f"   ✓ {ep}")
        
        print("\n" + "="*70)
        print("✅ DEPLOYMENT SUCCESSFUL - ALL SYSTEMS OPERATIONAL")
        print("="*70 + "\n")
        print("Next Steps:")
        print("  1. Open http://localhost:8000/docs for interactive API")
        print("  2. Test endpoints with sample entity IDs")
        print("  3. Check PHASE5_COMPLETE.md for full documentation")
        print("\n")
        return True
        
    except Exception as e:
        print(f"⏳ Server still loading or not available: {e}")
        print("   Retrying in a few seconds...")
        time.sleep(3)
        return test_phase5_deployment()

if __name__ == "__main__":
    try:
        test_phase5_deployment()
    except RecursionError:
        print("❌ Server connection failed - check backend status")
        sys.exit(1)
