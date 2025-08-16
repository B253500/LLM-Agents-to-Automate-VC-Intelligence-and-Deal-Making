from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path
import re

from core.schemas import StartupProfile
from chains.risk_assessment_chain import run_risk_assessment_chain
from typing import Optional
from chains.memo_synthesis_chain import run_risks_section_chain

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

# Text processing function moved to chains/risk_assessment_chain.py

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
[Write a comprehensive conclusion that includes: 1) Overall investment thesis and potential, 2) Key factors driving success, 3) Critical risks and challenges, 4) Strategic considerations for investors, 5) Final recommendation framework. Make this 4-5 sentences long with detailed analysis.]

CRITICAL INSTRUCTIONS:
- Do NOT include "Next Steps" or bullet points anywhere in the response
- Do NOT include any bullet points (•) anywhere in the response
- Use bold headers (**Key Strengths:**, **Key Weaknesses:**, etc.) for each section
- Make the conclusion comprehensive and detailed (4-5 sentences)
- Do NOT use numbered lists (1., 2., 3., etc.) - use bold headers instead

MEMO:
{memo_body}
"""
    discussion = llm.invoke(discussion_prompt).content.strip()
    
    # Clean up the discussion text
    # Remove any markdown headers (hashtags) from the start of lines
    discussion = re.sub(r'^#+\s*', '', discussion, flags=re.MULTILINE)
    
    # Remove any sentences before the first main section
    match = re.search(r'(Key Strengths[\s\S]*)', discussion, re.IGNORECASE)
    if match:
        discussion = match.group(1).lstrip()
    
    # Remove bullet points
    discussion = re.sub(r'^\s*•\s*', '', discussion, flags=re.MULTILINE)
    
    # Remove "Next Steps:" section and everything after it
    discussion = re.sub(r'\n\s*Next Steps:.*', '', discussion, flags=re.DOTALL | re.IGNORECASE)
    discussion = re.sub(r'\n\s*Next Steps.*', '', discussion, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert numbered lists to bold headers
    discussion = re.sub(r'^(\d+\.\s*)(Key Strengths|Key Weaknesses|Opportunities|Risks):', r'**\2:**', discussion, flags=re.MULTILINE)
    discussion = re.sub(r'^(\d+\.\s*)(Key Strengths|Key Weaknesses|Opportunities|Risks)$', r'**\2:**', discussion, flags=re.MULTILINE)
    
    # Ensure all section headers are bold (handle cases without numbers)
    discussion = re.sub(r'^(Key Strengths|Key Weaknesses|Opportunities|Risks):', r'**\1:**', discussion, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove duplicate "Conclusion:" headers
    discussion = re.sub(r'\n\s*Conclusion:\s*\n', '\n', discussion, flags=re.IGNORECASE)
    
    # Remove stray bullet points at the end
    discussion = re.sub(r'\n\s*•\s*$', '', discussion, flags=re.MULTILINE)
    
    # Move conclusion to right after Risks section
    # Find the end of the Risks section
    risks_match = re.search(r'(\*\*Risks:\*\*[\s\S]*?)(?=\n\*\*|$)', discussion, re.IGNORECASE)
    if risks_match:
        risks_section = risks_match.group(1)
        # Remove any existing conclusion from the end
        discussion = re.sub(r'\n\*\*Conclusion:\*\*.*', '', discussion, flags=re.DOTALL)
        # Add comprehensive conclusion right after risks
        discussion = discussion.replace(risks_section, risks_section + "\n\n**Conclusion:**\nThis investment opportunity presents a compelling case with both significant potential and notable risks that require careful consideration. The company demonstrates strong technological innovation and market positioning, with a clear competitive advantage in their core technology. However, several key risks must be carefully evaluated, including market adoption challenges, competitive pressures, and execution risks associated with scaling operations. The overall investment thesis hinges on the company's ability to execute its strategic vision while navigating the identified risks, requiring thorough due diligence on technical capabilities, market validation, and competitive landscape before making an investment decision.")
    else:
        # If no risks section found, add comprehensive conclusion at the end
        if '**Conclusion:**' not in discussion:
            discussion += "\n\n**Conclusion:**\nThis investment opportunity presents a compelling case with both significant potential and notable risks that require careful consideration. The company demonstrates strong technological innovation and market positioning, with a clear competitive advantage in their core technology. However, several key risks must be carefully evaluated, including market adoption challenges, competitive pressures, and execution risks associated with scaling operations. The overall investment thesis hinges on the company's ability to execute its strategic vision while navigating the identified risks, requiring thorough due diligence on technical capabilities, market validation, and competitive landscape before making an investment decision."
    
    return discussion


def run_risks_section_agent(profile: StartupProfile) -> str:
    """Run risks section analysis using the chain."""
    return run_risks_section_chain(profile)


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


def build_risk_assessment_agent(profile: StartupProfile, trace_id=None, evaluator: Optional[object] = None):
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
        # Run risk assessment with profile data
        updated = run_risk_assessment_chain(profile, evaluator=evaluator)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Flag risks, score overall risk, and provide a risk assessment summary for the startup.",
        agent=officer,
        expected_output="A detailed risk assessment report including risk flags, risk score, and mitigation suggestions.",
        callback=_callback,
    )
    return officer, task
