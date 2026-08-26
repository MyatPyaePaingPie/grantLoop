"""Tests for the two places a Google model and framework enter the system.

Both are required by the hackathon rules, but the bar here is higher than "it is
imported": the determination must stay deterministic, and every model path must
degrade to something no worse than the static behaviour it replaced.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grantloop.config import Config, load
from grantloop.sentinel import Sentinel, load_ruleset
from grantloop.sentinel.questions import DraftedQuestion, QuestionDrafter, _usable

ROOT = Path(__file__).resolve().parents[1]
SEED = json.loads((ROOT / "seed" / "riverbend_scenario.json").read_text())
TXNS = {t["txn_id"]: t for t in SEED["ledger_stream"]["transactions"]}


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, text: str | None = None, boom: bool = False) -> None:
        self._text, self._boom = text, boom
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self._boom:
            raise RuntimeError("vertex unavailable")
        return _FakeResponse(self._text)


class _FakeClient:
    def __init__(self, text: str | None = None, boom: bool = False) -> None:
        self.models = _FakeModels(text, boom)


CLOUD = Config(project="demo-project", model_id="gemini-3.5-flash",
               location="global", topic_prefix="grantloop")


def _drafter(client) -> QuestionDrafter:
    return QuestionDrafter(config=CLOUD, client=client)


def test_offline_uses_the_static_question() -> None:
    """No project configured means no model call, and no crash."""
    result = QuestionDrafter(config=load({})).draft(
        txn=TXNS["TXN-007"], rule_title="Memberships", citation="2 CFR 200.454",
        rationale="r", fact="counterparty_primary_purpose_is_lobbying",
        fallback="STATIC?")
    assert result == DraftedQuestion("STATIC?", "fallback")


def test_gemini_draft_is_used_when_it_is_good() -> None:
    client = _FakeClient("Does the Community Chamber Alliance exist primarily to lobby?")
    result = _drafter(client).draft(
        txn=TXNS["TXN-007"], rule_title="Memberships", citation="2 CFR 200.454(e)",
        rationale="r", fact="counterparty_primary_purpose_is_lobbying", fallback="STATIC?")
    assert result.source == "gemini"
    assert result.model_id == "gemini-3.5-flash"
    assert "Chamber" in result.text


def test_the_prompt_carries_the_actual_transaction() -> None:
    """A generic prompt would produce a generic question, which is the thing we are fixing."""
    client = _FakeClient("Is it a lobbying organization?")
    _drafter(client).draft(txn=TXNS["TXN-007"], rule_title="Memberships",
                           citation="2 CFR 200.454(e)", rationale="r",
                           fact="counterparty_primary_purpose_is_lobbying", fallback="STATIC?")
    prompt = client.models.calls[0]["contents"]
    assert "Community Chamber Alliance" in prompt
    assert "500.00" in prompt
    assert "200.454(e)" in prompt


@pytest.mark.parametrize("bad", ["", "   ", "A statement with no question mark.", "x" * 700])
def test_unusable_drafts_fall_back(bad: str) -> None:
    """A bad question in front of a human is worse than the static one."""
    result = _drafter(_FakeClient(bad)).draft(
        txn=TXNS["TXN-007"], rule_title="t", citation="c", rationale="r",
        fact="f", fallback="STATIC?")
    assert result == DraftedQuestion("STATIC?", "fallback")


def test_vertex_failure_never_breaks_a_determination() -> None:
    """Model plumbing must not be able to take down the compliance engine."""
    sentinel = Sentinel(load_ruleset(), SEED["notice_of_award"], SEED["org"],
                        drafter=_drafter(_FakeClient(boom=True)))
    determination = sentinel.classify(TXNS["TXN-007"])
    assert determination.determination == "requires_human_determination"
    assert determination.question_source == "fallback"
    assert "lobbying" in determination.question_for_human


def test_the_model_never_changes_the_determination() -> None:
    """The whole design rests on this: Gemini writes prose, not verdicts."""
    ruleset, noa, org = load_ruleset(), SEED["notice_of_award"], SEED["org"]
    static = Sentinel(ruleset, noa, org)
    drafted = Sentinel(ruleset, noa, org,
                       drafter=_drafter(_FakeClient("Totally different question?")))
    for txn in TXNS.values():
        a, b = static.classify(txn), drafted.classify(txn)
        assert a.determination == b.determination
        assert [c.label for c in a.citations] == [c.label for c in b.citations]
        assert [s.amount for s in a.splits] == [s.amount for s in b.splits]


def test_determination_records_where_its_question_came_from(model_source: str = "fallback") -> None:
    sentinel = Sentinel(load_ruleset(), SEED["notice_of_award"], SEED["org"])
    assert sentinel.classify(TXNS["TXN-007"]).to_dict()["question_source"] == model_source


# ---- ADK tool surface ----------------------------------------------------


def test_adk_tools_are_deterministic_and_cited() -> None:
    from grantloop.adk import TOOLS
    from grantloop.adk.fleet import classify_transaction, lookup_allowability_rule

    assert len(TOOLS) == 3
    first = classify_transaction("TXN-005")
    assert first == classify_transaction("TXN-005")
    assert first["determination"] == "conflicts_with_award_terms"
    assert first["citations"]

    rules = lookup_allowability_rule("wine")
    assert rules["citations_verified"] is True
    assert rules["matches"][0]["section"] == "200.423"


def test_every_adk_tool_documents_itself_for_the_model() -> None:
    """ADK turns the docstring into the tool declaration the model reads."""
    from grantloop.adk import TOOLS

    for tool in TOOLS:
        assert tool.__doc__ and len(tool.__doc__.strip()) > 120, tool.__name__
        assert "Returns:" in tool.__doc__, tool.__name__


def test_unknown_transaction_is_an_error_not_a_guess() -> None:
    from grantloop.adk.fleet import classify_transaction

    assert "error" in classify_transaction("TXN-NOPE")


def test_agent_instructions_forbid_self_answering() -> None:
    """The instructions are load-bearing: they are what stops the model improvising."""
    from grantloop.adk.fleet import COVENANT_INSTRUCTION, SENTINEL_INSTRUCTION

    assert "do not decide allowability yourself" in SENTINEL_INSTRUCTION.lower()
    assert "silence is never approval" in SENTINEL_INSTRUCTION.lower()
    assert "never state a dollar figure the tool did not return" in COVENANT_INSTRUCTION.lower()


def test_default_vertex_location_is_global() -> None:
    """Gemini 3.x is served from `global` only.

    Every regional endpoint returns 404 for gemini-3.5-flash, and a 404 on a
    publisher model reads like an auth failure while being nothing of the kind.
    Verified directly against the project on 2026-08-26: global 200, us-central1 404.
    This default cost the team a day the first time around.
    """
    assert load({}).location == "global"
    assert load({"GOOGLE_CLOUD_LOCATION": "europe-west4"}).location == "europe-west4"
