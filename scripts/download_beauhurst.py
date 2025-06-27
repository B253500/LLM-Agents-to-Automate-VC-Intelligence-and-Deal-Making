import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from core.download_utils import DOWNLOAD_DIR, NAV_TIMEOUT, download_utils, load_downloaded_mapping, save_downloaded_mapping, _fetch_and_save, save_webpage_as_pdf
import re

# --- Beauhurst-specific scraping logic ---
def scrape_and_download_beauhurst(page, max_pages=10):
    print("=== Beauhurst Reports ===")
    base = "https://www.beauhurst.com"
    for i in range(1, max_pages + 1):
        url = f"{base}/reports/" if i == 1 else f"{base}/reports/page/{i}/"
        print(f"Fetching report list page: {url}")
        try:
            page.goto(url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
        except PlaywrightError as e:
            print(f"⚠️ Could not load {url}: {e}")
            break
        cards = page.query_selector_all("a[href*='/research/']")
        report_links = []
        for a in cards:
            href = a.get_attribute('href')
            if not href or '/author/' in href or '/tag/' in href:
                continue
            if not href.startswith('http'):
                href = base + href
            if href not in report_links:
                report_links.append(href)
        print(f"Found {len(report_links)} report links on page {i}")
        for detail_url in report_links:
            print(f"Visiting detail page: {detail_url}")
            # You would call your download_pdf_from_detail here, or inline the logic
            # For now, just print the URL
            # download_pdf_from_detail(page, detail_url)
            print(f"Would process: {detail_url}")

if __name__ == "__main__":
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        scrape_and_download_beauhurst(page)
        browser.close() 