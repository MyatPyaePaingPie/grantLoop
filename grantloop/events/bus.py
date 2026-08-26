"""Transport for the event contract.

Two implementations behind one interface:

* `LocalBus` — in-process, ordered, no network. This is what the replay CLI drives
  and what the tests use. It is also the record-day fallback: a demo path that
  never touches the network cannot fail because of the network.
* `PubSubBus` — real Google Cloud Pub/Sub, one topic per event type, used once a
  project exists.

`open_bus` picks by configuration, so no caller decides which one it is talking to.

Idempotency lives here rather than in each agent: the bus refuses to deliver an
event whose `idempotency_key` a handler has already processed. In cloud mode the
same check belongs in a Firestore transaction alongside the handler's write, which
is what the event contract specifies; `SeenStore` is the seam for that.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable, Protocol

from .envelope import Event

Handler = Callable[[Event], Iterable[Event] | None]


class SeenStore(Protocol):
    """Records which (handler, idempotency_key) pairs are already done."""

    def seen(self, handler_name: str, key: str) -> bool: ...
    def mark(self, handler_name: str, key: str) -> None: ...


class MemorySeenStore:
    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()

    def seen(self, handler_name: str, key: str) -> bool:
        return (handler_name, key) in self._seen

    def mark(self, handler_name: str, key: str) -> None:
        self._seen.add((handler_name, key))


class Bus(Protocol):
    def subscribe(self, event_type: str, handler: Handler, *, name: str) -> None: ...
    def publish(self, event: Event) -> None: ...


class DeadLetter:
    """One failed delivery, kept so the UI can render a DLQ panel.

    The event contract is explicit that failures must be visible rather than logged
    away — judges score failure handling, so the DLQ is a screen, not a log line.
    """

    def __init__(self, event: Event, handler_name: str, attempts: int, last_error: str):
        self.event = event
        self.handler_name = handler_name
        self.attempts = attempts
        self.last_error = last_error

    def to_dict(self) -> dict[str, object]:
        return {
            "txn_ref": self.event.payload.get("txn_id") or self.event.event_id,
            "event_type": self.event.event_type,
            "handler": self.handler_name,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "first_seen": self.event.occurred_at,
        }


class LocalBus:
    """Ordered, in-process delivery with retry, DLQ and idempotency."""

    def __init__(self, *, max_attempts: int = 5, seen: SeenStore | None = None) -> None:
        self._handlers: dict[str, list[tuple[str, Handler]]] = defaultdict(list)
        self._seen = seen or MemorySeenStore()
        self.max_attempts = max_attempts
        self.log: list[Event] = []
        self.dead_letters: list[DeadLetter] = []

    def subscribe(self, event_type: str, handler: Handler, *, name: str) -> None:
        self._handlers[event_type].append((name, handler))

    def publish(self, event: Event) -> None:
        """Deliver depth-first so a causal chain lands in causal order."""
        self.log.append(event)
        for name, handler in self._handlers.get(event.event_type, []):
            if self._seen.seen(name, event.idempotency_key):
                continue  # at-least-once delivery, exactly-once effect
            self._deliver(event, handler, name)

    def _deliver(self, event: Event, handler: Handler, name: str) -> None:
        last_error = ""
        for attempt in range(1, self.max_attempts + 1):
            try:
                produced = handler(event) or []
                self._seen.mark(name, event.idempotency_key)
                for downstream in produced:
                    self.publish(downstream)
                return
            except Exception as exc:  # noqa: BLE001 - the DLQ is the point
                last_error = f"{type(exc).__name__}: {exc}"
        self.dead_letters.append(DeadLetter(event, name, self.max_attempts, last_error))

    def events_of(self, event_type: str) -> list[Event]:
        return [e for e in self.log if e.event_type == event_type]


class PubSubBus:
    """Real Pub/Sub publisher. Subscriptions are push endpoints on Cloud Run.

    Deliberately thin: the contract, retry semantics and DLQ policy are Pub/Sub
    configuration, not code. Kept import-light so the offline path never needs the
    google-cloud-pubsub dependency installed.
    """

    def __init__(self, project: str, topic_prefix: str = "grantloop") -> None:
        from google.cloud import pubsub_v1  # imported lazily, cloud-only path

        self.project = project
        self.topic_prefix = topic_prefix
        self._publisher = pubsub_v1.PublisherClient()

    def topic_path(self, event_type: str) -> str:
        topic = f"{self.topic_prefix}.{event_type}".replace("_", "-")
        return self._publisher.topic_path(self.project, topic)

    def subscribe(self, event_type: str, handler: Handler, *, name: str) -> None:
        raise NotImplementedError(
            "Pub/Sub subscriptions are push endpoints configured on Cloud Run, "
            "not registered in process. See schema/EVENT_CONTRACT.md."
        )

    def publish(self, event: Event) -> None:
        self._publisher.publish(
            self.topic_path(event.event_type),
            event.to_json().encode(),
            idempotency_key=event.idempotency_key,
            correlation_id=event.correlation_id,
        ).result()


def open_bus(config=None) -> Bus:
    from ..config import load

    cfg = config or load()
    if cfg.offline:
        return LocalBus()
    return PubSubBus(cfg.project, cfg.topic_prefix)
