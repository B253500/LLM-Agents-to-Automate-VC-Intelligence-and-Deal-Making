"""
LangChain chain that:
1. Reads a PDF pitch-deck
2. Prompts GPT-4o-mini to extract key metadata
3. Returns a validated `StartupProfile`
"""

from hashlib import sha1
from pathlib import Path
import json

import pdfplumber
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.vector_store import add_doc

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # loads OPENAI_API_KEY
LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

SYSTEM = (
    "You are a VC analyst. Extract the following JSON keys from the text: {keys}. "
    "Return ONLY valid JSON."
)
HUMAN = "Pitch-deck text (truncated to 5 000 characters):\n```markdown\n{deck}\n```"
PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", HUMAN)])


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def pdf_to_text(path: Path) -> str:
    """Concatenate text from every page of a PDF."""
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages)


# ---------------------------------------------------------------------
# Main chain function
# ---------------------------------------------------------------------
def run_pitch_deck_chain(pdf_path: str) -> StartupProfile:
    # 1  Extract raw text from the PDF (truncate to keep token-cost down)
    deck = pdf_to_text(Path(pdf_path))[:5000]

    # 2  Build and invoke the prompt
    keys = list(StartupProfile.model_fields.keys())[:6]  # basic subset
    prompt = PROMPT.format(keys=", ".join(keys), deck=deck)
    response = LLM.invoke(prompt)
    txt = response.content.strip()

    # 3  Robust JSON extraction: grab text between first `{` and last `}`
    first_curly, last_curly = txt.find("{"), txt.rfind("}")
    if first_curly == -1 or last_curly == -1 or last_curly < first_curly:
        raise ValueError("No JSON object found in LLM response")
    json_str = txt[first_curly : last_curly + 1]
    raw = json.loads(json_str)

    # 4  Unwrap {"StartupProfile": {...}} if the model nested it
    if "StartupProfile" in raw and isinstance(raw["StartupProfile"], dict):
        raw = raw["StartupProfile"]

    # 5  Validate into Pydantic model (startup_id may still be None)
    profile = StartupProfile(**raw)

    # 6  Ensure `name` exists (fallback to alt keys)
    if profile.name is None:
        for alt in ("CompanyName", "company_name", "Company"):
            if isinstance(raw.get(alt), str) and raw[alt].strip():
                profile.name = raw[alt].strip()
                break

    # 7  Compute deterministic ID (hash name or deck text)
    src_for_hash = profile.name if profile.name else deck[:40]
    profile.startup_id = sha1(src_for_hash.encode()).hexdigest()[:10]

    # 8  Persist deck text to Chroma for later RAG
    add_doc(profile.startup_id, deck)

    return profile
