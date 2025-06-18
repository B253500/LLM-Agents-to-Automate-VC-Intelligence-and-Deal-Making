# memo_api/services/memo_generator.py
from openai import OpenAI

CLIENT = OpenAI()

HTML_PROMPT = """
<h2>Generated using Flybridge Memo Generator</h2>

<h2>Executive Summary</h2>
Deal Terms: {currentRound} at {proposedValuation} (Date: {valuationDate})  
Opportunity: {opportunity}

<h2>Market Opportunity and Sizing</h2>
Market Analysis: {market_analysis}  
Competitor Analysis: {competitor_analysis}

<h2>Product/Service Description</h2>
Full Context: {extractedText}

<h2>Team</h2>
Founder Info: {founder_block}

<!-- and so on for the rest of the sections… -->

"""


async def generate(opportunity, analysis, founders, meta, trace_id):
    # Build the filled‐in prompt by substituting into HTML_PROMPT
    filled = HTML_PROMPT.format(
        opportunity=opportunity,
        currentRound=meta.get("currentRound", ""),
        proposedValuation=meta.get("proposedValuation", ""),
        valuationDate=meta.get("valuationDate", ""),
        market_analysis=analysis.get("market_analysis", ""),
        competitor_analysis=analysis.get("competitor_analysis", ""),
        extractedText=meta.get("extractedText", "")[:4000],  # truncated
        founder_block=founders,
    )

    # Send exactly one user‐role message containing all instructions + data
    resp = CLIENT.chat.completions.create(
        model="o1-mini",
        messages=[{"role": "user", "content": filled}],
    )

    return resp.choices[0].message.content
