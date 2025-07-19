from pydantic import BaseModel
from typing import List, Optional
from pydantic import BaseModel, Field


class Competitor(BaseModel):
    name: str
    url: Optional[str] = None
    differentiator: Optional[str] = None


class Table(BaseModel):
    page: int | None = None
    rows: list[list[str]] = []
    boundingBox: dict = {}

class Figure(BaseModel):
    page: int | None = None
    boundingBox: dict = {}
    blockType: str = ""

class StartupProfile(BaseModel):
    name: str = Field(None, alias="company_name")
    founder_name: str = Field(None, alias="founders")
    # Filled in after parsing, so keep it optional during validation
    startup_id: str | None = Field(
        default=None, description="Deterministic slug/hash added later"
    )
    # Basic identifiers
    sector: Optional[str] = None
    website: Optional[str] = None
    funding_stage: Optional[str] = None

    # Populated by specialised agents (Phase 2+)
    tech_maturity: Optional[str] = None
    moat_strength: Optional[str] = None
    founder_fit_score: Optional[float] = None
    prior_exits: Optional[int] = None
    top_competitors: List[Competitor] = []
    TAM: Optional[float] = None
    SAM: Optional[float] = None
    SOM: Optional[float] = None
    cash_burn_12m: Optional[float] = None
    runway_months: Optional[float] = None
    implied_valuation: Optional[float] = None
    risk_flags: List[str] = []
    risk_score: Optional[float] = None
    esg_summary: Optional[str] = None
    business_model: Optional[str] = None
    exit_strategy: Optional[str] = None
    follow_up_questions: Optional[str] = None
    tech_stack: Optional[str] = None  # Added for technical stack descriptions
    product_description: Optional[str] = None  # Description of the core product/service
    executives: Optional[List[dict]] = []
    prior_exit_details: Optional[List[dict]] = []
    founder_linkedin_data: Optional[dict] = None
    founder_linkedin_formatted: Optional[str] = None
    exa_market_context: Optional[str] = None

    # New fields for structured data
    tables: List[Table] = []
    figures: List[Figure] = []
    # Visuals and charts for memo
    extracted_image_paths: Optional[List[str]] = []
    market_chart_path: Optional[str] = None
    # Visual enrichment results (e.g., OCR from graphs/tables)
    visual_enrichment: Optional[List[dict]] = []
    # Technical news enrichment
    tech_news: Optional[str] = None
    # Financial news enrichment
    financial_news: Optional[str] = None
    # Risk news enrichment
    risk_news: Optional[str] = None
    # Enriched top competitors (from agent enrichment)
    enriched_top_competitors: Optional[list] = []
    # Raw extracted text from the PDF
    raw_text: Optional[str] = None
    # File path of the processed PDF
    filepath: Optional[str] = None
    figures_ocr: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
