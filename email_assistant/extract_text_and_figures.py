# download_reports.py - Playwright script for Crunchbase & Beauhurst with detail-page crawling
# Requirements:
#   python >=3.7
#   pip install playwright
#   playwright install

import os
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError, Download

# Download directory
DOWNLOAD_DIR = Path(__file__).parent / "data" / "vc_reports"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Timeouts
NAV_TIMEOUT = 60000
DOWNLOAD_TIMEOUT = 120000


def download_pdf_from_detail(page, detail_url):
    """Visit detail_url, find the PDF link or download button, and fetch or intercept it."""
    try:
        page.goto(detail_url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    except PlaywrightError as e:
        print(f"⚠️ Failed to load {detail_url}: {e}")
        return
    # Try to find a direct PDF link
    link = page.query_selector('a[href$=".pdf"]')
    if link:
        href = link.get_attribute('href')
        href = href if href.startswith('http') else page.url.rstrip('/') + href
        fname = href.split('/')[-1].split('?')[0]
        target = DOWNLOAD_DIR / fname
        if not target.exists():
            print(f"↓ fetching {fname}")
            try:
                page.context.request.get(href, timeout=DOWNLOAD_TIMEOUT).save_as(str(target))
            except PlaywrightError as ex:
                print(f"⚠️ Error fetching {href}: {ex}")
        else:
            print(f"✓ already have {fname}")
        return
    # Otherwise, click a download button if present
    button = page.query_selector("a:has-text('Download')") or page.query_selector("button:has-text('Download')")
    if button:
        fname = detail_url.rstrip('/').split('/')[-1] + '.pdf'
        target = DOWNLOAD_DIR / fname
        if not target.exists():
            print(f"↓ clicking to download {fname}")
            try:
                with page.expect_download(timeout=DOWNLOAD_TIMEOUT) as dl:
                    button.click()
                dl.value.save_as(str(target))
            except PlaywrightError as ex:
                print(f"⚠️ Download failed for {detail_url}: {ex}")
        else:
            print(f"✓ already have {fname}")
    else:
        print(f"⚠️ No PDF link/button found on {detail_url}")


def scrape_and_download_crunchbase(page):
    listing = "https://about.crunchbase.com/research-reports/"
    try:
        page.goto(listing, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    except PlaywrightError as e:
        print(f"⚠️ Could not load Crunchbase listing: {e}")
        return
    # Reports links typically in anchor with href '/research-reports/...'
    items = page.query_selector_all("a[href*='/research-report/']")
    seen = set()
    for a in items:
        href = a.get_attribute('href')
        if not href: continue
        url = href if href.startswith('http') else 'https://about.crunchbase.com' + href
        if url in seen: continue
        seen.add(url)
        download_pdf_from_detail(page, url)


def scrape_and_download_beauhurst(page):
    listing = "https://www.beauhurst.com/reports/"
    try:
        page.goto(listing, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    except PlaywrightError as e:
        print(f"⚠️ Could not load Beauhurst listing: {e}")
        return
    # Beauhurst detail pages anchor:
    items = page.query_selector_all("a.card--report[href]")
    seen = set()
    for a in items:
        href = a.get_attribute('href')
        if not href: continue
        url = href if href.startswith('http') else 'https://www.beauhurst.com' + href
        if url in seen: continue
        seen.add(url)
        download_pdf_from_detail(page, url)


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)

        print("=== Crunchbase Reports ===")
        scrape_and_download_crunchbase(page)

        print("=== Beauhurst Reports ===")
        scrape_and_download_beauhurst(page)

        browser.close()

if __name__ == '__main__':
    main()
