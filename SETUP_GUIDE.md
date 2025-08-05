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

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd new-vc-agents
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

**Option A: Minimal Installation (Recommended)**
```bash
# Upgrade pip first
pip install --upgrade pip

# Install minimal requirements (only what's actually used)
pip install -r minimal_requirements.txt
```

**Option B: Exact Environment (If you need the full conda environment)**
```bash
# Install exact requirements (586 packages from your environment)
pip install -r exact_requirements.txt
```

**Note**: The `minimal_requirements.txt` contains only the packages actually used by the memo generator (~50 packages). The `exact_requirements.txt` contains your entire conda environment (586 packages) and includes many unnecessary dependencies.

## 🔑 API Keys Configuration

### Required API Keys

Create a `.env` file in the project root with the following keys:

```bash
# MANDATORY - OpenAI API Key (Required for all LLM operations)
OPENAI_API_KEY=sk-your-openai-api-key-here

# RECOMMENDED - Perplexity API Key (For web search and market research)
PERPLEXITY_API_KEY=your-perplexity-api-key-here

# OPTIONAL - CoreSignal API Key (For company data enrichment)
CORESIGNAL_API_KEY=your-coresignal-api-key-here

# OPTIONAL - Exa API Key (For semantic search)
EXA_API_KEY=your-exa-api-key-here

# OPTIONAL - ProxyCurl API Key (For LinkedIn data enrichment)
PROXYCURL_API_KEY=your-proxcurl-api-key-here

# OPTIONAL - Email Configuration (For n8n integration)
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

# Multiple files
python main.py data/deck1.pdf data/deck2.pdf
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
2. **Use GPU**: If available, install CUDA for faster processing
3. **Batch Processing**: Process multiple files in sequence

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