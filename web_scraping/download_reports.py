import re
import json
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from playwright_stealth import Stealth
import imaplib
import email
from email.header import decode_header
import time
import requests
from fpdf import FPDF
import glob
import random
import string
import os
from twocaptcha import TwoCaptcha
from anticaptchaofficial.recaptchav2proxyless import *
from anticaptchaofficial.hcaptchaproxyless import *

# --- CONFIGURATION FOR CAPTCHA SERVICES ---
TWOCAPTCHA_API_KEY = os.getenv("TWOCAPTCHA_API_KEY", "YOUR_2CAPTCHA_API_KEY_HERE")
ANTICAPTCHA_API_KEY = os.getenv("ANTICAPTCHA_API_KEY", "YOUR_ANTICAPTCHA_API_KEY_HERE")


# Download directory
today_str = datetime.now().strftime('%Y-%m-%d')
DOWNLOAD_DIR = Path(__file__).parent / "data" / "vc_reports" / today_str
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Timeouts (ms)
NAV_TIMEOUT = 60000
DOWNLOAD_TIMEOUT = 120000

# --- CONFIGURATION FOR EMAIL DOWNLOAD ---
GMAIL_USER = os.getenv("GMAIL_USER", "ak.somnium@gmail.com")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD", "YOUR_APP_PASSWORD_HERE")  # Use an App Password if 2FA is enabled
BEAUHURST_EMAIL_DOMAIN = "@beauhurst.com"
EMAIL_CHECK_INTERVAL = 60  # seconds

DOWNLOADED_REPORTS_FILE = "downloaded_reports.txt"
MAPPING_FILE = Path(__file__).parent / "downloaded_reports.json"

def load_downloaded_reports():
    if not os.path.exists(DOWNLOADED_REPORTS_FILE):
        return set()
    with open(DOWNLOADED_REPORTS_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_downloaded_report(report_id):
    with open(DOWNLOADED_REPORTS_FILE, "a") as f:
        f.write(report_id + "\n")

def load_downloaded_mapping():
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE, "r") as f:
            return json.load(f)
    return {}

def save_downloaded_mapping(mapping):
    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)

def fill_beauhurst_form(page):
    try:
        # Add all known form IDs for robust detection
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

        # --- Progressive reveal: fill only always-visible fields first ---
        filled = False
        # 1. First name
        first_name = form_context.query_selector("input[name='firstname']")
        if first_name and first_name.is_visible() and first_name.is_enabled():
            first_name.fill("Aza")
            filled = True
        # 2. Last name
        last_name = form_context.query_selector("input[name='lastname']")
        if last_name and last_name.is_visible() and last_name.is_enabled():
            last_name.fill("Kan")
            filled = True
        # 3. Email (try both emails)
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

        # --- Wait for hidden fields to appear after filling the above ---
        # 4. Job title
        job_title = None
        try:
            page.wait_for_selector("input[name='jobtitle']", timeout=2000, state='visible')
            job_title = form_context.query_selector("input[name='jobtitle']")
        except Exception:
            job_title = form_context.query_selector("input[name='jobtitle']")
        if job_title and job_title.is_visible() and job_title.is_enabled():
            job_title.fill("student")
            filled = True
        # 5. Industry (select)
        industry = None
        try:
            page.wait_for_selector("select[name='demo_form_industries']", timeout=2000, state='visible')
            industry = form_context.query_selector("select[name='demo_form_industries']")
        except Exception:
            industry = form_context.query_selector("select[name='demo_form_industries']")
        if industry and industry.is_visible() and industry.is_enabled():
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
        # 6. Company, phone, company_size (wait for and fill if visible)
        for field_name in ['company', 'phone', 'demo_form_company_size']:
            try:
                page.wait_for_selector(f"input[name='{field_name}'], select[name='{field_name}']", timeout=1000, state='visible')
            except Exception:
                pass
            inp = form_context.query_selector(f"input[name='{field_name}']")
            sel = form_context.query_selector(f"select[name='{field_name}']")
            if inp and inp.is_visible() and inp.is_enabled():
                rand_val = ''.join(random.choices(string.ascii_letters, k=8))
                inp.fill(rand_val)
                filled = True
            if sel and sel.is_visible() and sel.is_enabled():
                options = sel.query_selector_all('option')
                valid_options = [opt for opt in options if opt.get_attribute('value')]
                if valid_options:
                    random_opt = random.choice(valid_options)
                    value = random_opt.get_attribute('value')
                    sel.select_option(value)
                    filled = True
        # --- Fill any other visible input or select fields randomly (as before) ---
        all_inputs = form_context.query_selector_all("input[type='text']")
        for inp in all_inputs:
            name = inp.get_attribute('name')
            if name not in ['firstname', 'lastname', 'email', 'jobtitle', 'company', 'phone', 'demo_form_company_size']:
                if inp.is_visible() and inp.is_enabled():
                    try:
                        rand_val = ''.join(random.choices(string.ascii_letters, k=8))
                        inp.fill(rand_val)
                        filled = True
                    except Exception:
                        continue
        all_selects = form_context.query_selector_all("select")
        for sel in all_selects:
            name = sel.get_attribute('name')
            if name not in ['demo_form_industries', 'demo_form_company_size']:
                if sel.is_visible() and sel.is_enabled():
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
            submit_btn.click(timeout=10000)
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

