import os
from pathlib import Path
import logging
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import pdfplumber
from dotenv import load_dotenv

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
PROCESSED_DIRS_FILE = "processed_dirs.txt"

# --- Helper Functions for Memory ---

def get_processed_dirs():
    """Reads the list of already processed directories from the log file."""
    if not os.path.exists(PROCESSED_DIRS_FILE):
        return set()
    with open(PROCESSED_DIRS_FILE, "r") as f:
        return set(line.strip() for line in f)

def add_dir_to_processed(dir_name):
    """Adds a directory name to the log file to mark it as processed."""
    with open(PROCESSED_DIRS_FILE, "a") as f:
        f.write(dir_name + "\n")

# --- Core Logic ---

def build_or_update_database(base_report_path: str, persist_directory: str):
    """
    Scans for new, unprocessed date-stamped directories in the base_report_path,
    extracts data from the PDFs within them, and adds this new data to the
    persistent ChromaDB vector store.
    """
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    base_reports_dir = Path(base_report_path)
    processed_dirs = get_processed_dirs()

    # Load the existing vector store if it exists, otherwise it will be created on the first run.
    vector_store = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    logger.info(f"Successfully loaded or initialized database at: {persist_directory}")

    new_dirs_found = False
    logger.info("Scanning for new report directories...")
    
    for date_dir in base_reports_dir.iterdir():
        if date_dir.is_dir() and date_dir.name not in processed_dirs:
            new_dirs_found = True
            logger.info(f"Found new directory to process: {date_dir.name}")
            
            documents = []
            for pdf_file in date_dir.glob("*.pdf"):
                try:
                    logger.info(f"  - Processing file: {pdf_file.name}")
                    # Extract text
                    loader = UnstructuredPDFLoader(str(pdf_file))
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["source"] = str(pdf_file.name)
                    documents.extend(docs)
                    
                    # Extract tables
                    with pdfplumber.open(str(pdf_file)) as pdf:
                        for page_num, page in enumerate(pdf.pages, 1):
                            tables = page.extract_tables()
                            for t_idx, table in enumerate(tables, 1):
                                table_str = "\n".join([", ".join([cell if cell is not None else "" for cell in row]) for row in table])
                                table_doc = Document(
                                    page_content=f"Table from {pdf_file.name}, page {page_num}:\n{table_str}",
                                    metadata={"source": str(pdf_file.name), "page": page_num, "type": "table"}
                                )
                                documents.append(table_doc)
                except Exception as e:
                    logger.error(f"    Error processing {pdf_file.name}: {e}")
            
            if documents:
                logger.info(f"  - Adding {len(documents)} new document chunks to the database.")
                vector_store.add_documents(documents)
                add_dir_to_processed(date_dir.name)
            else:
                logger.warning(f"  - No documents found in {date_dir.name}. Marking as processed to avoid re-scanning.")
                add_dir_to_processed(date_dir.name)

    if not new_dirs_found:
        logger.info("No new report directories to process. Database is up to date.")
    else:
        logger.info("Database update complete.")

if __name__ == '__main__':
    # The base path now points to the web_scraping output directory
    build_or_update_database(base_report_path="web_scraping/data/vc_reports", persist_directory="./chroma_db")
