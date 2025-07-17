from crewai import Agent, Task
from langchain_openai import ChatOpenAI

from core.schemas import StartupProfile
from chains.founder_profiling_chain import run_founder_profiling_chain
import os
import requests

llm = ChatOpenAI(model="gpt-4", temperature=0.2)


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


def build_founder_profiling_agent(profile: StartupProfile, trace_id=None):
    partner = Agent(
        role="Founder-profiling partner",
        goal="Evaluate founders' track-record, fit, and entrepreneurial experience.",
        backstory="20-year VC who focuses on team quality, founder-market fit, and leadership potential. Expert in assessing founder backgrounds and prior exits.",
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        updated = run_founder_profiling_chain(profile)
        # LinkedIn enrichment
        if updated.founder_name:
            linkedin_data = get_linkedin_profile_proxycurl(updated.founder_name, updated.name)
            updated.founder_linkedin_data = linkedin_data
            updated.founder_linkedin_formatted = format_linkedin_profile(linkedin_data)
        return updated.model_dump_json(indent=2)

    task = Task(
        description="Score founder fit, count prior exits, and provide a summary of founder experience and leadership, including LinkedIn enrichment.",
        agent=partner,
        expected_output="A detailed founder profile including fit score, prior exits, relevant experience, and LinkedIn data.",
        callback=_callback,
    )
    return partner, task


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
