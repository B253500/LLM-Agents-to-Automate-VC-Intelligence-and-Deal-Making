#!/usr/bin/env python3
"""
Test script to see what the LLM is actually returning for technical analysis
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.technical_dd_chain import PROMPT, llm, clean_llm_output

def test_llm_output():
    """Test what the LLM is actually returning for technical analysis"""
    
    # Load the extracted StoreDot document
    with open('extraction_cache/storedot.pdf_70f0efbe04165831c2d2b807ff7d3227ce6f59d2.json', 'r') as f:
        data = json.load(f)
    
    text = data['text']
    context = text[:8000]  # Same as in the chain
    
    print("=" * 80)
    print("LLM OUTPUT TEST")
    print("=" * 80)
    print(f"Context length: {len(context)} characters")
    print(f"Context preview: {context[:500]}...")
    print()
    
    # Clean the context as done in the chain
    clean_context = context.replace('"', "'").replace('\n', ' ').strip()
    
    print("Sending to LLM...")
    try:
        txt = llm.invoke(PROMPT.format(context=clean_context)).content.strip()
        print("✅ LLM call successful")
        print(f"Raw LLM output length: {len(txt)} characters")
        print(f"Raw LLM output preview: {txt[:500]}...")
        print()
        
        # Try to clean the output
        data = clean_llm_output(txt)
        if data:
            print("✅ JSON parsing successful")
            print("Parsed data:")
            for key, value in data.items():
                print(f"  {key}: {value}")
        else:
            print("❌ JSON parsing failed")
            print("Raw output that failed to parse:")
            print(txt)
            
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_output() 