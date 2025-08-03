#!/usr/bin/env python3
"""
Test team context extraction from Monzo PDF
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.pitch_deck_chain import get_smart_team_context

def test_team_context_extraction():
    """Test team context extraction from Monzo PDF text"""
    print("🔍 Testing team context extraction from Monzo PDF...")
    print("=" * 60)
    
    # Use the actual extracted text from the Monzo PDF (from the output we saw)
    pdf_text = """
Tom Blomfield
Chief Executive Officer
Tom was previously co-founder
of GoCardless, the payment
processor. He was named one
of the Top & Entrepreneurs
in Europe by the European
Commission in 2013.
Paul Rippon
Deputy CEO & Co-Founder
Paul has 23 years of retail
banking experience, looking
after millions of customers at
Lloyds, AIB and Natwest. He
lectures in Banking Practice at
the ifs.
Gary Dolman
CFO & Co-Founder
Gary was previously the CFO of
ABN AMRO Transaction Banking
overseeing a turnover of $5bn.
He is a qualified chartered
accountant
Jonas Huckstein
CTO & Co-Founder
Jonas graduated from university
at the age of 18, and has founded
several Silicon Valley-based
startups. He's a Combinator
alumnus.
Patrick Masera
Chief Operating Officer
Patrick has 20 years of
experience in retail banking
operations, previously holding
the role of Retail Operations
Director at Lloyds Banking
Group
Ole Mahrt
Head of Product
Ole was previously Product
Manager at Skype, where he
launched the video calling
product globally. He has also
held positions at Lulu and
CitySocialising
Ian Wilson
Chief Risk Officer
lan is a career risk management
professional with 35 years of
experience. Most recently lan
was CRO of Charter Savings
Bank.
Baroness Denise Kingsmill
Chairman of the Board
Denise was previously the
deputy chair of the Competition
Commission enquiry into
Banking and Senior Advisor to
ROS
Tim Brooke
Non-Executive Director
Tim has held senior business
leadership roles at JPMorgan
Chase 5 Co and PwC and
how continues his corporate
contribution as a NED for
a diverse range of large
companies.
Eileen Burbidge
Investor Director
Eileen is a partner at Passion
Capital and Fintech Enway for
HM Treasury. She has held
product roles at Yahool, Skype.
and Apple
"""
    
    print(f"📄 Original PDF text length: {len(pdf_text)} characters")
    print(f"📄 First 500 characters: {pdf_text[:500]}...")
    
    # Extract team context
    team_context = get_smart_team_context(pdf_text)
    
    print(f"\n🎯 Team context length: {len(team_context)} characters")
    print(f"🎯 Team context:\n{team_context}")
    
    # Check if key executives are in the team context
    key_executives = ["Tom Blomfield", "Paul Rippon", "Gary Dolman", "Jonas Huckstein"]
    found_executives = []
    
    for exec_name in key_executives:
        if exec_name in team_context:
            found_executives.append(exec_name)
            print(f"✅ Found {exec_name} in team context")
        else:
            print(f"❌ Missing {exec_name} in team context")
    
    print(f"\n📊 Summary: Found {len(found_executives)}/{len(key_executives)} executives in team context")

if __name__ == "__main__":
    test_team_context_extraction() 