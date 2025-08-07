# Investment Memo Generator - Complete Setup Guide

This guide provides the exact configuration needed to replicate the investment memo generator environment.

## 🐍 Python Environment

### Required Python Version
- **Python 3.11.4** (exact version used in development)
- **Virtual Environment**: Highly recommended to avoid conflicts

### System Requirements
- macOS (tested on macOS 24.5.0)
- At least 8GB RAM (for LLM operations)
- Stable internet connection (for API calls)

## 📦 Installation Steps

This project has two main components with different setup requirements:
1.  **Investment Memo Generator**: A Python application that analyzes pitch decks and generates investment memos.
2.  **Web Scraping & n8n**: A Dockerized n8n workflow for automated web scraping tasks.

---

### Part 1: Investment Memo Generator Setup

These steps are for running the core memo generator on your local machine.

#### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd new-vc-agents
```

#### 2. Create Virtual Environment
A virtual environment is crucial to manage dependencies and avoid conflicts.

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

#### 3. Install Full Requirements
This will install all necessary packages for the memo generator, including PDF processing, AI/ML libraries, and document creation tools.

```bash
# Upgrade pip first
pip install --upgrade pip

# Install the full set of requirements
pip install -r requirements.txt
```
**Note**: The `requirements.txt` file contains all packages needed for the memo generator to function fully. For a detailed list of the exact 586 packages used in the original development environment, you can refer to `exact_requirements.txt`, but this is not recommended for a typical setup.

---

### Part 2: Web Scraping & n8n Docker Setup

This setup is for running the automated web scraping workflows using Docker and n8n. It is isolated from your local Python environment.

#### 1. Docker and Docker Compose
Ensure you have Docker and Docker Compose installed on your system.
- [Install Docker](https://docs.docker.com/get-docker/)
- [Install Docker Compose](https://docs.docker.com/compose/install/)

#### 2. Build and Run the Docker Container
The n8n services are defined in the `docker-compose.n8n.yml` file. The Dockerfile for n8n (`n8n/Dockerfile`) is configured to use a minimal set of dependencies.

```bash
# Build and run the n8n container in detached mode
docker-compose -f docker-compose.n8n.yml up --build -d
```

#### 3. Understanding the Minimal Requirements
The Docker container for n8n uses the `web_scraping/minimal_requirements.txt` file. This file includes only the essential packages for the web scraping and automation tasks, making the Docker image lightweight. **You do not need to install these locally** if you are only using the Dockerized n8n setup.

---


## 🔑 API Keys Configuration

### Required API Keys

Create a `.env` file in the project root with the following keys:

```bash
#  OpenAI API Key (Required for all LLM operations)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Perplexity API Key (For web search and market research)
PERPLEXITY_API_KEY=your-perplexity-api-key-here

#  CoreSignal API Key (For company data enrichment)
CORESIGNAL_API_KEY=your-coresignal-api-key-here

#  Exa API Key (For semantic search)
EXA_API_KEY=your-exa-api-key-here

#  ProxyCurl API Key (For LinkedIn data enrichment)
PROXYCURL_API_KEY=your-proxcurl-api-key-here

#  Email Configuration (For n8n integration)
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-gmail-app-password
```

### How to Get API Keys

1. **OpenAI API Key** (Required)
   - Go to: https://platform.openai.com/api-keys
   - Create a new API key
   - Add billing information (required for GPT-4o)

2. **Perplexity API Key** (Recommended)
   - Go to: https://www.perplexity.ai/settings/api
   - Create a new API key

3. **CoreSignal API Key** (Optional)
   - Go to: https://coresignal.com/
   - Sign up for API access

4. **Exa API Key** (Optional)
   - Go to: https://exa.ai/
   - Sign up for API access

5. **ProxyCurl API Key** (Optional)
   - Go to: https://proxcurl.com/
   - Sign up for API access

## 🚀 Usage Instructions

### Command Line Usage
```bash
# Basic usage
python main.py data/your-pitch-deck.pdf

```

### API Server Usage
```bash
# Start the API server
python -m email_assistant.api.main_email

# Server will run on http://127.0.0.1:5002
```

### Email Assistant Usage
```bash
# Generate PDF memo
python email_assistant/generate_pdf_memo.py data/your-pitch-deck.pdf

