# Evaluation Metrics Integration Guide

This guide shows you how to integrate the automated evaluation metrics with your existing **web scraping** and **email assistant** scripts.

## 🕷️ Web Scraping Integration

### Quick Integration

Add this to your `web_scraping/download_reports.py`:

```python
# Add at the top of the file
from integrate_scraping_metrics import ScrapingMetricsIntegration

# Initialize metrics
metrics = ScrapingMetricsIntegration()

# Wrap your existing scraping functions
def tracked_scrape_crunchbase(page):
    metrics.start_scraping_session("Crunchbase")
    try:
        # Your existing scraping code here
        result = scrape_and_download_crunchbase(page)
        metrics.log_data_extraction(data_quality_score=0.8)
        return result
    except Exception as e:
        metrics.log_request(False, error_type=str(e))
        raise
    finally:
        metrics.end_scraping_session()

# Use tracked functions instead of original ones
tracked_scrape_crunchbase(page)
```

### Detailed Integration

For more detailed tracking, add these calls throughout your scraping code:

```python
# Track individual requests
start_time = time.time()
try:
    response = page.goto(url)
    response_time = time.time() - start_time
    metrics.log_request(True, response_time)
except Exception as e:
    metrics.log_request(False, error_type=str(e))

# Track data extraction
if data_found:
    metrics.log_data_extraction(data_quality_score=0.9)
```

## 📧 Email Assistant Integration

### Quick Integration

Add this to your `email_assistant/api_server.py`:

```python
# Add at the top of the file
from integrate_email_metrics import EmailMetricsIntegration

# Initialize metrics
metrics = EmailMetricsIntegration()

# Wrap your analyze_question function
def tracked_analyze_question(question, email_id):
    metrics.start_email_processing(email_id)
    try:
        # Track processing steps
        start_time = time.time()
        # Your existing analysis code here
        result = vc_agent.analyze_question(question)
        processing_time = time.time() - start_time
        
        metrics.log_processing_step("analysis", processing_time, True)
        metrics.log_response_generation(processing_time, True)
        metrics.log_data_extraction(True)
        
        return result
    except Exception as e:
        metrics.log_processing_step("error", 0, False, str(e))
        raise
    finally:
        metrics.end_email_processing()

# Use tracked function in your route
@app.route('/analyze', methods=['POST'])
def analyze_question():
    data = request.get_json()
    question = data.get('question', '')
    email_id = data.get('email_id', '')
    
    result = tracked_analyze_question(question, email_id)
    return jsonify(result)
```

### Detailed Integration

For more granular tracking:

```python
def tracked_analyze_question(question, email_id):
    metrics.start_email_processing(email_id)
    
    try:
        # Track question parsing
        start_time = time.time()
        parsed_question = parse_question(question)
        metrics.log_processing_step("parsing", time.time() - start_time, True)
        
        # Track agent initialization
        start_time = time.time()
        agent = initialize_agent()
        metrics.log_processing_step("initialization", time.time() - start_time, True)
        
        # Track analysis
        start_time = time.time()
        result = agent.analyze(parsed_question)
        analysis_time = time.time() - start_time
        metrics.log_processing_step("analysis", analysis_time, True)
        
        # Track response generation
        metrics.log_response_generation(analysis_time, True)
        metrics.log_data_extraction(True)
        
        return result
    except Exception as e:
        metrics.log_processing_step("error", 0, False, str(e))
        raise
    finally:
        metrics.end_email_processing()
```

## 📊 Getting Metrics Reports

### Web Scraping Reports

```python
# Save detailed reports
detailed_file, summary_file = metrics.save_metrics_report()

# Get overall metrics
overall = metrics.get_overall_metrics()
print(f"Overall Success Rate: {overall['overall_success_rate']:.1f}%")
print(f"Average Response Time: {overall['average_response_time']:.2f}s")
```

### Email Assistant Reports

```python
# Save detailed reports
detailed_file, summary_file = metrics.save_metrics_report()

# Get overall metrics
overall = metrics.get_overall_metrics()
print(f"Overall Success Rate: {overall['overall_success_rate']:.1f}%")
print(f"Average Response Time: {overall['average_response_time']:.2f}s")
```

## 🔧 Manual Metrics (For Non-Automated Tasks)

For metrics that require human judgment, create manual tracking:

```python
# Manual metrics tracking
manual_metrics = {
    'llm_hallucination_rate': 0.05,  # 5% estimated
    'factual_accuracy': 0.92,  # 92% human verified
    'extraction_accuracy': 0.88,  # 88% human verified
    'scraper_accuracy': 0.95,  # 95% human verified
    'form_submission_failure': 0.03  # 3% failure rate
}

# Save manual metrics
with open('manual_metrics.json', 'w') as f:
    json.dump(manual_metrics, f, indent=2)
```

## 📈 Integration Examples

### Example 1: Web Scraping with Metrics

```python
# In your download_reports.py
from integrate_scraping_metrics import ScrapingMetricsIntegration

metrics = ScrapingMetricsIntegration()

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Track Crunchbase scraping
        metrics.start_scraping_session("Crunchbase")
        try:
            scrape_and_download_crunchbase(page)
            metrics.log_data_extraction(data_quality_score=0.8)
        except Exception as e:
            metrics.log_request(False, error_type=str(e))
        finally:
            metrics.end_scraping_session()
        
        # Track Beauhurst scraping
        metrics.start_scraping_session("Beauhurst")
        try:
            scrape_and_download_beauhurst(page)
            metrics.log_data_extraction(data_quality_score=0.9)
        except Exception as e:
            metrics.log_request(False, error_type=str(e))
        finally:
            metrics.end_scraping_session()
        
        browser.close()
        
        # Save reports
        metrics.save_metrics_report()

if __name__ == "__main__":
    main()
```

### Example 2: Email Assistant with Metrics

```python
# In your api_server.py
from integrate_email_metrics import EmailMetricsIntegration

metrics = EmailMetricsIntegration()

@app.route('/analyze', methods=['POST'])
def analyze_question():
    data = request.get_json()
    question = data.get('question', '')
    email_id = data.get('email_id', '')
    
    metrics.start_email_processing(email_id)
    
    try:
        # Track processing steps
        start_time = time.time()
        result = vc_agent.analyze_question(question)
        processing_time = time.time() - start_time
        
        metrics.log_processing_step("analysis", processing_time, True)
        metrics.log_response_generation(processing_time, True)
        metrics.log_data_extraction(True)
        
        return jsonify(result)
    except Exception as e:
        metrics.log_processing_step("error", 0, False, str(e))
        return jsonify({'error': str(e)}), 500
    finally:
        metrics.end_email_processing()
```

## 🎯 What You Get

### Automated Metrics:
- ✅ **Agent Success Rate** - Tracks if systems complete successfully
- ✅ **Response Time** - How quickly systems respond
- ✅ **Error Tracking** - Rate limits, parsing errors, network issues
- ✅ **Data Quality** - Automated validation of extracted data
- ✅ **System Uptime** - System availability tracking

### Manual Metrics (You Track):
- 📊 **LLM Hallucination Rate** - Human verification needed
- 📊 **Factual Accuracy** - Human verification needed  
- 📊 **Extraction Accuracy** - Human verification needed
- 📊 **Form Submission Failure** - Track manually

## 🚀 Next Steps

1. **Add the integration scripts** to your existing files
2. **Run your scripts** to start collecting metrics
3. **Check the reports** in the `results/` directories
4. **Monitor performance** and optimize based on metrics
5. **Add manual tracking** for human-verified metrics

The metrics will help you identify bottlenecks, track performance improvements, and demonstrate the value of your automated systems! 