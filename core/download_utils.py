import json
import re
from pathlib import Path
from playwright.sync_api import Error as PlaywrightError
import os
import pdfplumber
from google.cloud import vision
import io
from docx import Document

DOWNLOAD_DIR = Path(__file__).parent.parent / "data" / "vc_reports"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAPPING_FILE = Path(__file__).parent.parent / "downloaded_reports.json"
NAV_TIMEOUT = 60000
DOWNLOAD_TIMEOUT = 120000

# --- Mapping helpers ---
def load_downloaded_mapping():
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE, "r") as f:
            return json.load(f)
    return {}

def save_downloaded_mapping(mapping):
    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)

# --- PDF download/save helpers ---
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

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join([page.extract_text() or "" for page in pdf.pages])
    if not text.strip():
        # Fallback to OCR if no text was extracted
        text = extract_text_from_image(pdf_path)
    return text

# General extraction dispatcher

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    elif ext in [".png", ".jpg", ".jpeg"]:
        return extract_text_from_image(file_path)
    else:
        raise ValueError("Unsupported file type") 