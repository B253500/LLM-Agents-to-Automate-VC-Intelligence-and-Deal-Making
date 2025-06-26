# download_reports.py - Playwright script for Crunchbase, Beauhurst & PitchBook
# Requirements:
#   python >=3.7
#   pip install playwright
#   playwright install

import re
import json
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, Error as PlaywrightError
import imaplib
import email
from email.header import decode_header
import time
import requests
from fpdf import FPDF
import glob
import random
import string

# Download directory
DOWNLOAD_DIR = Path(__file__).parent / "data" / "vc_reports"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Timeouts (ms)
NAV_TIMEOUT = 60000
DOWNLOAD_TIMEOUT = 120000

# --- CONFIGURATION FOR EMAIL DOWNLOAD ---
GMAIL_USER = "ak.somnium@gmail.com"
GMAIL_PASSWORD = "YOUR_APP_PASSWORD_HERE"  # Use an App Password if 2FA is enabled
BEAUHURST_EMAIL_DOMAIN = "@beauhurst.com"
EMAIL_CHECK_INTERVAL = 60  # seconds

def fill_beauhurst_form(page):
    try:
        # Try to find the form by generic HubSpot selector or by specific known ID
        form_selectors = [
            "form[id^='hsForm_']",
            "#hsForm_257d39dc-7a23-4ea9-9fea-aad43090d226_1"
        ]
        form_context = None
        for selector in form_selectors:
            try:
                page.wait_for_selector(selector, timeout=10000)
                form_context = page
                break
            except Exception:
                continue
        if not form_context:
            # If not found, check for iframes
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

        # Fill visible required fields first
        first_name = form_context.query_selector("input[name='firstname']")
        last_name = form_context.query_selector("input[name='lastname']")
        email_field = form_context.query_selector("input[name='email']")
        job_title = form_context.query_selector("input[name='jobtitle']")
        industry = form_context.query_selector("select[name='demo_form_industries']")
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

        filled = False
        if first_name:
            first_name.fill("Aza")
            filled = True
        if last_name:
            last_name.fill("Kan")
            filled = True
        # Try primary email first, fallback if error message appears
        email_to_try = ["ak.somnium@gmail.com", "a.kanatuly@sms.ed.ac.uk"]
        email_filled = False
        for email in email_to_try:
            if email_field:
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
        if job_title:
            job_title.fill("student")
            filled = True
        # --- Handle forms where industry and other fields are hidden until others are filled ---
        # Wait for industry select to appear if it was hidden
        if not industry:
            try:
                page.wait_for_selector("select[name='demo_form_industries']", timeout=3000)
                industry = form_context.query_selector("select[name='demo_form_industries']")
            except Exception:
                pass
        if industry:
            options = industry.query_selector_all('option')
            selected = False
            for opt in options:
                value = opt.get_attribute('value')
                text = opt.inner_text().lower() if opt.inner_text() else ''
                if value and (('student' in value.lower()) or ('university' in value.lower()) or ('student' in text) or ('university' in text)):
                    industry.select_option(value)
                    selected = True
                    filled = True
                    break
            if not selected and options:
                random_opt = random.choice(options)
                value = random_opt.get_attribute('value')
                if value:
                    industry.select_option(value)
                    filled = True
        # --- Fill any other visible input or select fields randomly ---
        all_inputs = form_context.query_selector_all("input[type='text']")
        for inp in all_inputs:
            name = inp.get_attribute('name')
            if name not in ['firstname', 'lastname', 'email', 'jobtitle']:
                try:
                    rand_val = ''.join(random.choices(string.ascii_letters, k=8))
                    inp.fill(rand_val)
                    filled = True
                except Exception:
                    continue
        all_selects = form_context.query_selector_all("select")
        for sel in all_selects:
            name = sel.get_attribute('name')
            if name != 'demo_form_industries':
                try:
                    options = sel.query_selector_all('option')
                    valid_options = [opt for opt in options if opt.get_attribute('value')]
                    if valid_options:
                        random_opt = random.choice(valid_options)
                        value = random_opt.get_attribute('value')
                        sel.select_option(value)
                        filled = True
                except Exception:
                    continue
        # --- Check and tick any visible checkboxes (e.g. marketing consent) ---
        checkboxes = form_context.query_selector_all("input[type='checkbox']")
        for cb in checkboxes:
            try:
                label = None
                cb_id = cb.get_attribute('id')
                if cb_id:
                    label_elem = form_context.query_selector(f"label[for='{cb_id}']")
                    if label_elem:
                        label = label_elem.inner_text().strip().lower()
                if not label:
                    parent_label = cb.evaluate("el => el.closest('label') && el.closest('label').innerText")
                    if parent_label:
                        label = parent_label.strip().lower()
                if label and (re.search(r'marketing|event|seminar|newsletter|receive', label) or 'i would like' in label or 'consent' in label or 'agree' in label):
                    if not cb.is_checked():
                        cb.check()
                        print(f"Checked marketing/consent checkbox: {label}")
                elif cb.get_attribute('required') or cb.get_attribute('aria-required') == 'true':
                    if not cb.is_checked():
                        cb.check()
                        print(f"Checked required checkbox: {label}")
            except Exception as e:
                print(f"Could not check a checkbox: {e}")
                continue
        if filled and submit_btn:
            print("Submitting Beauhurst report request form...")
            submit_btn.click()
            # --- Wait for paywall to disappear or .second_part to become visible ---
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

