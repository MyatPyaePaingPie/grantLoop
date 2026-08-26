"""Deterministic replay of the seeded scenario.

This is the record-day insurance. It fires the seeded ledger through the real
event contract and the real Sentinel, so what appears on screen is a genuine
determination rather than a fixture — but it never touches the network, so it
cannot fail because of a stalled bus, a cold start, or a model outage.

Determinism is a hard requirement: the same seed produces byte-identical output
every run. Nothing here reads the clock for anything that lands in the output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..events import Event, LocalBus, new_event
from ..events.envelope import deterministic_ids
from ..covenant import Covenant
from ..sentinel import Sentinel, load_ruleset

from ..paths import SCENARIO as DEFAULT_SEED


@dataclass
class ReplayResult:
    determinations: list[dict[str, Any]] = field(default_factory=list)
    escalations: list[dict[str, Any]] = field(default_factory=list)
    dead_letters: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        by_value: dict[str, int] = {}
        for d in self.determinations:
            by_value[d["determination"]] = by_value.get(d["determination"], 0) + 1
        return {
            "transactions": len(self.determinations),
            "events": len(self.events),
            "escalations": len(self.escalations),
            "dead_letters": len(self.dead_letters),
            "determinations_by_value": dict(sorted(by_value.items())),
        }


class Replay:
    def __init__(self, seed_path: str | Path | None = None, *,
                 fail_txn: str | None = None, redeliver: bool = False) -> None:
        """Configure the two demonstrable failure modes.

        `fail_txn` forces one handler to throw, to populate the DLQ on screen.
        `redeliver` publishes every event twice, simulating Pub/Sub at-least-once
        delivery. Output must be identical either way — that is what makes the
        idempotency claim in the event contract a demonstration rather than an
        assertion.
        """
        self.seed = json.loads(Path(seed_path or DEFAULT_SEED).read_text())
        self.ruleset = load_ruleset()
        self.sentinel = Sentinel(self.ruleset, self.seed["notice_of_award"], self.seed["org"])
        self.covenant = Covenant(self.seed["application"], self.seed["notice_of_award"])
        self.obligation_model = self.covenant.build()
        self.fail_txn = fail_txn
        self.redeliver = redeliver
        deterministic_ids(True)  # same seed in, same causation chain out
        self.bus = LocalBus()
        self.result = ReplayResult()
        self._txns: dict[str, dict[str, Any]] = {}
        self._wire()

    def _wire(self) -> None:
        self.bus.subscribe("transaction.posted", self._on_transaction, name="ledger_sentinel")

    def _on_transaction(self, event: Event) -> list[Event]:
        txn = event.payload
        self._txns[txn["txn_id"]] = txn
        if self.fail_txn and txn["txn_id"] == self.fail_txn:
            raise RuntimeError(
                f"simulated handler failure on {txn['txn_id']} — exercising retry and DLQ"
            )
        determination = self.sentinel.classify(txn)
        record = determination.to_dict()
        record["causation_id"] = event.event_id
        self.result.determinations.append(record)

        emitted = event.caused(
            "determination.escalated" if determination.escalated else "determination.made",
            record,
            actor_id="ledger_sentinel",
            natural_key=txn["txn_id"],
        )
        if determination.escalated:
            self.result.escalations.append(record)
        return [emitted]

    def run(self, *, on_event: Callable[[dict[str, Any]], None] | None = None) -> ReplayResult:
        org_id = self.seed["org"]["org_id"]
        award_id = self.seed["notice_of_award"]["award_id"]
        for txn in self.seed["ledger_stream"]["transactions"]:
            event = new_event(
                event_type="transaction.posted",
                org_id=org_id,
                award_id=award_id,
                payload=txn,
                actor_id="ledger_feed_simulated",
                actor_type="system",
                natural_key=txn["txn_id"],
            )
            self.bus.publish(event)
            if self.redeliver:
                self.bus.publish(event)  # at-least-once: must be a no-op
            if on_event:
                on_event(event.to_dict())
        self.result.events = [e.to_dict() for e in self.bus.log]
        self.result.dead_letters = [d.to_dict() for d in self.bus.dead_letters]
        return self.result

    def _ledger_row(self, determination: dict[str, Any]) -> dict[str, Any]:
        """Merge the transaction with its determination.

        The dashboard renders amount, vendor and memo alongside the verdict, so the
        API must return the transaction fields too — a bare determination record
        would render a row with no money in it. Per READ_API_PROPOSAL.md this is the
        seed shape with `determination` replacing `expected_determination`.
        """
        txn = dict(self._txns.get(determination["txn_id"], {}))
        for key in ("expected_determination", "expected_behavior",
                    "expected_citations", "citation_note", "note"):
            txn.pop(key, None)
        txn.update(determination)
        return txn

    def api_state(self) -> dict[str, Any]:
        """The seed-shaped payloads from dashboard/READ_API_PROPOSAL.md.

        Live mode must return these same shapes, so the dashboard switches between
        replay and cloud with a base-URL swap and no rendering changes.
        """
        noa = self.seed["notice_of_award"]
        return {
            "health": {
                "status": "ok",
                "mode": "replay",
                "ruleset_version": self.ruleset.version,
                "citations_verified": self.ruleset.citations_verified,
            },
            "award": {
                "award_id": noa["award_id"],
                "period_of_performance": noa["period_of_performance"],
                # Derived by the Covenant Agent, not read from the seed. The seed's
                # AWARD_DELTAS_TO_SURFACE is now a test fixture, not an input.
                "deltas": [d.to_dict() for d in self.obligation_model.deltas],
                "obligations": [o.to_dict() for o in self.obligation_model.obligations],
                "exceptions": self.obligation_model.exceptions,
                "headline": self.obligation_model.headline,
                "specific_conditions": noa["specific_conditions"],
                "citations_verified": self.ruleset.citations_verified,
            },
            "ledger": {
                "transactions": [self._ledger_row(d) for d in self.result.determinations],
                "citations_verified": self.ruleset.citations_verified,
            },
            "exceptions": {"items": self.result.dead_letters},
        }
