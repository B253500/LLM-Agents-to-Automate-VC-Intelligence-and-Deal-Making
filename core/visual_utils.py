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


# Example usage:
# images = extract_images_from_pdf("data/storedot.pdf", "extracted_images/")
# chart_path = generate_sample_market_chart({"2022": 1.2, "2023": 1.5, "2024": 2.0}, "market_chart.png") 