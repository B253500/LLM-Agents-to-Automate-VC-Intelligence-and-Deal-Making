# VC Agents Project Architecture

## 🏗️ Project Overview

This project consists of **3 distinct workflows** for venture capital analysis and automation:

1. **📊 Investment Memo Generation** (main.py) - Core AI-powered memo creation
2. **🌐 Web Scraping** (web_scraping/) - Automated report discovery and download
3. **📧 Email Assistant** (email_assistant/ + n8n/) - Intelligent email automation

## 📁 Project Structure

```
new-vc-agents/
├── 📊 Investment Memo Generation (Core Workflow)
│   ├── main.py                    # Core memo generation orchestrator
│   ├── agents/                    # AI agents for analysis
│   │   ├── market_sizing_agent.py
│   │   ├── competitive_intel_agent.py
│   │   ├── financial_analysis_agent.py
│   │   ├── founder_profiling_agent.py
│   │   ├── risk_assessment_agent.py
│   │   ├── technical_dd_agent.py
│   │   └── vc_report_agent.py
│   ├── chains/                    # LangChain processing chains
│   │   ├── business_model_chain.py
│   │   ├── competitive_intel_chain.py
│   │   ├── financial_analysis_chain.py
│   │   ├── market_sizing_chain.py
│   │   ├── memo_synthesis_chain.py
│   │   ├── pitch_deck_chain.py
│   │   └── risk_assessment_chain.py
│   ├── core/                      # Core utilities and functions
│   │   ├── download_utils.py      # PDF processing and OCR
│   │   ├── external_enrichment.py # Web search and data enrichment
│   │   ├── hybrid_context.py      # Context management
│   │   ├── llm_utils.py          # LLM integration
│   │   ├── orchestration.py       # Workflow orchestration
│   │   ├── perplexity_utils.py    # Perplexity API integration
│   │   ├── report_loader.py       # Report loading utilities
│   │   ├── schemas.py             # Data schemas
│   │   ├── utils.py               # General utilities
│   │   ├── vector_store.py        # Vector database operations
│   │   └── visual_utils.py        # Image processing
│   ├── data/                      # Data storage
│   │   ├── vc_reports/            # Downloaded VC reports (284+ PDFs)
│   │   └── *.pdf                  # Sample pitch decks
│   ├── extraction_cache/           # Cached extracted data
│   ├── out/                       # Generated memo outputs
│   ├── template.docx              # Memo template
│   ├── DejaVuSans.ttf            # Font for PDF generation
│   └── cloud-credentials.json     # Google Cloud Vision API
│
├── 🌐 Web Scraping Workflow
│   ├── download_reports.py        # Main scraping orchestrator
│   ├── scripts/                   # Individual scraping scripts
│   │   ├── download_beauhurst.py  # Beauhurst report scraping
│   │   ├── download_crunchbase.py # Crunchbase report scraping
│   │   ├── download_pitchbook.py  # PitchBook report scraping
│   │   └── download_techcrunch.py # TechCrunch article scraping
│   ├── data/                      # Downloaded reports
│   └── results/                   # Scraping results and analysis
│
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
│
├── 🤖 n8n Automation Hub
│   ├── docker-compose.yml         # Docker configuration
│   ├── Dockerfile                 # Custom n8n image with Python/Playwright
│   ├── data/                      # n8n data persistence
│   ├── workflows/                 # Organized workflow directories
│   │   ├── email_assistant/       # Email automation workflows
│   │   └── web_scraping/          # Web scraping automation workflows
│   └── README.md                  # n8n setup and documentation
│
├── 📊 Evaluation Metrics
│   ├── core/                      # Evaluation core components
│   │   ├── evaluation_metrics.py  # Memo evaluation logic
│   │   └── integrate_evaluation.py # Evaluation integration
│   ├── results/                   # Evaluation results
│   ├── config/                    # Evaluation configuration
│   ├── utils/                     # Evaluation utilities
│   └── templates/                 # Evaluation templates
│
├── 🧪 Tests
│   ├── test_competitive_intel.py
│   ├── test_deck_agent.py
│   ├── test_financial_agent.py
│   ├── test_market_agent.py
│   └── test_technical_agent.py
│
├── 🔧 Configuration Files
│   ├── .env                       # Environment variables
│   ├── requirements.txt           # Python dependencies
│   ├── .python-version            # Python version specification
│   ├── .pre-commit-config.yaml   # Code quality hooks
│   ├── .gitignore                 # Git ignore rules
│   └── README.md                  # Project documentation
│
└── 💾 Cache and Storage
    ├── .chroma/                   # Vector database cache
    └── venv/                      # Python virtual environment
```

## 🔄 Workflow Interactions

### 1. Investment Memo Generation (main.py)
**Input**: Pitch deck PDF → **Output**: Investment memo (PDF/DOCX)

**Process Flow**:
```
PDF Upload → Text Extraction → AI Analysis → Memo Generation → Output
     ↓              ↓              ↓              ↓              ↓
  OCR/PDF    →   Context    →   Agents    →   Synthesis   →   PDF/DOCX
  Processing     Building      Analysis       Chain
```

**Key Components**:
- **Agents**: Market sizing, competitive intelligence, financial analysis, founder profiling, risk assessment, technical due diligence
- **Chains**: Business model, competitive intel, financial analysis, market sizing, memo synthesis, pitch deck, risk assessment
- **Core**: PDF processing, web search, context management, LLM integration, vector storage

### 2. Web Scraping Workflow
**Input**: Website URLs → **Output**: Downloaded reports and analysis

