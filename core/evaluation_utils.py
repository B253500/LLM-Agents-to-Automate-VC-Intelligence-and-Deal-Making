"""
Evaluation utilities for investment memo generation.
Extracted from main.py to improve code organization.
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional


def generate_excel_output(metrics, company_name: str, timestamp: str, output_dir: str) -> Optional[str]:
    """Generate comprehensive Excel analysis"""
    try:
        excel_file = os.path.join(output_dir, f"memo_evaluation_{company_name}_{timestamp}.xlsx")
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            
            # Summary sheet
            summary_data = {
                "Metric": [
                    "Company Name",
                    "Generation Time (minutes)",
                    "Total Tokens",
                    "Total Cost (USD)",
                    "Overall Quality Score (/10)",
                    "Token Cost (USD)",
                    "External Cost (USD)",
                    "Sections Present",
                    "Readability Score"
                ],
                "Value": [
                    company_name,
                    f"{metrics.generation_time_seconds / 60:.2f}",
                    f"{sum(metrics.token_usage.values()):,}",
                    f"${metrics.total_cost_usd:.4f}",
                    f"{getattr(metrics, 'overall_quality_score', 0.0):.1f}",
                    f"${getattr(metrics, 'token_cost_usd', 0.0):.4f}",
                    f"${getattr(metrics, 'external_cost_usd', 0.0):.4f}",
                    f"{metrics.section_count}/17",
                    f"{metrics.flesch_kincaid_score:.1f}"
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            
            # Cost breakdown sheet
            cost_data = {
                "Metric": [
                    "Total Cost (USD)",
                    "Token Cost (USD)",
                    "External Cost (USD)"
                ],
                "Value": [
                    getattr(metrics, 'total_cost_usd', 0.0),
                    getattr(metrics, 'token_cost_usd', 0.0),
                    getattr(metrics, 'external_cost_usd', 0.0)
                ]
            }

            cost_df = pd.DataFrame(cost_data)
            cost_df.to_excel(writer, sheet_name="Cost Breakdown", index=False)
            
            # Performance metrics sheet
            performance_data = {
                "Metric": [
                    "Total Generation Time (seconds)",
                    "Total Generation Time (minutes)",
                    "Total Tokens Used",
                    "Total Cost (USD)",
                    "CPU Usage (%)",
                    "GPU Usage (%)",
                    "Memory Usage (MB)",
                    "Section Completeness",
                    "Duplicate Content Ratio",
                    "Unknown Coverage Ratio"
                ],
                "Value": [
                    metrics.generation_time_seconds,
                    metrics.generation_time_seconds / 60,
                    sum(metrics.token_usage.values()),
                    metrics.total_cost_usd,
                    metrics.cpu_usage_percent,
                    metrics.gpu_usage_percent,
                    metrics.memory_usage_mb,
                    "Complete" if metrics.all_sections_present else "Incomplete",
                    f"{metrics.duplicate_ratio:.2%}",
                    f"{metrics.unknown_coverage_ratio:.2%}"
                ]
            }
            
            performance_df = pd.DataFrame(performance_data)
            performance_df.to_excel(writer, sheet_name="Performance Metrics", index=False)
        
        return excel_file
        
    except Exception as e:
        print(f"❌ Error generating Excel output: {e}")
        return None


def save_evaluation_metrics(metrics, pdf_name: str, evaluation_dir: str) -> str:
    """Save detailed metrics for academic analysis."""
    os.makedirs(evaluation_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics_file = os.path.join(evaluation_dir, f"detailed_metrics_{pdf_name}_{timestamp}.json")
    
    # Saving metrics to JSON
    with open(metrics_file, 'w') as f:
        json.dump(metrics.__dict__, f, indent=2, default=str)
    
    return metrics_file


def print_evaluation_summary(metrics, evaluator, metrics_file: str, summary_file: str):
    """Print evaluation summary to console."""
    print(f"\n🎯 KEY RESULTS:")
    print(f"⏰ Time Savings: {metrics.traditional_vc_comparison['time_savings_percentage']:.1f}%")
    print(f"💰 Cost Savings: {metrics.traditional_vc_comparison['cost_savings_percentage']:.1f}%")
    print(f"📊 Quality Score: {evaluator._calculate_overall_score(metrics):.1f}/10")
    print(f"📈 Efficiency: {metrics.traditional_vc_comparison['efficiency_improvement']['time_efficiency']:.1f}x faster")
    print(f"📋 Sections: {metrics.section_count}/17 present")
    print(f"💵 Total Cost: ${metrics.total_cost_usd:.4f}")
    print(f"⏱️ Total Time: {metrics.generation_time_seconds:.1f} seconds")
    print(f"🖥️ CPU Usage: {metrics.cpu_usage_percent:.1f}%")
    print(f"🎮 GPU Usage: {metrics.gpu_usage_percent:.1f}%")
    print(f"💾 Memory Usage: {metrics.memory_usage_mb:.1f} MB")
    
    print(f"\n📊 Detailed metrics saved to: {metrics_file}")
    print(f"📚 Academic summary saved to: {summary_file}") 