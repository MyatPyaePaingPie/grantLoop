"""Runtime configuration.

Every cloud-facing value is an environment variable with a safe local default.
Nothing here hardcodes a GCP project or a model id: the project moved once already
and the model id is expected to change the moment Gemini 3.x access lands.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Config:
    """Resolved runtime settings.

    `offline` is the important one. When no project is configured the whole system
    runs as a pure local pipeline — no Pub/Sub, no Vertex, no network. That is both
    the development mode and the record-day fallback.
    """

    project: str | None
    model_id: str
    location: str
    topic_prefix: str

    #: Vertex serves Gemini 3.x from `global` only. Every regional endpoint we probed
    #: returns 404 for gemini-3.5-flash, which reads like an auth failure and is not
    #: one. Verified against active-future-506706-s7 on 2026-08-26: global 200,
    #: us-central1 404. This default is load-bearing, not cosmetic.
    DEFAULT_LOCATION: ClassVar[str] = "global"

    @property
    def offline(self) -> bool:
        return self.project is None

    def describe(self) -> dict[str, object]:
        """Payload for GET /api/health."""
        return {
            "project": self.project,
            "model_id": self.model_id,
            "location": self.location,
            "mode": "offline" if self.offline else "cloud",
        }


def load(env: dict[str, str] | None = None) -> Config:
    e = os.environ if env is None else env
    project = e.get("GOOGLE_CLOUD_PROJECT") or None
    return Config(
        project=project,
        model_id=e.get("MODEL_ID", "gemini-3.5-flash"),
        location=e.get("GOOGLE_CLOUD_LOCATION", Config.DEFAULT_LOCATION),
        topic_prefix=e.get("GRANTLOOP_TOPIC_PREFIX", "grantloop"),
    )
