from hashlib import sha1
from pathlib import Path
import json
import re

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
llm = ChatOpenAI(model="gpt-4", temperature=0.2)

SYSTEM = """
You are a top-tier VC investment analyst. Extract the following fields as JSON:
- name
- founder_name
- sector
- website
- funding_stage
If not explicitly stated, return "unknown". Do NOT hallucinate or infer.
Return ONLY valid JSON.
"""
HUMAN = "Pitch-deck text (first 5000 characters):\n```markdown\n{deck}\n```"
PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", HUMAN)])


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def pdf_to_text(path: Path) -> str:
    """Concatenate text from every page of a PDF."""
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages)


def extract_common_term(text: str, pdf_path: str) -> str:
    # Use regex to find frequent capitalized brand mentions
    matches = re.findall(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b", text)
    if matches:
        freq = {name: matches.count(name) for name in set(matches)}
        sorted_names = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        likely_term = sorted_names[0][0]
        return likely_term
    return Path(pdf_path).stem.replace("_", " ").replace("-", " ").title()


# ---------------------------------------------------------------------
# Main chain function
# ---------------------------------------------------------------------
def run_pitch_deck_chain(pdf_path: str) -> StartupProfile:
    deck_text = pdf_to_text(Path(pdf_path))
    truncated_text = deck_text[:5000]

    prompt = PROMPT.format(deck=truncated_text)
    response = llm.invoke(prompt)
    txt = response.content.strip()

    # Extract JSON from LLM output
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1 or last < first:
        print("[Warning] No JSON object found, falling back to extraction")
        fallback_name = extract_common_term(truncated_text, pdf_path)
        profile = StartupProfile(name=fallback_name)
    else:
        try:
            json_str = txt[first : last + 1]
            raw = json.loads(json_str)

            if not raw.get("name") or raw.get("name").lower() == "unknown":
                raw["name"] = extract_common_term(truncated_text, pdf_path)

            if (
                not raw.get("founder_name")
                or raw.get("founder_name").lower() == "unknown"
            ):
                raw["founder_name"] = "unknown"

            profile = StartupProfile(**raw)
        except Exception as e:
            print(f"[Error] Failed to parse LLM output: {e}")
            fallback_name = extract_common_term(truncated_text, pdf_path)
            profile = StartupProfile(name=fallback_name)

    # Fallback if still missing
    if not profile.name or profile.name.lower() == "unknown":
        profile.name = extract_common_term(truncated_text, pdf_path)

    # Assign deterministic ID
    profile.startup_id = sha1(profile.name.encode()).hexdigest()[:10]

    # Store the full deck in Chroma
    add_doc(profile.startup_id, deck_text)

    return profile
