import os
from google.cloud import vision, storage
import pdfplumber

# ─── Change here: load credentials from your JSON key ───
CREDS_PATH = os.path.join(os.getcwd(), "cloud-credentials.json")
client = vision.ImageAnnotatorClient.from_service_account_file(CREDS_PATH)
gcs = storage.Client.from_service_account_json(CREDS_PATH)

# The GCS bucket you created (or will create) for OCR
BUCKET = os.getenv("GCS_OCR_BUCKET", "investment_memo")
BATCH = 100


async def process_pdfs(paths):
    """
    Given a list of local PDF file paths, extract text using pdfplumber
    and return the concatenated text.
    """
    if not paths:
        return ""

    full_text = ""

    for pdf_path in paths:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n\n"
        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")
            continue

    return full_text
