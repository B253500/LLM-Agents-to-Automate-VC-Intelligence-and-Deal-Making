import json
import re
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing import Optional
from core.llm_logging import log_usage_from_message
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

def get_smart_technical_context(text):
    """Extract technical-relevant sections from text and create a focused 10k summary"""
    import re
    
    # High-priority technical keywords (these get more context)
    high_priority_keywords = [
        'technology', 'tech stack', 'platform', 'architecture', 'infrastructure',
        'API', 'database', 'cloud', 'security', 'scalability', 'performance',
        'development', 'engineering', 'code', 'software', 'hardware', 'system'
    ]
    
    # Medium-priority keywords (product/development context)
    medium_priority_keywords = [
        'product', 'feature', 'development', 'roadmap', 'patent', 'intellectual property',
        'team', 'engineer', 'developer', 'CTO', 'technical', 'implementation',
        'integration', 'partnership', 'technology partner', 'vendor'
    ]
    
    # Find high-priority sections with more context
    high_priority_sections = []
    for keyword in high_priority_keywords:
        # Get more context around high-priority keywords (1000 chars each side)
        pattern = re.compile(rf'.{{0,1000}}{keyword}.{{0,1000}}', re.IGNORECASE)
        matches = pattern.findall(text)
        high_priority_sections.extend(matches)
    
    # Find medium-priority sections with less context
    medium_priority_sections = []
    for keyword in medium_priority_keywords:
        # Get less context around medium-priority keywords (500 chars each side)
        pattern = re.compile(rf'.{{0,500}}{keyword}.{{0,500}}', re.IGNORECASE)
        matches = pattern.findall(text)
        medium_priority_sections.extend(matches)
    
    # Combine all sections, prioritizing high-priority ones
    all_sections = high_priority_sections + medium_priority_sections
    
    # Remove duplicates while preserving order
    seen = set()
    unique_sections = []
    for section in all_sections:
        if section not in seen:
            seen.add(section)
            unique_sections.append(section)
    
    # Combine sections
    combined_context = '\n\n'.join(unique_sections)
    
    # If we don't have enough context, add strategic parts of the text
    if len(combined_context) < 5000:
        # Add the end of the text (where technical data often is)
        combined_context += '\n\n' + text[-8000:]  # Add last 8k chars
    
    # Limit to 10k chars total for efficiency
    return combined_context[:10000]

