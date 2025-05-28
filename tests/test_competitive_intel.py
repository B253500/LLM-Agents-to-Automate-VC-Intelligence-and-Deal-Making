from core.schemas import StartupProfile
from core.vector_store import add_doc
from chains.competitive_intel_chain import run_competitive_intel_chain

from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage
import pytest


@pytest.fixture(autouse=True)
def _stub_llm(monkeypatch):
    def fake_invoke(self, prompt):
        return AIMessage(
            content='{"top_competitors":[{"name":"RivalCo","differentiator":"Legacy vendor"},{"name":"AltCorp","differentiator":"Cheaper"}]}'
        )

    monkeypatch.setattr(ChatOpenAI, "invoke", fake_invoke, raising=True)


def test_competitive_intel():
    prof = StartupProfile(startup_id="comp1", name="Delta")
    add_doc("comp1", "Competes with RivalCo and AltCorp in workflow SaaS.")
    prof = run_competitive_intel_chain(prof)

    assert prof.top_competitors[0].name == "RivalCo"
