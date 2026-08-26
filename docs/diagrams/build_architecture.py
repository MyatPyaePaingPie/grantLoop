#!/usr/bin/env python3
"""Generate the architecture diagram from the event contract.

Written as a generator rather than drawn by hand so the picture cannot drift from
the system: the topic list comes from schema/EVENT_CONTRACT.md, and the agents come
from the plan. Re-run it whenever either changes.

    python3 docs/diagrams/build_architecture.py
    rsvg-convert -w 2400 docs/diagrams/architecture.svg -o docs/diagrams/architecture.png
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "schema" / "EVENT_CONTRACT.md"
OUT = Path(__file__).resolve().parent / "architecture.svg"

W, H = 1600, 1120

INK = "#12181f"
MUTED = "#5b6b7c"
LINE = "#c3ced9"
PAPER = "#ffffff"
WASH = "#f4f7fa"
RUN = "#1a5fb4"
BUS = "#8a4fbd"
STORE = "#0f7b6c"
HUMAN = "#b8531a"
ALERT = "#b3261e"
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "SF Mono, Menlo, Consolas, monospace"


def topics() -> list[str]:
    """Topic names straight out of the event contract table."""
    rows = re.findall(r"^\|\s*\d+\s*\|\s*`([^`]+)`", CONTRACT.read_text(), re.M)
    return rows


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, *, size=13, fill=INK, weight="normal", family=FONT, anchor="start",
         spacing="0"):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" '
            f'letter-spacing="{spacing}">{esc(s)}</text>')


def box(x, y, w, h, *, fill=PAPER, stroke=LINE, rx=6, dash=None, width=1.25):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{width}"{d}/>')


def arrow(x1, y1, x2, y2, *, stroke=LINE, dash=None, width=1.4, head="head"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{stroke}" stroke-width="{width}" '
            f'fill="none" marker-end="url(#{head})"{d}/>')


def agent(x, y, w, name, role, *, note=None):
    parts = [box(x, y, w, 62, fill=PAPER, stroke=LINE),
             text(x + 14, y + 25, name, size=14, weight="600"),
             text(x + 14, y + 43, role, size=11, fill=MUTED)]
    if note:
        parts.append(text(x + w - 14, y + 25, note, size=10, fill=HUMAN,
                          weight="600", anchor="end"))
    return parts


def build() -> str:
    t = topics()
    o: list[str] = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">')
    o.append(f'''<defs>
      <marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
              markerHeight="6" orient="auto-start-reverse">
        <path d="M0,1 L9,5 L0,9 z" fill="{LINE}"/>
      </marker>
      <marker id="bus" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
              markerHeight="6" orient="auto-start-reverse">
        <path d="M0,1 L9,5 L0,9 z" fill="{BUS}"/>
      </marker>
      <marker id="human" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
              markerHeight="6" orient="auto-start-reverse">
        <path d="M0,1 L9,5 L0,9 z" fill="{HUMAN}"/>
      </marker>
    </defs>''')
    o.append(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')

    # ---- header
    o.append(text(60, 58, "GrantLoop", size=30, weight="700", spacing="-0.5"))
    o.append(text(60, 82, "Promise-to-proof agent fleet for federal grants",
                  size=13, fill=MUTED))
    o.append(text(W - 60, 58, "Google Cloud", size=13, fill=MUTED, anchor="end"))
    o.append(text(W - 60, 78, "2 Cloud Run services  ·  Pub/Sub  ·  Firestore  ·  Vertex AI",
                  size=11, fill=MUTED, anchor="end"))
    o.append(f'<line x1="60" y1="100" x2="{W-60}" y2="100" stroke="{LINE}"/>')

    # ---- lineage strip
    y0 = 130
    o.append(text(60, y0, "THE LINEAGE", size=10, fill=MUTED, weight="700", spacing="1.4"))
    steps = ["NOFO", "application", "award", "transaction + evidence", "report", "renewal"]
    x = 60
    for i, s in enumerate(steps):
        w = 26 + len(s) * 7.4
        o.append(box(x, y0 + 12, w, 30, fill=WASH, stroke=LINE, rx=15))
        o.append(text(x + w / 2, y0 + 32, s, size=12, anchor="middle"))
        x += w
        if i < len(steps) - 1:
            o.append(arrow(x + 5, y0 + 27, x + 27, y0 + 27))
            x += 34
    o.append(text(x + 6, y0 + 32, "↺", size=18, fill=MUTED))

    # ---- orchestrator service
    ox, oy, ow = 60, 232, 620
    o.append(box(ox, oy, ow, 350, fill=WASH, stroke=RUN, dash="5 4", width=1.6))
    o.append(text(ox + 16, oy + 26, "CLOUD RUN  ·  orchestrator", size=11, fill=RUN,
                  weight="700", spacing="1.2"))
    o.append(text(ox + 16, oy + 44, "Four human-paced agents sharing one working set",
                  size=10.5, fill=MUTED))
    ay = oy + 58
    for name, role, note in [
        ("Intake", "documents in, structured fields + confidence", None),
        ("Application", "one consistency check, narrative vs budget", "human resolves"),
        ("Covenant", "diffs award vs proposal, derives obligations", None),
        ("Reporting", "assembles SF-425, every line traceable", "human certifies"),
    ]:
        o.extend(agent(ox + 16, ay, ow - 32, name, role, note=note))
        ay += 70

    # ---- sentinel service
    sx, sy, sw = 940, 232, 600
    o.append(box(sx, sy, sw, 158, fill=WASH, stroke=RUN, dash="5 4", width=1.6))
    o.append(text(sx + 16, sy + 26, "CLOUD RUN  ·  ledger-sentinel", size=11, fill=RUN,
                  weight="700", spacing="1.2"))
    o.append(text(sx + 16, sy + 44, "Split out: the only high-volume, retry-heavy component",
                  size=10.5, fill=MUTED))
    o.extend(agent(sx + 16, sy + 58, sw - 32, "Ledger Sentinel",
                   "7-value determination under 2 CFR 200 + award terms",
                   note="escalates"))
    o.append(text(sx + 30, sy + 146, "push subscription  ·  5 attempts  ·  then DLQ",
                  size=10, fill=MUTED, family=MONO))

    # ---- bus
    bx, by, bw = 700, 232, 220
    bh = 92 + len(t) * 18.5
    o.append(box(bx, by, bw, bh, fill=PAPER, stroke=BUS, width=1.6))
    o.append(text(bx + bw / 2, by + 26, "Pub/Sub", size=13, weight="700", fill=BUS,
                  anchor="middle"))
    o.append(text(bx + bw / 2, by + 43, f"{len(t)} topics", size=10, fill=MUTED,
                  anchor="middle"))
    ty = by + 62
    for name in t:
        o.append(text(bx + 14, ty, name, size=9.2, fill=INK, family=MONO))
        ty += 18.5
    o.append(text(bx + bw / 2, by + bh - 14, "no agent calls another agent", size=9.5,
                  fill=BUS, anchor="middle", weight="600"))

    o.append(arrow(ox + ow, 400, bx - 6, 400, stroke=BUS, head="bus"))
    o.append(arrow(bx + bw + 6, 330, sx - 6, 330, stroke=BUS, head="bus"))
    o.append(arrow(sx - 6, 360, bx + bw + 6, 360, stroke=BUS, head="bus"))

    # ---- envelope
    ex, ey = 940, 418
    o.append(box(ex, ey, 600, 114, fill=PAPER, stroke=LINE))
    o.append(text(ex + 16, ey + 24, "EVERY EVENT CARRIES", size=10, fill=MUTED,
                  weight="700", spacing="1.4"))
    for i, (k, v) in enumerate([
        ("causation_id", "walks any fact back to the event that caused it"),
        ("correlation_id", "constant for the whole award lineage"),
        ("idempotency_key", "sha256 derived, so at-least-once becomes exactly-once"),
    ]):
        o.append(text(ex + 16, ey + 48 + i * 22, k, size=11, family=MONO, fill=BUS))
        o.append(text(ex + 150, ey + 48 + i * 22, v, size=10.5, fill=MUTED))

    # ---- storage and model row
    ry = int(by + bh + 34)
    o.append(box(60, ry, 300, 96, fill=PAPER, stroke=STORE))
    o.append(text(76, ry + 24, "Firestore", size=13, weight="700", fill=STORE))
    o.append(text(76, ry + 44, "obligations · determinations · reports", size=10.5, fill=MUTED))
    o.append(text(76, ry + 62, "processed/{agent}/{idempotency_key}", size=9.5,
                  family=MONO, fill=MUTED))
    o.append(text(76, ry + 80, "written in the same transaction as the output",
                  size=10, fill=MUTED))

    o.append(box(380, ry, 300, 96, fill=PAPER, stroke=LINE))
    o.append(text(396, ry + 24, "Vertex AI  ·  Gemini 3.5", size=13, weight="700"))
    o.append(text(396, ry + 44, "drafts the escalation question only", size=10.5, fill=MUTED))
    o.append(text(396, ry + 64, "never decides a determination", size=10.5, fill=ALERT,
                  weight="600"))
    o.append(text(396, ry + 82, "MODEL_ID env var, one swap point", size=9.5,
                  family=MONO, fill=MUTED))

    o.append(box(700, ry, 220, 96, fill=PAPER, stroke=ALERT))
    o.append(text(716, ry + 24, "Dead letter queue", size=13, weight="700", fill=ALERT))
    o.append(text(716, ry + 44, "after 5 attempts", size=10.5, fill=MUTED))
    o.append(text(716, ry + 64, "a panel on screen,", size=10.5, fill=MUTED))
    o.append(text(716, ry + 80, "not a line in a log", size=10.5, fill=MUTED))

    o.append(box(940, ry, 600, 96, fill=PAPER, stroke=HUMAN))
    o.append(text(956, ry + 24, "Where a human is required", size=13, weight="700", fill=HUMAN))
    for i, (label, cite) in enumerate([
        ("Consistency exception, three concrete resolutions offered", "application"),
        ("Determination that turns on a fact about the world", "200.454(e)"),
        ("SF-425 certification by an authorised official", "200.415(a)"),
    ]):
        o.append(text(956, ry + 44 + i * 17, "•  " + label, size=10.5, fill=MUTED))
        o.append(text(1524, ry + 44 + i * 17, cite, size=9.5, family=MONO,
                      fill=HUMAN, anchor="end"))

    # ---- determinations
    dy = ry + 140
    o.append(text(60, dy, "SEVEN DETERMINATIONS, EACH CITING THE PARAGRAPH THAT PRODUCED IT",
                  size=10, fill=MUTED, weight="700", spacing="1.4"))
    vals = [
        ("presumptively allowable", "200.453"),
        ("presumptively unallowable", "200.423"),
        ("missing documentation", "200.403(g)"),
        ("requires allocation", "200.405"),
        ("requires prior approval", "200.458"),
        ("conflicts with award terms", "award SC-2"),
        ("requires human determination", "200.454(e)"),
    ]
    x = 60
    for label, cite in vals:
        w = 20 + max(len(label), len(cite)) * 6.6
        o.append(box(x, dy + 14, w, 46, fill=PAPER, stroke=LINE, rx=5))
        o.append(text(x + 10, dy + 33, label, size=10.5))
        o.append(text(x + 10, dy + 50, cite, size=9.5, family=MONO, fill=MUTED))
        x += w + 10

    o.append(text(60, dy + 84,
                  "The determination is deterministic and citable. The model writes the question, "
                  "never the verdict.", size=11.5, fill=INK))
    o.append(text(60, dy + 104,
                  "A cost that matches no rule escalates. Silence is never approval.",
                  size=11.5, fill=ALERT, weight="600"))

    # ---- footer
    fy = dy + 156
    o.append(f'<line x1="60" y1="{fy}" x2="{W-60}" y2="{fy}" stroke="{LINE}"/>')
    o.append(text(60, fy + 26, "OFFLINE REPLAY PATH", size=10, fill=MUTED,
                  weight="700", spacing="1.4"))
    o.append(text(60, fy + 48,
                  "The same agents and the same event contract run over an in-process bus with "
                  "no cloud dependency and no installed packages.", size=11.5, fill=MUTED))
    o.append(text(60, fy + 68,
                  "Byte-identical every run, provenance chain included. A demo path that never "
                  "touches the network cannot fail because of the network.",
                  size=11.5, fill=MUTED))
    o.append(text(W - 60, fy + 48, "python -m grantloop.replay", size=11,
                  family=MONO, fill=INK, anchor="end"))
    o.append(text(W - 60, fy + 68, "python -m grantloop.api", size=11,
                  family=MONO, fill=INK, anchor="end"))

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"wrote {OUT} ({len(build())} bytes, {len(topics())} topics from the event contract)")
