from fastapi import FastAPI
from memo_api.routes import upload, memo, health, pdf_memo

app = FastAPI(title="VC Memo API")

app.include_router(upload.router, prefix="/api")
app.include_router(memo.router, prefix="/api")
app.include_router(health.router, prefix="/api")
# app.include_router(pdf_memo.router, prefix="/api")
