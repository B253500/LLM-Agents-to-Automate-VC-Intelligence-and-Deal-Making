#!/usr/bin/env python3
"""
Real test of Mermaid rendering with actual external service calls
"""

import os
import sys
import time
import requests
import base64

# Add the project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_real_mermaid_services():
    """Test actual Mermaid rendering with real external services."""
    
    print("🌐 Testing Real Mermaid External Services")
    print("=" * 60)
    
    # Test diagram
    test_code = """graph TD
    StoreDot --> Licensing_Fees
    StoreDot --> Direct_Sales
    StoreDot --> Partnerships
    Licensing_Fees --> Automotive_Manufacturers
    Direct_Sales --> Consumer_Electronics
    Partnerships --> Industrial_Firms"""
    
    print(f"📊 Test diagram:")
    print(f"```mermaid\n{test_code}\n```")
    print()
    
    # Test 1: Kroki.io
    print("1️⃣ Testing Kroki.io Service")
    print("-" * 40)
    
    start_time = time.time()
    try:
        headers = {'Content-Type': 'text/plain'}
        resp = requests.post('https://kroki.io/mermaid/png', 
                           data=test_code.encode('utf-8'), 
                           headers=headers, 
                           timeout=5)
        
        if resp.status_code == 200:
            print(f"✅ Kroki.io working - rendered in {time.time() - start_time:.2f}s")
            print(f"📏 Response size: {len(resp.content)} bytes")
        else:
            print(f"❌ Kroki.io failed - status {resp.status_code}")
            print(f"📝 Error: {resp.text[:200]}")
            
    except requests.exceptions.Timeout:
        print(f"⏰ Kroki.io timeout after {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"❌ Kroki.io error: {e}")
    
    # Test 2: Mermaid.ink
    print("\n2️⃣ Testing Mermaid.ink Service")
    print("-" * 40)
    
    start_time = time.time()
    try:
        encoded = base64.b64encode(test_code.encode('utf-8')).decode('utf-8')
        resp = requests.get(f"https://mermaid.ink/img/{encoded}", timeout=5)
        
        if resp.status_code == 200:
            print(f"✅ Mermaid.ink working - rendered in {time.time() - start_time:.2f}s")
            print(f"📏 Response size: {len(resp.content)} bytes")
        else:
            print(f"❌ Mermaid.ink failed - status {resp.status_code}")
            print(f"📝 Error: {resp.text[:200]}")
            
    except requests.exceptions.Timeout:
        print(f"⏰ Mermaid.ink timeout after {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"❌ Mermaid.ink error: {e}")
    
    # Test 3: Local fallback generation
    print("\n3️⃣ Testing Local Fallback Generation")
    print("-" * 40)
    
    from main import generate_simple_mermaid_diagram
    
    # Create a mock profile
    class MockProfile:
        def __init__(self):
            self.name = "StoreDot"
            self.revenue_streams = "licensing fees, direct sales, partnerships"
            self.customer_segments = "automotive manufacturers, consumer electronics, industrial firms"
            self.business_model = "B2B battery technology licensing and sales"
    
    profile = MockProfile()
    
    start_time = time.time()
    try:
        fallback_diagram = generate_simple_mermaid_diagram("StoreDot", profile=profile)
        print(f"✅ Local fallback generated in {time.time() - start_time:.2f}s")
        print(f"📊 Generated diagram:")
        print(f"```mermaid\n{fallback_diagram}\n```")
    except Exception as e:
        print(f"❌ Local fallback failed: {e}")
    
    # Test 4: Performance summary
    print("\n4️⃣ Performance Summary")
    print("-" * 40)
    
    print("🎯 What happens when external services fail:")
    print("   • System tries Kroki.io (5s timeout)")
    print("   • If that fails, tries Mermaid.ink (5s timeout)")
    print("   • If both fail, uses local fallback (instant)")
    print("   • Total max time: ~10 seconds")
    print()
    print("🚀 For fastest processing:")
    print("   • Set SKIP_MERMAID=true environment variable")
    print("   • Skips external services entirely")
    print("   • Shows diagrams as text (instant)")

if __name__ == "__main__":
    test_real_mermaid_services() 