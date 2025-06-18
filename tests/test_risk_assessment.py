from core.schemas import StartupProfile
from chains.risk_assessment_chain import run_risk_assessment_chain

from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage
import pytest


@pytest.fixture(autouse=True)
def _stub_llm(monkeypatch):
    def fake_invoke(self, prompt):
        return AIMessage(content='{"risk_flags":["single founder"],"risk_score":0.7}')

    monkeypatch.setattr(ChatOpenAI, "invoke", fake_invoke, raising=True)


def test_risk_assessment():
    prof = StartupProfile(startup_id="risk1", name="Epsilon")
    prof = run_risk_assessment_chain(prof)
    assert prof.risk_flags == ["single founder"]
    assert prof.risk_score == 0.7
