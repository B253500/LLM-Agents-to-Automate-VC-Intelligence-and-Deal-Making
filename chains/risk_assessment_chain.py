"""
Risk-assessment chain
Aggregates red-flags across all profile fields and provides deterministic text processing.
"""

import json
import re
from pathlib import Path
from hashlib import sha1

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

SYSTEM = """\
You are an investment-risk officer specializing in startup risk assessment.
Analyze the startup profile and identify potential risk factors.

Return JSON with:
  risk_flags – array of short risk descriptions (≤5 words each)
  risk_summary – brief summary of key risks

Consider factors like:
- Market size and competition
- Team experience and track record
- Financial health and runway
- Technology maturity
- Regulatory risks
- Market timing

If insufficient data to assess risks, set risk_flags to empty array.
Note: Do not provide a numerical risk score as it would be unreliable without clear methodology.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Profile:\n```json\n{profile}\n```")]
)


def deduplicate_and_paraphrase(text, min_phrase_len=3, max_allowed=2):
    """
    Deduplicate and paraphrase repeated phrases in text.
    - Finds repeated phrases (sequences of min_phrase_len+ words).
    - If a phrase occurs more than max_allowed times, paraphrase extra occurrences.
    - Keeps the first occurrence as-is.
    """
    # Find all phrases of min_phrase_len+ words
    words = text.split()
    phrase_counts = {}
    phrase_locs = {}
    for i in range(len(words) - min_phrase_len + 1):
        phrase = ' '.join(words[i:i+min_phrase_len])
        phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        phrase_locs.setdefault(phrase, []).append(i)
    # Only process phrases that occur more than max_allowed times
    for phrase, count in phrase_counts.items():
        if count > max_allowed:
            # Paraphrase all but the first occurrence
            locs = phrase_locs[phrase][1:]
            for loc in locs:
                # Find the phrase in the text and paraphrase it
                pattern = re.escape(phrase)
                matches = list(re.finditer(pattern, text))
                if len(matches) > 1:
                    match = matches[1]  # Paraphrase the second occurrence
                    start, end = match.start(), match.end()
                    # Use LLM to paraphrase
                    paraphrase_prompt = f"Paraphrase this phrase to mean the same thing but with different words: '{phrase}'"
                    try:
                        paraphrased = llm.invoke(paraphrase_prompt).content.strip()
                        text = text[:start] + paraphrased + text[end:]
                    except:
                        pass  # Keep original if paraphrasing fails
    return text


def run_risk_assessment_chain(profile: StartupProfile) -> StartupProfile:
    # Truncate profile data if it's too large to avoid context length exceeded
    profile_json = profile.model_dump_json()
    if len(profile_json) > 10000:  # If profile is very large, use a summary
        # Create a simplified profile with key fields only
        simplified_profile = {
            "name": profile.name,
            "sector": profile.sector,
            "funding_stage": profile.funding_stage,
            "TAM": profile.TAM,
            "revenue": profile.revenue,
            "top_competitors": profile.top_competitors[:3] if profile.top_competitors else None,  # Limit competitors
            "executives": profile.executives[:5] if profile.executives else None  # Limit executives
        }
        profile_json = json.dumps(simplified_profile)
    
    txt = llm.invoke(PROMPT.format(profile=profile_json)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        profile.risk_flags = data.get("risk_flags", [])
        # Note: risk_score is intentionally not set as it's unreliable without clear methodology
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or "risk").encode()).hexdigest()[:10]
    return profile

def run_risk_assessment_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    """Run risk assessment using extracted text as context."""
    context = full_text[:5000]  # Truncate if needed for prompt size
    # Use the same prompt but replace the profile with the context
    txt = llm.invoke(PROMPT.format(profile=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        profile.risk_flags = data.get("risk_flags", [])
        # Note: risk_score is intentionally not set as it's unreliable without clear methodology
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or "risk").encode()).hexdigest()[:10]
    return profile
