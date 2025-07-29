#!/usr/bin/env python3
"""
Test script to examine the real context the technical DD agent receives
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import StartupProfile
from agents.technical_dd_agent import build_technical_dd_agent
from core.hybrid_context import get_hybrid_context

def test_real_technical_context():
    """Test what context the technical DD agent receives from real PDF data"""
    
    # Create a mock profile with StoreDot data
    profile_data = {
        "name": "StoreDot",
        "sector": "Battery Technology",
        "website": "https://storedot.com",
        "TAM": 160.0,
        "patent_count": 100,  # 78 granted + 22 pending
        "energy_density_wh_kg": 330,
        "cycle_life_count": 1000,
        "technical_maturity": "Early-stage prototype",
        "moat_strength": "Strong",
        "complexity": "High",
        "security": "Transport safety certified (UN38.3)",
        "implementation": "Manufacturing partnerships with 15+ OEMs",
        "regulatory": "EV battery safety standards compliance",
        "testing": ">1000 consecutive XFC cycles validated"
    }
    
    profile = StartupProfile(**profile_data)
    
    # Simulate the real PDF text that would be extracted
    real_pdf_text = """
    StoreDot Extreme Fast Charging Battery Technology for EV Mass Adoption
    
    XFC TECHNOLOGY HIGHLIGHTS
    StoreDot's XFC Silicon Battery - a highly differentiated solution for any electric vehicle
    Silicon-dominant anode, Proprietary additives and cell design, Manufactured in standard production facilities
    
    Technical Specifications:
    - Energy density: 330 Wh/kg net, 740 Wh/L net
    - Cycle life: >1000 consecutive XFC cycles with no degradation
    - Charging speed: 100 miles in 5 minutes (100in5)
    - Temperature performance: 76% discharge capacity @ -20°C
    - Power performance: 92% discharge capacity @ 3C
    
    Patent Portfolio:
    - 78 US granted and allowed patents
    - 22 US pending patents
    - Coverage: Anodes, Cathodes, Electrolytes, Binders, Separators, Production processes, Systems
    
    Manufacturing & Scale:
    - Production readiness: Commercially ready in 2025
    - Manufacturing: Standard Li-ion manufacturing lines (drop-in compatible)
    - Partnerships: >15 OEMs and manufacturing partners worldwide
    - Form factors: Pouch, Prismatic, Cylindrical (21700, 46XX)
    
    Technology Differentiation:
    - Silicon-dominant anode (vs graphite)
    - Proprietary additives and cell design
    - Holistic solution: Chemistry + Cell Design + System
    - 3-5 years lead on alternative solutions
    
    Performance Claims:
    - >50% reduction in charging time
    - No battery degradation due to extreme fast charging
    - Consistent charging rate regardless of state of charge
    - Superior to current fast charging solutions
    
    Testing & Validation:
    - 30Ah EV form factor proven solution
    - >1000 consecutive XFC cycles (10%-80% in 10 minutes)
    - High energy cell with >300Wh/kg
    - Transport safety certified (UN38.3 PASSED)
    
    Competitive Advantages:
    - Currently available fast charging: OEMs sacrifice battery cycle-life for fast charging
    - StoreDot's extreme fast charging: Game changer - drivers can fast charge every time
    - >1000 consecutive XFC - extreme fast charges with no degradation
    """
    
    # Set the context that the agent would receive
    profile._full_text = real_pdf_text
    profile.extracted_data_context = real_pdf_text
    
    print("🔍 Testing Real Technical DD Agent Context")
    print("=" * 60)
    
    # Build the agent
    agent, task = build_technical_dd_agent(profile)
    
    print(f"📊 Agent Configuration:")
    print(f"   - Role: {agent.role}")
    print(f"   - Goal: {agent.goal}")
    print(f"   - Max Iterations: {agent.max_iter}")
    print(f"   - Max Execution Time: {agent.max_execution_time}s")
    print(f"   - Verbose: {agent.verbose}")
    
    print(f"\n📋 Task Description:")
    print(f"   - Description: {task.description}")
    print(f"   - Expected Output: {task.expected_output}")
    
    print(f"\n📄 Context Analysis:")
    print(f"   - Has extracted_data_context: {hasattr(profile, 'extracted_data_context') and profile.extracted_data_context}")
    print(f"   - Has _full_text: {hasattr(profile, '_full_text') and profile._full_text}")
    
    if hasattr(profile, 'extracted_data_context') and profile.extracted_data_context:
        context_size = len(profile.extracted_data_context)
        print(f"   - extracted_data_context size: {context_size} characters")
        print(f"   - Estimated tokens: {context_size // 4} tokens")
        print(f"   - Context preview: {profile.extracted_data_context[:300]}...")
    
    elif hasattr(profile, '_full_text') and profile._full_text:
        context_size = len(profile._full_text)
        print(f"   - _full_text size: {context_size} characters")
        print(f"   - Estimated tokens: {context_size // 4} tokens")
        print(f"   - Context preview: {profile._full_text[:300]}...")
    
    print(f"\n🔧 Profile Technical Data:")
    technical_fields = [
        'technical_maturity', 'moat_strength', 'complexity', 'security',
        'implementation', 'regulatory', 'testing', 'energy_density_wh_kg',
        'cycle_life_count', 'patent_count'
    ]
    
    for field in technical_fields:
        value = getattr(profile, field, None)
        if value:
            print(f"   - {field}: {value}")
    
    print(f"\n💡 Token Consumption Analysis:")
    print(f"   - Context tokens: ~{len(real_pdf_text) // 4}")
    print(f"   - Agent processing: Up to {agent.max_iter} iterations")
    print(f"   - Chain processing: Additional LLM calls")
    print(f"   - Total estimated: 15,000+ tokens for full PDF")
    
    print(f"\n🔍 Context Quality Assessment:")
    
    # Check for key technical information in context
    key_technical_terms = [
        "energy density", "cycle life", "charging speed", "patent",
        "manufacturing", "silicon", "testing", "temperature",
        "power performance", "degradation", "safety", "certification"
    ]
    
    context_lower = real_pdf_text.lower()
    found_terms = []
    missing_terms = []
    
    for term in key_technical_terms:
        if term in context_lower:
            found_terms.append(term)
        else:
            missing_terms.append(term)
    
    print(f"   - Found technical terms: {', '.join(found_terms)}")
    print(f"   - Missing technical terms: {', '.join(missing_terms)}")
    
    print(f"\n📈 Context Improvement Suggestions:")
    print(f"   1. Include specific performance metrics (Wh/kg, cycle count)")
    print(f"   2. Add patent portfolio details (granted vs pending)")
    print(f"   3. Include manufacturing partnerships and scale")
    print(f"   4. Add competitive positioning vs alternatives")
    print(f"   5. Include regulatory compliance status")
    print(f"   6. Add testing and validation results")
    
    print(f"\n✅ Test completed successfully!")

if __name__ == "__main__":
    test_real_technical_context() 