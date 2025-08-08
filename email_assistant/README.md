## Email Assistant (Consolidated Server)

This assistant receives a question (from n8n or any client), classifies the task, and routes it to the right tools:
- Market/segment deep dive: uses cached local report data first, then web search if missing.
- Company: web search + CoreSignal (now seeded by LinkedIn/company website via Perplexity).
- Fund: web search + CoreSignal (also seeded by website/LinkedIn).
- Person: Perplexity with LinkedIn first, then general web; synthesizes a rich bio.

### Key Components
- **API Server**: `email_assistant/api/main_email.py` (runs on port 5002)
- **Primary Endpoint**: `/api/analyze-report`
- **Core Logic**: `agents/vc_report_agent.py`
- **Market Cache Builder**: `email_assistant/build_market_cache.py`

### Setup
1) Create virtual environment and install dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2) Environment variables (project root `.env`)
```
OPENAI_API_KEY=...
PERPLEXITY_API_KEY=...
CORESIGNAL_API_KEY=...   # optional but recommended for company/fund
```

3) (Optional) Build/refresh market cache
```bash
# Build cache from all vc_reports (or use --only-test-sample)
python email_assistant/build_market_cache.py --only-test-sample
```
Cache location: `web_scraping/data/vc_reports/cached_market_data`.

4) Run the API (local) or expose a stable public URL
```bash
python email_assistant/api/main_email.py
# Server: http://127.0.0.1:5002 (health: /health)
```

Stable public URL via ngrok reserved domain (paid):
```bash
brew install ngrok/ngrok/ngrok
ngrok config add-authtoken <YOUR_AUTHTOKEN>
# Reserve domain in dashboard → Domains → Reserve a domain (e.g., your-assistant.ngrok.app)
ngrok http --domain=your-assistant.ngrok.app 5002
```
Use: `https://your-assistant.ngrok.app/api/analyze-report`

### Endpoint
POST `/api/analyze-report`
Body:
```json
{ "question": "<your question>" }
```
Response:
```json
{
  "answer": "...",
  "sources": [{"source": "<url or file>", "page": 12, "temporal_valid": true}],
  "classification": "market_deep_dive|company|fund|person|generic",
  "enrichment": { ... }
}
```

### Task routing (current behavior)
- Market/segment deep dive: reads cached JSON, filters by keywords and sector, answers with local snippets; falls back to web if no cache match.
- Company: Perplexity to get LinkedIn + official website; pass website domain into CoreSignal to improve matching; synthesize web + CoreSignal.
- Fund: same as company flow.
- Person: Perplexity twice (LinkedIn-focused + bio/university), then specialized bio synthesis with inline citations.

### n8n usage
- In your HTTP node, call `http://<host>:5002/api/analyze-report` with body `{ "question": "{{$json.body.text}}" }` and send the returned `answer` back via email.

### Notes
- RAG/vector DB is disabled in production flow. Market answers rely on prebuilt cache; no live PDF indexing at query time.
- For best CoreSignal results, ensure Perplexity can resolve the official domain and LinkedIn URL.
