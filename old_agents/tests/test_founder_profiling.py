from core.schemas import StartupProfile
from core.vector_store import add_doc
from chains.founder_profiling_chain import run_founder_profiling_chain

from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage
import pytest


@pytest.fixture(autouse=True)
def _stub_llm(monkeypatch):
    def fake_invoke(self, prompt):
        return AIMessage(content='{"founder_fit_score":0.85,"prior_exits":2}')

    monkeypatch.setattr(ChatOpenAI, "invoke", fake_invoke, raising=True)


def test_founder_profiling():
    prof = StartupProfile(startup_id="founder1", name="Alpha")
    add_doc("founder1", "CEO exited two startups; CTO is ex-Google.")

    prof = run_founder_profiling_chain(prof)

    assert prof.founder_fit_score == 0.85
    assert prof.prior_exits == 2
