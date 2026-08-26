"""Guards on the eCFR verification pass itself.

These exist because the first version of the ruleset cited § 200.474 for travel
costs, which is Transportation costs. A test that only inspects the citations the
seeded transactions happen to render does NOT catch that — no seeded transaction
reaches the travel rule. So these assert against the ruleset directly, and drive a
travel transaction through the engine on purpose.

Every assertion below corresponds to a defect found on 2026-08-26. Each one is a
regression test for a citation that was actually wrong.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grantloop.sentinel import Sentinel, load_ruleset

ROOT = Path(__file__).resolve().parents[1]
SEED = json.loads((ROOT / "seed" / "riverbend_scenario.json").read_text())


@pytest.fixture
def ruleset():
    return load_ruleset()


@pytest.fixture
def sentinel(ruleset):
    return Sentinel(ruleset, SEED["notice_of_award"], SEED["org"])


def test_travel_rule_cites_200_475(ruleset) -> None:
    """§ 200.474 is Transportation costs — goods, not staff travel."""
    rule = ruleset.by_id("R-474-TRAVEL")
    assert rule["section"] == "200.475"
    assert rule["title"] == "Travel costs"


def test_no_rule_anywhere_cites_200_474(ruleset) -> None:
    assert not [r["id"] for r in ruleset.rules if r["section"] == "200.474"]


def test_a_travel_transaction_renders_200_475(sentinel) -> None:
    """Drive the travel path explicitly; the seed never reaches it."""
    txn = {"txn_id": "TXN-T1", "date": "2026-11-05", "vendor": "Delta",
           "memo": "Airfare, program director site visit", "amount": 410.0,
           "attachments": ["boarding_pass.pdf"]}
    sections = {c.section for c in sentinel.classify(txn).citations}
    assert "200.475" in sections
    assert "200.474" not in sections


def test_documentation_rule_cites_403g_not_334(ruleset) -> None:
    """§ 200.334 is retention duration, not the requirement to have a receipt."""
    rule = ruleset.by_id("R-334-RETENTION")
    assert rule["section"] == "200.403"
    assert rule["paragraph"] == "(g)"


def test_civic_memberships_are_not_described_as_prior_approval(ruleset) -> None:
    """200.454(c) makes them allowable outright."""
    note = ruleset.by_id("R-454-MEMB")["note"].lower()
    assert "allowable" in note
    assert "civic and community organization memberships require prior approval" not in note


def test_participant_support_needs_no_prior_approval_to_incur(ruleset) -> None:
    rule = ruleset.by_id("R-456-PSC")
    assert rule["default"] == "presumptively_allowable"
    assert "200.308(f)(5)" in rule["note"]


def test_de_minimis_rate_is_fifteen_percent(ruleset) -> None:
    """Raised from 10% by the 2024 OMB revision. Never hardcode it from memory."""
    rate = ruleset.by_id("R-414-IDC")["de_minimis_rate"]
    assert rate["ceiling_percent"] == 15
    assert rate["base"] == "MTDC"
    assert rate["citation"] == "200.414(f)"
    assert SEED["org"]["indirect_rate"]["rate"] == 0.15


def test_equipment_threshold_is_ten_thousand(ruleset) -> None:
    assert ruleset.by_id("R-439-EQUIP")["special_purpose_prior_approval_threshold_usd"] == 10000


def test_ruleset_is_marked_verified(ruleset) -> None:
    assert ruleset.citations_verified
    assert ruleset.raw["verified_against"]["snapshot_date"] == "2026-08-01"


def test_every_rule_has_a_section_and_title(ruleset) -> None:
    for rule in ruleset.rules:
        assert rule["section"].startswith("200."), rule["id"]
        assert rule["title"].strip(), rule["id"]


def test_every_determination_default_is_in_the_taxonomy(ruleset) -> None:
    values = set(ruleset.determination_values)
    for rule in ruleset.rules:
        assert rule["default"] in values, rule["id"]
        if rule.get("escalate_to"):
            assert rule["escalate_to"] in values, rule["id"]
