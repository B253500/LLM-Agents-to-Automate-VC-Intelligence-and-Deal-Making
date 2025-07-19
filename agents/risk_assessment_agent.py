from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile
from core.perplexity_utils import search_perplexity
import json
from hashlib import sha1
from core.hybrid_context import safe_truncate

llm = ChatOpenAI(model="gpt-4", temperature=0.2)

SYSTEM = """\
You are an investment-risk officer specializing in startup risk assessment.
Analyze the startup profile and identify potential risk factors.

Return JSON with:
  risk_flags – array of short risk descriptions (≤5 words each)
  risk_score – float 0-1 (0 = low risk, 1 = high risk)
  risk_summary – brief summary of key risks

Consider factors like:
- Market size and competition
- Team experience and track record
- Financial health and runway
- Technology maturity
- Regulatory risks
- Market timing

If insufficient data to assess risks, set risk_score to null and risk_flags to empty array.
"""
PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Profile:\n```json\n{profile}\n```")
])

def get_recent_risk_news(company_name):
    if not company_name:
        return None
    query = f"Recent risk-related news, controversies, or red flags for {company_name} (past 12 months)."
    return search_perplexity(query)

def build_risk_assessment_agent(profile: StartupProfile, trace_id=None):
    officer = Agent(
        role="Risk-assessment officer",
        goal="Identify red-flags, compute risk score, and assess overall risk profile of the startup.",
        backstory="Former credit-risk VP now in VC. Expert in risk modeling, red-flag detection, and startup risk assessment.",
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
            print(f"[risk_assessment_agent] Deck text (first 200 chars): {deck_payload.get('text', '')[:200]}")
        else:
            print(f"[risk_assessment_agent] No deck_payload provided.")
        # Build context and prompt
        ctx = get_hybrid_context(profile, "risk OR mitigation OR threat OR challenge", 3, 3)
        ctx = safe_truncate(ctx, max_chars=1500)
        deck_text = safe_truncate(deck_payload.get('text', '') if deck_payload else '', max_chars=1500)
        prompt_context = f"{ctx}\n\nFull Deck Text:\n{deck_text}"
        print(f"[risk_assessment_agent] LLM prompt context (first 300 chars): {prompt_context[:300]}")
        raw = llm.invoke(PROMPT.format(context=prompt_context)).content.strip()
        print(f"[risk_assessment_agent] LLM raw output (first 300 chars): {raw[:300]}")
        # --- Chain logic inlined here ---
        txt = llm.invoke(PROMPT.format(profile=profile.model_dump_json())).content.strip()
        first, last = txt.find("{"), txt.rfind("}")
        if first != -1 and last != -1:
            try:
                data = json.loads(txt[first : last + 1])
                profile.risk_flags = data.get("risk_flags", [])
                risk_score = data.get("risk_score")
                if risk_score is not None:
                    profile.risk_score = float(risk_score)
            except Exception as e:
                print(f"[Risk Assessment Parsing Error] {e}")
        if not profile.startup_id:
            profile.startup_id = sha1((profile.name or "risk").encode()).hexdigest()[:10]
        # 2. Enrich: web search for recent risk-related news
        news = get_recent_risk_news(profile.name)
        profile.risk_news = news
        print(f"[risk_assessment_agent] Output profile: {profile.model_dump()}")
        output = profile.model_dump()
        print(f"[risk_assessment_agent] Output type: {type(output)}")
        print(f"[risk_assessment_agent] Output keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
        return output

    task = Task(
        description="Flag risks, score overall risk, provide a risk assessment summary, and enrich with recent risk-related news.",
        agent=officer,
        expected_output="A detailed risk assessment report including risk flags, risk score, mitigation suggestions, and recent risk-related news.",
        callback=_callback,
    )
    return officer, task


def build_risk_chain_agent(profile):
    def chain_callback(*_):
        from chains.risk_assessment_chain import run_risk_assessment_chain
        updated_profile = run_risk_assessment_chain(profile)
        return updated_profile.model_dump()
    agent = Agent(
        role="Risk Assessment Extractor",
        goal="Extract risk assessment data from the deck.",
        backstory="A specialized agent for extracting risk assessment data from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract risk assessment data from the deck.",
        agent=agent,
        callback=chain_callback,
        args=[profile.model_dump()],
        expected_output="Profile with risk assessment fields extracted."
    )
    return agent, task
