import sys
import os
import time
import random

from playwright.sync_api import sync_playwright, Error as PlaywrightError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.download_utils import DOWNLOAD_DIR, NAV_TIMEOUT, load_downloaded_mapping, _fetch_and_save, save_webpage_as_pdf, save_downloaded_mapping

REPORT_LISTING_URLS = [
    "https://pitchbook.com/news/reports",
    "https://pitchbook.com/news/reports?types=analyst-note",
    "https://pitchbook.com/news/reports?topics=industry-and-technology-research",
    "https://pitchbook.com/news/reports?types=market-update,snapshot"
]

def scroll_until_found(page, selector, max_scrolls=10, scroll_step=400):
    for i in range(max_scrolls):
        el = page.query_selector(selector)
        if el and el.is_visible():
            print(f"    [LOG] Found element for selector '{selector}' after {i} scrolls.")
            return el
        page.evaluate(f"window.scrollBy(0, {scroll_step})")
        page.wait_for_timeout(300)
    print(f"    [LOG] Could not find element for selector '{selector}' after {max_scrolls} scrolls.")
    return None

def scrape_and_download_pitchbook(page):
    print("\n=== PitchBook Reports ===")
    mapping = load_downloaded_mapping()
    for idx, listing_url in enumerate(REPORT_LISTING_URLS):
        print(f"\n[LOG] Processing listing: {listing_url}")
        try:
            page.context.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            })
            page.goto(listing_url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
        except PlaywrightError as e:
            print(f"⚠️ Could not load PitchBook listing: {e}")
            continue
        except Exception as e:
            print(f"⚠️ Error setting extra HTTP headers or loading listing: {e}")
            continue
        try:
            page.wait_for_selector(".report-center__feature, .report-center__list", timeout=10000)
            # For all but the first listing, wait for at least one real report link to appear
            if idx != 0:
                try:
                    page.wait_for_selector("a[href^='/news/reports/']:not([href='/news/reports'])", timeout=5000)
                except PlaywrightError:
                    print("⚠️ No report links loaded in time on this listing.")
                    continue
        except PlaywrightError:
            print("⚠️ Report list did not load in time")
            continue
        # Expand all 'See all'
        while True:
            btns = page.query_selector_all("a.btn-primary_teal, a:has-text('See all')")
            clicked = False
            for btn in btns:
                if btn.is_visible() and btn.is_enabled():
                    try:
                        btn.click()
                        page.wait_for_timeout(1000)
                        clicked = True
                    except:
                        pass
            if not clicked:
                break
        # For the first listing, behave as before
        if idx == 0:
            last_count = 0
            for _ in range(10):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1500)
                links = page.query_selector_all("a[href^='/news/reports/']")
                if len(links) == last_count:
                    break
                last_count = len(links)
                print(f"Scrolled, found {last_count} links so far...")
            detail_urls = []
            seen = set()
            for a in page.query_selector_all("a[href^='/news/reports/']"):
                href = a.get_attribute('href')
                if href and href != '/news/reports':
                    full = f"https://pitchbook.com{href}"
                    if full not in seen:
                        seen.add(full)
                        detail_urls.append(full)
                if len(detail_urls) >= 100:
                    break
            print(f"Found {len(detail_urls)} PitchBook reports on this listing")
            for du in detail_urls:
                if du in mapping:
                    print(f"✓ Already processed: {du} -> {mapping[du]}")
                    continue
                print(f"→ Processing: {du}")
                try:
                    page2 = page.context.new_page()
                    page2.goto(du, timeout=5000, wait_until="domcontentloaded")
                    print(f"  [LOG] Opened detail page: {du}")
                    # Dismiss cookies modals
                    for sel in [
                        "button:has-text('Accept All Cookies')",
                        "button:has-text('Reject All')",
                        "button[aria-label='Close']",
                        "button.ot-pc-refuse-all-handler",
                        "button.save-preference-btn-handler"
                    ]:
                        try:
                            page2.click(sel, timeout=2000, force=True)
                            page2.wait_for_timeout(500)
                        except:
                            continue
                    # Try direct PDF
                    pdf_link = None
                    for a in page2.query_selector_all("a"): 
                        href = a.get_attribute('href')
                        if href and href.lower().endswith('.pdf'):
                            pdf_link = href if href.startswith('http') else f"https://pitchbook.com{href}"
                            break
                    if pdf_link:
                        print(f"  [LOG] Found direct PDF link: {pdf_link}")
                        _fetch_and_save(page2, pdf_link, detail_url=du)
                        page2.close()
                        continue
                    # Fill form and download via Playwright download event
                    print("  [LOG] No direct PDF, using form workflow...")
                    page2.wait_for_selector("input[name='FirstName']", timeout=5000)
                    page2.fill("input[name='FirstName']", "Aza")
                    page2.fill("input[name='LastName']", "Kan")
                    page2.fill("input[name='Email']", "ak.somnium@gmail.com")
                    # Check agreement checkbox if present (robust)
                    checkbox_selectors = [
                        "input[type='checkbox'][name='agree']",
                        "label:has(input[type='checkbox'][name='agree'])",
                        ".custom-checkbox__icon"
                    ]
                    checked = False
                    for sel in checkbox_selectors:
                        try:
                            el = page2.query_selector(sel)
                            if el:
                                el.scroll_into_view_if_needed()
                                page2.wait_for_timeout(200)
                                # Log bounding box and visibility
                                bbox = el.bounding_box() if hasattr(el, 'bounding_box') else None
                                is_visible = el.is_visible() if hasattr(el, 'is_visible') else None
                                print(f"    [DEBUG] Checkbox selector: {sel}, bbox: {bbox}, is_visible: {is_visible}")
                                try:
                                    el.click(force=True)
                                    print(f"    [LOG] Checked agreement checkbox using selector: {sel} (Playwright .click())")
                                    checked = True
                                    break
                                except Exception as e:
                                    print(f"    [LOG] Playwright .click() failed for checkbox: {e}, trying JS click...")
                                    try:
                                        page2.evaluate('(el) => el.click()', el)
                                        print(f"    [LOG] Checked agreement checkbox using selector: {sel} (JS click)")
                                        checked = True
                                        break
                                    except Exception as e2:
                                        print(f"    [LOG] JS click also failed for checkbox: {e2}")
                                        # Take a screenshot for debugging
                                        sanitized_sel = sel.replace('[','').replace(']','').replace('=','_').replace('"','').replace("'",'')
                                        screenshot_path = f"checkbox_click_error_{sanitized_sel}.png"
                                        page2.screenshot(path=screenshot_path)
                                        print(f"    [DEBUG] Screenshot saved to {screenshot_path}")
                        except Exception as e:
                            print(f"    [LOG] Could not check agreement checkbox with selector {sel}: {e}")
                    if not checked:
                        print("⚠️ Could not check the agreement checkbox. Printing form HTML for debugging:")
                        try:
                            form = page2.query_selector('form')
                            if form:
                                print(form.inner_html())
                            else:
                                print(page2.content())
                        except Exception as e:
                            print(f"    [LOG] Could not print form HTML: {e}")
                    # Wait for submit button to become enabled
                    submit_btn = page2.wait_for_selector("input[type='submit'][value='Download report']:not([disabled]), input[type='submit'][value='Download']:not([disabled])", timeout=5000)
                    # Trigger form submission
                    submit_btn.click(force=True)
                    page2.wait_for_timeout(3000)  # Wait 3 seconds after submit for UI to update
                    # After 3 seconds, search for Download PDF or Download button and click it
                    # Try to directly extract the PDF link and download
                    a_tag = page2.query_selector("a.report__download-btn[href$='.pdf']")
                    if a_tag:
                        pdf_url = a_tag.get_attribute('href')
                        if pdf_url and not pdf_url.startswith('http'):
                            pdf_url = f'https://pitchbook.com{pdf_url}'
                        try:
                            pdf_bytes = page2.context.request.get(pdf_url).body()
                            filename = os.path.basename(pdf_url.split('?')[0])
                            with open(os.path.join(DOWNLOAD_DIR, filename), 'wb') as f:
                                f.write(pdf_bytes)
                            mapping = load_downloaded_mapping()
                            mapping[du] = filename
                            save_downloaded_mapping(mapping)
                            print(f'    [LOG] Downloaded PDF directly from link: {filename}')
                            page2.close()
                            continue
                        except Exception as e:
                            print(f'    [WARN] Failed to download PDF directly from link: {e}')
                    # Fill optional questionnaire if present before clicking Download PDF
                    # Check 'Raising capital' if present
                    try:
                        labels = page2.query_selector_all("label")
                        for label in labels:
                            text = label.inner_text().strip()
                            if "Raising capital" in text:
                                cb = label.query_selector("input[type='checkbox']")
                                if cb and not cb.is_checked():
                                    cb.check()
                                    print("    [LOG] Checked 'Raising capital' optional checkbox.")
                                break
                    except Exception as e:
                        print(f"    [LOG] Could not check 'Raising capital' checkbox: {e}")
                    # Select first available Job Role if present
                    try:
                        select = page2.query_selector("select")
                        if select:
                            options = select.query_selector_all("option")
                            for opt in options:
                                value = opt.get_attribute('value')
                                if value and value != '' and value.lower() != 'select one':
                                    select.select_option(value)
                                    print(f"    [LOG] Selected first Job Role option: {value}")
                                    break
                    except Exception as e:
                        print(f"    [LOG] Could not select Job Role: {e}")
                    # Robust click logic for Download PDF/Download button/link
                    print("    [LOG] Attempting to click Download PDF/Download button/link...")
                    # Take screenshot before click
                    debug_ts = int(time.time())
                    page2.screenshot(path=f"before_download_pdf_click_{debug_ts}.png")
                    print("    [DEBUG] Screenshot before clicking Download PDF.")
                    clicked = False
                    # Fill optional questionnaire if present before clicking Download PDF
                    # Check 'Raising capital' if present
                    try:
                        labels = page2.query_selector_all("label")
                        for label in labels:
                            text = label.inner_text().strip()
                            if "Raising capital" in text:
                                cb = label.query_selector("input[type='checkbox']")
                                if cb and not cb.is_checked():
                                    cb.check()
                                    print("    [LOG] Checked 'Raising capital' optional checkbox.")
                                break
                    except Exception as e:
                        print(f"    [LOG] Could not check 'Raising capital' checkbox: {e}")
                    # Select first available Job Role if present
                    try:
                        select = page2.query_selector("select")
                        if select:
                            options = select.query_selector_all("option")
                            for opt in options:
                                value = opt.get_attribute('value')
                                if value and value != '' and value.lower() != 'select one':
                                    select.select_option(value)
                                    print(f"    [LOG] Selected first Job Role option: {value}")
                                    break
                    except Exception as e:
                        print(f"    [LOG] Could not select Job Role: {e}")
                    if not pdf_link:
                        page2.close()
                        continue
                    # Robust click logic for Download PDF/Download button/link
                    print("    [LOG] Attempting to click Download PDF/Download button/link...")
                    # Take screenshot before click
                    debug_ts = int(time.time())
                    page2.screenshot(path=f"before_download_pdf_click_{debug_ts}.png")
                    print("    [DEBUG] Screenshot before clicking Download PDF.")
                    clicked = False
                    if pdf_link:
                        is_visible = pdf_link.is_visible()
                        is_enabled = not pdf_link.is_disabled()
                        box = pdf_link.bounding_box()
                        print(f"    [DEBUG] Download PDF button: visible={is_visible}, enabled={is_enabled}, bbox={box}")
                        if is_visible and is_enabled and box:
                            try:
                                pdf_link.scroll_into_view_if_needed()
                                page2.wait_for_timeout(200)
                                pdf_link.click(force=True)
                                print("    [LOG] Clicked using Playwright .click()")
                                clicked = True
                            except Exception as e:
                                print(f"    [LOG] Playwright .click() failed: {e}, trying JS click...")
                                try:
                                    page2.evaluate('(el) => el.click()', pdf_link)
                                    print("    [LOG] Clicked using JS .click()")
                                    clicked = True
                                except Exception as e2:
                                    print(f"    [LOG] JS .click() also failed: {e2}")
                        else:
                            print("    [WARN] Download PDF button is not interactable. Skipping click.")
                    # Take screenshot after click
                    page2.wait_for_timeout(1000)
                    page2.screenshot(path=f"after_download_pdf_click_{debug_ts}.png")
                    print("    [DEBUG] Screenshot after clicking Download PDF.")
                    if not clicked:
                        page2.close()
                        continue
                    # Handle new tab or download event, wait up to 30s, fallback wait if needed
                    download_success = False
                    popup_page = None
                    # Add handler to catch any new pages opened in the context
                    def on_new_page(new_page):
                        nonlocal popup_page
                        popup_page = new_page
                    page2.context.on('page', on_new_page)
                    try:
                        with page2.context.expect_page(timeout=5000) as popup_info:
                            pass  # The click has already been performed
                        try:
                            popup = popup_info.value
                            popup.wait_for_load_state("load", timeout=5000)
                            pdf_url = popup.url
                            if pdf_url.lower().endswith('.pdf'):
                                pdf_bytes = page2.context.request.get(pdf_url).body()
                                filename = os.path.basename(pdf_url.split("?")[0])
                                with open(os.path.join(DOWNLOAD_DIR, filename), "wb") as f:
                                    f.write(pdf_bytes)
                                mapping = load_downloaded_mapping()
                                mapping[du] = filename
                                save_downloaded_mapping(mapping)
                                print(f"    [LOG] Downloaded file from popup: {filename}")
                                download_success = True
                            else:
                                # Try to find PDF URL in iframe, embed, or <a> in popup
                                found_pdf_url = None
                                # Check for iframe or embed
                                for selector in ['iframe', 'embed']:
                                    elems = popup.query_selector_all(selector)
                                    for elem in elems:
                                        src = elem.get_attribute('src')
                                        if src and '.pdf' in src.lower():
                                            found_pdf_url = src if src.startswith('http') else f"https://pitchbook.com{src}"
                                            break
                                    if found_pdf_url:
                                        break
                                # Check for <a> with .pdf in href
                                if not found_pdf_url:
                                    for a in popup.query_selector_all('a'):
                                        href = a.get_attribute('href')
                                        if href and '.pdf' in href.lower():
                                            found_pdf_url = href if href.startswith('http') else f"https://pitchbook.com{href}"
                                            break
                                if found_pdf_url:
                                    pdf_bytes = page2.context.request.get(found_pdf_url).body()
                                    filename = os.path.basename(found_pdf_url.split("?")[0])
                                    with open(os.path.join(DOWNLOAD_DIR, filename), "wb") as f:
                                        f.write(pdf_bytes)
                                    mapping = load_downloaded_mapping()
                                    mapping[du] = filename
                                    save_downloaded_mapping(mapping)
                                    print(f"    [LOG] Downloaded file from popup viewer: {filename}")
                                    download_success = True
                                else:
                                    # Save screenshot and HTML for debugging
                                    debug_ts = int(time.time())
                                    popup.screenshot(path=f"popup_no_pdf_{debug_ts}.png")
                                    with open(f"popup_no_pdf_{debug_ts}.html", "w") as f:
                                        f.write(popup.content())
                                    print(f"    [DEBUG] No PDF found in popup, saved screenshot and HTML for debugging.")
                            popup.close()
                        except Exception:
                            with page2.expect_download(timeout=5000) as download_info:
                                pass  # The click has already been performed
                            download = download_info.value
                            path = download.path()
                            filename = download.suggested_filename or os.path.basename(path)
                            target = os.path.join(DOWNLOAD_DIR, filename)
                            download.save_as(target)
                            mapping = load_downloaded_mapping()
                            mapping[du] = filename
                            save_downloaded_mapping(mapping)
                            print(f"    [LOG] Downloaded file: {filename}")
                            download_success = True
                    except Exception:
                        pass
                    # If no download or popup detected, check if a new page was opened via the event handler
                    if not download_success and popup_page:
                        try:
                            popup_page.wait_for_load_state("load", timeout=5000)
                            pdf_url = popup_page.url
                            if pdf_url.lower().endswith('.pdf'):
                                pdf_bytes = page2.context.request.get(pdf_url).body()
                                filename = os.path.basename(pdf_url.split("?")[0])
                                with open(os.path.join(DOWNLOAD_DIR, filename), "wb") as f:
                                    f.write(pdf_bytes)
                                mapping = load_downloaded_mapping()
                                mapping[du] = filename
                                save_downloaded_mapping(mapping)
                                print(f"    [LOG] Downloaded file from event handler popup: {filename}")
                                download_success = True
                            else:
                                found_pdf_url = None
                                for selector in ['iframe', 'embed']:
                                    elems = popup_page.query_selector_all(selector)
                                    for elem in elems:
                                        src = elem.get_attribute('src')
                                        if src and '.pdf' in src.lower():
                                            found_pdf_url = src if src.startswith('http') else f"https://pitchbook.com{src}"
                                            break
                                    if found_pdf_url:
                                        break
                                if not found_pdf_url:
                                    for a in popup_page.query_selector_all('a'):
                                        href = a.get_attribute('href')
                                        if href and '.pdf' in href.lower():
                                            found_pdf_url = href if href.startswith('http') else f"https://pitchbook.com{href}"
                                            break
                                if found_pdf_url:
                                    pdf_bytes = page2.context.request.get(found_pdf_url).body()
                                    filename = os.path.basename(found_pdf_url.split("?")[0])
                                    with open(os.path.join(DOWNLOAD_DIR, filename), "wb") as f:
                                        f.write(pdf_bytes)
                                    mapping = load_downloaded_mapping()
                                    mapping[du] = filename
                                    save_downloaded_mapping(mapping)
                                    print(f"    [LOG] Downloaded file from event handler popup viewer: {filename}")
                                    download_success = True
                                else:
                                    debug_ts = int(time.time())
                                    popup_page.screenshot(path=f"popup_event_no_pdf_{debug_ts}.png")
                                    with open(f"popup_event_no_pdf_{debug_ts}.html", "w") as f:
                                        f.write(popup_page.content())
                                    print(f"    [DEBUG] No PDF found in event handler popup, saved screenshot and HTML for debugging.")
                                popup_page.close()
                        except Exception as e:
                            print(f"    [DEBUG] Error handling event handler popup: {e}")
                    # Fallback: wait 10s if no download detected
                    if not download_success:
                        print("    [LOG] No download or popup detected, waiting 10s as fallback...")
                        page2.wait_for_timeout(5000)
                    # If still no download, take screenshot and HTML of the current page for debugging
                    if not download_success:
                        debug_ts = int(time.time())
                        page2.screenshot(path=f"after_download_click_{debug_ts}.png")
                        with open(f"after_download_click_{debug_ts}.html", "w") as f:
                            f.write(page2.content())
                        print("    [DEBUG] Saved screenshot and HTML after clicking Download PDF.")
                    if not download_success:
                        print("    [LOG] No download detected for this report after all attempts.")
                    page2.close()
                except Exception as e:
                    print(f"⚠️ Error processing {du}: {e}")
        else:
            # For the next 3 listings, repeatedly click 'Load more' and process new reports
            processed = set()
            seen = set()
            total_detail_urls = []
            while len(total_detail_urls) < 100:
                # Always get all links currently visible
                links = page.query_selector_all("a[href^='/news/reports/']")
                new_detail_urls = []
                for a in links:
                    href = a.get_attribute('href')
                    if href and href != '/news/reports':
                        full = f"https://pitchbook.com{href}"
                        if full not in seen:
                            seen.add(full)
                            new_detail_urls.append(full)
                # Add only new ones to the total list
                for url in new_detail_urls:
                    if url not in total_detail_urls:
                        total_detail_urls.append(url)
                print(f"[LOG] {len(total_detail_urls)} unique report links collected so far...")
                # Process only the new ones
                for du in new_detail_urls:
                    if du in mapping or du in processed:
                        print(f"✓ Already processed: {du} -> {mapping.get(du, '')}")
                        continue
                    print(f"→ Processing: {du}")
                    try:
                        page2 = page.context.new_page()
                        page2.goto(du, timeout=60000, wait_until="domcontentloaded")
                        print(f"  [LOG] Opened detail page: {du}")
                        # Dismiss cookies modals
                        for sel in [
                            "button:has-text('Accept All Cookies')",
                            "button:has-text('Reject All')",
                            "button[aria-label='Close']",
                            "button.ot-pc-refuse-all-handler",
                            "button.save-preference-btn-handler"
                        ]:
                            try:
                                page2.click(sel, timeout=2000, force=True)
                                page2.wait_for_timeout(500)
                            except:
                                continue
                        # Try direct PDF
                        pdf_link = None
                        for a in page2.query_selector_all("a"): 
                            href = a.get_attribute('href')
                            if href and href.lower().endswith('.pdf'):
                                pdf_link = href if href.startswith('http') else f"https://pitchbook.com{href}"
                                break
                        if pdf_link:
                            print(f"  [LOG] Found direct PDF link: {pdf_link}")
                            _fetch_and_save(page2, pdf_link, detail_url=du)
                            page2.close()
                            continue
                        # Fill form and download via Playwright download event
                        print("  [LOG] No direct PDF, using form workflow...")
                        page2.wait_for_selector("input[name='FirstName']", timeout=5000)
                        page2.fill("input[name='FirstName']", "Aza")
                        page2.fill("input[name='LastName']", "Kan")
                        page2.fill("input[name='Email']", "ak.somnium@gmail.com")
                        # Check agreement checkbox if present (robust)
                        checkbox_selectors = [
                            "input[type='checkbox'][name='agree']",
                            "label:has(input[type='checkbox'][name='agree'])",
                            ".custom-checkbox__icon"
                        ]
                        checked = False
                        for sel in checkbox_selectors:
                            try:
                                el = page2.query_selector(sel)
                                if el:
                                    el.scroll_into_view_if_needed()
                                    page2.wait_for_timeout(200)
                                    # Log bounding box and visibility
                                    bbox = el.bounding_box() if hasattr(el, 'bounding_box') else None
                                    is_visible = el.is_visible() if hasattr(el, 'is_visible') else None
                                    print(f"    [DEBUG] Checkbox selector: {sel}, bbox: {bbox}, is_visible: {is_visible}")
                                    try:
                                        el.click(force=True)
                                        print(f"    [LOG] Checked agreement checkbox using selector: {sel} (Playwright .click())")
                                        checked = True
                                        break
                                    except Exception as e:
                                        print(f"    [LOG] Playwright .click() failed for checkbox: {e}, trying JS click...")
                                        try:
                                            page2.evaluate('(el) => el.click()', el)
                                            print(f"    [LOG] Checked agreement checkbox using selector: {sel} (JS click)")
                                            checked = True
                                            break
                                        except Exception as e2:
                                            print(f"    [LOG] JS click also failed for checkbox: {e2}")
                                            # Take a screenshot for debugging
                                            sanitized_sel = sel.replace('[','').replace(']','').replace('=','_').replace('"','').replace("'",'')
                                            screenshot_path = f"checkbox_click_error_{sanitized_sel}.png"
                                            page2.screenshot(path=screenshot_path)
                                            print(f"    [DEBUG] Screenshot saved to {screenshot_path}")
                            except Exception as e:
                                print(f"    [LOG] Could not check agreement checkbox with selector {sel}: {e}")
                        if not checked:
                            print("⚠️ Could not check the agreement checkbox. Printing form HTML for debugging:")
                            try:
                                form = page2.query_selector('form')
                                if form:
                                    print(form.inner_html())
                                else:
                                    print(page2.content())
                            except Exception as e:
                                print(f"    [LOG] Could not print form HTML: {e}")
                        # Wait for submit button to become enabled
                        submit_btn = page2.wait_for_selector("input[type='submit'][value='Download report']:not([disabled]), input[type='submit'][value='Download']:not([disabled])", timeout=5000)
                        # Trigger form submission
                        submit_btn.click(force=True)
                        page2.wait_for_timeout(3000)  # Wait 3 seconds after submit for UI to update
                        # After 3 seconds, search for Download PDF or Download button and click it
                        # Try to directly extract the PDF link and download
                        a_tag = page2.query_selector("a.report__download-btn[href$='.pdf']")
                        if a_tag:
                            pdf_url = a_tag.get_attribute('href')
                            if pdf_url and not pdf_url.startswith('http'):
                                pdf_url = f'https://pitchbook.com{pdf_url}'
                            try:
                                pdf_bytes = page2.context.request.get(pdf_url).body()
                                filename = os.path.basename(pdf_url.split('?')[0])
                                with open(os.path.join(DOWNLOAD_DIR, filename), 'wb') as f:
                                    f.write(pdf_bytes)
                                mapping = load_downloaded_mapping()
                                mapping[du] = filename
                                save_downloaded_mapping(mapping)
                                print(f'    [LOG] Downloaded PDF directly from link: {filename}')
                                page2.close()
                                continue
                            except Exception as e:
                                print(f'    [WARN] Failed to download PDF directly from link: {e}')
                        # Fill optional questionnaire if present before clicking Download PDF
                        # Check 'Raising capital' if present
                        try:
                            labels = page2.query_selector_all("label")
                            for label in labels:
                                text = label.inner_text().strip()
                                if "Raising capital" in text:
                                    cb = label.query_selector("input[type='checkbox']")
                                    if cb and not cb.is_checked():
                                        cb.check()
                                        print("    [LOG] Checked 'Raising capital' optional checkbox.")
                                    break
                        except Exception as e:
                            print(f"    [LOG] Could not check 'Raising capital' checkbox: {e}")
                        # Select first available Job Role if present
                        try:
                            select = page2.query_selector("select")
                            if select:
                                options = select.query_selector_all("option")
                                for opt in options:
                                    value = opt.get_attribute('value')
                                    if value and value != '' and value.lower() != 'select one':
                                        select.select_option(value)
                                        print(f"    [LOG] Selected first Job Role option: {value}")
                                        break
                        except Exception as e:
                            print(f"    [LOG] Could not select Job Role: {e}")
                        # Robust click logic for Download PDF/Download button/link
                        print("    [LOG] Attempting to click Download PDF/Download button/link...")
                        # Take screenshot before click
                        debug_ts = int(time.time())
                        page2.screenshot(path=f"before_download_pdf_click_{debug_ts}.png")
                        print("    [DEBUG] Screenshot before clicking Download PDF.")
                        clicked = False
                        # Fill optional questionnaire if present before clicking Download PDF
                        # Check 'Raising capital' if present
                        try:
                            labels = page2.query_selector_all("label")
                            for label in labels:
                                text = label.inner_text().strip()
                                if "Raising capital" in text:
                                    cb = label.query_selector("input[type='checkbox']")
                                    if cb and not cb.is_checked():
                                        cb.check()
                                        print("    [LOG] Checked 'Raising capital' optional checkbox.")
                                    break
                        except Exception as e:
                            print(f"    [LOG] Could not check 'Raising capital' checkbox: {e}")
                        # Select first available Job Role if present
                        try:
                            select = page2.query_selector("select")
                            if select:
                                options = select.query_selector_all("option")
                                for opt in options:
                                    value = opt.get_attribute('value')
                                    if value and value != '' and value.lower() != 'select one':
                                        select.select_option(value)
                                        print(f"    [LOG] Selected first Job Role option: {value}")
                                        break
                        except Exception as e:
                            print(f"    [LOG] Could not select Job Role: {e}")
                        if not pdf_link:
                            page2.close()
                            continue
                        # Robust click logic for Download PDF/Download button/link
                        print("    [LOG] Attempting to click Download PDF/Download button/link...")
                        # Take screenshot before click
                        debug_ts = int(time.time())
                        page2.screenshot(path=f"before_download_pdf_click_{debug_ts}.png")
                        print("    [DEBUG] Screenshot before clicking Download PDF.")
                        clicked = False
                        if pdf_link:
                            is_visible = pdf_link.is_visible()
                            is_enabled = not pdf_link.is_disabled()
                            box = pdf_link.bounding_box()
                            print(f"    [DEBUG] Download PDF button: visible={is_visible}, enabled={is_enabled}, bbox={box}")
                            if is_visible and is_enabled and box:
                                try:
                                    pdf_link.scroll_into_view_if_needed()
                                    page2.wait_for_timeout(200)
                                    pdf_link.click(force=True)
                                    print("    [LOG] Clicked using Playwright .click()")
                                    clicked = True
                                except Exception as e:
                                    print(f"    [LOG] Playwright .click() failed: {e}, trying JS click...")
                                    try:
                                        page2.evaluate('(el) => el.click()', pdf_link)
                                        print("    [LOG] Clicked using JS .click()")
                                        clicked = True
                                    except Exception as e2:
                                        print(f"    [LOG] JS .click() also failed: {e2}")
                        else:
                            print("    [WARN] Download PDF button is not interactable. Skipping click.")
                        # Take screenshot after click
                        page2.wait_for_timeout(1000)
                        page2.screenshot(path=f"after_download_pdf_click_{debug_ts}.png")
                        print("    [DEBUG] Screenshot after clicking Download PDF.")
                        if not clicked:
                            page2.close()
                            continue
                        # Handle new tab or download event, wait up to 30s, fallback wait if needed
                        download_success = False
                        popup_page = None
                        # Add handler to catch any new pages opened in the context
                        def on_new_page(new_page):
                            nonlocal popup_page
                            popup_page = new_page
                        page2.context.on('page', on_new_page)
                        try:
                            with page2.context.expect_page(timeout=5000) as popup_info:
                                pass  # The click has already been performed
                            try:
                                popup = popup_info.value
                                popup.wait_for_load_state("load", timeout=5000)
                                pdf_url = popup.url
                                if pdf_url.lower().endswith('.pdf'):
                                    pdf_bytes = page2.context.request.get(pdf_url).body()
                                    filename = os.path.basename(pdf_url.split("?")[0])
                                    with open(os.path.join(DOWNLOAD_DIR, filename), "wb") as f:
                                        f.write(pdf_bytes)
                                    mapping = load_downloaded_mapping()
                                    mapping[du] = filename
                                    save_downloaded_mapping(mapping)
                                    print(f"    [LOG] Downloaded file from popup: {filename}")
                                    download_success = True
                                else:
                                    # Try to find PDF URL in iframe, embed, or <a> in popup
                                    found_pdf_url = None
                                    # Check for iframe or embed
                                    for selector in ['iframe', 'embed']:
                                        elems = popup.query_selector_all(selector)
                                        for elem in elems:
                                            src = elem.get_attribute('src')
                                            if src and '.pdf' in src.lower():
                                                found_pdf_url = src if src.startswith('http') else f"https://pitchbook.com{src}"
                                                break
                                        if found_pdf_url:
                                            break
                                    # Check for <a> with .pdf in href
                                    if not found_pdf_url:
                                        for a in popup.query_selector_all('a'):
                                            href = a.get_attribute('href')
                                            if href and '.pdf' in href.lower():
                                                found_pdf_url = href if href.startswith('http') else f"https://pitchbook.com{href}"
                                                break
                                    if found_pdf_url:
                                        pdf_bytes = page2.context.request.get(found_pdf_url).body()
                                        filename = os.path.basename(found_pdf_url.split("?")[0])
                                        with open(os.path.join(DOWNLOAD_DIR, filename), "wb") as f:
                                            f.write(pdf_bytes)
                                        mapping = load_downloaded_mapping()
                                        mapping[du] = filename
                                        save_downloaded_mapping(mapping)
                                        print(f"    [LOG] Downloaded file from popup viewer: {filename}")
                                        download_success = True
                                    else:
                                        # Save screenshot and HTML for debugging
                                        debug_ts = int(time.time())
                                        popup.screenshot(path=f"popup_no_pdf_{debug_ts}.png")
                                        with open(f"popup_no_pdf_{debug_ts}.html", "w") as f:
                                            f.write(popup.content())
                                        print(f"    [DEBUG] No PDF found in popup, saved screenshot and HTML for debugging.")
                                popup.close()
                            except Exception:
                                with page2.expect_download(timeout=5000) as download_info:
                                    pass  # The click has already been performed
                                download = download_info.value
                                path = download.path()
                                filename = download.suggested_filename or os.path.basename(path)
                                target = os.path.join(DOWNLOAD_DIR, filename)
                                download.save_as(target)
                                mapping = load_downloaded_mapping()
                                mapping[du] = filename
                                save_downloaded_mapping(mapping)
                                print(f"    [LOG] Downloaded file: {filename}")
                                download_success = True
                        except Exception:
                            pass
                        # If no download or popup detected, check if a new page was opened via the event handler
                        if not download_success and popup_page:
                            try:
                                popup_page.wait_for_load_state("load", timeout=5000)
                                pdf_url = popup_page.url
                                if pdf_url.lower().endswith('.pdf'):
                                    pdf_bytes = page2.context.request.get(pdf_url).body()
                                    filename = os.path.basename(pdf_url.split("?")[0])
                                    with open(os.path.join(DOWNLOAD_DIR, filename), "wb") as f:
                                        f.write(pdf_bytes)
                                    mapping = load_downloaded_mapping()
                                    mapping[du] = filename
                                    save_downloaded_mapping(mapping)
                                    print(f"    [LOG] Downloaded file from event handler popup: {filename}")
                                    download_success = True
                                else:
                                    found_pdf_url = None
                                    for selector in ['iframe', 'embed']:
                                        elems = popup_page.query_selector_all(selector)
                                        for elem in elems:
                                            src = elem.get_attribute('src')
                                            if src and '.pdf' in src.lower():
                                                found_pdf_url = src if src.startswith('http') else f"https://pitchbook.com{src}"
                                                break
                                        if found_pdf_url:
                                            break
                                    if not found_pdf_url:
                                        for a in popup_page.query_selector_all('a'):
                                            href = a.get_attribute('href')
                                            if href and '.pdf' in href.lower():
                                                found_pdf_url = href if href.startswith('http') else f"https://pitchbook.com{href}"
                                                break
                                    if found_pdf_url:
                                        pdf_bytes = page2.context.request.get(found_pdf_url).body()
                                        filename = os.path.basename(found_pdf_url.split("?")[0])
                                        with open(os.path.join(DOWNLOAD_DIR, filename), "wb") as f:
                                            f.write(pdf_bytes)
                                        mapping = load_downloaded_mapping()
                                        mapping[du] = filename
                                        save_downloaded_mapping(mapping)
                                        print(f"    [LOG] Downloaded file from event handler popup viewer: {filename}")
                                        download_success = True
                                    else:
                                        debug_ts = int(time.time())
                                        popup_page.screenshot(path=f"popup_event_no_pdf_{debug_ts}.png")
                                        with open(f"popup_event_no_pdf_{debug_ts}.html", "w") as f:
                                            f.write(popup_page.content())
                                        print(f"    [DEBUG] No PDF found in event handler popup, saved screenshot and HTML for debugging.")
                                    popup_page.close()
                            except Exception as e:
                                print(f"    [DEBUG] Error handling event handler popup: {e}")
                        # Fallback: wait 10s if no download detected
                        if not download_success:
                            print("    [LOG] No download or popup detected, waiting 10s as fallback...")
                            page2.wait_for_timeout(5000)
                        # If still no download, take screenshot and HTML of the current page for debugging
                        if not download_success:
                            debug_ts = int(time.time())
                            page2.screenshot(path=f"after_download_click_{debug_ts}.png")
                            with open(f"after_download_click_{debug_ts}.html", "w") as f:
                                f.write(page2.content())
                            print("    [DEBUG] Saved screenshot and HTML after clicking Download PDF.")
                        if not download_success:
                            print("    [LOG] No download detected for this report after all attempts.")
                        page2.close()
                        processed.add(du)
                    except Exception as e:
                        print(f"⚠️ Error processing {du}: {e}")
                if len(total_detail_urls) >= 100:
                    break
                # Try to click 'Load more' if available
                load_more_btn = None
                for sel in ["a:has-text('Load more')", "button:has-text('Load more')", "a.btn-primary_teal", "a:has-text('See more')"]:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible() and btn.is_enabled():
                        load_more_btn = btn
                        break
                if load_more_btn:
                    prev_total = len(total_detail_urls)
                    print("[LOG] Clicking 'Load more' to reveal more reports...")
                    try:
                        load_more_btn.click()
                    except Exception as e:
                        print(f"[WARN] Failed to click 'Load more': {e}")
                        break
                    # Poll for up to 5 seconds for new links to appear
                    found_new = False
                    for _ in range(10):
                        page.wait_for_timeout(500)
                        links_after = page.query_selector_all("a[href^='/news/reports/']")
                        new_total = len(set([a.get_attribute('href') for a in links_after if a.get_attribute('href') and a.get_attribute('href') != '/news/reports']))
                        if new_total > prev_total:
                            found_new = True
                            break
                    if not found_new:
                        print("[LOG] No new reports loaded after clicking 'Load more'. Stopping.")
                        break
                else:
                    print("[LOG] No more 'Load more' button found. Stopping.")
                    break

if __name__ == '__main__':
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        scrape_and_download_pitchbook(page)
        browser.close()