# memo_api/services/memo_generator.py
from openai import OpenAI
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Import agent runners
from agents.competitive_intel_agent import build_competitive_intel_agent
from agents.deck_agent import run_crew as run_deck_agent
from agents.financial_analysis_agent import build_financial_analysis_agent
from agents.founder_profiling_agent import build_founder_profiling_agent
from agents.market_sizing_agent import build_market_sizing_agent
from agents.risk_assessment_agent import build_risk_assessment_agent
from agents.technical_dd_agent import build_technical_dd_agent
from core.schemas import StartupProfile

CLIENT = OpenAI()

def format_value(value, field_name=""):
    """Format values for display, handling None, 0.0, and empty values appropriately"""
    if value is None or value == "":
        return "Not Available"
    if isinstance(value, float):
        if value == 0.0:
            return "Not Available"
        if "revenue" in field_name.lower() or "funding" in field_name.lower() or "valuation" in field_name.lower():
            return f"${value:,.0f}"
        if "market" in field_name.lower() or "tam" in field_name.lower() or "sam" in field_name.lower() or "som" in field_name.lower():
            return f"${value:,.0f}M"
        return f"{value:.2f}"
    if isinstance(value, list):
        if not value:
            return "Not Available"
        return ", ".join(str(v) for v in value)
    return str(value)

def extract_company_profile_from_deck(pdf_path: str, trace_id: str) -> Dict[str, Any]:
    """Extract company profile from pitch deck using deck agent"""
    try:
        deck_result = run_deck_agent(pdf_path, trace_id)
        if isinstance(deck_result, str):
            try:
                return json.loads(deck_result)
            except:
                return {"error": "Failed to parse deck agent output"}
        return deck_result
    except Exception as e:
        print(f"Error extracting company profile: {e}")
        return {"error": f"Failed to extract profile: {str(e)}"}

def safe_agent_call(agent_builder, profile: StartupProfile, trace_id: str, agent_name: str) -> Dict[str, Any]:
    """Safely call an agent and handle errors gracefully"""
    try:
        agent, task = agent_builder(profile, trace_id)
        result = task.callback()
        
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return {"raw_output": result, "error": "Failed to parse JSON"}
        return result
    except Exception as e:
        print(f"Error in {agent_name}: {e}")
        return {"error": f"{agent_name} failed: {str(e)}"}

