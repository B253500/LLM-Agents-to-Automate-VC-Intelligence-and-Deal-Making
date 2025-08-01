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
from core.download_utils import extract_text, get_cache_path, load_from_cache, save_to_cache
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
from chains.pitch_deck_chain import run_pitch_deck_chain
from chains.technical_dd_chain import run_technical_dd_chain
from chains.market_sizing_chain import run_market_sizing_chain
from chains.financial_analysis_chain import run_financial_analysis_chain
from chains.competitive_intel_chain import run_competitive_intel_chain
from chains.risk_assessment_chain import run_risk_assessment_chain
from chains.product_description_chain import run_product_description_chain
from chains.memo_synthesis_chain import (
    run_detailed_summary_chain,
    run_problem_statement_chain,
    run_solution_overview_chain,
    run_business_model_chain,
    run_risks_section_chain,
    run_team_section_chain,
    run_esg_section_chain,
    run_analyst_commentary_chain,
    run_exit_strategies_chain,
    run_followup_section_chain
)

# Agent imports
from agents.technical_dd_agent import build_technical_dd_agent, format_technical_dd_section
from agents.market_sizing_agent import build_market_sizing_agent, generate_market_size_section
from agents.competitive_intel_agent import build_competitive_intel_agent, generate_competitive_landscape
from agents.founder_profiling_agent import build_founder_profiling_agent, generate_team_section
from agents.risk_assessment_agent import build_risk_assessment_agent, generate_discussion_section, generate_counterfactual_section

CACHE_DIR = "extraction_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def run_pitch_deck_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    from chains.pitch_deck_chain import run_pitch_deck_chain_with_text as run_pitch_chain
    return run_pitch_chain(full_text, profile)


def run_technical_dd_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_technical_dd_chain(profile)


def run_founder_profiling_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    from agents.founder_profiling_agent import run_founder_profiling_chain_with_text as run_founder_chain
    return run_founder_chain(full_text, profile)


def run_market_sizing_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_market_sizing_chain(profile)


def run_financial_analysis_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    try:
        # Use the enhanced financial analysis chain from new_main.py
        from chains.financial_analysis_chain import run_financial_analysis_chain
        
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
        print(f"[Financial Analysis] Error in enhanced chain: {e}")
        # Fallback to original simple approach
        try:
            from chains.financial_analysis_chain import run_financial_analysis_chain
            return run_financial_analysis_chain(profile)
        except ImportError as import_error:
            print(f"[Financial Analysis] Import error: {import_error}")
            # Final fallback to basic financial formatting
            return profile


def run_competitive_intel_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_competitive_intel_chain(profile)


def run_risk_assessment_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_risk_assessment_chain(profile)


def run_followup_section_chain_with_text(full_text: str, profile: StartupProfile) -> StartupProfile:
    return run_followup_section_chain(profile)


def format_memo(profile: StartupProfile) -> str:
    """Format the complete investment memo using refactored modules."""
    current_date = datetime.now().strftime("%B %d, %Y")

    memo_body = f"""
1. DETAILED SUMMARY
{clean_think_tags_and_debugging(clean(run_detailed_summary_chain(profile)))}

2. COMPANY OVERVIEW
{clean_think_tags_and_debugging(clean(format_company_overview_section(profile)))}

3. PROBLEM STATEMENT
{clean_think_tags_and_debugging(clean(run_problem_statement_chain(profile)))}
    
4. SOLUTION OVERVIEW
{clean_think_tags_and_debugging(clean(run_solution_overview_chain(profile)))}
    
5. PRODUCT/SERVICE DESCRIPTION
{clean_think_tags_and_debugging(run_product_description_chain(profile))}
    
6. MARKET SIZE & ANALYSIS
{clean_think_tags_and_debugging(generate_market_size_section(profile))}
{clean_think_tags_and_debugging(clean(getattr(profile, 'sector', '')))}

7. COMPETITORS
{clean_think_tags_and_debugging(clean(generate_competitive_landscape(profile)))}
{clean_think_tags_and_debugging(clean(getattr(profile, 'competitive_summary', '')))}

8. BUSINESS MODEL
{clean_think_tags_and_debugging(run_business_model_chain(profile))}

9. TECHNICAL DUE DILIGENCE
{clean_think_tags_and_debugging(clean(format_technical_dd_section(profile)))}

10. FINANCIAL ANALYSIS
{clean_think_tags_and_debugging(format_enhanced_financials_section(profile, current_date))}

{clean_think_tags_and_debugging(format_financial_history_section(profile))}

11. TEAM & MANAGEMENT
{clean_think_tags_and_debugging(clean(generate_team_section(profile)))}

12. ESG CONSIDERATIONS
{clean_think_tags_and_debugging(run_esg_section_chain(profile))}

13. RISKS
{clean_think_tags_and_debugging(run_risks_section_chain(profile))}

14. INVESTMENT & EXIT STRATEGIES
{clean_think_tags_and_debugging(run_exit_strategies_chain(profile))}

15. COUNTERFACTUAL ANALYSIS: WHAT IF WE DON'T INVEST?
{clean_think_tags_and_debugging(generate_counterfactual_section(profile))}

16. FOLLOW-UP QUESTIONS & NEXT STEPS
{clean_think_tags_and_debugging(clean(run_followup_section_chain(profile)))}
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
        
        # --- Caching logic ---
        extracted = load_from_cache(file_path)
        if extracted is None:
            try:
                extracted = extract_text(file_path, return_structured=True)
                
                # Validate extraction quality
                from core.download_utils import validate_extraction_quality
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
                continue
        else:
            print(f"[CACHE] Loaded extraction for {file_path}")
        
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
        
        # Initialising evaluation tracker with real-time tracking
        from evaluation_metrics.core.evaluation_metrics import MemoEvaluator
        evaluator = MemoEvaluator()
        evaluator.start_evaluation()
        
        # Tracking the main analysis pipeline with real timing
        evaluator.log_section_start("COMPLETE ANALYSIS PIPELINE")
        start_time = time.time()
        
        # Debug: Show what structured data we have before running the pipeline
        if hasattr(profile, 'structured_data') and profile.structured_data:
            print(f"[DEBUG] Profile has structured_data: {list(profile.structured_data.keys())}")
        else:
            print("[DEBUG] Profile has no structured_data")
        
        # Add timing for each major step
        evaluator.log_section_start("PITCH DECK EXTRACTION")
        profile = run_all_sequential_with_text(text, profile, file_path, evaluator)
        evaluator.log_section_end("PITCH DECK EXTRACTION", tokens_used=0, model="local")
        
        pipeline_time = time.time() - start_time
        
        # Estimating tokens based on text length and processing time
        estimated_tokens = min(len(text) // 2, 8000)  # Conservative estimate
        evaluator.log_section_end("COMPLETE ANALYSIS PIPELINE", tokens_used=estimated_tokens, model="gpt-4o-mini")
        
        # Populating structured data
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
        memo_text = format_memo(profile)
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


if __name__ == "__main__":
    main()
