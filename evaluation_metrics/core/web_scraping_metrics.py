"""
Web Scraping Evaluation Metrics
Tracks automated metrics for web scraping performance
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ScraperMetrics:
    """Individual scraper performance metrics"""
    scraper_name: str
    success_rate: float  # Percentage of successful runs
    average_response_time: float  # Average time per request
    total_requests: int  # Total requests made
    successful_requests: int  # Successful requests
    failed_requests: int  # Failed requests
    rate_limit_hits: int  # Number of rate limit encounters
    parsing_errors: int  # Number of parsing errors
    data_quality_score: float  # 0-1 score of extracted data quality

@dataclass
class WebScrapingEvaluationMetrics:
    """Container for all web scraping evaluation metrics"""
    
    # Overall scraper performance
    overall_success_rate: float  # Combined success rate across all scrapers
    total_scrapers: int  # Number of active scrapers
    total_requests: int  # Total requests across all scrapers
    total_successful: int  # Total successful requests
    total_failed: int  # Total failed requests
    
    # Performance metrics
    average_response_time: float  # Average response time across all scrapers
    fastest_scraper: str  # Name of fastest scraper
    slowest_scraper: str  # Name of slowest scraper
    
    # Data quality metrics
    overall_data_quality: float  # Average data quality score
    source_coverage: float  # Percentage of target sources covered
    parsing_accuracy: float  # Percentage of successfully parsed data
    
    # Error tracking
    rate_limit_encounters: int  # Total rate limit hits
    parsing_errors: int  # Total parsing errors
    network_errors: int  # Total network errors
    authentication_errors: int  # Total auth errors
    
    # Individual scraper metrics
    scraper_metrics: List[ScraperMetrics]
    
    # Timestamp
    evaluation_timestamp: str

class WebScrapingEvaluator:
    """Evaluates web scraping performance and data quality"""
    
    def __init__(self):
        self.scrapers = {
            "crunchbase": "scripts/download_crunchbase.py",
            "pitchbook": "scripts/download_pitchbook.py", 
            "beauhurst": "scripts/download_beauhurst.py",
            "perplexity": "core/perplexity_utils.py",
            "coresignal": "core/coresignal_utils.py"
        }
        self.start_time = None
        self.scraper_logs = {}
    
    def start_evaluation(self):
        """Start timing the scraping evaluation"""
        self.start_time = time.time()
        self.scraper_logs = {}
    
    def log_scraper_start(self, scraper_name: str):
        """Log the start of a scraper run"""
        if scraper_name not in self.scraper_logs:
            self.scraper_logs[scraper_name] = {
                "start_time": time.time(),
                "requests": 0,
                "successful": 0,
                "failed": 0,
                "rate_limits": 0,
                "parsing_errors": 0,
                "network_errors": 0,
                "auth_errors": 0
            }
    
    def log_scraper_request(self, scraper_name: str, success: bool, response_time: float = None):
        """Log individual scraper request results"""
        if scraper_name in self.scraper_logs:
            self.scraper_logs[scraper_name]["requests"] += 1
            if success:
                self.scraper_logs[scraper_name]["successful"] += 1
            else:
                self.scraper_logs[scraper_name]["failed"] += 1
    
    def log_scraper_error(self, scraper_name: str, error_type: str):
        """Log specific scraper errors"""
        if scraper_name in self.scraper_logs:
            if error_type == "rate_limit":
                self.scraper_logs[scraper_name]["rate_limits"] += 1
            elif error_type == "parsing":
                self.scraper_logs[scraper_name]["parsing_errors"] += 1
            elif error_type == "network":
                self.scraper_logs[scraper_name]["network_errors"] += 1
            elif error_type == "auth":
                self.scraper_logs[scraper_name]["auth_errors"] += 1
    
    def evaluate_scraping_performance(self) -> WebScrapingEvaluationMetrics:
        """Evaluate overall scraping performance"""
        
        # Calculate overall metrics
        total_requests = sum(log["requests"] for log in self.scraper_logs.values())
        total_successful = sum(log["successful"] for log in self.scraper_logs.values())
        total_failed = sum(log["failed"] for log in self.scraper_logs.values())
        
        overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate individual scraper metrics
        scraper_metrics = []
        total_rate_limits = 0
        total_parsing_errors = 0
        total_network_errors = 0
        total_auth_errors = 0
        
        for scraper_name, log in self.scraper_logs.items():
            success_rate = (log["successful"] / log["requests"] * 100) if log["requests"] > 0 else 0
            
            # Calculate data quality score (simplified)
            data_quality_score = min(1.0, success_rate / 100)
            
            scraper_metric = ScraperMetrics(
                scraper_name=scraper_name,
                success_rate=success_rate,
                average_response_time=0.0,  # Would need actual timing data
                total_requests=log["requests"],
                successful_requests=log["successful"],
                failed_requests=log["failed"],
                rate_limit_hits=log["rate_limits"],
                parsing_errors=log["parsing_errors"],
                data_quality_score=data_quality_score
            )
            scraper_metrics.append(scraper_metric)
            
            total_rate_limits += log["rate_limits"]
            total_parsing_errors += log["parsing_errors"]
            total_network_errors += log["network_errors"]
            total_auth_errors += log["auth_errors"]
        
        # Calculate source coverage (simplified)
        source_coverage = min(100.0, (len([s for s in scraper_metrics if s.success_rate > 0]) / len(self.scrapers)) * 100)
        
        # Calculate parsing accuracy (simplified)
        parsing_accuracy = min(100.0, ((total_successful - total_parsing_errors) / total_successful * 100) if total_successful > 0 else 0)
        
        return WebScrapingEvaluationMetrics(
            overall_success_rate=overall_success_rate,
            total_scrapers=len(self.scrapers),
            total_requests=total_requests,
            total_successful=total_successful,
            total_failed=total_failed,
            average_response_time=0.0,  # Would need actual timing data
            fastest_scraper="unknown",
            slowest_scraper="unknown",
            overall_data_quality=sum(s.data_quality_score for s in scraper_metrics) / len(scraper_metrics) if scraper_metrics else 0,
            source_coverage=source_coverage,
            parsing_accuracy=parsing_accuracy,
            rate_limit_encounters=total_rate_limits,
            parsing_errors=total_parsing_errors,
            network_errors=total_network_errors,
            authentication_errors=total_auth_errors,
            scraper_metrics=scraper_metrics,
            evaluation_timestamp=datetime.now().isoformat()
        )
    
    def generate_scraping_report(self, metrics: WebScrapingEvaluationMetrics) -> str:
        """Generate comprehensive scraping evaluation report"""
        report = f"""
