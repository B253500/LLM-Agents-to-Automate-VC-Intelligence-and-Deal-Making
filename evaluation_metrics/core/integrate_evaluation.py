"""
Integration script to capture detailed evaluation metrics during memo generation
Enhanced for academic analysis and comparison with traditional VC processes
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from .evaluation_metrics import MemoEvaluator, SectionMetrics

class MemoGenerationTracker:
    """Tracks memo generation process with detailed metrics"""
    
    def __init__(self):
        self.evaluator = MemoEvaluator()
        self.evaluator.start_evaluation()
        self.section_start_times = {}
        self.section_token_usage = {}
        self.section_models = {}
        
    def start_section(self, section_name: str):
        """Start timing a section"""
        self.evaluator.log_section_start(section_name)
        self.section_start_times[section_name] = time.time()
        print(f"⏱️ Starting section: {section_name}")
    
    def end_section(self, section_name: str, tokens_used: int = 0, model: str = "gpt-4"):
        """End timing a section and log metrics"""
        self.evaluator.log_section_end(section_name, tokens_used, model)
        self.section_token_usage[section_name] = tokens_used
        self.section_models[section_name] = model
        
        if section_name in self.section_start_times:
            runtime = time.time() - self.section_start_times[section_name]
            print(f"✅ Completed {section_name}: {runtime:.1f}s, {tokens_used:,} tokens, ${(tokens_used/1000) * self.evaluator.api_costs.get(model, 0.03):.4f}")
    
    def log_token_usage(self, model: str, tokens: int):
        """Log token usage for cost calculation"""
        self.evaluator.log_token_usage(model, tokens)
    
    def evaluate_memo(self, memo_text: str, memo_html: str = None, ground_truth: Dict = None):
        """Evaluate the generated memo"""
        return self.evaluator.evaluate_memo(memo_text, memo_html, ground_truth)
    
    def generate_report(self, metrics):
        """Generate comprehensive evaluation report"""
        return self.evaluator.generate_evaluation_report(metrics)
    
    def save_metrics(self, metrics, output_dir: str, pdf_name: str):
        """Save detailed metrics for academic analysis"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comprehensive metrics JSON
        metrics_file = f"{output_dir}/detailed_metrics_{pdf_name}_{timestamp}.json"

        total_tokens = sum(metrics.token_usage.values()) if getattr(metrics, "token_usage", None) else 0

        metrics_data = {
            "memo_info": {
                "pdf_name": pdf_name,
                "generation_timestamp": timestamp,
                "total_runtime_seconds": metrics.generation_time_seconds,
                "total_cost_usd": metrics.total_cost_usd,
                "token_cost_usd": getattr(metrics, "token_cost_usd", 0.0),
                "external_cost_usd": getattr(metrics, "external_cost_usd", 0.0),
                "total_tokens": total_tokens,
                "section_count": metrics.section_count
            },
            "quality_metrics": {
                "all_sections_present": metrics.all_sections_present,
                "missing_sections": metrics.missing_sections,
                "flesch_kincaid_score": metrics.flesch_kincaid_score,
                "overall_quality_score": getattr(metrics, "overall_quality_score", self.evaluator._calculate_overall_score(metrics)),
                "quality_breakdown": getattr(metrics, "quality_breakdown", []),
                "chart_present": getattr(metrics, "chart_present", False),
                "duplicate_ratio": getattr(metrics, "duplicate_ratio", 0.0)
            },
            "performance_metrics": {
                "token_usage_by_model": getattr(metrics, "token_usage", {}),
                "timing_table": getattr(metrics, "timing_table", {}),
                "system": {
                    "cpu_usage_percent": metrics.cpu_usage_percent,
                    "gpu_usage_percent": metrics.gpu_usage_percent,
                    "memory_usage_mb": metrics.memory_usage_mb,
                    "system_robustness_score": metrics.system_robustness_score
                }
            },
            "section_metrics": [
                {
                    "section_name": sm.section_name,
                    "runtime_seconds": sm.runtime_seconds,
                    "tokens_used": sm.tokens_used,
                    "cost_usd": sm.cost_usd,
                    "content_length_chars": sm.content_length_chars,
                    "content_length_words": sm.content_length_words,
                    "quality_score": sm.quality_score
                }
                for sm in metrics.section_metrics
            ],
            "cost_breakdown": {
                "token_cost_usd": getattr(metrics, "token_cost_usd", 0.0),
                "external_cost_usd": getattr(metrics, "external_cost_usd", 0.0),
                "external_service_costs": getattr(metrics, "external_service_costs", {}),
                "api_call_logs": getattr(metrics, "api_call_logs", [])
            }
        }
        
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, indent=2)
        
        print(f"📊 Detailed metrics saved to: {metrics_file}")
        return metrics_file


