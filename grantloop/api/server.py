"""Zero-dependency dev server: the read API plus the dashboard, one port.

Standard library only, deliberately. Everything else in the offline path runs with
nothing installed, and the dashboard is the piece most likely to be opened by
someone who has not made a venv. `python -m grantloop.api` and it is on screen.

Serving the dashboard from the same origin also removes CORS from the equation,
though CORS headers are set anyway so the dashboard can be opened from elsewhere.

This is not the production server. Cloud Run runs the ASGI app in app.py.
"""

from __future__ import annotations

import json
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .routes import Orchestrator, dispatch

from ..paths import ROOT


class Handler(SimpleHTTPRequestHandler):
    orchestrator: Orchestrator

    def __init__(self, *args, orchestrator: Orchestrator, **kwargs):
        self.orchestrator = orchestrator
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_response(302)
            self.send_header("Location", "/dashboard/")
            self.end_headers()
            return
        if not parsed.path.startswith("/api/"):
            return super().do_GET()

        if parsed.path == "/api/replay":
            self.orchestrator.refresh()
            return self._json({"status": "replayed"})

        payload = dispatch(self.orchestrator, parsed.path, parse_qs(parsed.query))
        if payload is None:
            return self._json({"error": "not found", "routes": sorted(_routes())}, status=404)
        self._json(payload)

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        if "/api/" in str(args[0] if args else ""):
            super().log_message(fmt, *args)


def _routes() -> list[str]:
    from .routes import ROUTES

    return [*ROUTES, "/api/replay"]


def serve(host: str = "127.0.0.1", port: int = 8080, *, fail_txn: str | None = None) -> None:
    orchestrator = Orchestrator(fail_txn=fail_txn)
    handler = partial(Handler, orchestrator=orchestrator)
    server = HTTPServer((host, port), handler)
    health = orchestrator.health()
    print(f"GrantLoop orchestrator on http://{host}:{port}")
    print(f"  dashboard  http://{host}:{port}/dashboard/")
    print(f"  mode {health['mode']}  ruleset {health['ruleset_version']}  "
          f"citations {'verified' if health['citations_verified'] else 'UNVERIFIED'}")
    for route in sorted(_routes()):
        print(f"  {route}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
