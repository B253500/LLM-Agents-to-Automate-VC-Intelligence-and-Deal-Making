import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

SYSTEM = """
You are a senior CTO performing technical due diligence for venture capital investment.
For the given company, provide a detailed, critical analysis of the technology, including:
- Technical feasibility and performance (with specific strengths and weaknesses)
- Scalability and architecture
- Integration complexity and dependencies
- Security and data protection risks
- Regulatory and compliance issues
- Implementation complexity and testing requirements
- Assumption risks and dependencies
- What needs to be validated or further investigated
Structure your answer with subheadings and bullet points for each area. Be specific, critical, and highlight both strengths and weaknesses. If information is missing, note it explicitly.
Return a detailed, multi-paragraph, multi-bullet analysis suitable for a VC investment memo.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Startup info:\n{context}\n")]
)


def run_technical_dd_chain(profile: StartupProfile) -> StartupProfile:
    context = get_hybrid_context(
        profile, "technology stack OR product OR patents OR infrastructure", 3, 3
    )
    txt = llm.invoke(PROMPT.format(context=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        # Flatten dicts if needed
        if isinstance(data.get("tech_maturity"), dict):
            data["tech_maturity"] = str(data["tech_maturity"])
        if isinstance(data.get("moat_strength"), dict):
            data["moat_strength"] = str(data["moat_strength"])
        
        # Only set values if they are not null/None
        if data.get("tech_maturity") is not None:
            profile.tech_maturity = data.get("tech_maturity")
        if data.get("moat_strength") is not None:
            profile.moat_strength = data.get("moat_strength")
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[
            :10
        ]
    return profile

def run_technical_dd_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    """Run technical due diligence using extracted text as context."""
    context = full_text[:5000]  # Truncate if needed for prompt size
    txt = llm.invoke(PROMPT.format(context=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        # Flatten dicts if needed
        if isinstance(data.get("tech_maturity"), dict):
            data["tech_maturity"] = str(data["tech_maturity"])
        if isinstance(data.get("moat_strength"), dict):
            data["moat_strength"] = str(data["moat_strength"])
        # Only set values if they are not null/None
        if data.get("tech_maturity") is not None:
            profile.tech_maturity = data.get("tech_maturity")
        if data.get("moat_strength") is not None:
            profile.moat_strength = data.get("moat_strength")
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile
