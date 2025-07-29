# html_to_pdf.py
import sys
from pathlib import Path
from weasyprint import HTML


def main(html_path: str):
    html_file = Path(html_path)
    if not html_file.exists():
        print(f"Error: {html_file} does not exist.")
        sys.exit(1)

    # Read the HTML and render it to PDF
    pdf_out = html_file.with_suffix(".pdf")  # e.g. memo.html → memo.pdf
    HTML(filename=str(html_file)).write_pdf(str(pdf_out))
    print(f"✅ PDF generated at {pdf_out.resolve()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python html_to_pdf.py memo.html")
        sys.exit(1)
    main(sys.argv[1])
