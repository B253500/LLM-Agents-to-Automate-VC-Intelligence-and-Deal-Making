import pdfplumber
from hashlib import sha1
from pathlib import Path
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.schemas import StartupProfile
from core.vector_store import add_doc

LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

SYSTEM = (
    "You are a VC analyst. Extract the following JSON keys from the text: {keys}. "
    "Return ONLY valid JSON."
)
HUMAN = "Pitch-deck text (truncated to 5 000 characters):\n```markdown\n{deck}\n```"
PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", HUMAN)])


def pdf_to_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages)


def run_pitch_deck_chain(pdf_path: str) -> StartupProfile:
    deck = pdf_to_text(Path(pdf_path))[:5000]
    keys = list(StartupProfile.model_fields.keys())[:6]
    prompt = PROMPT.format(keys=", ".join(keys), deck=deck)
    response = LLM.invoke(prompt)
    profile = StartupProfile.model_validate_json(response.content)
    profile.startup_id = sha1(profile.name.encode()).hexdigest()[:10]
    add_doc(profile.startup_id, deck)  # store for later RAG
    return profile
