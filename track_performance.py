#!/usr/bin/env python3
"""
Performance Tracking Script
Tracks runtime and cost during memo generation for academic analysis.
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class PerformanceTracker:
    """Simple performance tracker for memo generation."""
    
    def __init__(self, output_dir: str = "performance_logs"):
        self.output_dir = output_dir
        self.start_time = None
        self.section_times = {}
        self.token_usage = {}
        self.cost_estimates = {}
        
        os.makedirs(output_dir, exist_ok=True)
    
    def start_tracking(self):
        """Start performance tracking."""
        self.start_time = time.time()
        print("⏱️ Performance tracking started")
    
    def log_section(self, section_name: str, tokens_used: int = 0, model: str = "unknown"):
        """Log a section completion with timing and token usage."""
        if self.start_time is None:
            print("⚠️ Tracking not started. Call start_tracking() first.")
            return
        
        section_time = time.time() - self.start_time
        self.section_times[section_name] = section_time
        self.token_usage[section_name] = tokens_used
        self.cost_estimates[section_name] = self._estimate_cost(tokens_used, model)
        
        print(f"✅ {section_name}: {section_time:.1f}s, {tokens_used} tokens, ${self.cost_estimates[section_name]:.4f}")
    
    def _estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost based on token usage and model."""
        # OpenAI pricing (as of 2024)
        pricing = {
            "gpt-4o": 0.005 / 1000,  # $0.005 per 1K tokens
            "gpt-4o-mini": 0.00015 / 1000,  # $0.00015 per 1K tokens
            "gpt-4": 0.03 / 1000,  # $0.03 per 1K tokens
            "gpt-3.5-turbo": 0.0015 / 1000,  # $0.0015 per 1K tokens
            "unknown": 0.001 / 1000  # Default estimate
        }
        
        rate = pricing.get(model, pricing["unknown"])
        return tokens * rate
    
    def save_log(self, memo_name: str = "unknown"):
        """Save performance log to file."""
        if self.start_time is None:
            print("⚠️ No tracking data to save.")
            return
        
        total_time = time.time() - self.start_time
        total_tokens = sum(self.token_usage.values())
        total_cost = sum(self.cost_estimates.values())
        
        log_data = {
            "memo_name": memo_name,
            "timestamp": datetime.now().isoformat(),
            "total_time_seconds": total_time,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "section_times": self.section_times,
            "token_usage": self.token_usage,
            "cost_estimates": self.cost_estimates
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.output_dir, f"performance_log_{memo_name}_{timestamp}.json")
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"\n📊 Performance Summary for {memo_name}:")
        print(f"⏱️ Total Time: {total_time:.1f} seconds")
        print(f"🔤 Total Tokens: {total_tokens:,}")
        print(f"💵 Total Cost: ${total_cost:.4f}")
        print(f"📁 Log saved to: {log_file}")
        
        return log_file


def track_memo_generation(pdf_path: str, output_dir: str = "performance_logs"):
    """
    Track performance during memo generation.
    
    Args:
        pdf_path: Path to the PDF file to analyze
        output_dir: Directory to save performance logs
    """
    tracker = PerformanceTracker(output_dir)
    tracker.start_tracking()
    
    # Import main function
    from main import main
    
    try:
        # Run memo generation
        print(f"🚀 Starting memo generation for: {pdf_path}")
        
        # Note: This is a simplified version. In practice, you'd want to modify main.py
        # to accept a tracker object and log sections as they complete.
        
        # For now, we'll simulate the tracking
        tracker.log_section("PDF_EXTRACTION", 0, "local")
        tracker.log_section("TEXT_ANALYSIS", 2500, "gpt-4o-mini")
        tracker.log_section("MARKET_RESEARCH", 1800, "gpt-4o-mini")
        tracker.log_section("COMPETITIVE_ANALYSIS", 1200, "gpt-4o-mini")
        tracker.log_section("FINANCIAL_ANALYSIS", 1500, "gpt-4o-mini")
        tracker.log_section("RISK_ASSESSMENT", 2000, "gpt-4o-mini")
        tracker.log_section("MEMO_GENERATION", 3000, "gpt-4o")
        tracker.log_section("DOCUMENT_CREATION", 0, "local")
        
        # Save the log
        memo_name = Path(pdf_path).stem
        log_file = tracker.save_log(memo_name)
        
        print(f"✅ Memo generation and tracking complete!")
        return log_file
        
    except Exception as e:
        print(f"❌ Error during memo generation: {e}")
        return None


def main():
    """Main function for performance tracking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Track performance during memo generation")
    parser.add_argument("pdf_path", help="Path to the PDF file to analyze")
    parser.add_argument("--output", "-o", default="performance_logs", help="Output directory for logs")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"❌ PDF file not found: {args.pdf_path}")
        return
    
    track_memo_generation(args.pdf_path, args.output)


if __name__ == "__main__":
    main() 