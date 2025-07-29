#!/usr/bin/env python3
"""
Test script to verify business model section formatting works like main.py
"""

import os
import sys
import json
import re
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schemas import StartupProfile
from chains.business_model_chain import run_business_model_chain_with_text

def clean_think_tags_and_debugging(text):
    """Clean up text by removing think tags and debugging info (copied from main.py)"""
    if not isinstance(text, str):
        return text
    
    # Remove think tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    
    # Remove debugging info
    text = re.sub(r'\[DEBUG\].*?\n', '', text)
    text = re.sub(r'\[ERROR\].*?\n', '', text)
    text = re.sub(r'\[INFO\].*?\n', '', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    
    return text.strip()

def test_business_model_section():
    """Test business model section formatting like main.py"""
    
    print("🔄 Testing business model section generation...")
    
    # Create a mock profile like main.py would use
    profile_data = {
        "name": "StoreDot",
        "sector": "Battery Technology",
        "funding_stage": "Series D",
        "TAM": 160.0,
        "SAM": 48.0,
        "business_model": ""  # This will be populated by the chain
    }
    
    try:
        profile = StartupProfile(**profile_data)
    except Exception as e:
        print(f"❌ Failed to create StartupProfile: {e}")
        return
    
    print(f"✅ Created profile for: {profile.name}")
    
    # Generate business model section like main.py does
    print("🔄 Generating business model section...")
    
    # Simulate the full text that would be passed to the chain
    full_text = f"""
    Company: {profile.name}
    Sector: {profile.sector}
    Funding Stage: {profile.funding_stage}
    TAM: ${profile.TAM} billion
    SAM: ${profile.SAM} billion
    
    StoreDot is developing advanced battery technologies that enable ultra-fast charging for electric vehicles and consumer electronics. The company's proprietary technology allows batteries to charge in minutes rather than hours, addressing a key limitation of current lithium-ion batteries.
    """
    
    # Run business model chain like main.py
    try:
        updated_profile = run_business_model_chain_with_text(full_text, profile)
        business_model_text = updated_profile.business_model
        print("✅ Business model section generated successfully")
        print(f"📝 Content length: {len(business_model_text)} characters")
        print(f"📄 Content:\n{business_model_text}")
        
        # Test the formatting like main.py would do
        formatted_text = clean_think_tags_and_debugging(business_model_text)
        print(f"🧹 Cleaned content length: {len(formatted_text)} characters")
        print(f"🧹 Cleaned content:\n{formatted_text}")
        
        # Test that it's the right size (3-6 sentences as specified in the chain)
        sentences = formatted_text.split('.')
        sentence_count = len([s for s in sentences if s.strip()])
        print(f"📊 Sentence count: {sentence_count}")
        
        if 3 <= sentence_count <= 6:
            print("✅ Content size is within expected range (3-6 sentences)")
        else:
            print(f"⚠️ Content size ({sentence_count} sentences) is outside expected range (3-6 sentences)")
        
        # Test that the content is appropriate for business model section
        business_model_keywords = [
            "revenue", "customer", "market", "strategy", "partnership", 
            "licensing", "sales", "business", "model", "pricing"
        ]
        
        keyword_matches = sum(1 for keyword in business_model_keywords 
                            if keyword.lower() in formatted_text.lower())
        print(f"🔍 Business model keywords found: {keyword_matches}/{len(business_model_keywords)}")
        
        if keyword_matches >= 3:
            print("✅ Content contains appropriate business model terminology")
        else:
            print("⚠️ Content may be missing key business model elements")
        
    except Exception as e:
        print(f"❌ Error generating business model section: {e}")
        return
    
    print("✅ Business model section test completed successfully!")

if __name__ == "__main__":
    test_business_model_section() 