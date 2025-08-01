# VC Agents - AI-Powered Investment Memo Generation

> **Intelligent venture capital analysis and automation platform with enhanced AI-powered data extraction**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-✓-green.svg)](https://langchain.com/)
[![OpenAI GPT-4](https://img.shields.io/badge/OpenAI-GPT--4-orange.svg)](https://openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

The VC Agents platform is a comprehensive AI-powered system for generating investment memos from pitch decks, business plans, and call notes. It provides venture capitalists with detailed analysis including market sizing, competitive intelligence, financial analysis, and risk assessment. For founders, it offers insights into how VCs might evaluate your business and simplifies the process of presenting your company to investors.

The system consists of **3 distinct workflows**:
1. **📊 Investment Memo Generation** - Core AI-powered memo creation with enhanced data extraction
2. **🌐 Web Scraping** - Automated discovery and download of VC reports
3. **📧 Email Assistant** - Intelligent email automation with n8n integration

## Limitations

The memo generator produces a strong draft addressing key investor considerations but serves as a starting point, not a finished product. It covers 60-70% of the work, requiring human input for nuance and judgment. The tool may reflect biases in the input and is limited by the underlying AI models. Competitor analysis provides initial insights but should be supplemented with additional research, and market size estimates should include a separate bottoms-up analysis. This tool is for informational purposes only.

## Features

### Smart Document Processing
- Support for multiple document formats (PDF, Word, scanned documents)
- Built-in OCR capability for processing scanned materials using Google Cloud Vision
- AI-powered text extraction with structured data parsing
- Enhanced image and table extraction from PDFs

### AI-Powered Data Extraction
- **Market Data Extraction**: Comprehensive market size, growth rates, and geographic analysis
- **Financial Data Extraction**: Revenue, profitability, growth metrics, and business model analysis
- **Dynamic Schema Management**: Flexible field handling for AI-generated data
- **Enhanced Website Detection**: AI-powered company website detection with validation

### Agentic Research Analysis
- Multi-agent system for specialized analysis (market sizing, competitive intelligence, financial analysis)
- Automated market research and competitor analysis
- Real-time web search integration through Perplexity API
- Comprehensive founder and team background analysis

### Memorandum Generation
- Auto-generated comprehensive investment memorandums
- Professional formatting with customizable templates
- Multiple output formats (PDF, DOCX, HTML)
- Enhanced sections with AI-powered insights

### Feedback and Observability
- Integration with evaluation metrics for quality monitoring
- Performance tracking and cost analysis
- Automated quality assessment and readability scoring

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Docker** (for n8n automation)
- **Git**

### Required API Keys

You'll need to set up the following API keys in your environment variables:

| API Service | Purpose | Required | Setup Instructions |
|-------------|---------|----------|-------------------|
| **OpenAI API** | AI analysis and memo generation | ✅ **REQUIRED** | [Setup Guide](#openai-api-setup) |
| **Perplexity API** | Web search and data enrichment | ✅ **REQUIRED** | [Setup Guide](#perplexity-api-setup) |
| **Google Cloud Vision** | OCR and image processing | ✅ **REQUIRED** | [Setup Guide](#google-cloud-vision-setup) |
| **CoreSignal API** | Company data enrichment (fallback) | ❌ Optional | [Setup Guide](#coresignal-api-setup) |

### Installation

#### 1. Clone the Repository
```bash
git clone <repository-url>
cd new-vc-agents
```

#### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Create .env file
touch .env

# Edit with your API keys
nano .env  # or use your preferred editor
```

Add the following to your `.env` file:

```bash
# === REQUIRED API KEYS ===

# OpenAI API Key (Required for AI analysis)
OPENAI_API_KEY=your_openai_api_key_here

# Perplexity API Key (Required for web search)
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# Google Cloud Vision (Required for OCR)
GOOGLE_APPLICATION_CREDENTIALS=cloud-credentials.json

# === OPTIONAL API KEYS ===

# CoreSignal API Key (Optional - used as fallback)
CORESIGNAL_API_KEY=your_coresignal_api_key_here

# === SYSTEM CONFIGURATION ===
DEFAULT_MODEL=gpt-4o
DEFAULT_TEMPERATURE=0.2
OUTPUT_DIR=out
```

### API Setup Instructions

#### **🔑 OpenAI API Setup**

1. **Get API Key**:
   - Go to [OpenAI Platform](https://platform.openai.com/api-keys)
   - Sign up/login to your account
   - Click "Create new secret key"
   - Copy the key (starts with `sk-`)

2. **Add to .env**:
   ```bash
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

3. **Usage**: Used for all AI analysis, memo generation, and data extraction

#### **🔑 Perplexity API Setup**

1. **Get API Key**:
   - Go to [Perplexity API](https://www.perplexity.ai/settings/api)
   - Sign up/login to your account
   - Click "Generate API Key"
   - Copy the key

2. **Add to .env**:
   ```bash
   PERPLEXITY_API_KEY=your-perplexity-key-here
   ```

3. **Usage**: Used for web search, company data enrichment, and market research

#### **🔑 Google Cloud Vision Setup**

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable Cloud Vision API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Cloud Vision API"
   - Click "Enable"

3. **Create Service Account**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in details and create

4. **Download Credentials**:
   - Click on your service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download the file

5. **Place in Project**:
   ```bash
   # Rename the downloaded file to cloud-credentials.json
   mv ~/Downloads/your-project-credentials.json cloud-credentials.json
   
   # Ensure it's in the project root
   ls cloud-credentials.json
   ```

6. **Usage**: Used for OCR processing of PDFs and image text extraction

#### **🔑 CoreSignal API Setup (Optional)**

1. **Get API Key**:
   - Go to [CoreSignal](https://coresignal.com/)
   - Sign up for an account
   - Navigate to API section
   - Generate API key

2. **Add to .env**:
   ```bash
   CORESIGNAL_API_KEY=your-coresignal-key-here
   ```

3. **Usage**: Used as fallback for company data when AI detection fails

### Verify Setup

Test your API key configuration:

```bash
# Test API keys
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('🔑 API Key Status:')
print('OpenAI:', '✅ SET' if os.getenv('OPENAI_API_KEY') else '❌ NOT SET')
print('Perplexity:', '✅ SET' if os.getenv('PERPLEXITY_API_KEY') else '❌ NOT SET')
print('Google Cloud:', '✅ SET' if os.path.exists('cloud-credentials.json') else '❌ NOT SET')
print('CoreSignal:', '✅ SET' if os.getenv('CORESIGNAL_API_KEY') else '❌ NOT SET (Optional)')
"
```

## Usage

### Investment Memo Generation

Generate comprehensive investment memos from pitch deck PDFs:

```bash
# Generate memo from pitch deck
python main.py data/sample_pitch_deck.pdf

# Output will be saved to out/ directory
```

**Example Output Structure:**
```
out/
├── memo_CompanyName_20250728_143022.docx
├── memo_CompanyName_20250728_143022.pdf
└── memo_CompanyName_20250728_143022.html
```

### Web Scraping Workflow

Automated discovery and download of VC reports:

```bash
# Run comprehensive web scraping
cd web_scraping
python download_reports.py

# Or run individual scrapers
python scripts/download_beauhurst.py
python scripts/download_pitchbook.py
python scripts/download_crunchbase.py
```

### Email Assistant Workflow

Intelligent email automation with n8n integration:

```bash
# Start n8n Automation Hub
cd n8n
docker-compose up -d

# Start Email API Server
cd email_assistant
python api_server.py
```

## Project Structure

```
new-vc-agents/
├── 📊 Investment Memo Generation (Core)
│   ├── main.py                    # Core memo generation orchestrator
│   ├── agents/                    # AI agents for analysis
│   │   ├── market_sizing_agent.py
│   │   ├── competitive_intel_agent.py
│   │   ├── financial_analysis_agent.py
│   │   ├── founder_profiling_agent.py
│   │   ├── risk_assessment_agent.py
│   │   ├── technical_dd_agent.py
│   │   ├── deck_agent.py
│   │   ├── crewai_agents.py
│   │   └── vc_report_agent.py
│   ├── chains/                    # LangChain processing chains
│   │   ├── business_model_chain.py
│   │   ├── competitive_intel_chain.py
│   │   ├── financial_analysis_chain.py
│   │   ├── market_sizing_chain.py
│   │   ├── memo_synthesis_chain.py
│   │   ├── pitch_deck_chain.py
│   │   ├── risk_assessment_chain.py
│   │   ├── technical_dd_chain.py
│   │   ├── follow_up_chain.py
│   │   ├── esg_chain.py
│   │   ├── exit_strategy_chain.py
│   │   └── product_description_chain.py
│   ├── core/                      # Core utilities and functions
│   │   ├── download_utils.py      # Enhanced PDF processing with AI extraction
│   │   ├── external_enrichment.py # Web search and data enrichment
│   │   ├── hybrid_context.py      # Context management
│   │   ├── llm_utils.py          # LLM integration
│   │   ├── orchestration.py       # Workflow orchestration
│   │   ├── perplexity_utils.py    # Perplexity API integration
│   │   ├── report_loader.py       # Report loading utilities
│   │   ├── schemas.py             # Enhanced data schemas with dynamic fields
│   │   ├── utils.py               # General utilities
│   │   ├── vector_store.py        # Vector database operations
│   │   ├── visual_utils.py        # Image processing
│   │   ├── financial_formatters.py # Enhanced financial formatting
│   │   ├── memo_formatters.py     # Memo formatting utilities
│   │   ├── document_generators.py # Document generation
│   │   ├── text_cleaners.py       # Text cleaning utilities
│   │   ├── coresignal_utils.py    # CoreSignal API integration
│   │   └── evaluation_utils.py    # Evaluation utilities
│   ├── data/                      # Data storage
│   │   ├── vc_reports/            # Downloaded VC reports (284+ PDFs)
│   │   └── *.pdf                  # Sample pitch decks
│   ├── extraction_cache/           # Cached extracted data
│   ├── out/                       # Generated memo outputs
│   ├── evaluation_results/         # Evaluation metrics and results
│   ├── template.docx              # Memo template
│   ├── DejaVuSans.ttf            # Font for PDF generation
│   └── cloud-credentials.json     # Google Cloud Vision API
├── 🌐 Web Scraping Workflow
│   ├── download_reports.py        # Main scraping orchestrator
│   ├── scripts/                   # Individual scraping scripts
│   │   ├── download_beauhurst.py  # Beauhurst report scraping
│   │   ├── download_crunchbase.py # Crunchbase report scraping
│   │   ├── download_pitchbook.py  # PitchBook report scraping
│   │   └── download_techcrunch.py # TechCrunch article scraping
│   ├── data/                      # Downloaded reports
│   └── results/                   # Scraping results and analysis
├── 📧 Email Assistant Workflow
│   ├── api_server.py              # FastAPI server for email processing
│   ├── api/                       # API services
│   │   └── services/
│   │       ├── linkedin.py        # LinkedIn data extraction
│   │       ├── market_analysis.py # Market analysis service
│   │       ├── market_summary.py  # Market summary generation
│   │       └── ocr.py             # OCR processing service
│   ├── templates/                 # Email templates
│   ├── generate_pdf_memo.py       # PDF memo generation
│   ├── analyze_vc_questions.py    # VC question analysis
│   └── extract_text_and_figures.py # Text and figure extraction
├── 🤖 n8n Automation Hub
│   ├── docker-compose.yml         # Docker configuration
│   ├── Dockerfile                 # Custom n8n image with Python/Playwright
│   ├── data/                      # n8n data persistence
│   ├── workflows/                 # Organized workflow directories
│   │   ├── email_assistant/       # Email automation workflows
│   │   └── web_scraping/          # Web scraping automation workflows
│   └── README.md                  # n8n setup and documentation
├── 📊 Evaluation Metrics
│   ├── core/                      # Evaluation core components
│   │   ├── evaluation_metrics.py  # Memo evaluation logic
│   │   └── integrate_evaluation.py # Evaluation integration
│   ├── config/                    # Evaluation configuration
│   ├── utils/                     # Evaluation utilities
│   └── templates/                 # Evaluation templates
├── 🧪 Tests
│   ├── test_competitive_intel.py
│   ├── test_deck_agent.py
│   ├── test_financial_agent.py
│   ├── test_market_agent.py
│   └── test_technical_agent.py
├── 🔧 Configuration Files
│   ├── config.py                  # System configuration
│   ├── .env                       # Environment variables
│   ├── requirements.txt           # Python dependencies
│   ├── .python-version            # Python version specification
│   ├── .pre-commit-config.yaml   # Code quality hooks
│   ├── .gitignore                 # Git ignore rules
│   └── README.md                  # Project documentation
└── 💾 Cache and Storage
    ├── .chroma/                   # Vector database cache
    ├── temp_images/               # Temporary extracted images
    └── venv/                      # Python virtual environment
```

## AI Components

### Enhanced Agents
- **Market Sizing Agent**: TAM/SAM/SOM analysis with AI-powered data extraction
- **Competitive Intel Agent**: Competitor analysis and market positioning
- **Financial Analysis Agent**: Comprehensive financial metrics and AI-powered extraction
- **Founder Profiling Agent**: Executive background and track record
- **Risk Assessment Agent**: Risk identification and mitigation
- **Technical DD Agent**: Technical due diligence and assessment
- **VC Report Agent**: Report analysis

### Enhanced Chains
- **Business Model Chain**: Business model analysis and validation
- **Competitive Intel Chain**: Competitive landscape analysis
- **Financial Analysis Chain**: Comprehensive financial metrics extraction and analysis
- **Market Sizing Chain**: Market size calculation with AI-powered extraction
- **Memo Synthesis Chain**: Final memo compilation and formatting
- **Pitch Deck Chain**: Pitch deck analysis with enhanced data extraction
- **Risk Assessment Chain**: Risk assessment

### NEW: AI-Powered Data Extraction
- **Market Data Extraction**: `ai_extract_market_data()` - Comprehensive market data extraction
- **Financial Data Extraction**: `ai_extract_financial_data()` - Comprehensive financial data extraction
- **Dynamic Schema Handling**: `extra = "allow"` configuration for flexible field management
- **Enhanced Website Detection**: AI-powered website detection with CoreSignal fallback

## Development

### Code Quality
```bash
# Run linting
ruff check .

# Run formatting
black .

# Run tests
pytest

# Install pre-commit hooks
pre-commit install
```

### Adding New Agents
1. Create agent in `agents/` directory
2. Add chain in `chains/` directory
3. Update `main.py` orchestration
4. Add tests in `tests/` directory

### Adding New Scrapers
1. Create scraper in `web_scraping/scripts/`
2. Update `download_reports.py` integration
3. Add to tracking system

## Deployment

### Local Development
```bash
# Start all services
python main.py data/sample.pdf                    # Investment memo
cd web_scraping && python download_reports.py     # Web scraping
cd n8n && docker-compose up -d                    # n8n automation
cd email_assistant && python api_server.py        # Email API
```

### Production Considerations
- **Containerization**: Use Docker for consistent deployment
- **API Management**: Implement rate limiting and authentication
- **Monitoring**: Set up performance tracking and error handling
- **Backup**: Regular data backup and recovery procedures

## Performance Optimization

### Caching Strategy
- **Vector Cache**: ChromaDB for document embeddings
- **Extraction Cache**: Cached PDF processing results
- **Download Cache**: Tracked downloads to prevent duplicates

### Resource Management
- **Parallel Processing**: Multi-agent concurrent analysis
- **Incremental Updates**: Only process new/changed content
- **Smart Caching**: Intelligent cache invalidation
- **Dynamic Schema**: Flexible field management for AI-generated data

## Security

### API Key Management
- Store API keys in `.env` file (not in version control)
- Use environment variables for sensitive data
- Regularly rotate API keys
- Never commit API keys to version control

### Data Protection
- Secure access to n8n web interface
- Monitor workflow execution logs
- Backup important data regularly

## Troubleshooting

### Common Issues

#### Investment Memo Generation
```bash
# Check API keys
echo $OPENAI_API_KEY
echo $PERPLEXITY_API_KEY

# Verify Google Cloud credentials
ls cloud-credentials.json

# Test PDF processing
python -c "from core.download_utils import extract_text_from_pdf; print('PDF processing works')"
```

#### Web Scraping
```bash
# Check downloaded reports tracking
cat web_scraping/results/downloaded_reports.json

# Clear cache if needed
rm -rf web_scraping/data/*
```

#### Email Assistant
```bash
# Check n8n status
docker-compose ps

# Check API server
curl http://localhost:8000/health

# View n8n logs
docker-compose logs n8n
```

### Performance Issues
- **Memory**: Increase system memory for large PDFs
- **API Limits**: Check API rate limits and quotas
- **Cache**: Clear caches if experiencing issues

### API Key Issues
```bash
# Test all API keys
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('🔑 API Key Status:')
print('OpenAI:', '✅ SET' if os.getenv('OPENAI_API_KEY') else '❌ NOT SET')
print('Perplexity:', '✅ SET' if os.getenv('PERPLEXITY_API_KEY') else '❌ NOT SET')
print('Google Cloud:', '✅ SET' if os.path.exists('cloud-credentials.json') else '❌ NOT SET')
print('CoreSignal:', '✅ SET' if os.getenv('CORESIGNAL_API_KEY') else '❌ NOT SET (Optional)')
"
```

## Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Add** tests for new functionality
5. **Run** the test suite
6. **Submit** a pull request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add docstrings to new functions
- Include type hints where appropriate
- Write comprehensive tests

## Documentation

- **[Architecture.md](Architecture.md)**: Detailed technical architecture
- **[n8n/README.md](n8n/README.md)**: n8n automation setup
- **[evaluation_metrics/README.md](evaluation_metrics/README.md)**: Performance tracking

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **OpenAI** for GPT-4 API
- **Perplexity** for web search capabilities
- **Google Cloud** for Vision API
- **LangChain** for AI framework
- **n8n** for workflow automation
- **Playwright** for browser automation

## Support

For questions, issues, or contributions:
- **Issues**: Create a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Email**: Contact the maintainers

---

**Made with ❤️ for the VC community**
