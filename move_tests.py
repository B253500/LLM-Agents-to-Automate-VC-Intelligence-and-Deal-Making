#!/usr/bin/env python3
"""
Move test files to tests/ directory while avoiding duplicates
"""

import os
import shutil
from pathlib import Path

def get_existing_tests():
    """Get list of existing test files in tests/ directory"""
    tests_dir = "tests"
    existing_tests = []
    
    if os.path.exists(tests_dir):
        for file in os.listdir(tests_dir):
            if file.endswith('.py') and file.startswith('test_'):
                existing_tests.append(file)
    
    return existing_tests

def get_root_test_files():
    """Get list of test files in root directory"""
    root_tests = []
    for file in os.listdir('.'):
        if file.endswith('.py') and file.startswith('test_'):
            root_tests.append(file)
    
    return root_tests

def categorize_tests():
    """Categorize test files by type"""
    
    # Core functionality tests (should be moved)
    core_tests = [
        "test_market_agent.py",
        "test_financial_agent.py", 
        "test_technical_agent.py",
        "test_coresignal.py",
        "test_enhanced_extraction.py",
        "test_enrich_executive.py",
        "test_roadmap_extraction.py"
    ]
    
    # Debug/development tests (can be removed)
    debug_tests = [
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
        "test_context_content.py",
        "test_technical_context.py",
        "test_context_simple.py",
        "test_real_context.py",
        "test_context_generation.py",
        "test_google_vision.py",
        "test_run_memo_generator.py",
        "test_template_insertion.py"
    ]
    
    return core_tests, debug_tests

def move_tests():
    """Move test files to tests/ directory"""
    
    print("📁 Moving test files to tests/ directory...")
    print("=" * 50)
    
    # Get existing and root test files
    existing_tests = get_existing_tests()
    root_tests = get_root_test_files()
    core_tests, debug_tests = categorize_tests()
    
    print(f"📊 Current state:")
    print(f"   Tests in tests/: {len(existing_tests)}")
    print(f"   Tests in root: {len(root_tests)}")
    print(f"   Core tests to move: {len(core_tests)}")
    print(f"   Debug tests to remove: {len(debug_tests)}")
    
    # Create tests directory if it doesn't exist
    os.makedirs("tests", exist_ok=True)
    
    moved_count = 0
    removed_count = 0
    
    print(f"\n📦 Moving core test files...")
    print("-" * 30)
    
    for test_file in core_tests:
        if test_file in root_tests:
            source_path = test_file
            dest_path = f"tests/{test_file}"
            
            # Check if file already exists in tests/
            if os.path.exists(dest_path):
                print(f"⚠️  {test_file} already exists in tests/ - skipping")
                continue
            
            try:
                shutil.move(source_path, dest_path)
                print(f"✅ Moved: {test_file}")
                moved_count += 1
            except Exception as e:
                print(f"❌ Error moving {test_file}: {e}")
    
    print(f"\n🗑️ Removing debug test files...")
    print("-" * 30)
    
    for test_file in debug_tests:
        if test_file in root_tests:
            try:
                os.remove(test_file)
                print(f"🗑️ Removed: {test_file}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Error removing {test_file}: {e}")
    
    print(f"\n📊 Summary:")
    print(f"✅ Moved {moved_count} core test files to tests/")
    print(f"🗑️ Removed {removed_count} debug test files")
    
    # Show final state
    final_root_tests = [f for f in os.listdir('.') if f.endswith('.py') and f.startswith('test_')]
    final_tests_dir = [f for f in os.listdir('tests') if f.endswith('.py') and f.startswith('test_')]
    
    print(f"\n📋 Final state:")
    print(f"   Tests in root: {len(final_root_tests)}")
    print(f"   Tests in tests/: {len(final_tests_dir)}")
    
    if final_root_tests:
        print(f"\n⚠️  Remaining test files in root:")
        for test in final_root_tests:
            print(f"   - {test}")
    
    return moved_count, removed_count

def create_test_readme():
    """Create a README for the tests directory"""
    
    readme_content = """# Tests

This directory contains test files for the investment memo generation workflow.

## Test Categories

### Core Tests
- `test_market_agent.py` - Tests for market sizing agent
- `test_financial_agent.py` - Tests for financial analysis agent  
- `test_technical_agent.py` - Tests for technical due diligence agent
- `test_coresignal.py` - Tests for CoreSignal API integration
- `test_enhanced_extraction.py` - Tests for enhanced text extraction
- `test_enrich_executive.py` - Tests for executive enrichment
- `test_roadmap_extraction.py` - Tests for roadmap extraction

### Agent Tests
- `test_market_sizing.py` - Market sizing functionality tests
- `test_founder_profiling.py` - Founder profiling tests
- `test_competitive_intel.py` - Competitive intelligence tests
- `test_deck_agent.py` - Pitch deck analysis tests
- `test_financial_analysis.py` - Financial analysis tests
- `test_risk_assessment.py` - Risk assessment tests
- `test_technical_dd.py` - Technical due diligence tests

## Running Tests

To run all tests:
```bash
python -m pytest tests/
```

To run a specific test:
```bash
python -m pytest tests/test_market_agent.py
```

## Test Organization

- **Core Tests**: Test core functionality and API integrations
- **Agent Tests**: Test individual agent functionality
- **Integration Tests**: Test end-to-end workflows

## Notes

- Debug and development test files have been removed from the root directory
- Only essential tests are kept in this directory
- Test files follow the naming convention: `test_*.py`
"""
    
    with open("tests/README.md", "w") as f:
        f.write(readme_content)
    
    print("✅ Created tests/README.md")

if __name__ == "__main__":
    moved, removed = move_tests()
    create_test_readme()
    
    print(f"\n🎉 Test organization complete!")
    print(f"📁 Check the tests/ directory for organized test files")
    print(f"📖 See tests/README.md for test documentation") 