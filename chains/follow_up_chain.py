import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

def web_search_follow_up_context(company_name):
    # Placeholder: Integrate EXA, Perplexity, or other API here
    # Return a string with web search results
    return ""

SYSTEM = """
You are a VC analyst preparing for investment committee.
Based on the startup's materials, generate a list of actionable, critical follow-up questions and next steps for due diligence. Focus on areas where information is missing, ambiguous, or critical for decision-making. Use web search context if available.
Return a concise bullet-point list. If all information is clear, state 'No follow-up questions.'
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Startup info:\n{context}\nWeb search context:\n{web_context}\n")
])

def run_follow_up_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    context = full_text[:5000]
    web_context = web_search_follow_up_context(profile.name)
    txt = llm.invoke(PROMPT.format(context=context, web_context=web_context)).content.strip()
    profile.follow_up_questions = txt
    return profile 