from pydantic import BaseModel, Field
from typing import List, Optional


class Competitor(BaseModel):
    name: str
    url: Optional[str] = None
    differentiator: Optional[str] = None


class StartupProfile(BaseModel):
    # Filled in after parsing, so keep it optional during validation
    startup_id: str | None = Field(
        default=None, description="Deterministic slug/hash added later"
    )

    # Basic identifiers
    name: Optional[str] = None
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