def create_academic_summary(metrics_file: str, output_dir: str):
    """Create academic summary for supervisor presentation"""
    
    with open(metrics_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Backward compatibility: support raw dataclass JSON (no memo_info block)
    if 'memo_info' not in data:
        total_tokens = sum(data.get('token_usage', {}).values()) if data.get('token_usage') else 0
        data = {
            "memo_info": {
                "pdf_name": Path(metrics_file).stem,
                "generation_timestamp": data.get('generation_time_seconds'),
                "total_runtime_seconds": data.get('generation_time_seconds', 0.0),
                "total_cost_usd": data.get('total_cost_usd', 0.0),
                "token_cost_usd": data.get('token_cost_usd', 0.0),
                "external_cost_usd": data.get('external_cost_usd', 0.0),
                "total_tokens": total_tokens,
                "section_count": data.get('section_count', 0)
            },
            "quality_metrics": {
                "all_sections_present": data.get('all_sections_present', False),
                "missing_sections": data.get('missing_sections', []),
                "flesch_kincaid_score": data.get('flesch_kincaid_score', 0.0),
                "overall_quality_score": data.get('overall_quality_score', None),
                "quality_breakdown": data.get('quality_breakdown', []),
                "chart_present": data.get('chart_present', False),
                "duplicate_ratio": data.get('duplicate_ratio', 0.0)
            },
            "performance_metrics": {
                "token_usage_by_model": data.get('token_usage', {}),
                "timing_table": data.get('timing_table', {}),
                "system": {
                    "cpu_usage_percent": data.get('cpu_usage_percent', 0.0),
                    "gpu_usage_percent": data.get('gpu_usage_percent', 0.0),
                    "memory_usage_mb": data.get('memory_usage_mb', 0.0),
                    "system_robustness_score": data.get('system_robustness_score', 0.0)
                }
            },
            "section_metrics": data.get('section_metrics', []),
            "cost_breakdown": {
                "token_cost_usd": data.get('token_cost_usd', 0.0),
                "external_cost_usd": data.get('external_cost_usd', 0.0),
                "external_service_costs": data.get('external_service_costs', {}),
                "api_call_logs": data.get('api_call_logs', [])
            }
        }
    
    summary_file = f"{output_dir}/academic_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    summary = f"""## Key Performance Snapshot

- **Generation Time (minutes)**: {data['memo_info']['total_runtime_seconds']/60:.2f}
- **Total Cost (USD)**: ${data['memo_info']['total_cost_usd']:.4f}
- **Token Cost (USD)**: ${data['memo_info'].get('token_cost_usd', 0.0):.4f}
- **External Cost (USD)**: ${data['memo_info'].get('external_cost_usd', 0.0):.4f}
- **All Sections Present**: {data['quality_metrics']['all_sections_present']}
- **Flesch–Kincaid Grade**: {data['quality_metrics']['flesch_kincaid_score']:.1f}
- **Overall Quality Score (/10)**: {data['quality_metrics'].get('overall_quality_score', 'N/A')}

## Section-by-Section Analysis

| Section | AI Time (min) | Cost (USD) |
|---------|---------------|------------|
"""
    
    for section in data['section_metrics']:
        # Handle both object and string representations
        if isinstance(section, str):
            # Parse string representation like "SectionMetrics(section_name='...', runtime_seconds=0.0, ...)"
            import re
            section_name_match = re.search(r"section_name='([^']*)'", section)
            runtime_match = re.search(r"runtime_seconds=([0-9.]+)", section)
            cost_match = re.search(r"cost_usd=([0-9.]+)", section)
            
            section_name = section_name_match.group(1) if section_name_match else "Unknown"
            runtime_seconds = float(runtime_match.group(1)) if runtime_match else 0.0
            cost_usd = float(cost_match.group(1)) if cost_match else 0.0
        else:
            # Handle object representation
            section_name = section.section_name
            runtime_seconds = section.runtime_seconds
            cost_usd = section.cost_usd
            
        summary += f"| {section_name} | {runtime_seconds/60:.1f} | ${cost_usd:.4f} |\n"
    
    # Optional: show per-service external costs
    if 'cost_breakdown' in data:
        services = data['cost_breakdown'].get('external_service_costs', {}) or {}
        if services:
            summary += "\n### External Service Costs\n"
            for svc, amt in services.items():
                summary += f"- {svc}: ${amt:.4f}\n"

    summary += f"\n---\nGenerated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    print(f"📚 Academic summary saved to: {summary_file}")
    return summary_file


# Example usage for integration with existing pipeline
def integrate_with_main_pipeline():
    """Example of how to integrate with existing main.py pipeline"""
    
    # Initialize tracker
    tracker = MemoGenerationTracker()
    
    # Example section tracking (you would add these to your existing pipeline)
    tracker.start_section("DETAILED SUMMARY")
    # ... your existing detailed summary generation code ...
    tracker.end_section("DETAILED SUMMARY", tokens_used=500, model="gpt-4o")
    
    tracker.start_section("MARKET SIZE & ANALYSIS")
    # ... your existing market analysis code ...
    tracker.end_section("MARKET SIZE & ANALYSIS", tokens_used=800, model="gpt-4")
    
    # Continue for all sections...
    
    # After memo generation, evaluate
    memo_text = "..."  # Your generated memo text
    metrics = tracker.evaluate_memo(memo_text)
    
    # Save detailed metrics
    metrics_file = tracker.save_metrics(metrics, "evaluation_results", "sample_company")
    
    # Generate academic summary
    summary_file = create_academic_summary(metrics_file, "evaluation_results")
    
    # Print key results for supervisor
    print(f"\n🎯 KEY RESULTS FOR SUPERVISOR:")
    print(f"⏰ Time Savings: {metrics.traditional_vc_comparison['time_savings_percentage']:.1f}%")
    print(f"💰 Cost Savings: {metrics.traditional_vc_comparison['cost_savings_percentage']:.1f}%")
    print(f"📊 Quality Score: {tracker.evaluator._calculate_overall_score(metrics):.1f}/10")
    print(f"📈 Efficiency: {metrics.traditional_vc_comparison['efficiency_improvement']['time_efficiency']:.1f}x faster")


if __name__ == "__main__":
    # Example usage
    integrate_with_main_pipeline() 