def solve_captcha_if_present(page):
    """
    Detects and solves a reCAPTCHA or hCaptcha.
    Tries 2Captcha first, then falls back to Anti-Captcha.
    """
    is_2captcha_configured = TWOCAPTCHA_API_KEY != "YOUR_2CAPTCHA_API_KEY_HERE"
    is_anti_captcha_configured = ANTICAPTCHA_API_KEY != "YOUR_ANTICAPTCHA_API_KEY_HERE"

    if not is_2captcha_configured and not is_anti_captcha_configured:
        print("No captcha service is configured. Skipping captcha solving.")
        return True

    # --- Find the captcha details first ---
    site_key = None
    captcha_type = None
    
    # Check for reCAPTCHA
    recaptcha_iframe = page.query_selector('iframe[src*="api2/anchor"]')
    if recaptcha_iframe:
        site_key_match = re.search(r'k=([\w-]+)', recaptcha_iframe.get_attribute('src'))
        if site_key_match:
            site_key = site_key_match.group(1)
            captcha_type = 'recaptcha'
            print(f"reCAPTCHA detected. Site key: {site_key}")

    # Check for hCaptcha if reCAPTCHA not found
    if not captcha_type:
        hcaptcha_element = page.locator('.h-captcha')
        if hcaptcha_element.count() > 0:
            site_key = hcaptcha_element.first.get_attribute('data-sitekey')
            captcha_type = 'hcaptcha'
            print(f"hCaptcha detected. Site key: {site_key}")

    if not captcha_type:
        return True # No captcha found

    page_url = page.url

    # --- Attempt 1: 2Captcha ---
    if is_2captcha_configured:
        print("Attempting to solve with 2Captcha...")
        try:
            solver = TwoCaptcha(TWOCAPTCHA_API_KEY)
            if captcha_type == 'recaptcha':
                result = solver.recaptcha(sitekey=site_key, url=page_url)
            else: # hcaptcha
                result = solver.hcaptcha(sitekey=site_key, url=page_url)
            
            print("2Captcha solved successfully. Submitting solution...")
            if captcha_type == 'recaptcha':
                page.evaluate(f"document.getElementById('g-recaptcha-response').innerHTML = '{result['code']}';")
            else:
                page.evaluate(f"document.querySelector('[name=\"h-captcha-response\"]').innerHTML = '{result['code']}';")
                page.evaluate(f"document.querySelector('[name=\"g-recaptcha-response\"]').innerHTML = '{result['code']}';")
            return True
        except Exception as e:
            print(f"⚠️ 2Captcha failed: {e}")
            # Don't return false yet, try the fallback

    # --- Attempt 2: Anti-Captcha (Fallback) ---
    if is_anti_captcha_configured:
        print("Attempting to solve with Anti-Captcha as a fallback...")
        try:
            if captcha_type == 'recaptcha':
                solver = recaptchaV2Proxyless()
                solver.set_key(ANTICAPTCHA_API_KEY)
                solver.set_website_url(page_url)
                solver.set_website_key(site_key)
                g_response = solver.solve_and_return_solution()
                if g_response != 0:
                    print("Anti-Captcha solved successfully.")
                    page.evaluate(f'document.getElementById("g-recaptcha-response").innerHTML = "{g_response}";')
                    return True
                else:
                    print(f"Anti-Captcha task finished with error: {solver.error_code}")
            else: # hcaptcha
                solver = hcaptchaProxyless()
                solver.set_key(ANTICAPTCHA_API_KEY)
                solver.set_website_url(page_url)
                solver.set_website_key(site_key)
                g_response = solver.solve_and_return_solution()
                if g_response != 0:
                    print("Anti-Captcha solved successfully.")
                    page.evaluate(f'document.querySelector(\'[name="h-captcha-response"]\').innerHTML = "{g_response}";')
                    page.evaluate(f'document.querySelector(\'[name="g-recaptcha-response"]\').innerHTML = "{g_response}";')
                    return True
                else:
                    print(f"Anti-Captcha task finished with error: {solver.error_code}")

        except Exception as e:
            print(f"⚠️ Anti-Captcha failed: {e}")

    print("Both 2Captcha and Anti-Captcha failed or were not configured. Skipping page.")
    return False