# --- EMAIL DOWNLOAD LOGIC ---
def download_beauhurst_pdfs_from_gmail(download_dir, since=None):
    """Connect to Gmail, find new Beauhurst emails, and download PDF attachments."""
    print("Checking Gmail for new Beauhurst report emails...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select("inbox")
        # Search for emails from Beauhurst
        status, messages = mail.search(None, f'FROM "{BEAUHURST_EMAIL_DOMAIN}"')
        if status != "OK":
            print("No Beauhurst emails found.")
            return
        for num in messages[0].split():
            status, msg_data = mail.fetch(num, '(RFC822)')
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            # Only process emails since a certain date if provided
            if since:
                date_tuple = email.utils.parsedate_tz(msg["Date"])
                if date_tuple:
                    msg_time = email.utils.mktime_tz(date_tuple)
                    if msg_time < since:
                        continue
            # Download PDF attachments
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                filename = part.get_filename()
                if filename and filename.lower().endswith('.pdf'):
                    filepath = download_dir / filename
                    if not filepath.exists():
                        print(f"↓ Downloading PDF attachment: {filename}")
                        with open(filepath, 'wb') as f:
                            f.write(part.get_payload(decode=True))
        mail.logout()
    except Exception as e:
        print(f"⚠️ Error downloading PDFs from Gmail: {e}")

def extract_report_info(page, source):
    """Extract key information from a report page based on the source."""
    info = {
        'url': page.url,
        'title': '',
        'description': '',
        'date': '',
        'content': [],
        'extracted_date': datetime.now().isoformat()
    }
    
    try:
        print(f"\nExtracting information from {info['url']}")
        
        if source == "Crunchbase":
            # Crunchbase specific selectors
            title_elem = (
                page.query_selector('.article-title') or 
                page.query_selector('h1') or
                page.query_selector('.report-title')
            )
            if title_elem:
                info['title'] = title_elem.inner_text().strip()
                print(f"Found title: {info['title']}")
            
            desc_elem = (
                page.query_selector('.article-description') or 
                page.query_selector('meta[name="description"]') or
                page.query_selector('.report-summary') or
                page.query_selector('.intro-text')
            )
            if desc_elem:
                if hasattr(desc_elem, 'inner_text'):
                    info['description'] = desc_elem.inner_text().strip()
                elif desc_elem.get_attribute('content'):
                    info['description'] = desc_elem.get_attribute('content').strip()
                print(f"Found description: {info['description'][:100]}...")
            
            # Try multiple content selectors
            content_selectors = [
                '.article-content',
                '.report-content',
                '.main-content',
                'article',
                '.content-area'
            ]
            
            for selector in content_selectors:
                content_elem = page.query_selector(selector)
                if content_elem:
                    # Try to get text from paragraphs first
                    paragraphs = content_elem.query_selector_all('p')
                    for p in paragraphs:
                        if p and p.inner_text():
                            text = p.inner_text().strip()
                            if text:
                                info['content'].append(text)
                    
                    # If no paragraphs, try to get text from list items
                    if not info['content']:
                        items = content_elem.query_selector_all('li')
                        for item in items:
                            if item and item.inner_text():
                                text = item.inner_text().strip()
                                if text:
                                    info['content'].append(text)
                    
                    # If still no content, try direct text
                    if not info['content']:
                        text = content_elem.inner_text().strip()
                        if text:
                            info['content'] = [text]
                    
                    if info['content']:
                        print(f"Found content using selector '{selector}': {len(info['content'])} paragraphs")
                        break
            
        elif source == "Beauhurst":
            # Beauhurst specific selectors
            title_elem = (
                page.query_selector('h1.research-title') or 
                page.query_selector('h1') or
                page.query_selector('.page-title')
            )
            if title_elem:
                info['title'] = title_elem.inner_text().strip()
                print(f"Found title: {info['title']}")
            
            desc_elem = (
                page.query_selector('.research-description') or
                page.query_selector('.research-summary') or
                page.query_selector('meta[name="description"]') or
                page.query_selector('.intro-text')
            )
            if desc_elem:
                if hasattr(desc_elem, 'inner_text'):
                    info['description'] = desc_elem.inner_text().strip()
                elif desc_elem.get_attribute('content'):
                    info['description'] = desc_elem.get_attribute('content').strip()
                print(f"Found description: {info['description'][:100]}...")
            
            # Try multiple content areas
            content_selectors = [
                '.research-content',
                '.key-findings',
                '.report-highlights',
                '.main-content',
                'article',
                '.content-area',
                '.post-content'
            ]
            
            for selector in content_selectors:
                content = page.query_selector(selector)
                if content:
                    # Try paragraphs first
                    elements = content.query_selector_all('p')
                    for elem in elements:
                        if elem and elem.inner_text():
                            text = elem.inner_text().strip()
                            if text:
                                info['content'].append(text)
                    
                    # Then try list items
                    if not info['content']:
                        elements = content.query_selector_all('li')
                        for elem in elements:
                            if elem and elem.inner_text():
                                text = elem.inner_text().strip()
                                if text:
                                    info['content'].append(text)
                    
                    # If still no content, try direct text
                    if not info['content']:
                        text = content.inner_text().strip()
                        if text:
                            info['content'] = [text]
                    
                    if info['content']:
                        print(f"Found content using selector '{selector}': {len(info['content'])} paragraphs")
                        break
            
        elif source == "PitchBook":
            # PitchBook specific selectors
            title_elem = (
                page.query_selector('.report-title') or 
                page.query_selector('h1') or
                page.query_selector('.article-title')
            )
            if title_elem:
                info['title'] = title_elem.inner_text().strip()
                print(f"Found title: {info['title']}")
            
            desc_elem = (
                page.query_selector('.report-description') or
                page.query_selector('.report-summary') or
                page.query_selector('meta[name="description"]') or
                page.query_selector('.intro-text')
            )
            if desc_elem:
                if hasattr(desc_elem, 'inner_text'):
                    info['description'] = desc_elem.inner_text().strip()
                elif desc_elem.get_attribute('content'):
                    info['description'] = desc_elem.get_attribute('content').strip()
                print(f"Found description: {info['description'][:100]}...")
            
            # Try multiple content areas
            content_selectors = [
                '.report-content',
                '.key-insights',
                '.report-preview',
                '.article-content',
                '.main-content',
                'article',
                '.content-area'
            ]
            
            for selector in content_selectors:
                content = page.query_selector(selector)
                if content:
                    # Try paragraphs first
                    elements = content.query_selector_all('p')
                    for elem in elements:
                        if elem and elem.inner_text():
                            text = elem.inner_text().strip()
                            if text:
                                info['content'].append(text)
                    
                    # Then try list items
                    if not info['content']:
                        elements = content.query_selector_all('li')
                        for elem in elements:
                            if elem and elem.inner_text():
                                text = elem.inner_text().strip()
                                if text:
                                    info['content'].append(text)
                    
                    # If still no content, try direct text
                    if not info['content']:
                        text = content.inner_text().strip()
                        if text:
                            info['content'] = [text]
                    
                    if info['content']:
                        print(f"Found content using selector '{selector}': {len(info['content'])} paragraphs")
                        break
            
            # Try to get publication date
            date_elem = (
                page.query_selector('.report-date') or
                page.query_selector('time') or
                page.query_selector('.date')
            )
            if date_elem:
                info['date'] = date_elem.inner_text().strip()
                print(f"Found date: {info['date']}")
        
        # If we got no content but have description, use it as content
        if not info['content'] and info['description']:
            info['content'] = [info['description']]
            print("Using description as content")
            
        # If we still have no title, try to extract from URL
        if not info['title']:
            path_parts = page.url.rstrip('/').split('/')
            if path_parts:
                title_candidate = path_parts[-1]
                info['title'] = title_candidate.replace('-', ' ').title()
                print(f"Generated title from URL: {info['title']}")
        
        # Try to get any text if we still have no content
        if not info['content']:
            print("No content found with standard selectors, trying fallback methods...")
            
            # Try to get text from any visible paragraph
            all_paragraphs = page.query_selector_all('p')
            for p in all_paragraphs:
                if p and p.is_visible() and p.inner_text():
                    text = p.inner_text().strip()
                    if text and len(text) > 50:  # Only include substantial paragraphs
                        info['content'].append(text)
            
            if info['content']:
                print(f"Found {len(info['content'])} paragraphs using fallback method")
            else:
                print("No content found even with fallback method")
        
        return info
        
    except Exception as e:
        print(f"⚠️ Error extracting information: {e}")
        return info

def save_report_info(info, source):
    """Save report information to JSON file."""
    if not info.get('title') and not info.get('content'):
        print(f"⚠️ No meaningful information found to save from {info.get('url', 'unknown URL')}")
        return False
        
    # Create a filename from the title or URL
    if info.get('title'):
        filename = re.sub(r'[^\w\s-]', '', info['title'])
        filename = re.sub(r'[-\s]+', '-', filename).strip('-').lower()
    else:
        filename = re.sub(r'[^\w]', '-', info.get('url', '').split('/')[-1])
    
    # Save to appropriate JSON file
    json_file = Path(__file__).parent / "data" / f"{source.lower()}_downloaded.json"
    
    try:
        # Load existing data
        data = {'reports': []}
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict) or 'reports' not in data:
                    data = {'reports': []}
            except (json.JSONDecodeError, TypeError):
                # If file is corrupted, start fresh
                pass
        
        # Check if report already exists
        exists = False
        if isinstance(data.get('reports'), list):
            for report in data['reports']:
                if isinstance(report, dict) and report.get('url') == info.get('url'):
                    exists = True
                    break
        
        # Add new report info if not already present
        if not exists:
            data['reports'].append(info)
            
            # Save updated data
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"📝 Saved report information: {info.get('title', 'Untitled')}")
            return True
            
    except Exception as e:
        print(f"⚠️ Error saving report information: {e}")
        return False
    
    return False

