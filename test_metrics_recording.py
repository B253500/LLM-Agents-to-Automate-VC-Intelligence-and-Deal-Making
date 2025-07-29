"""
Test script to demonstrate automatic metrics recording
This shows how metrics are automatically generated when you run your scripts
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

def test_web_scraping_metrics():
    """Test web scraping metrics recording"""
    print("🧪 Testing Web Scraping Metrics Recording...")
    
    try:
        from web_scraping.integrate_scraping_metrics import ScrapingMetricsIntegration
        
        metrics = ScrapingMetricsIntegration()
        
        # Simulate scraping sessions
        print("📊 Simulating Crunchbase scraping...")
        metrics.start_scraping_session("Crunchbase")
        metrics.log_request(True, response_time=1.2)
        metrics.log_request(True, response_time=0.8)
        metrics.log_request(False, error_type="rate_limit")
        metrics.log_data_extraction(data_quality_score=0.8)
        metrics.end_scraping_session()
        
        print("📊 Simulating Beauhurst scraping...")
        metrics.start_scraping_session("Beauhurst")
        metrics.log_request(True, response_time=1.5)
        metrics.log_request(True, response_time=1.1)
        metrics.log_request(True, response_time=0.9)
        metrics.log_data_extraction(data_quality_score=0.9)
        metrics.end_scraping_session()
        
        print("📊 Simulating PitchBook scraping...")
        metrics.start_scraping_session("PitchBook")
        metrics.log_request(True, response_time=1.3)
        metrics.log_request(False, error_type="parsing_error")
        metrics.log_request(True, response_time=1.0)
        metrics.log_data_extraction(data_quality_score=0.85)
        metrics.end_scraping_session()
        
        # Generate reports
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
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing web scraping metrics: {e}")
        return False

def test_email_metrics():
    """Test email assistant metrics recording"""
    print("\n🧪 Testing Email Assistant Metrics Recording...")
    
    try:
        from email_assistant.integrate_email_metrics import EmailMetricsIntegration
        
        metrics = EmailMetricsIntegration()
        
        # Simulate email processing
        print("📧 Simulating email processing...")
        metrics.start_email_processing("test_email_1", "What is the market size for electric vehicles?")
        metrics.log_processing_step("parsing", 0.1, True)
        metrics.log_processing_step("analysis", 0.8, True)
        metrics.log_response_generation(0.8, True)
        metrics.log_data_extraction(True)
        metrics.end_email_processing()
        
        print("📧 Simulating another email...")
        metrics.start_email_processing("test_email_2", "Who are the main competitors?")
        metrics.log_processing_step("parsing", 0.15, True)
        metrics.log_processing_step("analysis", 1.2, True)
        metrics.log_response_generation(1.2, True)
        metrics.log_data_extraction(True)
        metrics.end_email_processing()
        
        print("📧 Simulating failed email...")
        metrics.start_email_processing("test_email_3", "Invalid question")
        metrics.log_processing_step("parsing", 0.05, False, "Invalid format")
        metrics.log_response_generation(0.05, False)
        metrics.log_data_extraction(False)
        metrics.end_email_processing()
        
        # Generate reports
        print("\n📈 Generating metrics reports...")
        detailed_file, summary_file = metrics.save_metrics_report()
        
        # Show overall metrics
        overall = metrics.get_overall_metrics()
        print(f"\n🎯 OVERALL EMAIL METRICS:")
        print(f"  ✅ Success Rate: {overall['overall_success_rate']:.1f}%")
        print(f"  ⏱️  Avg Response Time: {overall['average_response_time']:.2f}s")
        print(f"  📊 Total Emails: {overall['total_emails']}")
        print(f"  ❌ Failed Emails: {overall['total_failed_emails']}")
        print(f"  📋 Data Extraction Rate: {overall['data_extraction_rate']:.1f}%")
        
        print(f"\n📊 Reports saved:")
        print(f"  📈 Detailed metrics: {detailed_file}")
        print(f"  📋 Summary report: {summary_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing email metrics: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing Automatic Metrics Recording")
    print("=" * 50)
    
    # Test web scraping metrics
    web_success = test_web_scraping_metrics()
    
    # Test email metrics
    email_success = test_email_metrics()
    
    print("\n" + "=" * 50)
    if web_success and email_success:
        print("✅ All tests passed! Metrics recording is working correctly.")
        print("\n📋 To use with your actual scripts:")
        print("  🕷️  Web Scraping: Run 'python web_scraping/download_reports_with_metrics.py'")
        print("  📧 Email Assistant: Run 'python email_assistant/api_server_with_metrics.py'")
        print("\n📊 Reports will be automatically generated in the 'results/' directories")
    else:
        print("❌ Some tests failed. Check the error messages above.")
    
    return web_success and email_success

if __name__ == "__main__":
    main() 