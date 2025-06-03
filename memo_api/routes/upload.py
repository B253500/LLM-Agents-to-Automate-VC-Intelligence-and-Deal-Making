from fastapi import APIRouter, UploadFile, File, Form
from typing import List
import uuid, os, tempfile, shutil

from memo_api.services import ocr

router = APIRouter()


@router.post("/upload")
async def upload(
    documents: List[UploadFile] = File(default=[]),
    ocrDocuments: List[UploadFile] = File(default=[]),
    email: str = Form(...),
    currentRound: str = Form(""),
    proposedValuation: str = Form(""),
    valuationDate: str = Form(""),
    url: str = Form(""),
    linkedInUrls: List[str] = Form(default=[]),
):
    trace_id = str(uuid.uuid4())
    workdir = tempfile.mkdtemp(prefix="memo_")

    # 1 save files
    saved = []
    for up in documents + ocrDocuments:
        dest = os.path.join(workdir, up.filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(up.file, f)
        saved.append(dest)

    # 2 OCR scanned PDFs
    ocr_text = await ocr.process_pdfs([p for p in saved if p.lower().endswith(".pdf")])

    return {
        "traceId": trace_id,
        "extractedText": ocr_text,
        "email": email,
        "currentRound": currentRound,
        "proposedValuation": proposedValuation,
        "valuationDate": valuationDate,
        "url": url,
        "linkedInUrls": linkedInUrls,
    }
