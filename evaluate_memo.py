#!/usr/bin/env python3
"""
Memo Evaluation Script
Analyzes generated investment memos and provides academic metrics and comparisons.
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Import evaluation components
from evaluation_metrics import MemoEvaluationMetrics, MemoEvaluator
from integrate_evaluation import create_academic_summary


def evaluate_memo_file(memo_file_path: str, output_dir: str = "evaluation_results") -> Dict[str, Any]:
    """
    Evaluate a single memo file and generate metrics.
    
    Args:
        memo_file_path: Path to the memo file (PDF, DOCX, or TXT)
        output_dir: Directory to save evaluation results
    
    Returns:
        Dictionary containing evaluation results
    """
    print(f"🔍 Evaluating memo: {memo_file_path}")
    
    # Initialize evaluator
    evaluator = MemoEvaluator()
    
    # Read memo content
    memo_content = read_memo_content(memo_file_path)
    if not memo_content:
        print(f"❌ Could not read memo content from {memo_file_path}")
        return {}
    
    # Evaluate the memo
    metrics = evaluator.evaluate_memo(memo_content)
    
    # Save detailed metrics
    os.makedirs(output_dir, exist_ok=True)
    pdf_name = Path(memo_file_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics_file = os.path.join(output_dir, f"detailed_metrics_{pdf_name}_{timestamp}.json")
    
    # Save metrics to JSON
    with open(metrics_file, 'w') as f:
        json.dump(metrics.__dict__, f, indent=2, default=str)
    
    # Generate academic summary
    summary_file = create_academic_summary(metrics_file, output_dir)
    
    # Print key results
    print(f"\n🎯 EVALUATION RESULTS FOR {pdf_name.upper()}:")
    print(f"⏰ Time Savings: {metrics.traditional_vc_comparison['time_savings_percentage']:.1f}%")
    print(f"💰 Cost Savings: {metrics.traditional_vc_comparison['cost_savings_percentage']:.1f}%")
    print(f"📊 Quality Score: {evaluator._calculate_overall_score(metrics):.1f}/10")
    print(f"📈 Efficiency: {metrics.traditional_vc_comparison['efficiency_improvement']['time_efficiency']:.1f}x faster")
    print(f"📋 Sections: {metrics.section_count}/17 present")
    print(f"💵 Total Cost: ${metrics.total_cost_usd:.4f}")
    print(f"⏱️ Total Time: {metrics.generation_time_seconds:.1f} seconds")
    
    print(f"\n📊 Detailed metrics saved to: {metrics_file}")
    print(f"📚 Academic summary saved to: {summary_file}")
    
    return {
        'metrics': metrics.__dict__,
        'metrics_file': metrics_file,
        'summary_file': summary_file,
        'quality_score': evaluator._calculate_overall_score(metrics)
    }


def read_memo_content(file_path: str) -> Optional[str]:
    """
    Read memo content from various file formats.
    
    Args:
        file_path: Path to the memo file
    
    Returns:
        Memo content as string, or None if failed
    """
    file_path = Path(file_path)
    
    if file_path.suffix.lower() == '.txt':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading TXT file: {e}")
            return None
    
    elif file_path.suffix.lower() == '.docx':
        try:
            from docx import Document
            doc = Document(file_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            print(f"Error reading DOCX file: {e}")
            return None
    
    elif file_path.suffix.lower() == '.pdf':
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            print(f"Error reading PDF file: {e}")
            return None
    
    else:
        print(f"Unsupported file format: {file_path.suffix}")
        return None


def evaluate_all_memos(input_dir: str = "out", output_dir: str = "evaluation_results") -> Dict[str, Any]:
    """
    Evaluate all memo files in a directory.
    
    Args:
        input_dir: Directory containing memo files
        output_dir: Directory to save evaluation results
    
    Returns:
        Dictionary containing evaluation results for all memos
    """
    print(f"🔍 Evaluating all memos in: {input_dir}")
    
    results = {}
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"❌ Input directory does not exist: {input_dir}")
        return results
    
    # Find all memo files
    memo_files = []
    for ext in ['*.pdf', '*.docx', '*.txt']:
        memo_files.extend(input_path.glob(ext))
    
    if not memo_files:
        print(f"❌ No memo files found in {input_dir}")
        return results
    
    print(f"📋 Found {len(memo_files)} memo files to evaluate")
    
    # Evaluate each memo
    for memo_file in memo_files:
        try:
            result = evaluate_memo_file(str(memo_file), output_dir)
            if result:
                results[memo_file.stem] = result
        except Exception as e:
            print(f"❌ Error evaluating {memo_file}: {e}")
    
    # Generate summary report
    if results:
        generate_summary_report(results, output_dir)
    
    return results


def generate_summary_report(results: Dict[str, Any], output_dir: str):
    """
    Generate a summary report comparing all evaluated memos.
    
    Args:
        results: Dictionary of evaluation results
        output_dir: Directory to save the summary report
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = os.path.join(output_dir, f"comparative_analysis_{timestamp}.md")
    
    with open(summary_file, 'w') as f:
        f.write("# Comparative Memo Analysis Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Summary Statistics\n\n")
        
        # Calculate averages
        quality_scores = [r['quality_score'] for r in results.values()]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        f.write(f"- **Average Quality Score**: {avg_quality:.1f}/10\n")
        f.write(f"- **Number of Memos Evaluated**: {len(results)}\n")
        f.write(f"- **Best Quality Score**: {max(quality_scores):.1f}/10\n")
        f.write(f"- **Worst Quality Score**: {min(quality_scores):.1f}/10\n\n")
        
        f.write("## Individual Memo Results\n\n")
        
        for memo_name, result in results.items():
            metrics = result['metrics']
            f.write(f"### {memo_name}\n\n")
            f.write(f"- **Quality Score**: {result['quality_score']:.1f}/10\n")
            f.write(f"- **Sections Present**: {metrics['section_count']}/17\n")
            f.write(f"- **Time Savings**: {metrics['traditional_vc_comparison']['time_savings_percentage']:.1f}%\n")
            f.write(f"- **Cost Savings**: {metrics['traditional_vc_comparison']['cost_savings_percentage']:.1f}%\n")
            f.write(f"- **Total Cost**: ${metrics['total_cost_usd']:.4f}\n")
            f.write(f"- **Generation Time**: {metrics['generation_time_seconds']:.1f} seconds\n\n")
    
    print(f"📊 Comparative analysis saved to: {summary_file}")


def main():
    """Main function to run memo evaluation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate investment memos and generate academic metrics")
    parser.add_argument("--input", "-i", default="out", help="Input directory or file path")
    parser.add_argument("--output", "-o", default="evaluation_results", help="Output directory for results")
    parser.add_argument("--single", "-s", action="store_true", help="Evaluate a single file instead of directory")
    
    args = parser.parse_args()
    
    if args.single:
        # Evaluate single file
        if not os.path.exists(args.input):
            print(f"❌ File not found: {args.input}")
            return
        
        evaluate_memo_file(args.input, args.output)
    else:
        # Evaluate all files in directory
        evaluate_all_memos(args.input, args.output)


if __name__ == "__main__":
    main() 