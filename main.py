# Loading environment variables first
from dotenv import load_dotenv
load_dotenv()

# Suppressing SWIG deprecation warnings
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module=".*swig.*")

# Standard library imports
import sys
import os
import time
from datetime import datetime
from pathlib import Path

# Local application imports
from core.download_utils import extract_text, get_cache_path, load_from_cache, save_to_cache, validate_extraction_quality
from core.utils import merge_outputs
from core.orchestration import run_all_sequential_with_text
from core.schemas import StartupProfile
from core.vector_store import clear_collection
from core.visual_utils import extract_images_from_pdf, generate_sample_market_chart
from core.memo_formatters import format_company_overview_section, format_funding_stage, format_followup_section, format_risk_section, format_risk_score
from core.financial_formatters import format_enhanced_financials_section, format_financial_history_section
from core.document_generators import save_memo_with_template, convert_docx_to_pdf
from core.text_cleaners import clean_think_tags_and_debugging, clean, deduplicate_memo, clean_discussion_section
from core.evaluation_utils import generate_excel_output, save_evaluation_metrics, print_evaluation_summary

# Configuration
from config import Config

# Chain imports
from chains.pitch_deck_chain import run_pitch_deck_chain_with_text
from chains.technical_dd_chain import run_technical_dd_chain
from chains.market_sizing_chain import run_market_sizing_chain
from chains.financial_analysis_chain import run_financial_analysis_chain
from chains.competitive_intel_chain import run_competitive_intel_chain
from chains.risk_assessment_chain import run_risk_assessment_chain
from chains.memo_synthesis_chain import (
    run_detailed_summary_chain,
    run_problem_statement_chain,
    run_solution_overview_chain,
    run_risks_section_chain,
    run_team_section_chain,
    run_analyst_commentary_chain
)

# Agent imports
from agents.technical_dd_agent import build_technical_dd_agent
from chains.technical_dd_chain import format_technical_dd_section
from agents.market_sizing_agent import build_market_sizing_agent
from agents.competitive_intel_agent import build_competitive_intel_agent
from chains.market_sizing_chain import generate_market_size_section
from chains.competitive_intel_chain import generate_competitive_landscape
from agents.founder_profiling_agent import build_founder_profiling_agent
from chains.team_chain import generate_team_section
from agents.risk_assessment_agent import build_risk_assessment_agent, generate_discussion_section, generate_counterfactual_section
from agents.business_model_agent import build_business_model_agent
from agents.product_description_agent import build_product_description_agent
from agents.exit_strategy_agent import build_exit_strategy_agent
from agents.esg_agent import build_esg_agent
from agents.follow_up_agent import build_follow_up_agent