SYSTEM = """
You are a senior CTO performing technical due diligence for venture capital investment.
For the given company, provide a detailed, critical analysis of the technology.

IMPORTANT: Use tentative language and clearly indicate when you are making assumptions or interpretations. 
- Use phrases like "appears to be", "seems to", "may be", "could be", "based on available information"
- Do not present assumptions as facts
- If information is limited, explicitly state what additional research is needed

CRITICAL REQUIREMENTS:
1. CAREFULLY EXTRACT ALL PATENT INFORMATION from the provided context
2. CAREFULLY EXTRACT ALL PRODUCT ROADMAP INFORMATION from the provided context
3. CAREFULLY EXTRACT ALL PRODUCT TECHNICAL SPECIFICATIONS from the provided context
4. Look for specific patent numbers, filing dates, patent areas, and patent status
5. Look for development phases, milestones, timelines, and commercialization plans
6. Look for technical specifications, performance metrics, materials, dimensions, capabilities
7. If the context contains patent, roadmap, or technical specification information, USE IT - do not say "requires additional research"

TECH STACK REQUIREMENTS:
- Provide a detailed 3-4 sentence description of the technology stack
- Cover core technologies, infrastructure, and technical approach
- Include specific technologies, frameworks, or methodologies mentioned
- Be comprehensive but avoid speculation

PRODUCT TECHNICAL SPECIFICATIONS REQUIREMENTS:
- Extract and summarize all product technical specifications from the context
- Include performance metrics, materials, dimensions, capabilities, and key features
- Look for specific numbers, measurements, performance data, and technical parameters
- Cover sector-specific technical metrics (e.g., energy density for batteries, uptime for software, efficacy for biotech)
- Include any technical comparisons or benchmarks mentioned
- If technical specifications are present in the context, provide specific details

PRODUCT ROADMAP REQUIREMENTS:
- Extract and summarize any product development roadmap information from the context
- Include current phase, next milestones, and future development stages
- Focus on technical milestones and commercialization timeline
- If roadmap information is present in the context, provide specific details

PATENT ANALYSIS REQUIREMENTS:
- Extract and summarize any patent portfolio information from the context
- Include number of patents, key patent areas, and patent strength
- Look for specific patent numbers, filing dates, and patent descriptions
- Assess patent defensibility and potential for licensing revenue
- If patent information is present in the context, provide specific details

Return your analysis in the following JSON format:
{{
    "tech_maturity": "Brief assessment of technical maturity (e.g., 'Early-stage prototype', 'Production-ready', 'Lab-scale')",
    "moat_strength": "Assessment of technical moat and defensibility",
    "tech_stack": "Detailed description of the technology stack and architecture (3-4 sentences covering core technologies, infrastructure, and technical approach)",
    "product_specifications": "Detailed product technical specifications including performance metrics, materials, dimensions, capabilities, and key features (3-4 sentences with specific numbers and data)",
    "product_roadmap": "Brief product development roadmap with current phase and future milestones (2-3 sentences)",
    "patent_portfolio": "Assessment of patent portfolio including number of patents, key areas, and strength (2-3 sentences)",
    "complexity": "Assessment of technical complexity",
    "security": "Security considerations and risks",
    "implementation": "Implementation challenges and requirements",
    "regulatory": "Regulatory and compliance considerations",
    "testing": "Testing and validation requirements"
}}

Be specific, critical, and highlight both strengths and weaknesses. If information is missing, note it explicitly.
Focus on actionable insights for VC investment decision-making.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Startup info:\n{context}")]
)


def clean_llm_output(text):
    """Clean LLM output to extract valid JSON."""
    # Remove thinking output
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Keep B253500 tokens - don't remove them
    
    # Find JSON content
    first, last = text.find("{"), text.rfind("}")
    if first == -1 or last == -1:
        return None
    
    json_str = text[first:last + 1]
    
    # Clean up common JSON formatting issues
    json_str = json_str.strip()
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[Technical DD] JSON parsing error: {e}")
        print(f"[Technical DD] Raw JSON: {json_str[:200]}...")
        
        # Try to fix common JSON issues
        # Remove newlines and extra whitespace
        json_str = re.sub(r'\n\s*', ' ', json_str)
        json_str = re.sub(r'\s+', ' ', json_str)
        # Fix unquoted keys
        json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        # Fix unquoted string values
        json_str = re.sub(r':\s*([^",\{\}\[\]]+?)([,}\]])', r': "\1"\2', json_str)
        # Remove bullet points from string values
        json_str = re.sub(r'•\s*', '', json_str)
        # Fix trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e2:
            print(f"[Technical DD] Second JSON parsing error: {e2}")
            print(f"[Technical DD] Cleaned JSON: {json_str[:200]}...")
            return None


def extract_technical_specs_from_text(text: str) -> dict:
    """Extract technical specifications from document text using regex patterns."""
    import re
    
    specs = {}
    
    # Generic technical specification patterns that work for any sector
    technical_patterns = {
        'performance': [
            r'(\d+(?:\.\d+)?)\s*(wh|watt|wh/kg|wh/l|mhz|ghz|gb|mb|tb)',
            r'performance.*?(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?).*?performance',
            r'speed.*?(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?).*?speed',
        ],
        'capacity': [
            r'capacity.*?(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?).*?capacity',
            r'(\d+(?:\.\d+)?)\s*(gb|mb|tb|wh|ah)',
        ],
        'efficiency': [
            r'efficiency.*?(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?).*?efficiency',
            r'(\d+(?:\.\d+)?)\s*%',
        ],
        'accuracy': [
            r'accuracy.*?(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?).*?accuracy',
            r'(\d+(?:\.\d+)?)\s*%',
        ],
        'reliability': [
            r'reliability.*?(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?).*?reliability',
            r'uptime.*?(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?).*?uptime',
        ],
        'cycles': [
            r'cycle.*?life.*?(\d+(?:,\d+)?)',
            r'(\d+(?:,\d+)?).*?cycle.*?life',
            r'(\d+(?:,\d+)?)\s*cycles',
            r'>(\d+)\s*consecutive',
            r'(\d+)\s*consecutive.*?cycles',
        ],
        'time': [
            r'(\d+)\s*(min|minutes|sec|seconds|ms)',
            r'response.*?time.*?(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?).*?response.*?time',
        ],
        'temperature': [
            r'temperature.*?(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?).*?temperature',
            r'(\d+(?:\.\d+)?)\s*°[cf]',
        ]
    }
    
    # Extract technical specifications using generic patterns
    for spec_type, patterns in technical_patterns.items():
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                match = matches[0]
                if isinstance(match, tuple) and len(match) >= 2:
                    value, unit = match[0], match[1]
                    specs[f'{spec_type}_value'] = float(value)
                    specs[f'{spec_type}_unit'] = unit
                    break
                elif isinstance(match, str):
                    # Handle single value patterns
                    value = match.replace(',', '')
                    specs[f'{spec_type}_value'] = float(value)
                    break
    
    # Enhanced patent extraction (generic)
    granted_pattern = r'(\d+)\s*(us|patent).*?granted'
    pending_pattern = r'(\d+)\s*(us|patent).*?pending'
    
    granted_match = re.search(granted_pattern, text.lower())
    pending_match = re.search(pending_pattern, text.lower())
    
    if granted_match and pending_match:
        granted_count = int(granted_match.group(1))
        pending_count = int(pending_match.group(1))
        total_patents = granted_count + pending_count
        specs['patents'] = total_patents
        specs['granted_patents'] = granted_count
        specs['pending_patents'] = pending_count
        specs['patent_details'] = f"{granted_count} US granted and {pending_count} US pending patents"
    elif granted_match:
        specs['patents'] = int(granted_match.group(1))
        specs['granted_patents'] = int(granted_match.group(1))
    elif pending_match:
        specs['patents'] = int(pending_match.group(1))
        specs['pending_patents'] = int(pending_match.group(1))
    else:
        # Fallback to general patent patterns
        patent_patterns = [
            r'(\d+)\s*patents',
            r'patent.*?portfolio.*?(\d+)',
            r'(\d+).*?patent',
        ]
        for pattern in patent_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                specs['patents'] = int(matches[0])
                break
    
    # Generic charging/processing speed patterns
    speed_patterns = [
        r'(\d+)\s*(miles|km).*?(\d+)\s*(min|minutes)',
        r'(\d+)in(\d+)',  # Generic format like "100in5"
        r'(\d+)\s*(gb|mb).*?(\d+)\s*(sec|seconds)',
        r'(\d+)\s*(requests|queries).*?(\d+)\s*(sec|seconds)',
    ]
    
    for pattern in speed_patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            match = matches[0]
            if len(match) >= 2:
                value1, unit1 = match[0], match[1]
                if len(match) >= 4:
                    value2, unit2 = match[2], match[3]
                    specs['speed_value'] = f"{value1} {unit1} in {value2} {unit2}"
                else:
                    specs['speed_value'] = f"{value1} {unit1}"
                break
    
    return specs


def run_technical_dd_chain(profile: StartupProfile, evaluator: Optional[object] = None) -> StartupProfile:
    # Comprehensive context extraction to capture all valuable technical information
    context = get_hybrid_context(
        profile, "patents OR patent portfolio OR intellectual property OR IP OR product roadmap OR development timeline OR technical milestones OR technology stack OR product development OR technical specifications OR performance metrics OR energy density OR cycle life OR charging speed OR temperature range OR safety features OR materials OR dimensions OR capabilities OR battery chemistry OR cell design OR manufacturing OR testing OR certification", 5, 3
    )
    
    # Debug: Print a snippet of the context to see what's being passed
    print(f"[Technical DD] Context snippet: {context[:500]}...")
    
    # Get the full document text for better extraction
    full_text = ""
    try:
        # Use the profile's extracted data context if available
        if hasattr(profile, 'extracted_data_context') and profile.extracted_data_context:
            full_text = profile.extracted_data_context
        # Fallback to context if no extracted data
        if not full_text:
            full_text = context
    except:
        full_text = context
    
    # Extract technical specifications from full text
    tech_specs = extract_technical_specs_from_text(full_text)
    
    # Set extracted technical specifications on profile FIRST (before LLM call)
    if tech_specs.get('energy_density'):
        profile.energy_density_wh_kg = tech_specs['energy_density']
        profile.energy_density_source = 'technical_extraction'
    if tech_specs.get('cycle_life'):
        profile.cycle_life_count = tech_specs['cycle_life']
        profile.cycle_life_source = 'technical_extraction'
    if tech_specs.get('patents'):
        if isinstance(tech_specs['patents'], str):
            profile.patent_portfolio = f"{tech_specs['patents']} patents"
        else:
            profile.patent_portfolio = f"{tech_specs['patents']} patents"
    
    # Set all extracted technical specifications on profile (use correct keys)
    mapping = {
        'energy_density': 'energy_density_wh_kg',
        'cycle_life': 'cycle_life_count',
        'volumetric_energy_density': 'volumetric_energy_density',
        'granted_patents': 'granted_patents',
        'pending_patents': 'pending_patents',
        'patent_details': 'patent_details',
        'oem_partners': 'oem_partners',
        'safety_certifications': 'safety_certifications',
        'employees_count': 'employees_count',
        'low_temp_performance': 'low_temp_performance',
        'power_performance': 'power_performance',
        'cell_capacity': 'cell_capacity',
        'charging_speed_miles': 'charging_speed_miles',
        'charging_speed_minutes': 'charging_speed_minutes',
        'cell_dimensions': 'cell_dimensions',
        'charging_power': 'charging_power',
        'phds': 'phds',
        'professionals': 'professionals',
        'roadmap_100in_speed': 'roadmap_100in_speed',
        'roadmap_100in_year': 'roadmap_100in_year',
        'roadmap_production_year': 'roadmap_production_year',
        'roadmap_technologies': 'roadmap_technologies',
    }
    
    # Safely set extracted technical specifications on profile
    for extracted_key, profile_key in mapping.items():
        if extracted_key in tech_specs and tech_specs[extracted_key] is not None:
            try:
                setattr(profile, profile_key, tech_specs[extracted_key])
                print(f"[Technical DD] Set {profile_key} = {tech_specs[extracted_key]}")
            except Exception as e:
                print(f"[Technical DD] Error setting {profile_key}: {e}")
    
    # Now try the LLM call (but extracted data is already set)
    try:
        # Clean the context to avoid formatting issues
        clean_context = context.replace('"', "'").replace('\n', ' ').strip()
        resp = llm.invoke(PROMPT.format(context=clean_context))
        log_usage_from_message(evaluator, "TECHNICAL DD AGENT", resp, model="gpt-4o")
        txt = resp.content.strip()
        data = clean_llm_output(txt)
        
        if data:
            # Set profile attributes from the cleaned data
            if data.get("tech_maturity"):
                profile.tech_maturity = str(data["tech_maturity"])
            if data.get("moat_strength"):
                profile.moat_strength = str(data["moat_strength"])
            if data.get("tech_stack"):
                profile.tech_stack = str(data["tech_stack"])
            if data.get("product_specifications"):
                profile.product_specifications = str(data["product_specifications"])
            if data.get("product_roadmap"):
                profile.product_roadmap = str(data["product_roadmap"])
            if data.get("patent_portfolio"):
                # Only set if we don't already have extracted patent data
                if not hasattr(profile, 'patent_portfolio') or not profile.patent_portfolio or "requires additional research" in profile.patent_portfolio:
                    profile.patent_portfolio = str(data["patent_portfolio"])
                    print(f"[Technical DD] LLM set patent portfolio to: {profile.patent_portfolio}")
                else:
                    print(f"[Technical DD] Keeping extracted patent data: {profile.patent_portfolio}")
            if data.get("complexity"):
                profile.complexity = str(data["complexity"])
            if data.get("security"):
                profile.security = str(data["security"])
            if data.get("implementation"):
                profile.implementation = str(data["implementation"])
            if data.get("regulatory"):
                profile.regulatory = str(data["regulatory"])
            if data.get("testing"):
                profile.testing = str(data["testing"])
        else:
            # Fallback: set default values if parsing fails, but DON'T override extracted data
            if not hasattr(profile, 'tech_maturity') or not profile.tech_maturity or profile.tech_maturity == "Technical assessment unavailable":
                profile.tech_maturity = "Technical maturity assessment requires additional research"
            if not hasattr(profile, 'moat_strength') or not profile.moat_strength or profile.moat_strength == "Moat analysis unavailable":
                profile.moat_strength = "Moat strength analysis requires additional research"
            
    except Exception as e:
        print(f"[Technical DD] Error: {e}")
        # Set fallback values ONLY if extracted data is not available
        if not hasattr(profile, 'tech_maturity') or not profile.tech_maturity or profile.tech_maturity == "Technical assessment unavailable":
            profile.tech_maturity = "Technical assessment unavailable"
        if not hasattr(profile, 'moat_strength') or not profile.moat_strength or profile.moat_strength == "Moat analysis unavailable":
            profile.moat_strength = "Moat analysis unavailable"
        if not hasattr(profile, 'tech_stack') or not profile.tech_stack or profile.tech_stack == "Technology stack details require additional research":
            profile.tech_stack = "Technology stack details require additional research"
        if not hasattr(profile, 'product_specifications') or not profile.product_specifications or profile.product_specifications == "Product technical specifications require additional research":
            profile.product_specifications = "Product technical specifications require additional research"
        if not hasattr(profile, 'product_roadmap') or not profile.product_roadmap or profile.product_roadmap == "Product roadmap information requires additional research":
            profile.product_roadmap = "Product roadmap information requires additional research"
        if not hasattr(profile, 'patent_portfolio') or not profile.patent_portfolio or profile.patent_portfolio == "Patent portfolio information requires additional research":
            print(f"[Technical DD] Overriding patent portfolio. Current value: '{profile.patent_portfolio}'")
            profile.patent_portfolio = "Patent portfolio information requires additional research"
        if not hasattr(profile, 'complexity') or not profile.complexity or profile.complexity == "Technical complexity assessment requires additional research":
            profile.complexity = "Technical complexity assessment requires additional research"
        if not hasattr(profile, 'security') or not profile.security or profile.security == "Security considerations require additional research":
            profile.security = "Security considerations require additional research"
        if not hasattr(profile, 'implementation') or not profile.implementation or profile.implementation == "Implementation details require additional research":
            profile.implementation = "Implementation details require additional research"
        if not hasattr(profile, 'regulatory') or not profile.regulatory:
            profile.regulatory = "Regulatory compliance information requires additional research"
        if not hasattr(profile, 'testing') or not profile.testing:
            profile.testing = "Testing and validation information requires additional research"
    
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    
    return profile


def run_technical_dd_chain_with_text(full_text: str, profile: StartupProfile, evaluator: Optional[object] = None) -> StartupProfile:
    """Run technical due diligence using extracted text as context."""
    # Use comprehensive text to capture all valuable technical information
    # Use smart technical context instead of first 15k chars
    context = get_smart_technical_context(full_text)
    
    # Debug: Print a snippet of the context to see what's being passed
    print(f"[Technical DD] Full text context snippet: {context[:500]}...")
    print(f"[Technical DD] FULL CONTEXT PASSED TO AGENT:\n{context}\n{'='*60}")
    
    # Extract technical specifications from full text
    tech_specs = extract_technical_specs_from_text(full_text)
    
    # Set extracted technical specifications on profile
    if tech_specs.get('energy_density'):
        profile.energy_density_wh_kg = tech_specs['energy_density']
        profile.energy_density_source = 'technical_extraction'
    if tech_specs.get('volumetric_energy_density'):
        profile.volumetric_energy_density = tech_specs['volumetric_energy_density']
    if tech_specs.get('cycle_life'):
        profile.cycle_life_count = tech_specs['cycle_life']
        profile.cycle_life_source = 'technical_extraction'
    if tech_specs.get('patents'):
        if isinstance(tech_specs['patents'], str):
            profile.patent_portfolio = f"{tech_specs['patents']} patents"
        else:
            profile.patent_portfolio = f"{tech_specs['patents']} patents"
    if tech_specs.get('granted_patents'):
        profile.granted_patents = tech_specs['granted_patents']
    if tech_specs.get('pending_patents'):
        profile.pending_patents = tech_specs['pending_patents']
    if tech_specs.get('patent_details'):
        profile.patent_details = tech_specs['patent_details']
    
    # Set new technical specifications (only fields that exist in schema)
    if tech_specs.get('charging_speed_miles'):
        profile.charging_speed_miles = tech_specs['charging_speed_miles']
    if tech_specs.get('charging_speed_minutes'):
        profile.charging_speed_minutes = tech_specs['charging_speed_minutes']
    if tech_specs.get('volumetric_energy_density'):
        profile.volumetric_energy_density = tech_specs['volumetric_energy_density']
    if tech_specs.get('granted_patents'):
        profile.granted_patents = tech_specs['granted_patents']
    if tech_specs.get('pending_patents'):
        profile.pending_patents = tech_specs['pending_patents']
    if tech_specs.get('patent_details'):
        profile.patent_details = tech_specs['patent_details']
    if tech_specs.get('oem_partners'):
        profile.oem_partners = tech_specs['oem_partners']
    if tech_specs.get('safety_certifications'):
        profile.safety_certifications = tech_specs['safety_certifications']
    if tech_specs.get('low_temp_performance'):
        profile.low_temp_performance = tech_specs['low_temp_performance']
    if tech_specs.get('cell_capacity'):
        profile.cell_capacity = tech_specs['cell_capacity']
    if tech_specs.get('cell_dimensions'):
        profile.cell_dimensions = tech_specs['cell_dimensions']
    if tech_specs.get('charging_power'):
        profile.charging_power = tech_specs['charging_power']
    if tech_specs.get('power_performance'):
        profile.power_performance = tech_specs['power_performance']
    if tech_specs.get('employees_count'):
        profile.employees_count = tech_specs['employees_count']
    elif tech_specs.get('employees'):
        profile.employees_count = tech_specs['employees']
    if tech_specs.get('phds'):
        profile.phds = tech_specs['phds']
    if tech_specs.get('professionals'):
        profile.professionals = tech_specs['professionals']
    
    # Set roadmap specifications
    if tech_specs.get('roadmap_100in_speed'):
        profile.roadmap_100in_speed = tech_specs['roadmap_100in_speed']
    if tech_specs.get('roadmap_100in_year'):
        profile.roadmap_100in_year = tech_specs['roadmap_100in_year']
    if tech_specs.get('roadmap_production_year'):
        profile.roadmap_production_year = tech_specs['roadmap_production_year']
    if tech_specs.get('roadmap_technologies'):
        profile.roadmap_technologies = tech_specs['roadmap_technologies']
    
    # Set phase-specific roadmap years
    for key, value in tech_specs.items():
        if key.startswith('roadmap_phase_') and key.endswith('_year'):
            setattr(profile, key, value)
    
    # Print extracted technical specifications for debugging
    print(f"[Technical DD] Extracted specs: {tech_specs}")
    
    try:
        # Clean the context to avoid formatting issues and escape curly braces
        clean_context = context.replace('"', "'").replace('\n', ' ').replace('{', '{{').replace('}', '}}').strip()
        resp = llm.invoke(PROMPT.format(context=clean_context))
        log_usage_from_message(evaluator, "TECHNICAL DD AGENT", resp, model="gpt-4o")
        txt = resp.content.strip()
        data = clean_llm_output(txt)
        
        if data:
            # Set profile attributes from the cleaned data
            if data.get("tech_maturity"):
                profile.tech_maturity = str(data["tech_maturity"])
            if data.get("moat_strength"):
                profile.moat_strength = str(data["moat_strength"])
            if data.get("tech_stack"):
                profile.tech_stack = str(data["tech_stack"])
            if data.get("product_specifications"):
                profile.product_specifications = str(data["product_specifications"])
            if data.get("product_roadmap"):
                profile.product_roadmap = str(data["product_roadmap"])
            if data.get("patent_portfolio"):
                # Only set if we don't already have extracted patent data
                if not hasattr(profile, 'patent_portfolio') or not profile.patent_portfolio or "requires additional research" in profile.patent_portfolio:
                    profile.patent_portfolio = str(data["patent_portfolio"])
                    print(f"[Technical DD] LLM set patent portfolio to: {profile.patent_portfolio}")
                else:
                    print(f"[Technical DD] Keeping extracted patent data: {profile.patent_portfolio}")
            if data.get("complexity"):
                profile.complexity = str(data["complexity"])
            if data.get("security"):
                profile.security = str(data["security"])
            if data.get("implementation"):
                profile.implementation = str(data["implementation"])
            if data.get("regulatory"):
                profile.regulatory = str(data["regulatory"])
            if data.get("testing"):
                profile.testing = str(data["testing"])
        else:
            # Fallback: set default values if parsing fails, but DON'T override extracted data
            if not hasattr(profile, 'tech_maturity') or not profile.tech_maturity:
                profile.tech_maturity = "Technical maturity assessment requires additional research"
            if not hasattr(profile, 'moat_strength') or not profile.moat_strength:
                profile.moat_strength = "Moat strength analysis requires additional research"
            if not hasattr(profile, 'tech_stack') or not profile.tech_stack:
                profile.tech_stack = "Technology stack details require additional research"
            if not hasattr(profile, 'product_specifications') or not profile.product_specifications:
                profile.product_specifications = "Product technical specifications require additional research"
            if not hasattr(profile, 'product_roadmap') or not profile.product_roadmap:
                profile.product_roadmap = "Product roadmap information requires additional research"
            if not hasattr(profile, 'patent_portfolio') or not profile.patent_portfolio:
                profile.patent_portfolio = "Patent portfolio information requires additional research"
            if not hasattr(profile, 'complexity') or not profile.complexity:
                profile.complexity = "Technical complexity assessment requires additional research"
            if not hasattr(profile, 'security') or not profile.security:
                profile.security = "Security considerations require additional research"
            if not hasattr(profile, 'implementation') or not profile.implementation:
                profile.implementation = "Implementation details require additional research"
            if not hasattr(profile, 'regulatory') or not profile.regulatory:
                profile.regulatory = "Regulatory compliance information requires additional research"
            if not hasattr(profile, 'testing') or not profile.testing:
                profile.testing = "Testing and validation information requires additional research"
            
    except Exception as e:
        print(f"[Technical DD] Error: {e}")
        # Set fallback values ONLY if extracted data is not available
        if not hasattr(profile, 'tech_maturity') or not profile.tech_maturity:
            profile.tech_maturity = "Technical assessment unavailable"
        if not hasattr(profile, 'moat_strength') or not profile.moat_strength:
            profile.moat_strength = "Moat analysis unavailable"
        if not hasattr(profile, 'tech_stack') or not profile.tech_stack:
            profile.tech_stack = "Technology stack details require additional research"
        if not hasattr(profile, 'product_specifications') or not profile.product_specifications:
            profile.product_specifications = "Product technical specifications require additional research"
        if not hasattr(profile, 'product_roadmap') or not profile.product_roadmap:
            profile.product_roadmap = "Product roadmap information requires additional research"
        if not hasattr(profile, 'patent_portfolio') or not profile.patent_portfolio:
            profile.patent_portfolio = "Patent portfolio information requires additional research"
        if not hasattr(profile, 'complexity') or not profile.complexity:
            profile.complexity = "Technical complexity assessment requires additional research"
        if not hasattr(profile, 'security') or not profile.security:
            profile.security = "Security considerations require additional research"
        if not hasattr(profile, 'implementation') or not profile.implementation:
            profile.implementation = "Implementation details require additional research"
        if not hasattr(profile, 'regulatory') or not profile.regulatory:
            profile.regulatory = "Regulatory compliance information requires additional research"
        if not hasattr(profile, 'testing') or not profile.testing:
            profile.testing = "Testing and validation information requires additional research"
    
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    
    return profile


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
