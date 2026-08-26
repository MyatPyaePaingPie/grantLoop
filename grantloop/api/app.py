"""ASGI app for Cloud Run.

Shares the exact route table and payload logic with the stdlib dev server, so the
recorded demo and the deployed service cannot diverge. FastAPI is an optional
dependency: the offline path never imports this module.
"""

from __future__ import annotations

from typing import Any

from .routes import Orchestrator, ROUTES


def create_app() -> Any:
    from fastapi import FastAPI, Query
    from fastapi.middleware.cors import CORSMiddleware

    orchestrator = Orchestrator()
    app = FastAPI(title="GrantLoop orchestrator", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
    )

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return orchestrator.health()

    @app.get("/api/state/award")
    def award() -> dict[str, Any]:
        return orchestrator.award()

    @app.get("/api/state/ledger")
    def ledger(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
        return orchestrator.ledger(limit=limit)

    @app.get("/api/state/exceptions")
    def exceptions() -> dict[str, Any]:
        return orchestrator.exceptions()

    @app.get("/api/state/report/current")
    def report_current() -> dict[str, Any]:
        return orchestrator.report_current()

    _assert_routes_match(app)
    return app


def _assert_routes_match(app: Any) -> None:
    """Fail at startup if the ASGI app and the route table drift apart.

    Cheap insurance against the demo being recorded against one surface and the
    judges testing another.
    """
    declared = set(ROUTES)
    served = {r.path for r in app.routes if getattr(r, "path", "").startswith("/api/")}
    missing = declared - served
    if missing:
        raise RuntimeError(f"ASGI app is missing declared routes: {sorted(missing)}")


app = None  # populated by the server entrypoint, so importing this module is cheap