CACHE_DIR = "extraction_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def run_financial_analysis_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    """Enhanced financial analysis with comprehensive context building."""
    try:
        # Build comprehensive financial context
        financial_context = ""
        
        # Add tables data if available
        if hasattr(profile, 'tables_text') and profile.tables_text:
            financial_context += f"\n\nTABLES DATA:\n{profile.tables_text}"
        
        # Add figures/OCR data if available
        if hasattr(profile, 'figures_ocr') and profile.figures_ocr:
            financial_context += f"\n\nFIGURES/OCR DATA:\n{profile.figures_ocr}"
        
        # Add full text as backup
        if full_text:
            financial_context += f"\n\nFULL TEXT:\n{full_text[:3000]}"
        
        # Call the enhanced chain with comprehensive context
        updated_profile = run_financial_analysis_chain(profile, financial_context=financial_context)
        
        # Copy updated fields back to the original profile
        for field_name in updated_profile.model_fields.keys():
            try:
                new_value = getattr(updated_profile, field_name)
                if new_value is not None and new_value != '':
                    setattr(profile, field_name, new_value)
            except Exception:
                continue
        
        return profile
        
    except Exception as e:
        print(f"[Financial Analysis] Error: {e}")
        return profile


def clean_memo_section(content: str) -> str:
    """Helper function to clean memo sections consistently."""
    return clean_think_tags_and_debugging(clean(content))


def run_product_description_agent(profile: StartupProfile) -> str:
    """Run product description agent and return the result."""
    agent, task = build_product_description_agent(profile)
    # For now, we'll call the chain directly since we're not using CrewAI execution
    from chains.product_description_chain import run_product_description_chain
    return run_product_description_chain(profile)


def run_business_model_agent(profile: StartupProfile) -> str:
    """Run business model agent and return the result."""
    agent, task = build_business_model_agent(profile)
    # For now, we'll call the chain directly since we're not using CrewAI execution
    from chains.memo_synthesis_chain import run_business_model_chain
    return run_business_model_chain(profile)


def run_esg_section_agent(profile: StartupProfile) -> str:
    """Run ESG section agent and return the result."""
    agent, task = build_esg_agent(profile)
    # For now, we'll call the chain directly since we're not using CrewAI execution
    from chains.memo_synthesis_chain import run_esg_section_chain
    return run_esg_section_chain(profile)


def run_risks_section_agent(profile: StartupProfile) -> str:
    """Run risks section agent and return the result."""
    from agents.risk_assessment_agent import run_risks_section_agent
    return run_risks_section_agent(profile)


def run_exit_strategies_agent(profile: StartupProfile) -> str:
    """Run exit strategies agent and return the result."""
    agent, task = build_exit_strategy_agent(profile)
    # For now, we'll call the chain directly since we're not using CrewAI execution
    from chains.memo_synthesis_chain import run_exit_strategies_chain
    return run_exit_strategies_chain(profile)


def run_followup_section_agent(profile: StartupProfile) -> str:
    """Run follow-up section agent and return the result."""
    agent, task = build_follow_up_agent(profile)
    # For now, we'll call the chain directly since we're not using CrewAI execution
    from chains.memo_synthesis_chain import run_followup_section_chain
    return run_followup_section_chain(profile)


def format_memo(profile: StartupProfile, evaluator=None) -> str:
    """Format the complete investment memo using refactored modules.
    If an evaluator is provided, wrap synthesis agents with timing to avoid double runs elsewhere.
    """
    current_date = datetime.now().strftime("%B %d, %Y")

    # Synthesis agents with optional timing wrappers
    if evaluator:
        evaluator.log_section_start("BUSINESS MODEL AGENT")
    from chains.memo_synthesis_chain import run_business_model_chain
    bm_text = run_business_model_chain(profile, evaluator=evaluator)
    if evaluator:
        bm_tokens = max(1, len(bm_text) // 3)
        evaluator.log_section_end("BUSINESS MODEL AGENT", tokens_used=bm_tokens, model="gpt-4o")
        evaluator.log_agent_estimated_tokens("BUSINESS MODEL AGENT", bm_tokens, "gpt-4o")

    if evaluator:
        evaluator.log_section_start("PRODUCT AGENT")
    prod_text = run_product_description_agent(profile)
    if evaluator:
        prod_tokens = max(1, len(prod_text) // 3)
        evaluator.log_section_end("PRODUCT AGENT", tokens_used=prod_tokens, model="gpt-4o")
        evaluator.log_agent_estimated_tokens("PRODUCT AGENT", prod_tokens, "gpt-4o")

    if evaluator:
        evaluator.log_section_start("ESG AGENT")
    from chains.memo_synthesis_chain import run_esg_section_chain
    esg_text = run_esg_section_chain(profile, evaluator=evaluator)
    if evaluator:
        esg_tokens = max(1, len(esg_text) // 3)
        evaluator.log_section_end("ESG AGENT", tokens_used=esg_tokens, model="gpt-4o")
        evaluator.log_agent_estimated_tokens("ESG AGENT", esg_tokens, "gpt-4o")

    if evaluator:
        evaluator.log_section_start("EXIT AGENT")
    from chains.memo_synthesis_chain import run_exit_strategies_chain
    exit_text = run_exit_strategies_chain(profile, evaluator=evaluator)
    if evaluator:
        exit_tokens = max(1, len(exit_text) // 3)
        evaluator.log_section_end("EXIT AGENT", tokens_used=exit_tokens, model="gpt-4o")
        evaluator.log_agent_estimated_tokens("EXIT AGENT", exit_tokens, "gpt-4o")

    if evaluator:
        evaluator.log_section_start("FOLLOW-UP AGENT")
    from chains.memo_synthesis_chain import run_followup_section_chain
    follow_text = run_followup_section_chain(profile, evaluator=evaluator)
    if evaluator:
        follow_tokens = max(1, len(follow_text) // 3)
        evaluator.log_section_end("FOLLOW-UP AGENT", tokens_used=follow_tokens, model="gpt-4o")
        evaluator.log_agent_estimated_tokens("FOLLOW-UP AGENT", follow_tokens, "gpt-4o")

    memo_body = f"""
