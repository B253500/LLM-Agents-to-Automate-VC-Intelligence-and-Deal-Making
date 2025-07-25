from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path
import re

from core.schemas import StartupProfile
from chains.risk_assessment_chain import run_risk_assessment_chain

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

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

def generate_discussion_section(memo_body: str) -> str:
    """Generate AI discussion and commentary section."""
    discussion_prompt = f"""
You are a senior VC analyst. Based on the following investment memo, provide a critical discussion and analyst commentary. Structure your response with clear sections:

**Key Strengths:**
[List 3-4 key strengths with brief explanations]

**Key Weaknesses:**
[List 3-4 key weaknesses or concerns]

**Opportunities:**
[List 3-4 market opportunities]

**Risks:**
[List 3-4 key risks]

**Conclusion:**
[Write a clear, concise conclusion paragraph that summarizes the investment opportunity and key considerations]

MEMO:
{memo_body}
"""
    discussion = llm.invoke(discussion_prompt).content.strip()
    
    # Clean up the discussion text
    # Remove any markdown headers (hashtags) from the start of lines
    discussion = re.sub(r'^#+\s*', '', discussion, flags=re.MULTILINE)
    
    # Ensure proper section formatting
    discussion = re.sub(r'^(Key Strengths|Key Weaknesses|Opportunities|Risks|Conclusion):', r'**\1:**', discussion, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove any sentences before the first main section
    match = re.search(r'(Key Strengths[\s\S]*)', discussion, re.IGNORECASE)
    if match:
        discussion = match.group(1).lstrip()
    
    # Ensure conclusion is properly formatted
    if '**Conclusion:**' not in discussion:
        # Add conclusion if missing
        discussion += "\n\n**Conclusion:**\nBased on the analysis above, this investment opportunity presents both significant potential and notable risks that require careful consideration."
    
    return discussion

def generate_counterfactual_section(profile: StartupProfile) -> str:
    """Generate counterfactual analysis section."""
    # Compose system message
    system_msg = (
        "You are a senior VC analyst. "
        "Write a concise, neutral paragraph assessing the opportunity cost of NOT investing. "
        "Avoid promotional language; focus on market, competitive and strategic implications."
    )
    # Compose extra note for revenue
    revenue = getattr(profile, "revenue", None)
    if not revenue:
        extra_note = "Note: The company is pre-revenue; base the analysis on traction proxies (e.g. pilots, wait-lists, LOIs)."
    else:
        extra_note = f"Trailing 12-month revenue: {revenue}"
    # Format competitors
    competitors = getattr(profile, "top_competitors", None)
    if isinstance(competitors, list):
        competitors_str = ", ".join([c.get("name", "") for c in competitors if isinstance(c, dict) and c.get("name")])
        if not competitors_str:
            competitors_str = "None highlighted"
    else:
        competitors_str = str(competitors) if competitors else "None highlighted"
    # Prepare context
    ctx = {
        "name": getattr(profile, "name", "Unknown"),
        "sector": getattr(profile, "sector", "Unknown"),
        "stage": getattr(profile, "funding_stage", "Unknown"),
        "tam": getattr(profile, "TAM", "Unspecified"),
        "competitors": competitors_str,
        "extra_note": extra_note
    }
    # Compose user message
    user_msg = (
        f"Company: {ctx['name']}\n"
        f"Sector: {ctx['sector']}\n"
        f"Stage: {ctx['stage']}\n"
        f"Market size (TAM): {ctx['tam']}\n"
        f"Top competitors: {ctx['competitors']}\n"
        f"{ctx['extra_note']}"
    )
    try:
        response = llm.invoke(
            [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ]
        )
        return response.content.strip() if hasattr(response, 'content') else str(response)
    except Exception as e:
        return f"[Counterfactual section could not be generated: {e}]"


def build_risk_assessment_agent(profile: StartupProfile, trace_id=None):
    officer = Agent(
        role="Risk-assessment officer",
        goal="Identify red-flags, compute risk score, and assess overall risk profile of the startup.",
        backstory="Former credit-risk VP now in VC. Expert in risk modeling, red-flag detection, and startup risk assessment.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        updated = run_risk_assessment_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Flag risks, score overall risk, and provide a risk assessment summary for the startup.",
        agent=officer,
        expected_output="A detailed risk assessment report including risk flags, risk score, and mitigation suggestions.",
        callback=_callback,
    )
    return officer, task
