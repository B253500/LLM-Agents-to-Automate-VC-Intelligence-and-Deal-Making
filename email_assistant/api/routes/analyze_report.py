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
    Receives a question, classifies the intent, and routes to the appropriate
    tool (RAG, CoreSignal, web search, etc.). This is the primary, intelligent
    endpoint for all email assistant queries.
    """
    if not request.json or 'question' not in request.json:
        return jsonify({'error': 'Missing question in request body'}), 400

    question = request.json['question']
    
    try:
        print(f"Received question for intelligent analysis: {question}")
        # The agent is already initialized, so we can use it directly.
        result = agent.analyze_question_enriched(question)
        print(f"Analysis complete. Returning answer.")
        return jsonify(result)
    except Exception as e:
        print(f"Error during analysis: {e}")
        return jsonify({'error': str(e)}), 500


@analyze_bp.route('/api/build-index', methods=['POST'])
def build_index():
    """Build the local ChromaDB index from PDFs in data/vc_reports inside the container."""
    try:
        report_path = request.json.get('report_path', 'data/vc_reports') if request.is_json else 'data/vc_reports'
        num_docs = agent._initialize_vector_store(report_path)
        return jsonify({
            'status': 'ok',
            'message': f'Index built from {report_path} and persisted to ./chroma_db',
            'num_docs': num_docs
        })
    except Exception as e:
        print(f"Error during index build: {e}")
        return jsonify({'error': str(e)}), 500