def save_webpage_as_pdf(page, download_dir, report_title):
    # Clean the report title for filename
    safe_title = re.sub(r'[^\w\s-]', '', report_title)
    safe_title = re.sub(r'[-\s]+', '_', safe_title).strip('_').lower()
    pdf_path = download_dir / f"{safe_title}.pdf"
    # Optionally, set viewport size for better layout
    page.set_viewport_size({"width": 1280, "height": 1800})
    # Scroll through the page in increments to trigger lazy loading
    scroll_steps = 10
    for i in range(scroll_steps + 1):
        page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {i / scroll_steps})")
        page.wait_for_timeout(400)
    # Wait for SVG, canvas, or chart elements to appear (if any)
    try:
        page.wait_for_selector("svg, canvas, .chart, .highcharts-container", timeout=5000)
    except Exception:
        pass  # If not found, continue anyway
    # Wait a bit more for all images/charts to load
    page.wait_for_timeout(2000)
    # Save as PDF
    page.pdf(path=str(pdf_path), format="A4", print_background=True)
    print(f"Saved webpage as PDF: {pdf_path}")

def already_have_report(report_title, download_dir):
    safe_title = report_title.replace(' ', '_').replace('/', '_')
    for file in download_dir.glob(f"*{safe_title}*.pdf"):
        if file.exists():
            return True
    return False

