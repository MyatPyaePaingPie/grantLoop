#!/usr/bin/env python3
"""Record the dashboard beats by driving the real app with Playwright.

This is screen capture, not synthesis. Every frame is the actual dashboard
rendering actual output from the actual engines, driven by a script instead of a
hand. The distinction matters: fabricating footage of a compliance product working
would be exactly the dishonesty the product exists to prevent.

Each beat records for as long as its narration runs, so picture and voice stay in
step without anyone counting seconds.

    python3 video/capture.py
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import soundfile as sf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from script import BEATS  # noqa: E402

SHOTS = HERE / "build" / "shots"
VO = HERE / "build" / "vo"
VIEWPORT = {"width": 1600, "height": 900}

#: Recording against the deployed project. Falls back to whatever is already in
#: the environment, so a machine without access still records (in offline mode)
#: rather than failing.
CLOUD_ENV = {
    "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT", "active-future-506706-s7"),
    "MODEL_ID": os.environ.get("MODEL_ID", "gemini-3.5-flash"),
    "GOOGLE_CLOUD_LOCATION": os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
}
SCROLL_PAUSE = 1.2


def vo_seconds(beat_id: str) -> float:
    """How long this beat's picture must last: exactly its narration."""
    path = VO / f"{beat_id}.wav"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing. Run video/narrate.py first.")
    info = sf.info(str(path))
    return info.frames / info.samplerate


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    """The real orchestrator, serving the real dashboard."""

    def __init__(self) -> None:
        self.port = free_port()
        self.proc: subprocess.Popen | None = None

    def __enter__(self) -> "Server":
        # Run with the cloud configuration so the footage shows what actually
        # ships: the mode badge reads CLOUD and the escalation question on the
        # Sentinel tab is the one Gemini wrote, not the canned fallback. The
        # engine is identical either way; only the narration source differs.
        env = {**os.environ, **CLOUD_ENV}
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "grantloop.api", "--port", str(self.port)],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(60):
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.3):
                    time.sleep(0.6)
                    return self
            except OSError:
                time.sleep(0.2)
        raise RuntimeError("orchestrator did not come up")

    def __exit__(self, *exc: object) -> None:
        if self.proc:
            self.proc.terminate()
            self.proc.wait(timeout=10)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/dashboard/"


def record_beat(browser, server: Server, beat) -> Path:
    """One beat, one browser context, one video file."""
    seconds = vo_seconds(beat.id)
    tmp = SHOTS / f"_{beat.id}"
    tmp.mkdir(parents=True, exist_ok=True)

    context = browser.new_context(
        viewport=VIEWPORT, record_video_dir=str(tmp),
        record_video_size=VIEWPORT, device_scale_factor=2,
    )
    page = context.new_page()
    page.goto(server.url, wait_until="networkidle")
    page.wait_for_timeout(700)

    page.click(f'button[data-tab="{beat.target}"]')
    page.wait_for_timeout(500)

    # Hold on the tab, then walk down it so long panels are actually read on
    # camera rather than sitting off-screen for the whole beat.
    budget = seconds - 1.2
    page.wait_for_timeout(int(max(beat.dwell, 1.0) * 1000))
    budget -= max(beat.dwell, 1.0)

    height = page.evaluate("document.querySelector('main').scrollHeight")
    if height > VIEWPORT["height"] and budget > SCROLL_PAUSE * 2:
        steps = max(1, int(budget // SCROLL_PAUSE) - 1)
        for i in range(1, steps + 1):
            page.mouse.wheel(0, height / (steps + 1))
            page.wait_for_timeout(int(SCROLL_PAUSE * 1000))
            budget -= SCROLL_PAUSE
    if budget > 0:
        page.wait_for_timeout(int(budget * 1000))

    video = page.video
    context.close()  # flushes the file
    raw = Path(video.path())
    final = SHOTS / f"{beat.id}.webm"
    shutil.move(str(raw), final)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"  {beat.id:22} {seconds:5.1f}s  -> {final.name}")
    return final


def main() -> int:
    from playwright.sync_api import sync_playwright

    SHOTS.mkdir(parents=True, exist_ok=True)
    beats = [b for b in BEATS if b.source == "dashboard"]
    print(f"recording {len(beats)} dashboard beats")

    with Server() as server, sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--force-color-profile=srgb"])
        for beat in beats:
            record_beat(browser, server, beat)
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
