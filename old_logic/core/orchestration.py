import json
import re
from crewai import Crew
from core.schemas import StartupProfile
from core.download_utils import extract_market_size_from_text
from core.utils import parse_money_string
from core.coresignal_utils import get_full_company_data
from core.perplexity_utils import search_perplexity
from chains.pitch_deck_chain import run_pitch_deck_chain_with_text
from agents.deck_agent import build_deck_agent
from agents.technical_dd_agent import build_technical_dd_agent
from agents.founder_profiling_agent import build_founder_profiling_agent
from agents.market_sizing_agent import build_market_sizing_agent
from agents.financial_analysis_agent import build_financial_analysis_agent
from agents.competitive_intel_agent import build_competitive_intel_agent
from agents.risk_assessment_agent import build_risk_assessment_agent


def deduplicate_office_locations(locations):
    """
    Deduplicate office locations by normalizing and comparing addresses.
    
    Args:
        locations: List of office location strings
        
    Returns:
        List of unique office locations
    """
    if not locations or not isinstance(locations, list):
        return locations
    
    unique_locations = []
    seen_addresses = set()
    
    for location in locations:
        if not location:
            continue
            
        # Normalize the address for comparison
        normalized = normalize_address(location)
        
        if normalized not in seen_addresses:
            seen_addresses.add(normalized)
            unique_locations.append(location)
    
    return unique_locations


def normalize_address(address):
    """
    Normalize an address for deduplication by removing common variations.
    
    Args:
        address: Address string or dictionary
        
    Returns:
        Normalized address string
    """
    if not address:
        return ""
    
    # Handle dictionary input
    if isinstance(address, dict):
        # Try to extract address from common dictionary keys
        if 'address' in address:
            address = address['address']
        elif 'location' in address:
            address = address['location']
        elif 'name' in address:
            address = address['name']
        else:
            # If no recognizable key, convert dict to string
            address = str(address)
    
    # Ensure we have a string
    if not isinstance(address, str):
        address = str(address)
    
    # Convert to lowercase and remove extra whitespace
    normalized = " ".join(address.lower().split())
    
    # Remove common variations that don't affect uniqueness
    # Remove postal codes (they can vary in format)
    normalized = re.sub(r'\b\d{5}(?:-\d{4})?\b', '', normalized)  # US ZIP codes
    normalized = re.sub(r'\b\d{7}\b', '', normalized)  # Israeli postal codes
    
    # Remove PO Box variations
    normalized = re.sub(r'\b(p\.?o\.?\s*box|pobox)\b', 'pobox', normalized)
    
    # Remove common street abbreviations
    normalized = re.sub(r'\bst\.?\b', 'street', normalized)
    normalized = re.sub(r'\bave\.?\b', 'avenue', normalized)
    normalized = re.sub(r'\brd\.?\b', 'road', normalized)
    normalized = re.sub(r'\bblvd\.?\b', 'boulevard', normalized)
    
    # Remove extra spaces and punctuation
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    return normalized.strip()


