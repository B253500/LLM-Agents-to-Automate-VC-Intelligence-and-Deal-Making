from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile
from core.perplexity_utils import search_perplexity
import json
from hashlib import sha1
from core.hybrid_context import safe_truncate

llm = ChatOpenAI(model="gpt-4", temperature=0.2)

SYSTEM = """
You are a VC financial analyst specializing in startup financial analysis.
Analyze the company's financial data and provide:
- Key metrics (burn, runway, valuation, revenue, funding sought)
- A concise summary of financial health and risks
- Commentary on missing data and red flags
- Any recent financial news (use web search context if available)
- Attribute sources where possible
Return JSON with numeric fields and a 'summary' field.
If you cannot find reliable data for a field, set it to null instead of 0.
"""
PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Financial snippets:\n{context}\nWeb search context:\n{web_context}\n")
])

def get_recent_financial_news(company_name):
    if not company_name:
        return None
    query = f"Recent financial news, funding rounds, or valuation updates for {company_name} (past 12 months)."
    return search_perplexity(query)

def build_financial_analysis_agent(profile: StartupProfile, trace_id=None):
    fa = Agent(
        role="Financial analyst",
        goal="Estimate burn, runway, implied valuation, and analyze financial health of the startup.",
        backstory="Ex-investment-banker who crunches numbers for VC deals. Expert in financial modeling, cash flow analysis, and startup valuation.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(context, *args, **kwargs):
        # In hierarchical mode, ignore incoming context and start fresh
        profile = StartupProfile()
        if deck_payload:
            print(f"[financial_analysis_agent] Deck text (first 200 chars): {deck_payload.get('text', '')[:200]}")
        else:
            print(f"[financial_analysis_agent] No deck_payload provided.")
        # Build context and prompt
        ctx = get_hybrid_context(profile, "financial OR revenue OR profit OR loss OR EBITDA OR cash flow", 3, 3)
        ctx = safe_truncate(ctx, max_chars=1500)
        deck_text = safe_truncate(deck_payload.get('text', '') if deck_payload else '', max_chars=1500)
        prompt_context = f"{ctx}\n\nFull Deck Text:\n{deck_text}"
        print(f"[financial_analysis_agent] LLM prompt context (first 300 chars): {prompt_context[:300]}")
        raw = llm.invoke(PROMPT.format(context=prompt_context)).content.strip()
        print(f"[financial_analysis_agent] LLM raw output (first 300 chars): {raw[:300]}")
        # --- Chain logic inlined here ---
        context_str = f"""
Funding: {getattr(profile, 'funding_stage', '')}
Revenue: {getattr(profile, 'revenue', '')}
Prior Exits: {getattr(profile, 'prior_exits', '')}
Sector: {getattr(profile, 'sector', '')}
"""
        txt = llm.invoke(PROMPT.format(context=context_str, web_context="")).content.strip()
        first, last = txt.find("{"), txt.rfind("}")
        if first != -1 and last != -1:
            try:
                data = json.loads(txt[first : last + 1])
                if data.get("cash_burn_12m") is not None:
                    profile.cash_burn_12m = float(data.get("cash_burn_12m"))
                if data.get("runway_months") is not None and data.get("runway_months", 0) > 0:
                    profile.runway_months = float(data.get("runway_months"))
                if data.get("implied_valuation") is not None and data.get("implied_valuation", 0) > 0:
                    profile.implied_valuation = float(data.get("implied_valuation"))
                if data.get("summary"):
                    profile.financial_summary = data.get("summary")
            except Exception as e:
                print(f"[Financial Analysis Parsing Error] {e}")
        if not profile.startup_id:
            profile.startup_id = sha1((profile.name or ctx[:40]).encode()).hexdigest()[:10]
        # 2. Enrich: web search for recent financial news
        news = get_recent_financial_news(profile.name)
        profile.financial_news = news
        print(f"[financial_analysis_agent] Output profile: {profile.model_dump()}")
        output = profile.model_dump()
        print(f"[financial_analysis_agent] Output type: {type(output)}")
        print(f"[financial_analysis_agent] Output keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
        return output

    task = Task(
        description="Compute cash burn, runway, implied valuation, provide a financial health summary, and enrich with recent financial news.",
        agent=fa,
        expected_output="A detailed financial analysis report including cash burn, runway, valuation, key financial metrics, and recent financial news.",
        callback=_callback,
    )
    return fa, task


def build_financial_chain_agent(profile):
    def chain_callback(*_):
        from chains.financial_analysis_chain import run_financial_analysis_chain
        updated_profile = run_financial_analysis_chain(profile)
        return updated_profile.model_dump()
    agent = Agent(
        role="Financial Analysis Extractor",
        goal="Extract financial analysis data from the deck.",
        backstory="A specialized agent for extracting financial analysis data from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract financial analysis data from the deck.",
        agent=agent,
        callback=chain_callback,
        args=[profile.model_dump()],
        expected_output="Profile with financial analysis fields extracted."
    )
    return agent, task
