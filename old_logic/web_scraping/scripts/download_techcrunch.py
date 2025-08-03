import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import re
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from core.download_utils import NAV_TIMEOUT, save_webpage_as_pdf

TECHCRUNCH_URL = "https://techcrunch.com/latest/"
TECHCRUNCH_JSON = os.path.join(os.path.dirname(__file__), '..', 'data', 'techcrunch_downloaded.json')
PDF_DIR = Path('data/vc_reports')
PDF_DIR.mkdir(parents=True, exist_ok=True)


def load_techcrunch_reports():
    if os.path.exists(TECHCRUNCH_JSON):
        with open(TECHCRUNCH_JSON, 'r') as f:
            return json.load(f)
    return {"reports": []}

def save_techcrunch_reports(data):
    with open(TECHCRUNCH_JSON, 'w') as f:
        json.dump(data, f, indent=2)

def close_popups(page):
    # Try to close common popups or overlays
    try:
        # Cookie banner or modal close buttons
        selectors = [
            'button[aria-label="Close"]',
            'button:has-text("Accept")',
            'button:has-text("Got it")',
            'button:has-text("OK")',
            'button:has-text("Dismiss")',
            'button:has-text("No thanks")',
            'button:has-text("✕")',
            'button:has-text("×")',
        ]
        for sel in selectors:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
                print(f"[DEBUG] Closed popup/modal with selector: {sel}")
    except Exception as e:
        print(f"[DEBUG] Failed to close popup/modal: {e}")

