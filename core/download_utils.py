# Standard library imports
import os
import json
import hashlib
import re
import asyncio
from pathlib import Path

# Third-party imports
import pdfplumber
from docx import Document
from google.cloud import vision_v1
import io

# Local imports
import sys
sys.path.append(str(Path(__file__).parent.parent / "memo_api" / "services"))
from ocr import process_pdfs as ocr_process_pdfs
from core.visual_utils import extract_images_from_pdf

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
    client = vision_v1.ImageAnnotatorClient()
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision_v1.Image(content=content)
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
    result = asyncio.run(ocr_process_pdfs([pdf_path]))
    if return_structured:
        return result
    return result["text"]

def parse_money_string(value_str):
    """
    Parse money string to float value
    Examples: "$1.5B" -> 1500000000.0, "2.3M" -> 2300000.0
    """
    if not value_str:
        return None
    
    # Remove common currency symbols and whitespace
    value_str = str(value_str).strip().replace('$', '').replace(',', '')
    
    # Handle different suffixes
    multipliers = {
        'B': 1e9,
        'billion': 1e9,
        'M': 1e6,
        'million': 1e6,
        'K': 1e3,
        'thousand': 1e3,
        'k': 1e3
    }
    
    # Try to find a suffix
    for suffix, multiplier in multipliers.items():
        if suffix in value_str.lower():
            # Extract the number part
            number_part = value_str.lower().replace(suffix, '').strip()
            try:
                return float(number_part) * multiplier
            except ValueError:
                continue
    
    # If no suffix found, try to parse as float
    try:
        return float(value_str)
    except ValueError:
        return value_str  # Return as string if can't parse


# Enhanced PDF extraction with multi-modal approach
def enhanced_pdf_extraction(pdf_path, return_structured=False):
    """
    Multi-modal PDF extraction combining:
    - Native text extraction (pdfplumber)
    - OCR for scanned content (Google Cloud Vision)
    - Table extraction (pdfplumber)
    - Image extraction and OCR
    - Chart/graph text extraction
    """
    print(f"[Enhanced Extraction] Processing {pdf_path} with multi-modal approach...")
    
    results = {
        "text": "",
        "tables": [],
        "figures": [],
        "charts": [],
        "structured_data": {}
    }
    
    # 1. Native text extraction (fastest, most accurate)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            native_text = []
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    native_text.append(f"--- Page {page_num} ---\n{text}")
            results["text"] = "\n\n".join(native_text)
            print(f"[Enhanced Extraction] Native text: {len(results['text'])} characters")
    except Exception as e:
        print(f"[Enhanced Extraction] Native extraction failed: {e}")
    
    # 2. Table extraction with enhanced detection
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract structured tables
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables, 1):
                    if table and len(table) > 1:  # Valid table
                        # Convert table to readable format
                        table_text = "\n".join([
                            " | ".join([str(cell) if cell is not None else "" for cell in row])
                            for row in table
                        ])
                        results["tables"].append({
                            "page": page_num,
                            "table_index": table_idx,
                            "type": "structured_table",
                            "data": table,
                            "text": table_text
                        })
                        print(f"[Enhanced Extraction] Found table on page {page_num}")
                
                # Extract text that might be tabular data by looking for patterns
                page_text = page.extract_text()
                if page_text:
                    # Look for lines with consistent separators that might be tabular
                    lines = page_text.split('\n')
                    tabular_lines = []
                    for line in lines:
                        if is_tabular_text(line):
                            tabular_lines.append(line)
                    
                    if len(tabular_lines) >= 3:  # At least 3 lines to be considered a table
                        table_text = "\n".join(tabular_lines)
                        parsed_table = parse_tabular_text(table_text)
                        if parsed_table:
                            results["tables"].append({
                                "page": page_num,
                                "table_index": f"text_table",
                                "type": "text_table",
                                "data": parsed_table,
                                "text": table_text
                            })
                            print(f"[Enhanced Extraction] Found text table on page {page_num}")
    except Exception as e:
        print(f"[Enhanced Extraction] Table extraction failed: {e}")
    
    # 3. OCR for any missing/scanned content
    if not results["text"] or len(results["text"]) < 1000:
        print("[Enhanced Extraction] Text too short, running OCR...")
        try:
            ocr_result = asyncio.run(ocr_process_pdfs([pdf_path]))
            results["text"] += "\n\n" + ocr_result["text"]
            results["figures"] = ocr_result.get("figures", [])
            print(f"[Enhanced Extraction] OCR added {len(ocr_result['text'])} characters")
        except Exception as e:
            print(f"[Enhanced Extraction] OCR failed: {e}")
    
    # 4. Image/chart extraction and OCR
    try:
        image_paths = extract_images_from_pdf(pdf_path, "temp_images")
        chart_texts = []
        for img_path in image_paths:
            # OCR on images to extract text from charts
            try:
                img_text = extract_text_from_image(img_path)
                if img_text and len(img_text.strip()) > 10:
                    chart_texts.append(img_text)
                    results["charts"].append({
                        "image_path": img_path,
                        "text": img_text
                    })
                    print(f"[Enhanced Extraction] Found chart text: {len(img_text)} characters")
            except Exception as img_error:
                print(f"[Enhanced Extraction] Image OCR failed for {img_path}: {img_error}")
                # Fallback: try to extract text from image filename or path
                img_name = os.path.basename(img_path)
                if "chart" in img_name.lower() or "graph" in img_name.lower():
                    results["charts"].append({
                        "image_path": img_path,
                        "text": f"[Chart/Graph detected: {img_name}]"
                    })
                    print(f"[Enhanced Extraction] Added chart placeholder for {img_name}")
        
        # Add chart text to main text
        if chart_texts:
            results["text"] += "\n\n--- CHART AND GRAPH TEXT ---\n" + "\n\n".join(chart_texts)
    except Exception as e:
        print(f"[Enhanced Extraction] Image extraction failed: {e}")
        # Continue without image extraction
    
    # 5. Extract structured financial and market data
    results["structured_data"] = extract_financial_metrics_enhanced(
        results["text"], 
        results["tables"], 
        results["charts"]
    )
    
    if return_structured:
        return results
    return results["text"]


