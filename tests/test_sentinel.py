"""Acceptance test for the Ledger Sentinel.

The bar: every seeded transaction lands on the determination the demo script
promises, and all seven values fire exactly once. If this passes, beat 3 of the
demo is real rather than narrated.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grantloop.sentinel import Sentinel, load_ruleset

ROOT = Path(__file__).resolve().parents[1]
SEED = json.loads((ROOT / "seed" / "riverbend_scenario.json").read_text())
TXNS = {t["txn_id"]: t for t in SEED["ledger_stream"]["transactions"]}


@pytest.fixture
def sentinel() -> Sentinel:
    return Sentinel(load_ruleset(), SEED["notice_of_award"], SEED["org"])


@pytest.mark.parametrize("txn_id", sorted(TXNS))
def test_matches_seeded_expectation(sentinel: Sentinel, txn_id: str) -> None:
    txn = TXNS[txn_id]
    expected = txn.get("expected_determination")
    if expected is None:
        pytest.skip(f"{txn_id} is a split case, covered by test_alcohol_split")
    assert sentinel.classify(txn).determination == expected


def test_all_seven_determinations_fire(sentinel: Sentinel) -> None:
    """The seed exists to make each of the seven values visible exactly once.

    This is the acceptance bar for demo beat 3: seven transactions, seven visibly
    different behaviors, no value fired twice and none missing.
    """
    got = [sentinel.classify(t).determination for t in TXNS.values()]
    values = set(load_ruleset().determination_values)
    assert set(got) == values, f"missing {values - set(got)}, extra {set(got) - values}"
    assert len(got) == len(set(got)) == 7, got


def test_alcohol_split_carves_out_the_alcohol(sentinel: Sentinel) -> None:
    d = sentinel.classify(TXNS["TXN-002"])
    unallowable = [s for s in d.splits if s.determination == "presumptively_unallowable"]
    assert sum(s.amount for s in unallowable) == 412.00
    assert any("200.423" in c.section for s in unallowable for c in s.citations)
    # The remainder must NOT be auto-approved.
    remainder = [s for s in d.splits if s.determination != "presumptively_unallowable"]
    assert remainder and all(s.determination == "requires_human_determination" for s in remainder)
    assert sum(s.amount for s in d.splits) == TXNS["TXN-002"]["amount"]


def test_laptop_block_cites_the_award_term_not_just_the_cfr(sentinel: Sentinel) -> None:
    """The regulation permits this purchase. Only SC-2 forbids it."""
    d = sentinel.classify(TXNS["TXN-005"])
    assert d.determination == "conflicts_with_award_terms"
    assert d.award_term == "SC-2"
    assert "200.453" in {c.section for c in d.citations}


def test_travel_cites_200_475_never_200_474(sentinel: Sentinel) -> None:
    """200.474 is Transportation costs. Citing it for staff travel is the bug we fixed."""
    for txn in TXNS.values():
        d = sentinel.classify(txn)
        sections = {c.section for c in d.citations} | {
            c.section for s in d.splits for c in s.citations
        }
        assert "200.474" not in sections, f"{txn['txn_id']} cites Transportation costs for travel"


def test_missing_receipt_is_not_a_finding_of_unallowability(sentinel: Sentinel) -> None:
    d = sentinel.classify(TXNS["TXN-003"])
    assert d.determination == "missing_documentation"
    assert {c.section for c in d.citations} == {"200.403"}
    assert d.citations[0].paragraph == "(g)"


def test_chamber_dues_escalate_with_a_named_question(sentinel: Sentinel) -> None:
    d = sentinel.classify(TXNS["TXN-007"])
    assert d.escalated
    assert d.question_for_human and "lobbying" in d.question_for_human
    assert len(d.options) == 3


def test_unmatched_cost_never_defaults_to_allowable(sentinel: Sentinel) -> None:
    mystery = {"txn_id": "TXN-999", "date": "2026-11-01", "vendor": "Unknown Co",
               "memo": "qwertyuiop zxcvbnm", "amount": 100.0, "attachments": ["r.pdf"]}
    assert sentinel.classify(mystery).determination == "requires_human_determination"


def test_citations_are_verified(sentinel: Sentinel) -> None:
    assert load_ruleset().citations_verified
