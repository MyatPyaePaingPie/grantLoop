"""Where the ruleset, seed and dashboard live at runtime.

These are data directories, not package data, and their location differs between
a source checkout and a container. Resolving them from `__file__` works in a
checkout and silently breaks the moment the package is installed elsewhere, so
the location is explicit and overridable instead.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Directory holding schema/, seed/ and dashboard/. Set GRANTLOOP_ROOT to move it.
ROOT = Path(os.environ.get("GRANTLOOP_ROOT", Path(__file__).resolve().parents[1]))

SCHEMA = ROOT / "schema"
SEED = ROOT / "seed"
DASHBOARD = ROOT / "dashboard"
RULESET = SCHEMA / "allowability_rules.v0.json"
SCENARIO = SEED / "riverbend_scenario.json"


def require(path: Path) -> Path:
    """Fail loudly at startup rather than mysteriously on the first request."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Set GRANTLOOP_ROOT to the directory containing "
            f"schema/ and seed/ (currently {ROOT})."
        )
    return path