**Process Flow**:
```
URL Discovery → Form Filling → PDF Download → Data Extraction → Storage
      ↓              ↓              ↓              ↓              ↓
   Web Search   →   Automation   →   Download   →   OCR/Text   →   JSON/PDF
```

**Key Components**:
- **Sources**: Beauhurst, Crunchbase, PitchBook, TechCrunch
- **Automation**: Playwright browser automation, form filling, email integration
- **Tracking**: `downloaded_reports.json` for duplicate prevention

### 3. Email Assistant Workflow
**Input**: Email content → **Output**: Automated responses and memo generation

**Process Flow**:
```
Email → Analysis → API Call → Memo Generation → Response
  ↓         ↓         ↓            ↓              ↓
Receive  →  Parse   →  Process  →  Generate   →  Send
```

**Key Components**:
- **API Server**: FastAPI for email processing
- **Services**: LinkedIn extraction, market analysis, OCR processing
- **n8n Integration**: Workflow automation and orchestration

## 🤖 AI Components

### Agents (LangChain-based)
- **Market Sizing Agent**: TAM/SAM/SOM analysis with web search
- **Competitive Intel Agent**: Competitor analysis and market positioning
- **Financial Analysis Agent**: Financial metrics and projections
- **Founder Profiling Agent**: Executive background and track record
- **Risk Assessment Agent**: Risk identification and mitigation
- **Technical DD Agent**: Technical due diligence and assessment
- **VC Report Agent**: VC report analysis and insights

### Chains (Processing Pipelines)
- **Business Model Chain**: Business model analysis and validation
- **Competitive Intel Chain**: Competitive landscape analysis
- **Financial Analysis Chain**: Financial metrics extraction and analysis
- **Market Sizing Chain**: Market size calculation and validation
- **Memo Synthesis Chain**: Final memo compilation and formatting
- **Pitch Deck Chain**: Pitch deck analysis and insights
- **Risk Assessment Chain**: Risk identification and assessment

## 🔧 Technical Stack

### Core Technologies
- **Python 3.11**: Main programming language
- **LangChain**: AI agent and chain framework
- **OpenAI GPT-4**: Primary LLM for analysis
- **Perplexity API**: Web search and data retrieval
- **Google Cloud Vision**: OCR and image processing
- **ChromaDB**: Vector database for document similarity

### Web Scraping
- **Playwright**: Browser automation
- **BeautifulSoup**: HTML parsing
- **Requests**: HTTP client
- **PDF Processing**: pdfplumber, PyPDF2

### Email Automation
- **FastAPI**: API server
- **n8n**: Workflow automation
- **Docker**: Containerization
- **Playwright**: Browser automation for email processing

### Data Processing
- **Pandas**: Data manipulation
- **NumPy**: Numerical computing
- **Matplotlib**: Chart generation
- **Pillow**: Image processing

### Development Tools
- **pytest**: Testing framework
- **ruff**: Code linting
- **black**: Code formatting
- **pre-commit**: Git hooks
- **GitHub Actions**: CI/CD

## 📊 Data Flow

### Input Sources
1. **Pitch Decks**: PDF uploads for memo generation
2. **VC Reports**: Automated downloads from web scraping
3. **Emails**: Incoming emails for processing
4. **Web Search**: Real-time data from Perplexity API

### Processing Pipeline
1. **Text Extraction**: OCR and PDF processing
2. **Context Building**: Vector embeddings and similarity search
3. **AI Analysis**: Multi-agent analysis with specialized agents
4. **Synthesis**: Chain-based memo compilation
5. **Output Generation**: PDF/DOCX memo creation

### Output Formats
1. **Investment Memos**: PDF and DOCX formats
2. **Analysis Reports**: JSON and PDF formats
3. **Email Responses**: Automated email responses
4. **Evaluation Metrics**: Performance tracking and analysis

## 🔐 Security & Configuration

### Environment Variables
- `OPENAI_API_KEY`: OpenAI API access
- `PERPLEXITY_API_KEY`: Perplexity API access
- `CORESIGNAL_API_KEY`: CoreSignal API access
- `GOOGLE_APPLICATION_CREDENTIALS`: Google Cloud Vision API

### API Integrations
- **OpenAI**: GPT-4 for analysis and generation
- **Perplexity**: Web search and data retrieval
- **Google Cloud Vision**: OCR and image processing
- **CoreSignal**: Company data enrichment

## 📈 Performance & Scalability

### Caching Strategy
- **Vector Cache**: ChromaDB for document embeddings
- **Extraction Cache**: Cached PDF processing results
- **Download Cache**: Tracked downloads to prevent duplicates

### Optimization Features
- **Parallel Processing**: Multi-agent concurrent analysis
- **Incremental Updates**: Only process new/changed content
- **Smart Caching**: Intelligent cache invalidation
- **Resource Management**: Efficient memory and CPU usage

## 🚀 Deployment

### Local Development
```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run investment memo generation
python main.py data/sample.pdf

# Start n8n automation
cd n8n && docker-compose up -d
```

### Production Considerations
- **Containerization**: Docker for consistent deployment
- **API Management**: Rate limiting and authentication
- **Monitoring**: Performance tracking and error handling
- **Backup**: Regular data backup and recovery procedures

## 🔄 Continuous Improvement

### Evaluation Metrics
- **Section Completeness**: Track memo section coverage
- **Readability Scores**: Flesch-Kincaid readability analysis
- **Cost Tracking**: API usage and cost monitoring
- **Quality Scoring**: Automated quality assessment

### Future Enhancements
- **Multi-language Support**: International market analysis
- **Advanced Analytics**: Machine learning insights
- **Real-time Updates**: Live market data integration
- **Collaborative Features**: Team-based memo editing

