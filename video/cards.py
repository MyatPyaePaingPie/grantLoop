#!/usr/bin/env python3
"""Render the title cards as SVG, then PNG.

Two cards, both quoting Pooof's script verbatim. Drawn rather than screenshotted
because they are the only frames in the video that are not the product itself,
and they should look deliberate rather than like a slide someone made.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from script import BEATS  # noqa: E402

OUT = HERE / "build" / "cards"
W, H = 1920, 1080
INK = "#12181f"
MUTED = "#5b6b7c"
PAPER = "#ffffff"
RULE = "#c3ced9"
ACCENT = "#1a5fb4"
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def card(lines: list[str], footer: str) -> str:
    size = 62 if max(len(x) for x in lines) < 52 else 50
    start = H / 2 - (len(lines) - 1) * (size * 0.72) - 20
    body = "\n".join(
        f'<text x="{W/2}" y="{start + i * size * 1.45}" font-family="{FONT}" '
        f'font-size="{size}" fill="{INK}" text-anchor="middle" font-weight="600" '
        f'letter-spacing="-1">{esc(line)}</text>'
        for i, line in enumerate(lines)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{PAPER}"/>
  <text x="96" y="104" font-family="{FONT}" font-size="30" font-weight="700"
        fill="{INK}" letter-spacing="-0.5">Grant<tspan fill="{ACCENT}">Loop</tspan></text>
  <line x1="96" y1="136" x2="{W-96}" y2="136" stroke="{RULE}"/>
  {body}
  <line x1="96" y1="{H-136}" x2="{W-96}" y2="{H-136}" stroke="{RULE}"/>
  <text x="96" y="{H-92}" font-family="{FONT}" font-size="22" fill="{MUTED}">{esc(footer)}</text>
</svg>'''


CARDS = {
    "00-cold-open": "2 CFR Part 200 · federal grant compliance",
    "05-loop-closes": "promise to proof",
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for beat in BEATS:
        if beat.source != "title":
            continue
        svg = OUT / f"{beat.id}.svg"
        png = OUT / f"{beat.id}.png"
        svg.write_text(card(beat.title_lines, CARDS[beat.id]))
        subprocess.run(["rsvg-convert", "-w", str(W), str(svg), "-o", str(png)], check=True)
        print(f"  {beat.id:22} -> {png.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
