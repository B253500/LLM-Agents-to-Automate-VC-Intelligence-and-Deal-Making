import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from core.download_utils import DOWNLOAD_DIR, NAV_TIMEOUT

# --- Crunchbase-specific scraping logic ---
def scrape_and_download_crunchbase(page):
    print("\n=== Crunchbase Reports ===")
    try:
        page.goto("https://about.crunchbase.com/research-reports/", timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    except PlaywrightError as e:
        print(f"⚠️ Could not load Crunchbase listing: {e}")
        return

    anchors = page.query_selector_all("a:has-text('Learn More')")
    urls = []
    for a in anchors:
        href = a.get_attribute('href')
        if href:
            url = href if href.startswith('http') else f"https://about.crunchbase.com{href}"
            if url not in urls:
                urls.append(url)

    print(f"Found {len(urls)} Crunchbase reports")
    for url in urls:
        print(f"Would process: {url}")

if __name__ == "__main__":
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        scrape_and_download_crunchbase(page)
        browser.close() 