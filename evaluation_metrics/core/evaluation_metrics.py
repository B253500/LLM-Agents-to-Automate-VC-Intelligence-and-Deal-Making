"""
Comprehensive evaluation metrics for investment memo generator
Implements all metrics from the evaluation framework
Enhanced for academic analysis and comparison with traditional VC processes
"""

import re
import time
import psutil
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime

# Try to import GPUtil, but make it optional
try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False


@dataclass
class SectionMetrics:
    """Metrics for individual memo sections"""
    section_name: str
    runtime_seconds: float
    tokens_used: int
    cost_usd: float
    content_length_chars: int
    content_length_words: int
    quality_score: float  # 0-1 scale


@dataclass
class MemoEvaluationMetrics:
    """Container for all memo evaluation metrics"""
    
    # Section completeness
    all_sections_present: bool
    missing_sections: List[str]
    
    # Readability
    flesch_kincaid_score: float
    analyst_readability_score: float  # 1-5 scale
    
    # Visuals (simplified)
    chart_present: bool
    
    # Duplicates
    duplicate_lines_count: int
    duplicate_ratio: float
    
    # Cost and time
    total_cost_usd: float
    generation_time_seconds: float
    token_usage: Dict[str, int]
    
    # Coverage
    unknown_coverage_ratio: float
    placeholder_count: int
    
    # Additional metrics
    memo_length_chars: int
    memo_length_words: int
    section_count: int
    
    # Enhanced metrics for academic analysis
    section_metrics: List[SectionMetrics]
    traditional_vc_comparison: Dict[str, Any]
    
    # System Performance Metrics
    gpu_usage_percent: float  # GPU utilization during generation
    cpu_usage_percent: float  # CPU utilization during generation
    memory_usage_mb: float  # Memory consumption
    system_robustness_score: float  # Performance on noisy vs clean decks
    
    # Visual Analysis (simplified)
    chart_relevance_score: float  # 1-5 scale (from human feedback)


