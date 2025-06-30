import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from core.download_utils import DOWNLOAD_DIR, NAV_TIMEOUT, load_downloaded_mapping, save_downloaded_mapping, _fetch_and_save, save_webpage_as_pdf
import re

# --- Beauhurst-specific scraping logic ---
def scrape_and_download_beauhurst(page, max_pages=21):
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
            download_pdf_from_detail(page, detail_url)
            print(f"Would process: {detail_url}")

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
                    fname = download.suggested_filename or "beauhurst_report.pdf"
                    target = DOWNLOAD_DIR / fname
                    download.save_as(str(target))
                    print(f"↓ Downloaded Beauhurst PDF: {target}")
                    mapping[detail_url] = fname
                    save_downloaded_mapping(mapping)
                    return True
                except Exception as e:
                    print(f"⚠️ Download button click failed: {e}")
        return False
    if try_download():
        return
    if page.query_selector("form[id^='hsForm_']") or any(
        iframe.content_frame() and iframe.content_frame().query_selector("form[id^='hsForm_']")
        for iframe in page.query_selector_all("iframe")
    ):
        print("No download link/button found, but found a form. Attempting to fill the form...")
        # You may need to implement or import fill_beauhurst_form
        # if fill_beauhurst_form(page):
        #     page.wait_for_timeout(4000)
        #     confirmation_texts = [
        #         "your report is on the way",
        #         "we've sent your report",
        #         "check your inbox",
        #         "we have sent the report",
        #         "we've emailed your report"
        #     ]
        #     page_content = page.content().lower()
        #     if any(msg in page_content for msg in confirmation_texts):
        #         print("Form submitted: confirmation message detected. Report will be sent by email. Skipping download.")
        #         mapping[detail_url] = 'email_sent'
        #         save_downloaded_mapping(mapping)
        #         return
        #     print("Form filled, report appears to be revealed on page. Saving as PDF.")
        #     save_webpage_as_pdf(page, DOWNLOAD_DIR, safe_title, detail_url)
        #     return
    print("No download link/button or downloadable form found, saving page as PDF and logging HTML for debugging.")
    with open("debug_beauhurst_page.html", "w", encoding="utf-8") as f:
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
        scrape_and_download_beauhurst(page)
        browser.close() 