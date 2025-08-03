# Utility functions for the VC agents system

def merge_outputs(chain_output, agent_output):
    """
    Helper to merge chain and agent outputs.
    If both are dicts, merge keys; if both are strings, concatenate.
    """
    if not agent_output:
        return chain_output
    if not chain_output:
        return agent_output
    # If both are dicts, merge keys; if both are strings, concatenate
    if isinstance(chain_output, dict) and isinstance(agent_output, dict):
        merged = chain_output.copy()
        merged.update(agent_output)
        return merged
    return f"{chain_output}\n{agent_output}"

def synthesize_product_description(profile):
    """
    Enhanced Product Description Extraction.
    Prefer explicit product_description, else synthesize from solution, tech, business model.
    """
    descs = [
        getattr(profile, 'product_description', None),
        getattr(profile, 'tech_stack', None),
        getattr(profile, 'moat_strength', None),
        getattr(profile, 'business_model', None),
        getattr(profile, 'tech_maturity', None),
    ]
    # Filter out None values and convert to strings, handling non-string types
    filtered_descs = []
    for d in descs:
        if d is not None:
            if isinstance(d, str):
                if d.lower() not in ['n/a', 'not available', 'unknown']:
                    filtered_descs.append(d)
            else:
                # Convert non-string types to string
                filtered_descs.append(str(d))
    
    if not filtered_descs:
        return 'Product description not available.'
    
    # Remove duplicates and repetitive phrases
    seen = set()
    result = []
    for d in filtered_descs:
        if d not in seen and len(d.split()) > 6:
            result.append(d)
            seen.add(d)
    return '\n'.join(result) if result else filtered_descs[0]

def parse_money_string(s):
    """Enhanced money string parser that handles various currency formats."""
    if s is None:
        return None
    
    s = str(s).replace(",", "").strip()
    
    # Remove currency codes (USD, EUR, etc.) first - look anywhere in the string
    import re
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