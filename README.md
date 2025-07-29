# VC Agents - AI-Powered Investment Memo Generation

> **Intelligent venture capital analysis and automation platform with 3 distinct workflows**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-✓-green.svg)](https://langchain.com/)
[![OpenAI GPT-4](https://img.shields.io/badge/OpenAI-GPT--4-orange.svg)](https://openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Project Overview

VC Agents is a comprehensive AI-powered platform for venture capital analysis and automation. The project consists of **3 distinct workflows**:

1. **📊 Investment Memo Generation** - Core AI-powered memo creation from pitch decks
2. **🌐 Web Scraping** - Automated discovery and download of VC reports
3. **📧 Email Assistant** - Intelligent email automation with n8n integration

## 🏗️ Architecture

```
new-vc-agents/
├── 📊 Investment Memo Generation (Core)
│   ├── main.py                    # Core memo generation
│   ├── agents/                    # AI agents for analysis
│   ├── chains/                    # LangChain processing
│   └── core/                      # Core utilities
├── 🌐 Web Scraping
│   ├── download_reports.py        # Main scraper
│   └── scripts/                   # Individual scrapers
├── 📧 Email Assistant
│   ├── api_server.py              # FastAPI server
│   └── api/                       # API services
├── 🤖 n8n Automation Hub
│   ├── docker-compose.yml         # Docker setup
│   └── workflows/                 # Automation workflows
└── 📊 Evaluation Metrics
    └── core/                      # Performance tracking
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker** (for n8n automation)
- **API Keys**: OpenAI, Perplexity, Google Cloud Vision

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd new-vc-agents

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### 2. Environment Configuration

Create a `.env` file with your API keys:

```bash
# Required API Keys
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
GOOGLE_APPLICATION_CREDENTIALS=cloud-credentials.json

# Optional APIs
CORESIGNAL_API_KEY=your_coresignal_api_key
```

### 3. Google Cloud Vision Setup

1. **Download credentials**: Get `cloud-credentials.json` from Google Cloud Console
2. **Place in root**: Ensure the file is in the project root directory
3. **Enable APIs**: Enable Cloud Vision API in your Google Cloud project

## 📊 Workflow 1: Investment Memo Generation

### Overview
Generate comprehensive investment memos from pitch deck PDFs using AI agents.

### Usage

```bash
# Generate memo from pitch deck
python main.py data/sample_pitch_deck.pdf

# Output will be saved to out/ directory
```

### Features
- **Multi-agent Analysis**: Market sizing, competitive intelligence, financial analysis
- **Web Search Integration**: Real-time data from Perplexity API
- **PDF Processing**: OCR and text extraction with Google Cloud Vision
- **Template-based Output**: Professional memo formatting
- **Evaluation Metrics**: Performance tracking and quality assessment

### Example Output
```
out/
├── memo_CompanyName_20250728_143022.docx
├── memo_CompanyName_20250728_143022.pdf
└── memo_CompanyName_20250728_143022.html
```

## 🌐 Workflow 2: Web Scraping

### Overview
Automated discovery and download of VC reports from multiple sources.

### Usage

```bash
# Run comprehensive web scraping
cd web_scraping
python download_reports.py

# Or run individual scrapers
python scripts/download_beauhurst.py
python scripts/download_pitchbook.py
python scripts/download_crunchbase.py
```

### Sources
- **Beauhurst**: UK startup and investment reports
- **PitchBook**: Global private market data
- **Crunchbase**: Company and funding data
- **TechCrunch**: Tech industry news and analysis

### Features
- **Automated Form Filling**: Intelligent form completion
- **Email Integration**: Gmail PDF download automation
- **Duplicate Prevention**: JSON tracking to avoid re-downloads
- **Multi-format Support**: PDF, DOCX, and webpage capture

### Tracking
The system maintains `web_scraping/results/downloaded_reports.json` to track:
- Downloaded files
- Email-requested reports
- Source URLs and filenames

## 📧 Workflow 3: Email Assistant

### Overview
Intelligent email automation with n8n integration for VC analysis requests.

### Setup

#### 1. Start n8n Automation Hub
```bash
cd n8n
docker-compose up -d

# Access n8n web interface
# URL: http://localhost:5678
# Username: your-username (configured in docker-compose.yml)
# Password: your-password (configured in docker-compose.yml)
```

#### 2. Start Email API Server
```bash
cd email_assistant
python api_server.py

# API will be available at http://localhost:8000
```

#### 3. Configure n8n Workflows
1. **Import workflows** from `n8n/workflows/email_assistant/`
2. **Configure triggers** for email processing
3. **Set up API connections** to the email server

### Features
- **Email Processing**: Automatic email content analysis
- **VC Question Analysis**: Intelligent response generation
- **PDF Generation**: Automated memo creation
- **LinkedIn Integration**: Executive profile extraction
- **Market Analysis**: Real-time market data integration

### API Endpoints
```
POST /process_email          # Process incoming emails
POST /generate_memo          # Generate investment memo
GET  /health                 # Health check
POST /analyze_question       # Analyze VC questions
```

## 🤖 AI Components

### Agents
- **Market Sizing Agent**: TAM/SAM/SOM analysis
- **Competitive Intel Agent**: Competitor analysis
- **Financial Analysis Agent**: Financial metrics
- **Founder Profiling Agent**: Executive backgrounds
- **Risk Assessment Agent**: Risk identification
- **Technical DD Agent**: Technical due diligence
- **VC Report Agent**: Report analysis

### Chains
- **Business Model Chain**: Business model analysis
- **Competitive Intel Chain**: Competitive landscape
- **Financial Analysis Chain**: Financial metrics
- **Market Sizing Chain**: Market size calculation
- **Memo Synthesis Chain**: Final memo compilation
- **Pitch Deck Chain**: Pitch deck analysis
- **Risk Assessment Chain**: Risk assessment

## 📊 Evaluation & Performance

### Metrics Tracked
- **Section Completeness**: Memo section coverage
- **Readability Scores**: Flesch-Kincaid analysis
- **Cost Tracking**: API usage monitoring
- **Quality Scoring**: Automated assessment

### View Results
```bash
cd evaluation_metrics
# View evaluation results in results/ directory
```

## 🔧 Development

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

## 🚀 Deployment

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

## 📈 Performance Optimization

### Caching Strategy
- **Vector Cache**: ChromaDB for document embeddings
- **Extraction Cache**: Cached PDF processing results
- **Download Cache**: Tracked downloads to prevent duplicates

### Resource Management
- **Parallel Processing**: Multi-agent concurrent analysis
- **Incremental Updates**: Only process new/changed content
- **Smart Caching**: Intelligent cache invalidation

## 🔐 Security

### API Key Management
- Store API keys in `.env` file (not in version control)
- Use environment variables for sensitive data
- Regularly rotate API keys

### Data Protection
- Secure access to n8n web interface
- Monitor workflow execution logs
- Backup important data regularly

## 🤝 Contributing

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

## 📚 Documentation

- **[Architecture.md](Architecture.md)**: Detailed technical architecture
- **[n8n/README.md](n8n/README.md)**: n8n automation setup
- **[evaluation_metrics/README.md](evaluation_metrics/README.md)**: Performance tracking

## 🐛 Troubleshooting

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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT-4 API
- **Perplexity** for web search capabilities
- **Google Cloud** for Vision API
- **LangChain** for AI framework
- **n8n** for workflow automation
- **Playwright** for browser automation

## 📞 Support

For questions, issues, or contributions:
- **Issues**: Create a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Email**: Contact the maintainers

---

**Made with ❤️ for the VC community**
