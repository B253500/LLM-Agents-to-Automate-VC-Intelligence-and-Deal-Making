"""
CrewAI wrapper that hands off the heavy work to the LangChain pitch-deck chain.
Only the callback's return value is surfaced to the caller.
"""

from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from chains.pitch_deck_chain import run_pitch_deck_chain
from core.visual_utils import extract_images_from_pdf
from core.download_utils import extract_text_from_image
from google.cloud import vision
import os
import tempfile
import json

llm = ChatOpenAI(model="gpt-4", temperature=0.2)

# Helper: filter images for graphs/tables using Vision API label detection
def filter_graphs_and_tables(image_paths):
    client = vision.ImageAnnotatorClient()
    relevant_labels = {"table", "chart", "graph", "diagram", "plot"}
    selected = []
    for img_path in image_paths:
        with open(img_path, "rb") as image_file:
            content = image_file.read()
        image = vision.Image(content=content)
        response = client.label_detection(image=image)
        labels = response.label_annotations
        if any(label.description.lower() in relevant_labels for label in labels):
            selected.append(img_path)
    return selected


def build_deck_agent(pdf_path: str, trace_id=None):
    analyst = Agent(
        role="Pitch-deck analyst",
        goal="Extract basic metadata and key insights from a startup pitch deck PDF, including visual enrichment.",
        backstory=(
            "Former VC analyst who has reviewed 1,000+ decks and knows what matters in first-pass screening. Expert in extracting actionable insights from pitch decks, including visuals."
        ),
        verbose=True,
        llm=llm,
        allow_delegation=True,
        max_iter=25,
        max_execution_time=300
    )

    def _callback(*_):
        # 1. Run the pitch deck chain (text extraction and field extraction)
        profile = run_pitch_deck_chain(pdf_path)

        # 2. Extract images from PDF to a temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            image_paths = extract_images_from_pdf(pdf_path, tmpdir)
            # 3. Filter for graphs/tables using Vision API label detection
            filtered_images = filter_graphs_and_tables(image_paths)
            # 4. Run OCR/table extraction on filtered images
            ocr_results = []
            for img_path in filtered_images:
                ocr_text = extract_text_from_image(img_path)
                ocr_results.append({"image": img_path, "text": ocr_text})
            # 5. Optionally, parse/merge results into profile (simple append for now)
            if ocr_results:
                if not hasattr(profile, "visual_enrichment"):
                    profile.visual_enrichment = []
                profile.visual_enrichment.extend(ocr_results)
            # 6. Attach filtered image paths for later use in memo
            profile.extracted_image_paths = filtered_images
        return profile.model_dump_json(indent=2)

    task = Task(
        description="Read the PDF, extract key fields, and enrich with data from graphs/tables using Vision API.",
        agent=analyst,
        expected_output="JSON-serialised StartupProfile with key insights and visual enrichment.",
        async_execution=False,
        callback=_callback,
    )

    return analyst, task


def build_pitch_deck_chain_agent(profile, file_path):
    def chain_callback(*_):
        from chains.pitch_deck_chain import run_pitch_deck_chain
        updated_profile = run_pitch_deck_chain(file_path)
        return updated_profile.model_dump()
    agent = Agent(
        role="Pitch Deck Extractor",
        goal="Extract fields from the pitch deck PDF.",
        backstory="A specialized agent for extracting structured data from pitch decks.",
        verbose=True
    )
    task = Task(
        description="Extract fields from pitch deck PDF.",
        agent=agent,
        callback=chain_callback,
        args=[profile.model_dump()],
        expected_output="Profile with deck fields extracted."
    )
    return agent, task


def run_crew(pdf_path: str, trace_id=None) -> str:
    """Run the crew and return the JSON string our callback produced."""
    agent, task = build_deck_agent(pdf_path, trace_id)
    crew = Crew(agents=[agent], tasks=[task])
    return crew.kickoff().raw  # < to hold the clean JSON
