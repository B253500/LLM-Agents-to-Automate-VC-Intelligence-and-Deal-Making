import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from core.download_utils import DOWNLOAD_DIR, NAV_TIMEOUT, load_downloaded_mapping, save_downloaded_mapping, _fetch_and_save, save_webpage_as_pdf
import re

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
        download_pdf_from_detail(page, url)

def download_pdf_from_detail(page, detail_url):
    mapping = load_downloaded_mapping()
    if detail_url in mapping:
        mapped_val = mapping[detail_url]
        if mapped_val == 'email_sent':
            print(f"✓ Report already requested by email for {detail_url}, skipping form.")
            return
        pdf_path = DOWNLOAD_DIR / mapped_val
        if pdf_path.exists():
            print(f"✓ Report already exists (mapping): {pdf_path.name}, skipping.")
            return
        else:
            del mapping[detail_url]
            save_downloaded_mapping(mapping)
    safe_title = re.sub(r'[^0-9\w\s-]', '', detail_url.rstrip('/').split('/')[-1])
    safe_title = re.sub(r'[-\s]+', '_', safe_title).strip('_').lower()
    pdf_path = DOWNLOAD_DIR / f"{safe_title}.pdf"
    if pdf_path.exists():
        print(f"✓ Report already exists: {pdf_path.name}, skipping.")
        return
    try:
        page.goto(detail_url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    except PlaywrightError as e:
        print(f"⚠️ Failed to load {detail_url}: {e}")
        return
    if 'book-demo' in detail_url.lower() or 'book-a-demo' in detail_url.lower():
        print(f"Skipping non-report page (book demo): {detail_url}")
        return
    def try_download():
        try:
            page.wait_for_selector('a[href$=".pdf"], a:has-text("Download"), button:has-text("Download")', timeout=5000)
        except Exception:
            pass
        link = page.query_selector('a[href$=".pdf"]')
        if link and link.is_visible():
            href = link.get_attribute('href')
            if not href.startswith('http'):
                href = page.url.rstrip('/') + href
            print(f"↓ Downloading PDF: {href}")
            _fetch_and_save(page, href, detail_url)
            return True
        button = page.query_selector('a:has-text("Download"), button:has-text("Download")')
        if button and button.is_visible():
            href = button.get_attribute('href')
            if href and href.lower().endswith('.pdf'):
                print(f"↓ Downloading PDF: {href}")
                _fetch_and_save(page, href, detail_url)
                return True
            else:
                try:
                    with page.expect_download(timeout=30000) as dl:
                        button.click()
                    download = dl.value
                    fname = download.suggested_filename or "crunchbase_report.pdf"
                    target = DOWNLOAD_DIR / fname
                    download.save_as(str(target))
                    print(f"↓ Downloaded Crunchbase PDF: {target}")
                    mapping[detail_url] = fname
                    save_downloaded_mapping(mapping)
                    return True
                except Exception as e:
                    print(f"⚠️ Download button click failed: {e}")
        return False
    if try_download():
        return
    print("No download link/button found, saving page as PDF and logging HTML for debugging.")
    with open("debug_crunchbase_page.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    save_webpage_as_pdf(page, DOWNLOAD_DIR, safe_title, detail_url)
    mapping[detail_url] = pdf_path.name
    save_downloaded_mapping(mapping)

if __name__ == "__main__":
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        scrape_and_download_crunchbase(page)
        browser.close() 