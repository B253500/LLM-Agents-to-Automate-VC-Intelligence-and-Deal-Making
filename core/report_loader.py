from pathlib import Path
from typing import List
import hashlib
from chains.pitch_deck_chain import pdf_to_text
from core.vector_store import add_doc

def load_vc_reports(reports_dir: str = "data/vc_reports") -> List[str]:
    """
    Load all VC reports from the directory into the vector store.
    Returns list of report IDs for reference.
    """
    reports_dir = Path(reports_dir)
    report_ids = []
    
    for pdf_file in reports_dir.glob("*.pdf"):
        # Generate a deterministic ID for the report
        report_id = f"report_{hashlib.sha1(pdf_file.name.encode()).hexdigest()[:10]}"
        
        # Load and process the PDF
        try:
            text = pdf_to_text(pdf_file)
            # Store in vector database
            add_doc(report_id, text)
            report_ids.append(report_id)
            print(f"Loaded report: {pdf_file.name}")
        except Exception as e:
            print(f"Error loading {pdf_file.name}: {e}")
    
    return report_ids

def get_report_context(question: str, k: int = 3) -> str:
    """
    Get relevant context from all loaded reports for a specific question.
    Uses the existing vector store query mechanism.
    """
    from core.vector_store import collection
    
    # Query across all reports
    results = collection.query(
        query_texts=[question],
        n_results=k,
    )
    
    # Combine results
    contexts = results["documents"][0] if results["documents"] else []
    return "\n\n".join([str(c) for c in contexts if c]) if contexts else "No relevant report data found." 