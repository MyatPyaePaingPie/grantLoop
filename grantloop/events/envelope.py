"""The event envelope from schema/EVENT_CONTRACT.md.

Two properties matter and both are load-bearing for the demo:

* `idempotency_key` is derived, never random, so replaying the same event twice is
  a no-op rather than a double-count.
* `causation_id` / `correlation_id` carry the provenance chain. Every downstream
  fact can be walked back to the event that caused it, which is the entire product
  thesis rendered as a data structure.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


#: Namespace for deterministic event ids. Replay derives ids from the idempotency
#: key so the same seed reproduces the same causation chain byte for byte — without
#: it "deterministic replay" only holds for payloads, not for provenance.
GRANTLOOP_NS = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

_DETERMINISTIC = False


def deterministic_ids(enabled: bool = True) -> None:
    """Derive event ids from content instead of randomness. Used by replay."""
    global _DETERMINISTIC
    _DETERMINISTIC = enabled


def _utc(ts: datetime | None = None) -> str:
    return (ts or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def idempotency_key(org_id: str, event_type: str, natural_key: str) -> str:
    """sha256(org_id|event_type|natural_key), per the event contract."""
    raw = f"{org_id}|{event_type}|{natural_key}".encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass
class Event:
    event_type: str
    org_id: str
    award_id: str
    payload: dict[str, Any]
    idempotency_key: str
    actor: dict[str, str]
    correlation_id: str
    causation_id: str | None = None
    schema_version: str = "1.0.0"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: str = field(default_factory=_utc)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    def caused(self, event_type: str, payload: dict[str, Any], *, actor_id: str,
               natural_key: str, actor_type: str = "agent") -> "Event":
        """Derive a downstream event that keeps the provenance chain intact."""
        return new_event(
            event_type=event_type,
            org_id=self.org_id,
            award_id=self.award_id,
            payload=payload,
            actor_id=actor_id,
            actor_type=actor_type,
            natural_key=natural_key,
            correlation_id=self.correlation_id,
            causation_id=self.event_id,
        )


def new_event(*, event_type: str, org_id: str, award_id: str, payload: dict[str, Any],
              actor_id: str, natural_key: str, actor_type: str = "agent",
              correlation_id: str | None = None, causation_id: str | None = None,
              occurred_at: datetime | None = None) -> Event:
    event = Event(
        event_type=event_type,
        org_id=org_id,
        award_id=award_id,
        payload=payload,
        idempotency_key=idempotency_key(org_id, event_type, natural_key),
        actor={"type": actor_type, "id": actor_id},
        correlation_id=correlation_id or award_id,
        causation_id=causation_id,
        occurred_at=_utc(occurred_at),
    )
    if _DETERMINISTIC:
        event.event_id = str(uuid.uuid5(GRANTLOOP_NS, f"{event.idempotency_key}|{causation_id or ''}"))
    return event
