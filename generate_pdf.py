import json
import textwrap
from fpdf import FPDF, errors


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_page()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_font("Helvetica", size=11)


def main(json_path: str, output_path: str = "out/memo_final.pdf"):
    # 1. Load JSON
    with open(json_path, "r") as f:
        data = json.load(f)
    text = data.get("memorandum", "")

    # 2. Set up PDF
    pdf = PDF()

    # 3. Wrap lines at ~90 chars, forcing breaks on long “words”
    wrapper = textwrap.TextWrapper(
        width=90,
        break_long_words=True,
        break_on_hyphens=True,
    )

    wrapped_lines = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            wrapped_lines.append("")  # preserve blank line
        else:
            wrapped_lines.extend(wrapper.wrap(raw_line))

    # 4. Write wrapped lines, skipping any truly unfit characters
    for line in wrapped_lines:
        try:
            pdf.multi_cell(0, 8, line)
        except errors.FPDFException:
            # If an entire “line” fails, try each character; skip on failure
            for ch in line:
                try:
                    pdf.multi_cell(0, 8, ch)
                except errors.FPDFException:
                    # skip this character entirely
                    continue

    # 5. Save PDF
    pdf.output(output_path)
    print(f"✅ PDF written: {output_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python generate_pdf.py memo_response.json")
        sys.exit(1)
    main(sys.argv[1])
