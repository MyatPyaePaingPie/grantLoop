"""ASGI app for Cloud Run.

Shares the exact route table and payload logic with the stdlib dev server, so the
recorded demo and the deployed service cannot diverge. FastAPI is an optional
dependency: the offline path never imports this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .routes import Orchestrator, ROUTES

from ..paths import DASHBOARD, SEED


def create_app() -> Any:
    """Build the ASGI app by registering the shared route table.

    Routes are generated from ROUTES rather than hand-written decorators. A
    hand-written list can drift from the dev server the demo was recorded
    against, and the test that caught that drift needs FastAPI installed, so it
    silently skips on machines that only run the offline path. Generating them
    makes the drift impossible instead of merely detected.
    """
    from fastapi import FastAPI, Query
    from fastapi.middleware.cors import CORSMiddleware

    orchestrator = Orchestrator()
    app = FastAPI(title="GrantLoop orchestrator", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
    )

    for path, handler_name in ROUTES.items():
        _register(app, path, getattr(orchestrator, handler_name), Query)

    @app.get("/api/replay")
    def replay() -> dict[str, Any]:
        """Re-run the fleet. The dashboard's replay button calls this."""
        orchestrator.refresh()
        return {"status": "replayed"}

    _assert_routes_match(app)
    _mount_dashboard(app)
    return app


def _register(app: Any, path: str, handler: Any, Query: Any) -> None:
    """Attach one orchestrator method as a GET route.

    `ledger` is the only route taking a query parameter; everything else is a
    plain read. Kept explicit rather than reflected off the signature, because a
    surprise parameter should break loudly here rather than silently become part
    of the public API.
    """
    if path == "/api/state/ledger":
        @app.get(path, name="ledger")
        def _ledger(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
            return handler(limit=limit)
        return

    @app.get(path, name=path.strip("/").replace("/", "_"))
    def _read() -> dict[str, Any]:
        return handler()


def _mount_dashboard(app: Any) -> None:
    """Serve the dashboard from the same origin as the API.

    The deployed URL is what judges open and what the demo video shows, so it has
    to render the product rather than a JSON blob. Same origin also means the
    dashboard's fetch calls need no CORS round trip.
    """
    from fastapi.responses import RedirectResponse
    from fastapi.staticfiles import StaticFiles

    dashboard = DASHBOARD
    if not dashboard.is_dir():
        return

    @app.get("/", include_in_schema=False)
    def index() -> Any:
        return RedirectResponse("/dashboard/")

    # The dashboard reads the seed directly when live data is unavailable, so the
    # seed has to be reachable at the same relative path it uses locally.
    app.mount("/seed", StaticFiles(directory=str(SEED)), name="seed")
    app.mount("/dashboard", StaticFiles(directory=str(dashboard), html=True), name="dashboard")


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
