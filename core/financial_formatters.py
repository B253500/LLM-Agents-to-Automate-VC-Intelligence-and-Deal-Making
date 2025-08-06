"""
Financial formatting utilities for investment memo generation.
Extracted from main.py to improve code organization.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.schemas import StartupProfile

def format_money_display(value, currency="US$"):
    """Format money values for display like 'US$ 57.0M'."""
    if value is None:
        return None
    
    try:
        value = float(value)
        if value >= 1e9:
            return f"{currency} {value/1e9:.1f}B"
        elif value >= 1e6:
            return f"{currency} {value/1e6:.1f}M"
        elif value >= 1e3:
            return f"{currency} {value/1e3:.1f}K"
        else:
            return f"{currency} {value:,.0f}"
    except (ValueError, TypeError):
        return str(value)


def format_enhanced_financials_section(profile: StartupProfile, current_date: str) -> str:
    """Enhanced financial section using the financial analysis agent."""
    try:
        from agents.financial_analysis_agent import build_financial_analysis_agent
        
        # Build the financial analysis agent
        agent, task = build_financial_analysis_agent(
            profile,
            full_text=getattr(profile, '_full_text', ''),
            tables_text=getattr(profile, 'tables_text', ''),
            figures_ocr=getattr(profile, 'figures_ocr', '')
        )
        
        # Get the agent output
        agent_output = task.callback()
        
        # Parse the JSON output
        import json
        agent_data = json.loads(agent_output)
        
        # Update the profile with agent data
        for key, value in agent_data.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        
        # Use the new clean financial formatting
        return format_clean_financials_section(profile, current_date)
        
    except Exception as e:
        print(f"[Financial Agent] Error: {e}")
        # Fallback to clean formatting
        return format_clean_financials_section(profile, current_date)


def format_clean_financials_section(profile: StartupProfile, current_date: str) -> str:
    """Enhanced financial section that displays all extracted financial data."""
    lines = []
    
    # Get all available financial metrics
    implied_valuation = getattr(profile, 'implied_valuation', None)
    latest_round_amount = getattr(profile, 'latest_round_amount_display', None) or getattr(profile, 'latest_round_amount', None)
    total_funding_raised = getattr(profile, 'total_funding_raised_display', None) or getattr(profile, 'total_funding_raised', None)
    web_sources = getattr(profile, 'web_sources', [])
    
    # NEW: Get enhanced financial data from our extraction
    revenue = getattr(profile, 'revenue', None)
    mrr = getattr(profile, 'mrr', None)
    gmv = getattr(profile, 'gmv', None)
    cagr = getattr(profile, 'cagr', None)
    growth_rate = getattr(profile, 'growth_rate', None)
    gross_profit = getattr(profile, 'gross_profit', None)
    revenue_per_merchant = getattr(profile, 'revenue_per_merchant', None)
    subscription_pricing = getattr(profile, 'subscription_pricing', None)
    merchants = getattr(profile, 'merchants', None)
    
    # Check if we have any financial data
    has_financial_data = any([
        implied_valuation, latest_round_amount, total_funding_raised,
        revenue, mrr, gmv, cagr, growth_rate, gross_profit,
        revenue_per_merchant, subscription_pricing, merchants
    ])
    
    if not has_financial_data:
        return f"**📊 Financial Analysis**\n\nNo detailed financials were disclosed in the deck or public sources as of {current_date}. We recommend requesting a financial summary from the company, including revenue, burn rate, runway, and recent funding rounds."
    
    lines.append("**📊 Financial Analysis**")
    lines.append("")
    
    # NEW: Display enhanced financial metrics from deck extraction
    deck_metrics = []
    
    if revenue:
        formatted_revenue = format_money_display(revenue)
        deck_metrics.append(f"• **Revenue**: {formatted_revenue}")
    
    if mrr:
        formatted_mrr = format_money_display(mrr)
        deck_metrics.append(f"• **Monthly Recurring Revenue (MRR)**: {formatted_mrr}")
    
    if gmv:
        formatted_gmv = format_money_display(gmv)
        deck_metrics.append(f"• **Gross Merchandise Value (GMV)**: {formatted_gmv}")
    
    if cagr:
        deck_metrics.append(f"• **Compound Annual Growth Rate (CAGR)**: {cagr}%")
    
    if growth_rate:
        deck_metrics.append(f"• **Growth Rate**: {growth_rate}%")
    
    if gross_profit:
        formatted_profit = format_money_display(gross_profit)
        deck_metrics.append(f"• **Gross Profit**: {formatted_profit}")
    
    if revenue_per_merchant:
        deck_metrics.append(f"• **Revenue per Merchant**: {revenue_per_merchant}")
    
    if merchants:
        deck_metrics.append(f"• **Active Merchants**: {merchants}")
    
    if subscription_pricing:
        deck_metrics.append(f"• **Subscription Pricing**: {subscription_pricing}")
    
    # Display deck metrics if available
    if deck_metrics:
        lines.append("**📈 Key Financial Metrics (from Deck):**")
        lines.append("")
        lines.extend(deck_metrics)
        lines.append("")
    
    # Add web-sourced financial data
    web_metrics = []
    
    if implied_valuation:
        if isinstance(implied_valuation, (int, float)) and implied_valuation > 1_000_000:
            web_metrics.append(f"• **Current Valuation**: ${implied_valuation:,.0f}")
        elif isinstance(implied_valuation, str) and implied_valuation.strip():
            web_metrics.append(f"• **Current Valuation**: {implied_valuation}")
    
    if latest_round_amount:
        if isinstance(latest_round_amount, (int, float)) and latest_round_amount > 10_000:
            web_metrics.append(f"• **Latest Funding Round**: ${latest_round_amount:,.0f}")
        elif isinstance(latest_round_amount, str) and latest_round_amount.strip():
            web_metrics.append(f"• **Latest Funding Round**: {latest_round_amount}")
    
    if total_funding_raised:
        if isinstance(total_funding_raised, (int, float)) and total_funding_raised > 100_000:
            web_metrics.append(f"• **Total Funding Raised**: ${total_funding_raised:,.0f}")
        elif isinstance(total_funding_raised, str) and total_funding_raised.strip():
            web_metrics.append(f"• **Total Funding Raised**: {total_funding_raised}")
    
    # Display web-sourced metrics if available
    if web_metrics:
        lines.append("**🌐 Web-Sourced Financial Data:**")
        lines.append("")
        lines.extend(web_metrics)
        lines.append("")
    
    # Add data sources if available
    if web_sources:
        lines.append("**🔗 Data Sources**")
        for source in web_sources[:3]:  # Limit to 3 sources for better coverage
            # Handle both markdown links [text](url) and plain URLs
            if source.startswith('http'):
                # Extract domain name for cleaner display
                from urllib.parse import urlparse
                try:
                    parsed = urlparse(source)
                    domain = parsed.netloc
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    lines.append(f"• [{domain}]({source})")
                except:
                    lines.append(f"• {source}")
            elif '[' in source and '](' in source and ')' in source:
                # Extract URL from markdown link [text](url)
                url_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', source)
                if url_match:
                    text = url_match.group(1)
                    url = url_match.group(2)
                    lines.append(f"• [{text}]({url})")
            else:
                # Fallback: display as-is
                lines.append(f"• {source}")
    
    return "\n".join(lines)


def format_financials_section_original(profile: StartupProfile, current_date: str) -> str:
    """Original comprehensive financial section formatting."""
    # Collecting all financial metrics
    metrics = [
        ("Revenue", getattr(profile, 'revenue', None)),
        ("Projected Revenue", getattr(profile, 'projected_revenue', None)),
        ("Cash Burn (12m)", getattr(profile, 'cash_burn_12m', None)),
        ("Runway (months)", getattr(profile, 'runway_months', None)),
        ("Implied Valuation", getattr(profile, 'implied_valuation', None)),
        ("Total Funding Raised", getattr(profile, 'total_funding_raised', None)),
        ("Funding Rounds Count", getattr(profile, 'funding_rounds_count', None)),
        ("Latest Round Type", getattr(profile, 'latest_round_type', None)),
        ("Latest Round Date", getattr(profile, 'latest_round_date', None)),
        ("Latest Round Amount", getattr(profile, 'latest_round_amount', None)),
        ("Gross Margin", getattr(profile, 'gross_margin', None)),
        ("EBITDA", getattr(profile, 'ebitda', None)),
        ("Net Income", getattr(profile, 'net_income', None)),
        ("ARR", getattr(profile, 'arr', None)),
        ("MRR", getattr(profile, 'mrr', None)),
        ("CAC", getattr(profile, 'cac', None)),
        ("LTV", getattr(profile, 'ltv', None)),
        ("Payback Period", getattr(profile, 'payback_period', None)),
        ("Revenue Growth Rate", getattr(profile, 'revenue_growth_rate', None)),
        ("Debt", getattr(profile, 'debt', None)),
        ("Cash on Hand", getattr(profile, 'cash_on_hand', None)),
        ("Estimated Revenue", getattr(profile, 'estimated_revenue_range', None)),
        ("Revenue Currency", getattr(profile, 'revenue_currency', None)),
        ("Revenue Source", getattr(profile, 'revenue_source', None)),
        ("Last Funding Round", getattr(profile, 'last_funding_round_name', None)),
        ("Last Round Amount", getattr(profile, 'last_funding_round_amount_raised', None)),
        ("Last Round Date", getattr(profile, 'last_funding_round_announced_date', None)),
    ]
    
    # Get web-sourced financial data from financial analysis chain
    web_financial_data = getattr(profile, 'web_financial_data', None)
    valuation_source = getattr(profile, 'valuation_source', None)
    funding_source = getattr(profile, 'funding_source', None)
    
    # Get specific financial metrics from web search
    implied_valuation = getattr(profile, 'implied_valuation', None)
    total_funding_raised = getattr(profile, 'total_funding_raised', None)
    funding_rounds_count = getattr(profile, 'funding_rounds_count', None)
    latest_round_type = getattr(profile, 'latest_round_type', None)
    latest_round_date = getattr(profile, 'latest_round_date', None)
    latest_round_amount = getattr(profile, 'latest_round_amount', None)
    
    # Check for web sources from financial analysis
    web_sources = []
    if hasattr(profile, 'web_sources') and profile.web_sources:
        web_sources = profile.web_sources[:2]  # Limit to 2 sources (reduced from 5)
    elif hasattr(profile, 'financial_summary') and profile.financial_summary:
        urls = re.findall(r'https?://[^\s]+', profile.financial_summary)
        web_sources = urls[:2]  # Limit to 2 sources (reduced from 3)
    
    # Cap Table/Investors
    major_investors = getattr(profile, 'major_investors', None)
    ownership_breakdown = getattr(profile, 'ownership_breakdown', None)
    
    # Only counting as 'present' if not None and not empty string
    present_metrics = [v for _, v in metrics if v not in [None, '']]
    
    # Check if we have web-sourced financial data
    has_web_data = (web_financial_data and len(web_financial_data.strip()) > 100) or implied_valuation or total_funding_raised
    
    if len(present_metrics) < 3 and not (major_investors or ownership_breakdown) and not has_web_data:
        return f"Company has not released financials as of {current_date}. No detailed financials were disclosed in the deck or public sources. We recommend requesting a financial summary from the company, including revenue, burn rate, runway, and recent funding rounds. Independent verification of financials is advised before proceeding."
    
    # Build the financial analysis section
    lines = []
    
    # Check if we have any financial data from the deck first
    deck_financial_data = []
    if hasattr(profile, 'revenue') and profile.revenue:
        # Filter out obviously wrong revenue values
        if isinstance(profile.revenue, (int, float)) and profile.revenue > 1000:
            deck_financial_data.append(f"Revenue: ${profile.revenue:,.0f}")
    if hasattr(profile, 'funding_amount') and profile.funding_amount:
        # Filter out obviously wrong funding values
        if isinstance(profile.funding_amount, (int, float)) and profile.funding_amount > 1000:
            deck_financial_data.append(f"Funding: ${profile.funding_amount:,.0f}")
    if hasattr(profile, 'cash_burn_12m') and profile.cash_burn_12m:
        # Filter out obviously wrong burn values
        if isinstance(profile.cash_burn_12m, (int, float)) and profile.cash_burn_12m > 1000:
            deck_financial_data.append(f"Cash Burn (12m): ${profile.cash_burn_12m:,.0f}")
    if hasattr(profile, 'runway_months') and profile.runway_months:
        # Filter out obviously wrong runway values
        if isinstance(profile.runway_months, (int, float)) and 0 < profile.runway_months < 1000:
            deck_financial_data.append(f"Runway: {profile.runway_months} months")
    
    # If no deck financial data, show message
    if not deck_financial_data and not has_web_data:
        lines.append("**📊 Financial Data**")
        lines.append("")
        lines.append("No detailed financials were disclosed in the deck or public sources. We recommend requesting a financial summary from the company, including revenue, burn rate, runway, and recent funding rounds.")
        lines.append("")
    
    # If we have deck data, show it first
    elif deck_financial_data:
        lines.append("**📊 Financial Data from Deck**")
        lines.append("")
        for item in deck_financial_data:
            lines.append(f"• {item}")
        lines.append("")
    
    # Add web-sourced financial data as additional information
    web_data_added = False
    if has_web_data:
        lines.append("**📊 Additional Web-Sourced Financial Data**")
        lines.append("")
        
        # Display specific financial metrics with sources
        if implied_valuation:
            # Filter out obviously wrong valuation values
            if isinstance(implied_valuation, (int, float)) and implied_valuation > 1_000_000:
                valuation_str = f"${implied_valuation:,.0f}" if implied_valuation >= 1_000_000 else f"${implied_valuation:,.0f}"
                source_str = f" [Source: {valuation_source}]({valuation_source})" if valuation_source and valuation_source.startswith('http') else f" [Source: {valuation_source}]" if valuation_source else ""
                lines.append(f"• **Current Valuation**: {valuation_str}{source_str}")
                web_data_added = True
        
        if total_funding_raised:
            # Filter out obviously wrong funding values
            if isinstance(total_funding_raised, (int, float)) and total_funding_raised > 100_000:
                funding_str = f"${total_funding_raised:,.0f}"
                source_str = f" [Source: {funding_source}]({funding_source})" if funding_source and funding_source.startswith('http') else f" [Source: {funding_source}]" if funding_source else ""
                lines.append(f"• **Total Funding Raised**: {funding_str}{source_str}")
                web_data_added = True
        
        if funding_rounds_count:
            # Filter out obviously wrong round count values
            if isinstance(funding_rounds_count, (int, float)) and 0 < funding_rounds_count < 100:
                lines.append(f"• **Funding Rounds Count**: {funding_rounds_count}")
                web_data_added = True
        
        if latest_round_type and latest_round_date:
            lines.append(f"• **Latest Round**: {latest_round_type} ({latest_round_date})")
            if latest_round_amount:
                # Filter out obviously wrong round amount values
                if isinstance(latest_round_amount, (int, float)) and latest_round_amount > 10_000:
                    lines.append(f"• **Latest Round Amount**: ${latest_round_amount:,.0f}")
                    web_data_added = True
        
        # If no valid web data was added, show a message
        if not web_data_added:
            lines.append("• No reliable financial data found from web sources")
        
        lines.append("")
    
    # Add web research summary if available (clean up debugging artifacts)
    if web_financial_data and len(web_financial_data.strip()) > 100:
        # Use the comprehensive cleaning function
        cleaned_data = clean_think_tags_and_debugging(web_financial_data)
        
        if cleaned_data and len(cleaned_data) > 50:
            lines.append("**📋 Web Research Summary**")
            lines.append("")
            
            # Extract a concise summary from the cleaned web data
            summary_lines = cleaned_data.split('\n')[:5]  # First 5 lines for better context
            summary_text = ' '.join([line.strip() for line in summary_lines if line.strip()])
            if len(summary_text) > 400:
                summary_text = summary_text[:400] + "..."
            lines.append(summary_text)
            lines.append("")
    
    # Add data sources with clickable links
    if web_sources:
        lines.append("**🔗 Data Sources**")
        lines.append("")
        for i, source in enumerate(web_sources, 1):
            try:
                from urllib.parse import urlparse
                domain = urlparse(source).netloc
                if domain.startswith('www.'):
                    domain = domain[4:]
                # Create a more readable source name
                if 'crunchbase' in domain.lower():
                    source_name = "Crunchbase"
                elif 'cbinsights' in domain.lower():
                    source_name = "CB Insights"
                elif 'upmarket' in domain.lower():
                    source_name = "UpMarket"
                elif 'dizraptor' in domain.lower():
                    source_name = "Dizraptor"
                elif 'growjo' in domain.lower():
                    source_name = "Growjo"
                else:
                    source_name = domain.replace('.com', '').replace('.co', '').title()
                lines.append(f"• [{source_name}]({source})")
            except:
                lines.append(f"• [Source {i}]({source})")
        lines.append("")
    
    # Add traditional metrics table if available (filter out incorrect values)
    present_metrics_filtered = []
    for label, value in metrics:
        if value not in [None, '']:
            # Filter out obviously incorrect values
            if label == "Revenue" and value == 1.0:
                continue  # Skip incorrect revenue value
            if label == "Projected Revenue" and value == 1.0:
                continue  # Skip incorrect projected revenue value
            if isinstance(value, (int, float)) and value < 0:
                continue  # Skip negative values
            
            # Filter out values that are clearly wrong (like year numbers)
            if isinstance(value, (int, float)):
                # Skip if value looks like a year (between 1900-2030)
                if 1900 <= value <= 2030:
                    continue
                # Skip if value is too small for the metric type
                if label in ["Revenue", "Cash Burn (12m)", "Implied Valuation"] and value < 1000:
                    continue
                # Skip if value is unreasonably large for the metric type
                if label in ["Runway (months)", "Funding Rounds Count"] and value > 1000:
                    continue
            
            present_metrics_filtered.append((label, value))
    
    # Check if we have any valid financial data at all
    has_valid_data = (len(deck_financial_data) > 0 or 
                     web_data_added or 
                     len(present_metrics_filtered) > 0 or
                     (major_investors or ownership_breakdown))
    
    # If no valid financial data found, return early with a message
    if not has_valid_data:
        return f"**📊 Financial Data**\n\nNo reliable financial data was found in the deck or public sources. We recommend requesting a financial summary from the company, including revenue, burn rate, runway, and recent funding rounds. Independent verification of financials is advised before proceeding."
    
    if present_metrics_filtered:
        lines.append("**📈 Additional Financial Metrics**")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for label, value in present_metrics_filtered:
            lines.append(f"| {label} | {value} |")
        lines.append("")
    else:
        # Don't add empty table if no metrics
        pass
    
    # Add Cap Table/Investors if available
    if major_investors or ownership_breakdown:
        lines.append("**🏢 Ownership & Investors**")
        lines.append("")
        if major_investors:
            lines.append(f"**Major Investors**: {', '.join(major_investors)}")
        if ownership_breakdown:
            for owner in ownership_breakdown:
                name = owner.get('name', 'Unknown')
                percent = owner.get('percent', '')
                lines.append(f"• **{name}**: {percent}")
        lines.append("")
    
    return '\n'.join(lines)


def format_financial_history_section(profile: StartupProfile) -> str:
    """Format financial history section with funding rounds and investors."""
    lines = []
    rounds = getattr(profile, 'company_funding_rounds_collection', None) or getattr(profile, 'funding_rounds', None)
    
    if rounds and isinstance(rounds, list):
        lines.append("**Funding Rounds (source - coresignal):**")
        lines.append("")
        
        # Cleaning and deduplicating rounds
        cleaned_rounds = []
        seen_rounds = set()
        
        for r in rounds:
            if isinstance(r, dict):
                round_type = r.get('last_round_type') or r.get('round_type', 'Unknown')
                date = r.get('last_round_date') or r.get('date', '')
                amount = r.get('last_round_money_raised') or r.get('amount_usd', '')
                investors = r.get('last_round_investors_count') or r.get('investors', '')
                
                # Cleaning up the data
                round_type = str(round_type).strip()
                date = str(date).strip()
                amount = str(amount).strip()
                investors = str(investors).strip()
                
                # Filtering out unwanted round types
                unwanted_types = ['Series unknown', 'Non equity assistance', 'Unknown']
                if round_type in unwanted_types:
                    continue
                
                # Filtering out corporate rounds without amounts and secondary market rounds
                if round_type == 'Corporate round' and (not amount or amount == 'None' or amount == ''):
                    continue
                if 'secondary' in round_type.lower():
                    continue
                
                # Formatting date properly - extracting only the date part
                if date and date != 'None':
                    try:
                        # Handling different date formats
                        if ' ' in date:
                            # Remove time component and extract date
                            date_part = date.split(' ')[0]
                            if len(date_part) == 8 and date_part.isdigit():
                                # Format like "20180522" to "22 May 2018"
                                date_obj = datetime.strptime(date_part, '%Y%m%d')
                                formatted_date = date_obj.strftime('%d %B %Y')
                            elif len(date_part) == 10 and '-' in date_part:
                                # Format like "2018-05-22" to "22 May 2018"
                                date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                                formatted_date = date_obj.strftime('%d %B %Y')
                            else:
                                formatted_date = date_part
                        else:
                            # Handling single date strings
                            if len(date) == 8 and date.isdigit():
                                # Formatting like "20180522" to "22 May 2018"
                                date_obj = datetime.strptime(date, '%Y%m%d')
                                formatted_date = date_obj.strftime('%d %B %Y')
                            elif len(date) == 10 and '-' in date:
                                # Formatting like "2018-05-22" to "22 May 2018"
                                date_obj = datetime.strptime(date, '%Y-%m-%d')
                                formatted_date = date_obj.strftime('%d %B %Y')
                            else:
                                formatted_date = date
                    except:
                        formatted_date = date
                else:
                    formatted_date = 'Date not specified'
                
                # Formatting amount properly
                if amount and amount != 'None':
                    try:
                        # Converting to float and formatting as currency
                        amount_float = float(amount)
                        if amount_float >= 1_000_000:
                            formatted_amount = f"${amount_float/1_000_000:.1f}M"
                        elif amount_float >= 1_000:
                            formatted_amount = f"${amount_float/1_000:.1f}K"
                        else:
                            formatted_amount = f"${amount_float:.0f}"
                    except:
                        formatted_amount = amount
                else:
                    # For secondary rounds, specifying "Unknown amount" instead of "Amount not disclosed"
                    if 'secondary' in round_type.lower():
                        formatted_amount = 'Unknown amount'
                    else:
                        formatted_amount = 'Amount not disclosed'
                
                # Creating unique identifier for deduplication (by type and date, not amount)
                round_key = f"{round_type}_{formatted_date}"
                
                # Checking if we already have this round type and date
                existing_round = None
                for existing in cleaned_rounds:
                    if existing['type'] == round_type and existing['date'] == formatted_date:
                        existing_round = existing
                        break
                
                if existing_round:
                    # If we have a duplicate, keeping the one with the larger amount
                    try:
                        current_amount = float(existing_round['amount'].replace('$', '').replace('M', '').replace('K', '').replace(',', ''))
                        new_amount = float(formatted_amount.replace('$', '').replace('M', '').replace('K', '').replace(',', ''))
                        if new_amount > current_amount:
                            # Replacing with the larger amount
                            existing_round['amount'] = formatted_amount
                            existing_round['investors'] = investors
                    except:
                        # If we can't compare amounts, keeping the existing one
                        pass
                else:
                    # New round type and date combination
                    cleaned_rounds.append({
                        'type': round_type,
                        'date': formatted_date,
                        'amount': formatted_amount,
                        'investors': investors
                    })
        
        # Sorting rounds by date (most recent first)
        # Converting dates back to datetime for proper sorting
        def parse_date_for_sorting(date_str):
            try:
                if date_str == 'Date not specified':
                    return datetime.min
                # Trying different date formats for sorting
                for fmt in ['%d %B %Y', '%B %Y', '%Y-%m-%d', '%Y%m%d']:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except:
                        continue
                return datetime.min
            except:
                return datetime.min
        
        cleaned_rounds.sort(key=lambda x: parse_date_for_sorting(x['date']), reverse=True)
        
        # Displaying cleaned rounds
        for r in cleaned_rounds[:10]:  # Limit to top 10 rounds
            parts = []
            parts.append(f"**{r['type']}**")
            parts.append(r['date'])
            if r['amount'] != 'Amount not disclosed':
                parts.append(r['amount'])
            if r['investors'] and r['investors'] != 'None':
                parts.append(f"({r['investors']} investors)")
            
            lines.append(f"• {', '.join(parts)}")
    
    # Adding major investors section
    investors = getattr(profile, 'company_featured_investors_collection', None)
    if investors and isinstance(investors, list):
        lines.append("")
        lines.append("**Major Investors:**")
        lines.append("")
        
        seen_investors = set()
        for inv in investors:
            name = inv.get('name') if isinstance(inv, dict) else str(inv)
            url = inv.get('cb_url') if isinstance(inv, dict) else None
            
            if name and name not in seen_investors:
                seen_investors.add(name)
                # Keeping the name as is (including any tokens)
                if name and name != 'None':
                    if url:
                        lines.append(f"• **{name}** ([Profile]({url}))")
                    else:
                        lines.append(f"• **{name}**")
    
    # Adding acquisitions if available
    acquisitions = getattr(profile, 'acquisitions', None)
    if acquisitions and isinstance(acquisitions, list):
        lines.append("")
        lines.append("**Acquisitions:**")
        lines.append("")
        
        for acq in acquisitions:
            if isinstance(acq, dict):
                name = acq.get('name', 'Unknown')
                date = acq.get('date', '')
                amount = acq.get('amount', '')
                
                if name and name != 'Unknown':
                    parts = [f"**{name}**"]
                    if date:
                        parts.append(date)
                    if amount:
                        parts.append(amount)
                    lines.append(f"• {', '.join(parts)}")
            else:
                acq_str = str(acq).strip()
                if acq_str and acq_str != 'None':
                    lines.append(f"• **{acq_str}**")
    
    return '\n'.join(lines)


# Import the centralized clean_think_tags_and_debugging function
from core.text_cleaners import clean_think_tags_and_debugging 