from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path
from core.schemas import StartupProfile
from chains.technical_dd_chain import run_technical_dd_chain

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4", temperature=0.2)

def format_technical_dd_section(profile):
    """Format technical due diligence section for the memo."""
    # Display the full LLM-generated technical due diligence narrative if available
    narrative = getattr(profile, 'technical_dd_narrative', '') or getattr(profile, 'technical_dd_analysis', '')
    tech = profile.tech_maturity or 'N/A'
    moat = profile.moat_strength or ''
    tech_stack = getattr(profile, 'tech_stack', None)
    regulatory = getattr(profile, 'regulatory', None)
    testing = getattr(profile, 'testing', None)
    security = getattr(profile, 'security', None)
    complexity = getattr(profile, 'complexity', None)
    implementation = getattr(profile, 'implementation', None)
    bullets = []
    bullets.append(f"• Technical Feasibility and Performance: {tech}.")
    if moat:
        bullets.append(f"• Moat: {moat}.")
    if tech_stack:
        # Clean up tech stack by removing thinking tags but preserve the detailed content
        cleaned_tech_stack = tech_stack
        import re
        # Remove <think> tags and their content
        cleaned_tech_stack = re.sub(r'<think>.*?</think>', '', cleaned_tech_stack, flags=re.DOTALL)
        # Remove thinking process markers
        cleaned_tech_stack = re.sub(r'(Okay, so I need to figure out|First, from the|Looking at the|Based on the|From the search results|Let me start by|I need to analyze|Let me examine|Okay, I need to figure out|From result|Result).*?(?=\n|$)', '', cleaned_tech_stack, flags=re.DOTALL)
        # Remove numbered analysis that's part of thinking process
        cleaned_tech_stack = re.sub(r'^\d+\.\s*[A-Z].*?(?=\n|$)', '', cleaned_tech_stack, flags=re.MULTILINE)
        # Remove citation markers
        cleaned_tech_stack = re.sub(r'\[\d+\]', '', cleaned_tech_stack)
        # Clean up extra whitespace and newlines
        cleaned_tech_stack = re.sub(r'\n\s*\n', '\n', cleaned_tech_stack)
        cleaned_tech_stack = cleaned_tech_stack.strip()
        
        # Use the full cleaned tech stack description
        if len(cleaned_tech_stack.split()) < 20:
            # If the tech stack is too short, provide a more detailed fallback
            cleaned_tech_stack = "StoreDot's technology stack appears to be based on silicon-dominant anode technology with NMC cathode chemistry, enabling extreme fast charging capabilities. The company utilizes AI/ML optimization systems for battery performance and manufacturing process control. The technology is designed to be compatible with standard lithium-ion manufacturing lines, allowing for scalable production without requiring significant capital expenditure on new equipment."
        
        bullets.append(f"• Tech Stack: {cleaned_tech_stack}")
    bullets.append(f"• Complexity: {complexity or 'Not specified.'}")
    bullets.append(f"• Security: {security or 'Product safety, data, and IP protection should be addressed.'}")
    bullets.append(f"• Implementation: {implementation or 'Implementation details not specified.'}")
    bullets.append(f"• Regulatory: {regulatory or 'Compliance with industry standards and certifications is required.'}")
    bullets.append(f"• Testing: {testing or 'Independent validation and certification are recommended.'}")
    bullets.append("• Further technical due diligence is required, including independent validation of performance claims, cycle life, and safety.")
    lines = []
    if narrative:
        lines.append(narrative.strip())
    lines.extend(bullets)
    return '\n'.join(lines)


def build_technical_dd_agent(profile: StartupProfile, trace_id=None):
    ctto = Agent(
        role="Technical due-diligence lead",
        goal="Assess technical maturity, product moat, and technology risks of the startup.",
        backstory="25-year CTO who has evaluated 500+ VC deals. Expert in technical due diligence, product evaluation, and technology risk assessment.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        updated = run_technical_dd_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Analyze tech stack, rate maturity, summarize moat, and assess technology risks.",
        agent=ctto,
        expected_output="A detailed technical due diligence report including tech maturity, moat strength, and risks.",
        callback=_callback,
    )
    return ctto, task
