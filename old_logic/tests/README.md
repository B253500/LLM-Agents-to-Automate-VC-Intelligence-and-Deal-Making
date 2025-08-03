# Tests

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