WEB SCRAPING EVALUATION REPORT
==============================

OVERALL PERFORMANCE
------------------
✅ Overall Success Rate: {metrics.overall_success_rate:.1f}%
📊 Total Requests: {metrics.total_requests:,}
✅ Successful Requests: {metrics.total_successful:,}
❌ Failed Requests: {metrics.total_failed:,}
🕷️ Active Scrapers: {metrics.total_scrapers}

DATA QUALITY
------------
📈 Overall Data Quality: {metrics.overall_data_quality:.1f}/1.0
🌐 Source Coverage: {metrics.source_coverage:.1f}%
🔍 Parsing Accuracy: {metrics.parsing_accuracy:.1f}%

ERROR ANALYSIS
--------------
🚫 Rate Limit Encounters: {metrics.rate_limit_encounters}
🔧 Parsing Errors: {metrics.parsing_errors}
🌐 Network Errors: {metrics.network_errors}
🔐 Authentication Errors: {metrics.authentication_errors}

INDIVIDUAL SCRAPER PERFORMANCE
------------------------------
"""
        
        for scraper in metrics.scraper_metrics:
            report += f"""
{scraper.scraper_name.upper()}:
  Success Rate: {scraper.success_rate:.1f}%
  Requests: {scraper.total_requests:,}
  Successful: {scraper.successful_requests:,}
  Failed: {scraper.failed_requests:,}
  Rate Limits: {scraper.rate_limit_hits}
  Parsing Errors: {scraper.parsing_errors}
  Data Quality: {scraper.data_quality_score:.1f}/1.0
"""
        
        return report
    
    def save_metrics(self, metrics: WebScrapingEvaluationMetrics, output_dir: str):
        """Save scraping metrics to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = os.path.join(output_dir, f"web_scraping_metrics_{timestamp}.json")
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics.__dict__, f, indent=2, default=str)
        
        return metrics_file 