# --- EMAIL DOWNLOAD LOGIC ---
def download_beauhurst_pdfs_from_gmail(download_dir):
    """Connect to Gmail, find unread Beauhurst report emails, and download attachments."""
    print("\n=== Checking Gmail for Beauhurst Reports ===")
    
    # Check for credentials
    if GMAIL_USER == "ak.somnium@gmail.com" or GMAIL_PASSWORD == "YOUR_APP_PASSWORD_HERE":
        print("⚠️ Gmail user/password not configured. Skipping email download.")
        print("   Please set GMAIL_USER and GMAIL_PASSWORD environment variables or update the script.")
        return

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select("inbox")

        # Search for unread emails from Beauhurst with a specific subject
        search_criteria = f'(UNSEEN FROM "{BEAUHURST_EMAIL_DOMAIN}" SUBJECT "Report download beauhurst")'
        status, messages = mail.search(None, search_criteria)
        
        if status != "OK":
            print("Could not search emails.")
            mail.logout()
            return
        
        email_ids = messages[0].split()
        if not email_ids:
            print("No new unread Beauhurst report emails found.")
            mail.logout()
            return
        
        print(f"Found {len(email_ids)} new report emails from Beauhurst.")

        for num in email_ids:
            status, msg_data = mail.fetch(num, '(RFC822)')
            if status != "OK":
                continue
            
            msg = email.message_from_bytes(msg_data[0][1])
            
            # Download PDF attachments
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
                    continue
                
                filename = part.get_filename()
                if filename and filename.lower().endswith('.pdf'):
                    filepath = download_dir / filename
                    if not filepath.exists():
                        print(f"↓ Downloading PDF attachment: {filename}")
                        with open(filepath, 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        # Mark email as read after successful download
                        mail.store(num, '+FLAGS', '\\Seen')
                        print(f"✓ Marked email for '{filename}' as read.")
                    else:
                        print(f"✓ PDF '{filename}' already exists. Marking email as read.")
                        mail.store(num, '+FLAGS', '\\Seen')

        mail.logout()
    except imaplib.IMAP4.error as e:
        print(f"⚠️ IMAP Error: {e}. Please check your Gmail credentials and ensure Less Secure App Access is enabled or use an App Password.")
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
                '.article',
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

def save_webpage_as_pdf(page, download_dir, safe_title, detail_url=None):
    safe_title = re.sub(r'[^0-9\w\s-]', '', safe_title)
    safe_title = re.sub(r'[\W\s-]+', '_', safe_title).strip('_').lower()
    pdf_path = download_dir / f"{safe_title}.pdf"
    page.set_viewport_size({"width": 1280, "height": 1800})
    scroll_steps = 10
    for i in range(scroll_steps):
        page.evaluate(f"if (document.body) {{ window.scrollTo(0, document.body.scrollHeight * {i / scroll_steps}); }}")
        page.wait_for_timeout(100)
    try:
        page.wait_for_selector("svg, canvas, .chart, .highcharts-container", timeout=5000)
    except Exception:
        pass
    page.wait_for_timeout(2000)
    page.pdf(path=str(pdf_path), format="A4", print_background=True)
    print(f"Saved webpage as PDF: {pdf_path}")
    if detail_url:
        mapping = load_downloaded_mapping()
        mapping[detail_url] = pdf_path.name
        save_downloaded_mapping(mapping)

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
    try:
        print("Filling PitchBook form: First name Aza, Last name Kan, email ak.somnium@gmail.com")
        page.fill("input[name='FirstName']", "Aza")
        page.fill("input[name='LastName']", "Kan")
        page.fill("input[name='Email']", "ak.somnium@gmail.com")
        # Check the 'I agree' checkbox if present, robustly
        agree_checkbox = page.query_selector("input[name='agree']")
        if agree_checkbox and not agree_checkbox.is_checked():
            try:
                agree_checkbox.check()
            except Exception:
                # Fallback: set checked via JS and dispatch change event
                page.evaluate("el => el.checked = true", agree_checkbox)
                page.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))", agree_checkbox)
            page.wait_for_timeout(500)
        # Find and click the Download report button
        download_btn = (
            page.query_selector(
                "input[type='submit'][value*='Download report'], "
                "button[type='submit']:has-text('Download report'), "
                "button:has-text('Download report'), "
                "a:has-text('Download report'), "
                "input[type='submit'][value*='Download'], "
                "button:has-text('Download')"
            )
        )
        if download_btn and download_btn.is_visible() and download_btn.is_enabled():
            print("Clicking Download report button...")
            download_btn.click()
            page.wait_for_timeout(2000)
        else:
            print("Could not find Download report button. Printing form HTML for debugging:")
            form_html = page.content()
            with open("debug_pitchbook_form.html", "w", encoding="utf-8") as f:
                f.write(form_html)
            return False
        # Wait for Download PDF button to appear
        try:
            page.wait_for_selector("a[href$='.pdf'], a:has-text('Download PDF'), button:has-text('Download PDF')", timeout=5000, state='visible')
        except Exception:
            print("Download PDF button did not appear in time.")
            return False
        pdf_btn = page.query_selector("a[href$='.pdf'], a:has-text('Download PDF'), button:has-text('Download PDF')")
        if pdf_btn and pdf_btn.is_visible() and pdf_btn.is_enabled():
            print("Clicking Download PDF button...")
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
            return False
    except Exception as e:
        print(f"Failed to fill PitchBook form and download: {e}")
        return False

