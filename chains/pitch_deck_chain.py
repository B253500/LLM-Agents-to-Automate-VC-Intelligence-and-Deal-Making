import json
import os
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from dotenv import load_dotenv
import pdfplumber
from core.schemas import StartupProfile
import requests
from langchain_core.prompts import ChatPromptTemplate
from crewai.tools import BaseTool
from typing import Dict, List, Optional
from pydantic import Field, BaseModel
import warnings

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
load_dotenv()


def get_llm():
    return ChatOpenAI(model="gpt-4", temperature=0.2)


# EXA Search tool for internet research
class EXASearchTool(BaseTool):
    name: str = "exa_search"
    description: str = (
        "Search the web for current information about companies, markets, and competitors"
    )
    api_key: str = Field(default_factory=lambda: os.getenv("EXA_API_KEY", ""))
    base_url: str = "https://api.exa.ai/search"

    def _run(self, query: str) -> str:
        """Run the search tool."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "query": query,
            "type": "keyword",
            "use_autoprompt": True,
            "category": "news",
            "startPublishedDate": "2020-01-01",
            "excludeText": ["advertisement", "sponsored"],
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            results = response.json()
            return json.dumps(results, indent=2)
        except Exception as e:
            return f"Error performing search: {str(e)}"

    async def _arun(self, query: str) -> str:
        """Run the search tool asynchronously."""
        return self._run(query)


# Create the search tool
search_tool = EXASearchTool()


# Market Size tool
def estimate_market_size(data: str) -> str:
    return f"Estimated market size based on: {data}"


market_size_tool = Tool(
    name="Market Size Estimator",
    func=estimate_market_size,
    description="Estimates market size based on provided data.",
)


# CAGR calculator tool
def calculate_cagr(initial_value: float, final_value: float, num_years: int) -> float:
    cagr = (final_value / initial_value) ** (1 / num_years) - 1
    return cagr


cagr_tool = Tool(
    name="CAGR Calculator",
    func=calculate_cagr,
    description="Calculates CAGR given initial value, final value, and number of years.",
)


def create_agent(role: str, goal: str, backstory: str, tools: list = None) -> Agent:
    """Create a CrewAI agent with the specified role and tools."""
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        tools=tools or [],
        verbose=True,
        llm=ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7),
    )


SYSTEM = """
You are a top-tier VC investment analyst. Extract the following fields as JSON:
{{
    "name": "Company name",
    "founder_name": "Founder's full name",
    "sector": "Primary business sector",
    "website": "Company website URL",
    "funding_stage": "Current funding stage (e.g., Seed, Series A, etc.)"
}}