# With LLM enhancement
python email_assistant/generate_pdf_memo.py data/your-pitch-deck.pdf --llm
```

## 📁 Project Structure

```
new-vc-agents/
├── main.py                          # Main entry point
├── core/                            # Core utilities (22 files)
│   ├── pipeline.py                  # Refactored pipeline
│   ├── llm_utils.py                 # LLM utilities
│   ├── download_utils.py            # PDF extraction
│   └── ...
├── chains/                          # LangChain chains (14 files)
│   ├── pitch_deck_chain.py         # Pitch deck analysis
│   ├── market_sizing_chain.py       # Market sizing
│   └── ...
├── agents/                          # AI agents (15 files)
│   ├── technical_dd_agent.py        # Technical due diligence
│   ├── competitive_intel_agent.py   # Competitive intelligence
│   └── ...
├── email_assistant/                 # Email integration
│   ├── api/                         # API server
│   └── generate_pdf_memo.py         # PDF generator
├── requirements.txt                  # Development requirements
├── minimal_requirements.txt         # Minimal requirements (~50 packages)
├── exact_requirements.txt           # Exact environment (586 packages)
└── .env                             # API keys (create this)
```

## 🔧 Configuration Files

### config.py
The system uses a centralized configuration file that supports:
- LLM model selection (default: GPT-4o)
- Temperature settings (default: 0.2)
- Output directories
- API service configurations

### Environment Variables
All API keys and configuration can be set via environment variables or the `.env` file.

## 🧪 Testing the Setup

### 1. Test Basic Installation
```bash
# Activate virtual environment
source venv/bin/activate

# Test Python version
python --version  # Should show Python 3.11.4

# Test imports
python -c "import openai; import langchain; print('✅ Dependencies installed successfully')"
```

### 2. Test API Keys
```bash
# Test OpenAI connection
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
import openai
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
print('✅ OpenAI API key working')
"
```

### 3. Test with Sample Data
```bash
# Run with a sample PDF
python main.py data/sample.pdf
```

## 📊 Output Files

The system generates several output files:
- `out/memo_[company_name]_[timestamp].docx` - Word document memo
- `out/memo_[company_name]_[timestamp].pdf` - PDF memo
- `evaluation_results/` - Evaluation metrics and reports
- `extraction_cache/` - Cached PDF extractions

## 🐛 Troubleshooting

### Common Issues

1. **ModuleNotFoundError**
   ```bash
   # Solution: Ensure virtual environment is activated
   source venv/bin/activate
   pip install -r minimal_requirements.txt
   ```

2. **OpenAI API Key Error**
   ```bash
   # Solution: Check .env file exists and has correct key
   cat .env | grep OPENAI_API_KEY
   ```

3. **PDF Extraction Issues**
   ```bash
   # Solution: Install system dependencies
   brew install tesseract  # macOS
   # or
   sudo apt-get install tesseract-ocr  # Ubuntu
   ```

4. **Memory Issues**
   ```bash
   # Solution: Reduce batch size or use smaller models
   export DEFAULT_MODEL="gpt-4o-mini"
   ```

### Performance Optimization

1. **Enable Caching**: The system automatically caches PDF extractions
2. **Batch Processing**: Process multiple files in sequence

## 🔒 Security Notes

1. **Never commit API keys** to version control
2. **Use app passwords** for Gmail integration
3. **Rotate API keys** regularly
4. **Monitor usage** to avoid unexpected charges

## 📈 Monitoring and Logs

The system provides detailed logging:
- Token usage tracking
- Performance metrics
- Error reporting
- Evaluation results

Logs are saved in:
- `evaluation_results/` - Detailed metrics
- Console output - Real-time progress

## 🆘 Support

For issues:
1. Check the troubleshooting section above
2. Verify all API keys are correctly set
3. Ensure virtual environment is activated
4. Check Python version matches (3.11.4)

---

**Last Updated**: August 4, 2025  
**Version**: 1.0.0  
**Python**: 3.11.4  
**Minimal Dependencies**: ~50 packages (see minimal_requirements.txt)  
**Full Environment**: 586 packages (see exact_requirements.txt) 