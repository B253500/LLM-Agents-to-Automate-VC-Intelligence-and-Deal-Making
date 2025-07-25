import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

def web_search_business_model_context(company_name):
    # Placeholder: Integrate EXA, Perplexity, or other API here
    # Return a string with web search results
    return ""

SYSTEM = """
You are a VC analyst specializing in business model analysis.
Analyze the startup's materials and provide:
- A concise summary of the POTENTIAL business model based on available information
- Discussion of potential revenue streams, customer segments, go-to-market strategy, and scalability
- Any recent business model news or pivots (use web search context if available)
- Attribute sources where possible

IMPORTANT: Use tentative language and clearly indicate when you are making assumptions or interpretations.
- Use phrases like "appears to be", "seems to", "may be", "could be", "based on available information"
- Do not present assumptions as facts about current business model
- If information is limited, explicitly state what additional research is needed

Return a summary (3-6 sentences). If insufficient data, state what is missing.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Startup info:\n{context}\nWeb search context:\n{web_context}\n")
])

def run_business_model_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    context = full_text[:5000]
    web_context = web_search_business_model_context(profile.name)
    txt = llm.invoke(PROMPT.format(context=context, web_context=web_context)).content.strip()
    profile.business_model = txt
    return profile 