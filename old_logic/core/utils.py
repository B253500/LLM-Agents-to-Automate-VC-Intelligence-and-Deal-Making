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
    """
    Parse money strings like "$1.5M", "2.3B", "500K" into numeric values.
    """
    import re
    s = s.replace(",", "").strip()
    match = re.match(r"\$?([\d\.]+)\s*([KMB]?)", s, re.IGNORECASE)
    if not match:
        return None
    num, suffix = match.groups()
    num = float(num)
    multiplier = {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}
    return num * multiplier.get(suffix.upper(), 1) 