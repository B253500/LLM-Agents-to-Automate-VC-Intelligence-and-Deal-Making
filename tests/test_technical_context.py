#!/usr/bin/env python3
"""
Test script to examine what context the technical DD agent receives
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import StartupProfile
from agents.technical_dd_agent import build_technical_dd_agent

def test_technical_context():
    """Test what context the technical DD agent receives"""
    
    # Create a mock profile with some technical data
    profile_data = {
        "name": "StoreDot",
        "sector": "Battery Technology",
        "website": "https://storedot.com",
        "TAM": 160.0,
        "patent_count": 15,
        "energy_density_wh_kg": 300,
        "cycle_life_count": 1000,
        "technical_maturity": "Early-stage prototype",
        "moat_strength": "Moderate",
        "complexity": "High",
        "security": "Standard battery safety protocols",
        "implementation": "Manufacturing partnerships with 15+ OEMs",
        "regulatory": "EV battery safety standards compliance",
        "testing": "Ongoing validation with automotive partners"
    }
    
    profile = StartupProfile(**profile_data)
    
    # Add some mock context data to simulate what the agent would receive
    mock_full_text = """
    StoreDot is developing extreme fast charging (XFC) battery technology for electric vehicles.
    The company's technology enables charging to 100 miles of range in just 5 minutes.
    Technical specifications include energy density of 300 Wh/kg and cycle life of 1000 cycles.
    The company has 15 patents and is testing with over 15 OEM partners.
    Manufacturing partnerships are in place for commercial scale production by 2025.
    The technology uses proprietary solid-state electrolyte materials.
    Safety testing includes automotive industry standard protocols.
    Regulatory compliance focuses on EV battery safety standards.
    The technical maturity is early-stage prototype with ongoing validation.
    """
    
    # Set the context that the agent would receive
    profile._full_text = mock_full_text
    profile.extracted_data_context = mock_full_text
    
    print("🔍 Testing Technical DD Agent Context")
    print("=" * 50)
    
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
        print(f"   - Context preview: {profile.extracted_data_context[:200]}...")
    
    elif hasattr(profile, '_full_text') and profile._full_text:
        context_size = len(profile._full_text)
        print(f"   - _full_text size: {context_size} characters")
        print(f"   - Estimated tokens: {context_size // 4} tokens")
        print(f"   - Context preview: {profile._full_text[:200]}...")
    
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
    print(f"   - Context tokens: ~{len(mock_full_text) // 4}")
    print(f"   - Agent processing: Up to {agent.max_iter} iterations")
    print(f"   - Chain processing: Additional LLM calls")
    print(f"   - Total estimated: 10,000+ tokens for full PDF")
    
    print(f"\n✅ Test completed successfully!")

if __name__ == "__main__":
    test_technical_context() 