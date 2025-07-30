import os
from pathlib import Path
from typing import Dict, List, Any

class Config:
    """Centralized configuration for the VC Analysis System - Generic for any startup sector"""
    
    # Directories
    CACHE_DIR = "extraction_cache"  # Keep this fixed - it's not a hardcoding problem
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "out")
    TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "template.docx")
    
    # Document formatting
    DEFAULT_FONT = "Times New Roman"  # Standard business document font
    DEFAULT_FONT_SIZE = int(os.getenv("DEFAULT_FONT_SIZE", "12"))
    HYPERLINK_COLOR = os.getenv("HYPERLINK_COLOR", "0563C1")  # Blue
    
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
    
    # Market sizing defaults
    DEFAULT_SOM_RATIO = float(os.getenv("DEFAULT_SOM_RATIO", "0.1"))
    
    # Generic technical terms that work across all sectors
    TECHNICAL_TERMS = [
        'platform', 'software', 'hardware', 'device', 'app', 'service',
        'technology', 'solution', 'system', 'tool', 'product', 'service',
        'algorithm', 'model', 'framework', 'protocol', 'standard',
        'component', 'module', 'interface', 'api', 'database',
        'network', 'cloud', 'mobile', 'web', 'desktop', 'embedded',
        'analytics', 'automation', 'optimization', 'integration',
        'security', 'compliance', 'scalability', 'performance',
        'reliability', 'efficiency', 'accuracy', 'speed', 'capacity',
        'battery', 'energy', 'storage', 'charging', 'power',
        'drug', 'therapy', 'medical', 'biotech', 'pharma',
        'payment', 'banking', 'financial', 'fintech', 'transaction',
        'ai', 'machine learning', 'artificial intelligence', 'neural',
        'consumer', 'retail', 'ecommerce', 'marketplace', 'user'
    ]
    
    # Generic metric patterns that work across all sectors
    METRIC_PATTERNS = {
        'performance': ['performance', 'speed', 'efficiency', 'throughput', 'capacity'],
        'quality': ['quality', 'accuracy', 'precision', 'reliability', 'durability'],
        'scale': ['scale', 'size', 'volume', 'capacity', 'throughput'],
        'cost': ['cost', 'price', 'value', 'efficiency', 'economy'],
        'time': ['time', 'duration', 'speed', 'latency', 'response'],
        'security': ['security', 'safety', 'protection', 'compliance'],
        'user': ['user', 'customer', 'adoption', 'engagement', 'satisfaction']
    }
    
    # Generic market research sources that work for any sector
    GENERIC_MARKET_SOURCES = [
        os.getenv("MARKET_SOURCE_1", "https://www.grandviewresearch.com/"),
        os.getenv("MARKET_SOURCE_2", "https://www.marketsandmarkets.com/"),
        os.getenv("MARKET_SOURCE_3", "https://www.alliedmarketresearch.com/"),
        os.getenv("MARKET_SOURCE_4", "https://www.researchandmarkets.com/"),
        os.getenv("MARKET_SOURCE_5", "https://www.ibisworld.com/"),
        os.getenv("MARKET_SOURCE_6", "https://www.statista.com/")
    ]
    
    # Generic competitive intelligence sources
    COMPETITIVE_SOURCES = [
        os.getenv("COMPETITIVE_SOURCE_1", "https://www.crunchbase.com/"),
        os.getenv("COMPETITIVE_SOURCE_2", "https://www.linkedin.com/"),
        os.getenv("COMPETITIVE_SOURCE_3", "https://www.pitchbook.com/"),
        os.getenv("COMPETITIVE_SOURCE_4", "https://www.cbinsights.com/")
    ]
    
    @classmethod
    def get_technical_terms(cls) -> List[str]:
        """Get all available technical terms for any sector"""
        return cls.TECHNICAL_TERMS
    
    @classmethod
    def get_metric_patterns(cls) -> Dict[str, List[str]]:
        """Get metric patterns that work across all sectors"""
        return cls.METRIC_PATTERNS
    
    @classmethod
    def get_market_sources(cls) -> List[str]:
        """Get generic market research sources for any sector"""
        return cls.GENERIC_MARKET_SOURCES
    
    @classmethod
    def get_competitive_sources(cls) -> List[str]:
        """Get generic competitive intelligence sources for any sector"""
        return cls.COMPETITIVE_SOURCES
    
    @classmethod
    def detect_sector_from_data(cls, profile_data: Dict[str, Any]) -> str:
        """Dynamically detect sector from actual profile data"""
        # Check explicit sector field first
        sector = profile_data.get('sector', '').lower()
        if sector:
            return sector
        
        # Check product description for technical terms
        description = profile_data.get('product_description', '').lower()
        if description:
            for term in cls.TECHNICAL_TERMS:
                if term in description:
                    return term
        
        # Check company name for hints
        company_name = profile_data.get('name', '').lower()
        if company_name:
            for term in cls.TECHNICAL_TERMS:
                if term in company_name:
                    return term
        
        # Default to generic
        return 'technology'
    
    @classmethod
    def get_relevant_metrics(cls, profile_data: Dict[str, Any]) -> List[str]:
        """Dynamically find relevant metrics from profile data"""
        metrics = []
        
        for key, value in profile_data.items():
            if value and isinstance(value, (str, int, float)):
                key_lower = key.lower()
                for pattern_name, keywords in cls.METRIC_PATTERNS.items():
                    if any(keyword in key_lower for keyword in keywords):
                        metrics.append(f"{key.replace('_', ' ')} of {value}")
                        break
        
        return metrics 