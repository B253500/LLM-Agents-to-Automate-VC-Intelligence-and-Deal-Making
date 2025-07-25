from chromadb import PersistentClient
from pathlib import Path

ROOT = Path(".chroma")
ROOT.mkdir(exist_ok=True)

client = PersistentClient(path=str(ROOT))
collection = client.get_or_create_collection("startup_docs")


def clear_collection():
    """Clear all documents from the collection to prevent contamination between runs."""
    try:
        # Get all document IDs and delete them
        results = collection.get()
        if results and results['ids']:
            collection.delete(ids=results['ids'])
            print("Vector store cleared for fresh run")
        else:
            print("Vector store was already empty")
    except Exception as e:
        print(f"Warning: Could not clear vector store: {e}")


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
