"""The video, as data.

The VO is Pooof's word-for-word script from docs/VIDEO_RECORDING_KIT.md, unchanged.
Everything else here is how to capture the picture that goes with it.

Keeping the script as data rather than prose means the narration, the footage and
the timing all derive from one source: change a line and the audio, the shot
length and the final cut all move together. A recorded video drifts from its
script the moment either is edited; this cannot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Source = Literal["title", "dashboard", "terminal", "image", "http"]


@dataclass
class Beat:
    id: str
    source: Source
    vo: str
    #: Dashboard tab to show, terminal tape to play, or image/endpoint to display.
    target: str = ""
    #: Extra dashboard interactions, as (selector-ish description, seconds).
    dwell: float = 0.0
    title_lines: list[str] = field(default_factory=list)

    @property
    def words(self) -> int:
        return len(self.vo.split())


BEATS: list[Beat] = [
    Beat(
        id="00-cold-open",
        source="title",
        title_lines=[
            "A 2-person nonprofit wins a $250K federal grant.",
            "Now the hard part starts.",
        ],
        vo=("A two-person nonprofit wins a two hundred fifty thousand dollar federal grant. "
            "With it, they inherit 2 CFR Part 200: an allowability test on every expense, "
            "an SF-425 on a deadline, and a high-risk designation waiting if they slip. "
            "Grant-writing AI abandons you at the moment of victory. Compliance tools start "
            "from scratch after it. Nobody closes the loop. GrantLoop is the loop."),
    ),
    Beat(
        id="01-application",
        source="dashboard",
        target="award",
        vo=("It starts before the award. The application agent reads what the narrative "
            "promises, a hundred twenty youth at a one-to-ten ratio, against what the budget "
            "funds: two mentors at half time. It flags the contradiction and offers three "
            "concrete resolutions. The system reads what you promised, not just what you wrote."),
    ),
    Beat(
        id="02-award-handoff",
        source="dashboard",
        target="award",
        dwell=3.0,
        vo=("Award day. Covenant diffs the Notice of Award against the application, and derives "
            "three findings nobody scripted. Participant support: cut forty percent. The target "
            "it paid for: accepted unchanged at a hundred twenty youth. They cut the money and "
            "kept the promise. Then it finds the same pattern again on outreach, a rule firing, "
            "not a special case. And a third finding: this award's stated total is twenty-two "
            "thousand dollars less than its own budget lines. The award doesn't add up, and "
            "Covenant caught that too, because it reconciles instead of trusting the headline "
            "number."),
    ),
    Beat(
        id="03a-sentinel-replay",
        source="terminal",
        target="replay",
        vo=("Now money starts moving. Seven transactions, seven different determinations, every "
            "one citing the regulation it applied. A catering invoice isn't rejected; it's "
            "split. Four hundred twelve dollars of wine carved out under 200.423, the rest "
            "routed for review."),
    ),
    Beat(
        id="03b-sentinel-dashboard",
        source="dashboard",
        target="sentinel",
        dwell=3.0,
        vo=("The laptops are the interesting one: the regulation actually permits them. The "
            "award's own condition doesn't. The regulation permits this, your award does not. "
            "The Sentinel doesn't ask a model whether a cost is allowable. It's a deterministic "
            "rule engine over eCFR-verified citations, reproducible on camera, defensible to a "
            "judge. The model's job is drafting the human-facing question when it escalates."),
    ),
    Beat(
        id="03c-dlq",
        source="terminal",
        target="dlq",
        vo=("And when a message poisons, it retries five times and lands here, on screen, "
            "loudly. Unmatched costs escalate to a human. Silence is never approval."),
    ),
    Beat(
        id="04-sf425",
        source="dashboard",
        target="report",
        dwell=3.0,
        vo=("Reporting day. The SF-425 assembles itself from actual ledger state. The catering "
            "split survives all the way through: two lines, reconciling to the cent. Every "
            "figure traces to its transactions. And then it stops. 2 CFR 200.415 requires an "
            "official who can legally bind the recipient, so the system assembles, and a human "
            "certifies. That button is disabled by construction."),
    ),
    Beat(
        id="05-loop-closes",
        source="title",
        title_lines=[
            "Most grant software remembers the documents.",
            "GrantLoop remembers the promises.",
        ],
        vo=("Next application, the loop closes: verified performance and a machine-checked "
            "compliance record carry forward as evidence. Most grant software remembers the "
            "documents. GrantLoop remembers the promises."),
    ),
    Beat(
        id="06a-architecture",
        source="image",
        target="docs/diagrams/architecture.png",
        vo=("Under the hood: two Cloud Run services, deliberately not five. Four human-paced "
            "agents share an orchestrator; the Sentinel deploys alone because it's the only "
            "high-volume, retry-heavy component. That's real failure isolation, not diagram "
            "decoration. Agents never call each other: every transition is an event with a "
            "causation ID, every handler idempotent, failures land in a dead-letter queue you "
            "just saw on screen."),
    ),
    Beat(
        id="06b-cloud-proof",
        source="terminal",
        target="health",
        vo=("ADK agents plan and explain; deterministic engines decide and cite. Gemini 3.5 "
            "drafts the questions only humans can answer. Running on Google Cloud: here's the "
            "live service. GrantLoop: from promise to proof."),
    ),
]

#: Words per minute the narrator actually speaks at. Used only for reporting.
WPM = 150


def total_words() -> int:
    return sum(b.words for b in BEATS)