def run_all_agents(profile: StartupProfile, pdf_path: Optional[str] = None, trace_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run all agents and return a dictionary of their outputs.
    Now uses consistent company context from the profile.
    """
    print(f"Running agents for company: {profile.name} in {profile.sector}")
    
    # Run all agents with the same company profile
    results = {
        "company_profile": profile.model_dump(),
        "competitive_intel": safe_agent_call(build_competitive_intel_agent, profile, trace_id, "Competitive Intel"),
        "financial_analysis": safe_agent_call(build_financial_analysis_agent, profile, trace_id, "Financial Analysis"),
        "founder_profiling": safe_agent_call(build_founder_profiling_agent, profile, trace_id, "Founder Profiling"),
        "market_sizing": safe_agent_call(build_market_sizing_agent, profile, trace_id, "Market Sizing"),
        "risk_assessment": safe_agent_call(build_risk_assessment_agent, profile, trace_id, "Risk Assessment"),
        "technical_dd": safe_agent_call(build_technical_dd_agent, profile, trace_id, "Technical DD"),
    }
    
    # If we have a PDF, also extract deck-specific information
    if pdf_path:
        results["deck_analysis"] = extract_company_profile_from_deck(pdf_path, trace_id)
    
    return results

def generate_html_memo(agent_outputs: Dict[str, Any], meta: Dict[str, Any]) -> str:
    """Generate a comprehensive HTML memo from agent outputs"""
    
    # Extract key data with proper formatting
    company_profile = agent_outputs.get("company_profile", {})
    market_data = agent_outputs.get("market_sizing", {})
    financial_data = agent_outputs.get("financial_analysis", {})
    risk_data = agent_outputs.get("risk_assessment", {})
    technical_data = agent_outputs.get("technical_dd", {})
    founder_data = agent_outputs.get("founder_profiling", {})
    competitive_data = agent_outputs.get("competitive_intel", {})
    
    # Format market data
    tam = format_value(market_data.get("TAM"), "TAM")
    sam = format_value(market_data.get("SAM"), "SAM") 
    som = format_value(market_data.get("SOM"), "SOM")
    
    # Format financial data
    revenue = format_value(financial_data.get("revenue"), "revenue")
    projected_revenue = format_value(financial_data.get("projected_revenue"), "projected_revenue")
    funding_sought = format_value(financial_data.get("funding_sought"), "funding_sought")
    
    # Format risk data
    risk_score = format_value(risk_data.get("risk_score"), "risk_score")
    risk_flags = format_value(risk_data.get("risk_flags"), "risk_flags")
    
    # Format technical data
    tech_maturity = format_value(technical_data.get("tech_maturity"), "tech_maturity")
    moat_strength = format_value(technical_data.get("moat_strength"), "moat_strength")
    
    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Investment Memo - {company_profile.get('name', 'Company')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #2c3e50;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 2.5em;
        }}
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 1.2em;
            margin-top: 10px;
        }}
        .section {{
            margin-bottom: 30px;
            padding: 20px;
            border-left: 4px solid #3498db;
            background-color: #f8f9fa;
        }}
        .section h2 {{
            color: #2c3e50;
            margin-top: 0;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 10px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #e1e8ed;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-label {{
            font-weight: bold;
            color: #34495e;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 1.2em;
            color: #2c3e50;
        }}
        .risk-high {{ color: #e74c3c; }}
        .risk-medium {{ color: #f39c12; }}
        .risk-low {{ color: #27ae60; }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            color: #7f8c8d;
        }}
        .generated-by {{
            font-style: italic;
            color: #95a5a6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Investment Memo</h1>
            <div class="subtitle">{company_profile.get('name', 'Company')} - {company_profile.get('sector', 'Sector')}</div>
            <div class="subtitle">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Deal Terms</div>
                    <div class="metric-value">{meta.get('currentRound', 'Not Available')} at {meta.get('proposedValuation', 'Not Available')}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Valuation Date</div>
                    <div class="metric-value">{meta.get('valuationDate', 'Not Available')}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Company</div>
                    <div class="metric-value">{company_profile.get('name', 'Not Available')}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Sector</div>
                    <div class="metric-value">{company_profile.get('sector', 'Not Available')}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Market Opportunity & Sizing</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Addressable Market (TAM)</div>
                    <div class="metric-value">{tam}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Serviceable Available Market (SAM)</div>
                    <div class="metric-value">{sam}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Serviceable Obtainable Market (SOM)</div>
                    <div class="metric-value">{som}</div>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <strong>Market Analysis:</strong> {json.dumps(market_data, indent=2) if isinstance(market_data, dict) else str(market_data)}
            </div>
        </div>

        <div class="section">
            <h2>Financial Analysis</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Current Revenue</div>
                    <div class="metric-value">{revenue}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Projected Revenue</div>
                    <div class="metric-value">{projected_revenue}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Funding Sought</div>
                    <div class="metric-value">{funding_sought}</div>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <strong>Detailed Financial Analysis:</strong> {json.dumps(financial_data, indent=2) if isinstance(financial_data, dict) else str(financial_data)}
            </div>
        </div>

        <div class="section">
            <h2>Risk Assessment</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Risk Score</div>
                    <div class="metric-value">{risk_score}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Risk Flags</div>
                    <div class="metric-value">{risk_flags}</div>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <strong>Detailed Risk Analysis:</strong> {json.dumps(risk_data, indent=2) if isinstance(risk_data, dict) else str(risk_data)}
            </div>
        </div>

        <div class="section">
            <h2>Technical Due Diligence</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Technology Maturity</div>
                    <div class="metric-value">{tech_maturity}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Moat Strength</div>
                    <div class="metric-value">{moat_strength}</div>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <strong>Technical Analysis:</strong> {json.dumps(technical_data, indent=2) if isinstance(technical_data, dict) else str(technical_data)}
            </div>
        </div>

        <div class="section">
            <h2>Team & Founder Analysis</h2>
            <div style="margin-top: 20px;">
                <strong>Founder Profile:</strong> {json.dumps(founder_data, indent=2) if isinstance(founder_data, dict) else str(founder_data)}
            </div>
        </div>

        <div class="section">
            <h2>Competitive Intelligence</h2>
            <div style="margin-top: 20px;">
                <strong>Competitive Analysis:</strong> {json.dumps(competitive_data, indent=2) if isinstance(competitive_data, dict) else str(competitive_data)}
            </div>
        </div>

        <div class="footer">
            <div class="generated-by">Generated using Flybridge Memo Generator</div>
        </div>
    </div>
</body>
</html>
"""
    
    return html_template

def generate_pdf_from_html(html_content: str, output_path: str = "memo_output.pdf") -> str:
    """Generate PDF from HTML content using weasyprint or similar"""
    try:
        # Try to use weasyprint first (better HTML/CSS support)
        from weasyprint import HTML, CSS
        HTML(string=html_content).write_pdf(output_path)
        print(f"✅ PDF generated successfully: {output_path}")
        return output_path
    except ImportError:
        try:
            # Fallback to pdfkit if weasyprint not available
            import pdfkit
            pdfkit.from_string(html_content, output_path)
            print(f"✅ PDF generated successfully: {output_path}")
            return output_path
        except ImportError:
            print("⚠️  PDF generation requires weasyprint or pdfkit. Install with: pip install weasyprint")
            print(f"📄 HTML memo saved to: {output_path.replace('.pdf', '.html')}")
            # Save as HTML instead
            html_path = output_path.replace('.pdf', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return html_path

async def generate(profile: StartupProfile, pdf_path: Optional[str], meta: Dict[str, Any], trace_id: str) -> Dict[str, str]:
    """
    Run all agents, collect outputs, and generate comprehensive memo in both HTML and PDF formats.
    
    Returns:
        Dict with 'html' and 'pdf' keys containing file paths
    """
    print(f"🚀 Starting memo generation for {profile.name}")
    
    # Run all agents with consistent company context
    agent_outputs = run_all_agents(profile, pdf_path, trace_id)
    
    # Generate HTML memo
    html_content = generate_html_memo(agent_outputs, meta)
    
    # Save HTML
    html_path = f"memo_{trace_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Generate PDF
    pdf_path_output = f"memo_{trace_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_result = generate_pdf_from_html(html_content, pdf_path_output)
    
    return {
        "html": html_path,
        "pdf": pdf_result,
        "html_content": html_content
    }
