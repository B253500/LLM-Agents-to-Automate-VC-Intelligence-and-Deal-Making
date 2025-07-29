"""
Modified api_server.py with automatic metrics recording
Run this script and it will automatically generate metrics reports
"""

import sys
import os
import time
from pathlib import Path

# Add the parent directory to import metrics
sys.path.append(str(Path(__file__).parent.parent))

from integrate_email_metrics import EmailMetricsIntegration

# Import Flask and other dependencies
from flask import Flask, request, jsonify
from agents.vc_report_agent import VCReportAgent
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize the VC agent
vc_agent = None

# Track processed emails to prevent duplicates
processed_emails = set()

# Initialize metrics
metrics = EmailMetricsIntegration()

def initialize_agent():
    global vc_agent
    if vc_agent is None:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        report_path = "data/vc_reports"
        vc_agent = VCReportAgent(openai_api_key, report_path)

@app.route('/analyze', methods=['POST'])
def analyze_question():
    try:
        data = request.get_json()
        question = data.get('question', '')
        email_id = data.get('email_id', '')  # Add email ID from n8n
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        # Check if we've already processed this email
        if email_id and email_id in processed_emails:
            print(f"Email {email_id} already processed, skipping...")
            return jsonify({
                'question': question,
                'answer': 'This email has already been processed.',
                'sources': [],
                'validation': 'duplicate'
            }), 200
        
        # Start metrics tracking
        if not email_id:
            email_id = f"email_{int(time.time())}"
        
        metrics.start_email_processing(email_id)
        
        # Initialize agent if needed
        initialize_agent()
        
        # Track agent initialization
        start_time = time.time()
        metrics.log_processing_step("agent_initialization", time.time() - start_time, True)
        
        # Retry logic for rate limits
        max_retries = 3
        retry_delay = 60  # Wait 60 seconds between retries
        
        for attempt in range(max_retries):
            try:
                # Track analysis step
                analysis_start = time.time()
                result = vc_agent.analyze_question(question)
                analysis_time = time.time() - analysis_start
                
                # Log successful analysis
                metrics.log_processing_step("analysis", analysis_time, True)
                metrics.log_response_generation(analysis_time, True)
                metrics.log_data_extraction(True)
                
                # Mark email as processed
                if email_id:
                    processed_emails.add(email_id)
                    # Keep only last 1000 emails to prevent memory issues
                    if len(processed_emails) > 1000:
                        processed_emails.clear()
                
                # End metrics tracking
                metrics.end_email_processing()
                
                return jsonify({
                    'question': question,
                    'answer': result['answer'],
                    'sources': result['sources'],
                    'validation': result['validation']
                })
                
            except Exception as e:
                error_str = str(e)
                
                # Log error in metrics
                metrics.log_processing_step("error", 0, False, error_str)
                
                # Check if it's a rate limit error
                if '429' in error_str and 'rate_limit' in error_str.lower():
                    if attempt < max_retries - 1:
                        print(f"Rate limit hit, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        metrics.end_email_processing()
                        return jsonify({
                            'error': 'OpenAI rate limit exceeded. Please try again in a few minutes.',
                            'question': question,
                            'answer': 'Sorry, the system is currently experiencing high demand. Please try again in a few minutes.',
                            'sources': [],
                            'validation': 'rate_limit_error'
                        }), 429
                else:
                    # Non-rate limit error, don't retry
                    metrics.end_email_processing()
                    raise e
        
    except Exception as e:
        print(f"Error analyzing question: {str(e)}")
        metrics.end_email_processing()
        return jsonify({
            'error': str(e),
            'question': question,
            'answer': 'Sorry, there was an error processing your question. Please try again.',
            'sources': [],
            'validation': 'error'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Endpoint to get current metrics"""
    overall = metrics.get_overall_metrics()
    return jsonify(overall)

@app.route('/metrics/report', methods=['POST'])
def generate_metrics_report():
    """Endpoint to generate and save metrics report"""
    try:
        detailed_file, summary_file = metrics.save_metrics_report()
        return jsonify({
            'status': 'success',
            'detailed_file': detailed_file,
            'summary_file': summary_file,
            'overall_metrics': metrics.get_overall_metrics()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def main_with_metrics():
    """Main function with automatic metrics recording"""
    print("🚀 Starting email assistant with metrics tracking...")
    print("📊 Metrics will be automatically recorded for each email processed")
    print("📈 Access metrics at /metrics endpoint")
    print("📋 Generate reports at /metrics/report endpoint")
    
    # Start the Flask app
    app.run(debug=True, host='0.0.0.0', port=5001)

if __name__ == '__main__':
    main_with_metrics() 