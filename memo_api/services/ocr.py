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
    extract text, clean up, and return the concatenated text.
    """
    if not paths:
        return ""

    bucket = gcs.bucket(BUCKET)
    full_text = ""

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

        # 3. Download results from GCS, extract text, then delete blobs
        for res_blob in bucket.list_blobs(prefix=dest_prefix):
            j = json.loads(res_blob.download_as_text())
            for r in j.get("responses", []):
                if "fullTextAnnotation" in r:
                    full_text += r["fullTextAnnotation"]["text"] + "\n\n"
            res_blob.delete()
        bucket.blob(blob_name).delete()

    return full_text
