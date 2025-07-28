#!/usr/bin/env python3
"""
Organize the project into 3 distinct workflows:
1. Investment Memo Generation (main.py)
2. Web Scraping 
3. Intelligent Email Assistant (n8n workflow)
"""

import os
import shutil
from pathlib import Path

def create_workflow_directories():
    """Create organized workflow directories"""
    
    workflows = {
        "1_investment_memo": {
            "description": "Investment Memo Generation Workflow",
            "main_file": "main.py",
            "files": [
                # Core files
                "core/",
                "agents/",
                "chains/",
                "data/",
                "extraction_cache/",
                "logo/",
                "template.docx",
                "requirements.txt",
                ".env",
                "README.md"
            ]
        },
        "2_web_scraping": {
            "description": "Web Scraping and Data Collection",
            "main_file": "download_reports.py",
            "files": [
                "download_reports.py",
                "scripts/",
                "downloaded_reports.json",
                "vc_report_analysis.pdf",
                "vc_report_analysis_results.json",
                "data/vc_reports/",
                "requirements.txt"
            ]
        },
        "3_email_assistant": {
            "description": "Intelligent Email Assistant (n8n)",
            "main_file": "memo_api/main.py",
            "files": [
                "memo_api/",
                "n8n_data/",
                "api_server.py",
                "run_memo.py",
                "automate_memo_pipeline.py",
                "analyze_vc_questions.py",
                "extract_text_and_figures.py",
                "generate_pdf_memo.py",
                "generate_pdf.py",
                "generate_html.py",
                "html_to_pdf.py",
                "html_to_pdf_chrome.py",
                "requirements.txt"
            ]
        }
    }
    
    print("🏗️ Creating organized workflow structure...")
    print("=" * 60)
    
    for workflow_name, config in workflows.items():
        print(f"\n📁 Creating {workflow_name}/")
        print(f"   Description: {config['description']}")
        print(f"   Main file: {config['main_file']}")
        
        # Create workflow directory
        os.makedirs(workflow_name, exist_ok=True)
        
        # Create README for each workflow
        readme_content = f"""# {config['description']}

## Overview
This workflow handles {config['description'].lower()}.

## Main Entry Point
- **Main file**: `{config['main_file']}`

## Key Files
"""
        
        for file in config['files']:
            if os.path.exists(file):
                readme_content += f"- `{file}`\n"
        
        readme_content += f"""
## Usage
Run the main file to execute this workflow.

## Dependencies
See `requirements.txt` for required packages.
"""
        
        with open(f"{workflow_name}/README.md", 'w') as f:
            f.write(readme_content)
    
    return workflows

def identify_redundant_files():
    """Identify files that can be cleaned up"""
    
    redundant_files = [
        # Test files (all test_*.py)
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
        "memo_*.html",
        "memo_*.pdf", 
        "memo_response.json",
        "upload.json",
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
        "~$sk.docx",
        
        # Analysis files
        "analyze_memo_dependencies.py",
        "organize_project.py"
    ]
    
    return redundant_files

def create_cleanup_script():
    """Create a cleanup script"""
    
    cleanup_script = """#!/usr/bin/env python3
\"\"\"
Cleanup script to remove redundant files and organize the project
\"\"\"

import os
import glob
import shutil

def cleanup_redundant_files():
    \"\"\"Remove redundant files and directories\"\"\"
    
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
    
    print(f"\\n📊 Cleanup Summary:")
    print(f"Total files removed: {removed_count}")
    
    return removed_count

if __name__ == "__main__":
    cleanup_redundant_files()
"""
    
    with open("cleanup_redundant_files.py", "w") as f:
        f.write(cleanup_script)
    
    print("✅ Created cleanup script: cleanup_redundant_files.py")

def main():
    """Main organization function"""
    
    print("🏗️ **Project Organization**")
    print("=" * 60)
    print("Organizing your project into 3 distinct workflows:")
    print("1. Investment Memo Generation (main.py)")
    print("2. Web Scraping (download_reports.py)")
    print("3. Intelligent Email Assistant (n8n workflow)")
    print()
    
    # Create workflow directories
    workflows = create_workflow_directories()
    
    # Create cleanup script
    create_cleanup_script()
    
    # Show redundant files
    redundant_files = identify_redundant_files()
    
    print(f"\n🗑️ **Redundant Files Found:**")
    print("-" * 40)
    redundant_count = 0
    for file in redundant_files:
        if os.path.exists(file):
            print(f"📄 {file}")
            redundant_count += 1
    
    print(f"\n📊 **Summary:**")
    print(f"✅ 3 workflow directories created")
    print(f"✅ Cleanup script created: cleanup_redundant_files.py")
    print(f"🗑️ {redundant_count} redundant files identified")
    print(f"💡 Run 'python cleanup_redundant_files.py' to clean up redundant files")
    
    print(f"\n📋 **Next Steps:**")
    print("1. Review the created workflow directories")
    print("2. Run 'python cleanup_redundant_files.py' to remove redundant files")
    print("3. Move files to appropriate workflow directories as needed")
    print("4. Update any hardcoded paths in your code")

if __name__ == "__main__":
    main() 