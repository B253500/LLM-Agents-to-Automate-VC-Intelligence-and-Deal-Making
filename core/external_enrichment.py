"""
External enrichment utilities including ProxyCurl integration.
Additional enrichment sources without replacing existing functionality.
"""

import os
import requests
from typing import Dict, Optional, Any
from core.schemas import StartupProfile
from langchain_openai import ChatOpenAI


def find_company_website(company_name, founder_name=None, sector=None, full_text=None):
    """
    Find the official website for a company using AI reasoning.
    """
    # Compose a reasoning prompt for the LLM
    prompt = (
        f"You are a research analyst. Find the official website for the company '{company_name}'."
        f"{' The founder is ' + founder_name + '.' if founder_name else ''}"
        f"{' The sector is ' + sector + '.' if sector else ''}"
        " Use Google or web search if needed. Return only the official website URL. If ambiguous, explain your reasoning."
    )
    
    try:
        llm = ChatOpenAI(model='gpt-4o', api_key=os.getenv('OPENAI_API_KEY'))
        result = llm.invoke(prompt).content.strip()
        return result
    except Exception as e:
        print(f"Website finder error: {e}")
        return None


def get_linkedin_profile_proxycurl(founder_name: str, company_name: str = None) -> Optional[Dict[str, Any]]:
    """
    Get LinkedIn profile data using ProxyCurl API.
    Additional enrichment source without replacing existing functionality.
    """
    api_key = os.getenv("PROXYCURL_API_KEY")
    if not api_key:
        print("PROXYCURL_API_KEY not found in environment variables")
        return None
    
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {
        "first_name": founder_name.split()[0],
        "last_name": founder_name.split()[-1],
    }
    if company_name:
        params["company"] = company_name
    
    url = "https://nubela.co/proxycurl/api/v2/linkedin/person"
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"ProxyCurl error: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"ProxyCurl request failed: {e}")
        return None


def format_linkedin_profile_proxycurl(data: Dict[str, Any]) -> str:
    """Format ProxyCurl LinkedIn data for memo inclusion."""
    if not data:
        return "No LinkedIn profile found via ProxyCurl."
    
    lines = []
    lines.append(f"LinkedIn: {data.get('profile_url', 'N/A')}")
    lines.append(f"Headline: {data.get('headline', 'N/A')}")
    
    summary = data.get('summary', '')
    if summary and len(summary) > 50:
        lines.append(f"Summary: {summary[:200]}...")
    elif summary:
        lines.append(f"Summary: {summary}")
    
    current_position = data.get('occupation', '')
    if current_position:
        lines.append(f"Current Position: {current_position}")
    
    # Add experience if available
    experiences = data.get('experiences', [])
    if experiences:
        lines.append("Experience:")
        for exp in experiences[:3]:  # Limit to 3 most recent
            company = exp.get('company', 'Unknown')
            title = exp.get('title', '')
            if company and title:
                lines.append(f"  - {title} at {company}")
    
    return '\n'.join(lines)


def enrich_executives_with_proxycurl(profile: StartupProfile) -> StartupProfile:
    """
    Enrich executives with ProxyCurl data as additional source.
    Does not replace existing enrichment, just adds to it.
    """
    execs = getattr(profile, 'executives', None) or []
    company_name = getattr(profile, 'name', '')
    
    if not execs:
        return profile
    
    for exec in execs:
        if isinstance(exec, dict):
            name = exec.get('name', '').strip()
            if name:
                # Get ProxyCurl data
                proxycurl_data = get_linkedin_profile_proxycurl(name, company_name)
                if proxycurl_data:
                    # Add ProxyCurl data as additional field
                    exec['proxycurl_data'] = proxycurl_data
                    exec['proxycurl_formatted'] = format_linkedin_profile_proxycurl(proxycurl_data)
    
    profile.executives = execs
    return profile


def get_enhanced_team_section(profile: StartupProfile) -> str:
    """
    Generate enhanced team section with ProxyCurl data included.
    Combines existing team data with ProxyCurl enrichment.
    """
    from chains.memo_synthesis_chain import run_team_section_chain
    
    # First get the standard team section
    base_team_section = run_team_section_chain(profile)
    
    # Add ProxyCurl enrichment if available
    execs = getattr(profile, 'executives', None) or []
    enhanced_lines = []
    
    for exec in execs:
        if isinstance(exec, dict):
            proxycurl_formatted = exec.get('proxycurl_formatted', '')
            if proxycurl_formatted:
                name = exec.get('name', 'Unknown')
                enhanced_lines.append(f"\n**{name} - Additional LinkedIn Data:**")
                enhanced_lines.append(proxycurl_formatted)
    
    if enhanced_lines:
        return base_team_section + '\n' + '\n'.join(enhanced_lines)
    
    return base_team_section 