def scrape_techcrunch_news(page, max_clicks=100):
    print("\n=== TechCrunch News ===")
    data = load_techcrunch_reports()
    seen_urls = set(r["url"] for r in data["reports"])
    news = []
    clicks = 0
    last_count = 0
    page.goto(TECHCRUNCH_URL, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    close_popups(page)
    for _ in range(5):
        articles1 = page.query_selector_all('a.post-block__title__link')
        articles2 = page.query_selector_all('a.loop-card__title-link')
        articles = articles1 if articles1 else articles2
        if articles:
            break
        page.wait_for_timeout(1000)
    if not articles:
        print("[DEBUG] No article links found after waiting. Exiting.")
        return
    while clicks < max_clicks:
        articles = page.query_selector_all('a.post-block__title__link')
        if not articles:
            articles = page.query_selector_all('a.loop-card__title-link')
        if not articles:
            print("[DEBUG] No article links found with either selector on this page.")
        new_found = False
        for a in articles:
            url = a.get_attribute('href')
            title = a.inner_text().strip()
            if not url:
                continue
            # Try to get date and description
            parent = a.evaluate_handle('node => node.closest("article")')
            date = ""
            desc = ""
            try:
                time_elem = parent.query_selector('time')
                if time_elem:
                    date = time_elem.get_attribute('datetime') or ""
            except Exception:
                pass
            try:
                desc_elem = parent.query_selector('.post-block__content')
                if desc_elem:
                    desc = desc_elem.inner_text().strip()
            except Exception:
                pass
            # Save PDF for every article (unless it already exists)
            safe_title = re.sub(r'[^0-9\w\s-]', '', title)[:50]
            safe_title = re.sub(r'[-\s]+', '_', safe_title).strip('_').lower()
            pdf_path = PDF_DIR / f"{safe_title}.pdf"
            article_success = False
            if not pdf_path.exists():
                try:
                    page2 = page.context.new_page()
                    page2.goto(url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
                    close_popups(page2)
                    # Extract the main article HTML (try headline + main content, then fallback)
                    article_html = None
                    selectors = [
                        ('h1.article-hero__title', 'div.article-content'),  # Headline + main content
                        ('h1.article-hero__title', 'article'),
                        ('h1.article-hero__title', 'main'),
                        (None, 'div.article-hero__middle'),  # Try to extract headline from this if present
                        (None, 'article'),
                        (None, 'main'),
                        (None, 'body')
                    ]
                    for headline_sel, content_sel in selectors:
                        try:
                            content_elem = page2.query_selector(content_sel)
                            if not content_elem:
                                continue
                            content_html = content_elem.inner_html()
                            # Remove unwanted elements from content_html
                            # Remove social/share/author elements by regex
                            content_html = re.sub(r'<div[^>]+class="[^"]*(article-hero__share|article-hero__authors|wp-block-techcrunch-social-share|wp-block-tc23-author-card)[^"]*"[^>]*>.*?</div>', '', content_html, flags=re.DOTALL)
                            # Remove empty divs
                            content_html = re.sub(r'<div[^>]*>\s*</div>', '', content_html, flags=re.DOTALL)
                            # Remove <img> tags with logo-related classes
                            content_html = re.sub(r'<img[^>]+class="[^"]*(logo|logotype|brand-logo)[^"]*"[^>]*>', '', content_html, flags=re.IGNORECASE)
                            # Remove <img> tags with src or alt containing 'arrow' or 'microphone'
                            content_html = re.sub(r'<img[^>]+(src|alt)="[^"]*(arrow|microphone)[^"]*"[^>]*>', '', content_html, flags=re.IGNORECASE)
                            # Remove all <svg> elements (often used for icons)
                            content_html = re.sub(r'<svg[\s\S]*?</svg>', '', content_html, flags=re.IGNORECASE)
                            # Get headline if selector provided
                            headline_html = ''
                            if headline_sel:
                                headline_elem = page2.query_selector(headline_sel)
                                if headline_elem:
                                    headline_html = headline_elem.inner_html()
                                    headline_html = f'<h1>{headline_html}</h1>'
                            # Special case: if content_sel is 'div.article-hero__middle', try to extract <h1> inside it
                            if content_sel == 'div.article-hero__middle' and not headline_html:
                                h1_elem = content_elem.query_selector('h1')
                                if h1_elem:
                                    headline_html = h1_elem.inner_html()
                                    headline_html = f'<h1>{headline_html}</h1>'
                            article_html = f'{headline_html}{content_html}'
                            break
                        except Exception:
                            continue
                    if not article_html:
                        print(f"[ERROR] Could not extract article HTML for {url}")
                        page2.close()
                        # Log failed URL
                        failed_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'techcrunch_failed.json')
                        try:
                            if os.path.exists(failed_path):
                                with open(failed_path, 'r') as f:
                                    failed_data = json.load(f)
                            else:
                                failed_data = {"failed": []}
                            failed_data["failed"].append({"url": url, "title": title, "reason": "extract_html_failed"})
                            with open(failed_path, 'w') as f:
                                json.dump(failed_data, f, indent=2)
                        except Exception as e:
                            print(f"[ERROR] Could not log failed URL: {e}")
                        continue
                    # Minimal CSS for readability
                    minimal_css = '''<style>body { font-family: Arial, sans-serif; margin: 40px; } img { max-width: 100%; } h1, h2, h3 { font-weight: bold; } </style>'''
                    html_content = f'<!DOCTYPE html><html><head>{minimal_css}</head><body>{article_html}</body></html>'
                    # Open a new blank page and set content
                    pdf_page = page.context.new_page()
                    pdf_page.set_content(html_content, wait_until="domcontentloaded")
                    pdf_page.wait_for_timeout(1000)
                    save_webpage_as_pdf(pdf_page, PDF_DIR, safe_title, url)
                    pdf_page.close()
                    page2.close()
                    print(f"[PDF] Saved article as PDF: {pdf_path}")
                    article_success = True
                except Exception as e:
                    print(f"[PDF] Failed to save article as PDF: {e}")
                    # Log failed URL
                    failed_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'techcrunch_failed.json')
                    try:
                        if os.path.exists(failed_path):
                            with open(failed_path, 'r') as f:
                                failed_data = json.load(f)
                        else:
                            failed_data = {"failed": []}
                        failed_data["failed"].append({"url": url, "title": title, "reason": str(e)})
                        with open(failed_path, 'w') as f:
                            json.dump(failed_data, f, indent=2)
                    except Exception as e2:
                        print(f"[ERROR] Could not log failed URL: {e2}")
            else:
                print(f"[PDF] PDF already exists: {pdf_path}")
                article_success = True
            # Only add to JSON if not already present
            if url not in seen_urls:
                news_item = {
                    "url": url,
                    "title": title,
                    "description": desc,
                    "date": date,
                    "content": [],
                    "extracted_date": datetime.utcnow().isoformat()
                }
                news.append(news_item)
                seen_urls.add(url)
                print(f"[DEBUG] Adding new article: {title} ({url})")
                # Save progress after each article
                data["reports"].append(news_item)
                save_techcrunch_reports(data)
            else:
                print(f"[DEBUG] Article already in seen_urls: {title} ({url})")
        if new_found:
            print("[DEBUG] Found and saved new articles, moving to next page if available.")
        if len(news) == last_count:
            print("No new articles found after clicking. Stopping.")
            break
        last_count = len(news)
        # Try to click Next (Load More)
        try:
            btn = page.query_selector('a.wp-block-query-pagination-next')
            if btn and btn.is_enabled():
                btn.click()
                clicks += 1
                print(f"Clicked Next ({clicks}/{max_clicks})")
                page.wait_for_timeout(2000)
            else:
                print("No more Next button found.")
                break
        except Exception:
            print("Failed to click Next button. Stopping.")
            break
    print(f"Found {len(news)} new TechCrunch articles.")
    data["reports"].extend(news)
    save_techcrunch_reports(data)

if __name__ == "__main__":
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        scrape_techcrunch_news(page)
        browser.close() 