"""
Financial-analysis chain
• Extracts annual burn, runway, implied valuation.
"""

import json
from hashlib import sha1
from pathlib import Path
import re

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from core.schemas import StartupProfile
from core.vector_store import query_doc
from core.hybrid_context import get_hybrid_context
from core.text_cleaners import clean_think_tags_and_debugging

# ------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

def web_search_financial_context(company_name):
    """Search for company financial data and valuation information with source attribution."""
    try:
        from core.perplexity_utils import search_perplexity
        
        # Focused queries for key financial data - use actual company name
        search_queries = [
            f"{company_name} current valuation funding rounds Crunchbase Wikipedia",
            f"{company_name} total funding raised latest funding round Crunchbase Wikipedia"
        ]
        
        web_data = []
        sources = []
        
        for query in search_queries:
            try:
                result = search_perplexity(query)
                if result and len(result.strip()) > 50:
                    # Clean up the result by removing debugging and thinking process markers
                    cleaned_result = result.strip()
                    
                    # Remove <think> tags and their content
                    cleaned_result = re.sub(r'<think>.*?</think>', '', cleaned_result, flags=re.DOTALL)
                    
                    # Remove thinking process markers (more comprehensive)
                    thinking_patterns = [
                        r'(Okay, so I need to figure out|First, from the|Looking at the|Based on the|From the search results|Let me start by|I need to analyze|Let me examine).*?(?=\n|$)',
                        r'(Let me look through|I need to look through|Looking at result|Result mentions|First, result|Result from|Based on result).*?(?=\n|$)',
                        r'(The user wants|The user asked|The user is asking|The query is about).*?(?=\n|$)',
                        r'(I need to answer|I need to tackle|Let me tackle|Let me answer).*?(?=\n|$)',
                        r'(Okay, let\'s tackle|Let\'s tackle|Let me tackle).*?(?=\n|$)',
                        r'(The user wants me to|The user wants to know|The user is looking for).*?(?=\n|$)',
                        r'(I should look|I need to look|Let me look).*?(?=\n|$)',
                        r'(Based on the provided|Based on the search|From the search).*?(?=\n|$)',
                        r'(Financial Research Summary for|Company:).*?(?=\n|$)',
                    ]
                    
                    for pattern in thinking_patterns:
                        cleaned_result = re.sub(pattern, '', cleaned_result, flags=re.DOTALL)
                    
                    # Remove numbered analysis that's part of thinking process
                    cleaned_result = re.sub(r'^\d+\.\s*[A-Z].*?(?=\n|$)', '', cleaned_result, flags=re.MULTILINE)
                    
                    # Remove citation markers
                    cleaned_result = re.sub(r'\[\d+\]', '', cleaned_result)
                    
                    # Remove hashtags and markdown formatting that might be artifacts
                    cleaned_result = re.sub(r'#+\s*[A-Za-z\s]+', '', cleaned_result)
                    
                    # Remove standalone bullet points that don't have content
                    cleaned_result = re.sub(r'^\s*•\s*$', '', cleaned_result, flags=re.MULTILINE)
                    
                    # Remove bullet points at the beginning of lines that are followed by whitespace
                    cleaned_result = re.sub(r'^\s*•\s+(?=\s|$)', '', cleaned_result, flags=re.MULTILINE)
                    
                    # Clean up extra whitespace and newlines
                    cleaned_result = re.sub(r'\n\s*\n', '\n', cleaned_result)
                    cleaned_result = cleaned_result.strip()
                    
                    # Only add if we have meaningful content after cleaning
                    if len(cleaned_result) > 50:
                        web_data.append(cleaned_result)
                        # Extract URLs from the result with better pattern matching
                        urls = re.findall(r'https?://[^\s\)\]]+', cleaned_result)
                        # Clean URLs and remove trailing punctuation
                        cleaned_urls = []
                        for url in urls:
                            # Remove trailing punctuation and clean up
                            clean_url = url.rstrip('.,;!?')
                            if clean_url and len(clean_url) > 10:  # Basic URL validation
                                cleaned_urls.append(clean_url)
                        sources.extend(cleaned_urls[:1])  # Limit to first 1 URL per query
            except Exception as e:
                print(f"[Financial Analysis] Web search error for query '{query}': {e}")
                continue
        
        if web_data:
            combined_data = "\n\n".join(web_data)
            # Remove duplicate sources and prioritize Crunchbase
            unique_sources = list(set(sources))
            
            # Prioritize financial and reliable sources
            financial_sources = [s for s in unique_sources if any(keyword in s.lower() for keyword in ['crunchbase', 'yahoo', 'marketwatch', 'seekingalpha', 'reuters', 'bloomberg', 'cnbc', 'wsj'])]
            other_sources = [s for s in unique_sources if s not in financial_sources]
            
            # Put financial sources first, then others (limit to 5 total for better coverage)
            prioritized_sources = financial_sources + other_sources[:5-len(financial_sources)]
            
            # Format sources as clickable links
            source_links = []
            for url in prioritized_sources:
                # Extract domain name for display
                from urllib.parse import urlparse
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    source_links.append(f"• [{domain}]({url})")
                except:
                    source_links.append(f"• {url}")
            
            source_links_text = "\n".join(source_links)
            
            return f"""
Financial Research Summary for {company_name}:
{combined_data}

Sources:
{source_links_text}
"""
        else:
            return ""
            
    except Exception as e:
        print(f"[Financial Analysis] Web search error: {e}")
        return ""

# Simple cache for Crunchbase API calls to avoid repeated requests
_crunchbase_cache = {}

