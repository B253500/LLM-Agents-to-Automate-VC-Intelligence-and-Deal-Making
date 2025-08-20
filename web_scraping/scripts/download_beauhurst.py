import sys
import os
# Add both parent (web_scraping) and project root so `core` resolves like old logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import re
import random
import string
from pathlib import Path
import platform
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from core.download_utils import DOWNLOAD_DIR, NAV_TIMEOUT, load_downloaded_mapping, save_downloaded_mapping, _fetch_and_save, save_webpage_as_pdf

# Optional metrics hook (set by metrics runner)
_METRICS = None
def set_metrics(metrics):
    global _METRICS
    _METRICS = metrics

# --- Robust Beauhurst-specific scraping logic ---
def fill_beauhurst_form(page):
    try:
        form_selectors = [
            "form[id^='hsForm_']",
            "#hsForm_257d39dc-7a23-4ea9-9fea-aad43090d226_1",
            "#hsForm_d6c1adf0-2bee-44a2-b628-63275657f2a8_1",
            "#hsForm_154937a5-8bb5-4e38-82be-311ba862058b_1"
        ]
        form_context = None
        for selector in form_selectors:
            try:
                page.wait_for_selector(selector, timeout=20000)
                form_context = page
                break
            except Exception:
                continue
        if not form_context:
            iframes = page.query_selector_all("iframe")
            for iframe in iframes:
                try:
                    frame = iframe.content_frame()
                    for selector in form_selectors:
                        if frame and frame.query_selector(selector):
                            form_context = frame
                            break
                    if form_context:
                        break
                except Exception:
                    continue
        if not form_context:
            print("No HubSpot form found on page or in iframes (tried selectors: %s)" % form_selectors)
            return False
        filled = False
        first_name = form_context.query_selector("input[name='firstname']")
        if first_name and first_name.is_visible() and first_name.is_enabled():
            first_name.fill("Aza")
            filled = True
        last_name = form_context.query_selector("input[name='lastname']")
        if last_name and last_name.is_visible() and last_name.is_enabled():
            last_name.fill("Kan")
            filled = True
        email_field = form_context.query_selector("input[name='email']")
        email_to_try = ["ak.somnium@gmail.com", "a.kanatuly@sms.ed.ac.uk"]
        email_filled = False
        for email in email_to_try:
            if email_field and email_field.is_visible() and email_field.is_enabled():
                email_field.fill(email)
                filled = True
                email_field.press('Tab')
                page.wait_for_timeout(500)
                error_elem = None
                error_selectors = [
                    ".hs-error-msg", ".error", "[data-error]", ".field-error", ".invalid-feedback"
                ]
                for sel in error_selectors:
                    error_elem = form_context.query_selector(sel)
                    if error_elem and error_elem.is_visible():
                        error_text = error_elem.inner_text().lower()
                        if ("valid email" in error_text or "business email" in error_text or "enter a valid" in error_text or "not accepted" in error_text):
                            print(f"Email {email} rejected: {error_text}")
                            break
                        else:
                            error_elem = None
                if not error_elem:
                    email_filled = True
                    break
        if not email_filled:
            print("Could not find a valid email to use for this form.")
            return False
        # Try to fill job title, industry, company, phone, company_size, etc. (see download_reports.py for details)
        # ... (omitted for brevity, but can be copied in full if needed) ...
        # --- Submit ---
        submit_btns = form_context.query_selector_all("input[type='submit'], button[type='submit']")
        submit_btn = None
        for btn in submit_btns:
            if btn.is_visible() and btn.is_enabled():
                value = btn.get_attribute("value")
                text = btn.inner_text() if hasattr(btn, 'inner_text') else ''
                btn_text = (value or text or '').lower()
                if 'book demo' in btn_text or 'book a demo' in btn_text:
                    continue
                submit_btn = btn
                print("Submit button value:", value or text)
                break
        if filled and submit_btn:
            print("Submitting Beauhurst report request form...")
            submit_btn.click()
            try:
                page.wait_for_selector('.second_part', timeout=10000, state='visible')
            except Exception:
                try:
                    page.wait_for_selector('#paywall', timeout=10000, state='hidden')
                except Exception:
                    pass
            page.wait_for_timeout(2000)
            return True
        else:
            print("No Beauhurst form fields found or could not fill.")
            return False
    except Exception as e:
        print(f"⚠️ Error filling Beauhurst form: {e}")
        return False

