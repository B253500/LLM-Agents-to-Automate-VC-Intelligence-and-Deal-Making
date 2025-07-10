import os
import json
import uuid
from google.cloud import vision_v1, storage

# ─── Change here: load credentials from your JSON key ───
CREDS_PATH = os.path.join(os.getcwd(), "cloud-credentials.json")
client = vision_v1.ImageAnnotatorClient.from_service_account_file(CREDS_PATH)
gcs = storage.Client.from_service_account_json(CREDS_PATH)

# The GCS bucket you created (or will create) for OCR
BUCKET = os.getenv("GCS_OCR_BUCKET", "investment_memo")
BATCH = 100


async def process_pdfs(paths):
    """
    Given a list of local PDF file paths, upload each to GCS,
    run asyncBatchAnnotateFiles, pull down the JSON results,
    extract text, tables, figures, clean up, and return a dict.
    Returns: dict with keys: 'text', 'tables', 'figures'
    """
    if not paths:
        return {"text": "", "tables": [], "figures": []}

    bucket = gcs.bucket(BUCKET)
    full_text = ""
    all_tables = []
    all_figures = []

    for local_path in paths:
        # 1. Upload PDF to GCS
        blob_name = f"temp/{uuid.uuid4()}.pdf"
        bucket.blob(blob_name).upload_from_filename(
            local_path, content_type="application/pdf"
        )

        # 2. Request async batch OCR
        dest_prefix = f"ocr-results/{uuid.uuid4()}-"
        req = {
            "input_config": {
                "gcs_source": {"uri": f"gs://{BUCKET}/{blob_name}"},
                "mime_type": "application/pdf",
            },
            "features": [{"type_": vision_v1.Feature.Type.DOCUMENT_TEXT_DETECTION}],
            "output_config": {
                "gcs_destination": {"uri": f"gs://{BUCKET}/{dest_prefix}"},
                "batch_size": BATCH,
            },
        }

        # Kick off and wait for completion
        op = client.async_batch_annotate_files(requests=[req])
        op.result(timeout=300)

        # 3. Download results from GCS, extract text, tables, figures, then delete blobs
        for res_blob in bucket.list_blobs(prefix=dest_prefix):
            j = json.loads(res_blob.download_as_text())
            for r in j.get("responses", []):
                # Extract full text
                if "fullTextAnnotation" in r:
                    full_text += r["fullTextAnnotation"]["text"] + "\n\n"
                # Extract tables and figures from blocks
                if "pages" in r:
                    for page in r["pages"]:
                        for block in page.get("blocks", []):
                            block_type = block.get("blockType", "UNKNOWN")
                            # Table detection: blockType == 'TABLE' or lots of rows/columns
                            if block_type == "TABLE" or (block_type == "TEXT" and len(block.get("paragraphs", [])) > 2):
                                # Reconstruct table as list of rows (each row is list of cell texts)
                                table_rows = []
                                for para in block.get("paragraphs", []):
                                    row = []
                                    for word in para.get("words", []):
                                        symbols = [s.get("text", "") for s in word.get("symbols", [])]
                                        row.append("".join(symbols))
                                    if row:
                                        table_rows.append(row)
                                if table_rows:
                                    all_tables.append({
                                        "page": page.get("pageNumber", None),
                                        "rows": table_rows,
                                        "boundingBox": block.get("boundingBox", {})
                                    })
                            # Figure detection: blockType == 'PICTURE' or block has no text but has boundingBox
                            if block_type == "PICTURE" or (not block.get("paragraphs") and block.get("boundingBox")):
                                all_figures.append({
                                    "page": page.get("pageNumber", None),
                                    "boundingBox": block.get("boundingBox", {}),
                                    "blockType": block_type
                                })
            res_blob.delete()
        bucket.blob(blob_name).delete()

    return {"text": full_text, "tables": all_tables, "figures": all_figures}
