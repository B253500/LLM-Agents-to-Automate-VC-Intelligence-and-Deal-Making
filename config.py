import os
from pathlib import Path
from typing import Dict, List, Any

# Configuration settings for the VC memo generation system

# LLM Configuration
DEFAULT_MODEL = "gpt-4o"
FALLBACK_MODEL = "gpt-4o"
TEMPERATURE = 0.2

# Token tracking and evaluation
ENABLE_TOKEN_TRACKING = True
ENABLE_EVALUATION_METRICS = True

# External enrichment sources
ENABLE_PROXYCURL_ENRICHMENT = False  # Disabled due to 404 errors
ENABLE_PERPLEXITY_ENRICHMENT = True  # Enable Perplexity web search enrichment

# Output settings
OUTPUT_DIR = "out"
CACHE_DIR = "extraction_cache"

# Document processing
MAX_TEXT_LENGTH = 8000  # Maximum characters for text processing
MAX_TOKENS_PER_REQUEST = 4000  # Maximum tokens per LLM request

# Evaluation settings
EVALUATION_OUTPUT_DIR = "evaluation_results"
EVALUATION_TEMPLATES_DIR = "evaluation_metrics/templates"

# API Keys (set in environment variables)
REQUIRED_API_KEYS = [
    "OPENAI_API_KEY",
    "PERPLEXITY_API_KEY",  # Optional for web search
    "PROXYCURL_API_KEY",   # Optional for LinkedIn enrichment
    "EXA_API_KEY"          # Optional for semantic search
]

class Config:
    """Generic configuration for the VC Analysis System - Works for any startup sector"""
    
    # === ESSENTIAL SYSTEM CONFIGURATION ===
    # Directories
    CACHE_DIR = "extraction_cache"
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "out")
    TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "template.docx")
    
    # Document formatting
    DEFAULT_FONT = "Times New Roman"
    DEFAULT_FONT_SIZE = int(os.getenv("DEFAULT_FONT_SIZE", "12"))
    HYPERLINK_COLOR = os.getenv("HYPERLINK_COLOR", "0563C1")
    
    # LLM Configuration
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
    DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.2"))
    
    # API Services
    MERMAID_SERVICES = [
        ("https://kroki.io/mermaid/png", "Kroki.io"),
        ("https://mermaid.ink/img/", "Mermaid.ink"),
    ]
    
    # Financial validation thresholds
    MIN_REVENUE_THRESHOLD = float(os.getenv("MIN_REVENUE_THRESHOLD", "1000"))
    MIN_FUNDING_THRESHOLD = float(os.getenv("MIN_FUNDING_THRESHOLD", "1000"))
    DEFAULT_SOM_RATIO = float(os.getenv("DEFAULT_SOM_RATIO", "0.1"))
    
    # === GENERIC UTILITY METHODS ===
    @classmethod
    def get_market_sources(cls) -> List[str]:
        """Get generic market research sources - can be overridden per sector"""
        return [
            os.getenv("MARKET_SOURCE_1", "https://www.grandviewresearch.com/"),
            os.getenv("MARKET_SOURCE_2", "https://www.marketsandmarkets.com/"),
            os.getenv("MARKET_SOURCE_3", "https://www.statista.com/"),
            os.getenv("MARKET_SOURCE_4", "https://www.ibisworld.com/"),
        ]
    
    @classmethod
    def get_competitive_sources(cls) -> List[str]:
        """Get generic competitive intelligence sources"""
        return [
            os.getenv("COMPETITIVE_SOURCE_1", "https://www.crunchbase.com/"),
            os.getenv("COMPETITIVE_SOURCE_2", "https://www.linkedin.com/"),
            os.getenv("COMPETITIVE_SOURCE_3", "https://www.pitchbook.com/"),
        ]
    
    @classmethod
    def detect_sector_from_data(cls, profile_data: Dict[str, Any]) -> str:
        """Generic sector detection - uses AI instead of hardcoded terms"""
        # Check explicit sector field first
        sector = profile_data.get('sector', '')
        if sector and isinstance(sector, str) and sector.lower() not in ['unknown', 'n/a', '']:
            return sector.lower()
        
        # For now, return generic - let AI chains handle sector detection
        # This removes the problematic hardcoded technical terms
        return 'technology'
    
    @classmethod
    def get_relevant_metrics(cls, profile_data: Dict[str, Any]) -> List[str]:
        """Generic metric detection - let AI determine relevant metrics"""
        # Return empty list - let AI chains determine relevant metrics
        # This removes hardcoded metric patterns
        return []
    
    @classmethod
    def get_sector_specific_config(cls, sector: str) -> Dict[str, Any]:
        """Get sector-specific configuration if needed"""
        # This can be extended later for sector-specific settings
        return {
            'market_sources': cls.get_market_sources(),
            'competitive_sources': cls.get_competitive_sources(),
        } 