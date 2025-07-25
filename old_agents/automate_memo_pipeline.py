import json
from pathlib import Path
from weasyprint import HTML

# Paths
JSON_PATH = Path("memo_response.json")
HTML_PATH = Path("memo.html")
PDF_PATH = Path("out/memo.pdf")

# 1. Read memo JSON
with open(JSON_PATH, "r", encoding="utf-8") as f:
    memo_data = json.load(f)

# 2. Convert JSON to HTML content (very basic formatter)
html_content = f"""
<html>
<head>
    <meta charset="utf-8">
    <title>{memo_data['StartupProfile']['StartupName']}</title>
</head>
<body>
    <h1>{memo_data['StartupProfile']['StartupName']}</h1>
    <p><strong>Founder:</strong> {memo_data['StartupProfile']['FounderName']}</p>
    <p><strong>Requested:</strong> {memo_data['StartupProfile']['AmountRequested']}</p>
    <p><strong>Use of Funds:</strong> {memo_data['StartupProfile']['UseOfFunds']}</p>
    <p><strong>Date:</strong> {memo_data['StartupProfile']['PresentationDate']}</p>
    <p><strong>Contact:</strong> {memo_data['StartupProfile']['ContactEmail']}</p>
</body>
</html>
"""

# 3. Save to HTML
HTML_PATH.write_text(html_content, encoding="utf-8")

# 4. Convert HTML to PDF
HTML(filename=str(HTML_PATH)).write_pdf(str(PDF_PATH))

print(f"✅ Memo pipeline complete: {PDF_PATH}")