def find_visible_form(page):
    # Check main page
    form = page.query_selector("form")
    if form and form.is_visible():
        return page  # Use page as context if form is on main page
    # Check iframes
    for iframe in page.query_selector_all("iframe"):
        try:
            frame = iframe.content_frame()
            if frame:
                form = frame.query_selector("form")
                if form and form.is_visible():
                    return frame  # Use frame as context if form is in iframe
        except Exception:
            continue
    return None

def fill_login_form(form_context):
    # Accept cookies
    try:
        cookie_btn = (
            form_context.query_selector("button:has-text('Accept')") or
            form_context.query_selector("button:has-text('I agree')") or
            form_context.query_selector("button:has-text('Agree')") or
            form_context.query_selector("button:has-text('Got it')") or
            form_context.query_selector("button:has-text('Allow all')") or
            form_context.query_selector("button:has-text('OK')") or
            form_context.query_selector("[id*='cookie'][type='button']")
        )
        if cookie_btn and cookie_btn.is_visible() and cookie_btn.is_enabled():
            print("Clicking cookie consent button...")
            cookie_btn.click()
            form_context.wait_for_timeout(1000)
    except Exception:
        pass

    # Fill form fields
    def random_str(n=5):
        return ''.join(random.choices(string.ascii_letters, k=n))

    fields = {
        "FirstName": "Aza",
        "LastName": "Kan",
        "Email": "ak@somnium@gmail.com",
        "JobTitle": "student",
        "Industry": "university"
    }
    filled_any = False
    for name, value in fields.items():
        try:
            selector = f"input[name='{name}'], select[name='{name}']"
            el = form_context.query_selector(selector)
            if el:
                el.fill(value)
                filled_any = True
            else:
                # Try to fill with random if not found
                for inp in form_context.query_selector_all("input[type='text'], select"):
                    try:
                        inp.fill(random_str())
                        filled_any = True
                    except Exception:
                        continue
        except Exception:
            continue

    # Tick acceptance checkbox if present
    checkbox = form_context.query_selector("input[type='checkbox']")
    if checkbox:
        try:
            checkbox.check()
            filled_any = True
        except Exception:
            try:
                label = checkbox.evaluate_handle('el => el.closest("label")')
                if label:
                    label.click()
                    filled_any = True
            except Exception:
                pass
    return filled_any

