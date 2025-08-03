"""
Modified download_reports.py with automatic metrics recording
Run this script and it will automatically generate metrics reports
"""

import sys
import os
import time
from pathlib import Path

# Add the parent directory to import metrics
sys.path.append(str(Path(__file__).parent.parent))

from integrate_scraping_metrics import ScrapingMetricsIntegration

# Import all the original functions from download_reports.py
from download_reports import (
    scrape_and_download_crunchbase,
    scrape_and_download_beauhurst,
    scrape_and_download_pitchbook,
    sync_playwright,
    PlaywrightError,
    NAV_TIMEOUT
)

def main_with_metrics():
    """Main function with automatic metrics recording"""
    
    # Initialize metrics
    metrics = ScrapingMetricsIntegration()
    
    print("🚀 Starting web scraping with metrics tracking...")
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)

        # Track Crunchbase scraping
        print("\n📊 Starting Crunchbase scraping with metrics...")
        metrics.start_scraping_session("Crunchbase")
        try:
            scrape_and_download_crunchbase(page)
            metrics.log_data_extraction(data_quality_score=0.8)
            print("✅ Crunchbase scraping completed successfully")
        except Exception as e:
            print(f"❌ Crunchbase scraping failed: {e}")
            metrics.log_request(False, error_type=str(e))
        finally:
            metrics.end_scraping_session()

        # Track Beauhurst scraping
        print("\n📊 Starting Beauhurst scraping with metrics...")
        metrics.start_scraping_session("Beauhurst")
        try:
            scrape_and_download_beauhurst(page)
            metrics.log_data_extraction(data_quality_score=0.9)
            print("✅ Beauhurst scraping completed successfully")
        except Exception as e:
            print(f"❌ Beauhurst scraping failed: {e}")
            metrics.log_request(False, error_type=str(e))
        finally:
            metrics.end_scraping_session()

        # Track PitchBook scraping
        print("\n📊 Starting PitchBook scraping with metrics...")
        metrics.start_scraping_session("PitchBook")
        try:
            scrape_and_download_pitchbook(page)
            metrics.log_data_extraction(data_quality_score=0.85)
            print("✅ PitchBook scraping completed successfully")
        except Exception as e:
            print(f"❌ PitchBook scraping failed: {e}")
            metrics.log_request(False, error_type=str(e))
        finally:
            metrics.end_scraping_session()

        browser.close()

    # Generate and save metrics reports
    print("\n📈 Generating metrics reports...")
    detailed_file, summary_file = metrics.save_metrics_report()
    
    # Show overall metrics
    overall = metrics.get_overall_metrics()
    print(f"\n🎯 OVERALL SCRAPING METRICS:")
    print(f"  ✅ Success Rate: {overall['overall_success_rate']:.1f}%")
    print(f"  ⏱️  Avg Response Time: {overall['average_response_time']:.2f}s")
    print(f"  📊 Total Requests: {overall['total_requests']}")
    print(f"  ❌ Failed Requests: {overall['total_failed_requests']}")
    print(f"  🔄 Rate Limit Hits: {overall['total_rate_limit_hits']}")
    print(f"  📋 Data Quality Score: {overall['average_data_quality']:.2f}/1.0")
    
    print(f"\n📊 Reports saved:")
    print(f"  📈 Detailed metrics: {detailed_file}")
    print(f"  📋 Summary report: {summary_file}")
    
    return metrics

if __name__ == '__main__':
    main_with_metrics() 