import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

SYSTEM = """
You are a VC analyst specializing in exit strategies.
Analyze the startup's materials and summarize potential exit scenarios, including likely acquirers, IPO potential, and recommended exit strategies and timelines.
Return a concise summary (3-6 sentences). If insufficient data, state what is missing.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Startup info:\n{context}\n")
])

def run_exit_strategy_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    context = full_text[:5000]
    txt = llm.invoke(PROMPT.format(context=context)).content.strip()
    profile.exit_strategy = txt
    return profile 