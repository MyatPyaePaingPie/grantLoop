"""Runtime configuration.

Every cloud-facing value is an environment variable with a safe local default.
Nothing here hardcodes a GCP project or a model id: the project moved once already
and the model id is expected to change the moment Gemini 3.x access lands.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


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
        location=e.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        topic_prefix=e.get("GRANTLOOP_TOPIC_PREFIX", "grantloop"),
    )
