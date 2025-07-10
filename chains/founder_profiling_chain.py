import json
from hashlib import sha1
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os
import requests

from core.schemas import StartupProfile
from core.hybrid_context import get_hybrid_context

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

SYSTEM = """\
You are an experienced VC partner evaluating founders.
Return JSON with two keys:
  founder_fit_score  – float between 0 and 1 (higher = stronger team)
  prior_exits        – integer count of successful past exits
If info is missing, default to 0.3 and 0.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM), ("human", "Founder info:\n{context}\n")]
)


def run_founder_profiling_chain(profile: StartupProfile) -> StartupProfile:
    context = get_hybrid_context(
        profile, "founder OR CEO OR linkedin OR crunchbase", 3, 3
    )
    txt = llm.invoke(PROMPT.format(context=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        profile.founder_fit_score = float(data.get("founder_fit_score", 0.3))
        profile.prior_exits = int(data.get("prior_exits", 0))
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[
            :10
        ]
    return profile

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


def run_founder_profiling_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    """Run founder profiling using extracted text as context."""
    context = full_text[:5000]  # Truncate if needed for prompt size
    txt = llm.invoke(PROMPT.format(context=context)).content.strip()
    first, last = txt.find("{"), txt.rfind("}")
    if first == -1 or last == -1:
        return profile
    try:
        data = json.loads(txt[first : last + 1])
        profile.founder_fit_score = float(data.get("founder_fit_score", 0.3))
        profile.prior_exits = int(data.get("prior_exits", 0))
    except:
        pass
    if not profile.startup_id:
        profile.startup_id = sha1((profile.name or context[:40]).encode()).hexdigest()[:10]
    # After extracting founder name:
    if profile.founder_name:
        linkedin_data = get_linkedin_profile_proxycurl(profile.founder_name, profile.name)
        profile.founder_linkedin_data = linkedin_data
        profile.founder_linkedin_formatted = format_linkedin_profile(linkedin_data)
    return profile
