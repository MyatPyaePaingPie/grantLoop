"""Acceptance tests for the Covenant Agent — the award handoff.

The bar is that every finding is DERIVED. If any assertion here could be satisfied
by reading AWARD_DELTAS_TO_SURFACE out of the seed, the demo's centrepiece is a
hand-written string and the test is worthless.

`AWARD_DELTAS_TO_SURFACE` is used here only as an expected-output fixture: the
agent must independently reach the same conclusions the demo script promises.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grantloop.covenant import Covenant

ROOT = Path(__file__).resolve().parents[1]
SEED = json.loads((ROOT / "seed" / "riverbend_scenario.json").read_text())
SCRIPTED = {d["obligation_ref"]: d for d in SEED["notice_of_award"]["AWARD_DELTAS_TO_SURFACE"]}


@pytest.fixture
def model():
    return Covenant(SEED["application"], SEED["notice_of_award"]).build()


@pytest.mark.parametrize("ref", sorted(SCRIPTED))
def test_derived_deltas_match_the_demo_script(model, ref: str) -> None:
    """Every scripted beat must be reached from the documents, not read from the list."""
    expected = SCRIPTED[ref]
    got = next(d for d in model.deltas if d.obligation_ref == ref)
    assert got.status == expected["status"]
    assert got.proposed_value == expected["proposed_value"]
    assert got.awarded_value == expected["awarded_value"]


def test_the_headline_is_found_not_narrated(model) -> None:
    """The money shot: money cut, promise kept, discovered by the agent."""
    headline = model.headline
    assert headline is not None
    assert headline["budget_line"] == "BL-04"
    assert headline["promise"] == "PP-1"
    assert headline["severity"] == "critical"
    assert "40%" in headline["summary"]
    assert headline["options"]


def test_underfunded_promise_also_caught_for_convenings(model) -> None:
    """BL-07 cut 33% while PP-3 stayed at 4 convenings. Same failure, second instance."""
    findings = [e for e in model.exceptions if e["kind"] == "underfunded_promise"]
    assert {f["budget_line"] for f in findings} == {"BL-04", "BL-07"}


def test_award_total_mismatch_is_raised_not_absorbed(model) -> None:
    """The NOA states $212,000; its own lines sum to $234,000. Trusting the headline hides it."""
    mismatch = next(e for e in model.exceptions if e["kind"] == "award_total_mismatch")
    assert mismatch["severity"] == "critical"
    assert "212,000" in mismatch["summary"] and "234,000" in mismatch["summary"]


def test_participant_support_cut_names_the_prior_approval_rule(model) -> None:
    """Moving funds out of participant support needs prior approval — 200.308(f)(5)."""
    delta = next(d for d in model.deltas if d.obligation_ref == "BL-04")
    assert "200.308(f)(5)" in delta.downstream_effect


def test_conditioned_line_tells_the_sentinel_what_to_block(model) -> None:
    delta = next(d for d in model.deltas if d.obligation_ref == "BL-08")
    assert delta.status == "condition_attached"
    assert "SC-2" in delta.downstream_effect
    obligation = next(o for o in model.obligations if o.obligation_id == "BL-08")
    assert obligation.conditions == ["SC-2"]


def test_every_budget_line_and_promise_becomes_an_obligation(model) -> None:
    lines = len(SEED["notice_of_award"]["awarded_budget_lines"])
    promises = len(SEED["notice_of_award"]["awarded_performance_targets"])
    assert len(model.obligations) == lines + promises


def test_unchanged_lines_produce_no_delta_noise(model) -> None:
    """Only genuine changes surface; a 10-line budget must not yield 10 deltas."""
    budget_deltas = [d for d in model.deltas if d.obligation_ref.startswith("BL-")]
    assert len(budget_deltas) == 3, [d.obligation_ref for d in budget_deltas]


def test_a_promise_reduced_alongside_its_funding_is_not_flagged() -> None:
    """The finding is money-cut-promise-kept. Cutting both together is legitimate."""
    noa = json.loads(json.dumps(SEED["notice_of_award"]))
    for line in noa["awarded_budget_lines"]:
        if line["line_id"] == "BL-04":
            line["amount"] = 18000
    for target in noa["awarded_performance_targets"]:
        if target["id"] == "PP-1":
            target["target"] = 72          # agency cut the target too
    model = Covenant(SEED["application"], noa).build()
    flagged = {e["promise"] for e in model.exceptions if e["kind"] == "underfunded_promise"}
    assert "PP-1" not in flagged


def test_removed_line_is_critical() -> None:
    noa = json.loads(json.dumps(SEED["notice_of_award"]))
    noa["awarded_budget_lines"] = [l for l in noa["awarded_budget_lines"]
                                   if l["line_id"] != "BL-06"]
    model = Covenant(SEED["application"], noa).build()
    delta = next(d for d in model.deltas if d.obligation_ref == "BL-06")
    assert delta.status == "removed" and delta.severity == "critical"


def test_api_serves_derived_deltas_not_the_seed_list() -> None:
    """If the API ever falls back to the seed list, this fails."""
    from grantloop.api.routes import Orchestrator

    award = Orchestrator().award()
    assert award["headline"] is not None
    assert award["exceptions"]
    for delta in award["deltas"]:
        assert "delta" in delta and "severity" in delta  # fields the seed list lacks
