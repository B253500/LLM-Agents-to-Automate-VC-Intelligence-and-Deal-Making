import chromadb
from chromadb.config import Settings

client = chromadb.Client(
    Settings(chroma_db_impl="duckdb+parquet", persist_directory=".chroma")
)
collection = client.get_or_create_collection("startup_docs")


def add_doc(startup_id: str, text: str):
    collection.add(documents=[text], ids=[startup_id], metadatas=[{"sid": startup_id}])


def query_doc(startup_id: str, question: str, k: int = 4):
    return collection.query(
        query_texts=[question],
        n_results=k,
        where={"sid": startup_id},
    )
