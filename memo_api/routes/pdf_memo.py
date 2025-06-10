# memo_api/routes/pdf_memo.py

import uuid
from fastapi import APIRouter, Body, Response
from memo_api.services import market_summary, market_analysis, memo_generator, linkedin
from weasyprint import HTML

router = APIRouter()


@router.post("/memo-pdf")
async def memo_pdf_endpoint(payload: dict = Body(...)):
    trace_id = payload.get("traceId") or str(uuid.uuid4())

    # 1) Summarise market → 2) Run analysis → 3) Fetch founders
    text = payload["extractedText"]
    opportunity = await market_summary.summarize(text, trace_id)
    analysis = await market_analysis.run_cli(opportunity, trace_id)
    founders = await linkedin.batch_fetch(payload.get("linkedInUrls", []), trace_id)

    # 4) Generate HTML memo
    memo_html = await memo_generator.generate(
        opportunity=opportunity,
        analysis=analysis,
        founders=founders,
        meta=payload,
        trace_id=trace_id,
    )

    # 5) Convert HTML string to PDF bytes
    pdf_bytes = HTML(string=memo_html).write_pdf()

    # 6) Return as a PDF response
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="investment_memo.pdf"'},
    )