def parse_money_string(s):
    """Enhanced money string parser that handles various currency formats."""
    if s is None:
        return None
    
    s = str(s).replace(",", "").strip()
    
    # Remove currency codes (USD, EUR, etc.) first - look anywhere in the string
    s = re.sub(r'\s*(USD|EUR|GBP|CAD|AUD|JPY)\s*', '', s, flags=re.IGNORECASE)
    
    # Remove $ and other currency symbols first
    s = re.sub(r'[\$\€\£\¥]', '', s)
    
    # Clean up any extra whitespace that might have been left
    s = re.sub(r'\s+', ' ', s).strip()
    
    # Handle various formats like "1.5 billion", "1.5B", "1,500M", etc.
    
    # Handle billion/million/thousand suffixes with various formats
    if 'billion' in s.lower() or 'b' in s.lower():
        try:
            # Remove 'billion' or 'b' and clean up
            clean_s = re.sub(r'\s*(billion|b)\s*', '', s.lower())
            # Handle ranges like "70-80 million" by taking the average
            if '-' in clean_s:
                parts = clean_s.split('-')
                if len(parts) == 2:
                    try:
                        num1 = float(parts[0].strip())
                        num2 = float(parts[1].strip())
                        return ((num1 + num2) / 2) * 1e9
                    except (ValueError, TypeError):
                        pass
            # Try to extract just the number part - look for the first number
            num_match = re.search(r'([\d\.]+)', clean_s)
            if num_match:
                num = float(num_match.group(1))
                return num * 1e9
            # If no number found, try to parse the whole string
            num = float(clean_s.strip())
            return num * 1e9
        except (ValueError, TypeError):
            return None
    elif 'million' in s.lower() or 'm' in s.lower():
        try:
            # Remove 'million' or 'm' and clean up
            clean_s = re.sub(r'\s*(million|m)\s*', '', s.lower())
            # Handle ranges like "70-80 million" by taking the average
            if '-' in clean_s:
                parts = clean_s.split('-')
                if len(parts) == 2:
                    try:
                        num1 = float(parts[0].strip())
                        num2 = float(parts[1].strip())
                        return ((num1 + num2) / 2) * 1e6
                    except (ValueError, TypeError):
                        pass
            # Try to extract just the number part
            num_match = re.search(r'([\d\.]+)', clean_s)
            if num_match:
                num = float(num_match.group(1))
                return num * 1e6
            num = float(clean_s.strip())
            return num * 1e6
        except (ValueError, TypeError):
            return None
    elif 'thousand' in s.lower() or 'k' in s.lower():
        try:
            # Remove 'thousand' or 'k' and clean up
            clean_s = re.sub(r'\s*(thousand|k)\s*', '', s.lower())
            # Try to extract just the number part
            num_match = re.search(r'([\d\.]+)', clean_s)
            if num_match:
                num = float(num_match.group(1))
                return num * 1e3
            num = float(clean_s.strip())
            return num * 1e3
        except (ValueError, TypeError):
            return None
    
    # Original pattern matching for K, M, B suffixes
    match = re.match(r"([\d\.]+)\s*([KMB]?)", s, re.IGNORECASE)
    if not match:
        return None
    num, suffix = match.groups()
    try:
        num = float(num)
    except (ValueError, TypeError):
        return None
    multiplier = {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}
    return num * multiplier.get(suffix.upper(), 1)

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