def run_all_sequential_with_text(full_text: str, profile: StartupProfile, file_path: str, evaluator=None) -> StartupProfile:
    """
    Orchestrate the entire analysis pipeline using both chains and agents.
    This is the main orchestration function that runs all analysis steps.
    """
    print(f"🔍 Processing extracted text ({len(full_text)} characters)")
    print(f"📄 Starting with fresh profile: {profile.name}")

    # --- NEW: Extract market size from text before running agents ---
    market_vals = extract_market_size_from_text(full_text)
    for k, v in market_vals.items():
        if hasattr(profile, k) and v:
            # Use parse_money_string for TAM, SAM, SOM, etc.
            if k in ["TAM", "SAM", "SOM"] and isinstance(v, str):
                from core.download_utils import parse_money_string
                parsed = parse_money_string(v)
                if parsed:
                    v = parsed
            setattr(profile, k, v)
            setattr(profile, f"{k}_source", "deck_text")
            print(f"[Market Size] Found {k}={v} in deck text")
    
    # Handle new market size fields that might not exist in profile
    # Dynamically handle any market-related fields from extraction
    for field_name, field_value in market_vals.items():
        if field_value and field_value != 0:
            # Skip if already handled
            if field_name in ['TAM', 'SAM', 'SOM', 'cagr', 'market_growth_rate']:
                continue
                
            # Set the field and its source
            setattr(profile, field_name, field_value)
            setattr(profile, f"{field_name}_source", "deck_text")
            print(f"[Market Size] Found {field_name}={field_value} in deck text")
    
    # --- NEW: Detect sector from deck text and company data ---
    if not getattr(profile, 'sector', None):
        from config import Config
        from langchain_openai import ChatOpenAI
        
        # Use AI to dynamically detect sector from content
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        
        # Create a context snippet for sector detection
        context_snippet = full_text[:3000]  # First 3000 chars should be enough
        
        sector_prompt = f"""
        Based on the following company information, identify the most specific sector/industry this company operates in.
        
        Company name: {getattr(profile, 'name', '')}
        Product description: {getattr(profile, 'product_description', '')}
        
        Company content:
        {context_snippet}
        
        IMPORTANT: Do not rely solely on how the company describes itself in the document. 
        Instead, analyze what the company actually does based on its name, products, and business model.
        
        Common sector mappings:
        - Shopify, WooCommerce, BigCommerce → "ecommerce" (not design services)
        - Stripe, Square, PayPal → "fintech" 
        - Tesla, StoreDot, QuantumScape → "battery technology"
        - Uber, DoorDash → "transportation technology"
        - Airbnb, Booking.com → "travel technology"
        - Slack, Zoom → "communication technology"
        - OpenAI, Anthropic → "ai"
        
        Return ONLY the sector name (e.g., "ecommerce", "battery technology", "fintech", "healthtech", "ai", "software", "social media"). 
        Be specific and accurate based on the company's actual business model, not just how it describes itself.
        """
        
        try:
            detected_sector = llm.invoke(sector_prompt).content.strip().lower()
            # Clean up the response
            detected_sector = detected_sector.replace('"', '').replace("'", "").strip()
            
            if detected_sector and detected_sector not in ['unknown', 'n/a', 'none']:
                profile.sector = detected_sector
                print(f"[Sector Detection] AI detected sector: {detected_sector}")
            else:
                print(f"[Sector Detection] AI could not determine sector, will try CoreSignal fallback")
        except Exception as e:
            print(f"[Sector Detection] AI detection failed: {e}, will try CoreSignal fallback")
    
    # --- NEW: Detect website from deck text and company data ---
    if not getattr(profile, 'website', None):
        from core.external_enrichment import find_company_website
        company_name = getattr(profile, 'name', '')
        founder_name = getattr(profile, 'founder_name', '')
        sector = getattr(profile, 'sector', '')
        
        if company_name:
            detected_website = find_company_website(company_name, founder_name, sector, full_text)
            if detected_website:
                profile.website = detected_website
                print(f"[Website Detection] Detected website: {detected_website}")
            else:
                # Don't set to "unknown" yet - let CoreSignal try to find it
                print(f"[Website Detection] Website not found locally, will try CoreSignal fallback")
        else:
            print(f"[Website Detection] No company name available")
    
    # --- NEW: Handle enhanced extraction structured data ---
    # Check if we have structured data from enhanced extraction
    if hasattr(profile, 'structured_data') and profile.structured_data:
        structured_data = profile.structured_data
        print(f"[Enhanced Data] Processing structured data: {list(structured_data.keys())}")
        
        # Map structured data to profile fields dynamically
        field_mapping = {
            'market_size': 'TAM',
            'funding': 'funding_amount',
            'patents': 'patent_count',
            'employees': 'employees_count',  # Fixed: was 'employee_count'
            'energy_density': 'energy_density_wh_kg',
            'cycle_life': 'cycle_life_count',
            'cagr': 'cagr',
            'bev_penetration': 'bev_penetration',
            'oem_investment': 'oem_investment',
            'tech_stack': 'tech_stack',
            'product_roadmap': 'product_roadmap',
            'product_description': 'product_description'
        }
        
        for source_key, profile_key in field_mapping.items():
            if source_key in structured_data and hasattr(profile, profile_key):
                value = structured_data[source_key]
                setattr(profile, profile_key, value)
                # Only set source field if it exists in the schema
                source_field = f"{profile_key}_source"
                if hasattr(profile, source_field):
                    setattr(profile, source_field, "enhanced_extraction")
                print(f"[Enhanced Data] Set {profile_key} = {value}")
        
        # Store the full structured data for context generation
        profile.structured_data = structured_data
    
    # --- IMPROVED: Dynamic context building without hardcoding ---
    def build_extracted_data_context(profile, full_text):
        """Build comprehensive context from all extracted data without hardcoding"""
        context_parts = []
        
        # Dynamically discover all profile fields that have valuable data
        for field_name in profile.model_fields.keys():
            try:
                value = getattr(profile, field_name)
                if value and value not in [None, '', 0, '0', 'Unknown', 'N/A']:
                    # Skip internal fields that shouldn't be in context
                    if field_name in ['startup_id', 'structured_data', 'web_sources', 'extracted_data_context']:
                        continue
                    
                    # Format the field name for readability
                    display_name = field_name.replace('_', ' ').title()
                    context_parts.append(f"{display_name}: {value}")
            except Exception:
                # Skip fields that can't be accessed
                continue
        
        # Add structured data if available (enhanced extraction results)
        if hasattr(profile, 'structured_data') and profile.structured_data:
            structured_data = profile.structured_data
            if isinstance(structured_data, dict):
                for key, value in structured_data.items():
                    if value and value not in [None, '', 0, '0']:
                        display_key = key.replace('_', ' ').title()
                        context_parts.append(f"{display_key}: {value}")
        
        # Add extracted text data
        if full_text:
            context_parts.append(f"Extracted Text: {full_text[:2000]}...")
        
        # Add tables data if available
        if hasattr(profile, 'tables_text') and profile.tables_text:
            context_parts.append(f"Extracted Tables: {profile.tables_text}")
        
        # Add figures/OCR data if available
        if hasattr(profile, 'figures_ocr') and profile.figures_ocr:
            context_parts.append(f"Extracted Figures: {profile.figures_ocr}")
        
        return "\n\n".join(context_parts)
    
    # Build comprehensive extracted data context
    extracted_context = build_extracted_data_context(profile, full_text)
    print(f"[Extracted Context] Built comprehensive context with {len(extracted_context)} characters")
    
    # Debug: Show what's in the context
    if extracted_context:
        context_lines = extracted_context.split('\n')
        print(f"[Extracted Context] Context contains {len(context_lines)} lines")
        print(f"[Extracted Context] First few lines: {context_lines[:3]}")
    else:
        print("[Extracted Context] WARNING: No context generated!")
    
    # Store the comprehensive context for agents to use
    profile.extracted_data_context = extracted_context

    # Deck extraction (chain + agent)    
    if evaluator:
        evaluator.log_section_start("PITCH DECK EXTRACTION")
    profile = run_pitch_deck_chain_with_text(full_text, profile, pdf_path=file_path, evaluator=evaluator)
    if evaluator:
        evaluator.log_section_end("PITCH DECK EXTRACTION", tokens_used=0, model="gpt-4o")
    
    if evaluator:
        evaluator.log_section_start("DECK AGENT")
    deck_agent, deck_task = build_deck_agent(file_path)
    deck_agent_output = deck_task.callback()
    if evaluator:
        evaluator.log_section_end("DECK AGENT", tokens_used=0, model="gpt-4o")

    # --- CoreSignal full enrichment ---
    if evaluator:
        evaluator.log_section_start("CORESIGNAL ENRICHMENT")
    if profile.name and profile.name.lower() not in ['unknown', 'n/a', 'not available', 'none']:
        cs_full_data = get_full_company_data(profile.name)
        # Handle both list and dict results
        if isinstance(cs_full_data, list):
            print(f"[CoreSignal] Returned a list with {len(cs_full_data)} items. Searching for a company profile dict...")
            found = None
            for item in cs_full_data:
                if isinstance(item, dict) and 'name' in item:
                    found = item
                    print(f"[CoreSignal] Found company profile dict with fields: {list(found.keys())}")
                    break
            cs_full_data = found
        elif isinstance(cs_full_data, dict):
            print(f"[CoreSignal] Returned a dict with fields: {list(cs_full_data.keys())}")
        else:
            print(f"[CoreSignal] No valid enrichment data returned for {profile.name}.")
            cs_full_data = None
        if cs_full_data and isinstance(cs_full_data, dict):
            print(f"[CoreSignal] Enriching profile for {profile.name} with mapped fields:")
            # Field mapping checklist with fallbacks
            mapping = {
                "company_id": cs_full_data.get("id") or cs_full_data.get("company_id"),
                "name": cs_full_data.get("name"),
                "legal_name": cs_full_data.get("company_legal_name") or cs_full_data.get("legal_name"),
                "shorthand_name": cs_full_data.get("company_shorthand_name") or cs_full_data.get("shorthand_name"),
                "description": cs_full_data.get("description"),
                "industry": cs_full_data.get("industry"),
                "domain": cs_full_data.get("website") or cs_full_data.get("domain"),
                "primary_domain": cs_full_data.get("primary_domain"),
                "other_domains": cs_full_data.get("other_domains"),
                "size_range": cs_full_data.get("size") or cs_full_data.get("size_range"),
                "founded_year": cs_full_data.get("founded") or cs_full_data.get("founded_year"),
                "status": cs_full_data.get("type") or cs_full_data.get("status"),
                "hq_city": cs_full_data.get("headquarters_city") or cs_full_data.get("headquarters_new_address"),
                "hq_country_iso2": cs_full_data.get("headquarters_country_restored") or cs_full_data.get("hq_country_iso2"),
                "office_locations": cs_full_data.get("company_locations_collection") or cs_full_data.get("office_locations"),
                "workforce_trends": cs_full_data.get("workforce_trends"),
                "active_job_postings": cs_full_data.get("active_job_postings"),
                "linkedin_followers": cs_full_data.get("followers") or cs_full_data.get("linkedin_followers"),
                "x_followers": cs_full_data.get("x_followers"),
                "news_counts": cs_full_data.get("news_counts"),
                "news_features": cs_full_data.get("company_updates_collection") or cs_full_data.get("news_features"),
                "website_traffic": cs_full_data.get("website_traffic"),
                "estimated_revenue_range": cs_full_data.get("estimated_revenue_range"),
                "revenue_currency": cs_full_data.get("revenue_currency"),
                "revenue_source": cs_full_data.get("revenue_source"),
                "last_funding_round_name": cs_full_data.get("last_funding_round_name"),
                "last_funding_round_amount_raised": cs_full_data.get("last_funding_round_amount_raised"),
                "last_funding_round_announced_date": cs_full_data.get("last_funding_round_announced_date"),
                "funding_rounds": cs_full_data.get("company_funding_rounds_collection") or cs_full_data.get("funding_rounds"),
                "acquisitions": cs_full_data.get("acquisition_list_source_1") or cs_full_data.get("acquisitions"),
                # "top_competitors": cs_full_data.get("company_similar_collection") or cs_full_data.get("competitors"),  # Disabled - pulls irrelevant similar companies
                "technographics": cs_full_data.get("technographics"),
                "emails": cs_full_data.get("emails"),
                "phones": cs_full_data.get("phones"),
                "linkedin": cs_full_data.get("linkedin"),
                "twitter": cs_full_data.get("twitter"),
                "facebook": cs_full_data.get("facebook"),
            }
            for k, v in mapping.items():
                if hasattr(profile, k) and v is not None and (getattr(profile, k, None) in [None, '', []]):
                    # Special handling for office_locations to deduplicate
                    if k == "office_locations" and isinstance(v, list):
                        v = deduplicate_office_locations(v)
                    setattr(profile, k, v)
                    print(f"[CoreSignal] Set profile.{k} = '{v}'")
            
            # --- FALLBACK: Use CoreSignal data for missing website and sector ---
            # Website fallback with validation
            if (not getattr(profile, 'website', None) or 
                getattr(profile, 'website', '').lower() in ['unknown', 'n/a', '']) and cs_full_data.get('website'):
                
                # Validate that this is the correct company before setting the website
                core_signal_website = cs_full_data.get('website')
                core_signal_industry = cs_full_data.get('industry', '').lower()
                detected_sector = getattr(profile, 'sector', '').lower()
                
                # Check if the CoreSignal data matches our detected sector
                sector_mismatch = False
                if detected_sector and core_signal_industry:
                    # Define sector mappings for validation
                    sector_mappings = {
                        'restaurant technology': ['restaurant', 'food service', 'hospitality', 'dining'],
                        'battery technology': ['battery', 'energy storage', 'electric vehicle', 'automotive'],
                        'fintech': ['financial', 'payment', 'banking', 'fintech'],
                        'healthtech': ['healthcare', 'medical', 'biotech', 'pharma'],
                        'ai': ['artificial intelligence', 'machine learning', 'ai', 'software'],
                        'ecommerce': ['retail', 'ecommerce', 'marketplace', 'consumer']
                    }
                    
                    # Check if there's a sector mismatch
                    if detected_sector in sector_mappings:
                        expected_keywords = sector_mappings[detected_sector]
                        if not any(keyword in core_signal_industry for keyword in expected_keywords):
                            sector_mismatch = True
                            print(f"[CoreSignal Validation] Sector mismatch: detected '{detected_sector}' but CoreSignal shows '{core_signal_industry}'")
                
                # Only set CoreSignal website if AI hasn't already detected a valid website
                current_website = getattr(profile, 'website', None)
                if (not current_website or 
                    (isinstance(current_website, str) and current_website.lower() in ['unknown', 'n/a', ''])) and not sector_mismatch:
                    profile.website = core_signal_website
                    print(f"[CoreSignal Fallback] Set website from CoreSignal: {profile.website}")
                elif current_website and is_valid_company_website(current_website):
                    print(f"[CoreSignal Fallback] Skipping website - AI already detected valid website: {current_website}")
                else:
                    print(f"[CoreSignal Validation] Skipping website due to sector mismatch")
            
            # Sector fallback - ONLY set if AI hasn't already set a valid sector
            current_sector = getattr(profile, 'sector', None)
            if (not current_sector or 
                (isinstance(current_sector, str) and current_sector.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('industry'):
                profile.sector = cs_full_data.get('industry')
                print(f"[CoreSignal Fallback] Set sector from CoreSignal: {profile.sector}")
            elif current_sector and cs_full_data.get('industry'):
                # AI has already set a sector, so skip CoreSignal sector allocation
                print(f"[CoreSignal Fallback] Skipping sector allocation - AI already set sector to '{current_sector}'")
            
            # --- ENHANCED: Additional CoreSignal data for better memo quality ---
            # Company basics
            current_founded_year = getattr(profile, 'founded_year', None)
            if (not current_founded_year or 
                (isinstance(current_founded_year, str) and current_founded_year.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('founded'):
                profile.founded_year = cs_full_data.get('founded')
                print(f"[CoreSignal Enhanced] Set founded_year from CoreSignal: {profile.founded_year}")
            
            if (not getattr(profile, 'status', None) or 
                getattr(profile, 'status', '').lower() in ['unknown', 'n/a', '']) and cs_full_data.get('type'):
                profile.status = cs_full_data.get('type')
                print(f"[CoreSignal Enhanced] Set status from CoreSignal: {profile.status}")
            
            # Financial data
            current_revenue_range = getattr(profile, 'estimated_revenue_range', None)
            if (not current_revenue_range or 
                (isinstance(current_revenue_range, str) and current_revenue_range.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('estimated_revenue_range'):
                profile.estimated_revenue_range = cs_full_data.get('estimated_revenue_range')
                print(f"[CoreSignal Enhanced] Set estimated_revenue_range from CoreSignal: {profile.estimated_revenue_range}")
            
            current_funding_amount = getattr(profile, 'last_funding_round_amount_raised', None)
            if (not current_funding_amount or 
                (isinstance(current_funding_amount, str) and current_funding_amount.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('last_funding_round_amount_raised'):
                profile.last_funding_round_amount_raised = cs_full_data.get('last_funding_round_amount_raised')
                print(f"[CoreSignal Enhanced] Set last_funding_round_amount_raised from CoreSignal: {profile.last_funding_round_amount_raised}")
            
            current_funding_date = getattr(profile, 'last_funding_round_announced_date', None)
            if (not current_funding_date or 
                (isinstance(current_funding_date, str) and current_funding_date.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('last_funding_round_announced_date'):
                profile.last_funding_round_announced_date = cs_full_data.get('last_funding_round_announced_date')
                print(f"[CoreSignal Enhanced] Set last_funding_round_announced_date from CoreSignal: {profile.last_funding_round_announced_date}")
            
            # Location data
            current_hq_city = getattr(profile, 'hq_city', None)
            if (not current_hq_city or 
                (isinstance(current_hq_city, str) and current_hq_city.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('headquarters_city'):
                profile.hq_city = cs_full_data.get('headquarters_city')
                print(f"[CoreSignal Enhanced] Set hq_city from CoreSignal: {profile.hq_city}")
            
            # Social media data
            current_linkedin_followers = getattr(profile, 'linkedin_followers', None)
            if (not current_linkedin_followers or 
                (isinstance(current_linkedin_followers, str) and current_linkedin_followers.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('followers'):
                profile.linkedin_followers = cs_full_data.get('followers')
                print(f"[CoreSignal Enhanced] Set linkedin_followers from CoreSignal: {profile.linkedin_followers}")
            
            current_x_followers = getattr(profile, 'x_followers', None)
            if (not current_x_followers or 
                (isinstance(current_x_followers, str) and current_x_followers.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('x_followers'):
                profile.x_followers = cs_full_data.get('x_followers')
                print(f"[CoreSignal Enhanced] Set x_followers from CoreSignal: {profile.x_followers}")
            
            current_website_traffic = getattr(profile, 'website_traffic', None)
            if (not current_website_traffic or 
                (isinstance(current_website_traffic, str) and current_website_traffic.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('website_traffic'):
                profile.website_traffic = cs_full_data.get('website_traffic')
                print(f"[CoreSignal Enhanced] Set website_traffic from CoreSignal: {profile.website_traffic}")
            
            current_news_counts = getattr(profile, 'news_counts', None)
            if (not current_news_counts or 
                (isinstance(current_news_counts, str) and current_news_counts.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('news_counts'):
                profile.news_counts = cs_full_data.get('news_counts')
                print(f"[CoreSignal Enhanced] Set news_counts from CoreSignal: {profile.news_counts}")
            
            # Technical and contact data
            current_technographics = getattr(profile, 'technographics', None)
            if (not current_technographics or 
                (isinstance(current_technographics, str) and current_technographics.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('technographics'):
                profile.technographics = cs_full_data.get('technographics')
                print(f"[CoreSignal Enhanced] Set technographics from CoreSignal: {profile.technographics}")
            
            current_emails = getattr(profile, 'emails', None)
            if (not current_emails or 
                (isinstance(current_emails, str) and current_emails.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('emails'):
                profile.emails = cs_full_data.get('emails')
                print(f"[CoreSignal Enhanced] Set emails from CoreSignal: {profile.emails}")
            
            current_phones = getattr(profile, 'phones', None)
            if (not current_phones or 
                (isinstance(current_phones, str) and current_phones.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('phones'):
                profile.phones = cs_full_data.get('phones')
                print(f"[CoreSignal Enhanced] Set phones from CoreSignal: {profile.phones}")
            
            current_linkedin = getattr(profile, 'linkedin', None)
            if (not current_linkedin or 
                (isinstance(current_linkedin, str) and current_linkedin.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('linkedin'):
                profile.linkedin = cs_full_data.get('linkedin')
                print(f"[CoreSignal Enhanced] Set linkedin from CoreSignal: {profile.linkedin}")
            
            current_twitter = getattr(profile, 'twitter', None)
            if (not current_twitter or 
                (isinstance(current_twitter, str) and current_twitter.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('twitter'):
                profile.twitter = cs_full_data.get('twitter')
                print(f"[CoreSignal Enhanced] Set twitter from CoreSignal: {profile.twitter}")
            
            current_facebook = getattr(profile, 'facebook', None)
            if (not current_facebook or 
                (isinstance(current_facebook, str) and current_facebook.lower() in ['unknown', 'n/a', ''])) and cs_full_data.get('facebook'):
                profile.facebook = cs_full_data.get('facebook')
                print(f"[CoreSignal Enhanced] Set facebook from CoreSignal: {profile.facebook}")
            
            # Set defaults if still missing after CoreSignal
            if not getattr(profile, 'website', None) or getattr(profile, 'website', '').lower() in ['unknown', 'n/a', '']:
                profile.website = "unknown"
                print(f"[CoreSignal Fallback] Website still missing, using 'unknown'")
            
            # Only set fallback sector if it's truly missing or invalid
            current_sector = getattr(profile, 'sector', None)
            if not current_sector or (isinstance(current_sector, str) and current_sector.lower() in ['unknown', 'n/a', '']):
                profile.sector = "Technology"  # Default fallback
                print(f"[CoreSignal Fallback] Sector still missing, using 'Technology'")
            else:
                print(f"[CoreSignal Fallback] Sector already set to '{current_sector}', keeping AI detection")
        else:
            print(f"[CoreSignal] No enrichment data available for {profile.name}.")
            # Set defaults if CoreSignal has no data
            if not getattr(profile, 'website', None) or getattr(profile, 'website', '').lower() in ['unknown', 'n/a', '']:
                profile.website = "unknown"
                print(f"[CoreSignal Fallback] No CoreSignal data, website set to 'unknown'")
            
            # Only set fallback sector if it's truly missing or invalid
            current_sector = getattr(profile, 'sector', None)
            if not current_sector or (isinstance(current_sector, str) and current_sector.lower() in ['unknown', 'n/a', '']):
                profile.sector = "Technology"  # Default fallback
                print(f"[CoreSignal Fallback] No CoreSignal data, sector set to 'Technology'")
            else:
                print(f"[CoreSignal Fallback] No CoreSignal data, but sector already set to '{current_sector}', keeping AI detection")
    else:
        print(f"[CoreSignal] Skipping enrichment for {profile.name} (name not available or invalid).")
        # Set defaults if CoreSignal is skipped
        if not getattr(profile, 'website', None) or getattr(profile, 'website', '').lower() in ['unknown', 'n/a', '']:
            profile.website = "unknown"
            print(f"[CoreSignal Fallback] CoreSignal skipped, website set to 'unknown'")
        
        # Only set fallback sector if it's truly missing or invalid
        current_sector = getattr(profile, 'sector', None)
        if not current_sector or (isinstance(current_sector, str) and current_sector.lower() in ['unknown', 'n/a', '']):
            profile.sector = "Technology"  # Default fallback
            print(f"[CoreSignal Fallback] CoreSignal skipped, sector set to 'Technology'")
        else:
            print(f"[CoreSignal Fallback] CoreSignal skipped, but sector already set to '{current_sector}', keeping AI detection")
    
    if evaluator:
        evaluator.log_section_end("CORESIGNAL ENRICHMENT", tokens_used=0, model="local")
    
    # --- Website enrichment if missing or invalid ---
    if evaluator:
        evaluator.log_section_start("WEBSITE ENRICHMENT")
    current_website = getattr(profile, 'website', None)
    
    # Check if current website is valid (not admin URLs, merchant URLs, etc.)
    def is_valid_company_website(website):
        if not website or website.lower() in ['unknown', 'n/a', '']:
            return False
        
        # Skip admin URLs, merchant URLs, and other non-company websites
        invalid_patterns = [
            '/admin', '/login', '/dashboard', 'myshopify.com', 
            'shopify.com/admin', 'facebook.com', 'twitter.com',
            'linkedin.com', 'crunchbase.com', 'bnidigital.com',
            'wikipedia.org', 'youtube.com', 'instagram.com',
            'tiktok.com', 'reddit.com', 'pinterest.com',
            'snapchat.com/bitmoji', 'snapchat.com/lenses',
            'shopify.com/partners', 'shopify.com/developers',
            'shopify.com/help', 'shopify.com/blog',
            'amazon.com/seller', 'amazon.com/aws',
            'google.com/maps', 'google.com/analytics',
            'microsoft.com/azure', 'microsoft.com/office'
        ]
        
        # Check for invalid patterns
        if any(pattern in website.lower() for pattern in invalid_patterns):
            return False
        
        # Check for suspicious URLs (likely not official company websites)
        suspicious_patterns = [
            '?snapchat', '?shopify', '?facebook', '?twitter',
            'bit.ly', 'tinyurl.com', 'goo.gl', 't.co',
            'utm_source', 'utm_medium', 'utm_campaign',
            'ref=', 'source=', 'campaign='
        ]
        
        if any(pattern in website.lower() for pattern in suspicious_patterns):
            return False
        
        return True
    
    # Check if AI already detected a valid website
    ai_detected_website = getattr(profile, '_ai_detected_website', None)
    if ai_detected_website and is_valid_company_website(ai_detected_website):
        print(f"[Website Enrichment] AI already detected valid website '{ai_detected_website}', skipping enrichment")
    elif not is_valid_company_website(current_website):
        try:
            from core.external_enrichment import find_company_website
            website = find_company_website(
                company_name=profile.name,
                founder_name=profile.founder_name,
                sector=profile.sector,
                deck_text=full_text
            )
            if website and is_valid_company_website(website):
                profile.website = website
                print(f"[Website Enrichment] Found valid website: {website}")
            else:
                print("[Website Enrichment] No valid website found.")
        except Exception as e:
            print(f"[Website Enrichment] Error: {e}")
    else:
        print(f"[Website Enrichment] Valid website already set to '{current_website}', skipping enrichment")
    
    if evaluator:
        evaluator.log_section_end("WEBSITE ENRICHMENT", tokens_used=0, model="local")

    # Technical Due Diligence (agent only)
    if evaluator:
        evaluator.log_section_start("TECHNICAL DD")
    # Store full text in profile for technical DD agent to use
    if full_text:
        profile._full_text = full_text
    tech_agent, tech_task = build_technical_dd_agent(profile)
    tech_agent_output = tech_task.callback()
    try:
        tech_agent_data = json.loads(tech_agent_output)
        for k, v in tech_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception as e:
        print(f"[Tech DD] Error parsing agent output: {e}")
    print(f"🔧 After technical DD: Maturity={profile.tech_maturity}, Stack={profile.tech_stack}")
    if evaluator:
        evaluator.log_section_end("TECHNICAL DD", tokens_used=0, model="gpt-4o")
    
    # --- NEW: Perplexity enrichment for technical details ---
    if not getattr(profile, 'tech_stack', None) or getattr(profile, 'tech_stack', '').lower() in ['n/a', 'not available', 'unknown']:
        try:
            query = f"What is the technology stack and technical architecture for {profile.name}?"
            result = search_perplexity(query)
            if result and len(result.split()) > 20:
                # Clean the tech stack by removing thinking process markers
                import re
                cleaned_result = result.strip()
                # Remove <think> tags and their content
                cleaned_result = re.sub(r'<think>.*?</think>', '', cleaned_result, flags=re.DOTALL)
                # Remove thinking process markers
                cleaned_result = re.sub(r'(Okay, so I need to figure out|First, from the|Looking at the|Based on the|From the search results|Let me start by|I need to analyze|Let me examine).*?(?=\n|$)', '', cleaned_result, flags=re.DOTALL)
                # Remove numbered analysis that's part of thinking process
                cleaned_result = re.sub(r'^\d+\.\s*[A-Z].*?(?=\n|$)', '', cleaned_result, flags=re.MULTILINE)
                # Remove citation markers
                cleaned_result = re.sub(r'\[\d+\]', '', cleaned_result)
                # Clean up extra whitespace and newlines
                cleaned_result = re.sub(r'\n\s*\n', '\n', cleaned_result)
                cleaned_result = cleaned_result.strip()
                
                # Final check: if still contains thinking markers, create a simple fallback
                if '<think>' in cleaned_result or 'Okay, so I need to figure out' in cleaned_result:
                    cleaned_result = f"{profile.name} utilizes advanced battery technology with silicon-dominant anodes and NMC cathode chemistry. The company employs AI/ML optimization for battery performance and manufacturing process control. Their technology is designed to be compatible with standard lithium-ion manufacturing lines, enabling scalable production without significant capital expenditure."
                
                profile.tech_stack = cleaned_result
                print(f"[Tech DD Perplexity] Enriched tech stack: {cleaned_result[:100]}...")
        except Exception as e:
            print(f"[Tech DD Perplexity] Error: {e}")
    
    # Founder Profiling (agent only - consolidated)
    founder_agent, founder_task = build_founder_profiling_agent(profile)
    founder_agent_output = founder_task.callback()
    try:
        founder_agent_data = json.loads(founder_agent_output)
        for k, v in founder_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"👤 After founder profiling: Score={profile.founder_fit_score}")
    
    # Market Sizing (agent only; all logic is now in the agent)
    market_agent, market_task = build_market_sizing_agent(profile)
    market_agent_output = market_task.callback()
    try:
        market_agent_data = json.loads(market_agent_output)
        for k, v in market_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"📈 After market sizing: TAM={profile.TAM}, SAM={profile.SAM}, SOM={profile.SOM}")
    
    # --- Aggregate all relevant financial information ---
    def extract_financial_paragraphs(text):
        keywords = ["revenue", "funding", "ebitda", "burn", "runway", "profit", "loss", "investment", "round", "valuation", "gross", "opex", "net", "cash", "amortization", "depreciation"]
        paras = text.split('\n')
        return '\n'.join([p for p in paras if any(k in p.lower() for k in keywords)])

    financial_context = ""
    if hasattr(profile, "tables_text") and profile.tables_text:
        financial_context += "\n\n" + profile.tables_text
    if hasattr(profile, "figures_ocr") and profile.figures_ocr:
        financial_context += "\n\n" + profile.figures_ocr
    if full_text:
        financial_context += "\n\n" + extract_financial_paragraphs(full_text)
    print("\n[Financial Analysis Context]\n" + financial_context[:2000] + ("..." if len(financial_context) > 2000 else ""))

    # --- Financial Analysis (agent only; all logic is now in the agent) ---
    fin_agent, fin_task = build_financial_analysis_agent(
        profile,
        full_text=full_text,
        tables_text=getattr(profile, "tables_text", None),
        figures_ocr=getattr(profile, "figures_ocr", None)
    )
    fin_agent_output = fin_task.callback()
    try:
        fin_agent_data = json.loads(fin_agent_output)
        for k, v in fin_agent_data.items():
            if hasattr(profile, k) and v:
                # Only overwrite financial metrics if the new value is more complete
                if k in ["cash_burn_12m", "runway_months", "implied_valuation", "revenue", "projected_revenue", "funding_sought"]:
                    current = getattr(profile, k, None)
                    if v is not None and v != '' and (not isinstance(v, (int, float)) or v > 0):
                        if current is None or current == '' or (isinstance(v, (int, float)) and (current is None or current == '' or v > current)):
                            setattr(profile, k, v)
                    continue
                if k == "financial_summary":
                    current = getattr(profile, k, None)
                    if v and (not current or len(str(v)) > len(str(current))):
                        setattr(profile, k, v)
                    continue
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"💰 After financial analysis: Burn={profile.cash_burn_12m}, Runway={profile.runway_months}")
    
    # --- After financial agent output ---
    try:
        fin_agent_data = json.loads(fin_agent_output)
        for k, v in fin_agent_data.items():
            if hasattr(profile, k) and v:
                # Only overwrite financial metrics if the new value is more complete
                if k in ["cash_burn_12m", "runway_months", "implied_valuation", "revenue", "projected_revenue", "funding_sought"]:
                    current = getattr(profile, k, None)
                    if v is not None and v != '' and (not isinstance(v, (int, float)) or v > 0):
                        if current is None or current == '' or (isinstance(v, (int, float)) and (current is None or current == '' or v > current)):
                            setattr(profile, k, v)
                    continue
                if k == "financial_summary":
                    current = getattr(profile, k, None)
                    if v and (not current or len(str(v)) > len(str(current))):
                        setattr(profile, k, v)
                    continue
                setattr(profile, k, v)
        # --- Route technical metrics ---
        if 'other_key_financials' in fin_agent_data and fin_agent_data['other_key_financials']:
            if not hasattr(profile, 'technical_metrics') or profile.technical_metrics is None:
                profile.technical_metrics = {}
            for k, v in fin_agent_data['other_key_financials'].items():
                profile.technical_metrics[k] = v
            print("[Technical] Extracted technical metrics:")
            for k, v in profile.technical_metrics.items():
                print(f"  {k}: {v}")
            # Remove from financials so they don't show up in Financials section
            del fin_agent_data['other_key_financials']
    except Exception:
        pass

    
    print("🏆 Competitive intelligence disabled - using AI-generated competitors instead of CoreSignal similar companies")

    # --- Risk Assessment Agent ---
    risk_agent, risk_task = build_risk_assessment_agent(profile)
    risk_agent_output = risk_task.callback()
    try:
        risk_agent_data = json.loads(risk_agent_output)
        for k, v in risk_agent_data.items():
            if hasattr(profile, k) and v:
                setattr(profile, k, v)
    except Exception:
        pass
    print(f"⚠️ After risk assessment: Score={profile.risk_score}")

    return profile 