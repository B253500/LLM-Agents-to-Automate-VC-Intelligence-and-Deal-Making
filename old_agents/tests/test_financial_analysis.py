from core.schemas import StartupProfile
from core.vector_store import add_doc
from chains.financial_analysis_chain import run_financial_analysis_chain

from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage
import pytest


@pytest.fixture(autouse=True)
def _stub_llm(monkeypatch):
    """Stub GPT call so the test runs offline & deterministically."""

    def fake_invoke(self, prompt):
        return AIMessage(
            content='{"cash_burn_12m": 4.2, "runway_months": 14, "implied_valuation": 28}'
        )

    monkeypatch.setattr(ChatOpenAI, "invoke", fake_invoke, raising=True)


def test_financial_analysis():
    prof = StartupProfile(startup_id="fin1", name="Gamma")
    add_doc(
        "fin1",
        "We burn $350k per month with $5M in the bank. Raised $7M for 25% equity.",
    )

    prof = run_financial_analysis_chain(prof)

    assert prof.cash_burn_12m == 4.2  # 0.35 * 12
    assert prof.runway_months == 14
    assert prof.implied_valuation == 28
