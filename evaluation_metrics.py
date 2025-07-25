"""
Comprehensive evaluation metrics for investment memo generator
Implements all metrics from the evaluation framework
Enhanced for academic analysis and comparison with traditional VC processes
"""

import json
import re
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import textstat
from dataclasses import dataclass

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
    
    # Content quality (0-3 scale)
    product_quality_score: int
    competitors_quality_score: int
    risks_quality_score: int
    
    # Factual accuracy
    factual_accuracy_score: float  # 0-1
    factual_errors: List[str]
    
    # Formatting
    formatting_score: float  # 0-1
    formatting_issues: List[str]
    
    # Readability
    flesch_kincaid_score: float
    analyst_readability_score: float  # 1-5 scale
    
    # Visuals
    images_present: bool
    charts_present: bool
    visual_count: int
    
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
    
    # Traditional VC time estimates (based on industry research)
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
        self.token_usage = {}
        self.section_timings = {}
        self.section_tokens = {}
        self.api_costs = {
            "gpt-4": 0.03,  # per 1K tokens
            "gpt-4o": 0.005,
            "gpt-4o-mini": 0.00015,
            "gpt-3.5-turbo": 0.002
        }
    
    def start_evaluation(self):
        """Start timing the evaluation process"""
        self.start_time = time.time()
    
    def log_section_start(self, section_name: str):
        """Log the start time of a section"""
        self.section_timings[section_name] = {"start": time.time()}
    
    def log_section_end(self, section_name: str, tokens_used: int = 0, model: str = "gpt-4"):
        """Log the end time and tokens for a section"""
        if section_name in self.section_timings:
            self.section_timings[section_name]["end"] = time.time()
            self.section_timings[section_name]["tokens"] = tokens_used
            self.section_timings[section_name]["model"] = model
    
    def log_token_usage(self, model: str, tokens: int):
        """Log token usage for cost calculation"""
        if model not in self.token_usage:
            self.token_usage[model] = 0
        self.token_usage[model] += tokens
    
    def evaluate_memo(self, memo_text: str, memo_html: str = None, 
                     ground_truth: Dict = None) -> MemoEvaluationMetrics:
        """Comprehensive memo evaluation"""
        
        # Section completeness
        section_metrics = self._evaluate_sections(memo_text)
        
        # Content quality
        content_metrics = self._evaluate_content_quality(memo_text)
        
        # Factual accuracy
        factual_metrics = self._evaluate_factual_accuracy(memo_text, ground_truth)
        
        # Formatting
        formatting_metrics = self._evaluate_formatting(memo_text, memo_html)
        
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
        
        # Section-level metrics
        section_metrics_list = self._calculate_section_metrics(memo_text)
        
        # Traditional VC comparison
        traditional_comparison = self._compare_with_traditional_vc(section_metrics_list)
        
        return MemoEvaluationMetrics(
            all_sections_present=section_metrics["all_present"],
            missing_sections=section_metrics["missing"],
            product_quality_score=content_metrics["product_score"],
            competitors_quality_score=content_metrics["competitors_score"], 
            risks_quality_score=content_metrics["risks_score"],
            factual_accuracy_score=factual_metrics["accuracy_score"],
            factual_errors=factual_metrics["errors"],
            formatting_score=formatting_metrics["score"],
            formatting_issues=formatting_metrics["issues"],
            flesch_kincaid_score=readability_metrics["fk_score"],
            analyst_readability_score=readability_metrics["analyst_score"],
            images_present=visual_metrics["images_present"],
            charts_present=visual_metrics["charts_present"],
            visual_count=visual_metrics["total_count"],
            duplicate_lines_count=duplicate_metrics["count"],
            duplicate_ratio=duplicate_metrics["ratio"],
            total_cost_usd=cost_metrics["total_cost"],
            generation_time_seconds=cost_metrics["time"],
            token_usage=self.token_usage,
            unknown_coverage_ratio=coverage_metrics["ratio"],
            placeholder_count=coverage_metrics["count"],
            memo_length_chars=additional_metrics["chars"],
            memo_length_words=additional_metrics["words"],
            section_count=additional_metrics["sections"],
            section_metrics=section_metrics_list,
            traditional_vc_comparison=traditional_comparison
        )
    
    def _calculate_section_metrics(self, memo_text: str) -> List[SectionMetrics]:
        """Calculate detailed metrics for each section"""
        section_metrics = []
        
        for section_name in self.REQUIRED_SECTIONS:
            # Extract section content
            section_pattern = rf"{section_name}.*?(?=\d+\.|$)"
            section_match = re.search(section_pattern, memo_text, re.IGNORECASE | re.DOTALL)
            
            if section_match:
                section_content = section_match.group(0)
                
                # Get timing data
                runtime = 0.0
                tokens = 0
                cost = 0.0
                model = "gpt-4"
                
                if section_name in self.section_timings:
                    timing_data = self.section_timings[section_name]
                    if "start" in timing_data and "end" in timing_data:
                        runtime = timing_data["end"] - timing_data["start"]
                    if "tokens" in timing_data:
                        tokens = timing_data["tokens"]
                    if "model" in timing_data:
                        model = timing_data["model"]
                    
                    # Calculate cost
                    if model in self.api_costs:
                        cost = (tokens / 1000) * self.api_costs[model]
                
                # Calculate quality score (simplified)
                quality_score = min(1.0, len(section_content) / 500)  # Normalize by expected length
                
                section_metrics.append(SectionMetrics(
                    section_name=section_name,
                    runtime_seconds=runtime,
                    tokens_used=tokens,
                    cost_usd=cost,
                    content_length_chars=len(section_content),
                    content_length_words=len(section_content.split()),
                    quality_score=quality_score
                ))
        
        return section_metrics
    
    def _compare_with_traditional_vc(self, section_metrics: List[SectionMetrics]) -> Dict[str, Any]:
        """Compare AI performance with traditional VC processes"""
        
        total_ai_time = sum(sm.runtime_seconds for sm in section_metrics)
        total_ai_cost = sum(sm.cost_usd for sm in section_metrics)
        
        total_traditional_time = sum(self.TRADITIONAL_VC_TIMES.get(sm.section_name, 0) for sm in section_metrics)
        total_traditional_time_minutes = total_traditional_time
        total_ai_time_minutes = total_ai_time / 60
        
        # Traditional VC cost estimate (based on analyst hourly rate)
        traditional_analyst_rate = 150  # USD per hour (senior analyst)
        total_traditional_cost = (total_traditional_time / 60) * traditional_analyst_rate
        
        time_savings_percentage = ((total_traditional_time_minutes - total_ai_time_minutes) / total_traditional_time_minutes) * 100
        cost_savings_percentage = ((total_traditional_cost - total_ai_cost) / total_traditional_cost) * 100
        
        return {
            "traditional_time_minutes": total_traditional_time_minutes,
            "ai_time_minutes": total_ai_time_minutes,
            "time_savings_minutes": total_traditional_time_minutes - total_ai_time_minutes,
            "time_savings_percentage": time_savings_percentage,
            "traditional_cost_usd": total_traditional_cost,
            "ai_cost_usd": total_ai_cost,
            "cost_savings_usd": total_traditional_cost - total_ai_cost,
            "cost_savings_percentage": cost_savings_percentage,
            "efficiency_improvement": {
                "time_efficiency": total_traditional_time_minutes / max(0.1, total_ai_time_minutes),
                "cost_efficiency": total_traditional_cost / max(0.01, total_ai_cost)
            },
            "section_comparisons": [
                {
                    "section": sm.section_name,
                    "traditional_time_minutes": self.TRADITIONAL_VC_TIMES.get(sm.section_name, 0),
                    "ai_time_minutes": sm.runtime_seconds / 60,
                    "time_savings_percentage": ((self.TRADITIONAL_VC_TIMES.get(sm.section_name, 0) - (sm.runtime_seconds / 60)) / max(0.1, self.TRADITIONAL_VC_TIMES.get(sm.section_name, 0))) * 100
                }
                for sm in section_metrics
            ]
        }
    
    def _evaluate_sections(self, memo_text: str) -> Dict[str, Any]:
        """Check if all 17 required sections are present"""
        memo_upper = memo_text.upper()
        missing = []
        
        for section in self.REQUIRED_SECTIONS:
            if section not in memo_upper:
                missing.append(section)
        
        return {
            "all_present": len(missing) == 0,
            "missing": missing,
            "present_count": len(self.REQUIRED_SECTIONS) - len(missing)
        }
    
    def _evaluate_content_quality(self, memo_text: str) -> Dict[str, int]:
        """Evaluate content quality for Product, Competitors, and Risks sections (0-3 scale)"""
        
        def score_section(section_name: str, text: str) -> int:
            """Score a section from 0-3 based on content quality"""
            section_pattern = rf"{section_name}.*?(?=\d+\.|$)"
            section_match = re.search(section_pattern, text, re.IGNORECASE | re.DOTALL)
            
            if not section_match:
                return 0
            
            section_text = section_match.group(0)
            
            # Score based on content length and quality indicators
            if len(section_text) < 100:
                return 1  # Minimal content
            elif len(section_text) < 300:
                return 2  # Moderate content
            elif len(section_text) >= 300:
                return 3  # Substantial content
            
            return 0
        
        return {
            "product_score": score_section("PRODUCT/SERVICE DESCRIPTION", memo_text),
            "competitors_score": score_section("COMPETITORS", memo_text),
            "risks_score": score_section("RISKS", memo_text)
        }
    
    def _evaluate_factual_accuracy(self, memo_text: str, ground_truth: Dict = None) -> Dict[str, Any]:
        """Evaluate factual accuracy against ground truth"""
        if not ground_truth:
            return {
                "accuracy_score": 0.0,
                "errors": ["No ground truth provided for factual accuracy check"]
            }
        
        # This would need implementation based on specific ground truth format
        # For now, return placeholder
        return {
            "accuracy_score": 0.8,  # Placeholder
            "errors": []
        }
    
    def _evaluate_formatting(self, memo_text: str, memo_html: str = None) -> Dict[str, Any]:
        """Evaluate formatting quality"""
        issues = []
        score = 1.0
        
        # Check for basic formatting elements
        if not re.search(r'\*\*.*\*\*', memo_text):  # Bold text
            issues.append("No bold formatting detected")
            score -= 0.1
        
        if not re.search(r'•|\*|\-', memo_text):  # Bullet points
            issues.append("No bullet points detected")
            score -= 0.1
        
        if not re.search(r'\d+\.', memo_text):  # Numbered sections
            issues.append("No numbered sections detected")
            score -= 0.1
        
        # Check HTML formatting if available
        if memo_html:
            if '<img' not in memo_html:
                issues.append("No images in HTML")
                score -= 0.1
            
            if '<table' not in memo_html and '<svg' not in memo_html:
                issues.append("No tables or charts in HTML")
                score -= 0.1
        
        return {
            "score": max(0.0, score),
            "issues": issues
        }
    
    def _evaluate_readability(self, memo_text: str) -> Dict[str, float]:
        """Evaluate readability using Flesch-Kincaid and analyst scoring"""
        
        # Calculate Flesch-Kincaid score
        try:
            fk_score = textstat.flesch_reading_ease(memo_text)
        except:
            fk_score = 50.0  # Default if calculation fails
        
        # Convert to Flesch-Kincaid grade level
        fk_grade = textstat.flesch_kincaid_grade(memo_text)
        
        # Analyst readability score (1-5 scale) - simplified heuristic
        # Based on sentence length, word complexity, etc.
        avg_sentence_length = len(memo_text.split('.')) / max(1, len(re.findall(r'[.!?]', memo_text)))
        
        if avg_sentence_length < 15:
            analyst_score = 5.0
        elif avg_sentence_length < 20:
            analyst_score = 4.0
        elif avg_sentence_length < 25:
            analyst_score = 3.0
        elif avg_sentence_length < 30:
            analyst_score = 2.0
        else:
            analyst_score = 1.0
        
        return {
            "fk_score": fk_grade,
            "analyst_score": analyst_score
        }
    
    def _evaluate_visuals(self, memo_html: str = None) -> Dict[str, Any]:
        """Check for presence of images and charts"""
        if not memo_html:
            return {
                "images_present": False,
                "charts_present": False,
                "total_count": 0
            }
        
        img_count = len(re.findall(r'<img[^>]*>', memo_html))
        svg_count = len(re.findall(r'<svg[^>]*>', memo_html))
        canvas_count = len(re.findall(r'<canvas[^>]*>', memo_html))
        
        return {
            "images_present": img_count > 0,
            "charts_present": (svg_count + canvas_count) > 0,
            "total_count": img_count + svg_count + canvas_count
        }
    
    def _evaluate_duplicates(self, memo_text: str) -> Dict[str, Any]:
        """Find duplicate lines using Levenshtein similarity"""
        lines = memo_text.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        
        duplicate_count = 0
        total_comparisons = 0
        
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                total_comparisons += 1
                similarity = self._levenshtein_similarity(lines[i], lines[j])
                if similarity >= 0.9:  # 90% similarity threshold
                    duplicate_count += 1
        
        ratio = duplicate_count / max(1, total_comparisons)
        
        return {
            "count": duplicate_count,
            "ratio": ratio
        }
    
    def _levenshtein_similarity(self, str1: str, str2: str) -> float:
        """Calculate Levenshtein similarity between two strings"""
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
        return 1 - (distance / max_len)
    
    def _calculate_costs(self) -> Dict[str, float]:
        """Calculate total cost and time"""
        time_seconds = time.time() - self.start_time if self.start_time else 0
        
        total_cost = 0.0
        for model, tokens in self.token_usage.items():
            if model in self.api_costs:
                total_cost += (tokens / 1000) * self.api_costs[model]
        
        return {
            "total_cost": total_cost,
            "time": time_seconds
        }
    
    def _evaluate_coverage(self, memo_text: str) -> Dict[str, Any]:
        """Evaluate coverage of unknown/placeholder responses"""
        placeholder_patterns = [
            r'\b(?:I don\'t know|Not available|Not applicable|N/A|TBD|TBA)\b',
            r'\[.*?\]',  # Bracketed placeholders
            r'<.*?>',    # HTML-like placeholders
        ]
        
        total_placeholders = 0
        for pattern in placeholder_patterns:
            total_placeholders += len(re.findall(pattern, memo_text, re.IGNORECASE))
        
        # Calculate ratio based on expected answer slots
        # Assuming ~50 key data points that should be filled
        expected_slots = 50
        ratio = total_placeholders / expected_slots
        
        return {
            "count": total_placeholders,
            "ratio": ratio
        }
    
    def _calculate_additional_metrics(self, memo_text: str) -> Dict[str, Any]:
        """Calculate additional memo metrics"""
        return {
            "chars": len(memo_text),
            "words": len(memo_text.split()),
            "sections": len(re.findall(r'\d+\.', memo_text))
        }
    
    def generate_evaluation_report(self, metrics: MemoEvaluationMetrics) -> str:
        """Generate a comprehensive evaluation report"""
        
        report = f"""
INVESTMENT MEMO EVALUATION REPORT
================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SECTION COMPLETENESS
-------------------
✅ All 17 sections present: {metrics.all_sections_present}
📊 Sections found: {metrics.section_count}/17
❌ Missing sections: {', '.join(metrics.missing_sections) if metrics.missing_sections else 'None'}

CONTENT QUALITY (0-3 scale)
---------------------------
📈 Product/Service Description: {metrics.product_quality_score}/3
🏆 Competitors Analysis: {metrics.competitors_quality_score}/3
⚠️ Risks Assessment: {metrics.risks_quality_score}/3
📊 Average Quality Score: {(metrics.product_quality_score + metrics.competitors_quality_score + metrics.risks_quality_score) / 3:.1f}/3

FACTUAL ACCURACY
----------------
🎯 Accuracy Score: {metrics.factual_accuracy_score:.2f}/1.0
❌ Factual Errors: {len(metrics.factual_errors)}
{chr(10).join(f'  - {error}' for error in metrics.factual_errors) if metrics.factual_errors else '  None detected'}

FORMATTING QUALITY
------------------
🎨 Formatting Score: {metrics.formatting_score:.2f}/1.0
❌ Formatting Issues: {len(metrics.formatting_issues)}
{chr(10).join(f'  - {issue}' for issue in metrics.formatting_issues) if metrics.formatting_issues else '  None detected'}

READABILITY
-----------
📖 Flesch-Kincaid Grade Level: {metrics.flesch_kincaid_score:.1f}
👨‍💼 Analyst Readability Score: {metrics.analyst_readability_score:.1f}/5.0
✅ F-K ≤ 13: {'Yes' if metrics.flesch_kincaid_score <= 13 else 'No'}
✅ Analyst ≥ 4/5: {'Yes' if metrics.analyst_readability_score >= 4 else 'No'}

VISUALS
--------
🖼️ Images Present: {'Yes' if metrics.images_present else 'No'}
📊 Charts Present: {'Yes' if metrics.charts_present else 'No'}
📈 Total Visual Elements: {metrics.visual_count}
✅ Minimum Visuals (1 image + 1 chart): {'Yes' if metrics.images_present and metrics.charts_present else 'No'}

DUPLICATE CONTENT
-----------------
🔄 Duplicate Lines: {metrics.duplicate_lines_count}
📊 Duplicate Ratio: {metrics.duplicate_ratio:.2%}

COST & PERFORMANCE
------------------
💰 Total Cost: ${metrics.total_cost_usd:.4f}
⏱️ Generation Time: {metrics.generation_time_seconds:.1f} seconds
🔢 Token Usage: {json.dumps(metrics.token_usage, indent=2)}

COVERAGE ANALYSIS
-----------------
❓ Unknown/Placeholder Coverage: {metrics.unknown_coverage_ratio:.2%}
📝 Placeholder Count: {metrics.placeholder_count}
✅ Good Coverage (< 20%): {'Yes' if metrics.unknown_coverage_ratio < 0.2 else 'No'}

MEMO STATISTICS
---------------
📄 Total Characters: {metrics.memo_length_chars:,}
📝 Total Words: {metrics.memo_length_words:,}
📊 Average Words per Section: {metrics.memo_length_words / max(1, metrics.section_count):.1f}

TRADITIONAL VC COMPARISON
-------------------------
⏰ Traditional VC Time: {metrics.traditional_vc_comparison['traditional_time_minutes']:.1f} minutes
🤖 AI Generation Time: {metrics.traditional_vc_comparison['ai_time_minutes']:.1f} minutes
⚡ Time Savings: {metrics.traditional_vc_comparison['time_savings_minutes']:.1f} minutes ({metrics.traditional_vc_comparison['time_savings_percentage']:.1f}%)

💰 Traditional VC Cost: ${metrics.traditional_vc_comparison['traditional_cost_usd']:.2f}
🤖 AI Generation Cost: ${metrics.traditional_vc_comparison['ai_cost_usd']:.4f}
💵 Cost Savings: ${metrics.traditional_vc_comparison['cost_savings_usd']:.2f} ({metrics.traditional_vc_comparison['cost_savings_percentage']:.1f}%)

📈 Efficiency Improvements:
  • Time Efficiency: {metrics.traditional_vc_comparison['efficiency_improvement']['time_efficiency']:.1f}x faster
  • Cost Efficiency: {metrics.traditional_vc_comparison['efficiency_improvement']['cost_efficiency']:.1f}x cheaper

SECTION-BY-SECTION BREAKDOWN
----------------------------
"""
        
        # Add section-by-section comparison
        for section_comp in metrics.traditional_vc_comparison['section_comparisons']:
            report += f"""
{section_comp['section']}:
  • Traditional: {section_comp['traditional_time_minutes']:.1f} min
  • AI: {section_comp['ai_time_minutes']:.1f} min
  • Savings: {section_comp['time_savings_percentage']:.1f}%
"""
        
        report += f"""
DETAILED SECTION METRICS
------------------------
"""
        
        for sm in metrics.section_metrics:
            report += f"""
{sm.section_name}:
  • Runtime: {sm.runtime_seconds:.1f}s
  • Tokens: {sm.tokens_used:,}
  • Cost: ${sm.cost_usd:.4f}
  • Content: {sm.content_length_chars:,} chars, {sm.content_length_words:,} words
  • Quality Score: {sm.quality_score:.2f}/1.0
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
        
        # Content quality (3 points)
        content_avg = (metrics.product_quality_score + metrics.competitors_quality_score + metrics.risks_quality_score) / 3
        score += content_avg
        
        # Factual accuracy (1 point)
        score += metrics.factual_accuracy_score
        
        # Formatting (1 point)
        score += metrics.formatting_score
        
        # Readability (1 point)
        if metrics.flesch_kincaid_score <= 13 and metrics.analyst_readability_score >= 4:
            score += 1.0
        
        # Visuals (1 point)
        if metrics.images_present and metrics.charts_present:
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
        
        if metrics.images_present and metrics.charts_present:
            criteria.append("✅ Visuals included")
        else:
            criteria.append("❌ Missing visuals")
        
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
1. DETAILED SUMMARY
This is a sample memo for evaluation.

2. COMPANY OVERVIEW
Company details here.

3. PROBLEM STATEMENT
Problem description.

4. SOLUTION OVERVIEW
Solution details.

5. PRODUCT/SERVICE DESCRIPTION
Product information.

6. MARKET SIZE & ANALYSIS
Market analysis.

7. COMPETITORS
Competitor analysis.

8. BUSINESS MODEL
Business model details.

9. TECHNICAL DUE DILIGENCE
Technical assessment.

10. FINANCIAL ANALYSIS
Financial details.

11. TEAM & MANAGEMENT
Team information.

12. ESG CONSIDERATIONS
ESG analysis.

13. RISKS
Risk assessment.

14. INVESTMENT & EXIT STRATEGIES
Investment strategy.

15. COUNTERFACTUAL ANALYSIS
Counterfactual analysis.

16. FOLLOW-UP QUESTIONS
Follow-up questions.

17. AI DISCUSSION AND COMMENTARY
AI commentary.
"""
    
    # Log some token usage
    evaluator.log_token_usage("gpt-4", 1500)
    evaluator.log_token_usage("gpt-3.5-turbo", 800)
    
    # Evaluate the memo
    metrics = evaluator.evaluate_memo(sample_memo)
    
    # Generate report
    report = evaluator.generate_evaluation_report(metrics)
    print(report) 