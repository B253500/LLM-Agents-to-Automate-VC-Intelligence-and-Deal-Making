from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path
from core.schemas import StartupProfile
from chains.technical_dd_chain import run_technical_dd_chain, run_technical_dd_chain_with_text

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
    
    lines = []
    
    # Add product specifications if available
    product_specs = getattr(profile, 'product_specifications', None)
    if product_specs and len(product_specs.strip()) > 50:
        lines.append("Product Technical Specifications")
        lines.append(product_specs)
        lines.append("")
    
    # Add technical specifications paragraph if we have meaningful tech stack info
    if tech_stack and len(tech_stack.strip()) > 50:
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
        # Remove hashtags only
        cleaned_tech_stack = re.sub(r'#+\s*[A-Za-z\s]+', '', cleaned_tech_stack)
        # Remove standalone bullet points that don't have content
        cleaned_tech_stack = re.sub(r'^\s*•\s*$', '', cleaned_tech_stack, flags=re.MULTILINE)
        # Remove bullet points at the beginning of lines that are followed by whitespace
        cleaned_tech_stack = re.sub(r'^\s*•\s+(?=\s|$)', '', cleaned_tech_stack, flags=re.MULTILINE)
        # Clean up extra whitespace and newlines
        cleaned_tech_stack = re.sub(r'\n\s*\n', '\n', cleaned_tech_stack)
        cleaned_tech_stack = cleaned_tech_stack.strip()
        
        if len(cleaned_tech_stack.split()) >= 20:
            lines.append("Technical Specifications")
            lines.append(cleaned_tech_stack)
            lines.append("")
    
    # Add product roadmap if available or generate a basic one based on tech maturity
    roadmap = getattr(profile, 'product_roadmap', None)
    if not roadmap and tech:
        # Generate a basic roadmap based on tech maturity
        if 'prototype' in tech.lower() or 'early' in tech.lower():
            roadmap = "Current Phase: Prototype development and initial testing. Next Phase: Beta testing with select partners. Future Phase: Commercial production and market launch."
        elif 'beta' in tech.lower() or 'testing' in tech.lower():
            roadmap = "Current Phase: Beta testing and partner validation. Next Phase: Pilot production and certification. Future Phase: Full commercial launch."
        elif 'production' in tech.lower() or 'commercial' in tech.lower():
            roadmap = "Current Phase: Commercial production and market deployment. Next Phase: Scale manufacturing and expand partnerships. Future Phase: Technology iteration and new product development."
        else:
            roadmap = "Product roadmap details require additional research to understand current development stage and future milestones."
    
    if roadmap:
        lines.append("Product Roadmap")
        lines.append(roadmap)
        lines.append("")
    
    # Add patent portfolio if available
    patent_portfolio = getattr(profile, 'patent_portfolio', None)
    if patent_portfolio and len(patent_portfolio.strip()) > 20:
        lines.append("Patent Portfolio")
        lines.append(patent_portfolio)
        lines.append("")
    
    # Add the narrative if available
    if narrative:
        lines.append(narrative.strip())
        lines.append("")
    
    # Add structured assessment bullets
    bullets = []
    
    # Technical feasibility assessment
    if tech and tech.lower() != 'n/a':
        bullets.append(f"• Technical Feasibility and Performance: {tech}")
    else:
        bullets.append("• Technical Feasibility and Performance: Assessment requires additional technical documentation and independent validation")
    
    # Moat analysis
    if moat and moat.strip():
        bullets.append(f"• Moat: {moat}")
    else:
        bullets.append("• Moat: Technology moat analysis requires deeper technical assessment and competitive positioning review")
    
    # Complexity assessment
    if complexity and complexity.strip():
        bullets.append(f"• Complexity: {complexity}")
    else:
        bullets.append("• Complexity: Technical complexity assessment needed based on product architecture and implementation requirements")
    
    # Security considerations
    if security and security.strip():
        bullets.append(f"• Security: {security}")
    else:
        bullets.append("• Security: Product safety, data protection, and IP security measures should be thoroughly evaluated")
    
    # Implementation details
    if implementation and implementation.strip():
        bullets.append(f"• Implementation: {implementation}")
    else:
        bullets.append("• Implementation: Detailed implementation roadmap and technical architecture review required")
    
    # Regulatory compliance
    if regulatory and regulatory.strip():
        bullets.append(f"• Regulatory: {regulatory}")
    else:
        bullets.append("• Regulatory: Compliance with industry standards, safety certifications, and regulatory requirements must be verified")
    
    # Testing and validation
    if testing and testing.strip():
        bullets.append(f"• Testing: {testing}")
    else:
        bullets.append("• Testing: Independent validation, performance testing, and certification processes should be reviewed")
    
    bullets.append("• Further technical due diligence is required, including independent validation of performance claims, cycle life, and safety")
    
    lines.extend(bullets)
    
    # Final cleanup: remove any remaining standalone bullet points
    result = '\n'.join(lines)
    import re
    # Remove lines that are just bullet points
    result = re.sub(r'^\s*•\s*$', '', result, flags=re.MULTILINE)
    # Remove bullet points at the beginning of lines with no content
    result = re.sub(r'^\s*•\s+(?=\s*$)', '', result, flags=re.MULTILINE)
    # Clean up extra whitespace
    result = re.sub(r'\n\s*\n', '\n\n', result)
    result = result.strip()
    
    return result


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
        # Try to get full text from the profile if available
        full_text = getattr(profile, '_full_text', None)
        if full_text:
            # Use the full text version for better patent and roadmap extraction
            updated = run_technical_dd_chain_with_text(full_text, profile)
        else:
            # Fall back to hybrid context
            updated = run_technical_dd_chain(profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Analyze tech stack, rate maturity, summarize moat, and assess technology risks.",
        agent=ctto,
        expected_output="A detailed technical due diligence report including tech maturity, moat strength, and risks.",
        callback=_callback,
    )
    return ctto, task
