import json
import re
from pathlib import Path
from playwright.sync_api import Error as PlaywrightError

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