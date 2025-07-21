import os
import fitz  # PyMuPDF
import matplotlib.pyplot as plt
from typing import List


def extract_images_from_pdf(pdf_path: str, output_dir: str) -> List[str]:
    """
    Extracts images from a PDF and saves them to the output directory.
    Returns a list of file paths to the extracted images.
    """
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    image_paths = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_filename = f"page{page_num+1}_img{img_index+1}.{image_ext}"
            image_path = os.path.join(output_dir, image_filename)
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            image_paths.append(image_path)
    return image_paths


def generate_sample_market_chart(data: dict, output_path: str) -> str:
    """
    Generates a sample bar chart from memo data and saves it as an image.
    Example data: {"2022": 1.2, "2023": 1.5, "2024": 2.0}
    Returns the path to the saved image.
    """
    years = list(data.keys())
    values = list(data.values())
    plt.figure(figsize=(6, 4))
    plt.bar(years, values, color="#2a5599")
    plt.xlabel("Year")
    plt.ylabel("Market Size (B USD)")
    plt.title("Market Size by Year")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path


def filter_graphs_and_tables(image_paths: list[str]) -> list[str]:
    """
    Use Google Vision API to keep only images that are likely tables, charts, graphs, diagrams, or plots.
    If Google Vision is not available, return all images.
    """
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()
        wanted = {"table", "chart", "graph", "diagram", "plot"}
        keep: list[str] = []
        for p in image_paths:
            with open(p, "rb") as f:
                img = vision.Image(content=f.read())
            labels = {l.description.lower() for l in client.label_detection(image=img).label_annotations}
            if labels & wanted:
                keep.append(p)
        return keep
    except ImportError:
        # Fallback: no filtering if Vision API isn't available
        return image_paths


def extract_market_and_financials_from_visuals(profile, figures_ocr, tables_text):
    """
    Extract market size and financial metrics from figures_ocr and tables_text using LLM.
    Updates the profile in-place with extracted values and sources.
    """
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    missing_fields = []
    if not getattr(profile, 'TAM', None): missing_fields.append('TAM')
    if not getattr(profile, 'SAM', None): missing_fields.append('SAM')
    if not getattr(profile, 'SOM', None): missing_fields.append('SOM')
    if not getattr(profile, 'cash_burn_12m', None): missing_fields.append('cash_burn_12m')
    if not getattr(profile, 'runway_months', None): missing_fields.append('runway_months')
    if not getattr(profile, 'implied_valuation', None): missing_fields.append('implied_valuation')
    if not getattr(profile, 'cagr', None): missing_fields.append('CAGR')
    if not getattr(profile, 'market_growth_rate', None): missing_fields.append('market_growth_rate')
    if not missing_fields:
        return profile
    ocr_context = figures_ocr or ''
    table_context = tables_text or ''
    context = ocr_context + "\n\n" + table_context
    prompt = f"""
You are a VC analyst extracting market size and financial metrics from pitch deck text, figures, and tables.
- Your TOP PRIORITY is to find market size values (TAM, SAM, SOM, etc.) in figures and tables extracted from the deck, especially those with currency symbols ($, €, £, etc.).
- For each value, state the context (e.g., 'from figure on page X', 'from table on page Y', or 'from OCR text').
- If multiple values are found, prefer the most recent or most clearly labeled.
- Only if a value is not found in figures/tables, leave it null (web search will be used as fallback).
- For each value, pair it with its context/label (e.g., 'Total Addressable Market', 'CAGR', 'Revenue 2025', etc.).
- Extract the following fields if present: {', '.join(missing_fields)}. If a field is missing, leave it null.
- Return a JSON object with these fields and a short explanation for each value if possible.
Context:
{context}
"""
    txt = llm.invoke(prompt).content.strip()
    import json
    first, last = txt.find("{"), txt.rfind("}")
    if first != -1 and last != -1:
        data = json.loads(txt[first : last + 1])
        for k, v in data.items():
            if hasattr(profile, k) and v:
                # Try to cast to float for numeric fields
                if k in ['TAM', 'SAM', 'SOM', 'cagr', 'market_growth_rate']:
                    try:
                        setattr(profile, k, float(v))
                    except Exception:
                        setattr(profile, k, v)
                else:
                    setattr(profile, k, v)
                # Set source for each value
                if k in ['TAM', 'SAM', 'SOM', 'cagr', 'market_growth_rate']:
                    setattr(profile, f"{k}_source", 'deck_ocr/table')
    return profile


# Example usage:
# images = extract_images_from_pdf("data/storedot.pdf", "extracted_images/")
# chart_path = generate_sample_market_chart({"2022": 1.2, "2023": 1.5, "2024": 2.0}, "market_chart.png") 