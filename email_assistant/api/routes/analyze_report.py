from flask import Blueprint, request, jsonify
import os
import sys

# Add the project root to the Python path to allow for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from agents.vc_report_agent import VCReportAgent

analyze_bp = Blueprint('analyze_bp', __name__)

# Initialize the agent globally so it loads the database only once when the server starts.
# This is much more efficient than reloading it on every request.
print("Initializing VC Report Agent for API...")
agent = VCReportAgent(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    report_path="data/vc_reports"  # This path is used to find sources, the DB is loaded from chroma_db
)
print("VC Report Agent initialized.")

@analyze_bp.route('/api/analyze-report', methods=['POST'])
def analyze_report():
    """
    Receives a question in a JSON payload, gets an answer from the VCReportAgent,
    and returns the answer.
    """
    if not request.json or 'question' not in request.json:
        return jsonify({'error': 'Missing question in request body'}), 400

    question = request.json['question']
    
    try:
        print(f"Received question for analysis: {question}")
        # The agent is already initialized, so we can use it directly.
        result = agent.analyze_question(question)
        print(f"Analysis complete. Returning answer.")
        
        # We return the whole result object, which includes the answer, sources, and validation.
        return jsonify(result)
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return jsonify({'error': str(e)}), 500