def download_pdf_from_detail(page, detail_url):
    mapping = load_downloaded_mapping()
    # Check mapping before any page interaction
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
            # Remove stale mapping if file is missing
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
        if not solve_captcha_if_present(page):
            print(f"Skipping page due to captcha failure: {detail_url}")
            return
    except PlaywrightError as e:
        print(f"⚠️ Failed to load {detail_url}: {e}")
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
            _fetch_and_save(page, href, detail_url)
            return True
        # Try any link or button with text "Download"
        button = page.query_selector('a:has-text("Download"), button:has-text("Download")')
        if button and button.is_visible():
            href = button.get_attribute('href')
            if href and href.lower().endswith('.pdf'):
                print(f"↓ Downloading PDF: {href}")
                _fetch_and_save(page, href, detail_url)
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
                    mapping[detail_url] = fname
                    save_downloaded_mapping(mapping)
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
        if not solve_captcha_if_present(page):
            print(f"Skipping form due to captcha failure: {page.url}")
            return
        
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
                return
            print("Form filled, report appears to be revealed on page. Saving as PDF.")
            save_webpage_as_pdf(page, DOWNLOAD_DIR, safe_title, detail_url)
            return
    # If still nothing, log the HTML for debugging
    print("No download link/button or downloadable form found, saving page as PDF and logging HTML for debugging.")
    with open("debug_beauhurst_page.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    save_webpage_as_pdf(page, DOWNLOAD_DIR, safe_title, detail_url)
    # After successful download or email confirmation:
    mapping[detail_url] = pdf_path.name
    save_downloaded_mapping(mapping)

def _fetch_and_save(page, url: str, detail_url=None):
    """Helper: fetch PDF via HTTP and save. Updates mapping if detail_url is provided."""
    fname = url.split('/')[-1].split('?')[0]
    target = DOWNLOAD_DIR / fname
    mapping = load_downloaded_mapping()
    if target.exists():
        print(f"✓ Already have {fname}")
        if detail_url:
            mapping[detail_url] = fname
            save_downloaded_mapping(mapping)
        return True
    print(f"↓ Downloading {fname}")
    try:
        resp = page.context.request.get(url, timeout=DOWNLOAD_TIMEOUT)
        with open(target, 'wb') as f:
            f.write(resp.body())
        if detail_url:
            mapping[detail_url] = fname
            save_downloaded_mapping(mapping)
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

def scrape_and_download_beauhurst(page, max_pages=20):
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
        if not cards:
            print(f"No report links found on page {i}. Stopping pagination.")
            break
            
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
    mapping = load_downloaded_mapping()
    
    REPORT_LISTING_URLS = [
        "https://pitchbook.com/news/reports",
        "https://pitchbook.com/news/reports?types=analyst-note",
        "https://pitchbook.com/news/reports?topics=industry-and-technology-research",
        "https://pitchbook.com/news/reports?types=market-update,snapshot"
    ]
    
    all_detail_urls = set()

    for listing_url in REPORT_LISTING_URLS:
        print(f"\n[LOG] Processing listing: {listing_url}")
        try:
            page.goto(listing_url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
            page.wait_for_selector("a[href^='/news/reports/']", timeout=30000)
            
            # Scroll to load all reports on the page
            last_height = page.evaluate("document.body.scrollHeight")
            while True:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                page.wait_for_timeout(2000) # Wait for content to load
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            links = page.query_selector_all("a[href^='/news/reports/']")
            for a in links:
                href = a.get_attribute('href')
                if href and href != '/news/reports':
                    full_url = f"https://pitchbook.com{href}"
                    all_detail_urls.add(full_url)
        except Exception as e:
            print(f"⚠️ Could not process listing {listing_url}: {e}")
            continue

    print(f"Found a total of {len(all_detail_urls)} unique PitchBook reports across all listings.")
    for du in all_detail_urls:
        download_pdf_from_detail(page, du)

def scrape_and_download_techcrunch(page, max_clicks=100):
    print("\n=== TechCrunch News ===")
    base = "https://techcrunch.com"
    start_url = f"{base}/latest"
    
    # Load existing data to avoid duplicates
    json_file = Path(__file__).parent / "data" / "techcrunch_downloaded.json"
    if json_file.exists():
        with open(json_file, 'r') as f:
            try:
                data = json.load(f)
                seen_urls = set(r.get("url") for r in data.get("reports", []))
            except json.JSONDecodeError:
                data = {"reports": []}
                seen_urls = set()
    else:
        data = {"reports": []}
        seen_urls = set()

    page.goto(start_url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    accept_cookies(page)

    clicks = 0
    while clicks < max_clicks:
        # Wait for either of the two known selectors for article links to appear.
        page.wait_for_selector('a.post-block__title__link, a.loop-card__title-link', timeout=10000)
        # Query for all article links that match either selector.
        articles = page.query_selector_all('a.post-block__title__link, a.loop-card__title-link')
        new_articles_found_on_page = 0

        for article in articles:
            url = article.get_attribute('href')
            if url and url not in seen_urls:
                new_articles_found_on_page += 1
                seen_urls.add(url)
                title = article.inner_text().strip()
                print(f"Found new article: {title}")
                
                # Save the article as a PDF
                try:
                    page2 = page.context.new_page()
                    page2.goto(url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
                    accept_cookies(page2)
                    
                    safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
                    safe_title = re.sub(r'[-\s]+', '_', safe_title).strip('_').lower()
                    
                    # Try to save just the main article content for a cleaner PDF
                    content_selector = "div.article-content"
                    if page2.query_selector(content_selector):
                        save_webpage_as_pdf(page2, DOWNLOAD_DIR, safe_title, detail_url=url, selector=content_selector)
                    else:
                        save_webpage_as_pdf(page2, DOWNLOAD_DIR, safe_title, detail_url=url)
                    
                    page2.close()
                except Exception as e:
                    print(f"⚠️ Failed to process and save article {url}: {e}")

        if new_articles_found_on_page == 0 and clicks > 0:
            print("No new articles found on this page. Stopping.")
            break

        # Click the "Load More" button to get new articles
        try:
            load_more_button = page.query_selector('a.wp-block-query-pagination-next')
            if load_more_button and load_more_button.is_enabled():
                print("Clicking 'Load More'...")
                load_more_button.click()
                clicks += 1
                # Wait for the new content to load
                page.wait_for_timeout(3000) 
            else:
                print("No 'Load More' button found. Stopping.")
                break
        except Exception as e:
            print(f"Could not click 'Load More' button: {e}")
            break

def main():
    with sync_playwright() as pw:
        user_data_dir = "/tmp/playwright_user_data"
        env = {
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", "YOUR_GOOGLE_API_KEY_HERE")
        }
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
        context = pw.chromium.launch_persistent_context(user_data_dir, headless=True, accept_downloads=True, env=env, args=browser_args)
        stealth = Stealth()
        stealth.apply_stealth_sync(context)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)

        scrape_and_download_crunchbase(page)
        scrape_and_download_beauhurst(page)
        scrape_and_download_pitchbook(page)
        scrape_and_download_techcrunch(page)

        # Download any reports from email
        download_beauhurst_pdfs_from_gmail(DOWNLOAD_DIR)

        context.close()

if __name__ == '__main__':
    main()