1. DETAILED SUMMARY
{clean_memo_section(run_detailed_summary_chain(profile, evaluator))}

2. COMPANY OVERVIEW
{clean_memo_section(format_company_overview_section(profile))}

3. PROBLEM STATEMENT
{clean_memo_section(run_problem_statement_chain(profile, evaluator))}
    
4. SOLUTION OVERVIEW
{clean_memo_section(run_solution_overview_chain(profile, evaluator))}
    
5. PRODUCT/SERVICE DESCRIPTION
{clean_memo_section(prod_text)}
    
6. MARKET SIZE & ANALYSIS
{clean_memo_section(generate_market_size_section(profile, evaluator))}
{clean_memo_section(getattr(profile, 'sector', ''))}

7. COMPETITORS
{clean_memo_section(generate_competitive_landscape(profile))}
{clean_memo_section(getattr(profile, 'competitive_summary', ''))}

8. BUSINESS MODEL
{clean_memo_section(bm_text)}

9. TECHNICAL DUE DILIGENCE
{clean_memo_section(format_technical_dd_section(profile))}

10. FINANCIAL ANALYSIS
{clean_memo_section(format_enhanced_financials_section(profile, current_date))}

{clean_memo_section(format_financial_history_section(profile))}

11. TEAM & MANAGEMENT
{clean_memo_section(generate_team_section(profile))}

12. ESG CONSIDERATIONS
{clean_memo_section(esg_text)}

13. RISKS
{clean_memo_section(run_risks_section_agent(profile))}

14. INVESTMENT & EXIT STRATEGIES
{clean_memo_section(exit_text)}

15. COUNTERFACTUAL ANALYSIS: WHAT IF WE DON'T INVEST?
{clean_memo_section(generate_counterfactual_section(profile))}

