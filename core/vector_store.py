from chromadb import Client, Settings
from pathlib import Path
import os

# Get the ChromaDB directory from environment variable or use default
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", ".chroma")
ROOT = Path(CHROMA_DB_DIR)
ROOT.mkdir(exist_ok=True)

# Initialize ChromaDB with proper settings
client = Client(
    Settings(
        anonymized_telemetry=False,
        allow_reset=True,
        is_persistent=True,
        persist_directory=str(ROOT),
    )
)

# Create or get the collection with proper configuration
collection = client.get_or_create_collection(
    name="startup_docs", metadata={"hnsw:space": "cosine"}
)


def add_doc(startup_id: str, text: str) -> None:
    collection.add(
        documents=[text],
        ids=[startup_id],
        metadatas=[{"sid": startup_id}],
    )


def query_doc(startup_id: str | None, question: str, k: int = 4):
    """Return k document snippets, or [] if no id yet."""
    if not startup_id:  # ← guard against None/empty
        return []
    res = collection.query(
        query_texts=[question],
        n_results=k,
        where={"sid": startup_id},
    )
    return res["documents"][0] if res["documents"] else []
