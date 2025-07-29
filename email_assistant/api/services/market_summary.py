import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env at import time so OPENAI_API_KEY is set
load_dotenv()

client = OpenAI()

PROMPT = """You are a market research expert…
(<<< same prompt text you saw in Flybridge index.js >>>)"""


async def summarize(text: str, trace_id: str) -> str:
    # We remove headers=… since the OpenAI client doesn't accept that parameter.
    r = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": f"Company description:\n{text}"},
        ],
    )
    return r.choices[0].message.content.strip()