Guidelines:
1. Extract ONLY information explicitly stated in the text
2. If a field is not found, use "unknown"
3. For website, look for URLs or "visit us at..." patterns
4. For funding stage, look for terms like "Seed", "Series A", "Pre-seed", etc.
5. Do NOT make assumptions or infer information
6. Return ONLY valid JSON
"""
HUMAN = "Pitch-deck text (first 5000 characters):\n```markdown\n{deck}\n```"
PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", HUMAN)])

# Suppress PDF warnings
warnings.filterwarnings("ignore", message=".*CropBox.*")


class MarketInfo(BaseModel):
    TAM: Optional[str] = None
    SAM: Optional[str] = None
    SOM: Optional[str] = None
    growth_rate: Optional[str] = None
    key_drivers: List[str] = []
    barriers: List[str] = []


class CompetitorInfo(BaseModel):
    competitors: List[Dict] = []


def read_pdf_content(pdf_path: str) -> str:
    """Read and extract text content from PDF with improved error handling."""
    try:
        content = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    text = page.extract_text()
                    if text:
                        content.append(text)
                except Exception as e:
                    print(f"Warning: Error extracting text from page: {e}")
                    continue
        return "\n---PAGE BREAK---\n".join(content)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""


def run_pitch_deck_chain(pdf_path: str) -> StartupProfile:
    """Run the pitch deck analysis chain."""
    # Read PDF content
    pdf_content = read_pdf_content(pdf_path)
    if not pdf_content:
        raise ValueError("Failed to extract content from PDF")

    # Create agents
    company_analyst = Agent(
        role="Company Analyst",
        goal="Extract accurate company information from pitch decks",
        backstory="""You are an expert at analyzing pitch decks and extracting key company information.
        You have years of experience in venture capital and startup analysis.
        You are thorough and precise in your analysis.""",
        verbose=True,
        allow_delegation=False,
        llm=get_llm(),
    )

    market_analyst = Agent(
        role="Market Analyst",
        goal="Analyze market size and dynamics from pitch decks",
        backstory="""You are a market research expert specializing in startup markets.
        You have deep experience in market sizing and competitive analysis.
        You are skilled at identifying market drivers and barriers.""",
        verbose=True,
        allow_delegation=False,
        llm=get_llm(),
    )

    competitor_analyst = Agent(
        role="Competitor Analyst",
        goal="Analyze competitive landscape from pitch decks",
        backstory="""You are an expert in competitive analysis and market positioning.
        You have extensive experience analyzing startup competitive advantages.
        You are skilled at identifying market leaders and their strategies.""",
        verbose=True,
        allow_delegation=False,
        llm=get_llm(),
    )

    # Create tasks with unique names
    company_task = Task(
        description=f"""Analyze the following pitch deck content and extract key company information.
        You MUST return a valid JSON object with the following structure:
        {{
            "name": "Company name",
            "founder": "Founder name",
            "sector": "Primary sector",
            "website": "Company website",
            "funding_stage": "Current funding stage",
            "funding_amount": "Total funding raised",
            "tech_maturity": "Technology readiness level",
            "moat_strength": "Competitive moat assessment"
        }}

        Pitch deck content:
        {pdf_content}

        Guidelines:
        1. Look for company name in headers and title slides
        2. Find founder information in team/about sections
        3. Identify sector from problem statement and solution
        4. Look for website in contact/footer sections
        5. Find funding info in financial/traction slides
        6. Assess tech maturity from product/roadmap slides
        7. Evaluate moat from competitive advantage slides

        IMPORTANT: Your response must be ONLY the JSON object, with no additional text or explanation.
        Do not include any markdown formatting or code blocks.""",
        agent=company_analyst,
        expected_output="JSON object containing company information",
        name="company_analysis",
    )

    market_task = Task(
        description=f"""Analyze the following pitch deck content and extract market information.
        You MUST return a valid JSON object with the following structure:
        {{
            "TAM": "Total addressable market size",
            "SAM": "Serviceable addressable market size",
            "SOM": "Serviceable obtainable market size",
            "growth_rate": "Market growth rate",
            "key_drivers": ["List of key market drivers"],
            "barriers": ["List of market barriers"]
        }}

        Pitch deck content:
        {pdf_content}

        Guidelines:
        1. Look for market size in market analysis slides
        2. Find growth rates in market trends slides
        3. Identify drivers in market opportunity slides
        4. Look for barriers in market challenges slides

        IMPORTANT: Your response must be ONLY the JSON object, with no additional text or explanation.
        Do not include any markdown formatting or code blocks.""",
        agent=market_analyst,
        expected_output="JSON object containing market information",
        name="market_analysis",
    )

    competitor_task = Task(
        description=f"""Analyze the following pitch deck content and extract competitor information.
        You MUST return a valid JSON object with the following structure:
        {{
            "competitors": [
                {{
                    "name": "Competitor name",
                    "position": "Market position",
                    "advantages": ["List of advantages"],
                    "moats": ["List of competitive moats"],
                    "market_share": "Market share",
                    "growth_rate": "Growth rate",
                    "technology": "Technology description",
                    "pricing": "Pricing strategy",
                    "gtm": "Go-to-market approach"
                }}
            ]
        }}

        Pitch deck content:
        {pdf_content}

        Guidelines:
        1. Look for competitors in competitive analysis slides
        2. Find market positions in market share slides
        3. Identify advantages in competitive advantage slides
        4. Look for technology comparisons in product slides

        IMPORTANT: Your response must be ONLY the JSON object, with no additional text or explanation.
        Do not include any markdown formatting or code blocks.""",
        agent=competitor_analyst,
        expected_output="JSON object containing competitor information",
        name="competitor_analysis",
    )

    # Create and run crew
    crew = Crew(
        agents=[company_analyst, market_analyst, competitor_analyst],
        tasks=[company_task, market_task, competitor_task],
        verbose=True,
        process=Process.sequential,
    )

    result = crew.kickoff()

    # Parse results using task names
    try:
        # Access results from the crew output
        company_info = {}
        market_info = {}
        competitor_info = {}

        # Extract results from each task's output
        for task in result.tasks:
            try:
                if task.name == "company_analysis":
                    # Clean the output to ensure it's valid JSON
                    output = task.output.strip()
                    if output.startswith("```json"):
                        output = output[7:]
                    if output.endswith("```"):
                        output = output[:-3]
                    company_info = json.loads(output.strip())
                elif task.name == "market_analysis":
                    output = task.output.strip()
                    if output.startswith("```json"):
                        output = output[7:]
                    if output.endswith("```"):
                        output = output[:-3]
                    market_info = json.loads(output.strip())
                elif task.name == "competitor_analysis":
                    output = task.output.strip()
                    if output.startswith("```json"):
                        output = output[7:]
                    if output.endswith("```"):
                        output = output[:-3]
                    competitor_info = json.loads(output.strip())
            except json.JSONDecodeError as e:
                print(f"Error parsing {task.name} output: {e}")
                print(f"Raw output: {task.output}")

    except Exception as e:
        print(f"Error processing results: {e}")
        company_info = {}
        market_info = {}
        competitor_info = {}

    # Create profile with proper model instances
    profile = StartupProfile(
        startup_id=company_info.get("name", "").lower().replace(" ", "_"),
        name=company_info.get("name"),
        founder_name=company_info.get("founder"),
        sector=company_info.get("sector"),
        website=company_info.get("website"),
        funding_stage=company_info.get("funding_stage"),
        funding_amount=company_info.get("funding_amount"),
        tech_maturity=company_info.get("tech_maturity"),
        moat_strength=company_info.get("moat_strength"),
        market_info=MarketInfo(**market_info) if market_info else None,
        competitor_info=CompetitorInfo(**competitor_info) if competitor_info else None,
    )

    return profile
