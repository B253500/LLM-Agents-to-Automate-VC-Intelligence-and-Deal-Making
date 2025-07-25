from core.schemas import StartupProfile
from core.vector_store import add_doc
from chains.technical_dd_chain import run_technical_dd_chain

# Patch ChatOpenAI.invoke so the test is deterministic and FAST
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage
import pytest


@pytest.fixture(autouse=True)
def _stub_llm(monkeypatch):
    def fake_invoke(self, prompt):
        return AIMessage(
            content='{"tech_maturity":"production","moat_strength":"Proprietary SaaS stack"}'
        )

    monkeypatch.setattr(ChatOpenAI, "invoke", fake_invoke, raising=True)


def test_technical_dd():
    # Minimal profile & fake context
    prof = StartupProfile(startup_id="dummy123", name="DemoCo")
    add_doc(
        "dummy123",
        "Our SaaS is built on Django & PostgreSQL, live in production for 3 years.",
    )

    prof = run_technical_dd_chain(prof)

    assert prof.tech_maturity == "production"
    assert prof.moat_strength.startswith("Proprietary")
