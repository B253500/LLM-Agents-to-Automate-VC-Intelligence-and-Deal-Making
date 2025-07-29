from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path
from core.schemas import StartupProfile
from chains.technical_dd_chain import run_technical_dd_chain, run_technical_dd_chain_with_text
# Import format_technical_dd_section at the top to avoid local variable errors
# (If this is the same file, this import is not needed)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

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
    
    # Enhanced technical data extraction from profile
    energy_density = getattr(profile, 'energy_density_wh_kg', None)
    cycle_life = getattr(profile, 'cycle_life_count', None)
    patent_count = getattr(profile, 'patent_count', None)
    cell_format = getattr(profile, 'cell_format', None)
    energy_density_source = getattr(profile, 'energy_density_source', None)
    cycle_life_source = getattr(profile, 'cycle_life_source', None)
    
    # Extract additional technical specs from structured data
    if hasattr(profile, 'structured_data') and profile.structured_data:
        structured_data = profile.structured_data
        if isinstance(structured_data, dict):
            # Extract technical specifications from structured data
            if not energy_density and 'energy_density' in structured_data:
                energy_density = structured_data['energy_density']
                energy_density_source = 'enhanced_extraction'
            if not cycle_life and 'cycle_life' in structured_data:
                cycle_life = structured_data['cycle_life']
                cycle_life_source = 'enhanced_extraction'
            if not patent_count and 'patents' in structured_data:
                patent_count = structured_data['patents']
    
    # Add product specifications if available
    product_specs = getattr(profile, 'product_specifications', None)
    if product_specs and len(product_specs.strip()) > 50:
        lines.append("**Product Technical Specifications**")
        lines.append("")
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
            lines.append("**Technical Specifications**")
            lines.append("")
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
        lines.append("**Product Roadmap**")
        lines.append("")
        lines.append(roadmap)
        lines.append("")
    
    # Add patent portfolio if available
    patent_portfolio = getattr(profile, 'patent_portfolio', None)
    if patent_portfolio and len(patent_portfolio.strip()) > 5:
        lines.append("**Patent Portfolio**")
        lines.append("")
        lines.append(patent_portfolio)
        lines.append("")
    
    # Enhanced technical specifications display
    bullets = []
    
    # Display enhanced technical specifications if available
    if hasattr(profile, 'energy_density_wh_kg') and profile.energy_density_wh_kg:
        bullets.append(f"• Energy Density: {profile.energy_density_wh_kg} Wh/kg")
    
    if hasattr(profile, 'volumetric_energy_density') and profile.volumetric_energy_density:
        bullets.append(f"• Volumetric Energy Density: {profile.volumetric_energy_density} Wh/L")
    
    if hasattr(profile, 'cycle_life_count') and profile.cycle_life_count:
        bullets.append(f"• Cycle Life: {profile.cycle_life_count} consecutive XFC cycles")
    
    # Enhanced patent information
    if hasattr(profile, 'patent_portfolio') and profile.patent_portfolio:
        if hasattr(profile, 'granted_patents') and hasattr(profile, 'pending_patents'):
            bullets.append(f"• Patent Portfolio: {profile.granted_patents} US granted and {profile.pending_patents} US pending patents")
        else:
            bullets.append(f"• Patent Portfolio: {profile.patent_portfolio}")
    
    # Enhanced charging specifications
    charging_speed_miles = getattr(profile, 'charging_speed_miles', None)
    charging_speed_minutes = getattr(profile, 'charging_speed_minutes', None)
    if charging_speed_miles and charging_speed_minutes:
        bullets.append(f"• Charging Speed: {charging_speed_miles} miles in {charging_speed_minutes} minutes")
    elif charging_speed_miles:
        bullets.append(f"• Charging Speed: {charging_speed_miles} miles")
    
    # Enhanced temperature and power performance
    low_temp_performance = getattr(profile, 'low_temp_performance', None)
    if low_temp_performance:
        bullets.append(f"• Low Temperature Performance: {low_temp_performance}")
    
    power_performance = getattr(profile, 'power_performance', None)
    if power_performance:
        bullets.append(f"• Power Performance: {power_performance}")
    
    # Enhanced cell specifications
    cell_capacity = getattr(profile, 'cell_capacity', None)
    if cell_capacity:
        bullets.append(f"• Cell Capacity: {cell_capacity}Ah")
    
    cell_dimensions = getattr(profile, 'cell_dimensions', None)
    if cell_dimensions:
        bullets.append(f"• Cell Dimensions: {cell_dimensions}")
    
    # Enhanced team metrics
    employees_count = getattr(profile, 'employees_count', None)
    if employees_count:
        bullets.append(f"• Total Employees: {employees_count}")
    
    phds = getattr(profile, 'phds', None)
    if phds:
        bullets.append(f"• PhD Scientists: {phds}")
    
    # Enhanced manufacturing and partnerships
    oem_partners = getattr(profile, 'oem_partners', None)
    if oem_partners:
        bullets.append(f"• OEM Partners: Testing with {oem_partners} OEMs and manufacturing partners")
    
    safety_certifications = getattr(profile, 'safety_certifications', None)
    if safety_certifications:
        bullets.append(f"• Safety Certifications: {safety_certifications}")
    
    # Enhanced technology roadmap
    roadmap_100in_speed = getattr(profile, 'roadmap_100in_speed', None)
    roadmap_100in_year = getattr(profile, 'roadmap_100in_year', None)
    if roadmap_100in_speed and roadmap_100in_year:
        bullets.append(f"• Technology Roadmap: 100in{roadmap_100in_speed} by {roadmap_100in_year}")
    
    production_readiness = getattr(profile, 'production_readiness', None)
    if production_readiness:
        bullets.append(f"• Production Readiness: {production_readiness}")
    
    # Technical maturity
    if tech and tech != 'N/A':
        bullets.append(f"• Technical Maturity: {tech}")
    else:
        bullets.append("• Technical Maturity: Technical assessment unavailable")
    
    # Moat analysis
    if moat and moat.strip():
        bullets.append(f"• Moat Strength: {moat}")
    else:
        bullets.append("• Moat Strength: Moat analysis unavailable")
    
    # Complexity assessment
    if complexity and complexity.strip():
        bullets.append(f"• Complexity: {complexity}")
    else:
        bullets.append("• Complexity: Technical complexity assessment requires additional research")
    
    # Security considerations
    if security and security.strip():
        bullets.append(f"• Security: {security}")
    else:
        bullets.append("• Security: Security considerations require additional research")
    
    # Implementation details
    if implementation and implementation.strip():
        bullets.append(f"• Implementation: {implementation}")
    else:
        bullets.append("• Implementation: Implementation details require additional research")
    
    # Regulatory compliance
    if regulatory and regulatory.strip():
        bullets.append(f"• Regulatory: {regulatory}")
    else:
        bullets.append("• Regulatory: Regulatory compliance information requires additional research")
    
    # Testing and validation
    if testing and testing.strip():
        bullets.append(f"• Testing: {testing}")
    else:
        bullets.append("• Testing: Testing and validation information requires additional research")
    
    # Only add the bullets if we have meaningful technical data
    if bullets:
        lines.append("**Technical Assessment**")
        lines.append("")
        lines.extend(bullets)
        lines.append("")
    
    # Add the narrative if available and meaningful
    if narrative and len(narrative.strip()) > 100:
        # Clean the narrative
        import re
        cleaned_narrative = re.sub(r'<think>.*?</think>', '', narrative, flags=re.DOTALL)
        cleaned_narrative = re.sub(r'(Okay, so I need to figure out|First, from the|Looking at the|Based on the|From the search results|Let me start by|I need to analyze|Let me examine).*?(?=\n|$)', '', cleaned_narrative, flags=re.DOTALL)
        cleaned_narrative = cleaned_narrative.strip()
        
        if len(cleaned_narrative) > 100:
            lines.append("**Technical Analysis**")
            lines.append("")
            lines.append(cleaned_narrative)
            lines.append("")
    
    # Add conclusion only if we have some meaningful content
    if len(lines) > 0:
        lines.append("• Further technical due diligence is required, including independent validation of performance claims, cycle life, and safety")
    
    # Remove any duplicate lines
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    
    # If we have no meaningful content, provide a default message
    if len(unique_lines) == 0:
        return "Technical due diligence information requires additional research and independent validation of the company's technology claims, performance metrics, and development roadmap."
    
    return '\n'.join(unique_lines)


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
        # Use comprehensive extracted data context to capture all valuable technical information
        from core.hybrid_context import get_hybrid_context
        
        # Get comprehensive technical context
        full_text = ""
        if hasattr(profile, 'extracted_data_context') and profile.extracted_data_context:
            # Use comprehensive search within extracted data
            full_text = get_hybrid_context(profile, "technical analysis OR energy density OR cycle life OR battery technology OR technical specifications OR patents OR product roadmap OR manufacturing OR testing", use_reports=False)
        else:
            # Fallback to comprehensive hybrid context
            full_text = get_hybrid_context(profile, "technical analysis OR energy density OR cycle life OR battery technology OR technical specifications OR patents OR product roadmap OR manufacturing OR testing", use_reports=False)
        
        # Use the comprehensive context for technical analysis
        updated = run_technical_dd_chain_with_text(full_text, profile)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Analyze tech stack, rate maturity, summarize moat, and assess technology risks.",
        agent=ctto,
        expected_output="A detailed technical due diligence report including tech maturity, moat strength, and risks.",
        callback=_callback,
    )
    return ctto, task
