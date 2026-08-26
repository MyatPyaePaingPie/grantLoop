"""Test environment.

The suite must be hermetic: no network, no cloud project, no ambient credentials.
Without this, running the tests in a shell that happens to export
GOOGLE_CLOUD_PROJECT turns them into live Vertex calls, which is slow, costs
money, and makes results depend on whose laptop ran them. Tests that want the
cloud path inject a fake client instead.
"""

from __future__ import annotations

import pytest

CLOUD_ENV = (
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "MODEL_ID",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GRANTLOOP_TOPIC_PREFIX",
)


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in CLOUD_ENV:
        monkeypatch.delenv(name, raising=False)
