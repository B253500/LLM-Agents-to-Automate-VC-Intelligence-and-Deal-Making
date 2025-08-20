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

# Prefer the shared metrics class if available; otherwise, provide a lightweight fallback
try:
    from evaluation_metrics.core.web_scraping_metrics import WebScrapingMetrics  # type: ignore
except Exception:
    class WebScrapingMetrics:  # minimal drop-in used by the scraper wrapper
        def __init__(self):
            self.sessions = []  # list of dicts produced in end_scraping_session

        def add_scraper_metrics(self, metrics_dict: dict):
            if isinstance(metrics_dict, dict):
                self.sessions.append(metrics_dict)

        def get_overall_metrics(self) -> dict:
            total_requests = sum(s.get('total_requests', 0) for s in self.sessions)
            total_failed = sum(s.get('failed_requests', 0) for s in self.sessions)
            total_success = sum(s.get('successful_requests', 0) for s in self.sessions)
            overall_success_rate = (total_success / total_requests * 100.0) if total_requests else 0.0
            # Average over available averages to avoid request-weighting complexity here
            avg_resp = 0.0
            avgs = [s.get('average_response_time', 0.0) for s in self.sessions if 'average_response_time' in s]
            if avgs:
                avg_resp = sum(avgs) / len(avgs)
            total_rate_limits = sum(s.get('rate_limit_hits', 0) for s in self.sessions)
            avg_quality = 0.0
            quals = [s.get('data_quality_score', 0.0) for s in self.sessions]
            if quals:
                avg_quality = sum(quals) / len(quals)
            return {
                'overall_success_rate': overall_success_rate,
                'average_response_time': avg_resp,
                'total_requests': total_requests,
                'total_failed_requests': total_failed,
                'total_rate_limit_hits': total_rate_limits,
                'average_data_quality': avg_quality,
            }

        def save_detailed_metrics(self, output_file: str):
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            payload = {
                'sessions': self.sessions,
                'generated_at': datetime.now().isoformat(),
            }
            with open(output_file, 'w') as f:
                import json
                json.dump(payload, f, indent=2)

        def generate_summary_report(self, output_file: str):
            overall = self.get_overall_metrics()
            lines = [
                'SCRAPING SUMMARY',
                f"Success Rate: {overall.get('overall_success_rate', 0.0):.1f}%",
                f"Total Requests: {overall.get('total_requests', 0)}",
                f"Failed Requests: {overall.get('total_failed_requests', 0)}",
                f"Rate Limit Hits: {overall.get('total_rate_limit_hits', 0)}",
                f"Avg Response Time: {overall.get('average_response_time', 0.0):.2f}s",
                f"Avg Data Quality: {overall.get('average_data_quality', 0.0):.2f}",
            ]
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                f.write('\n'.join(lines) + '\n')

class ScrapingMetricsIntegration:
    """Integrates evaluation metrics with existing web scraping system"""
    
    def __init__(self):
        self.metrics = WebScrapingMetrics()
        self.current_session = None
        # system usage sampling
        self._sampler_running = False
        self._cpu_samples = []
        self._mem_samples = []
        self._sampler_thread = None
        try:
            import psutil  # noqa: F401
            self._psutil_available = True
        except Exception:
            self._psutil_available = False
        
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
            'data_extracted': 0,
            # fine-grained counters
            'attempts': 0,
            'direct_saved': 0,
            'fallback_saved': 0,
            'email_sent': 0,
            'fail': 0,
            'cf_hits': 0,
            'timeouts': 0,
        }
        print(f"[Metrics] Started tracking session for {scraper_name}")
        self._start_sampler()
        
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
        # stop sampler and compute system stats
        cpu_avg = cpu_max = mem_avg = mem_max = 0.0
        samples = self._stop_sampler()
        if samples:
            cpu_vals = [c for c, _ in samples]
            mem_vals = [m for _, m in samples]
            if cpu_vals:
                cpu_avg = sum(cpu_vals) / len(cpu_vals)
                cpu_max = max(cpu_vals)
            if mem_vals:
                mem_avg = sum(mem_vals) / len(mem_vals)
                mem_max = max(mem_vals)
        
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
            'cpu_avg_percent': cpu_avg,
            'cpu_max_percent': cpu_max,
            'mem_avg_mb': mem_avg,
            'mem_max_mb': mem_max,
            'data_extracted': self.current_session['data_extracted'],
            # fine-grained counters
            'attempts': self.current_session.get('attempts', 0),
            'direct_saved': self.current_session.get('direct_saved', 0),
            'fallback_saved': self.current_session.get('fallback_saved', 0),
            'email_sent': self.current_session.get('email_sent', 0),
            'fail': self.current_session.get('fail', 0),
            'cf_hits': self.current_session.get('cf_hits', 0),
            'timeouts': self.current_session.get('timeouts', 0),
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

    # --- Fine-grained counters API (used by scraper) ---
    def inc_attempt(self):
        if self.current_session:
            self.current_session['attempts'] += 1
            # also count a request made
            self.current_session['requests_made'] += 1

    def inc_direct_saved(self):
        if self.current_session:
            self.current_session['direct_saved'] += 1
            self.current_session['successful_requests'] += 1

    def inc_fallback_saved(self):
        if self.current_session:
            self.current_session['fallback_saved'] += 1
            self.current_session['successful_requests'] += 1

    def inc_email_sent(self):
        if self.current_session:
            self.current_session['email_sent'] += 1
            self.current_session['successful_requests'] += 1

    def inc_fail(self, reason: str = None):
        if self.current_session:
            self.current_session['fail'] += 1
            self.current_session['failed_requests'] += 1
            if reason:
                if 'cf' in reason.lower():
                    self.current_session['cf_hits'] += 1
                if 'timeout' in reason.lower():
                    self.current_session['timeouts'] += 1

    # ----- internal: system usage sampler -----
    def _start_sampler(self):
        if not self._psutil_available:
            return
        if self._sampler_running:
            return
        try:
            import threading, psutil, os
            proc = psutil.Process(os.getpid())
            self._cpu_samples = []
            self._mem_samples = []
            self._sampler_running = True

            def _sample_loop():
                # prime cpu_percent
                psutil.cpu_percent(interval=None)
                while self._sampler_running:
                    cpu = psutil.cpu_percent(interval=0.5)
                    mem_mb = proc.memory_info().rss / (1024 * 1024)
                    self._cpu_samples.append(cpu)
                    self._mem_samples.append(mem_mb)

            self._sampler_thread = threading.Thread(target=_sample_loop, daemon=True)
            self._sampler_thread.start()
        except Exception:
            self._psutil_available = False

    def _stop_sampler(self):
        if not self._psutil_available:
            return []
        self._sampler_running = False
        try:
            if self._sampler_thread:
                self._sampler_thread.join(timeout=2.0)
        except Exception:
            pass
        samples = list(zip(self._cpu_samples, self._mem_samples)) if self._cpu_samples else []
        self._cpu_samples = []
        self._mem_samples = []
        self._sampler_thread = None
        return samples


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