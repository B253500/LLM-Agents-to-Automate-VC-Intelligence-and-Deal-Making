#!/usr/bin/env python3
"""
Test script to verify problem statement and solution overview length
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.memo_synthesis_chain import run_problem_statement_chain, run_solution_overview_chain
from core.schemas import StartupProfile

def test_problem_solution_length():
    """Test that problem statement and solution overview generate 4-5 sentences."""
    
    # Create a test profile
    profile = StartupProfile(
        name="StoreDot",
        sector="Battery Technology",
        product_description="Fast-charging battery technology for electric vehicles",
        funding_stage="Series C",
        business_model="B2B partnerships with automotive manufacturers",
        go_to_market="Strategic partnerships with OEMs"
    )
    
    print("Testing Problem Statement length...")
    print("=" * 50)
    
    try:
        problem_statement = run_problem_statement_chain(profile)
        sentences = problem_statement.split('.')
        # Filter out empty sentences and count
        sentence_count = len([s.strip() for s in sentences if s.strip()])
        
        print(f"Problem Statement ({sentence_count} sentences):")
        print(problem_statement)
        print()
        
        if 4 <= sentence_count <= 5:
            print("✅ PASS: Problem statement has 4-5 sentences")
        else:
            print(f"❌ FAIL: Problem statement has {sentence_count} sentences (expected 4-5)")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\nTesting Solution Overview length...")
    print("=" * 50)
    
    try:
        solution_overview = run_solution_overview_chain(profile)
        sentences = solution_overview.split('.')
        # Filter out empty sentences and count
        sentence_count = len([s.strip() for s in sentences if s.strip()])
        
        print(f"Solution Overview ({sentence_count} sentences):")
        print(solution_overview)
        print()
        
        if 4 <= sentence_count <= 5:
            print("✅ PASS: Solution overview has 4-5 sentences")
        else:
            print(f"❌ FAIL: Solution overview has {sentence_count} sentences (expected 4-5)")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\nExpected behavior:")
    print("- Both Problem Statement and Solution Overview should be exactly 4-5 sentences")
    print("- Content should be comprehensive and relevant to the company")
    
    return True

if __name__ == "__main__":
    test_problem_solution_length() 