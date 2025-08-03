"""
Memo formatting utilities for generating investment memo sections.
Extracted from main.py to improve code organization.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.schemas import StartupProfile


def format_company_overview_section(profile: StartupProfile) -> str:
    """Format company overview section for the memo."""
    lines = []
    lines.append(f"Company: {getattr(profile, 'name', 'TBD')}")
    
    if getattr(profile, 'sector', None):
        lines.append(f"Sector: {profile.sector}")
    if getattr(profile, 'website', None):
        lines.append(f"Website: {profile.website}")
    if getattr(profile, 'status', None):
        lines.append(f"Status: {profile.status}")
    if getattr(profile, 'size_range', None):
        lines.append(f"Size: {profile.size_range}")
    elif getattr(profile, 'size', None):
        lines.append(f"Size: {profile.size}")
    if getattr(profile, 'founded_year', None):
        lines.append(f"Founded: {profile.founded_year}")
    elif getattr(profile, 'founded', None):
        lines.append(f"Founded: {profile.founded}")
    
    # HQ - check CoreSignal fields first, then fallback
    hq = getattr(profile, 'hq_city', None) or getattr(profile, 'headquarters_new_address', None) or getattr(profile, 'headquarters_city', None)
    if hq:
        lines.append(f"Headquarters: {hq}")
    hq_country = getattr(profile, 'hq_country_iso2', None) or getattr(profile, 'headquarters_country_restored', None)
    if hq_country:
        lines.append(f"Country: {hq_country}")
    
    if getattr(profile, 'linkedin', None):
        lines.append(f"LinkedIn: {profile.linkedin}")
    elif getattr(profile, 'canonical_url', None):
        lines.append(f"LinkedIn: {profile.canonical_url}")
    if getattr(profile, 'linkedin_followers', None):
        lines.append(f"LinkedIn Followers: {profile.linkedin_followers}")
    elif getattr(profile, 'followers', None):
        lines.append(f"Followers: {profile.followers}")
    if getattr(profile, 'employees_count', None):
        lines.append(f"Employees: {profile.employees_count}")
    
    # Enhanced CoreSignal data
    if getattr(profile, 'website_traffic', None):
        lines.append(f"Website Traffic: {profile.website_traffic}")
    if getattr(profile, 'x_followers', None):
        lines.append(f"X/Twitter Followers: {profile.x_followers}")
    if getattr(profile, 'news_counts', None):
        lines.append(f"Media Mentions: {profile.news_counts}")
    if getattr(profile, 'estimated_revenue_range', None):
        lines.append(f"Estimated Revenue: {profile.estimated_revenue_range}")
    if getattr(profile, 'last_funding_round_amount_raised', None):
        lines.append(f"Latest Funding: {profile.last_funding_round_amount_raised}")
    if getattr(profile, 'last_funding_round_announced_date', None):
        lines.append(f"Funding Date: {profile.last_funding_round_announced_date}")
    if getattr(profile, 'technographics', None):
        lines.append(f"Tech Stack: {profile.technographics}")
    
    # Contact information
    if getattr(profile, 'emails', None):
        lines.append(f"Company Emails: {profile.emails}")
    if getattr(profile, 'phones', None):
        lines.append(f"Company Phones: {profile.phones}")
    if getattr(profile, 'twitter', None):
        lines.append(f"Twitter: {profile.twitter}")
    if getattr(profile, 'facebook', None):
        lines.append(f"Facebook: {profile.facebook}")
    
    # Office locations - check CoreSignal field first, then fallback
    locs = getattr(profile, 'office_locations', None) or getattr(profile, 'company_locations_collection', None)
    if locs and isinstance(locs, list):
        # Using deduplication function to get unique locations
        from core.orchestration import deduplicate_office_locations
        unique_locs = deduplicate_office_locations(locs)
        
        loc_strs = []
        for loc in unique_locs:
            addr = loc.get('location_address') if isinstance(loc, dict) else str(loc)
            if addr and addr.strip():
                loc_strs.append(addr.strip())
        
        if loc_strs:
            # Showing only the first (primary) location to avoid clutter
            primary_location = loc_strs[0]
            if len(loc_strs) > 1:
                lines.append(f"Office Location: {primary_location} (and {len(loc_strs)-1} other locations)")
            else:
                lines.append(f"Office Location: {primary_location}")
    
    # Funding Stage - Enhanced to show latest significant funding
    funding_stage = format_funding_stage(profile)
    
    # Trying to get more detailed funding info from funding rounds
    latest_funding_info = ""
    if hasattr(profile, 'funding_rounds') and profile.funding_rounds:
        try:
            import json
            funding_rounds = json.loads(profile.funding_rounds) if isinstance(profile.funding_rounds, str) else profile.funding_rounds
            
            if funding_rounds and isinstance(funding_rounds, list):
                # Finding the most recent significant funding round by sorting by date
                valid_rounds = []
                for round_data in funding_rounds:
                    if isinstance(round_data, dict):
                        round_type = round_data.get('last_round_type') or round_data.get('round_type')
                        round_amount = round_data.get('last_round_money_raised') or round_data.get('amount_usd')
                        round_date = round_data.get('last_round_date') or round_data.get('date')
                        
                        if round_type and round_amount and round_date:
                            # Parsing date for sorting
                            try:
                                if isinstance(round_date, str) and len(round_date) == 8 and round_date.isdigit():
                                    # Format like "20180522"
                                    from datetime import datetime
                                    date_obj = datetime.strptime(round_date, '%Y%m%d')
                                elif isinstance(round_date, str) and '-' in round_date:
                                    # Format like "2018-05-22" to "22 May 2018"
                                    from datetime import datetime
                                    date_obj = datetime.strptime(round_date.split(' ')[0], '%Y-%m-%d')
                                else:
                                    # Trying to parse other date formats
                                    from datetime import datetime
                                    date_obj = datetime.strptime(str(round_date), '%Y-%m-%d')
                                
                                valid_rounds.append({
                                    'type': round_type,
                                    'amount': round_amount,
                                    'date': round_date,
                                    'date_obj': date_obj
                                })
                            except:
                                # Skipping rounds with unparseable dates
                                continue
                
                # Sorting by date (most recent first) and taking the first one
                if valid_rounds:
                    valid_rounds.sort(key=lambda x: x['date_obj'], reverse=True)
                    latest_round = valid_rounds[0]
                    
                    # Format the date for display
                    try:
                        if isinstance(latest_round['date'], str) and len(latest_round['date']) == 8 and latest_round['date'].isdigit():
                            # Formatting like "20180522" to "May 2018"
                            from datetime import datetime
                            date_obj = datetime.strptime(latest_round['date'], '%Y%m%d')
                            formatted_date = date_obj.strftime('%B %Y')
                        elif isinstance(latest_round['date'], str) and '-' in latest_round['date']:
                            # Formatting like "2018-05-22" to "May 2018"
                            from datetime import datetime
                            date_obj = datetime.strptime(latest_round['date'].split(' ')[0], '%Y-%m-%d')
                            formatted_date = date_obj.strftime('%B %Y')
                        else:
                            formatted_date = str(latest_round['date'])
                    except:
                        formatted_date = str(latest_round['date'])
                    
                    # Formatting the amount
                    try:
                        amount_float = float(latest_round['amount'])
                        if amount_float >= 1_000_000:
                            formatted_amount = f"${amount_float/1_000_000:.1f}M"
                        elif amount_float >= 1_000:
                            formatted_amount = f"${amount_float/1_000:.1f}K"
                        else:
                            formatted_amount = f"${amount_float:.0f}"
                    except:
                        formatted_amount = str(latest_round['amount'])
                    
                    latest_funding_info = f" ({latest_round['type']} - {formatted_amount} - {formatted_date})"
        except Exception as e:
            print(f"[Company Overview] Error processing funding rounds: {e}")
    
    lines.append(f"Funding Stage: {funding_stage}{latest_funding_info}")
    
    # Team
    execs = getattr(profile, 'executives', []) or []
    if execs:
        team_members = []
        for e in execs[:3]:
            if isinstance(e, dict):
                name = e.get('name', 'Unknown')
                role = e.get('role', '')
                if role:
                    team_members.append(f"{name} ({role})")
                else:
                    team_members.append(name)
            else:
                team_members.append(str(e))
        team_str = "Team: " + ", ".join(team_members)
        lines.append(team_str)
    
    return '\n'.join(lines)


def format_funding_stage(profile: StartupProfile) -> str:
    """Format funding stage information."""
    funding_stage = getattr(profile, 'funding_stage', None) or 'Undisclosed'
    
    # Enhanced: Use CoreSignal funding data if available
    last_funding_round_name = getattr(profile, 'last_funding_round_name', None)
    last_funding_round_amount = getattr(profile, 'last_funding_round_amount_raised', None)
    last_funding_round_date = getattr(profile, 'last_funding_round_announced_date', None)
    
    if funding_stage.lower() in ['unknown', 'n/a', '']:
        # Try CoreSignal funding data first
        if last_funding_round_name and last_funding_round_amount:
            funding_stage = f"{last_funding_round_name} ({last_funding_round_amount})"
            if last_funding_round_date:
                funding_stage += f" - {last_funding_round_date}"
        else:
            # Fallback to PitchBook data
            pitchbook_round = getattr(profile, 'pitchbook_last_round', None)
            pitchbook_year = getattr(profile, 'pitchbook_last_year', None)
            if pitchbook_round and pitchbook_year:
                funding_stage = f"{pitchbook_round} ({pitchbook_year})"
            else:
                last_round = getattr(profile, 'last_funding_round', None)
                last_round_year = getattr(profile, 'last_funding_year', None)
                if last_round and last_round_year:
                    funding_stage = f"Undisclosed (last round: {last_round} - {last_round_year})"
                else:
                    funding_stage = "Undisclosed (no public data found)"
    
    return funding_stage


def format_product_description_section(profile: StartupProfile) -> str:
    """Format product description section."""
    # Gathering all relevant fields
    desc = getattr(profile, 'product_description', None)
    specs = getattr(profile, 'product_specs', None)
    roadmap = getattr(profile, 'product_roadmap', None)
    unique = getattr(profile, 'unique_features', None)
    status = getattr(profile, 'status', None)
    uniqueness = getattr(profile, 'uniqueness', None)
    diff = getattr(profile, 'difference_from_competitors', None)
    scalability = getattr(profile, 'scalability', None)
    sustainability = getattr(profile, 'sustainability', None)
    regulatory = getattr(profile, 'regulatory', None)
    testing = getattr(profile, 'testing', None)
    security = getattr(profile, 'security', None)

    # Detect product type for sector-agnostic description
    product_type = detect_product_type(profile)
    
    # Get sector-specific metrics
    sector_metrics = get_sector_specific_metrics(profile, product_type)

    # Synthesising a narrative lead sentence
    lead = None
    if desc and len(desc.split()) > 6:
        lead = desc
    else:
        # Trying to synthesise a narrative
        parts = []
        if status:
            parts.append(f"The core {product_type} is {status}.")
        if unique:
            parts.append(f"It features {unique}.")
        if specs:
            parts.append(f"Key specs: {specs}.")
        if sector_metrics:
            parts.append(f"It offers " + " and ".join(sector_metrics) + ".")
        if roadmap:
            parts.append(f"Product roadmap: {roadmap}.")
        if uniqueness:
            parts.append(f"What makes it unique: {uniqueness}.")
        if diff:
            parts.append(f"Compared to competitors: {diff}.")
        if scalability:
            parts.append(f"Scalability: {scalability}.")
        if sustainability:
            parts.append(f"Sustainability: {sustainability}.")
        if regulatory:
            parts.append(f"Regulatory: {regulatory}.")
        if testing:
            parts.append(f"Testing: {testing}.")
        if security:
            parts.append(f"Security: {security}.")
        # Composing a paragraph
        lead = ' '.join(parts)
    if not lead or len(lead.strip()) < 20:
        # Fallback: concatenate all fields if no narrative possible
        all_fields = [desc, specs, roadmap, unique, status, uniqueness, diff, scalability, sustainability, regulatory, testing, security]
        all_fields = [str(f) for f in all_fields if f]
        if all_fields:
            lead = ' '.join(all_fields)
        else:
            return 'Product description not available.'
    return lead.strip()


def detect_product_type(profile: StartupProfile) -> str:
    """Generic product type detection that works for any startup sector."""
    # Check for explicit product type indicators first
    product_type = getattr(profile, 'product_type', None)
    if product_type:
        return product_type.lower()
    
    # Use the actual sector from the profile data
    sector = getattr(profile, 'sector', '').lower()
    if sector:
        return sector
    
    # Check product description for any technical indicators
    desc = getattr(profile, 'product_description', '').lower()
    if desc:
        # Extract any technical terms from the description
        technical_terms = extract_technical_terms(desc)
        if technical_terms:
            return technical_terms[0]  # Use the most prominent technical term
    
    # Default to generic product
    return 'product'


def extract_technical_terms(description: str) -> List[str]:
    """Extract technical terms from product description dynamically."""
    # Common technical terms across all sectors
    technical_terms = [
        'platform', 'software', 'hardware', 'device', 'app', 'service',
        'technology', 'solution', 'system', 'tool', 'product', 'service',
        'algorithm', 'model', 'framework', 'protocol', 'standard',
        'component', 'module', 'interface', 'api', 'database',
        'network', 'cloud', 'mobile', 'web', 'desktop', 'embedded',
        'analytics', 'automation', 'optimization', 'integration',
        'security', 'compliance', 'scalability', 'performance',
        'reliability', 'efficiency', 'accuracy', 'speed', 'capacity'
    ]
    
    found_terms = []
    for term in technical_terms:
        if term in description:
            found_terms.append(term)
    
    return found_terms


def get_sector_specific_metrics(profile: StartupProfile, product_type: str) -> List[str]:
    """Get metrics dynamically based on available profile data."""
    metrics = []
    
    # Get all available profile attributes
    profile_attrs = [attr for attr in dir(profile) if not attr.startswith('_')]
    
    # Common metric patterns across all sectors
    metric_patterns = {
        'performance': ['performance', 'speed', 'efficiency', 'throughput', 'capacity'],
        'quality': ['quality', 'accuracy', 'precision', 'reliability', 'durability'],
        'scale': ['scale', 'size', 'volume', 'capacity', 'throughput'],
        'cost': ['cost', 'price', 'value', 'efficiency', 'economy'],
        'time': ['time', 'duration', 'speed', 'latency', 'response'],
        'security': ['security', 'safety', 'protection', 'compliance'],
        'user': ['user', 'customer', 'adoption', 'engagement', 'satisfaction']
    }
    
    # Check for any metrics in the profile data
    for attr in profile_attrs:
        try:
            value = getattr(profile, attr)
            if value and isinstance(value, (str, int, float)):
                # Check if this attribute looks like a metric
                attr_lower = attr.lower()
                for metric_type, keywords in metric_patterns.items():
                    if any(keyword in attr_lower for keyword in keywords):
                        metrics.append(f"{attr.replace('_', ' ')} of {value}")
                        break
        except:
            continue
    
    # If no metrics found, return generic ones based on product type
    if not metrics:
        if product_type == 'product':
            metrics.append("product specifications and performance metrics")
        else:
            metrics.append(f"{product_type} specific metrics and KPIs")
    
    return metrics


def format_risk_section(profile: StartupProfile) -> str:
    """Format risk section for the memo."""
    risk_flags = getattr(profile, 'risk_flags', [])
    regulatory = getattr(profile, 'regulatory', None)
    testing = getattr(profile, 'testing', None)
    security = getattr(profile, 'security', None)
    discussion = []
    # Enumerate and describe all risks
    if risk_flags:
        for rf in risk_flags:
            discussion.append(f"• {rf}")
    else:
        discussion.append("• Risks are present but not fully disclosed. Investors should request more information and conduct further diligence.")
    # Always including regulatory, testing, security
    discussion.append(f"• Regulatory: {regulatory or 'Compliance with evolving standards and certifications is required.'}")
    discussion.append(f"• Testing: {testing or 'Independent validation and certification are recommended.'}")
    discussion.append(f"• Security: {security or 'Product safety, data, and IP protection should be addressed.'}")
    return '\n'.join(discussion)


def format_risk_score(profile: StartupProfile) -> str:
    """Format risk score information."""
    risk_score = getattr(profile, 'risk_score', None)
    if risk_score is not None and risk_score != 'N/A':
        return f"Risk Score: {risk_score}"
    else:
        return ""


def format_followup_section(profile: StartupProfile) -> str:
    """Format follow-up questions section."""
    fq = getattr(profile, 'follow_up_questions', None) or ''
    # Removing all '**' and leading '-' from every line
    lines = []
    for line in fq.split('\n'):
        clean_line = line.replace('**', '').strip()
        # Removing leading '-' and any whitespace after it
        if clean_line.startswith('-'):
            clean_line = clean_line[1:].lstrip()
        if clean_line.startswith('• -'):
            clean_line = clean_line[3:].lstrip()
        elif clean_line.startswith('•') and clean_line[1:2] in [' ', '-']:
            clean_line = '•' + clean_line[2:].lstrip('-').lstrip()
        # Header if ends with ':' after cleaning, or if it is a title-like line (contains & or is Title Case)
        is_header = False
        if clean_line.endswith(':'):
            is_header = True
        elif clean_line and (clean_line.istitle() or ('&' in clean_line and clean_line == clean_line.title())):
            is_header = True
        # Special case: if line started with '• -', treat as header if it looks like a section
        if line.strip().startswith('• -') and (':' not in clean_line and (clean_line.istitle() or '&' in clean_line)):
            is_header = True
        if is_header:
            lines.append(f"<HEADER>{clean_line.rstrip(':')}")
        elif clean_line:
            lines.append(f"• {clean_line}")
    return '\n'.join(lines) if lines else 'No follow-up questions generated.' 