16. FOLLOW-UP QUESTIONS & NEXT STEPS
{clean_memo_section(follow_text)}
"""
    discussion = generate_discussion_section(memo_body)
    return deduplicate_memo(f"{memo_body}\n17. AI DISCUSSION AND COMMENTARY\n{clean_discussion_section(discussion)}\n\n---\nGenerated by VC Analysis System on {current_date}\nData Sources: Company documents, market research, competitive intelligence, technical analysis\nAnalysis Framework: Multi-agent AI system with specialized domain expertise\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_file1> [<path_to_file2> ...]")
        sys.exit(1)

    file_paths = sys.argv[1:]
    for file_path in file_paths:
        print(f"Extracting text and structured data from: {file_path}")
        
        # Initialize evaluation tracker early to capture extraction timing as a separate bucket
        from evaluation_metrics.core.evaluation_metrics import MemoEvaluator
        evaluator = MemoEvaluator()
        evaluator.start_evaluation()

        # --- Extraction & caching (timed) ---
        evaluator.log_section_start("EXTRACTION")
        extracted = load_from_cache(file_path)
        if extracted is None:
            try:
                extracted = extract_text(file_path, return_structured=True)
                # Validate extraction quality
                quality_report = validate_extraction_quality(extracted)
                if quality_report["recommendation"] == "reprocess":
                    print(f"⚠️ [Quality Check] Extraction quality low (score: {quality_report['quality_score']})")
                    print(f"⚠️ [Quality Check] Missing: {quality_report['missing_critical']}")
                    print("⚠️ [Quality Check] Consider reprocessing with different extraction method")
                else:
                    print(f"✅ [Quality Check] Extraction quality acceptable (score: {quality_report['quality_score']})")
                save_to_cache(file_path, extracted)
                print(f"[CACHE] Saved extraction for {file_path}")
            except Exception as e:
                print(f"Error extracting {file_path}: {e}")
                evaluator.log_section_end("EXTRACTION", tokens_used=0, model="local")
                continue
        else:
            print(f"[CACHE] Loaded extraction for {file_path}")
        evaluator.log_section_end("EXTRACTION", tokens_used=0, model="local")

        text = extracted["text"]
        tables = extracted["tables"]
        figures = extracted["figures"]

        clear_collection()
        profile = StartupProfile()

        # Adding structured data to profile if available (AFTER profile creation)
        structured_data = extracted.get("structured_data", {})
        if structured_data:
            print(f"[Structured Data] Found: {list(structured_data.keys())}")
            # Set the structured data on the profile
            profile.structured_data = structured_data
            print(f"[Structured Data] Set profile.structured_data with {len(structured_data)} items")
            
            # Also map key fields directly to profile attributes
            field_mapping = {
                'market_size': 'TAM',
                'funding': 'funding_amount', 
                'patents': 'patent_count',
                'employees': 'employees_count',
                # Dynamic technical field mapping based on actual data
                'performance_value': 'performance_metric',
                'capacity_value': 'capacity_metric',
                'efficiency_value': 'efficiency_metric',
                'accuracy_value': 'accuracy_metric',
                'reliability_value': 'reliability_metric',
                'speed_value': 'speed_metric'
            }
            
            for source_key, profile_key in field_mapping.items():
                if source_key in structured_data and hasattr(profile, profile_key):
                    value = structured_data[source_key]
                    setattr(profile, profile_key, value)
                    # Only set source field if it exists in the schema
                    source_field = f"{profile_key}_source"
                    if hasattr(profile, source_field):
                        setattr(profile, source_field, "enhanced_extraction")
                    print(f"[Structured Data] Set {profile_key} = {value}")
        
        # Tracking the full pipeline with real timing
        evaluator.log_section_start("COMPLETE ANALYSIS PIPELINE")
        start_time = time.time()
        
        # Debug: Show what structured data we have before running the pipeline
        if hasattr(profile, 'structured_data') and profile.structured_data:
            print(f"[DEBUG] Profile has structured_data: {list(profile.structured_data.keys())}")
        else:
            print("[DEBUG] Profile has no structured_data")
        
        # Add timing for each major step
        evaluator.log_section_start("ORCHESTRATION")
        profile = run_all_sequential_with_text(text, profile, file_path, evaluator)
        print(f"[DEBUG] Profile after orchestration: {profile}")
        if profile is None:
            print("[ERROR] Profile is None after orchestration!")
            return
        evaluator.log_section_end("ORCHESTRATION", tokens_used=0, model="local")
        
        pipeline_time = time.time() - start_time
        
        # Populating structured data
        if profile is None:
            print("[ERROR] Profile is None - cannot continue with memo generation")
            return
        profile.tables = tables
        profile.figures = figures

        # Extracting images from PDF and generate chart 
        # Using extraction_cache/ for intermediate image extraction only
        intermediate_dir = CACHE_DIR
        output_dir = "out"
        os.makedirs(output_dir, exist_ok=True)
        
        evaluator.log_section_start("VISUAL EXTRACTION")
        extracted_image_paths = extract_images_from_pdf(file_path, intermediate_dir)
        company_name = profile.name or "unknown_company"
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        market_chart_path = None
        if hasattr(profile, "market_size_by_year") and profile.market_size_by_year:
            chart_path = os.path.join(output_dir, f"{company_name.replace(' ', '_')}_market_chart_{date_str}.png")
            generate_sample_market_chart(profile.market_size_by_year, chart_path)
            market_chart_path = chart_path
        evaluator.log_section_end("VISUAL EXTRACTION", tokens_used=0, model="local")
        
        # Attaching visuals to profile for use in memo formatting
        profile.extracted_image_paths = extracted_image_paths
        profile.market_chart_path = market_chart_path
        
        # Tracking memo generation with real timing
        evaluator.log_section_start("MEMO GENERATION")
        memo_start_time = time.time()
        # Build final memo with internal agent timing to avoid double execution
        memo_text = format_memo(profile, evaluator)
        memo_time = time.time() - memo_start_time
        
        # Estimating tokens for memo generation based on content length
        memo_tokens = len(memo_text) // 3  # Rough estimate: 1 token per 3 characters
        evaluator.log_section_end("MEMO GENERATION", tokens_used=memo_tokens, model="gpt-4o")
        
        print(memo_text)
        
        # Print token usage summary
        evaluator.print_token_summary()
        
        print("\n" + "="*80)
        print("EVALUATION METRICS")
        print("="*80)
        
        # Tracking document creation
        evaluator.log_section_start("DOCUMENT CREATION")
        docx_filename = f"memo_{company_name.replace(' ', '_')}_{date_str}.docx"
        docx_path = os.path.join(output_dir, docx_filename)
        save_memo_with_template(memo_text, profile, docx_path)
        convert_docx_to_pdf(docx_path)
        evaluator.log_section_end("DOCUMENT CREATION", tokens_used=0, model="local")

        # Close the full pipeline timer here (covers extraction → memo → document)
        estimated_tokens = min(len(text) // 2, 8000)  # Conservative estimate
        evaluator.log_section_end("COMPLETE ANALYSIS PIPELINE", tokens_used=estimated_tokens, model="gpt-4o-mini")
        
        # Evaluating the complete memo (using tracked data)
        print("\n🔍 Evaluating memo quality and performance...")
        metrics = evaluator.evaluate_memo(memo_text)
        
        # Saving detailed metrics for academic analysis
        evaluation_dir = "evaluation_results"
        pdf_name = Path(file_path).stem
        metrics_file = save_evaluation_metrics(metrics, pdf_name, evaluation_dir)
        
        # Generating summary of evaluation metrics
        from evaluation_metrics.core.integrate_evaluation import create_academic_summary
        summary_file = create_academic_summary(metrics_file, evaluation_dir)
        
        # Print evaluation summary
        print_evaluation_summary(metrics, evaluator, metrics_file, summary_file)
        
        # Generate Excel output with comprehensive analysis
        try:
            excel_file = generate_excel_output(metrics, company_name, date_str, evaluation_dir)
            if excel_file:
                print(f"📈 Excel analysis saved to: {excel_file}")
        except ImportError:
            print("⚠️ pandas not available - skipping Excel output")
        except Exception as e:
            print(f"⚠️ Error generating Excel output: {e}")

        # Simple evaluation export (new directory)
        try:
            from evaluation_metrics.core.simple_memo_evaluator import evaluate_simple_memo
            simple_dir = "memo_evaluation_results"
            simple_path = evaluate_simple_memo(
                memo_text=memo_text,
                output_dir=simple_dir,
                pdf_name=Path(file_path).stem,
                evaluator=evaluator,
                profile=profile,
                existing_metrics=metrics
            )
            print(f"🧾 Simple evaluation saved to: {simple_path}")
        except Exception as e:
            print(f"⚠️ Simple evaluator failed: {e}")


if __name__ == "__main__":
    main()