def is_tabular_text(text_block):
    """
    Determine if a text block contains tabular data
    """
    if not text_block or len(text_block) < 50:
        return False
    
    # Look for patterns that suggest tabular data
    lines = text_block.split('\n')
    if len(lines) < 2:
        return False
    
    # Check for consistent separators (tabs, multiple spaces, pipes)
    separator_patterns = [
        r'\t+',  # Tabs
        r'\s{3,}',  # Multiple spaces
        r'\s*\|\s*',  # Pipes
        r'\s*,\s*',  # Commas
    ]
    
    for pattern in separator_patterns:
        matches = 0
        for line in lines[:5]:  # Check first 5 lines
            if re.search(pattern, line):
                matches += 1
        if matches >= 3:  # At least 3 lines have separators
            return True
    
    return False


def parse_tabular_text(text_block):
    """
    Parse text block into tabular format
    """
    lines = text_block.split('\n')
    table_data = []
    
    for line in lines:
        if not line.strip():
            continue
        
        # Try different separators
        for separator in ['\t', '  ', ' | ', ', ']:
            if separator in line:
                row = [cell.strip() for cell in line.split(separator)]
                if len(row) > 1:
                    table_data.append(row)
                    break
    
    return table_data if table_data else None


def extract_financial_metrics_enhanced(text, tables, charts):
    """
    Enhanced financial metric extraction from all sources
    """
    print("[Enhanced Extraction] Extracting financial metrics...")
    
    # Combine all text sources
    all_text = text
    for table in tables:
        if isinstance(table, dict) and "text" in table:
            all_text += "\n" + table["text"]
        elif isinstance(table, list):
            all_text += "\n" + str(table)
    
    for chart in charts:
        if isinstance(chart, dict) and "text" in chart:
            all_text += "\n" + chart["text"]
        elif isinstance(chart, str):
            all_text += "\n" + chart
    
    # Enhanced patterns for financial data
    patterns = {
        "market_size": [
            r"(\$?\d+\.?\d*)\s*[Bb]illion.*[Tt]otal.*[Aa]ddressable.*[Mm]arket",
            r"[Tt]otal.*[Aa]ddressable.*[Mm]arket.*(\$?\d+\.?\d*)\s*[Bb]illion",
            r"TAM.*(\$?\d+\.?\d*)\s*[Bb]illion",
            r"(\$?\d+\.?\d*)\s*[Bb]illion.*TAM",
            r"(\$?\d+\.?\d*)\s*[Bb]illion.*[Bb]attery.*[Mm]arket",
            r"[Bb]attery.*[Mm]arket.*(\$?\d+\.?\d*)\s*[Bb]illion",
            r"(\$?\d+\.?\d*)\s*[Bb]illion.*[Mm]arket",
            r"[Mm]arket.*(\$?\d+\.?\d*)\s*[Bb]illion"
        ],
        "revenue": [
            r"(\$?\d+\.?\d*)\s*[KMB]?.*[Rr]evenue",
            r"[Rr]evenue.*(\$?\d+\.?\d*)\s*[KMB]?",
            r"(\$?\d+\.?\d*)\s*[KMB]?.*[Ss]ales",
            r"[Ss]ales.*(\$?\d+\.?\d*)\s*[KMB]?"
        ],
        "funding": [
            r"(\$?\d+\.?\d*)\s*[KMB]?.*[Ff]unding",
            r"[Ff]unding.*(\$?\d+\.?\d*)\s*[KMB]?",
            r"(\$?\d+\.?\d*)\s*[KMB]?.*[Ii]nvested",
            r"[Ii]nvested.*(\$?\d+\.?\d*)\s*[KMB]?",
            r"(\$?\d+\.?\d*)\s*[KMB]?.*[Rr]aised",
            r"[Rr]aised.*(\$?\d+\.?\d*)\s*[KMB]?",
            r"(\$?\d+\.?\d*)\s*[KMB]?.*[Mm]illion.*[Ii]nvested",
            r"(\$?\d+\.?\d*)\s*[KMB]?.*[Bb]illion.*[Ii]nvested",
            r"(\$?\d+\.?\d*)\s*[KMB]?.*[Dd]ollars?.*[Ii]nvested",
            r"(\$?\d+\.?\d*)\s*[KMB]?.*[Uu]SD.*[Ii]nvested",
            r"(\$?\d+\.?\d*)\s*[KMB]?.*[Cc]apital",
            r"[Cc]apital.*(\$?\d+\.?\d*)\s*[KMB]?",
            r"(\$?\d+\.?\d*)\s*[KMB]?.*[Ss]trategic.*[Ii]nvestors?",
            r"[Ss]trategic.*[Ii]nvestors?.*(\$?\d+\.?\d*)\s*[KMB]?"
        ],
        "patents": [
            r"(\d+)\s*[Pp]atents?",
            r"(\d+)\s*[Gg]ranted.*[Pp]atents?",
            r"(\d+)\s*[Pp]ending.*[Pp]atents?",
            r"[Pp]atents?.*(\d+)"
        ],
        "employees": [
            r"(\d+)\s*[Ee]mployees?",
            r"(\d+)\s*[Ss]taff",
            r"(\d+)\s*[Tt]eam.*[Mm]embers?",
            r"[Tt]eam.*(\d+)"
        ],
        "energy_density": [
            r"(\d+)\s*[Ww]h/[Kk]g",
            r"(\d+)\s*[Ww]h/[Ll]",
            r"[Ee]nergy.*[Dd]ensity.*(\d+)",
            r"(\d+)\s*[Ww]h.*[Dd]ensity"
        ],
        "cycle_life": [
            r"(\d+)\s*[Cc]ycles?",
            r"(\d+)\s*[Cc]ycle.*[Ll]ife",
            r"[Cc]ycle.*[Ll]ife.*(\d+)",
            r"(\d+)\s*[Cc]onsecutive.*[Cc]ycles?"
        ]
    }
    
    results = {}
    
    for metric_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                # Parse the value
                value = matches[0]
                try:
                    if metric_type in ["patents", "employees", "energy_density", "cycle_life"]:
                        results[metric_type] = int(value)
                    else:
                        results[metric_type] = parse_money_string(value)
                    print(f"[Enhanced Extraction] Found {metric_type}: {results[metric_type]}")
                    break
                except Exception as e:
                    print(f"[Enhanced Extraction] Error parsing {metric_type} value '{value}': {e}")
                    results[metric_type] = value
                    break
    
    return results


