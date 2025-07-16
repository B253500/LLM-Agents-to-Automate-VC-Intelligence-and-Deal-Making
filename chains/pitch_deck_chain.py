import json
import re
import pdfplumber
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile
from core.vector_store import add_doc
from hashlib import sha1
from pathlib import Path

# Configurations

load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # loads OPENAI_API_KEY
llm = ChatOpenAI(model="gpt-4", temperature=0.2)

SYSTEM = """
You are a top-tier VC investment analyst. Extract the following fields as JSON:
- name
- founder_name
- sector
- website
- funding_stage
- executives: a list of ONLY the following roles if present: CEO/Founder, CFO (Chief Financial Officer), Chairman, CTO (Chief Technology Officer). For each, include name, role, LinkedIn if available, and a list of prior exits with company name and link if available.
If not explicitly stated, return "unknown". Do NOT hallucinate or infer.
Return ONLY valid JSON.
"""
HUMAN = "Pitch-deck text (first 5000 characters):\n```markdown\n{deck}\n```"
PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", HUMAN)])


# Helpers
def pdf_to_text(path: Path) -> str:
    """Concatenate text from every page of a PDF."""
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages)


def extract_common_term(text: str, pdf_path: str) -> str:
    # Uses regex to find frequent capitalized brand mentions
    matches = re.findall(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b", text)
    if matches:
        freq = {name: matches.count(name) for name in set(matches)}
        sorted_names = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        likely_term = sorted_names[0][0]
        # Avoids generic terms
        if likely_term.lower() in ["all", "company", "unknown"]:
            return Path(pdf_path).stem.replace("_", " ").replace("-", " ").title()
        return likely_term
    return Path(pdf_path).stem.replace("_", " ").replace("-", " ").title()


# Main chain function
def run_pitch_deck_chain_with_text(deck_text: str, profile: StartupProfile = None, pdf_path: str = None) -> StartupProfile:
    """Run pitch deck analysis using extracted text directly"""
    if profile is None:
        profile = StartupProfile()
    
    truncated_text = deck_text[:5000]

    prompt = PROMPT.format(deck=truncated_text)
    response = llm.invoke(prompt)
    txt = response.content.strip()

    # Extracts JSON from LLM output
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1 or last < first:
        print("[Warning] No JSON object found, falling back to extraction")
        fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf")
        profile.name = fallback_name
    else:
        try:
            json_str = txt[first : last + 1]
            raw = json.loads(json_str)

            if not raw.get("name") or raw.get("name").lower() in ["unknown", "all", "company"]:
                fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf")
                raw["name"] = fallback_name

            if (
                not raw.get("founder_name")
                or raw.get("founder_name").lower() == "unknown"
            ):
                raw["founder_name"] = "unknown"

            # Updates profile with extracted data
            for key, value in raw.items():
                if hasattr(profile, key) and value:
                    setattr(profile, key, value)
            # Explicitly handle executives if present
            if "executives" in raw and raw["executives"]:
                profile.executives = raw["executives"]
                # Collect all prior exits from executives
                prior_exit_details = []
                for exec in raw["executives"]:
                    if isinstance(exec, dict) and exec.get("prior_exits"):
                        for ex in exec["prior_exits"]:
                            prior_exit_details.append(ex)
                if prior_exit_details:
                    profile.prior_exit_details = prior_exit_details
        except Exception as e:
            print(f"[Error] Failed to parse LLM output: {e}")
            fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf")
            profile.name = fallback_name

    # Fallback if still missing
    if not profile.name or profile.name.lower() in ["unknown", "all", "company"]:
        fallback_name = extract_common_term(truncated_text, pdf_path or "unknown.pdf")
        profile.name = fallback_name

    # Assigns deterministic ID
    profile.startup_id = sha1(profile.name.encode()).hexdigest()[:10]

    # Stores the full deck in Chroma
    add_doc(profile.startup_id, deck_text)

    return profile

def extract_common_term_from_text(text: str, pdf_path: str) -> str:
    # Uses regex to find frequent capitalized brand mentions
    matches = re.findall(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b", text)
    if matches:
        freq = {name: matches.count(name) for name in set(matches)}
        sorted_names = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        likely_term = sorted_names[0][0]
        if likely_term.lower() in ["all", "company", "unknown"]:
            return ""
        return likely_term
    return ""

def run_pitch_deck_chain(pdf_path: str) -> StartupProfile:
    """Legacy function that extracts text from PDF and calls the text-based version"""
    deck_text = pdf_to_text(Path(pdf_path))
    return run_pitch_deck_chain_with_text(deck_text, pdf_path=pdf_path)
