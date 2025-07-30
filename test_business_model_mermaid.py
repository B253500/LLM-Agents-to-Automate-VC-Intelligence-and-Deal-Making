#!/usr/bin/env python3
"""
Test business model chain Mermaid generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.schemas import StartupProfile
from chains.memo_synthesis_chain import run_business_model_chain

def test_business_model_mermaid():
    """Test if the business model chain generates correct Mermaid syntax."""
    
    # Create a test profile
    profile = StartupProfile()
    profile.name = "Test Company"
    profile.business_model = "SaaS subscription model with licensing fees"
    profile.revenue_streams = "subscription, licensing, partnerships"
    profile.customer_segments = "enterprise, smb, consumers"
    
    print("🧪 Testing Business Model Chain Mermaid Generation")
    print("=" * 60)
    
    try:
        # Run the business model chain
        result = run_business_model_chain(profile)
        print(f"✅ Business model chain completed successfully")
        
        # Check if it contains Mermaid diagram
        if "```mermaid" in result:
            print("✅ Mermaid diagram found in output")
            
            # Extract the Mermaid code
            import re
            mermaid_match = re.search(r'(```mermaid[\s\S]+?```)', result)
            if mermaid_match:
                diagram = mermaid_match.group(1)
                print(f"\n📋 Generated Mermaid Diagram:")
                print("-" * 40)
                print(diagram)
                print("-" * 40)
                
                # Check for syntax issues
                if ';' in diagram and 'graph TD' in diagram:
                    print("⚠️  WARNING: Found semicolons in diagram - this might cause rendering issues")
                else:
                    print("✅ No syntax issues detected")
                
                # Test the cleaning logic
                cleaned = diagram.replace(';', '\n')
                if cleaned != diagram:
                    print("✅ Syntax cleaning would fix issues")
                else:
                    print("✅ No syntax cleaning needed")
                    
            else:
                print("❌ No Mermaid diagram found in output")
        else:
            print("❌ No Mermaid diagram found in output")
            
    except Exception as e:
        print(f"❌ Error running business model chain: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Business Model Test Complete!")

if __name__ == "__main__":
    test_business_model_mermaid() 