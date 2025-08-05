from fastapi import APIRouter, Body
import os
import sys

# Add the project root to the Python path to allow importing the 'agents' module
# This makes the API runnable from the project root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from agents.vc_report_agent import VCReportAgent


# This assumes your .env file with OPENAI_API_KEY is in the project root
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

@router.post("/analyze-report")
async def analyze_report_endpoint(payload: dict = Body(...)):
    """
    Accepts a question in a JSON payload, uses the VCReportAgent to analyze it 
    against the report corpus, and returns the answer and sources.
    
    Example Payload:
    {
        "question": "What's the total value of exits in the biotechnology space in Q1 2025?"
    }
    """
    question = payload.get("question")
    if not question:
        return {"error": "No question provided"}, 400

    # This calls the same logic your Python script used
    try:
        # Initialize the agent. 
        # The report_path is relative to the project root.
        agent = VCReportAgent(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            report_path="data/vc_reports"
        )
        result = agent.analyze_question(question)
        return result
    except Exception as e:
        return {"error": f"An error occurred during analysis: {e}"}, 500
