import os
from pathlib import Path
from typing import Dict, List, Any

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