def validate_extraction_quality(extracted_data):
    """
    Validate extraction quality and completeness
    """
    quality_score = 0
    missing_critical = []
    
    text = extracted_data.get("text", "")
    tables = extracted_data.get("tables", [])
    charts = extracted_data.get("charts", [])
    
    # Check for critical information
    critical_indicators = [
        ("company_name", r"[Cc]ompany|Corp|Inc|Ltd|LLC"),
        ("market_size", r"[Tt]otal.*[Aa]ddressable.*[Mm]arket|TAM|SAM|SOM"),
        ("funding", r"[Ff]unding|[Ii]nvestment|[Rr]aised"),
        ("team", r"[Cc]EO|[Ff]ounder|[Cc]hief|[Pp]resident"),
        ("technology", r"[Tt]echnology|[Pp]roduct|[Ss]olution")
    ]
    
    for indicator, pattern in critical_indicators:
        if not re.search(pattern, text, re.IGNORECASE):
            missing_critical.append(indicator)
            quality_score -= 1
    
    # Check text length (should be substantial)
    if len(text) < 2000:
        quality_score -= 2
        print(f"[Quality Check] Text too short: {len(text)} characters")
    
    # Check for tables (important for financial data)
    if not tables:
        quality_score -= 1
        print("[Quality Check] No tables found")
    
    # Check for charts (important for market data)
    if not charts:
        quality_score -= 1
        print("[Quality Check] No charts found")
    
    # Check for financial metrics
    structured_data = extracted_data.get("structured_data", {})
    if not structured_data:
        quality_score -= 1
        print("[Quality Check] No structured data found")
    
    recommendation = "reprocess" if quality_score < -2 else "proceed"
    
    print(f"[Quality Check] Score: {quality_score}, Recommendation: {recommendation}")
    print(f"[Quality Check] Missing: {missing_critical}")
    
    return {
        "quality_score": quality_score,
        "missing_critical": missing_critical,
        "recommendation": recommendation,
        "text_length": len(text),
        "table_count": len(tables),
        "chart_count": len(charts)
    }


