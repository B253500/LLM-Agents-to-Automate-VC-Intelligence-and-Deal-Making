from core.schemas import StartupProfile
from core.vector_store import add_doc
from chains.market_sizing_chain import run_market_sizing_chain

from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage
import pytest


@pytest.fixture(autouse=True)
def _stub_llm(monkeypatch):
    def fake_invoke(self, prompt):
        return AIMessage(content='{"TAM":5000,"SAM":800,"SOM":50}')

    monkeypatch.setattr(ChatOpenAI, "invoke", fake_invoke, raising=True)


def test_market_sizing():
    prof = StartupProfile(startup_id="market1", name="Beta")
    add_doc("market1", "We address a rapidly growing $5 billion global market.")

    prof = run_market_sizing_chain(prof)

    assert prof.TAM == 5000
    assert prof.SAM == 800
    assert prof.SOM == 50
