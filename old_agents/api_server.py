from flask import Flask, request, jsonify
from agents.vc_report_agent import VCReportAgent
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize the VC agent
vc_agent = None

# Track processed emails to prevent duplicates
processed_emails = set()

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
        
        # Initialize agent if needed
        initialize_agent()
        
        # Retry logic for rate limits
        max_retries = 3
        retry_delay = 60  # Wait 60 seconds between retries
        
        for attempt in range(max_retries):
            try:
                # Analyze the question
                result = vc_agent.analyze_question(question)
                
                # Mark email as processed
                if email_id:
                    processed_emails.add(email_id)
                    # Keep only last 1000 emails to prevent memory issues
                    if len(processed_emails) > 1000:
                        processed_emails.clear()
                
                return jsonify({
                    'question': question,
                    'answer': result['answer'],
                    'sources': result['sources'],
                    'validation': result['validation']
                })
                
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a rate limit error
                if '429' in error_str and 'rate_limit' in error_str.lower():
                    if attempt < max_retries - 1:
                        print(f"Rate limit hit, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        return jsonify({
                            'error': 'OpenAI rate limit exceeded. Please try again in a few minutes.',
                            'question': question,
                            'answer': 'Sorry, the system is currently experiencing high demand. Please try again in a few minutes.',
                            'sources': [],
                            'validation': 'rate_limit_error'
                        }), 429
                else:
                    # Non-rate limit error, don't retry
                    raise e
        
    except Exception as e:
        print(f"Error analyzing question: {str(e)}")
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 