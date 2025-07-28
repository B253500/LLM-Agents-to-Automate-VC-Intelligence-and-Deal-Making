#!/usr/bin/env python3
"""
Analyze dependencies for the investment memo generation workflow (main.py)
"""

import os
import ast
import importlib
from pathlib import Path

def analyze_imports(file_path):
    """Analyze imports in a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        
        return imports
    except Exception as e:
        return [f"Error parsing {file_path}: {e}"]

def check_file_usage():
    """Check which files are actually used by main.py"""
    
    print("🔍 Analyzing Investment Memo Workflow Dependencies")
    print("=" * 60)
    
    # Core files used by main.py
    core_files = [
        "main.py",
        "core/download_utils.py",
        "core/utils.py", 
        "core/orchestration.py",
        "core/schemas.py",
        "core/vector_store.py",
        "core/visual_utils.py",
        "core/coresignal_utils.py",
        "core/perplexity_utils.py",
        "core/hybrid_context.py",
        "core/llm_utils.py",
        "core/external_enrichment.py"
    ]
    
    # Chain files
    chain_files = [
        "chains/pitch_deck_chain.py",
        "chains/technical_dd_chain.py", 
        "chains/market_sizing_chain.py",
        "chains/financial_analysis_chain.py",
        "chains/competitive_intel_chain.py",
        "chains/risk_assessment_chain.py",
        "chains/product_description_chain.py",
        "chains/memo_synthesis_chain.py",
        "chains/business_model_chain.py",
        "chains/esg_chain.py",
        "chains/exit_strategy_chain.py",
        "chains/follow_up_chain.py"
    ]
    
    # Agent files
    agent_files = [
        "agents/technical_dd_agent.py",
        "agents/market_sizing_agent.py",
        "agents/competitive_intel_agent.py", 
        "agents/founder_profiling_agent.py",
        "agents/financial_analysis_agent.py",
        "agents/risk_assessment_agent.py",
        "agents/deck_agent.py",
        "agents/vc_report_agent.py"
    ]
    
    # Configuration and template files
    config_files = [
        "requirements.txt",
        "template.docx",
        ".env"
    ]
    
    # Data directories
    data_dirs = [
        "data/",
        "extraction_cache/",
        "logo/"
    ]
    
    # Files that are NOT used by main.py (redundant)
    redundant_files = [
        # Test files
        "test_*.py",
        "test_url_fix.py",
        "test_think_tag_cleaning.py", 
        "test_perplexity_production.py",
        "test_url_cleaning.py",
        "test_perplexity_urls.py",
        "test_financial_chain_simple.py",
        "test_financial_web_search.py",
        "test_financial_clean.py",
        "test_main_technical.py",
        "test_prompt_debug.py",
        "test_context_debug.py",
        "test_llm_output.py",
        "test_technical_llm_analysis.py",
        "test_technical_extraction.py",
        "test_market_agent.py",
        "test_financial_agent.py",
        "test_technical_agent.py",
        "test_roadmap_extraction.py",
        "test_context_content.py",
        "test_technical_context.py",
        "test_context_simple.py",
        "test_real_context.py",
        "test_context_generation.py",
        "test_google_vision.py",
        "test_enhanced_extraction.py",
        "test_coresignal.py",
        "test_run_memo_generator.py",
        "test_enrich_executive.py",
        "test_template_insertion.py",
        
        # Old/backup files
        "old_agents/",
        "memo_api/",  # This is for web API, not main.py
        "n8n_data/",  # This is for n8n workflow
        
        # Evaluation files
        "evaluation_metrics.py",
        "integrate_evaluation.py",
        "evaluation_results/",
        "methodology_update_suggestions.md",
        "AI_Memo_Review_Template.numbers",
        
        # Other workflow files
        "run_crewai_analysis.py",
        "run_all_sources.py",
        "run_memo.py",
        "automate_memo_pipeline.py",
        "analyze_vc_questions.py",
        "api_server.py",
        "extract_text_and_figures.py",
        "generate_pdf_memo.py",
        "generate_pdf.py",
        "generate_html.py",
        "html_to_pdf.py",
        "html_to_pdf_chrome.py",
        "download_reports.py",
        
        # Output files
        "memo_*.html",
        "memo_*.pdf",
        "memo_response.json",
        "upload.json",
        "vc_report_analysis.pdf",
        "vc_report_analysis_results.json",
        "downloaded_reports.json",
        
        # Temporary files
        "temp_images/",
        "memo.html",
        "test_memo.html",
        "memo_test-run-storedot_*.pdf",
        "memo_test-run-storedot_*.html",
        "memo_memo_*.html",
        "memo_memo_*.pdf",
        
        # Configuration files not used by main.py
        "docker-compose.yml",
        "Dockerfile",
        "conftest.py",
        "cloud-credentials.json",
        "DejaVuSans.ttf",
        ".pre-commit-config.yaml",
        ".python-version",
        "Architecture.md",
        "Project Goal.docx",
        "~$sk.docx"
    ]
    
    print("\n📋 **Files Used by Investment Memo Workflow (main.py):**")
    print("-" * 50)
    
    all_used_files = core_files + chain_files + agent_files + config_files + data_dirs
    
    for file in all_used_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} (missing)")
    
    print(f"\n📊 **Summary:**")
    print(f"Core files: {len(core_files)}")
    print(f"Chain files: {len(chain_files)}") 
    print(f"Agent files: {len(agent_files)}")
    print(f"Config files: {len(config_files)}")
    print(f"Data directories: {len(data_dirs)}")
    print(f"Total files used: {len(all_used_files)}")
    
    print(f"\n🗑️ **Redundant Files (can be cleaned up):**")
    print("-" * 50)
    
    redundant_count = 0
    for pattern in redundant_files:
        if pattern.endswith("/"):
            # Directory
            if os.path.exists(pattern):
                print(f"📁 {pattern} (entire directory)")
                redundant_count += 1
        elif pattern.endswith("*"):
            # Pattern
            import glob
            matches = glob.glob(pattern)
            for match in matches:
                print(f"📄 {match}")
                redundant_count += 1
        else:
            # Single file
            if os.path.exists(pattern):
                print(f"📄 {pattern}")
                redundant_count += 1
    
    print(f"\n📊 **Cleanup Summary:**")
    print(f"Files used by main.py: {len(all_used_files)}")
    print(f"Redundant files: {redundant_count}")
    print(f"Total files in project: {len(os.listdir('.'))}")
    
    return all_used_files, redundant_files

if __name__ == "__main__":
    check_file_usage() 