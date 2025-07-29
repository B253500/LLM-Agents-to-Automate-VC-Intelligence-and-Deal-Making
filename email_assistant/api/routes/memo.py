from fastapi import APIRouter, Body
import uuid
from memo_api.services.truncate import truncate_to_chars

from memo_api.services import (
    market_summary,
    market_analysis,
    memo_generator,
    linkedin,
)

router = APIRouter()


@router.post("/memo")
async def memo_endpoint(payload: dict = Body(...)):
    # 1) Trace ID (for logging, if you want)
    trace_id = payload.get("traceId") or str(uuid.uuid4())

    # 2) Grab the full text that came from /upload
    raw_text = payload["extractedText"]

    # 3) Truncate it to, e.g., 8000 characters
    truncated_text = truncate_to_chars(raw_text, max_chars=8000)

    # 4) Summarize the truncated chunk
    opportunity = await market_summary.summarize(truncated_text, trace_id)

    # 5) Run market analysis on that summary
    analysis = await market_analysis.run_cli(opportunity, trace_id)

    # 6) Fetch founder info (unchanged)
    founders = await linkedin.batch_fetch(
        payload.get("linkedInUrls", []),
        trace_id,
    )

    # 7) Build a new “meta” dict that replaces the FULL extractedText
    #    with the truncated version. This ensures the final generator
    #    only ever sees truncated_text rather than raw_text.
    meta = {**payload, "extractedText": truncated_text}

    # 8) Generate the final HTML memo. Make sure generate(...) uses
    #    meta["extractedText"] (the truncated text) when constructing its prompt.
    memo_html = await memo_generator.generate(
        opportunity=opportunity,
        analysis=analysis,
        founders=founders,
        meta=meta,  # passes truncated_text instead of full text
        trace_id=trace_id,
    )

    return {"memorandum": memo_html, "traceId": trace_id}
