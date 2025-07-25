import json
import re
import os
import pdfplumber
import io
import asyncio
from pathlib import Path
from playwright.sync_api import Error as PlaywrightError
from google.cloud import vision
from docx import Document
from memo_api.services import ocr
import hashlib

DOWNLOAD_DIR = Path(__file__).parent.parent / "data" / "vc_reports"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAPPING_FILE = Path(__file__).parent.parent / "downloaded_reports.json"
NAV_TIMEOUT = 60000
DOWNLOAD_TIMEOUT = 120000

#  Mapping helpers 
def load_downloaded_mapping():
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE, "r") as f:
            return json.load(f)
    return {}

def save_downloaded_mapping(mapping):
    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)

# PDF download/save helpers 
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

def save_webpage_as_pdf(page, download_dir, safe_title, detail_url=None, selector=None):
    """
    Save the current page as a PDF. If selector is provided, only the element matching that selector is saved as PDF.
    """
    safe_title = re.sub(r'[^0-9\w\s-]', '', safe_title)
    safe_title = re.sub(r'[\W\s-]+', '_', safe_title).strip('_').lower()
    pdf_path = download_dir / f"{safe_title}.pdf"
    page.set_viewport_size({"width": 1280, "height": 1800})
    if selector:
        # Wait for the element to appear
        try:
            element = page.wait_for_selector(selector, timeout=5000)
            page.wait_for_timeout(1000)
            element.pdf(path=str(pdf_path), format="A4", print_background=True)
            print(f"Saved element ({selector}) as PDF: {pdf_path}")
        except Exception as e:
            print(f"[ERROR] Could not save element {selector} as PDF: {e}")
            return
    else:
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

# OCR for images and scanned PDFs

def extract_text_from_image(image_path):
    client = vision.ImageAnnotatorClient()
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    return response.full_text_annotation.text if response.full_text_annotation else ""

# DOCX extraction

def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])

# PDF extraction with OCR fallback

def extract_text_from_pdf(pdf_path, return_structured=False):
    """
    Extract text (and optionally structured OCR data) from a PDF using Google Cloud Vision OCR.
    Args:
        pdf_path (str): Path to the PDF file.
        return_structured (bool): If True, return dict with text, tables, figures.
    Returns:
        str or dict: Extracted text, or dict with text/tables/figures.
    """
    print(f"[OCR] Extracting all text from {pdf_path} using Google Cloud Vision...")
    result = asyncio.run(ocr.process_pdfs([pdf_path]))
    if return_structured:
        return result
    return result["text"]

# General extraction dispatcher

def extract_text(file_path, return_structured=False):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path, return_structured=return_structured)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    elif ext in [".png", ".jpg", ".jpeg"]:
        return extract_text_from_image(file_path)
    else:
        raise ValueError("Unsupported file type") 

def get_cache_path(file_path):
    # Use file hash for uniqueness
    with open(file_path, 'rb') as f:
        file_hash = hashlib.sha1(f.read()).hexdigest()
    return os.path.join("extraction_cache", f"{os.path.basename(file_path)}_{file_hash}.json")

def load_from_cache(file_path):
    cache_path = get_cache_path(file_path)
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_to_cache(file_path, data):
    cache_path = get_cache_path(file_path)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f) 

def extract_market_size_from_text(text):
    """Extract market size values with better error handling and logging"""
    results = {}
    try:
        tam_match = re.search(r'(Total Addressable Market|Addressable market|TAM)[^\d$]{0,20}(\$?\d+[,.]?\d*)\s*[Bb]?', text, re.IGNORECASE)
        if tam_match:
            val = tam_match.group(2).replace(',', '').replace('$', '')
            try:
                results['TAM'] = float(val) * 1e9 if 'B' in tam_match.group(0) or 'billion' in tam_match.group(0).lower() else float(val)
                print(f"[Market Size] Found TAM={results['TAM']}")
            except Exception as e:
                print(f"[Market Size] Error parsing TAM value '{val}': {e}")
                results['TAM'] = val
        # SAM
        sam_match = re.search(r'(Serviceable Available Market|SAM)[^\d$]{0,20}(\$?\d+[,.]?\d*)\s*[BbMmKk]?', text, re.IGNORECASE)
        if sam_match:
            val = sam_match.group(2).replace(',', '').replace('$', '')
            try:
                results['SAM'] = float(val) * 1e9 if 'B' in sam_match.group(0) or 'billion' in sam_match.group(0).lower() else float(val)
                print(f"[Market Size] Found SAM={results['SAM']}")
            except Exception as e:
                print(f"[Market Size] Error parsing SAM value '{val}': {e}")
        # SOM
        som_match = re.search(r'(Serviceable Obtainable Market|SOM)[^\d$]{0,20}(\$?\d+[,.]?\d*)\s*[BbMmKk]?', text, re.IGNORECASE)
        if som_match:
            val = som_match.group(2).replace(',', '').replace('$', '')
            try:
                results['SOM'] = float(val) * 1e9 if 'B' in som_match.group(0) or 'billion' in som_match.group(0).lower() else float(val)
                print(f"[Market Size] Found SOM={results['SOM']}")
            except Exception as e:
                print(f"[Market Size] Error parsing SOM value '{val}': {e}")
        # CAGR
        cagr_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%\s*CAGR', text)
        if cagr_match:
            try:
                results['cagr'] = float(cagr_match.group(1))
                print(f"[Market Size] Found CAGR={results['cagr']}%")
            except Exception as e:
                print(f"[Market Size] Error parsing CAGR: {e}")
    except Exception as e:
        print(f"[Market Size] Error extracting market sizes: {e}")
    return results 

def update_market_value(profile, key, value, source):
    """Update market size value if new source has higher priority"""
    if not value:
        return
    
    current = getattr(profile, key, None)
    current_source = getattr(profile, f"{key}_source", None)
    
    # Priority: deck_text > web_search > None
    source_priority = {
        "deck_text": 3,
        "deck_ocr/table": 3,
        "web_search": 2,
        None: 1
    }
    
    current_priority = source_priority.get(current_source, 1)
    new_priority = source_priority.get(source, 1)
    
    if new_priority > current_priority or (new_priority == current_priority and current is None):
        setattr(profile, key, value)
        setattr(profile, f"{key}_source", source)
        print(f"[Market Size] Updated {key}={value} (source: {source})")
    else:
        print(f"[Market Size] Skipped {key}={value} (current: {current}, priority: {current_priority} vs {new_priority})")

def log_market_size_changes(profile):
    """Log all market size values and their sources"""
    market_keys = ['TAM', 'SAM', 'SOM', 'cagr', 'market_growth_rate']
    print("\n[Market Size Summary]")
    for key in market_keys:
        value = getattr(profile, key, None)
        source = getattr(profile, f"{key}_source", None)
        if value:
            print(f"  {key}: {value} (source: {source})")
        else:
            print(f"  {key}: Not found")
    print() 