"""
Founder-profiling chain
• Looks up founder data (mocked in tests)
• Returns founder_fit_score (0–1) & prior_exits (int)
"""

import json
from hashlib import sha1
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.vector_store import query_doc

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

SYSTEM = """\
You are an experienced VC partner evaluating founders.
Return JSON with two keys:
  founder_fit_score  – float between 0 and 1 (higher = stronger team)
  prior_exits        – integer count of successful past exits
If info is missing, default to 0.3 and 0.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Founder info:\n{context}\n")]
)


# ------------------------------------------------------------------
def run_founder_profiling_chain(profile: StartupProfile) -> StartupProfile:
    context_snips = query_doc(
        profile.startup_id, "founder background or biography", k=4
    )
    context = "\n---\n".join(context_snips) or "No founder info provided."

    raw = llm.invoke(PROMPT.format(context=context)).content.strip()

    # Robust JSON slice
    first, last = raw.find("{"), raw.rfind("}")
    json_str = raw[first : last + 1]
    data = json.loads(json_str)

    profile.founder_fit_score = float(data.get("founder_fit_score", 0.3))
    profile.prior_exits = int(data.get("prior_exits", 0))

    if not profile.startup_id:
        src = profile.name or context[:40]
        profile.startup_id = sha1(src.encode()).hexdigest()[:10]

    return profile
