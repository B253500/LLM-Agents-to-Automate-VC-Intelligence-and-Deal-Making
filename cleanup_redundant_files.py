#!/usr/bin/env python3
"""
Cleanup script to remove redundant files and organize the project
"""

import os
import glob
import shutil

def cleanup_redundant_files():
    """Remove redundant files and directories"""
    
    redundant_items = [
        # Test files
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
        
        # Evaluation files
        "evaluation_metrics.py",
        "integrate_evaluation.py",
        "evaluation_results/",
        "methodology_update_suggestions.md",
        "AI_Memo_Review_Template.numbers",
        
        # Other workflow files
        "run_crewai_analysis.py",
        "run_all_sources.py",
        
        # Output files
        "memo_response.json",
        "upload.json",
        "downloaded_reports.json",
        
        # Temporary files
        "temp_images/",
        "memo.html",
        "test_memo.html",
        
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
    
    # Pattern-based files
    patterns = [
        "memo_*.html",
        "memo_*.pdf",
        "memo_test-run-storedot_*.pdf",
        "memo_test-run-storedot_*.html", 
        "memo_memo_*.html",
        "memo_memo_*.pdf"
    ]
    
    print("🧹 Cleaning up redundant files...")
    print("=" * 50)
    
    removed_count = 0
    
    # Remove specific files
    for item in redundant_items:
        if os.path.exists(item):
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                    print(f"🗑️ Removed directory: {item}")
                else:
                    os.remove(item)
                    print(f"🗑️ Removed file: {item}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Error removing {item}: {e}")
    
    # Remove pattern-based files
    for pattern in patterns:
        matches = glob.glob(pattern)
        for match in matches:
            try:
                os.remove(match)
                print(f"🗑️ Removed pattern file: {match}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Error removing {match}: {e}")
    
    print(f"\n📊 Cleanup Summary:")
    print(f"Total files removed: {removed_count}")
    
    return removed_count

if __name__ == "__main__":
    cleanup_redundant_files()
