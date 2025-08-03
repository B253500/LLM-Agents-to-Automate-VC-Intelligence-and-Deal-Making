#!/usr/bin/env python3
"""
Test LLM executive extraction from team context
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_openai import ChatOpenAI
from chains.pitch_deck_chain import PROMPT

def test_llm_extraction():
    """Test LLM executive extraction from team context"""
    print("🔍 Testing LLM executive extraction from team context...")
    print("=" * 60)
    
    # Use the team context that we know contains executives
    team_context = """
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
    
    print(f"📄 Team context length: {len(team_context)} characters")
    print(f"📄 Team context:\n{team_context}")
    
    # Test the LLM extraction
    llm = ChatOpenAI(model="gpt-4", temperature=0.2)
    prompt = PROMPT.format(deck=team_context)
    response = llm.invoke(prompt)
    txt = response.content.strip()
    
    print(f"\n🤖 LLM Response:\n{txt}")
    
    # Try to extract JSON
    first, last = txt.find("{"), txt.rfind("}")
    if first != -1 and last != -1 and last > first:
        try:
            json_str = txt[first : last + 1]
            result = json.loads(json_str)
            
            print(f"\n✅ Successfully parsed JSON:")
            print(f"Company: {result.get('name', 'N/A')}")
            print(f"Executives: {result.get('executives', [])}")
            
            if result.get('executives'):
                print(f"\n📊 Found {len(result['executives'])} executives:")
                for i, exec_info in enumerate(result['executives'], 1):
                    print(f"  {i}. {exec_info.get('name', 'N/A')} - {exec_info.get('role', 'N/A')}")
            else:
                print(f"\n❌ No executives found in LLM response")
                
        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse JSON: {e}")
            print(f"JSON string: {json_str}")
    else:
        print(f"\n❌ No JSON found in LLM response")

if __name__ == "__main__":
    test_llm_extraction() 