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
    founder_name: str | None = None
    
    class Config:
        extra = "allow"  # Allow any extra fields from AI extraction
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
    TAM_source: Optional[str] = None
    SAM: Optional[float] = None
    SAM_source: Optional[str] = None
    SOM: Optional[float] = None
    SOM_source: Optional[str] = None
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
    product_roadmap: Optional[str] = None  # Product development roadmap and milestones
    patent_portfolio: Optional[str] = None  # Patent portfolio assessment and analysis
    executives: Optional[List[dict]] = []
    prior_exit_details: Optional[List[dict]] = []

    founding_year: Optional[int] = None
    funding_rounds: Optional[list] = None
    investors: Optional[list] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    facebook: Optional[str] = None
    revenue_estimate: Optional[float] = None
    revenue_currency: Optional[str] = None
    revenue_source: Optional[str] = None
    size_range: Optional[str] = None
    status: Optional[str] = None
    parent_id: Optional[str] = None
    hq_city: Optional[str] = None
    hq_country_iso2: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    office_locations: Optional[list] = None
    emails: Optional[list] = None
    phones: Optional[list] = None
    linkedin_followers: Optional[int] = None
    x_followers: Optional[int] = None
    competitor_ids: Optional[list] = None
    products: Optional[list] = None
    keywords: Optional[list] = None
    employee_cost_estimate: Optional[float] = None
    app_store_links: Optional[list] = None
    similarweb_monthly_visits: Optional[int] = None
    bounce_rate: Optional[float] = None
    avg_visit_duration_s: Optional[float] = None
    news_mentions: Optional[int] = None
    news_headlines: Optional[list] = None
    news_sentiment: Optional[float] = None

    # New fields for structured data
    tables: List[Table] = []
    figures: List[Figure] = []
    # Visuals and charts for memo
    extracted_image_paths: Optional[List[str]] = []
    market_chart_path: Optional[str] = None
    figures_ocr: Optional[str] = None
    cagr: Optional[float] = None
    cagr_source: Optional[str] = None
    market_growth_rate: Optional[str] = None
    market_growth_rate_source: Optional[str] = None
    gross_margin: Optional[float] = None
    ebitda: Optional[float] = None
    net_income: Optional[float] = None
    arr: Optional[float] = None
    mrr: Optional[float] = None
    cac: Optional[float] = None
    ltv: Optional[float] = None
    payback_period: Optional[str] = None
    revenue_growth_rate: Optional[str] = None
    major_investors: Optional[list[str]] = None
    ownership_breakdown: Optional[list[dict]] = None
    debt: Optional[float] = None
    cash_on_hand: Optional[float] = None
    tables_text: Optional[str] = None
    market_size_sources: Optional[list[str]] = None
    revenue: Optional[float] = None
    gmv: Optional[float] = None
    mrr: Optional[float] = None
    gross_profit: Optional[float] = None
    cagr: Optional[float] = None
    cagr_source: Optional[str] = None
    growth_rate: Optional[float] = None
    growth_rate_source: Optional[str] = None
    financial_growth_rate: Optional[float] = None
    financial_growth_rate_source: Optional[str] = None

    # --- Add missing fields for LLM outputs ---
    financial_summary: Optional[str] = None
    financials_table: Optional[str] = None
    financials_by_year: Optional[dict] = None
    market_summary: Optional[str] = None
    market_reasoning: Optional[str] = None
    
    # --- Technical DD fields ---
    complexity: Optional[str] = None
    security: Optional[str] = None
    implementation: Optional[str] = None
    regulatory: Optional[str] = None
    testing: Optional[str] = None
    product_specifications: Optional[str] = None
    
    # --- Additional fields used in main.py ---
    size: Optional[str] = None
    founded: Optional[str] = None
    followers: Optional[int] = None
    employees_count: Optional[int] = None
    website_traffic: Optional[str] = None
    funding_amount: Optional[str] = None
    funding_source: Optional[str] = None
    market_size_by_year: Optional[dict] = None
    
    # --- Financial analysis fields ---
    web_sources: Optional[list[str]] = None
    web_financial_data: Optional[str] = None
    
    # --- Additional financial fields ---
    total_funding_raised: Optional[float] = None
    funding_rounds_count: Optional[int] = None
    latest_round_type: Optional[str] = None
    latest_round_date: Optional[str] = None
    latest_round_amount: Optional[float] = None
    
    # --- Market sizing fields ---
    TAM_original: Optional[str] = None
    SAM_original: Optional[str] = None
    SOM_original: Optional[str] = None
    market_reasoning: Optional[str] = None
    market_size: Optional[float] = None
    market_size_source: Optional[str] = None
    total_merchants: Optional[float] = None
    total_merchants_source: Optional[str] = None
    global_merchants: Optional[float] = None
    global_merchants_source: Optional[str] = None
    core_geography_merchants: Optional[float] = None
    core_geography_merchants_source: Optional[str] = None
    revenue_per_merchant: Optional[float] = None
    revenue_per_merchant_source: Optional[str] = None
    subscription_pricing: Optional[str] = None
    subscription_pricing_source: Optional[str] = None
    merchants: Optional[float] = None
    merchants_source: Optional[str] = None
    market_definition: Optional[str] = None
    market_definition_source: Optional[str] = None
    geographic_focus: Optional[str] = None
    geographic_focus_source: Optional[str] = None
    market_source: Optional[str] = None
    market_source_source: Optional[str] = None
    
    # --- AI-detected market fields ---
    ai_detected_market_sizes: Optional[dict] = None
    ai_detected_market_sizes_source: Optional[str] = None
    ai_detected_customer_and_user_numbers: Optional[dict] = None
    ai_detected_customer_and_user_numbers_source: Optional[str] = None
    ai_detected_geographic_markets: Optional[dict] = None
    ai_detected_geographic_markets_source: Optional[str] = None
    ai_detected_competitive_positioning: Optional[dict] = None
    ai_detected_competitive_positioning_source: Optional[str] = None
    ai_detected_growth_rates_and_drivers: Optional[dict] = None
    ai_detected_growth_rates_and_drivers_source: Optional[str] = None
    ai_detected_target_market_definitions: Optional[dict] = None
    ai_detected_target_market_definitions_source: Optional[str] = None
    ai_detected_industry_trends_and_drivers: Optional[dict] = None
    ai_detected_industry_trends_and_drivers_source: Optional[str] = None
    ai_detected_market_validation_signals: Optional[dict] = None
    ai_detected_market_validation_signals_source: Optional[str] = None
    ai_detected_pricing_models: Optional[dict] = None
    ai_detected_pricing_models_source: Optional[str] = None
    ai_detected_data_sources: Optional[dict] = None
    ai_detected_data_sources_source: Optional[str] = None
    ai_detected_data_sources_and_research_firms: Optional[dict] = None
    ai_detected_data_sources_and_research_firms_source: Optional[str] = None
    ai_detected_customer_numbers_and_growth: Optional[dict] = None
    ai_detected_customer_numbers_and_growth_source: Optional[str] = None
    
    # --- AI-detected financial fields ---
    ai_detected_revenue_metrics: Optional[dict] = None
    ai_detected_revenue_metrics_source: Optional[str] = None
    ai_detected_profitability_metrics: Optional[dict] = None
    ai_detected_profitability_metrics_source: Optional[str] = None
    ai_detected_growth_metrics: Optional[dict] = None
    ai_detected_growth_metrics_source: Optional[str] = None
    ai_detected_business_model: Optional[dict] = None
    ai_detected_business_model_source: Optional[str] = None
    ai_detected_operational_metrics: Optional[dict] = None
    ai_detected_operational_metrics_source: Optional[str] = None
    ai_detected_efficiency_metrics: Optional[dict] = None
    ai_detected_efficiency_metrics_source: Optional[str] = None
    ai_detected_valuation_metrics: Optional[dict] = None
    ai_detected_valuation_metrics_source: Optional[str] = None
    ai_detected_historical_data: Optional[dict] = None
    ai_detected_historical_data_source: Optional[str] = None
    ai_detected_operating_expenses: Optional[dict] = None
    ai_detected_operating_expenses_source: Optional[str] = None
    
    # --- AI-detected market fields (comprehensive list) ---
    ai_detected_market_size: Optional[dict] = None
    ai_detected_market_size_source: Optional[str] = None
    ai_detected_target_market: Optional[dict] = None
    ai_detected_target_market_source: Optional[str] = None
    
    # --- AI-extracted market data fields (from ai_extract_market_data) ---
    market_size_tam: Optional[str] = None
    market_size_tam_source: Optional[str] = None
    market_size_sam: Optional[str] = None
    market_size_sam_source: Optional[str] = None
    market_size_som: Optional[str] = None
    market_size_som_source: Optional[str] = None
    market_size_market_size: Optional[str] = None
    market_size_market_size_source: Optional[str] = None
    
    # --- Market metrics fields ---
    market_metrics_total_customers: Optional[str] = None
    market_metrics_total_customers_source: Optional[str] = None
    market_metrics_active_customers: Optional[str] = None
    market_metrics_active_customers_source: Optional[str] = None
    market_metrics_target_customers: Optional[str] = None
    market_metrics_target_customers_source: Optional[str] = None
    market_metrics_market_penetration: Optional[str] = None
    market_metrics_market_penetration_source: Optional[str] = None
    market_metrics_revenue_per_customer: Optional[str] = None
    market_metrics_revenue_per_customer_source: Optional[str] = None
    market_metrics_customer_growth_rate: Optional[str] = None
    market_metrics_customer_growth_rate_source: Optional[str] = None
    
    # --- Geographic data fields ---
    geographic_data_global_market: Optional[str] = None
    geographic_data_global_market_source: Optional[str] = None
    geographic_data_core_geographies: Optional[str] = None
    geographic_data_core_geographies_source: Optional[str] = None
    geographic_data_international_presence: Optional[str] = None
    geographic_data_international_presence_source: Optional[str] = None
    geographic_data_regional_breakdown: Optional[str] = None
    geographic_data_regional_breakdown_source: Optional[str] = None
    
    # --- Market definition fields ---
    market_definition_target_segment: Optional[str] = None
    market_definition_target_segment_source: Optional[str] = None
    market_definition_customer_type: Optional[str] = None
    market_definition_customer_type_source: Optional[str] = None
    market_definition_market_criteria: Optional[str] = None
    market_definition_market_criteria_source: Optional[str] = None
    
    # --- Growth metrics fields ---
    growth_metrics_cagr: Optional[str] = None
    growth_metrics_cagr_source: Optional[str] = None
    growth_metrics_growth_rate: Optional[str] = None
    growth_metrics_growth_rate_source: Optional[str] = None
    growth_metrics_growth_drivers: Optional[str] = None
    growth_metrics_growth_drivers_source: Optional[str] = None
    
    # --- Competitive data fields ---
    competitive_data_market_share: Optional[str] = None
    competitive_data_market_share_source: Optional[str] = None
    competitive_data_competitors: Optional[str] = None
    competitive_data_competitors_source: Optional[str] = None
    competitive_data_competitive_advantage: Optional[str] = None
    competitive_data_competitive_advantage_source: Optional[str] = None
    
    # --- Source attribution fields ---
    source_attribution_data_source: Optional[str] = None
    source_attribution_data_source_source: Optional[str] = None
    source_attribution_research_firm: Optional[str] = None
    source_attribution_research_firm_source: Optional[str] = None
    source_attribution_date: Optional[str] = None
    source_attribution_date_source: Optional[str] = None
    
    # --- Technical data fields ---
    energy_density_wh_kg: Optional[float] = None
    cycle_life_count: Optional[int] = None
    energy_density_source: Optional[str] = None
    cycle_life_source: Optional[str] = None
    
    # --- Additional technical specifications ---
    charging_speed_miles: Optional[int] = None
    charging_speed_minutes: Optional[int] = None
    low_temp_performance: Optional[str] = None
    cell_capacity: Optional[int] = None
    cell_dimensions: Optional[str] = None
    charging_power: Optional[int] = None
    power_performance: Optional[str] = None
    phds: Optional[int] = None
    professionals: Optional[int] = None
    
    # --- Enhanced technical specifications ---
    volumetric_energy_density: Optional[int] = None
    granted_patents: Optional[int] = None
    pending_patents: Optional[int] = None
    patent_details: Optional[str] = None
    oem_partners: Optional[int] = None
    safety_certifications: Optional[str] = None
    employees_count: Optional[int] = None
    
    # --- Roadmap fields ---
    roadmap_100in_speed: Optional[int] = None
    roadmap_100in_year: Optional[int] = None
    roadmap_production_year: Optional[int] = None
    roadmap_technologies: Optional[list[str]] = None
    
    # --- Financial data fields ---
    valuation_source: Optional[str] = None
    
    # --- Founder profiling fields ---
    founder_linkedin_data: Optional[dict] = None
    founder_linkedin_formatted: Optional[str] = None
    
    # --- Document processing fields ---
    figures_ocr: Optional[str] = None
    tables_text: Optional[str] = None
    
    # --- Comprehensive extracted data context for agents ---
    extracted_data_context: Optional[str] = None
    
    # --- Structured data from enhanced extraction ---
    structured_data: Optional[dict] = None
    
    # --- CoreSignal enhanced fields ---
    founded_year: Optional[str] = None
    estimated_revenue_range: Optional[str] = None
    last_funding_round_name: Optional[str] = None
    last_funding_round_amount_raised: Optional[str] = None
    last_funding_round_announced_date: Optional[str] = None
    news_counts: Optional[str] = None
    news_features: Optional[str] = None
    technographics: Optional[str] = None
    ai_detected_brand_positioning_and_recognition: Optional[dict] = None
    ai_detected_brand_positioning_and_recognition_source: Optional[str] = None
    market_size_tam: Optional[str] = None
    market_size_tam_source: Optional[str] = None
    ai_detected_revenue_per_customer: Optional[dict] = None
    ai_detected_revenue_per_customer_source: Optional[str] = None
    ai_detected_customer_and_user_data: Optional[dict] = None
    ai_detected_customer_and_user_data_source: Optional[str] = None
    ai_detected_growth_and_trends: Optional[dict] = None
    ai_detected_growth_and_trends_source: Optional[str] = None
    ai_detected_revenue_per_customer_metrics: Optional[dict] = None
    ai_detected_revenue_per_customer_metrics_source: Optional[str] = None
    ai_detected_growth_and_market_penetration: Optional[dict] = None
    ai_detected_growth_and_market_penetration_source: Optional[str] = None