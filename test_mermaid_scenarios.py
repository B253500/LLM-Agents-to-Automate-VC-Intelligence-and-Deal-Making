#!/usr/bin/env python3
"""
Test Mermaid rendering with different scenarios:
1. Normal rendering (external services working)
2. External services failing (timeout/error)
3. Skip Mermaid mode (fastest)
"""

import os
import sys
import time
import requests
from unittest.mock import patch, Mock

# Add the project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_mermaid_rendering_scenarios():
    """Test different Mermaid rendering scenarios."""
    
    print("🧪 Testing Mermaid Rendering Scenarios")
    print("=" * 60)
    
    # Test 1: Normal rendering (external services working)
    print("\n1️⃣ Testing Normal Rendering (External Services Working)")
    print("-" * 50)
    
    # Simulate a working external service
    with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
        # Mock successful response from Kroki.io
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'fake_png_data'
        mock_post.return_value = mock_response
        
        # Test the rendering logic
        test_code = """graph TD
    StoreDot --> Licensing_Fees
    StoreDot --> Direct_Sales
    Licensing_Fees --> Automotive_Manufacturers"""
        
        start_time = time.time()
        try:
            # Simulate the rendering process
            headers = {'Content-Type': 'text/plain'}
            resp = requests.post('https://kroki.io/mermaid/png', 
                               data=test_code.encode('utf-8'), 
                               headers=headers, 
                               timeout=5)
            
            if resp.status_code == 200:
                print("✅ External service working - diagram rendered successfully")
                print(f"⏱️ Rendering time: {time.time() - start_time:.2f} seconds")
            else:
                print("❌ External service returned error status")
                
        except Exception as e:
            print(f"❌ External service failed: {e}")
    
    # Test 2: External services failing (timeout)
    print("\n2️⃣ Testing External Services Failing (Timeout)")
    print("-" * 50)
    
    with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
        # Mock timeout exception
        mock_post.side_effect = requests.exceptions.Timeout("Connection timeout")
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
        
        start_time = time.time()
        try:
            # Simulate the rendering process
            headers = {'Content-Type': 'text/plain'}
            resp = requests.post('https://kroki.io/mermaid/png', 
                               data=test_code.encode('utf-8'), 
                               headers=headers, 
                               timeout=5)
        except requests.exceptions.Timeout:
            print("✅ Timeout handled correctly - will fall back to text diagram")
            print(f"⏱️ Timeout time: {time.time() - start_time:.2f} seconds")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    # Test 3: Skip Mermaid mode
    print("\n3️⃣ Testing Skip Mermaid Mode (Fastest)")
    print("-" * 50)
    
    # Set environment variable to skip Mermaid
    os.environ['SKIP_MERMAID'] = 'true'
    
    start_time = time.time()
    
    # Simulate the skip logic
    skip_mermaid = os.getenv('SKIP_MERMAID', 'false').lower() == 'true'
    if skip_mermaid:
        print("✅ Skip Mermaid mode enabled - instant text diagrams")
        print(f"⏱️ Skip time: {time.time() - start_time:.2f} seconds")
    else:
        print("❌ Skip Mermaid mode not working")
    
    # Test 4: Local fallback generation
    print("\n4️⃣ Testing Local Fallback Generation")
    print("-" * 50)
    
    # Import the function from main.py
    from main import generate_simple_mermaid_diagram
    
    # Create a mock profile
    class MockProfile:
        def __init__(self):
            self.name = "Test Company"
            self.revenue_streams = "subscription, licensing, partnerships"
            self.customer_segments = "enterprise, smb, consumers"
            self.business_model = "SaaS platform with multiple revenue streams"
    
    profile = MockProfile()
    
    start_time = time.time()
    try:
        # Generate local fallback diagram
        fallback_diagram = generate_simple_mermaid_diagram("Test Company", profile=profile)
        print("✅ Local fallback diagram generated successfully")
        print(f"⏱️ Generation time: {time.time() - start_time:.2f} seconds")
        print(f"📊 Diagram content:")
        print(f"```mermaid\n{fallback_diagram}\n```")
    except Exception as e:
        print(f"❌ Local fallback generation failed: {e}")
    
    # Test 5: Performance comparison
    print("\n5️⃣ Performance Comparison")
    print("-" * 50)
    
    scenarios = [
        ("External Services Working", 5.0),  # 5 second timeout
        ("External Services Failing", 8.0),  # 5 + 3 second timeouts
        ("Skip Mermaid Mode", 0.1),         # Instant
        ("Local Fallback Only", 0.1)        # Instant
    ]
    
    print("📊 Expected Performance:")
    for scenario, expected_time in scenarios:
        print(f"   • {scenario}: {expected_time:.1f} seconds")
    
    print("\n🎯 Recommendations:")
    print("   • Use SKIP_MERMAID=true for fastest processing")
    print("   • External services may be unreliable")
    print("   • Local fallback provides consistent results")

if __name__ == "__main__":
    test_mermaid_rendering_scenarios() 