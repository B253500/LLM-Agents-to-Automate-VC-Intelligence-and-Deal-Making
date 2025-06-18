from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import datetime
from agents.vc_report_agent import VCReportAgent
from fpdf import FPDF
import json
from typing import Dict, Any

# Load environment variables
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'VC Report Analysis', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 10, body)
        self.ln()

    def add_validation_info(self, validation: Dict[str, Any]):
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.multi_cell(0, 5, f"Validation: {'[OK]' if validation['temporal_valid'] else '[!]'} Temporal validity")
        self.multi_cell(0, 5, f"Tokens used: {validation['tokens_used']}")
        self.multi_cell(0, 5, f"Cost: ${validation['cost']:.4f}")
        self.set_text_color(0, 0, 0)
        self.ln()

def format_answer_with_validation(result: Dict[str, Any]) -> str:
    """Format the answer with validation information and sources."""
    answer = result["answer"]
    
    # Add validation warnings if needed
    if not result["validation"]["temporal_valid"]:
        answer = "! WARNING: Temporal data validation failed. The answer may mix data from different time periods.\n\n" + answer
    
    # Add sources
    sources = result["sources"]
    if sources:
        answer += "\n\nSources:"
        for source in sources:
            source_info = f"\n- {source['source']}"
            if source.get('has_visual'):
                source_info += " (contains visual data)"
            answer += source_info
    
    return answer

def generate_pdf_report(results: Dict[str, Dict[str, Any]], output_file: str = "vc_report_analysis.pdf"):
    """Generate a PDF report from the analysis results with validation information."""
    pdf = PDFReport()
    pdf.add_page()
    
    # Add title
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'VC Report Analysis Results', 0, 1, 'C')
    pdf.ln(10)
    
    # Add each question and answer
    for question, result in results.items():
        pdf.chapter_title(f"Q: {question}")
        
        # Format and add the answer with validation info
        formatted_answer = format_answer_with_validation(result)
        pdf.chapter_body(formatted_answer)
        
        # Add validation information using ASCII characters
        pdf.set_font('Arial', 'I', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 5, f"Validation: {'[OK]' if result['validation']['temporal_valid'] else '[!]'} Temporal validity")
        pdf.multi_cell(0, 5, f"Tokens used: {result['validation']['tokens_used']}")
        pdf.multi_cell(0, 5, f"Cost: ${result['validation']['cost']:.4f}")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(10)
    
    # Save the PDF
    pdf.output(output_file)
    print(f"\nPDF report saved to {output_file}")

def main():
    # Initialize the VC Report Agent
    print("Initializing VC Report Agent...")
    agent = VCReportAgent(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        report_path="data/vc_reports"
    )
    
    # Questions to analyze
    questions = [
        "What's the current deal activity size for Insurtech in the most recent financial quarter?",
        "What's the total value of exits in the biotechnology/bio tools space in Q1 2025?",
        "What are the top 3 academic institutions by spin out activity in the UK? How many companies do they spin out on average individually?",
        "What is the top sector of UK academic spinouts?",
        "What's the top sub-sector of Quantum Computing by number of companies generated?",
        "What's the CAGR of median gaming early-stage VC deal value and pre-money valuation ($M) in the segment of development?"
    ]
    
    # Analyze each question
    results = {}
    total_tokens = 0
    total_cost = 0.0
    
    for question in questions:
        print(f"\nAnalyzing: {question}")
        
        # Get analysis from agent
        result = agent.analyze_question(question)
        results[question] = result
        
        # Update totals
        total_tokens += result["validation"]["tokens_used"]
        total_cost += result["validation"]["cost"]
        
        # Print result with validation
        print("\n" + "="*80)
        print(f"Question: {question}")
        print("-"*80)
        print(f"Answer: {result['answer']}")
        print("\nValidation:")
        print(f"- Temporal validity: {'✓' if result['validation']['temporal_valid'] else '⚠'}")
        print(f"- Tokens used: {result['validation']['tokens_used']}")
        print(f"- Cost: ${result['validation']['cost']:.4f}")
        if result["sources"]:
            print("\nSources:")
            for source in result["sources"]:
                print(f"- {source['source']}" + (" (contains visual data)" if source.get('has_visual') else ""))
        print("="*80 + "\n")
    
    # Print summary
    print("\nAnalysis Summary:")
    print(f"Total tokens used: {total_tokens}")
    print(f"Total cost: ${total_cost:.4f}")
    
    # Save results to JSON
    output_file = "vc_report_analysis_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_file}")
    
    # Generate PDF report
    generate_pdf_report(results)

if __name__ == "__main__":
    main() 