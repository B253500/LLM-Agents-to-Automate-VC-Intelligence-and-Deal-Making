# agents/deck_agent.py
"""
CrewAI wrapper around the LangChain pitch-deck chain.  
Each call:

1.  Re-hydrates the incoming profile-dict.
2.  Runs the text-based pitch-deck extractor.
3.  (Optionally) enriches the profile with information from graphs / tables.
4.  Returns an updated profile-dict.

No other task needs anything except that single dictionary.
"""

from __future__ import annotations
import os
import tempfile
from typing import Tuple, Dict, Any
from collections.abc import Mapping
import json

from crewai import Agent, Task
from langchain_openai import ChatOpenAI

from core.schemas import StartupProfile
from core.visual_utils import extract_images_from_pdf
from core.download_utils import extract_text_from_image

# ――― LLM used by the agent ―――
_llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

# ――― optional Google Vision helper ―――
try:
    from google.cloud import vision

    def filter_graphs_and_tables(image_paths: list[str]) -> list[str]:
        """
        Run Google Vision label detection and keep only tables/charts/graphs/diagrams.
        """
        client = vision.ImageAnnotatorClient()
        wanted = {"table", "chart", "graph", "diagram", "plot"}
        keep: list[str] = []
        for p in image_paths:
            with open(p, "rb") as f:
                img = vision.Image(content=f.read())
            labels = {l.description.lower() for l in client.label_detection(image=img).label_annotations}
            if labels & wanted:
                keep.append(p)
        return keep

except ImportError:
    # Fallback: no filtering if Vision API isn't available
    def filter_graphs_and_tables(image_paths: list[str]) -> list[str]:
        return image_paths


def build_deck_agent(deck_payload: Dict[str, Any]) -> Tuple[Agent, Task]:
    """
    Parameters
    ----------
    deck_payload : dict
        {
          "text": str,
          "tables": list,
          "figures": list,
          "file_path": str
        }
    """

    analyst = Agent(
        role="Pitch-deck analyst",
        goal="Extract key facts and visuals from a startup’s pitch-deck PDF.",
        backstory=(
            "A former VC analyst who has reviewed more than a thousand decks; "
            "knows exactly which slides hide the crucial information."
        ),
        llm=_llm,
        verbose=True,
        allow_delegation=False,   # keep it simple – no sub-agents
        max_iter=12,
        max_execution_time=180,
    )

    def _callback(profile_dict: Dict[str, Any],
                  _payload: Dict[str, Any] = deck_payload) -> Dict[str, Any]:
        # In hierarchical mode, ignore incoming profile_dict and start fresh
        profile = StartupProfile()
        # --- 1  basic text extraction using LLM ----------
        print("Extracted text being sent to LLM for extraction:", _payload["text"][:500])
        prompt = f"""
You are a VC analyst. Extract the following fields from the pitch deck text below and respond ONLY with a valid JSON object with these keys:
- company_name
- sector
- founders
- product_description
- market_size
- key_financials
- competitors
- business_model
- esg_considerations
- risks
- exit_strategy

If a field is missing, use an empty string or null. 
Respond ONLY with a valid JSON object. Do NOT include any explanation, commentary, or markdown. The first character of your response must be '{{'.

Pitch deck text:
{_payload['text']}
"""
        result = _llm.invoke(prompt)
        raw = result.content.strip()
        # Remove Markdown code block if present
        if raw.startswith("```"):
            lines = raw.splitlines()
            # Remove the first line (``` or ```json)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove the last line if it's ```
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw = "\n".join(lines).strip()
        print(f"[Deck Agent] Cleaned JSON string to parse:\n{raw}")
        try:
            extracted = json.loads(raw)
            # Map LLM keys to model keys for compatibility
            if "company_name" in extracted:
                extracted["name"] = extracted.pop("company_name")
            if "founders" in extracted:
                extracted["founder_name"] = extracted.pop("founders")
            for k, v in extracted.items():
                if hasattr(profile, k) and v:
                    setattr(profile, k, v)
        except Exception as e:
            print(f"[Deck Agent] LLM extraction failed: {e}")
            print(f"[Deck Agent] Raw LLM output:\n{result.content}")
        # --- 2  optional visual enrichment -----------------------------
        try:
            # extract images once – they’re cached on disk by the util
            all_imgs = extract_images_from_pdf(_payload["file_path"], "extraction_cache")
            graph_imgs = filter_graphs_and_tables(all_imgs)
            # very naïve OCR of each kept image → append to profile.figures_ocr
            ocr_texts = []
            for img in graph_imgs:
                ocr_texts.append(extract_text_from_image(img))
            if ocr_texts:
                profile.figures_ocr = "\n\n".join(ocr_texts)
        except Exception as exc:  # never fail the whole run because of OCR
            profile.figures_ocr = f"[visual-enrichment error: {exc}]"
        output = profile.model_dump()
        print(f"[Deck Agent] Output type: {type(output)}")
        print(f"[Deck Agent] Output keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
        return output

    task = Task(
        description=(
            "Read the PDF’s raw text + images, extract company/market/product "
            "facts, and enrich the StartupProfile."
        ),
        agent=analyst,
        callback=_callback,
        expected_output="Updated StartupProfile as a dict",
    )

    return analyst, task
