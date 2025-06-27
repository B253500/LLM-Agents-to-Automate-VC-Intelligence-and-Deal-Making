import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from core.download_utils import DOWNLOAD_DIR, NAV_TIMEOUT, load_downloaded_mapping, _fetch_and_save, save_webpage_as_pdf, save_downloaded_mapping
import time

# --- PitchBook-specific scraping logic ---
def scrape_and_download_pitchbook(page):
    print("\n=== PitchBook Reports ===")
    try:
        page.context.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })
        page.goto("https://pitchbook.com/news/reports", timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    except PlaywrightError as e:
        print(f"⚠️ Could not load PitchBook listing: {e}")
        return

    try:
        page.wait_for_selector(".report-center__feature, .report-center__list", timeout=30000)
    except PlaywrightError:
        print("⚠️ Report list did not load in time")
        return

    # Robustly click all 'See all' buttons until no more appear
    while True:
        see_all_buttons = page.query_selector_all("a.btn-primary_teal, a:has-text('See all')")
        clicked = False
        for btn in see_all_buttons:
            if btn.is_visible() and btn.is_enabled():
                try:
                    btn.click()
                    page.wait_for_timeout(2000)
                    clicked = True
                except Exception:
                    continue
        if not clicked:
            break

    # Scroll to bottom several times to trigger lazy loading
    last_count = 0
    for _ in range(10):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1500)
        links = page.query_selector_all("a[href^='/news/reports/']")
        if len(links) == last_count:
            break
        last_count = len(links)
        print(f"Scrolled, found {last_count} links so far...")

    # Use the broad selector to get all report links
    links = page.query_selector_all("a[href^='/news/reports/']")
    detail_urls = set()
    for a in links:
        href = a.get_attribute('href')
        if href and href != '/news/reports':
            full = f"https://pitchbook.com{href}"
            detail_urls.add(full)

    print(f"Found {len(detail_urls)} PitchBook reports")
    mapping = load_downloaded_mapping()
    for du in detail_urls:
        if du in mapping:
            print(f"✓ Already processed: {du} -> {mapping[du]}")
            continue
        print(f"→ Processing: {du}")
        try:
            page2 = page.context.new_page()
            page2.goto(du, timeout=60000, wait_until="domcontentloaded")
            print(f"  [LOG] Opened detail page: {du}")

            # Dismiss custom cookie modal if present (prefer Accept All Cookies)
            try:
                page2.wait_for_selector("button:has-text('Accept All Cookies'), button:has-text('Reject All'), button[aria-label='Close']", timeout=5000)
                try:
                    page2.click("button:has-text('Accept All Cookies')", timeout=2000, force=True)
                    print("    [LOG] Clicked 'Accept All Cookies' on custom cookie modal")
                except Exception:
                    try:
                        page2.click("button:has-text('Reject All')", timeout=2000, force=True)
                        print("    [LOG] Clicked 'Reject All' on custom cookie modal")
                    except Exception:
                        page2.click("button[aria-label='Close']", timeout=2000, force=True)
                        print("    [LOG] Clicked close (X) on custom cookie modal")
                page2.wait_for_timeout(1000)
            except Exception as e:
                print(f"    [LOG] No custom cookie modal or could not dismiss: {e}")

            # Robustly dismiss OneTrust cookie modal if present (fallback)
            try:
                page2.wait_for_selector("button.ot-pc-refuse-all-handler, button.save-preference-btn-handler", timeout=5000)
                try:
                    page2.click("button.ot-pc-refuse-all-handler", timeout=2000, force=True)
                    print("    [LOG] Clicked 'Reject All' on OneTrust modal")
                except Exception:
                    try:
                        page2.click("button.save-preference-btn-handler", timeout=2000, force=True)
                        print("    [LOG] Clicked 'Confirm My Choices' on OneTrust modal")
                    except Exception:
                        page2.evaluate("""() => {
                            let btn = document.querySelector('button.ot-pc-refuse-all-handler') || document.querySelector('button.save-preference-btn-handler');
                            if (btn) btn.click();
                        }""")
                        print("    [LOG] Clicked modal button via JS")
                page2.wait_for_selector("button.ot-pc-refuse-all-handler, button.save-preference-btn-handler", state='detached', timeout=5000)
                print("    [LOG] OneTrust modal gone")
            except Exception as e:
                print(f"    [LOG] No OneTrust modal or could not dismiss: {e}")
            # Take a debug screenshot after attempting to dismiss modal
            try:
                page2.screenshot(path=f"debug_modal_{int(time.time())}.png")
            except Exception as e:
                print(f"    [LOG] Could not take debug screenshot: {e}")

            # Try to find a direct PDF link
            pdf_link = None
            for a in page2.query_selector_all("a"):
                href = a.get_attribute("href")
                if href and href.lower().endswith(".pdf"):
                    pdf_link = href if href.startswith("http") else f"https://pitchbook.com{href}"
                    break
            if pdf_link:
                print(f"  [LOG] Found direct PDF link: {pdf_link}")
                _fetch_and_save(page2, pdf_link, detail_url=du)
            else:
                print(f"  [LOG] No direct PDF link found, trying form workflow...")
                try:
                    # Minimal, robust PitchBook workflow: fill only required fields, handle checkbox, submit, fetch PDF
                    try:
                        # Wait for the form to appear
                        page2.wait_for_selector("input[name='FirstName']", timeout=15000)
                        page2.fill("input[name='FirstName']", "Aza")
                        page2.fill("input[name='LastName']", "Kan")
                        page2.fill("input[name='Email']", "ak.somnium@gmail.com")
                        print("    [LOG] Filled required fields")

                        # Try to check the checkbox using page2.click for more realism
                        checkbox_selector = "input[type='checkbox'][name='agree']"
                        label_selector = "label:has(input[type='checkbox'][name='agree'])"
                        icon_selector = ".custom-checkbox__icon"
                        checked = False
                        try:
                            page2.click(checkbox_selector, force=True)
                            print("    [LOG] Checked agreement checkbox (input) via page2.click")
                            checked = True
                        except Exception:
                            try:
                                page2.click(label_selector, force=True)
                                print("    [LOG] Checked agreement checkbox (label) via page2.click")
                                checked = True
                            except Exception:
                                try:
                                    page2.click(icon_selector, force=True)
                                    print("    [LOG] Checked agreement checkbox (icon) via page2.click")
                                    checked = True
                                except Exception:
                                    print("⚠️ No agreement checkbox found or clickable.")
                        if not checked:
                            print("⚠️ Could not check the agreement checkbox. Printing HTML for debugging:")
                            print(page2.content())

                        # Wait for the submit button to be enabled
                        try:
                            page2.wait_for_selector("input[type='submit'][value='Download report']:not([disabled])", timeout=5000)
                        except Exception:
                            print("⚠️ Submit button may be disabled. Printing HTML for debugging:")
                            print(page2.content())

                        # Click the submit button using page2.click for realism
                        try:
                            page2.click("input[type='submit'][value='Download report']", force=True)
                            print("    [LOG] Clicked 'Download report' submit button via page2.click")
                        except Exception as e:
                            print(f"⚠️ Could not click Download report submit input: {e}")
                            print(page2.content())
                            return

                        # Wait for the Download PDF button to appear and click it
                        try:
                            page2.wait_for_selector("a:has-text('Download PDF'), a[href$='.pdf']", timeout=10000)
                            pdf_button = page2.query_selector("a:has-text('Download PDF'), a[href$='.pdf']")
                            if pdf_button:
                                pdf_button.click()
                                print("    [LOG] Clicked 'Download PDF' button")
                                # Wait for the download event
                                with page2.expect_download(timeout=15000) as download_info:
                                    pass
                                download = download_info.value
                                fname = download.suggested_filename
                                target = DOWNLOAD_DIR / fname
                                download.save_as(str(target))
                                print(f"↓ Downloaded {fname}")
                                mapping = load_downloaded_mapping()
                                mapping[du] = fname
                                save_downloaded_mapping(mapping)
                                download_success = True
                            else:
                                print("⚠️ Download PDF button not found after form submission.")
                        except Exception as e:
                            print(f"⚠️ Error waiting for or clicking Download PDF button: {e}")
                    except Exception as e:
                        print(f"⚠️ Error during PitchBook download workflow: {e}")
                except Exception as e:
                    print(f"⚠️ Error during PitchBook download workflow: {e}")
            page2.close()
        except Exception as e:
            print(f"⚠️ Error processing {du}: {e}")

if __name__ == "__main__":
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        scrape_and_download_pitchbook(page)
        browser.close() 