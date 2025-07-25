# generate_html.py
import json
import sys
from pathlib import Path


def main(json_path: str):
    # Load the JSON
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    memo_text = data.get("memorandum", "")

    # If your memo already contains Markdown or HTML tags, you can embed it directly.
    # If it’s plain-text, wrap lines in <p>…</p> or <pre>…</pre>.
    #
    # Here we assume `memo_text` is already markup-friendly (e.g. it contains Markdown-style headings).
    # We’ll convert newlines to <br> for simplicity. If you actually output Markdown, consider
    # pip-installing a Markdown-to-HTML converter (e.g. `markdown`).
    #
    # For now, we’ll do a very naive newline → <br> replacement inside a <div>.
    html_body = memo_text.replace("\n", "<br>\n")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Memo</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 40px; }}
    h1, h2, h3 {{ color: #333; }}
    pre {{ white-space: pre-wrap; word-wrap: break-word; }}
  </style>
</head>
<body>
  {html_body}
</body>
</html>
"""

    out_path = Path("memo.html")
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ HTML generated at {out_path.resolve()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_html.py memo_response.json")
        sys.exit(1)
    main(sys.argv[1])