def fetch_crunchbase_funding_data(crunchbase_url):
    """Fetch funding and valuation data from Crunchbase URL with caching"""
    global _crunchbase_cache
    
    # Check cache first
    if crunchbase_url in _crunchbase_cache:
        print(f"[Financial Analysis] Using cached data for: {crunchbase_url}")
        return _crunchbase_cache[crunchbase_url]
    
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(crunchbase_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract funding information
            funding_data = {}
            
            # Look for valuation information
            valuation_selectors = [
                'span[data-test="valuation"]',
                '.valuation',
                '[data-test="post-money-valuation"]',
                '.post-money-valuation'
            ]
            
            for selector in valuation_selectors:
                elements = soup.select(selector)
                if elements:
                    funding_data['valuation'] = elements[0].get_text().strip()
                    break
            
            # Look for funding amount
            amount_selectors = [
                'span[data-test="money-raised"]',
                '.money-raised',
                '[data-test="funding-amount"]',
                '.funding-amount'
            ]
            
            for selector in amount_selectors:
                elements = soup.select(selector)
                if elements:
                    funding_data['funding_amount'] = elements[0].get_text().strip()
                    break
            
            # Look for round type
            round_selectors = [
                'span[data-test="round-type"]',
                '.round-type',
                '[data-test="funding-round"]',
                '.funding-round'
            ]
            
            for selector in round_selectors:
                elements = soup.select(selector)
                if elements:
                    funding_data['round_type'] = elements[0].get_text().strip()
                    break
            
            # Look for date
            date_selectors = [
                'span[data-test="funding-date"]',
                '.funding-date',
                '[data-test="date"]',
                '.date'
            ]
            
            for selector in date_selectors:
                elements = soup.select(selector)
                if elements:
                    funding_data['funding_date'] = elements[0].get_text().strip()
                    break
            
            # Cache the result
            _crunchbase_cache[crunchbase_url] = funding_data
            return funding_data
            
    except Exception as e:
        print(f"[Crunchbase Fetch Error] {e}")
        # Cache empty result to avoid repeated failed requests
        _crunchbase_cache[crunchbase_url] = {}
        return {}
    
    # Cache empty result
    _crunchbase_cache[crunchbase_url] = {}
    return {}

SYSTEM = """
You are a VC financial analyst specializing in startup financial analysis.
Extract key financial metrics from the provided context and web search results.

IMPORTANT REQUIREMENTS:
1. Focus on the most critical financial metrics: valuation, funding amounts, and total funding raised
2. Use Crunchbase data as the primary source when available
3. Include source URLs for web-sourced data
4. Generate clean, concise output without thinking process or debugging text
5. Format URLs as clickable links in the final output

CRITICAL METRICS TO EXTRACT:
- Current valuation (from Crunchbase or web search)
- Latest funding round amount and date
- Total funding raised
- Revenue (if available from reliable sources)

OUTPUT FORMAT:
Return a JSON object with these fields:
{{
    "implied_valuation": "Current valuation in USD",
    "latest_round_amount": "Latest funding round amount in USD", 
    "latest_round_date": "Date of latest funding round",
    "total_funding_raised": "Total funding raised in USD",
    "revenue": "Annual revenue if available",
    "web_sources": ["List of source URLs for web data"]
}}

IMPORTANT:
- Only extract numbers that are explicitly stated in the text, Crunchbase data, or web search results
- Do NOT guess, estimate, or hallucinate values
- If a value is not explicitly stated, return null for that field
- Include source URLs for web-sourced data to enable verification
- Clean output should be ready for direct use in investment memos
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Financial snippets:\n{context}\nWeb search context:\n{web_context}\n")
])

# Import the centralized parse_money_string function
from core.utils import parse_money_string

def get_smart_financial_context(text):
    """Extract financial-relevant sections from text and create a focused 10k summary"""
    
    # High-priority financial keywords (these get more context)
    high_priority_keywords = [
        'revenue', 'MRR', 'GMV', 'TAM', 'valuation', 'funding', 'growth',
        'profit', 'margin', 'merchants', 'customers', 'sales', 'income',
        'financial', 'earnings', 'quarterly', 'annual', 'monthly'
    ]
    
    # Medium-priority keywords (business model related)
    medium_priority_keywords = [
        'business model', 'pricing', 'subscription', 'revenue stream',
        'market size', 'market opportunity', 'competitive', 'partnership'
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
        # Add the end of the text (where financial data often is)
        combined_context += '\n\n' + text[-8000:]  # Add last 8k chars
    
    # Limit to 10k chars total for efficiency
    return combined_context[:10000]

def ai_extract_financial_data(text):
    """AI-powered extraction of ANY financial data from text"""
    try:
        from config import Config
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        
        prompt = f"""
You are a financial analyst extracting ALL financial-related data from a company pitch deck.

Extract ANY financial information from this text and return it as a JSON object with the following structure:

{{
    "revenue_metrics": {{
        "revenue": "annual revenue amount",
        "mrr": "monthly recurring revenue",
        "arr": "annual recurring revenue",
        "gmv": "gross merchandise value",
        "revenue_growth_rate": "revenue growth percentage",
        "revenue_per_customer": "revenue per customer amount"
    }},
    "profitability_metrics": {{
        "gross_profit": "gross profit amount",
        "gross_margin": "gross margin percentage",
        "operating_margin": "operating margin percentage",
        "ebitda": "EBITDA amount",
        "net_income": "net income amount",
        "profit_margin": "profit margin percentage"
    }},
    "growth_metrics": {{
        "cagr": "compound annual growth rate",
        "growth_rate": "overall growth rate",
        "customer_growth": "customer growth rate",
        "revenue_growth": "revenue growth rate",
        "merchant_growth": "merchant growth rate"
    }},
    "business_model": {{
        "subscription_pricing": "subscription pricing tiers",
        "revenue_streams": "different revenue streams",
        "pricing_model": "pricing model description",
        "customer_segments": "target customer segments"
    }},
    "operational_metrics": {{
        "cash_burn": "cash burn rate",
        "runway_months": "runway in months",
        "cash_on_hand": "cash on hand amount",
        "working_capital": "working capital amount",
        "debt": "debt amount",
        "equity": "equity amount"
    }},
    "efficiency_metrics": {{
        "cac": "customer acquisition cost",
        "ltv": "lifetime value",
        "payback_period": "payback period in months",
        "churn_rate": "customer churn rate",
        "retention_rate": "customer retention rate"
    }},
    "valuation_metrics": {{
        "valuation": "company valuation",
        "market_cap": "market capitalization",
        "enterprise_value": "enterprise value",
        "pe_ratio": "P/E ratio",
        "ev_ebitda": "EV/EBITDA ratio"
    }},
    "historical_data": {{
        "revenue_by_year": "revenue data by year",
        "growth_by_year": "growth data by year",
        "profit_by_year": "profit data by year"
    }},
    "operating_expenses": {{
        "sales_marketing": "sales and marketing expense percentage",
        "research_development": "R&D expense percentage",
        "general_administrative": "G&A expense percentage"
    }}
}}

IMPORTANT:
- Extract ANY financial-related data, not just predefined fields
- If a field is not found, use null
- For numbers, include units (e.g., "$46B", "85%", "12 months")
- For text fields, extract the exact wording from the text
- Be comprehensive - extract everything that could be financial-related
- Include historical data if available (year-over-year comparisons)
- Extract business model details (pricing, revenue streams)
- Capture efficiency metrics and ratios

Text to analyze:
{get_smart_financial_context(text)}  # Smart context selection for financial data
"""
        
        response = llm.invoke(prompt).content.strip()
        
        # Parse the JSON response
        import json
        
        # Clean up the response to extract JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            financial_data = json.loads(json_match.group())
            print(f"[AI Financial Extraction] Extracted {len(financial_data)} financial data categories")
            return financial_data
        else:
            print(f"[AI Financial Extraction] Could not parse JSON from response")
            return {}
            
    except Exception as e:
        print(f"[AI Financial Extraction] Error: {e}")
        return {}


def extract_financials_from_text(text):
    """Extract financial data using comprehensive regex patterns with validation"""
    results = {}
    
    # Additional validation: exclude technical specifications that might be confused with financial data
    technical_indicators = ['mhz', 'ghz', 'gb', 'mb', 'tb', 'pixels', 'resolution', 'fps', 'latency']
    
    try:
        # Enhanced regex patterns for financial extraction
        patterns = {
            "revenue": [
                # Look for revenue numbers in the format $XXX.XM (like $195.0M, $135.1M)
                r'(\$[\d,\.]+M)\s*(?:revenue|sales|income|growth)',
                r'revenue[^\d$]*(\$[\d,\.]+M)',
                r'(\$[\d,\.]+M)\s*revenue',
                # Look for standalone revenue numbers in charts/tables
                r'(\$[\d,\.]+M)(?=\s*\n|\s*$|\s*\+|\s*%)',
                # Handle cases where $ is stripped
                r'([\d,\.]+M)\s*(?:revenue|sales|income)',
                r'revenue[^\d]*([\d,\.]+M)',
                r'([\d,\.]+M)\s*revenue'
            ],
            "mrr": [
                r'(\$[\d,\.]+M)\s*MRR',
                r'MRR[^\d$]*(\$[\d,\.]+M)',
                r'(\$[\d,\.]+M)\s*monthly\s*recurring',
                # Look for MRR in growth charts
                r'(\$[\d,\.]+M)(?=\s*Q\d|\s*\d{4})',
                # Handle cases where $ is stripped
                r'([\d,\.]+M)\s*MRR',
                r'MRR[^\d]*([\d,\.]+M)',
                r'([\d,\.]+M)\s*monthly\s*recurring'
            ],
            "gmv": [
                r'(\$[\d,\.]+[BM])\s*GMV',
                r'GMV[^\d$]*(\$[\d,\.]+[BM])',
                r'(\$[\d,\.]+[BM])\s*gross\s*merchandise',
                # Look for GMV numbers in growth charts
                r'(\$[\d,\.]+[BM])(?=\s*\n|\s*$|\s*\+|\s*%)',
                # Handle cases where $ is stripped
                r'([\d,\.]+[BM])\s*GMV',
                r'GMV[^\d]*([\d,\.]+[BM])',
                r'([\d,\.]+[BM])\s*gross\s*merchandise'
            ],
            "gross_profit": [
                r'(\$[\d,\.]+[KMB]?)\s*(?:gross\s+)?profit',
                r'gross\s+profit[^\d$]*(\$[\d,\.]+[KMB]?)',
                r'(\$[\d,\.]+[KMB]?)\s*profit',
                r'([\d,\.]+[KMB]?)\s*(?:gross\s+)?profit',  # Handle cases where $ is stripped
                r'gross\s+profit[^\d]*([\d,\.]+[KMB]?)',  # Handle cases where $ is stripped
                r'([\d,\.]+[KMB]?)\s*profit'  # Handle cases where $ is stripped
            ],
            "cagr": [
                r'(\d+\.?\d*)\s*%\s*CAGR',
                r'CAGR[^\d]*(\d+\.?\d*)%',
                r'(\d+\.?\d*)\s*CAGR'
            ],
            "growth_rate": [
                r'\+(\d+\.?\d*)\s*%',
                r'(\d+\.?\d*)%\s*growth',
                r'growth[^\d]*(\d+\.?\d*)%'
            ],
            "cash_burn_12m": [
                r'(\$[\d,\.]+[KMB]?)\s*(?:burn|burn\s+rate)',
                r'cash\s+burn[^\d$]*(\$[\d,\.]+[KMB]?)',
                r'burn\s+rate[^\d$]*(\$[\d,\.]+[KMB]?)'
            ],
            "runway_months": [
                r'(\d+\.?\d*)\s*(?:months|mo)\s*(?:runway)',
                r'runway[^\d]*(\d+\.?\d*)\s*(?:months|mo)',
                r'(\d+\.?\d*)\s*months?\s*runway'
            ],
            "implied_valuation": [
                r'(\$[\d,\.]+[KMB]?)\s*(?:valuation|market\s+cap)',
                r'valuation[^\d$]*(\$[\d,\.]+[KMB]?)',
                r'(\$[\d,\.]+[KMB]?)\s*market\s+cap'
            ],
            "merchants": [
                r'(\d+[,.]?\d*)\+?\s*(?:merchants|customers|users)',
                r'(\d+[,.]?\d*)\s*active\s*(?:merchants|customers)',
                r'(\d+[,.]?\d*)\s*merchants',
                # Look for merchant count in format like "200,000+ ACTIVE SHOPIFY MERCHANTS"
                r'(\d+[,.]?\d*)\+\s*ACTIVE\s*(?:SHOPIFY\s+)?MERCHANTS',
                r'(\d+[,.]?\d*)\s*MERCHANTS'
            ],
            "revenue_per_merchant": [
                r'(\$[\d,\.]+[KMB]?)\s*(?:per\s+)?(?:merchant|customer)',
                r'revenue\s+per\s+merchant[^\d$]*(\$[\d,\.]+[KMB]?)',
                r'(\$[\d,\.]+[KMB]?)\s*per\s+merchant'
            ],
            "subscription_pricing": [
                r'(\$[\d,\.]+[KMB]?)\s*(?:subscription|monthly|annual)',
                r'(\$[\d,\.]+[KMB]?)\s*(?:basic|professional|enterprise)',
                r'(\$[\d,\.]+[KMB]?)\s*per\s*month'
            ],
            "operating_expenses": [
                r'(\d+\.?\d*)%\s*(?:S&M|sales\s+and\s+marketing)',
                r'(\d+\.?\d*)%\s*(?:R&D|research\s+and\s+development)',
                r'(\d+\.?\d*)%\s*(?:G&A|general\s+and\s+administrative)'
            ],
            "margins": [
                r'(\d+\.?\d*)%\s*(?:gross\s+)?margin',
                r'(\d+\.?\d*)%\s*operating\s+margin',
                r'(\d+\.?\d*)%\s*profit\s+margin'
            ],
            "tam": [
                r'(\$[\d,\.]+[BM])\s*(?:Global\s+)?TAM',
                r'TAM[^\d$]*(\$[\d,\.]+[BM])',
                r'(\$[\d,\.]+[BM])\s*Total\s*Addressable\s*Market',
                # Look for TAM in format like "$46B Global TAM"
                r'(\$[\d,\.]+[BM])\s*Global\s*TAM',
                r'(\$[\d,\.]+[BM])\s*TAM\s*\([^)]*\)'
            ]
        }
        
        for financial_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Get the full matched text for context validation
                    full_match = match.group(0)
                    
                    # Skip if the match contains technical indicators (not financial)
                    if any(indicator in full_match.lower() for indicator in technical_indicators):
                        continue
                    
                    val = match.group(1)
                    
                    # Parse the value appropriately
                    if financial_type in ['cagr', 'growth_rate', 'runway_months', 'operating_expenses', 'margins']:
                        try:
                            parsed_value = float(val.replace(',', ''))
                            
                            # Additional validation for specific metrics
                            if financial_type == "runway_months":
                                # Skip if value looks like a year (1900-2030)
                                if 1900 <= parsed_value <= 2030:
                                    continue
                                # Skip if value is unreasonably large for runway
                                if parsed_value > 100:
                                    continue
                            
                            results[financial_type] = parsed_value
                            print(f"[Financial Extraction] Found {financial_type}={parsed_value}")
                            break
                        except:
                            # If parsing fails, store as string
                            results[financial_type] = val.strip()
                            print(f"[Financial Extraction] Found {financial_type}={val.strip()} (as string)")
                            break
                    else:
                        # For dollar amounts, try to parse with parse_money_string first
                        parsed_value = parse_money_string(val)
                        
                        if parsed_value is not None:
                            # Skip if value looks like a year (1900-2030)
                            if 1900 <= parsed_value <= 2030:
                                continue
                            
                            # Skip if value is too small for the metric type
                            if financial_type in ["revenue", "cash_burn_12m", "implied_valuation"] and parsed_value < 1000:
                                continue
                            
                            # Skip if value is unreasonably large for certain metrics
                            if financial_type in ["runway_months"] and parsed_value > 1000:
                                continue
                            
                            results[financial_type] = parsed_value
                            print(f"[Financial Extraction] Found {financial_type}={parsed_value}")
                            break
                        else:
                            # If parsing fails, store as string
                            results[financial_type] = val.strip()
                            print(f"[Financial Extraction] Found {financial_type}={val.strip()} (as string)")
                            break
                        
    except Exception as e:
        print(f"[Financial Extraction] Error extracting financial data: {e}")
    
    return results

def value_in_text(value, text):
    """Check if the numeric value (as string) appears in the text (case-insensitive, ignoring commas)."""
    if value is None:
        return False
    if isinstance(value, float) or isinstance(value, int):
        value_str = f"{value:,.0f}".replace(",", "")
        return value_str in text.replace(",", "")
    return str(value) in text

def run_financial_analysis_chain(profile: StartupProfile, financial_context: str = "") -> StartupProfile:
    # If financial_context is provided, use it; otherwise, build from profile fields
    if financial_context and financial_context.strip():
        context = financial_context
    else:
        # Build context from all available financial fields
        financial_fields = []
        
        # Core financial metrics
        if getattr(profile, 'revenue', None):
            financial_fields.append(f"Revenue: {profile.revenue}")
        if getattr(profile, 'funding_amount', None):
            financial_fields.append(f"Funding Amount: {profile.funding_amount}")
        if getattr(profile, 'funding_stage', None):
            financial_fields.append(f"Funding Stage: {profile.funding_stage}")
        if getattr(profile, 'implied_valuation', None):
            financial_fields.append(f"Implied Valuation: {profile.implied_valuation}")
        if getattr(profile, 'total_funding_raised', None):
            financial_fields.append(f"Total Funding Raised: {profile.total_funding_raised}")
        if getattr(profile, 'funding_rounds_count', None):
            financial_fields.append(f"Funding Rounds Count: {profile.funding_rounds_count}")
        if getattr(profile, 'latest_round_type', None):
            financial_fields.append(f"Latest Round Type: {profile.latest_round_type}")
        if getattr(profile, 'latest_round_amount', None):
            financial_fields.append(f"Latest Round Amount: {profile.latest_round_amount}")
        if getattr(profile, 'latest_round_date', None):
            financial_fields.append(f"Latest Round Date: {profile.latest_round_date}")
        
        # Additional financial metrics
        if getattr(profile, 'cash_burn_12m', None):
            financial_fields.append(f"Cash Burn (12m): {profile.cash_burn_12m}")
        if getattr(profile, 'runway_months', None):
            financial_fields.append(f"Runway (months): {profile.runway_months}")
        if getattr(profile, 'gross_margin', None):
            financial_fields.append(f"Gross Margin: {profile.gross_margin}")
        if getattr(profile, 'ebitda', None):
            financial_fields.append(f"EBITDA: {profile.ebitda}")
        if getattr(profile, 'net_income', None):
            financial_fields.append(f"Net Income: {profile.net_income}")
        if getattr(profile, 'arr', None):
            financial_fields.append(f"ARR: {profile.arr}")
        if getattr(profile, 'mrr', None):
            financial_fields.append(f"MRR: {profile.mrr}")
        if getattr(profile, 'cac', None):
            financial_fields.append(f"CAC: {profile.cac}")
        if getattr(profile, 'ltv', None):
            financial_fields.append(f"LTV: {profile.ltv}")
        if getattr(profile, 'payback_period', None):
            financial_fields.append(f"Payback Period: {profile.payback_period}")
        if getattr(profile, 'revenue_growth_rate', None):
            financial_fields.append(f"Revenue Growth Rate: {profile.revenue_growth_rate}")
        if getattr(profile, 'debt', None):
            financial_fields.append(f"Debt: {profile.debt}")
        if getattr(profile, 'cash_on_hand', None):
            financial_fields.append(f"Cash on Hand: {profile.cash_on_hand}")
        
        # AI-extracted financial metrics
        if getattr(profile, 'gmv', None):
            financial_fields.append(f"GMV: {profile.gmv}")
        if getattr(profile, 'TAM', None):
            financial_fields.append(f"TAM: {profile.TAM}")
        if getattr(profile, 'business_model', None):
            financial_fields.append(f"Business Model: {profile.business_model}")
        if getattr(profile, 'merchants_count', None):
            financial_fields.append(f"Merchants: {profile.merchants_count}")
        if getattr(profile, 'growth_rate', None):
            financial_fields.append(f"Growth Rate: {profile.growth_rate}")
        if getattr(profile, 'valuation', None):
            financial_fields.append(f"Valuation: {profile.valuation}")
        if getattr(profile, 'gross_profit', None):
            financial_fields.append(f"Gross Profit: {profile.gross_profit}")
        
        # Company info
        if getattr(profile, 'sector', None):
            financial_fields.append(f"Sector: {profile.sector}")
        if getattr(profile, 'name', None):
            financial_fields.append(f"Company: {profile.name}")
        
        context = "\n".join(financial_fields) if financial_fields else "No financial data available"
    
    # Check if we have CoreSignal funding data with Crunchbase URLs
    crunchbase_data = ""
    if hasattr(profile, 'funding_rounds') and profile.funding_rounds:
        try:
            import json
            funding_rounds = json.loads(profile.funding_rounds) if isinstance(profile.funding_rounds, str) else profile.funding_rounds
            
            print(f"[Financial Analysis] Found {len(funding_rounds)} funding rounds to process")
            
            # Find the most recent significant funding round with a Crunchbase URL
            # Only process the first 3 rounds with valid URLs to avoid excessive API calls
            processed_count = 0
            max_rounds_to_process = 3
            
            for round_data in funding_rounds:
                if processed_count >= max_rounds_to_process:
                    print(f"[Financial Analysis] Reached limit of {max_rounds_to_process} rounds, stopping...")
                    break
                if isinstance(round_data, dict) and round_data.get('cb_url'):
                    cb_url = round_data['cb_url']
                    print(f"[Financial Analysis] Fetching data from Crunchbase: {cb_url}")
                    
                    # Fetch data from Crunchbase
                    funding_data = fetch_crunchbase_funding_data(cb_url)
                    processed_count += 1
                    if funding_data:
                        crunchbase_data = f"""
Crunchbase Funding Data:
- Round Type: {funding_data.get('round_type', 'Unknown')}
- Funding Amount: {funding_data.get('funding_amount', 'Unknown')}
- Valuation: {funding_data.get('valuation', 'Unknown')}
- Date: {funding_data.get('funding_date', 'Unknown')}
- Source: {cb_url}
"""
                        print(f"[Financial Analysis] Found Crunchbase data: {funding_data}")
                        break  # Only process the first successful round
                    else:
                        print(f"[Financial Analysis] No data found for {cb_url}, trying next round...")
                        continue
        except Exception as e:
            print(f"[Financial Analysis] Error processing funding rounds: {e}")
    
    # Add web search data for company valuation and financial information
    web_search_data = ""
    web_sources = []
    company_name = getattr(profile, 'name', '')
    
    # Skip web search if web sources already exist (to prevent overwriting)
    existing_web_sources = getattr(profile, 'web_sources', [])
    if existing_web_sources:
        print(f"[Financial Analysis] Web sources already exist ({len(existing_web_sources)} sources), skipping web search")
        web_sources = existing_web_sources
    elif company_name and company_name.strip():
        print(f"[Financial Analysis] Searching web for financial data on {company_name}")
        web_search_data = web_search_financial_context(company_name)
        if web_search_data:
            print(f"[Financial Analysis] Found web search data for {company_name}")
            # Extract URLs from web search data
            urls = re.findall(r'https?://[^\s]+', web_search_data)
            web_sources = list(set(urls))  # Remove duplicates
            # Store web sources and data in profile
            profile.web_sources = web_sources
            # Clean the web financial data before storing
            cleaned_web_data = web_search_data
            if cleaned_web_data:
                # Remove <think> tags and their content
                cleaned_web_data = re.sub(r'<think>.*?</think>', '', cleaned_web_data, flags=re.DOTALL)
                
                # Remove thinking process markers (comprehensive)
                thinking_patterns = [
                    r'(Okay, so I need to figure out|First, from the|Looking at the|Based on the|From the search results|Let me start by|I need to analyze|Let me examine).*?(?=\n|$)',
                    r'(Let me look through|I need to look through|Looking at result|Result mentions|First, result|Result from|Based on result).*?(?=\n|$)',
                    r'(The user wants|The user asked|The user is asking|The query is about).*?(?=\n|$)',
                    r'(I need to answer|I need to tackle|Let me tackle|Let me answer).*?(?=\n|$)',
                    r'(Okay, let\'s tackle|Let\'s tackle|Let me tackle).*?(?=\n|$)',
                    r'(The user wants me to|The user wants to know|The user is looking for).*?(?=\n|$)',
                    r'(I should look|I need to look|Let me look).*?(?=\n|$)',
                    r'(Based on the provided|Based on the search|From the search).*?(?=\n|$)',
                    r'(Financial Research Summary for|Company:).*?(?=\n|$)',
                    r'(Okay, I need to find|I need to find|Let me find).*?(?=\n|$)',
                    r'(The search result|The search results|From the search).*?(?=\n|$)',
                    r'(Revenue is|Revenue was|The revenue).*?(?=\n|$)',
                    r'(The answer should state|The answer is|Based on the data).*?(?=\n|$)',
                    r'(So the answer should|So the answer is|So the data shows).*?(?=\n|$)',
                    r'(The search result dates|The data dates|The information dates).*?(?=\n|$)',
                    r'(But I need to check|But I need to verify|But I need to confirm).*?(?=\n|$)',
                    r'(Maybe the|Maybe there\'s|Maybe it\'s).*?(?=\n|$)',
                    r'(It\'s possible that|It\'s likely that).*?(?=\n|$)',
                    r'(Without more|Without additional).*?(?=\n|$)',
                ]
                for pattern in thinking_patterns:
                    cleaned_web_data = re.sub(pattern, '', cleaned_web_data, flags=re.DOTALL)
                
                # Remove numbered analysis that's part of thinking process
                cleaned_web_data = re.sub(r'^\d+\.\s*[A-Z].*?(?=\n|$)', '', cleaned_web_data, flags=re.MULTILINE)
                
                # Remove citation markers
                cleaned_web_data = re.sub(r'\[\d+\]', '', cleaned_web_data)
                
                # Remove hashtags and markdown formatting that might be artifacts
                cleaned_web_data = re.sub(r'#+\s*[A-Za-z\s]+', '', cleaned_web_data)
                
                # Remove standalone bullet points that don't have content
                cleaned_web_data = re.sub(r'^\s*•\s*$', '', cleaned_web_data, flags=re.MULTILINE)
                
                # Remove bullet points at the beginning of lines that are followed by whitespace
                cleaned_web_data = re.sub(r'^\s*•\s+(?=\s|$)', '', cleaned_web_data, flags=re.MULTILINE)
                
                            # Clean up extra whitespace and newlines
            cleaned_web_data = re.sub(r'\n\s*\n', '\n', cleaned_web_data)
            cleaned_web_data = cleaned_web_data.strip()
            
            # Import the centralized clean_think_tags_and_debugging function
            from core.text_cleaners import clean_think_tags_and_debugging
            
            # Apply comprehensive cleaning
            cleaned_web_data = clean_think_tags_and_debugging(cleaned_web_data)
        
            profile.web_financial_data = cleaned_web_data
        else:
            print(f"[Financial Analysis] No web search data found for {company_name}")
    
    # Combine all context data
    combined_context = f"{context}\n\n{crunchbase_data}\n\n{web_search_data}"
    
    # Optionally, add more fields as needed
    txt = llm.invoke(PROMPT.format(context=context, web_context=combined_context)).content.strip()
    print("[Financial Chain] LLM raw output:", txt)
    
    # NEW: Run comprehensive financial extraction (regex + AI) on the context
    print("[Financial Chain] Running comprehensive financial extraction...")
    
    # Extract from the full context using both regex and AI
    regex_extracted = extract_financials_from_text(combined_context)
    ai_extracted = ai_extract_financial_data(combined_context)
    
    print(f"[Financial Chain] Regex extracted: {len(regex_extracted)} fields")
    print(f"[Financial Chain] AI extracted: {len(ai_extracted)} categories")
    
    # Update profile with extracted data (prefer AI data, fallback to regex)
    for key, value in regex_extracted.items():
        if value and value != "null":
            # Convert field names to match profile attributes
            field_name = key.replace('_', '')  # Remove underscores for compatibility
            if hasattr(profile, field_name):
                setattr(profile, field_name, value)
                print(f"[Financial Chain] Updated {field_name}={value} (regex)")
            else:
                # Store as custom field
                custom_field = f"financial_{key}"
                setattr(profile, custom_field, value)
                print(f"[Financial Chain] Stored {custom_field}={value} (regex)")
    
    # Process AI-extracted data (more comprehensive)
    for category, category_data in ai_extracted.items():
        if isinstance(category_data, dict):
            for key, value in category_data.items():
                if value and value != "null":
                    # Store as AI-detected field
                    ai_field = f"ai_detected_{category}_{key}"
                    setattr(profile, ai_field, value)
                    print(f"[Financial Chain] Stored {ai_field}={value} (AI)")
        elif value and value != "null":
            # Store as AI-detected field
            ai_field = f"ai_detected_{category}"
            setattr(profile, ai_field, category_data)
            print(f"[Financial Chain] Stored {ai_field}={category_data} (AI)")
    
    # Clean the LLM output to remove debugging artifacts
    cleaned_txt = txt
    
    # Remove <think> tags and their content
    cleaned_txt = re.sub(r'<think>.*?</think>', '', cleaned_txt, flags=re.DOTALL)
    
    # Remove thinking process markers (more comprehensive)
    thinking_patterns = [
        r'(Okay, so I need to figure out|First, from the|Looking at the|Based on the|From the search results|Let me start by|I need to analyze|Let me examine).*?(?=\n|$)',
        r'(Let me look through|I need to look through|Looking at result|Result mentions|First, result|Result from|Based on result).*?(?=\n|$)',
        r'(The user wants|The user asked|The user is asking|The query is about).*?(?=\n|$)',
        r'(I need to answer|I need to tackle|Let me tackle|Let me answer).*?(?=\n|$)',
        r'(Okay, let\'s tackle|Let\'s tackle|Let me tackle).*?(?=\n|$)',
        r'(The user wants me to|The user wants to know|The user is looking for).*?(?=\n|$)',
        r'(I should look|I need to look|Let me look).*?(?=\n|$)',
        r'(Based on the provided|Based on the search|From the search).*?(?=\n|$)',
        r'(Financial Research Summary for|Company:).*?(?=\n|$)',
    ]
    
    for pattern in thinking_patterns:
        cleaned_txt = re.sub(pattern, '', cleaned_txt, flags=re.DOTALL)
    
    # Remove numbered analysis that's part of thinking process
    cleaned_txt = re.sub(r'^\d+\.\s*[A-Z].*?(?=\n|$)', '', cleaned_txt, flags=re.MULTILINE)
    
    # Remove citation markers
    cleaned_txt = re.sub(r'\[\d+\]', '', cleaned_txt)
    
    # Remove hashtags and markdown formatting that might be artifacts
    cleaned_txt = re.sub(r'#+\s*[A-Za-z\s]+', '', cleaned_txt)
    
    # Remove standalone bullet points that don't have content
    cleaned_txt = re.sub(r'^\s*•\s*$', '', cleaned_txt, flags=re.MULTILINE)
    
    # Remove bullet points at the beginning of lines that are followed by whitespace
    cleaned_txt = re.sub(r'^\s*•\s+(?=\s|$)', '', cleaned_txt, flags=re.MULTILINE)
    
    # Clean up extra whitespace and newlines
    cleaned_txt = re.sub(r'\n\s*\n', '\n', cleaned_txt)
    cleaned_txt = cleaned_txt.strip()
    
    # Use cleaned text for JSON parsing
    first, last = cleaned_txt.find("{"), cleaned_txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        print("[Financial Chain] Parsed JSON:", data)
        # Only assign values if they are present in the original text/tables
        for field in ["cash_burn_12m", "runway_months", "implied_valuation", "revenue", "mrr", "gmv", "gross_profit"]:
            val = data.get(field)
            if val is not None and value_in_text(val, context):
                # Additional filtering for obviously wrong values
                if isinstance(val, (int, float)):
                    # Skip if value looks like a year (1900-2030)
                    if 1900 <= val <= 2030:
                        continue
                    # Skip if value is too small for the metric type
                    if field in ["revenue", "cash_burn_12m", "implied_valuation"] and val < 1000:
                        continue
                    # Skip if value is unreasonably large for certain metrics
                    if field in ["runway_months"] and val > 1000:
                        continue
                setattr(profile, field, float(val))
        
        # Store additional financial data from web search - prefer original string format for readability
        if data.get("implied_valuation"):
            valuation_str = str(data.get("implied_valuation")).strip()
            if valuation_str and valuation_str.lower() not in ['none', 'null', 'n/a', 'unknown']:
                # Store the original string format for better readability
                profile.implied_valuation = valuation_str
                # Also store parsed number for calculations if needed
                try:
                    parsed_val = parse_money_string(valuation_str)
                    if parsed_val is not None:
                        profile.implied_valuation_numeric = parsed_val
                except Exception:
                    pass
                
                profile.valuation_source = "web_search"
                # If we have web sources, use the first one as valuation source
                if web_sources:
                    profile.valuation_source = web_sources[0]
                print(f"[Financial Analysis] Stored implied_valuation: {profile.implied_valuation}")
        
        if data.get("total_funding_raised"):
            funding_str = str(data.get("total_funding_raised")).strip()
            if funding_str and funding_str.lower() not in ['none', 'null', 'n/a', 'unknown']:
                # Store the original string format for better readability
                profile.total_funding_raised = funding_str
                # Also store parsed number for calculations if needed
                try:
                    parsed_val = parse_money_string(funding_str)
                    if parsed_val is not None:
                        profile.total_funding_raised_numeric = parsed_val
                except Exception:
                    pass
                
                # Format the funding amount for display
                formatted_funding = format_money_display(profile.total_funding_raised)
                profile.total_funding_raised_display = formatted_funding
                
                profile.funding_source = "web_search"
                # If we have web sources, use the first one as funding source
                if web_sources:
                    profile.funding_source = web_sources[0]
                print(f"[Financial Analysis] Stored total_funding_raised: {formatted_funding}")
        
        if data.get("latest_round_amount"):
            round_str = str(data.get("latest_round_amount")).strip()
            if round_str and round_str.lower() not in ['none', 'null', 'n/a', 'unknown']:
                # Consolidate with existing data - prefer larger/more recent amounts
                existing_amount = getattr(profile, 'latest_round_amount', None)
                if existing_amount:
                    # Parse both amounts for comparison
                    try:
                        new_amount_parsed = parse_money_string(round_str)
                        existing_amount_parsed = parse_money_string(existing_amount)
                        
                        if new_amount_parsed and existing_amount_parsed:
                            # Prefer the larger amount (more recent/larger round)
                            if new_amount_parsed > existing_amount_parsed:
                                profile.latest_round_amount = round_str
                                print(f"[Financial Analysis] Updated latest_round_amount: {existing_amount} -> {round_str}")
                            else:
                                print(f"[Financial Analysis] Keeping existing amount: {existing_amount} (larger than {round_str})")
                                return profile
                        else:
                            # If parsing fails, prefer the one that looks more recent
                            if 'million' in round_str.lower() or 'billion' in round_str.lower():
                                profile.latest_round_amount = round_str
                                print(f"[Financial Analysis] Updated to larger amount: {round_str}")
                    except Exception:
                        # If comparison fails, keep existing
                        print(f"[Financial Analysis] Keeping existing amount due to parsing error")
                        return profile
                else:
                    # No existing amount, store the new one
                    profile.latest_round_amount = round_str
                
                # Format the round amount for display
                formatted_round = format_money_display(profile.latest_round_amount)
                profile.latest_round_amount_display = formatted_round
                
                # Also store parsed number for calculations if needed
                try:
                    parsed_val = parse_money_string(round_str)
                    if parsed_val is not None:
                        profile.latest_round_amount_numeric = parsed_val
                except Exception:
                    pass
                print(f"[Financial Analysis] Stored latest_round_amount: {formatted_round}")
        
        if data.get("latest_round_date"):
            profile.latest_round_date = data.get("latest_round_date")
        
        if data.get("revenue"):
            try:
                parsed_val = parse_money_string(str(data.get("revenue")))
                if parsed_val is not None:
                    profile.revenue = parsed_val
                else:
                    print(f"[Financial Analysis] Could not parse revenue: {data.get('revenue')}")
            except Exception as e:
                print(f"[Financial Analysis] Error parsing revenue: {e}")
        
        # Store web sources for clickable links
        if data.get("web_sources"):
            profile.web_sources = data.get("web_sources")
            print(f"[Financial Analysis] Stored {len(data.get('web_sources'))} web sources from LLM")
            print(f"[Financial Analysis] Web sources content: {data.get('web_sources')}")
        elif web_sources:
            profile.web_sources = web_sources
            print(f"[Financial Analysis] Stored {len(web_sources)} web sources from search")
            print(f"[Financial Analysis] Web sources content: {web_sources}")
        
        # Debug: Check what's actually stored
        print(f"[Financial Analysis] Final profile.web_sources: {profile.web_sources}")
        print(f"[Financial Analysis] Final profile.web_sources type: {type(profile.web_sources)}")
        
        if data.get("summary"):
            profile.financial_summary = data.get("summary")
        if data.get("financials_table"):
            profile.financials_table = data.get("financials_table")
        if data.get("financials_by_year"):
            profile.financials_by_year = data.get("financials_by_year")
    except Exception as e:
        print(f"[Financial Chain Parsing Error] {e}")
        # Don't pass here, continue with regex fallback
    # Regex fallback: extract from summary text if present
    summary_text = txt if isinstance(txt, str) else ""
    extracted = extract_financials_from_text(summary_text)
    print("[Financial Chain] Regex extracted:", extracted)
    if extracted:
        print("[Financial Chain] Context for extraction:", summary_text[:500] + "..." if len(summary_text) > 500 else summary_text)
    
    # Only use regex fallback for fields that weren't already set by LLM JSON parsing
    for k, v in extracted.items():
        if hasattr(profile, k) and v and value_in_text(v, context):
            # Only set if the field is None or if the regex value is more reasonable
            current_value = getattr(profile, k)
            if current_value is None:
                setattr(profile, k, v)
            elif isinstance(current_value, (int, float)) and isinstance(v, (int, float)):
                # Only override if the new value is more reasonable (larger for financial metrics)
                if k in ["revenue", "cash_burn_12m", "implied_valuation"] and v > current_value:
                    setattr(profile, k, v)
                elif k in ["runway_months"] and 0 < v < 100:  # Reasonable runway range
                    setattr(profile, k, v)
    if not profile.startup_id:
        from hashlib import sha1
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    return profile
