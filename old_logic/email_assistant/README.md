# Email Assistant Workflow

This directory contains the intelligent email assistant workflow using n8n automation.

## Components

### api/
API server and endpoints for email assistant functionality.

### n8n/
n8n workflow data and configurations for email automation.

### Scripts
- `api_server.py` - API server for email assistant
- `run_memo.py` - Memo generation script
- `automate_memo_pipeline.py` - Automation pipeline
- `analyze_vc_questions.py` - VC questions analysis
- `extract_text_and_figures.py` - Text and figure extraction
- `generate_pdf_memo.py` - PDF memo generation
- `generate_pdf.py` - PDF generation utility
- `generate_html.py` - HTML generation utility
- `html_to_pdf.py` - HTML to PDF conversion
- `html_to_pdf_chrome.py` - Chrome-based PDF conversion

## Usage

1. Start the API server: `python api_server.py`
2. Configure n8n workflows in `n8n/` directory
3. Use automation scripts for email processing
4. Generate memos and reports as needed

## Integration

This workflow integrates with:
- Email systems for automated processing
- n8n for workflow automation
- API endpoints for external access
