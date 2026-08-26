"""Acceptance tests for the orchestrator read API.

Two bars beyond "it responds":

* Every dollar in the ledger appears somewhere in the SF-425. A report that
  silently drops a split remainder is worse than no report, and the dashboard
  promises every figure is traceable to its transaction.
* The stdlib dev server and the ASGI app return identical payloads, because the
  demo is recorded against one and deployed on the other.
"""

from __future__ import annotations

import json
import threading
from http.server import HTTPServer
from functools import partial
from urllib.request import urlopen

import pytest

from grantloop.api.routes import Orchestrator, ROUTES, dispatch
from grantloop.api.server import Handler


@pytest.fixture
def orch() -> Orchestrator:
    return Orchestrator()


def test_every_dollar_reaches_the_report(orch: Orchestrator) -> None:
    """TXN-002's $828 remainder must not vanish between ledger and SF-425."""
    ledger_total = sum(t["amount"] for t in orch.ledger(limit=500)["transactions"])
    report = orch.report_current()
    assert report["total_reported"] == round(ledger_total, 2)
    assert sum(v["amount"] for v in report["lines"].values()) == report["total_reported"]


def test_split_transaction_appears_in_two_report_lines(orch: Orchestrator) -> None:
    lines = orch.report_current()["lines"]
    appearances = [name for name, line in lines.items() if "TXN-002" in line["source_txn_ids"]]
    assert len(appearances) == 2, appearances
    assert lines["questioned_costs"]["amount"] >= 412.0


def test_report_is_never_certified_by_the_machine(orch: Orchestrator) -> None:
    """2 CFR 200.415(a) requires a named human. The API exposes the gate, not a filing."""
    report = orch.report_current()
    assert report["certified"] is False
    assert report["certification_gate"]["required"] is True
    assert report["certification_gate"]["citation"]["label"] == "2 CFR 200.415(a)"
    assert report["submission"] == {"mode": "simulated", "disclosed": True}


def test_unresolved_exceptions_include_split_remainders(orch: Orchestrator) -> None:
    assert "TXN-002" in orch.report_current()["unresolved_exceptions"]


def test_health_never_leaks_a_hardcoded_project(orch: Orchestrator) -> None:
    """No project id may be baked in. conftest strips the env so this is real."""
    health = orch.health()
    assert health["project"] is None
    assert health["citations_verified"] is True
    assert health["source"] == "replay"


@pytest.mark.parametrize("path", sorted(ROUTES))
def test_every_declared_route_dispatches(orch: Orchestrator, path: str) -> None:
    payload = dispatch(orch, path, {})
    assert isinstance(payload, dict) and payload


def test_unknown_route_returns_none(orch: Orchestrator) -> None:
    assert dispatch(orch, "/api/nope", {}) is None


def test_ledger_limit_is_honoured(orch: Orchestrator) -> None:
    assert len(orch.ledger(limit=3)["transactions"]) == 3


class _Server:
    def __init__(self) -> None:
        self.httpd = HTTPServer(("127.0.0.1", 0), partial(Handler, orchestrator=Orchestrator()))
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def get(self, path: str) -> dict:
        with urlopen(f"http://127.0.0.1:{self.port}{path}") as r:
            return json.loads(r.read())

    def status(self, path: str) -> int:
        with urlopen(f"http://127.0.0.1:{self.port}{path}") as r:
            return r.status

    def close(self) -> None:
        self.httpd.shutdown()


@pytest.fixture
def server():
    s = _Server()
    yield s
    s.close()


@pytest.mark.parametrize("path", sorted(ROUTES))
def test_dev_server_matches_direct_dispatch(server: _Server, path: str) -> None:
    assert server.get(path) == dispatch(Orchestrator(), path, {})


def test_dev_server_serves_the_dashboard(server: _Server) -> None:
    assert server.status("/dashboard/index.html") == 200


def test_dev_server_sets_cors(server: _Server) -> None:
    with urlopen(f"http://127.0.0.1:{server.port}/api/health") as r:
        assert r.headers["Access-Control-Allow-Origin"] == "*"


def test_asgi_app_declares_every_route() -> None:
    """Guards against the recorded demo and the deployed service drifting apart."""
    fastapi = pytest.importorskip("fastapi")  # noqa: F841
    from grantloop.api.app import create_app

    app = create_app()
    served = {r.path for r in app.routes if getattr(r, "path", "").startswith("/api/")}
    assert set(ROUTES) <= served
