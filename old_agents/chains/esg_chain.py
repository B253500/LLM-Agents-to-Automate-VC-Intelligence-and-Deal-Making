import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)

def web_search_esg_context(company_name):
    # Placeholder: Integrate EXA, Perplexity, or other API here
    # Return a string with web search results
    return ""

SYSTEM = """
You are an ESG (Environmental, Social, Governance) analyst for venture capital deals.
Analyze the startup's materials and provide:
- A concise summary of key ESG considerations
- Discussion of sustainability, social impact, governance, and regulatory alignment
- Any recent ESG news or controversies (use web search context if available)
- Attribute sources where possible
Return a summary (3-6 sentences). If insufficient data, state what is missing.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Startup info:\n{context}\nWeb search context:\n{web_context}\n")
])

def run_esg_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    context = full_text[:5000]
    web_context = web_search_esg_context(profile.name)
    txt = llm.invoke(PROMPT.format(context=context, web_context=web_context)).content.strip()
    profile.esg_summary = txt
    return profile 