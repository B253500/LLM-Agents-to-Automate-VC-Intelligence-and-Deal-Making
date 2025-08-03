"""
CrewAI wrapper that hands off the heavy work to the LangChain pitch-deck chain.
Only the callback's return value is surfaced to the caller.
"""

from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path
from chains.pitch_deck_chain import run_pitch_deck_chain_with_text
from core.visual_utils import extract_images_from_pdf, filter_graphs_and_tables
from core.download_utils import extract_text_from_image
import pdfplumber

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)


def build_deck_agent(pdf_path: str, existing_profile=None, trace_id=None):
    analyst = Agent(
        role="Pitch-deck analyst",
        goal="Extract basic metadata and key insights from a startup pitch deck PDF.",
        backstory=(
            "Former VC analyst who has reviewed 1,000+ decks and knows what matters in first-pass screening. Expert in extracting actionable insights from pitch decks."
        ),
        verbose=True,
        llm=llm,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    # CrewAI passes a TaskOutput object to the callback; we ignore it.
    def _callback(*_) -> str:
        # Use the full text version for better context
        from core.download_utils import extract_text_from_pdf
        full_text = extract_text_from_pdf(pdf_path)
        profile = run_pitch_deck_chain_with_text(full_text, profile=existing_profile, pdf_path=pdf_path)
        # --- Visual enrichment: extract images and run OCR ---
        try:
            image_paths = extract_images_from_pdf(pdf_path, "extraction_cache")
            filtered_images = filter_graphs_and_tables(image_paths)
            ocr_texts = []
            for img_path in filtered_images:
                ocr_result = extract_text_from_image(img_path)
                if ocr_result:
                    ocr_texts.append(ocr_result)
            if ocr_texts:
                profile.figures_ocr = "\n\n".join(ocr_texts)
        except Exception as exc:
            profile.figures_ocr = f"[visual-enrichment error: {exc}]"
        # --- Table extraction: extract tables as text using pdfplumber ---
        tables_text = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        # Convert table to readable string (CSV-like)
                        table_str = "\n".join([", ".join([cell if cell is not None else "" for cell in row]) for row in table])
                        tables_text.append(table_str)
            if tables_text:
                profile.tables_text = "\n\n".join(tables_text)
        except Exception as exc:
            profile.tables_text = f"[table-extraction error: {exc}]"
        return profile.model_dump_json(indent=2)

    task = Task(
        description="Read the PDF and populate the basic StartupProfile fields and key insights.",
        agent=analyst,
        expected_output="JSON-serialised StartupProfile with key insights.",
        async_execution=False,
        callback=_callback,
    )

    return analyst, task


def run_crew(pdf_path: str, trace_id=None) -> str:
    """Run the crew and return the JSON string our callback produced."""
    agent, task = build_deck_agent(pdf_path, trace_id)
    crew = Crew(agents=[agent], tasks=[task])
    return crew.kickoff().raw  # <-- this holds the clean JSON
