"""
Integration script to add evaluation metrics to web scraping system
"""

import sys
import os
import time
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path to import evaluation metrics
sys.path.append(str(Path(__file__).parent.parent))

from evaluation_metrics.core.web_scraping_metrics import WebScrapingMetrics

class ScrapingMetricsIntegration:
    """Integrates evaluation metrics with existing web scraping system"""
    
    def __init__(self):
        self.metrics = WebScrapingMetrics()
        self.current_session = None
        
    def start_scraping_session(self, scraper_name: str):
        """Start tracking a new scraping session"""
        self.current_session = {
            'scraper_name': scraper_name,
            'start_time': time.time(),
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limit_hits': 0,
            'parsing_errors': 0,
            'data_extracted': 0
        }
        print(f"[Metrics] Started tracking session for {scraper_name}")
        
    def log_request(self, success: bool, response_time: float = None, error_type: str = None):
        """Log a single request attempt"""
        if not self.current_session:
            return
            
        self.current_session['requests_made'] += 1
        
        if success:
            self.current_session['successful_requests'] += 1
        else:
            self.current_session['failed_requests'] += 1
            
        if error_type:
            if 'rate_limit' in error_type.lower():
                self.current_session['rate_limit_hits'] += 1
            elif 'parsing' in error_type.lower():
                self.current_session['parsing_errors'] += 1
                
        if response_time:
            if 'response_times' not in self.current_session:
                self.current_session['response_times'] = []
            self.current_session['response_times'].append(response_time)
            
    def log_data_extraction(self, data_quality_score: float = None):
        """Log successful data extraction"""
        if not self.current_session:
            return
            
        self.current_session['data_extracted'] += 1
        
        if data_quality_score:
            if 'data_quality_scores' not in self.current_session:
                self.current_session['data_quality_scores'] = []
            self.current_session['data_quality_scores'].append(data_quality_score)
            
    def end_scraping_session(self):
        """End current session and save metrics"""
        if not self.current_session:
            return
            
        session_time = time.time() - self.current_session['start_time']
        
        # Calculate metrics
        success_rate = (self.current_session['successful_requests'] / 
                       max(self.current_session['requests_made'], 1)) * 100
        
        avg_response_time = 0
        if 'response_times' in self.current_session and self.current_session['response_times']:
            avg_response_time = sum(self.current_session['response_times']) / len(self.current_session['response_times'])
            
        data_quality_score = 0
        if 'data_quality_scores' in self.current_session and self.current_session['data_quality_scores']:
            data_quality_score = sum(self.current_session['data_quality_scores']) / len(self.current_session['data_quality_scores'])
            
        # Create metrics object
        scraper_metrics = {
            'scraper_name': self.current_session['scraper_name'],
            'success_rate': success_rate,
            'average_response_time': avg_response_time,
            'total_requests': self.current_session['requests_made'],
            'successful_requests': self.current_session['successful_requests'],
            'failed_requests': self.current_session['failed_requests'],
            'rate_limit_hits': self.current_session['rate_limit_hits'],
            'parsing_errors': self.current_session['parsing_errors'],
            'data_quality_score': data_quality_score,
            'session_duration': session_time,
            'data_extracted': self.current_session['data_extracted']
        }
        
        # Save to metrics system
        self.metrics.add_scraper_metrics(scraper_metrics)
        
        # Print summary
        print(f"\n[Metrics] Session Summary for {self.current_session['scraper_name']}:")
        print(f"  ✅ Success Rate: {success_rate:.1f}%")
        print(f"  ⏱️  Avg Response Time: {avg_response_time:.2f}s")
        print(f"  📊 Data Quality Score: {data_quality_score:.2f}/1.0")
        print(f"  🔄 Total Requests: {self.current_session['requests_made']}")
        print(f"  ❌ Failed Requests: {self.current_session['failed_requests']}")
        print(f"  ⏰ Session Duration: {session_time:.1f}s")
        
        # Reset session
        self.current_session = None
        
    def get_overall_metrics(self):
        """Get overall scraping performance metrics"""
        return self.metrics.get_overall_metrics()
        
    def save_metrics_report(self, output_dir: str = None):
        """Save detailed metrics report"""
        if output_dir is None:
            output_dir = Path(__file__).parent / "results"
            
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed metrics
        detailed_file = os.path.join(output_dir, f"scraping_metrics_{timestamp}.json")
        self.metrics.save_detailed_metrics(detailed_file)
        
        # Generate summary report
        summary_file = os.path.join(output_dir, f"scraping_summary_{timestamp}.txt")
        self.metrics.generate_summary_report(summary_file)
        
        print(f"\n[Metrics] Reports saved:")
        print(f"  📊 Detailed metrics: {detailed_file}")
        print(f"  📋 Summary report: {summary_file}")
        
        return detailed_file, summary_file


# Integration functions for existing scraping scripts
def integrate_with_download_reports():
    """Integration function for download_reports.py"""
    
    # Import the original functions
    from download_reports import (
        scrape_and_download_crunchbase,
        scrape_and_download_beauhurst, 
        scrape_and_download_pitchbook
    )
    
    metrics = ScrapingMetricsIntegration()
    
    def tracked_scrape_crunchbase(page):
        """Tracked version of Crunchbase scraping"""
        metrics.start_scraping_session("Crunchbase")
        try:
            result = scrape_and_download_crunchbase(page)
            metrics.log_data_extraction(data_quality_score=0.8)  # Estimate
            return result
        except Exception as e:
            metrics.log_request(False, error_type=str(e))
            raise
        finally:
            metrics.end_scraping_session()
    
    def tracked_scrape_beauhurst(page, max_pages=10):
        """Tracked version of Beauhurst scraping"""
        metrics.start_scraping_session("Beauhurst")
        try:
            result = scrape_and_download_beauhurst(page, max_pages)
            metrics.log_data_extraction(data_quality_score=0.9)  # Estimate
            return result
        except Exception as e:
            metrics.log_request(False, error_type=str(e))
            raise
        finally:
            metrics.end_scraping_session()
    
    def tracked_scrape_pitchbook(page):
        """Tracked version of PitchBook scraping"""
        metrics.start_scraping_session("PitchBook")
        try:
            result = scrape_and_download_pitchbook(page)
            metrics.log_data_extraction(data_quality_score=0.85)  # Estimate
            return result
        except Exception as e:
            metrics.log_request(False, error_type=str(e))
            raise
        finally:
            metrics.end_scraping_session()
    
    return metrics, tracked_scrape_crunchbase, tracked_scrape_beauhurst, tracked_scrape_pitchbook


if __name__ == "__main__":
    # Example usage
    metrics = ScrapingMetricsIntegration()
    
    # Simulate a scraping session
    metrics.start_scraping_session("TestScraper")
    
    # Log some requests
    metrics.log_request(True, response_time=1.2)
    metrics.log_request(True, response_time=0.8)
    metrics.log_request(False, error_type="rate_limit")
    metrics.log_request(True, response_time=1.5)
    
    # Log data extraction
    metrics.log_data_extraction(data_quality_score=0.9)
    metrics.log_data_extraction(data_quality_score=0.8)
    
    # End session
    metrics.end_scraping_session()
    
    # Save reports
    metrics.save_metrics_report()
    
    # Show overall metrics
    overall = metrics.get_overall_metrics()
    print(f"\n[Overall] Total Success Rate: {overall['overall_success_rate']:.1f}%") 