def accept_cookies(page):
    """Try to accept cookies on the page if a consent button is present."""
    cookie_selectors = [
        "button:has-text('Accept')",
        "button:has-text('I agree')",
        "button:has-text('Agree')",
        "button:has-text('Got it')",
        "button:has-text('Allow all')",
        "button:has-text('OK')",
        "button:has-text('Accept All')",
        "button:has-text('Accept all cookies')",
        "button[aria-label*='accept']",
        "button[title*='accept']",
        "[id*='cookie'][type='button']",
        "#onetrust-accept-btn-handler",
        ".cookie-accept, .cc-accept, .cookies-accept, .accept-cookies"
    ]
    # Wait for up to 5 seconds for any cookie button to appear
    for _ in range(5):
        for selector in cookie_selectors:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible() and btn.is_enabled():
                    print(f"Clicking cookie consent button for selector: {selector}")
                    btn.click()
                    page.wait_for_timeout(1000)
                    # Try again in case there are multiple banners
            except Exception:
                continue
        page.wait_for_timeout(1000)
    return True

def fill_pitchbook_form_and_download(page):
    accept_cookies(page)
    try:
        page.wait_for_selector("form#reportDownloadForm", timeout=7000)
    except Exception:
        print("No PitchBook download form found.")
        return False

    # Fill only required fields
    page.fill("input[name='FirstName']", "Aza")
    page.fill("input[name='LastName']", "Kan")
    page.fill("input[name='Email']", "ak.somnium@gmail.com")

    # Wait for the agreement checkbox to be enabled and visible
    try:
        page.wait_for_selector("input[name='agree']:not([disabled])", timeout=2000)
        page.check("input[name='agree']")
    except Exception:
        try:
            page.click("label[for='agree']")
        except Exception:
            print("Could not check agreement box.")

    # Trigger form validation by blurring the last input
    try:
        page.locator("input[name='Email']").evaluate("el => el.blur()")
        page.wait_for_timeout(500)
    except Exception:
        pass

    # Submit the form
    try:
        page.click("input[type='submit']")
        page.wait_for_timeout(2000)
    except Exception:
        print("Form submission did not trigger navigation, continuing...")

    # Wait for the 'Download report' button to become visible and enabled
    try:
        page.wait_for_selector("a.report__btn:has-text('Download report'):not([disabled])", timeout=7000, state='visible')
        download_btn = page.query_selector("a.report__btn:has-text('Download report')")
        if download_btn and download_btn.is_visible():
            download_btn.click()
            page.wait_for_timeout(1000)
        else:
            print("Download report button not found or not visible.")
            return False
    except Exception as e:
        print(f"Failed to find/click Download report button: {e}")
        return False

    # Now look for the actual PDF download button
    try:
        pdf_btn = page.query_selector("a[href$='.pdf'], a:has-text('Download PDF'), button:has-text('Download PDF')")
        if pdf_btn and pdf_btn.is_visible():
            href = pdf_btn.get_attribute('href')
            if href and href.lower().endswith('.pdf'):
                _fetch_and_save(page, href)
                print("Downloaded PitchBook PDF via href.")
                return True
            else:
                with page.expect_download(timeout=DOWNLOAD_TIMEOUT) as dl:
                    pdf_btn.click()
                download = dl.value
                fname = download.suggested_filename or "pitchbook_report.pdf"
                target = DOWNLOAD_DIR / fname
                download.save_as(str(target))
                print(f"Downloaded PitchBook report: {target}")
                return True
        else:
            print("No Download PDF button found after clicking Download report.")
    except Exception as e:
        print(f"Failed to download PitchBook report: {e}")
    return False

