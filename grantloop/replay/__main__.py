"""`python -m grantloop.replay` — fire the seeded ledger on demand.

Record-day usage:

    python -m grantloop.replay --pace 1.5          # narratable pace, live on screen
    python -m grantloop.replay --dlq TXN-004       # force the DLQ panel to populate
    python -m grantloop.replay --json > state.json # feed the dashboard directly
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from ..config import load
from .runner import Replay

COLORS = {
    "presumptively_allowable": "\033[32m",
    "presumptively_unallowable": "\033[31m",
    "missing_documentation": "\033[33m",
    "requires_allocation": "\033[36m",
    "requires_prior_approval": "\033[35m",
    "conflicts_with_award_terms": "\033[91m",
    "requires_human_determination": "\033[94m",
}
RESET = "\033[0m"
BOLD = "\033[1m"


def _paint(text: str, color: str, plain: bool) -> str:
    return text if plain else f"{color}{text}{RESET}"


def _bold(text: str, plain: bool) -> str:
    return _paint(text, BOLD, plain)


def _render(d: dict[str, Any], plain: bool) -> None:
    color = COLORS.get(d["determination"], "")
    print(f"\n  {_paint(d['determination'].upper().replace('_', ' '), color + BOLD, plain)}"
          f"   {d['txn_id']}")
    for citation in d["citations"]:
        print(f"    ├─ {citation['label']}  {citation['title']}")
    if d.get("award_term"):
        print(f"    ├─ award term {_paint(d['award_term'], BOLD, plain)}")
    print(f"    └─ {d['rationale']}")
    for split in d.get("splits", []):
        cites = ", ".join(c["label"] for c in split["citations"]) or "—"
        print(f"       • ${split['amount']:>9,.2f}  "
              f"{_paint(split['determination'], COLORS.get(split['determination'], ''), plain)}"
              f"  [{cites}]")
    if d.get("question_for_human"):
        print(f"    {_paint('? ASKS A HUMAN:', BOLD, plain)} {d['question_for_human']}")
        for option in d.get("options", []):
            print(f"       - \"{option['answer']}\" -> {option['determination']} ({option['citation']})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grantloop.replay", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", help="path to a scenario file")
    parser.add_argument("--pace", type=float, default=0.0,
                        help="seconds between transactions, for narrating on camera")
    parser.add_argument("--dlq", metavar="TXN_ID",
                        help="force this transaction's handler to fail, to show retry and DLQ")
    parser.add_argument("--redeliver", action="store_true",
                        help="publish every event twice, proving exactly-once handling")
    parser.add_argument("--json", action="store_true", help="emit API-shaped state, nothing else")
    parser.add_argument("--plain", action="store_true", help="no ANSI color")
    args = parser.parse_args(argv)

    replay = Replay(args.seed, fail_txn=args.dlq, redeliver=args.redeliver)

    if args.json:
        replay.run()
        json.dump(replay.api_state(), sys.stdout, indent=2)
        print()
        return 0

    cfg = load()
    print(f"{_bold('GrantLoop replay', args.plain)}  "
          f"ruleset {replay.ruleset.version}  "
          f"citations {'verified' if replay.ruleset.citations_verified else 'UNVERIFIED'}  "
          f"mode {cfg.describe()['mode']}")
    print(f"award {replay.seed['notice_of_award']['award_id']}  "
          f"period {replay.seed['notice_of_award']['period_of_performance']['start']} "
          f"to {replay.seed['notice_of_award']['period_of_performance']['end']}")

    seen = 0

    def on_event(_: dict[str, Any]) -> None:
        nonlocal seen
        while seen < len(replay.result.determinations):
            _render(replay.result.determinations[seen], args.plain)
            seen += 1
        if args.pace:
            time.sleep(args.pace)

    result = replay.run(on_event=on_event)

    summary = result.summary()
    print(f"\n{_bold('—', args.plain)} {summary['transactions']} transactions, "
          f"{summary['events']} events, {summary['escalations']} escalated, "
          f"{summary['dead_letters']} dead-lettered")
    if result.dead_letters:
        print(f"\n{_bold('Dead letter queue', args.plain)}")
        for item in result.dead_letters:
            print(f"  {item['txn_ref']}  {item['attempts']} attempts  {item['last_error']}")
    missing = set(replay.ruleset.determination_values) - set(summary["determinations_by_value"])
    if missing and not args.dlq:
        print(f"\n  warning: these determinations never fired: {sorted(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
