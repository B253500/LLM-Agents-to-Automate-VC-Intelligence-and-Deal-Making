#!/usr/bin/env python3
"""
Debug pipeline flow to trace where executives are getting lost
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chains.pitch_deck_chain import run_pitch_deck_chain_with_text
from chains.team_chain import run_team_chain
from core.schemas import StartupProfile

def debug_pipeline_flow():
    """Debug the pipeline flow to see where executives are getting lost"""
    print("🔍 Debugging pipeline flow...")
    print("=" * 60)
    
    # Use the actual extracted text from Monzo PDF
    deck_text = """
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
    
    print("📄 Step 1: Running pitch deck chain...")
    profile = StartupProfile()
    profile = run_pitch_deck_chain_with_text(deck_text, profile)
    
    print(f"📊 After pitch deck chain:")
    print(f"  - Company name: {profile.name}")
    print(f"  - Executives count: {len(profile.executives) if profile.executives else 0}")
    if profile.executives:
        for i, exec_info in enumerate(profile.executives, 1):
            print(f"    {i}. {exec_info.get('name', 'N/A')} - {exec_info.get('role', 'N/A')}")
    else:
        print("    ❌ No executives found!")
    
    print(f"\n📄 Step 2: Running team chain...")
    profile = run_team_chain(profile)
    
    print(f"📊 After team chain:")
    print(f"  - Company name: {profile.name}")
    print(f"  - Executives count: {len(profile.executives) if profile.executives else 0}")
    if profile.executives:
        for i, exec_info in enumerate(profile.executives, 1):
            print(f"    {i}. {exec_info.get('name', 'N/A')} - {exec_info.get('role', 'N/A')}")
            if exec_info.get('linkedin'):
                print(f"       LinkedIn: {exec_info.get('linkedin')}")
            if exec_info.get('background_summary'):
                print(f"       Background: {exec_info.get('background_summary')[:100]}...")
    else:
        print("    ❌ No executives found!")
    
    print(f"\n🎯 Summary:")
    print(f"  - Pitch deck chain found executives: {'✅' if profile.executives else '❌'}")
    print(f"  - Team chain preserved executives: {'✅' if profile.executives else '❌'}")

if __name__ == "__main__":
    debug_pipeline_flow() 