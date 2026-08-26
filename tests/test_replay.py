"""Acceptance tests for the deterministic replay path.

This is the record-day fallback, so its bar is higher than "it runs": the same
seed must produce byte-identical output, it must never touch the network, and the
failure path must be demonstrable on command.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from grantloop.config import load
from grantloop.replay import Replay


def _digest(replay: Replay) -> str:
    replay.run()
    return hashlib.sha256(json.dumps(replay.api_state(), sort_keys=True).encode()).hexdigest()


def test_replay_is_byte_identical_across_runs() -> None:
    """Including causation ids — provenance must reproduce, not just payloads."""
    assert _digest(Replay()) == _digest(Replay())


def test_every_transaction_produces_a_determination() -> None:
    result = Replay().run()
    txns = len(Replay().seed["ledger_stream"]["transactions"])
    assert len(result.determinations) == txns


def test_events_carry_the_provenance_chain() -> None:
    replay = Replay()
    replay.run()
    posted = {e["event_id"]: e for e in replay.result.events
              if e["event_type"] == "transaction.posted"}
    downstream = [e for e in replay.result.events if e["event_type"].startswith("determination.")]
    assert downstream, "no determinations were emitted"
    for event in downstream:
        assert event["causation_id"] in posted, "determination lost its causing event"
        assert event["correlation_id"] == posted[event["causation_id"]]["correlation_id"]


def test_dlq_populates_on_forced_failure() -> None:
    """Failure handling has to be demonstrable on camera, not just implemented."""
    result = Replay(fail_txn="TXN-004").run()
    assert len(result.dead_letters) == 1
    entry = result.dead_letters[0]
    assert entry["txn_ref"] == "TXN-004"
    assert entry["attempts"] == 5
    assert "RuntimeError" in entry["last_error"]
    # The rest of the stream must survive one poisoned message.
    assert len(result.determinations) == 6


def test_replay_needs_no_cloud_project() -> None:
    assert load({}).offline is True
    Replay().run()  # would raise if anything reached for a client


def test_api_state_matches_the_dashboard_contract() -> None:
    """Shapes agreed in dashboard/READ_API_PROPOSAL.md."""
    replay = Replay()
    replay.run()
    state = replay.api_state()
    assert set(state) == {"health", "award", "ledger", "exceptions"}
    assert state["health"]["citations_verified"] is True
    assert state["ledger"]["citations_verified"] is True
    assert state["award"]["deltas"] and state["award"]["specific_conditions"]
    for txn in state["ledger"]["transactions"]:
        assert {"txn_id", "determination", "citations", "rationale"} <= set(txn)
        for citation in txn["citations"]:
            assert citation["label"].startswith("2 CFR ")


def test_no_unverified_citation_can_render() -> None:
    replay = Replay()
    replay.run()
    for txn in replay.result.determinations:
        for citation in txn["citations"]:
            assert citation["section"].startswith("200."), citation
            assert citation["title"], f"{citation['label']} has no title to show"


@pytest.mark.parametrize("argv", [[], ["--plain"], ["--json"], ["--dlq", "TXN-004", "--plain"]])
def test_cli_exits_clean(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    from grantloop.replay.__main__ import main

    assert main(argv) == 0
    assert capsys.readouterr().out.strip()


def test_redelivery_changes_nothing() -> None:
    """Pub/Sub is at-least-once. Every handler must be exactly-once in effect.

    Without this, disabling the idempotency check in the bus passes the entire
    suite — replay publishes each transaction once, so the guarantee is never
    exercised. Found by deliberately breaking the bus on 2026-08-26.
    """
    once = Replay().run()
    twice = Replay(redeliver=True).run()
    assert len(twice.determinations) == len(once.determinations)
    assert [d["txn_id"] for d in twice.determinations] == [d["txn_id"] for d in once.determinations]
    assert twice.summary()["determinations_by_value"] == once.summary()["determinations_by_value"]


def test_redelivery_does_not_duplicate_downstream_events() -> None:
    twice = Replay(redeliver=True).run()
    emitted = [e for e in twice.events if e["event_type"].startswith("determination.")]
    assert len(emitted) == len({e["event_id"] for e in emitted})


def test_ledger_rows_carry_the_money_and_the_verdict() -> None:
    """The dashboard renders amount and vendor beside the determination.

    A bare determination record would render a row with no money in it, which is
    how live mode would have silently differed from seed mode on record day.
    """
    replay = Replay()
    replay.run()
    rows = replay.api_state()["ledger"]["transactions"]
    for row in rows:
        assert {"txn_id", "vendor", "amount", "date", "determination", "citations"} <= set(row)
        assert isinstance(row["amount"], (int, float))
        # Seed-only expectation fields must never reach the API: live mode has no
        # "expected" anything, and leaking them would let the UI render a promise
        # instead of a result.
        assert not [k for k in row if k.startswith("expected_")]


def test_split_amounts_reconcile_to_the_transaction() -> None:
    replay = Replay()
    replay.run()
    for row in replay.api_state()["ledger"]["transactions"]:
        if row.get("splits"):
            assert round(sum(s["amount"] for s in row["splits"]), 2) == round(row["amount"], 2)
