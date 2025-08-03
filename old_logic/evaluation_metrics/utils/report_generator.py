#!/usr/bin/env python3
"""
Utility functions for generating evaluation reports
"""

import json
import pandas as pd
from typing import Dict, Any
from datetime import datetime

def generate_summary_report(metrics: Dict[str, Any]) -> str:
    """Generate a summary report from metrics"""
    
    report = f"""# Evaluation Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Key Metrics
- **Quality Score**: {metrics.get('quality_score', 'N/A')}
- **Generation Time**: {metrics.get('generation_time_seconds', 'N/A')} seconds
- **Cost**: ${metrics.get('cost_usd', 'N/A')}
- **Token Usage**: {metrics.get('token_usage', 'N/A')}

## Performance Analysis
- **Time Efficiency**: {metrics.get('time_efficiency', 'N/A')}x faster than traditional VC
- **Cost Savings**: {metrics.get('cost_savings_percentage', 'N/A')}% savings
- **Quality Assessment**: {metrics.get('quality_assessment', 'N/A')}

## Recommendations
Based on the evaluation results, consider the following improvements:
1. Optimize generation time if above 54,000 seconds (15 hours)
2. Reduce costs if above $2,250 per memo
3. Improve quality if score is below 7.0
"""
    
    return report

def export_to_excel(metrics: Dict[str, Any], output_file: str):
    """Export metrics to Excel format"""
    
    # Create DataFrame from metrics
    df = pd.DataFrame([metrics])
    
    # Save to Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Metrics', index=False)
    
    print(f"✅ Exported metrics to: {output_file}")

if __name__ == "__main__":
    print("Report generator utility loaded")