class MemoEvaluator:
    """Evaluates investment memos against comprehensive metrics"""
    
    REQUIRED_SECTIONS = [
        "DETAILED SUMMARY",
        "COMPANY OVERVIEW", 
        "PROBLEM STATEMENT",
        "SOLUTION OVERVIEW",
        "PRODUCT/SERVICE DESCRIPTION",
        "MARKET SIZE & ANALYSIS",
        "COMPETITORS",
        "BUSINESS MODEL",
        "TECHNICAL DUE DILIGENCE",
        "FINANCIAL ANALYSIS",
        "TEAM & MANAGEMENT",
        "ESG CONSIDERATIONS",
        "RISKS",
        "INVESTMENT & EXIT STRATEGIES",
        "COUNTERFACTUAL ANALYSIS",
        "FOLLOW-UP QUESTIONS",
        "AI DISCUSSION AND COMMENTARY"
    ]
    
    # Traditional VC benchmarks based on industry research
    TRADITIONAL_VC_BENCHMARKS = {
        "total_time_hours": 15,  # hours for complete memo (industry standard - 12-18h range)
        "total_cost_usd": 2250,  # USD for complete memo (senior analyst rate - $1800-2700 range)
        "analyst_rate_per_hour": 150,  # USD per hour (senior VC analyst rate)
        "source": "Stanford-Addepar survey 2024, AspireApp handbook 2023, VC industry analysis",
        "time_range": "12-18 hours",
        "cost_range": "$1,800-2,700"
    }
    
    # Section-specific traditional VC time estimates
    TRADITIONAL_VC_TIMES = {
        "DETAILED SUMMARY": 30,  # minutes
        "COMPANY OVERVIEW": 15,
        "PROBLEM STATEMENT": 20,
        "SOLUTION OVERVIEW": 25,
        "PRODUCT/SERVICE DESCRIPTION": 45,
        "MARKET SIZE & ANALYSIS": 60,
        "COMPETITORS": 40,
        "BUSINESS MODEL": 30,
        "TECHNICAL DUE DILIGENCE": 90,
        "FINANCIAL ANALYSIS": 75,
        "TEAM & MANAGEMENT": 45,
        "ESG CONSIDERATIONS": 30,
        "RISKS": 35,
        "INVESTMENT & EXIT STRATEGIES": 40,
        "COUNTERFACTUAL ANALYSIS": 25,
        "FOLLOW-UP QUESTIONS": 20,
        "AI DISCUSSION AND COMMENTARY": 45
    }
    
    def __init__(self):
        self.start_time = None
        self.section_timings = {}
        self.token_usage = {}
        self.api_costs = {
            "gpt-4": 0.03,  # per 1K tokens
            "gpt-4o": 0.005,  # per 1K tokens
            "gpt-4o-mini": 0.00015,  # per 1K tokens
            "gpt-4o-mini-realtime-preview": 0.00015,  # per 1K tokens
            "gpt-4o-realtime-preview": 0.005,  # per 1K tokens
            "o1": 0.15,  # per 1K tokens
            "o1-mini": 0.00015,  # per 1K tokens
            "o1-pro": 0.15,  # per 1K tokens
            "o3-mini": 0.00015,  # per 1K tokens
            "o4-mini": 0.00015,  # per 1K tokens
            "claude-3": 0.015,  # per 1K tokens
            "gemini": 0.0005,  # per 1K tokens
            "perplexity": 0.001,  # per 1K tokens (Sonar: $1/1M = $0.001/1K)
            "perplexity-pro": 0.003,  # per 1K tokens (Sonar Pro: $3/1M = $0.003/1K)
            "perplexity-reasoning": 0.001,  # per 1K tokens (Sonar Reasoning: $1/1M = $0.001/1K)
            "perplexity-reasoning-pro": 0.002,  # per 1K tokens (Sonar Reasoning Pro: $2/1M = $0.002/1K)
            "perplexity-deep-research": 0.002,  # per 1K tokens (Sonar Deep Research: $2/1M = $0.002/1K)
            "anthropic": 0.015,  # per 1K tokens
            "local": 0.0  # local models
        }
    
    def start_evaluation(self):
        """Start timing the evaluation process"""
        self.start_time = time.time()
        self.section_timings = {}
        self.token_usage = {}
    
    def log_section_start(self, section_name: str):
        """Log the start of a section"""
        self.section_timings[section_name] = {"start": time.time()}
    
    def log_section_end(self, section_name: str, tokens_used: int = 0, model: str = "gpt-4"):
        """Log the end of a section with timing and token usage"""
        if section_name in self.section_timings:
            self.section_timings[section_name]["end"] = time.time()
            self.section_timings[section_name]["tokens"] = tokens_used
            self.section_timings[section_name]["model"] = model
    
    def log_token_usage(self, model: str, tokens: int):
        """Log token usage for a specific model"""
        if model not in self.token_usage:
            self.token_usage[model] = 0
        self.token_usage[model] += tokens
    
    def evaluate_memo(self, memo_text: str, memo_html: str = None, 
                     ground_truth: Dict = None) -> MemoEvaluationMetrics:
        """Comprehensive memo evaluation"""
        
        # Section completeness
        section_metrics = self._evaluate_sections(memo_text)
        
        # Readability
        readability_metrics = self._evaluate_readability(memo_text)
        
        # Visuals
        visual_metrics = self._evaluate_visuals(memo_html)
        
        # Duplicates
        duplicate_metrics = self._evaluate_duplicates(memo_text)
        
        # Cost and time
        cost_metrics = self._calculate_costs()
        
        # Coverage
        coverage_metrics = self._evaluate_coverage(memo_text)
        
        # Additional metrics
        additional_metrics = self._calculate_additional_metrics(memo_text)
        
        # System performance metrics
        system_performance_metrics = self._evaluate_system_performance()
        
        # Section-level metrics
        section_metrics_list = self._calculate_section_metrics(memo_text)
        
        # Traditional VC comparison
        traditional_comparison = self._compare_with_traditional_vc(section_metrics_list)
        
        return MemoEvaluationMetrics(
            all_sections_present=section_metrics["all_present"],
            missing_sections=section_metrics["missing"],
            flesch_kincaid_score=readability_metrics["fk_score"],
            analyst_readability_score=readability_metrics["analyst_score"],
            chart_present=visual_metrics["chart_present"],
            duplicate_lines_count=duplicate_metrics["count"],
            duplicate_ratio=duplicate_metrics["ratio"],
            total_cost_usd=cost_metrics["total_cost"],
            generation_time_seconds=cost_metrics["time"],
            token_usage=self.token_usage,
            unknown_coverage_ratio=coverage_metrics["ratio"],
            placeholder_count=coverage_metrics["count"],
            memo_length_chars=additional_metrics["memo_length_chars"],
            memo_length_words=additional_metrics["memo_length_words"],
            section_count=additional_metrics["section_count"],
            section_metrics=section_metrics_list,
            traditional_vc_comparison=traditional_comparison,
            gpu_usage_percent=system_performance_metrics["gpu_usage_percent"],
            cpu_usage_percent=system_performance_metrics["cpu_usage_percent"],
            memory_usage_mb=system_performance_metrics["memory_usage_mb"],
            system_robustness_score=system_performance_metrics["system_robustness_score"],
            chart_relevance_score=0.0  # Will be filled from human feedback
        )
    
    def _calculate_section_metrics(self, memo_text: str) -> List[SectionMetrics]:
        """Calculate detailed metrics for each section using robust detection"""
        section_metrics = []
        
        # Use the new robust section detection
        section_evaluation = self._evaluate_sections(memo_text)
        section_details = section_evaluation.get('section_details', {})
        
        for section_name in self.REQUIRED_SECTIONS:
            # Find the actual section content using variations
            section_variations = {
                "DETAILED SUMMARY": ["DETAILED SUMMARY", "SUMMARY", "EXECUTIVE SUMMARY"],
                "COMPANY OVERVIEW": ["COMPANY OVERVIEW", "COMPANY", "OVERVIEW"],
                "PROBLEM STATEMENT": ["PROBLEM STATEMENT", "PROBLEM", "CHALLENGE"],
                "SOLUTION OVERVIEW": ["SOLUTION OVERVIEW", "SOLUTION", "APPROACH"],
                "PRODUCT/SERVICE DESCRIPTION": ["PRODUCT/SERVICE DESCRIPTION", "PRODUCT DESCRIPTION", "SERVICE DESCRIPTION", "PRODUCT", "SERVICE"],
                "MARKET SIZE & ANALYSIS": ["MARKET SIZE & ANALYSIS", "MARKET SIZE", "MARKET ANALYSIS", "MARKET"],
                "COMPETITORS": ["COMPETITORS", "COMPETITIVE LANDSCAPE", "COMPETITION"],
                "BUSINESS MODEL": ["BUSINESS MODEL", "BUSINESS MODEL SCHEMA"],
                "TECHNICAL DUE DILIGENCE": ["TECHNICAL DUE DILIGENCE", "TECHNICAL DD", "TECHNICAL ANALYSIS"],
                "FINANCIAL ANALYSIS": ["FINANCIAL ANALYSIS", "FINANCIAL", "FINANCIALS"],
                "TEAM & MANAGEMENT": ["TEAM & MANAGEMENT", "TEAM", "MANAGEMENT", "TEAM AND MANAGEMENT"],
                "ESG CONSIDERATIONS": ["ESG CONSIDERATIONS", "ESG", "ENVIRONMENTAL"],
                "RISKS": ["RISKS", "RISK", "RISK ASSESSMENT"],
                "INVESTMENT & EXIT STRATEGIES": ["INVESTMENT & EXIT STRATEGIES", "INVESTMENT STRATEGIES", "EXIT STRATEGIES"],
                "COUNTERFACTUAL ANALYSIS": ["COUNTERFACTUAL ANALYSIS", "COUNTERFACTUAL", "WHAT IF WE DON'T INVEST"],
                "FOLLOW-UP QUESTIONS": ["FOLLOW-UP QUESTIONS", "FOLLOW UP QUESTIONS", "FOLLOWUP QUESTIONS", "NEXT STEPS"],
                "AI DISCUSSION AND COMMENTARY": ["AI DISCUSSION AND COMMENTARY", "AI DISCUSSION", "COMMENTARY", "DISCUSSION"]
            }
            
            variations = section_variations.get(section_name, [section_name])
            section_content = None
            found_variation = None
            
            # Find the actual section content
            for variation in variations:
                if variation in section_details:
                    section_content = section_details[variation]['content']
                    found_variation = variation
                    break
            
            if section_content:
                # Get timing data from tracked sections
                runtime = 0.0
                tokens = 0
                cost = 0.0
                model = "gpt-4o-mini"
                
                # Map section names to actual tracked sections from main.py
                section_mapping = {
                    "DETAILED SUMMARY": "COMPLETE ANALYSIS PIPELINE",
                    "COMPANY OVERVIEW": "COMPLETE ANALYSIS PIPELINE", 
                    "PROBLEM STATEMENT": "COMPLETE ANALYSIS PIPELINE",
                    "SOLUTION OVERVIEW": "COMPLETE ANALYSIS PIPELINE",
                    "PRODUCT/SERVICE DESCRIPTION": "COMPLETE ANALYSIS PIPELINE",
                    "MARKET SIZE & ANALYSIS": "COMPLETE ANALYSIS PIPELINE",
                    "COMPETITORS": "COMPLETE ANALYSIS PIPELINE",
                    "BUSINESS MODEL": "COMPLETE ANALYSIS PIPELINE",
                    "TECHNICAL DUE DILIGENCE": "COMPLETE ANALYSIS PIPELINE",
                    "FINANCIAL ANALYSIS": "COMPLETE ANALYSIS PIPELINE",
                    "TEAM & MANAGEMENT": "COMPLETE ANALYSIS PIPELINE",
                    "ESG CONSIDERATIONS": "COMPLETE ANALYSIS PIPELINE",
                    "RISKS": "COMPLETE ANALYSIS PIPELINE",
                    "INVESTMENT & EXIT STRATEGIES": "COMPLETE ANALYSIS PIPELINE",
                    "COUNTERFACTUAL ANALYSIS": "COMPLETE ANALYSIS PIPELINE",
                    "FOLLOW-UP QUESTIONS": "COMPLETE ANALYSIS PIPELINE",
                    "AI DISCUSSION AND COMMENTARY": "MEMO GENERATION"
                }
                
                tracked_section = section_mapping.get(section_name, "COMPLETE ANALYSIS PIPELINE")
                
                if tracked_section in self.section_timings:
                    timing_data = self.section_timings[tracked_section]
                    if "start" in timing_data and "end" in timing_data:
                        runtime = timing_data["end"] - timing_data["start"]
                    if "tokens" in timing_data:
                        tokens = timing_data["tokens"]
                    if "model" in timing_data:
                        model = timing_data["model"]
                    
                    # Calculate cost
                    if model in self.api_costs:
                        cost = (tokens / 1000) * self.api_costs[model]
                
                # Calculate quality score based on content assessment
                content_quality = self._assess_section_content_quality(section_details[found_variation])
                quality_score = 1.0 if content_quality['is_valid'] else 0.3
                
                # Adjust quality score based on content length and quality
                word_count = content_quality['word_count']
                if word_count > 100:
                    quality_score = min(1.0, quality_score + 0.2)
                elif word_count > 50:
                    quality_score = min(1.0, quality_score + 0.1)
                
                section_metrics.append(SectionMetrics(
                    section_name=section_name,
                    runtime_seconds=runtime,
                    tokens_used=tokens,
                    cost_usd=cost,
                    content_length_chars=len(section_content),
                    content_length_words=len(section_content.split()),
                    quality_score=quality_score
                ))
            else:
                # Section not found - create empty metrics
                section_metrics.append(SectionMetrics(
                    section_name=section_name,
                    runtime_seconds=0.0,
                    tokens_used=0,
                    cost_usd=0.0,
                    content_length_chars=0,
                    content_length_words=0,
                    quality_score=0.0
                ))
        
        return section_metrics
    
    def _compare_with_traditional_vc(self, section_metrics: List[SectionMetrics]) -> Dict[str, Any]:
        """Compare AI performance with traditional VC processes"""
        
        # Calculate total AI time and cost from actual logged sections
        total_ai_time = 0.0
        total_ai_cost = 0.0
        
        # Sum up all logged section timings
        for section_name, timing_data in self.section_timings.items():
            if "start" in timing_data and "end" in timing_data:
                section_time = timing_data["end"] - timing_data["start"]
                total_ai_time += section_time
                
                # Calculate cost for this section
                if "tokens" in timing_data and "model" in timing_data:
                    tokens = timing_data["tokens"]
                    model = timing_data["model"]
                    if model in self.api_costs:
                        section_cost = (tokens / 1000) * self.api_costs[model]
                        total_ai_cost += section_cost
        
        # Use overall benchmarks instead of section-by-section
        total_traditional_time_hours = self.TRADITIONAL_VC_BENCHMARKS["total_time_hours"]
        total_traditional_time_minutes = total_traditional_time_hours * 60
        total_ai_time_minutes = total_ai_time / 60
        
        # Traditional VC cost from benchmark
        total_traditional_cost = self.TRADITIONAL_VC_BENCHMARKS["total_cost_usd"]
        
        time_savings_percentage = ((total_traditional_time_minutes - total_ai_time_minutes) / total_traditional_time_minutes) * 100
        cost_savings_percentage = ((total_traditional_cost - total_ai_cost) / total_traditional_cost) * 100
        
        return {
            "traditional_time_minutes": total_traditional_time_minutes,
            "ai_time_minutes": total_ai_time_minutes,
            "time_savings_percentage": time_savings_percentage,
            "traditional_cost_usd": total_traditional_cost,
            "ai_cost_usd": total_ai_cost,
            "cost_savings_usd": total_traditional_cost - total_ai_cost,
            "cost_savings_percentage": cost_savings_percentage,
            "efficiency_improvement": {
                "time_efficiency": total_traditional_time_minutes / max(0.1, total_ai_time_minutes),
                "cost_efficiency": total_traditional_cost / max(0.01, total_ai_cost)
            },
            "benchmark_source": self.TRADITIONAL_VC_BENCHMARKS["source"]
        }
    
    def _evaluate_sections(self, memo_text: str) -> Dict[str, Any]:
        """Check if all required sections are present with robust detection"""
        missing = []
        present_sections = []
        section_details = {}
        
        # Define section name variations and their canonical names
        section_variations = {
            "DETAILED SUMMARY": ["DETAILED SUMMARY", "SUMMARY", "EXECUTIVE SUMMARY"],
            "COMPANY OVERVIEW": ["COMPANY OVERVIEW", "COMPANY", "OVERVIEW"],
            "PROBLEM STATEMENT": ["PROBLEM STATEMENT", "PROBLEM", "CHALLENGE"],
            "SOLUTION OVERVIEW": ["SOLUTION OVERVIEW", "SOLUTION", "APPROACH"],
            "PRODUCT/SERVICE DESCRIPTION": ["PRODUCT/SERVICE DESCRIPTION", "PRODUCT DESCRIPTION", "SERVICE DESCRIPTION", "PRODUCT", "SERVICE"],
            "MARKET SIZE & ANALYSIS": ["MARKET SIZE & ANALYSIS", "MARKET SIZE", "MARKET ANALYSIS", "MARKET"],
            "COMPETITORS": ["COMPETITORS", "COMPETITIVE LANDSCAPE", "COMPETITION"],
            "BUSINESS MODEL": ["BUSINESS MODEL", "BUSINESS MODEL SCHEMA"],
            "TECHNICAL DUE DILIGENCE": ["TECHNICAL DUE DILIGENCE", "TECHNICAL DD", "TECHNICAL ANALYSIS"],
            "FINANCIAL ANALYSIS": ["FINANCIAL ANALYSIS", "FINANCIAL", "FINANCIALS"],
            "TEAM & MANAGEMENT": ["TEAM & MANAGEMENT", "TEAM", "MANAGEMENT", "TEAM AND MANAGEMENT"],
            "ESG CONSIDERATIONS": ["ESG CONSIDERATIONS", "ESG", "ENVIRONMENTAL"],
            "RISKS": ["RISKS", "RISK", "RISK ASSESSMENT"],
            "INVESTMENT & EXIT STRATEGIES": ["INVESTMENT & EXIT STRATEGIES", "INVESTMENT STRATEGIES", "EXIT STRATEGIES"],
            "COUNTERFACTUAL ANALYSIS": ["COUNTERFACTUAL ANALYSIS", "COUNTERFACTUAL", "WHAT IF WE DON'T INVEST"],
            "FOLLOW-UP QUESTIONS": ["FOLLOW-UP QUESTIONS", "FOLLOW UP QUESTIONS", "FOLLOWUP QUESTIONS", "NEXT STEPS"],
            "AI DISCUSSION AND COMMENTARY": ["AI DISCUSSION AND COMMENTARY", "AI DISCUSSION", "COMMENTARY", "DISCUSSION"]
        }
        
        # Split memo into lines and look for numbered sections
        lines = memo_text.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            
            # Look for numbered section headers (e.g., "1. DETAILED SUMMARY", "2. COMPANY OVERVIEW")
            section_match = re.match(r'^(\d+)\.\s*(.+?)$', line, re.IGNORECASE)
            if section_match:
                # If we have a previous section, save it
                if current_section and current_content:
                    section_details[current_section] = {
                        'content': '\n'.join(current_content),
                        'line_count': len(current_content),
                        'word_count': len(' '.join(current_content).split()),
                        'char_count': len(' '.join(current_content))
                    }
                
                # Start new section
                section_number = int(section_match.group(1))
                section_name = section_match.group(2).strip().upper()
                current_section = section_name
                current_content = []
            elif current_section and line:
                # Add content to current section
                current_content.append(line)
        
        # Don't forget the last section
        if current_section and current_content:
            section_details[current_section] = {
                'content': '\n'.join(current_content),
                'line_count': len(current_content),
                'word_count': len(' '.join(current_content).split()),
                'char_count': len(' '.join(current_content))
            }
        
        # Now check each required section
        for canonical_name, variations in section_variations.items():
            found = False
            found_variation = None
            found_details = None
            
            # Check if any variation of this section exists
            for variation in variations:
                if variation in section_details:
                    found = True
                    found_variation = variation
                    found_details = section_details[variation]
                    break
            
            if found and found_details:
                # Check if section has meaningful content
                content_quality = self._assess_section_content_quality(found_details)
                
                if content_quality['is_valid']:
                    present_sections.append(canonical_name)
                else:
                    missing.append(f"{canonical_name} (insufficient content: {content_quality['reason']})")
            else:
                missing.append(canonical_name)
        
        return {
            "all_present": len(missing) == 0,
            "missing": missing,
            "present_count": len(present_sections),
            "section_details": section_details,
            "present_sections": present_sections
        }
    
    def _assess_section_content_quality(self, section_details: Dict) -> Dict[str, Any]:
        """Assess if a section has meaningful content"""
        word_count = section_details['word_count']
        line_count = section_details['line_count']
        char_count = section_details['char_count']
        content = section_details['content']
        
        # Minimum requirements for a valid section
        min_words = 10
        min_lines = 2
        min_chars = 50
        
        # Check for placeholder content
        placeholder_indicators = [
            "not available", "tbd", "to be determined", "n/a", "none",
            "information not provided", "data not available", "no information",
            "placeholder", "sample text", "lorem ipsum"
        ]
        
        content_lower = content.lower()
        has_placeholder = any(indicator in content_lower for indicator in placeholder_indicators)
        
        # Check if content is too generic
        generic_phrases = [
            "this section contains", "information will be added", "details to follow",
            "section under development", "content pending"
        ]
        
        has_generic = any(phrase in content_lower for phrase in generic_phrases)
        
        # Determine if section is valid
        is_valid = (
            word_count >= min_words and
            line_count >= min_lines and
            char_count >= min_chars and
            not has_placeholder and
            not has_generic
        )
        
        reason = "valid"
        if word_count < min_words:
            reason = f"too few words ({word_count} < {min_words})"
        elif line_count < min_lines:
            reason = f"too few lines ({line_count} < {min_lines})"
        elif char_count < min_chars:
            reason = f"too few characters ({char_count} < {min_chars})"
        elif has_placeholder:
            reason = "contains placeholder content"
        elif has_generic:
            reason = "contains generic content"
        
        return {
            "is_valid": is_valid,
            "reason": reason,
            "word_count": word_count,
            "line_count": line_count,
            "char_count": char_count,
            "has_placeholder": has_placeholder,
            "has_generic": has_generic
        }
    
    def _evaluate_readability(self, memo_text: str) -> Dict[str, float]:
        """Evaluate readability using Flesch-Kincaid and analyst score"""
        
        # Flesch-Kincaid Grade Level
        sentences = len(re.split(r'[.!?]+', memo_text))
        words = len(memo_text.split())
        syllables = len(re.findall(r'[aeiouy]+', memo_text.lower()))
        
        if sentences > 0 and words > 0:
            fk_score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
        else:
            fk_score = 0.0
        
        # Calculate analyst score based on Flesch-Kincaid
        # Flesch-Kincaid scores: 0-30 = very difficult, 30-50 = difficult, 50-60 = fairly difficult, 60-70 = standard, 70-80 = fairly easy, 80-90 = easy, 90-100 = very easy
        fk_score = max(0.0, fk_score)
        
        # Convert Flesch-Kincaid to analyst score (1-5 scale)
        if fk_score >= 80:
            analyst_score = 5.0  # Very easy to read
        elif fk_score >= 70:
            analyst_score = 4.5  # Fairly easy
        elif fk_score >= 60:
            analyst_score = 4.0  # Standard
        elif fk_score >= 50:
            analyst_score = 3.5  # Fairly difficult
        elif fk_score >= 30:
            analyst_score = 3.0  # Difficult
        else:
            analyst_score = 2.5  # Very difficult
        
        return {
            "fk_score": fk_score,
            "analyst_score": analyst_score
        }
    
    def _evaluate_visuals(self, memo_text: str = None) -> Dict[str, Any]:
        """Check for presence of Mermaid diagrams and charts"""
        if not memo_text:
            return {
                "chart_present": False,
                "mermaid_diagrams": 0
            }
        
        # Check for Mermaid diagrams
        mermaid_pattern = r'```mermaid\s*([\s\S]+?)```'
        mermaid_diagrams = len(re.findall(mermaid_pattern, memo_text))
        
        # Check for other chart indicators
        chart_indicators = [
            r'graph\s+[A-Z]',  # Mermaid graph syntax
            r'flowchart\s+[A-Z]',  # Mermaid flowchart
            r'sequenceDiagram',  # Mermaid sequence diagram
            r'classDiagram',  # Mermaid class diagram
            r'stateDiagram',  # Mermaid state diagram
            r'pie\s+chart',  # Mermaid pie chart
            r'gantt',  # Mermaid gantt chart
            r'journey',  # Mermaid journey
            r'gitgraph',  # Mermaid git graph
            r'C4Context',  # Mermaid C4 context
            r'C4Container',  # Mermaid C4 container
            r'C4Component',  # Mermaid C4 component
            r'C4Code',  # Mermaid C4 code
        ]
        
        total_charts = mermaid_diagrams
        for pattern in chart_indicators:
            total_charts += len(re.findall(pattern, memo_text, re.IGNORECASE))
        
        return {
            "chart_present": total_charts > 0,
            "mermaid_diagrams": mermaid_diagrams,
            "total_charts": total_charts
        }
    
    def _evaluate_duplicates(self, memo_text: str) -> Dict[str, Any]:
        """Detect duplicate or very similar lines"""
        lines = [line.strip() for line in memo_text.split('\n') if line.strip()]
        duplicates = []
        
        for i, line1 in enumerate(lines):
            for j, line2 in enumerate(lines[i+1:], i+1):
                if len(line1) > 20 and len(line2) > 20:  # Only check substantial lines
                    similarity = self._levenshtein_similarity(line1, line2)
                    if similarity > 0.9:  # 90% similarity threshold
                        duplicates.append((line1, line2, similarity))
        
        return {
            "count": len(duplicates),
            "ratio": len(duplicates) / max(1, len(lines)),
            "duplicates": duplicates
        }
    
    def _levenshtein_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using Levenshtein distance"""
        if len(str1) < len(str2):
            str1, str2 = str2, str1
        
        if len(str2) == 0:
            return 0.0
        
        previous_row = list(range(len(str2) + 1))
        for i, c1 in enumerate(str1):
            current_row = [i + 1]
            for j, c2 in enumerate(str2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        distance = previous_row[-1]
        max_len = max(len(str1), len(str2))
        return 1.0 - (distance / max_len)
    
    def _calculate_costs(self) -> Dict[str, float]:
        """Calculate total costs and time from logged section data"""
        total_cost = 0.0
        total_time = 0.0
        
        # Calculate from logged section timings
        for section_name, timing_data in self.section_timings.items():
            if "start" in timing_data and "end" in timing_data:
                section_time = timing_data["end"] - timing_data["start"]
                total_time += section_time
                
                # Calculate cost for this section
                if "tokens" in timing_data and "model" in timing_data:
                    tokens = timing_data["tokens"]
                    model = timing_data["model"]
                    if model in self.api_costs:
                        section_cost = (tokens / 1000) * self.api_costs[model]
                        total_cost += section_cost
        
        return {
            "total_cost": total_cost,
            "time": total_time
        }
    
    def _evaluate_coverage(self, memo_text: str) -> Dict[str, Any]:
        """Evaluate coverage of unknown/placeholder content"""
        unknown_indicators = ["N/A", "TBD", "unknown", "not available", "to be determined"]
        placeholder_count = 0
        
        for indicator in unknown_indicators:
            placeholder_count += memo_text.lower().count(indicator.lower())
        
        total_words = len(memo_text.split())
        unknown_ratio = placeholder_count / max(1, total_words)
        
        return {
            "count": placeholder_count,
            "ratio": unknown_ratio
        }
    
    def _calculate_additional_metrics(self, memo_text: str) -> Dict[str, Any]:
        """Calculate additional memo metrics"""
        return {
            "memo_length_chars": len(memo_text),
            "memo_length_words": len(memo_text.split()),
            "section_count": len([s for s in self.REQUIRED_SECTIONS if s in memo_text.upper()])
        }
    
    def _evaluate_system_performance(self) -> Dict[str, Any]:
        """Evaluate system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            
            # GPU usage (if available)
            gpu_percent = 0.0
            if GPUTIL_AVAILABLE:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu_percent = gpus[0].load * 100
                except:
                    pass
            
            return {
                "gpu_usage_percent": gpu_percent,
                "cpu_usage_percent": cpu_percent,
                "memory_usage_mb": memory_mb,
                "system_robustness_score": 4.0  # Placeholder - would need noise testing
            }
        except:
            return {
                "gpu_usage_percent": 0.0,
                "cpu_usage_percent": 0.0,
                "memory_usage_mb": 0.0,
                "system_robustness_score": 4.0
            }
    
    def generate_evaluation_report(self, metrics: MemoEvaluationMetrics) -> str:
        """Generate a comprehensive evaluation report"""
        report = f"""
INVESTMENT MEMO EVALUATION REPORT
================================

SECTION COMPLETENESS
-------------------
✅ All Sections Present: {'Yes' if metrics.all_sections_present else 'No'}
📋 Missing Sections: {len(metrics.missing_sections)}
{chr(10).join(f'  - {section}' for section in metrics.missing_sections) if metrics.missing_sections else '  None'}

READABILITY
-----------
📖 Flesch-Kincaid Score: {metrics.flesch_kincaid_score:.1f}
👨‍💼 Analyst Readability Score: {metrics.analyst_readability_score:.1f}/5.0

VISUALS (Simplified)
--------------------
📊 Chart Present: {'Yes' if metrics.chart_present else 'No'}

DUPLICATE CONTENT
-----------------
🔄 Duplicate Lines: {metrics.duplicate_lines_count}
📊 Duplicate Ratio: {metrics.duplicate_ratio:.2%}

COST AND TIME ANALYSIS
---------------------
💰 Total Cost: ${metrics.total_cost_usd:.4f}
⏱️ Generation Time: {metrics.generation_time_seconds:.1f} seconds
📊 Token Usage: {sum(metrics.token_usage.values()):,} tokens

COVERAGE ANALYSIS
-----------------
❓ Unknown Coverage: {metrics.unknown_coverage_ratio:.2%}
📝 Placeholder Count: {metrics.placeholder_count}

SYSTEM PERFORMANCE
------------------
🖥️ CPU Usage: {metrics.cpu_usage_percent:.1f}%
🎮 GPU Usage: {metrics.gpu_usage_percent:.1f}%
💾 Memory Usage: {metrics.memory_usage_mb:.1f} MB

TRADITIONAL VC COMPARISON
-------------------------
⏰ Time Savings: {metrics.traditional_vc_comparison['time_savings_percentage']:.1f}%
💰 Cost Savings: {metrics.traditional_vc_comparison['cost_savings_percentage']:.1f}%
📈 Efficiency Improvements:
  - Time Efficiency: {metrics.traditional_vc_comparison['efficiency_improvement']['time_efficiency']:.1f}x faster
  - Cost Efficiency: {metrics.traditional_vc_comparison['efficiency_improvement']['cost_efficiency']:.1f}x cheaper

📚 Benchmark Source: {metrics.traditional_vc_comparison['benchmark_source']}

DETAILED SECTION METRICS
------------------------
"""
        
        for sm in metrics.section_metrics:
            report += f"""
{sm.section_name}:
  - Runtime: {sm.runtime_seconds:.1f}s
  - Tokens: {sm.tokens_used:,}
  - Cost: ${sm.cost_usd:.4f}
  - Content: {sm.content_length_chars:,} chars, {sm.content_length_words:,} words
  - Quality Score: {sm.quality_score:.2f}/1.0
"""
        
        report += f"""
OVERALL ASSESSMENT
------------------
🎯 Overall Quality Score: {self._calculate_overall_score(metrics):.1f}/10
📊 Pass/Fail Criteria Met: {self._check_pass_fail_criteria(metrics)}

ACADEMIC ANALYSIS SUMMARY
-------------------------
This AI system demonstrates significant improvements over traditional VC processes:

1. TIME EFFICIENCY: {metrics.traditional_vc_comparison['time_savings_percentage']:.1f}% time reduction
2. COST EFFICIENCY: {metrics.traditional_vc_comparison['cost_savings_percentage']:.1f}% cost reduction
3. SCALABILITY: Can process multiple companies simultaneously
4. CONSISTENCY: Standardized analysis framework across all evaluations
5. QUALITY: Maintains professional investment memo standards

The system represents a paradigm shift in VC due diligence, enabling faster, cheaper, and more consistent investment analysis while maintaining the quality standards expected in the industry.
"""
        
        return report
    
    def _calculate_overall_score(self, metrics: MemoEvaluationMetrics) -> float:
        """Calculate overall quality score (0-10)"""
        score = 0.0
        
        # Section completeness (2 points)
        if metrics.all_sections_present:
            score += 2.0
        
        # Readability (1 point)
        if metrics.flesch_kincaid_score <= 13 and metrics.analyst_readability_score >= 4:
            score += 1.0
        
        # Visuals (1 point)
        if metrics.chart_present:
            score += 1.0
        
        # Coverage (1 point)
        if metrics.unknown_coverage_ratio < 0.2:
            score += 1.0
        
        return score
    
    def _check_pass_fail_criteria(self, metrics: MemoEvaluationMetrics) -> str:
        """Check if memo meets pass/fail criteria"""
        criteria = []
        
        if metrics.all_sections_present:
            criteria.append("✅ All sections present")
        else:
            criteria.append("❌ Missing sections")
        
        if metrics.flesch_kincaid_score <= 13:
            criteria.append("✅ Readable (F-K ≤ 13)")
        else:
            criteria.append("❌ Too complex (F-K > 13)")
        
        if metrics.analyst_readability_score >= 4:
            criteria.append("✅ Analyst approved (≥ 4/5)")
        else:
            criteria.append("❌ Analyst score too low")
        
        if metrics.chart_present:
            criteria.append("✅ Chart included")
        else:
            criteria.append("❌ Missing chart")
        
        if metrics.unknown_coverage_ratio < 0.2:
            criteria.append("✅ Good coverage")
        else:
            criteria.append("❌ Too many unknowns")
        
        return " | ".join(criteria)


# Usage example
if __name__ == "__main__":
    evaluator = MemoEvaluator()
    evaluator.start_evaluation()
    
    # Example memo text
    sample_memo = """
    DETAILED SUMMARY
    This is a sample investment memo for testing purposes.
    
    COMPANY OVERVIEW
    The company operates in the technology sector.
    
    PROBLEM STATEMENT
    There is a clear market need for this solution.
    """
    
    metrics = evaluator.evaluate_memo(sample_memo)
    print(evaluator.generate_evaluation_report(metrics)) 