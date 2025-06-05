# html_to_pdf_chrome.py
import asyncio
import os
import sys
from pyppeteer import launch


async def html_to_pdf(input_html: str, output_pdf: str) -> None:
    # Launch a headless Chromium (Pyppeteer downloads a bundled Chromium).
    browser = await launch(args=["--no-sandbox"])
    page = await browser.newPage()

    # Construct file:// URL for local HTML
    html_path = os.path.abspath(input_html)
    url = f"file://{html_path}"
    await page.goto(url, {"waitUntil": "networkidle2"})

    # Give it a moment to render CSS/fonts, etc.
    await asyncio.sleep(0.5)

    # Save as PDF (you can adjust margin/pageSize here if needed)
    await page.pdf(
        {
            "path": output_pdf,
            "format": "Letter",
            "printBackground": True,
            "margin": {
                "top": "0.5in",
                "right": "0.5in",
                "bottom": "0.5in",
                "left": "0.5in",
            },
        }
    )

    await browser.close()
    print(f"✅ PDF written to: {output_pdf}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python html_to_pdf_chrome.py <input.html> <output.pdf>")
        sys.exit(1)

    input_html = sys.argv[1]
    output_pdf = sys.argv[2]
    asyncio.get_event_loop().run_until_complete(html_to_pdf(input_html, output_pdf))


if __name__ == "__main__":
    main()