def download_pdf_from_detail(page, detail_url):
    try:
        page.goto(detail_url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    except PlaywrightError as e:
        print(f"⚠️ Failed to load {detail_url}: {e}")
        return
    # Check if report already exists (by filename)
    safe_title = re.sub(r'[^0-9\w\s-]', '', detail_url.rstrip('/').split('/')[-1])
    safe_title = re.sub(r'[-\s]+', '_', safe_title).strip('_').lower()
    pdf_path = DOWNLOAD_DIR / f"{safe_title}.pdf"
    if pdf_path.exists():
        print(f"✓ Report already exists: {pdf_path.name}, skipping.")
        return
    # Skip book demo or similar pages (case-insensitive)
    if 'book-demo' in detail_url.lower() or 'book-a-demo' in detail_url.lower():
        print(f"Skipping non-report page (book demo): {detail_url}")
        return
    # PitchBook special handling
    if "pitchbook.com/news/reports/" in detail_url:
        print("Detected PitchBook report page, attempting form fill and download...")
        if fill_pitchbook_form_and_download(page):
            return
    # --- BEAUHURST/CRUNCHBASE LOGIC: Try to find a direct PDF link or Download button ---
    def try_download():
        try:
            page.wait_for_selector('a[href$=".pdf"], a:has-text("Download"), button:has-text("Download")', timeout=5000)
        except Exception:
            pass  # Continue even if not found
        # Try direct PDF link first
        link = page.query_selector('a[href$=".pdf"]')
        if link and link.is_visible():
            href = link.get_attribute('href')
            if not href.startswith('http'):
                href = page.url.rstrip('/') + href
            print(f"↓ Downloading PDF: {href}")
            _fetch_and_save(page, href)
            return True
        # Try any link or button with text "Download"
        button = page.query_selector('a:has-text("Download"), button:has-text("Download")')
        if button and button.is_visible():
            href = button.get_attribute('href')
            if href and href.lower().endswith('.pdf'):
                print(f"↓ Downloading PDF: {href}")
                _fetch_and_save(page, href)
                return True
            else:
                try:
                    with page.expect_download(timeout=DOWNLOAD_TIMEOUT) as dl:
                        button.click()
                    download = dl.value
                    fname = download.suggested_filename or "beauhurst_report.pdf"
                    target = DOWNLOAD_DIR / fname
                    download.save_as(str(target))
                    print(f"↓ Downloaded Beauhurst PDF: {target}")
                    return True
                except Exception as e:
                    print(f"⚠️ Download button click failed: {e}")
        return False

    # First attempt to download
    if try_download():
        return

    # If no download link/button, check for HubSpot form and try to fill it
    if page.query_selector("form[id^='hsForm_']") or any(
        iframe.content_frame() and iframe.content_frame().query_selector("form[id^='hsForm_']")
        for iframe in page.query_selector_all("iframe")
    ):
        print("No download link/button found, but found a form. Attempting to fill the form...")
        if fill_beauhurst_form(page):
            # Wait for possible confirmation message or content after form submission
            page.wait_for_timeout(4000)
            # Check for confirmation message
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
                return
            # Otherwise, save the now-visible page as PDF (report likely revealed on page)
            print("Form filled, report appears to be revealed on page. Saving as PDF.")
            save_webpage_as_pdf(page, DOWNLOAD_DIR, safe_title)
            return

    # If still nothing, log the HTML for debugging
    print("No download link/button or downloadable form found, saving page as PDF and logging HTML for debugging.")
    with open("debug_beauhurst_page.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    save_webpage_as_pdf(page, DOWNLOAD_DIR, safe_title)

def _fetch_and_save(page, url: str):
    """Helper: fetch PDF via HTTP and save."""
    fname = url.split('/')[-1].split('?')[0]
    target = DOWNLOAD_DIR / fname
    if target.exists():
        print(f"✓ Already have {fname}")
        return True
    print(f"↓ Downloading {fname}")
    try:
        resp = page.context.request.get(url, timeout=DOWNLOAD_TIMEOUT)
        with open(target, 'wb') as f:
            f.write(resp.body())
        return True
    except PlaywrightError:
        return False

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
        # More flexible selector, but filter by /research/ and not /author/ or /tag/
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
        page.wait_for_selector("ul.report-center__feature, ul.report-center__list", timeout=30000)
    except PlaywrightError:
        print("⚠️ Report list did not load in time")
        return

    # Scroll to load more reports
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)

    links = page.query_selector_all("a[href^='/news/reports/']")
    detail_urls = []
    for a in links:
        href = a.get_attribute('href')
        if href and href != '/news/reports':
            full = f"https://pitchbook.com{href}"
            if full not in detail_urls:
                detail_urls.append(full)

    print(f"Found {len(detail_urls)} PitchBook reports")
    for du in detail_urls:
        download_pdf_from_detail(page, du)

def main():
    with sync_playwright() as pw:
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

# --- INSTRUCTIONS FOR GMAIL SETUP ---
# To use Gmail IMAP, enable IMAP in your Gmail settings and use an App Password if 2FA is enabled.
# See: https://support.google.com/mail/answer/7126229?hl=en
