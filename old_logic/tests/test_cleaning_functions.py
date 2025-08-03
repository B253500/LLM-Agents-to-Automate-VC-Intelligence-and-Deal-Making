#!/usr/bin/env python3
"""
Test script to see what cleaning functions are doing to content
"""

import sys
import os
import re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import clean_think_tags_and_debugging

def clean(text):
    """Clean up text by removing hashtags, special markers, and normalizing formatting."""
    if not isinstance(text, str):
        return text
    # Removing hashtags only
    text = re.sub(r'#+\s*[A-Za-z\s]+', '', text)
    # Removing extra whitespace and normalising line breaks
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

def test_cleaning_functions():
    """Test what the cleaning functions do to sample content."""
    
    # Sample problem statement (4-5 sentences as requested)
    sample_problem_statement = """The global demand for efficient and sustainable energy storage solutions is intensifying, driven by the rapid growth of electric vehicles (EVs) and renewable energy sources. Current lithium-ion battery technology faces significant limitations in charging speed, with most EVs requiring 30-60 minutes for an 80% charge, creating a major barrier to widespread adoption. The automotive industry is under increasing pressure to meet stricter emissions regulations while consumers demand faster charging times and longer range capabilities. Additionally, the existing battery supply chain is heavily dependent on rare earth materials and faces geopolitical risks, while current manufacturing processes are energy-intensive and environmentally challenging."""
    
    # Sample solution overview (4-5 sentences as requested)
    sample_solution_overview = """StoreDot addresses these critical challenges through its innovative fast-charging battery technology that can charge electric vehicles in just 5 minutes. The company's proprietary silicon-dominant anode technology enables significantly faster charging speeds while maintaining high energy density and long cycle life. This breakthrough technology eliminates range anxiety and charging time concerns that have hindered EV adoption, making electric vehicles as convenient as traditional gasoline-powered cars. StoreDot's solution also reduces dependency on rare earth materials through its innovative chemistry, while its scalable manufacturing process supports the automotive industry's transition to sustainable mobility."""
    
    print("Testing cleaning functions on sample content...")
    print("=" * 60)
    
    print("\n1. ORIGINAL Problem Statement:")
    print("-" * 40)
    print(sample_problem_statement)
    print(f"\nSentence count: {len([s.strip() for s in sample_problem_statement.split('.') if s.strip()])}")
    
    print("\n2. AFTER clean() function:")
    print("-" * 40)
    cleaned_problem = clean(sample_problem_statement)
    print(cleaned_problem)
    print(f"\nSentence count: {len([s.strip() for s in cleaned_problem.split('.') if s.strip()])}")
    
    print("\n3. AFTER clean_think_tags_and_debugging() function:")
    print("-" * 40)
    final_problem = clean_think_tags_and_debugging(cleaned_problem)
    print(final_problem)
    print(f"\nSentence count: {len([s.strip() for s in final_problem.split('.') if s.strip()])}")
    
    print("\n" + "=" * 60)
    
    print("\n4. ORIGINAL Solution Overview:")
    print("-" * 40)
    print(sample_solution_overview)
    print(f"\nSentence count: {len([s.strip() for s in sample_solution_overview.split('.') if s.strip()])}")
    
    print("\n5. AFTER clean() function:")
    print("-" * 40)
    cleaned_solution = clean(sample_solution_overview)
    print(cleaned_solution)
    print(f"\nSentence count: {len([s.strip() for s in cleaned_solution.split('.') if s.strip()])}")
    
    print("\n6. AFTER clean_think_tags_and_debugging() function:")
    print("-" * 40)
    final_solution = clean_think_tags_and_debugging(cleaned_solution)
    print(final_solution)
    print(f"\nSentence count: {len([s.strip() for s in final_solution.split('.') if s.strip()])}")
    
    print("\n" + "=" * 60)
    print("\nAnalysis:")
    print("- If sentence counts decrease, the cleaning functions are removing content")
    print("- If sentence counts stay the same, the cleaning functions are working correctly")
    print("- The goal is to maintain 4-5 sentences in both sections")
    
    return True

if __name__ == "__main__":
    test_cleaning_functions() 