def download_pdf_from_detail(page, detail_url):
    # Count an attempt per detail page visited
    try:
        if _METRICS:
            _METRICS.inc_attempt()
    except Exception:
        pass
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
            try:
                if _METRICS:
                    _METRICS.inc_direct_saved()
            except Exception:
                pass
            return True
        button = page.query_selector('a:has-text("Download"), button:has-text("Download")')
        if button and button.is_visible():
            href = button.get_attribute('href')
            if href and href.lower().endswith('.pdf'):
                print(f"↓ Downloading PDF: {href}")
                _fetch_and_save(page, href, detail_url)
                try:
                    if _METRICS:
                        _METRICS.inc_direct_saved()
                except Exception:
                    pass
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
                    try:
                        if _METRICS:
                            _METRICS.inc_direct_saved()
                    except Exception:
                        pass
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
        if fill_beauhurst_form(page):
            page.wait_for_timeout(4000)
            confirmation_texts = [
                "your report is on the way",
                "we've sent your report",
                "check your inbox",
                "we have sent the report",
                "we've emailed your report"
            ]
            page_content = page.content().lower()
            if any(msg in page_content for msg in confirmation_texts):
                print("Form submitted: confirmation message detected. Report will be sent by email. Skipping download.")
                mapping[detail_url] = 'email_sent'
                save_downloaded_mapping(mapping)
                try:
                    if _METRICS:
                        _METRICS.inc_email_sent()
                except Exception:
                    pass
                return
            print("Form filled, report appears to be revealed on page. Saving as PDF.")
            save_webpage_as_pdf(page, DOWNLOAD_DIR, safe_title, detail_url)
            try:
                if _METRICS:
                    _METRICS.inc_fallback_saved()
            except Exception:
                pass
            return
    print("No download link/button or downloadable form found, saving page as PDF and logging HTML for debugging.")
    with open("debug_beauhurst_page.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    save_webpage_as_pdf(page, DOWNLOAD_DIR, safe_title, detail_url)
    mapping[detail_url] = pdf_path.name
    save_downloaded_mapping(mapping)
    try:
        if _METRICS:
            _METRICS.inc_fallback_saved()
    except Exception:
        pass

def scrape_and_download_beauhurst(page, max_pages=21):
    print("=== Beauhurst Reports ===")
    base = "https://www.beauhurst.com"
    for i in range(1, max_pages + 1):
        url = f"{base}/reports/" if i == 1 else f"{base}/reports/page/{i}/"
        print(f"Fetching report list page: {url}")
        try:
            page.goto(url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
        except Exception as e:
            print(f"⚠️ Could not load {url}: {e}")
            continue
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
            try:
                download_pdf_from_detail(page, detail_url)
            except Exception as e:
                print(f"⚠️ Could not process detail page {detail_url}: {e}")
                continue

if __name__ == "__main__":
    with sync_playwright() as pw:
        # Launch like the stable runner to avoid macOS headless crashes
        if platform.system() == "Darwin":
            try:
                browser = pw.chromium.launch(channel="chrome", headless=False)
                context = browser.new_context(accept_downloads=True)
            except Exception:
                # Fallback to bundled Chromium persistent context
                user_data_dir = "/tmp/playwright_user_data"
                context = pw.chromium.launch_persistent_context(user_data_dir, headless=False, accept_downloads=True)
        else:
            # Non-macOS: persistent headless context with safe flags
            user_data_dir = "/tmp/playwright_user_data"
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu'
            ]
            context = pw.chromium.launch_persistent_context(user_data_dir, headless=True, accept_downloads=True, args=browser_args)

        page = context.new_page()
        # Match older behavior: desktop UA helps avoid odd render paths
        try:
            page.context.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            })
        except Exception:
            pass
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        scrape_and_download_beauhurst(page)
        try:
            context.close()
        except Exception:
            pass