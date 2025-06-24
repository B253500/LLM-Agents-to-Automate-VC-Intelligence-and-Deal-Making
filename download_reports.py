# download_reports.py - Playwright script for Crunchbase, Beauhurst & PitchBook
# Requirements:
#   python >=3.7
#   pip install playwright
#   playwright install

import re
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError

# Download directory
DOWNLOAD_DIR = Path(__file__).parent / "data" / "vc_reports"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Timeouts (ms)
NAV_TIMEOUT = 60000
DOWNLOAD_TIMEOUT = 120000


def download_pdf_from_detail(page, detail_url):
    """Visit a detail page and download the PDF via iframe, link, or button."""
    try:
        page.goto(detail_url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    except PlaywrightError as e:
        print(f"⚠️ Failed to load {detail_url}: {e}")
        return

    print(f"Looking for download button on: {detail_url}")
    button = page.query_selector("a.elementor-button:has-text('Download')")
    print(f"Button found: {bool(button)}")
    if button:
        href = button.get_attribute('href')
        if href and href.lower().endswith('.pdf'):
            fname = href.split('/')[-1].split('?')[0]
            target = DOWNLOAD_DIR / fname
            if not target.exists():
                print(f"↓ fetching {fname}")
                resp = page.context.request.get(href, timeout=DOWNLOAD_TIMEOUT)
                with open(target, 'wb') as f:
                    f.write(resp.body())
            else:
                print(f"✓ already have {fname}")
            return
    # Try iframe/embed
    frame = page.query_selector('iframe[src$=".pdf"], embed[type="application/pdf"]')
    if frame:
        href = frame.get_attribute('src')
        if href:
            full = href if href.startswith('http') else page.url.rstrip('/') + href
            _fetch_and_save(page, full)
        return
    # Try direct <a href="...pdf">
    link = page.query_selector('a[href$=".pdf"]')
    if link:
        href = link.get_attribute('href')
        if href:
            full = href if href.startswith('http') else page.url.rstrip('/') + href
            _fetch_and_save(page, full)
        return
    # Try Download button (generic)
    button = page.query_selector("a:has-text('Download')") or page.query_selector("button:has-text('Download')")
    if button:
        try:
            with page.expect_download(timeout=DOWNLOAD_TIMEOUT) as dl:
                button.click()
            download = dl.value
            fname = download.suggested_filename or Path(detail_url).name + '.pdf'
            target = DOWNLOAD_DIR / fname
            if not target.exists():
                print(f"↓ saving {fname}")
                download.save_as(str(target))
            else:
                print(f"✓ already have {fname}")
        except PlaywrightError as e:
            print(f"⚠️ Download failed for {detail_url}: {e}")
        return
    print(f"⚠️ No PDF found on {detail_url}")


def _fetch_and_save(page, url: str):
    """Helper: fetch PDF via HTTP and save."""
    fname = url.split('/')[-1].split('?')[0]
    target = DOWNLOAD_DIR / fname
    if target.exists():
        print(f"✓ already have {fname}")
        return
    print(f"↓ fetching {fname}")
    resp = page.context.request.get(url, timeout=DOWNLOAD_TIMEOUT)
    with open(target, 'wb') as f:
        f.write(resp.body())


def scrape_and_download_crunchbase(page):
    print("=== Crunchbase Reports ===")
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
    print(f"Found {len(urls)} Crunchbase detail pages. Only a limited number have direct PDF downloads; others are summaries or require manual access.")
    for url in urls:
        download_pdf_from_detail(page, url)


def scrape_and_download_beauhurst(page, max_pages=5):
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
        # Updated selector for Beauhurst report links
        cards = page.query_selector_all("a[href*='/research/']")
        print(f"Found {len(cards)} report cards on page {i}")
        report_links = []
        for a in cards:
            href = a.get_attribute('href')
            text = a.inner_text().strip() if a.inner_text() else ''
            print(f"Found report: {text} ({href})")
            if not href:
                continue
            detail_url = href if href.startswith('http') else base + href
            if detail_url not in report_links:
                report_links.append(detail_url)
        for detail_url in report_links:
            print(f"Visiting detail page: {detail_url}")
            download_pdf_from_detail(page, detail_url)


def scrape_and_download_pitchbook(page):
    print("=== PitchBook Reports ===")
    try:
        # Set a real user-agent
        page.context.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })
        page.goto("https://pitchbook.com/news/reports", timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    except PlaywrightError as e:
        print(f"⚠️ Could not load PitchBook listing: {e}")
        return

    # Wait for the report list to load (try longer)
    try:
        page.wait_for_selector("ul.report-center__feature, ul.report-center__list", timeout=30000)
        print("Report list loaded.")
    except PlaywrightError:
        print("⚠️ Report list did not load in time.")

    # Try scrolling to the bottom multiple times to trigger lazy loading
    for i in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)  # wait for 2 seconds
        print(f"Scrolled to bottom {i+1}/5")

    # Save the page content to a file for inspection
    html_content = page.content()
    with open("pitchbook_debug.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Saved page content to pitchbook_debug.html")

    # Find all report links (not the main listing page itself)
    links = page.query_selector_all("a[href^='/news/reports/']")
    print(f"DEBUG: Found {len(links)} <a> tags with /news/reports/ in href")
    for a in links:
        print("DEBUG:", a.get_attribute('href'), "|", a.inner_text())

    detail_urls = []
    for a in links:
        href = a.get_attribute('href')
        if href and href != '/news/reports':
            full = f"https://pitchbook.com{href}"
            if full not in detail_urls:
                detail_urls.append(full)
    print(f"Found {len(detail_urls)} PitchBook detail pages")
    for du in detail_urls:
        try:
            print(f"Visiting PitchBook detail page: {du}")
            page.goto(du, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
        except PlaywrightError as e:
            print(f"⚠️ Failed to load {du}: {e}")
            continue
        # Wait for the form to appear after navigation
        try:
            page.wait_for_selector("input[name='FirstName']", timeout=15000)
        except PlaywrightError:
            print(f"⚠️ No form found on detail page after navigating to {du}")
            continue
        print("Filling out PitchBook download form...")
        page.fill("input[name='FirstName']", "Aza")
        page.fill("input[name='LastName']", "Kan")
        page.fill("input[name='Email']", "a.kanatuly@sms.ed.ac.uk")
        checkbox = page.query_selector("input[type='checkbox']")
        if checkbox:
            # Try to check the checkbox, or click the label/icon if that fails
            try:
                checkbox.check()
                print("Checked agreement checkbox (input).")
            except Exception as e:
                print("Checkbox .check() failed, trying to click the label or icon...")
                # Try clicking the parent label
                label = checkbox.evaluate_handle('el => el.closest("label")')
                if label:
                    label.click()
                    print("Checked agreement checkbox (label).")
                else:
                    icon = page.query_selector(".custom-checkbox__icon")
                    if icon:
                        icon.click()
                        print("Checked agreement checkbox (icon).")
        else:
            print("⚠️ No agreement checkbox found.")
        # Wait a moment for the button to become enabled
        page.wait_for_timeout(500)
        # Print all button texts for debug
        buttons = page.query_selector_all("button")
        for b in buttons:
            print("BUTTON DEBUG:", b.inner_text())
        # Try to click the Download Report button or input[type=submit] (case-insensitive, flexible selector)
        try:
            # Wait for the submit input to be enabled
            page.wait_for_selector("input[type='submit'][value^='Download report']:not([disabled])", timeout=10000)
            download_btn = (
                page.query_selector("input[type='submit'][value^='Download report']:not([disabled])") or
                page.query_selector("input[type='submit'][value^='Download Report']:not([disabled])")
            )
            if download_btn:
                download_btn.click()
                print("Clicked Download report submit input.")
            else:
                print("⚠️ Could not find Download report submit input.")
                continue
            print("Submitted form, waiting for download PDF button...")
        except PlaywrightError as e:
            print(f"⚠️ Form submit failed: {e}")
            continue
        # Wait for and click the final 'Download PDF' button
        try:
            page.wait_for_selector("a:has-text('Download PDF')", timeout=DOWNLOAD_TIMEOUT)
            pdf_button = page.query_selector("a:has-text('Download PDF')")
            if pdf_button:
                href = pdf_button.get_attribute('href')
                if href and href.lower().endswith('.pdf'):
                    fname = href.split('/')[-1].split('?')[0]
                    target = DOWNLOAD_DIR / fname
                    if not target.exists():
                        print(f"↓ fetching {fname}")
                        resp = page.context.request.get(href, timeout=DOWNLOAD_TIMEOUT)
                        with open(target, 'wb') as f:
                            f.write(resp.body())
                    else:
                        print(f"✓ already have {fname}")
                    continue
            print(f"⚠️ No Download PDF button found after form submit")
        except PlaywrightError as e:
            print(f"⚠️ Waiting for Download PDF button failed: {e}")


def main():
    with sync_playwright() as pw:
        global page
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)

        scrape_and_download_crunchbase(page)
        scrape_and_download_beauhurst(page)
        scrape_and_download_pitchbook(page)

        browser.close()

if __name__ == '__main__':
    main()