# General extraction dispatcher

def extract_text(file_path, return_structured=False):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return enhanced_pdf_extraction(file_path, return_structured=return_structured)
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
        # Enhanced patterns for market size extraction
        patterns = {
            "TAM": [
                r'(Total Addressable Market|Addressable market|TAM)[^\d$]{0,20}(\$?\d+[,.]?\d*)\s*[Bb]?',
                r'(\$?\d+[,.]?\d*)\s*[Bb]illion.*[Tt]otal.*[Aa]ddressable.*[Mm]arket',
                r'[Tt]otal.*[Aa]ddressable.*[Mm]arket.*(\$?\d+[,.]?\d*)\s*[Bb]illion',
                r'TAM.*(\$?\d+[,.]?\d*)\s*[Bb]illion',
                r'(\$?\d+[,.]?\d*)\s*[Bb]illion.*TAM'
            ],
            "SAM": [
                r'(Serviceable Available Market|SAM)[^\d$]{0,20}(\$?\d+[,.]?\d*)\s*[BbMmKk]?',
                r'(\$?\d+[,.]?\d*)\s*[BbMmKk]?.*[Ss]erviceable.*[Aa]vailable.*[Mm]arket',
                r'[Ss]erviceable.*[Aa]vailable.*[Mm]arket.*(\$?\d+[,.]?\d*)\s*[BbMmKk]?'
            ],
            "SOM": [
                r'(Serviceable Obtainable Market|SOM)[^\d$]{0,20}(\$?\d+[,.]?\d*)\s*[BbMmKk]?',
                r'(\$?\d+[,.]?\d*)\s*[BbMmKk]?.*[Ss]erviceable.*[Oo]btainable.*[Mm]arket',
                r'[Ss]erviceable.*[Oo]btainable.*[Mm]arket.*(\$?\d+[,.]?\d*)\s*[BbMmKk]?'
            ],
            "market_size": [
                r'(\$?\d+[,.]?\d*)\s*[Bb]illion.*[Mm]arket',
                r'[Mm]arket.*(\$?\d+[,.]?\d*)\s*[Bb]illion',
                r'(\$?\d+[,.]?\d*)\s*[Bb]illion.*[Bb]attery.*[Mm]arket',
                r'[Bb]attery.*[Mm]arket.*(\$?\d+[,.]?\d*)\s*[Bb]illion'
            ]
        }
        
        for market_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    val = match.group(2) if len(match.groups()) > 1 else match.group(1)
                    parsed_value = parse_money_string(val)
                    if parsed_value:
                        results[market_type] = parsed_value
                        print(f"[Market Size] Found {market_type}={parsed_value}")
                        break
        
        # CAGR extraction
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