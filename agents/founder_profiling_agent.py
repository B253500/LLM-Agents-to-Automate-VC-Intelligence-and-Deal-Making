from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context
import os
import requests
import json
from hashlib import sha1

llm = ChatOpenAI(model="gpt-4", temperature=0.2)

SYSTEM = """\
You are an experienced VC partner evaluating founders.
Return JSON with two keys:
  founder_fit_score  – float between 0 and 1 (higher = stronger team)
  prior_exits        – integer count of successful past exits
If info is missing, default to 0.3 and 0.
"""
PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM), ("human", "Founder info:\n{context}\n")
])

def get_linkedin_profile_proxycurl(founder_name, company_name=None):
    api_key = os.getenv("PROXYCURL_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {
        "first_name": founder_name.split()[0],
        "last_name": founder_name.split()[-1],
    }
    if company_name:
        params["company"] = company_name
    url = "https://nubela.co/proxycurl/api/v2/linkedin/person"
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Proxycurl error: {response.status_code} {response.text}")
        return None

def format_linkedin_profile(data):
    if not data:
        return "No LinkedIn profile found."
    return f"""
LinkedIn: {data.get('profile_url', 'N/A')}
Headline: {data.get('headline', 'N/A')}
Summary: {data.get('summary', 'N/A')}
Current Position: {data.get('occupation', 'N/A')}
"""

def build_founder_profiling_agent(deck_payload):
    founder = Agent(
        role="Founder-profiling partner",
        goal="Enrich the team profile with detailed founder and executive backgrounds, achievements, and unique skills.",
        backstory="A former executive search partner…",
        verbose=True,
        llm=llm,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300,
    )

    def _callback(context, *args, **kwargs):
        # In hierarchical mode, ignore incoming context and start fresh
        profile = StartupProfile()
        if deck_payload:
            print(f"[founder_profiling_agent] Deck text (first 200 chars): {deck_payload.get('text', '')[:200]}")
        else:
            print(f"[founder_profiling_agent] No deck_payload provided.")
        from core.hybrid_context import safe_truncate
        ctx = get_hybrid_context(profile, "founder OR CEO OR linkedin OR crunchbase", 3, 3)
        ctx = safe_truncate(ctx, max_chars=1500)
        deck_text = safe_truncate(deck_payload.get('text', '') if deck_payload else '', max_chars=1500)
        prompt_context = f"{ctx}\n\nFull Deck Text:\n{deck_text}"
        print(f"[founder_profiling_agent] LLM prompt context (first 300 chars): {prompt_context[:300]}")
        raw = llm.invoke(PROMPT.format(context=prompt_context)).content.strip()
        print(f"[founder_profiling_agent] LLM raw output (first 300 chars): {raw[:300]}")
        first, last = raw.find("{"), raw.rfind("}")
        if first != -1 and last != -1:
            try:
                data = json.loads(raw[first : last + 1])
                print(f"[founder_profiling_agent] Parsed LLM JSON: {data}")
                profile.founder_fit_score = float(data.get("founder_fit_score", 0.3))
                profile.prior_exits      = int(data.get("prior_exits", 0))
            except Exception as e:
                print(f"[founder_profiling_agent] [Error] parsing founder JSON: {e}")
        if not profile.startup_id:
            seed = profile.name or ctx[:40]
            profile.startup_id = sha1(seed.encode()).hexdigest()[:10]
        if profile.founder_name:
            linkedin_data = get_linkedin_profile_proxycurl(profile.founder_name, profile.name)
            profile.founder_linkedin_data      = linkedin_data
            profile.founder_linkedin_formatted = format_linkedin_profile(linkedin_data)
        output = profile.model_dump()
        print(f"[founder_profiling_agent] Output type: {type(output)}")
        print(f"[founder_profiling_agent] Output keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
        return output

    task = Task(
        description="Score founder fit, count prior exits, and enrich with LinkedIn data.",
        agent=founder,
        callback=_callback,
        expected_output="JSON with founder_fit_score, prior_exits, linkedin_data, etc."
    )

    return founder, task


def build_founder_chain_agent(profile):
    def chain_callback(*_):
        from chains.founder_profiling_chain import run_founder_profiling_chain
        updated_profile = run_founder_profiling_chain(profile)
        return updated_profile.model_dump()
    agent = Agent(
        role="Founder Extractor",
        goal="Extract founder and team information from the deck.",
        backstory="A specialized agent for extracting founder and team data from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract founder and team information from the deck.",
        agent=agent,
        callback=chain_callback,
        args=[profile.model_dump()],
        expected_output="Profile with founder/team fields extracted."
    )
    return agent, task
