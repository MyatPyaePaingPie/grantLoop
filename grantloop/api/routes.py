"""Orchestrator read API — the routes, independent of any web framework.

One route table, two adapters (stdlib dev server, ASGI for Cloud Run). Keeping the
payload logic here means the two servers cannot drift, which matters because the
demo is recorded against one and deployed on the other.

Shapes are fixed by dashboard/READ_API_PROPOSAL.md: live mode must return exactly
what seed mode returns, so the dashboard switches with a base-URL swap and no
rendering changes.
"""

from __future__ import annotations

from typing import Any, Callable

from ..config import Config, load
from ..replay import Replay


class Orchestrator:
    """Serves award, ledger and exception state.

    Today it is backed by the replay engine, which runs the real Sentinel over the
    seeded ledger. When Firestore lands, only `_state` changes — the routes and
    their shapes do not, which is the point of pinning them now.
    """

    def __init__(self, *, config: Config | None = None, seed_path: str | None = None,
                 fail_txn: str | None = None) -> None:
        self.config = config or load()
        self._seed_path = seed_path
        self._fail_txn = fail_txn
        self._cache: dict[str, Any] | None = None
        self._drafter: Any = None

    def _state(self) -> dict[str, Any]:
        if self._cache is None:
            replay = Replay(self._seed_path, fail_txn=self._fail_txn)
            replay.run()
            self._cache = replay.api_state()
            self._ruleset_version = replay.ruleset.version
            self._drafter = replay.sentinel.drafter
        return self._cache

    def refresh(self) -> None:
        """Re-run the fleet. The dashboard's replay button calls this."""
        self._cache = None
        self._state()

    # ---- routes -----------------------------------------------------------

    def health(self) -> dict[str, Any]:
        state = self._state()
        return {
            "status": "ok",
            **self.config.describe(),
            "ruleset_version": self._ruleset_version,
            "citations_verified": state["health"]["citations_verified"],
            # Say what is actually serving the data. This read "firestore"
            # whenever a project was configured, which was a lie in every
            # deployment that had not yet been wired to Firestore.
            "source": self._source,
            "model_lane": self._model_lane(),
        }

    @property
    def _source(self) -> str:
        return "replay"

    def _model_lane(self) -> dict[str, Any]:
        """Whether Gemini is actually answering, and why not when it is not.

        A fallback is correct behaviour, but an invisible fallback means the
        model requirement can silently go unmet in production while every screen
        still looks right.
        """
        drafter = self._drafter
        used = [t.get("question_source") for t in self._state()["ledger"]["transactions"]
                if t.get("question_for_human")]
        return {
            "configured": not self.config.offline,
            "questions_drafted_by": sorted(set(used)) or ["none"],
            "last_error": getattr(drafter, "last_error", None),
        }

    def award(self) -> dict[str, Any]:
        return self._state()["award"]

    def ledger(self, limit: int = 50) -> dict[str, Any]:
        state = self._state()["ledger"]
        return {**state, "transactions": state["transactions"][:limit]}

    def exceptions(self) -> dict[str, Any]:
        return self._state()["exceptions"]

    def report_current(self) -> dict[str, Any]:
        """SF-425 draft with every line traceable to the transactions behind it.

        Uncertified by construction: 2 CFR 200.415(a) requires a named official to
        certify, so the API exposes the draft and the certification gate, never a
        filed report.
        """
        ledger = self._state()["ledger"]["transactions"]
        lines: dict[str, dict[str, Any]] = {}
        for txn in ledger:
            for determination, amount in _portions(txn):
                bucket = _report_bucket(determination)
                entry = lines.setdefault(bucket, {"amount": 0.0, "source_txn_ids": []})
                entry["amount"] += amount
                if txn["txn_id"] not in entry["source_txn_ids"]:
                    entry["source_txn_ids"].append(txn["txn_id"])
        unresolved = [t["txn_id"] for t in ledger
                      if {d for d, _ in _portions(t)} & {"requires_human_determination",
                                                        "missing_documentation",
                                                        "requires_prior_approval",
                                                        "conflicts_with_award_terms"}]
        return {
            "form": "SF-425",
            "certified": False,
            "certification_gate": {
                "required": True,
                "citation": {"section": "200.415", "paragraph": "(a)",
                             "title": "Required certifications",
                             "label": "2 CFR 200.415(a)"},
                "statement": (
                    "By signing this report, I certify to the best of my knowledge and belief "
                    "that the report is true, complete, and accurate, and the expenditures, "
                    "disbursements and cash receipts are for the purposes and objectives set "
                    "forth in the terms and conditions of the Federal award."
                ),
                "signer_role": "official authorized to legally bind the recipient",
            },
            "lines": {k: {**v, "amount": round(v["amount"], 2)} for k, v in sorted(lines.items())},
            "total_reported": round(sum(v["amount"] for v in lines.values()), 2),
            "unresolved_exceptions": unresolved,
            "submission": {"mode": "simulated", "disclosed": True},
            "citations_verified": self._state()["ledger"]["citations_verified"],
        }


def _portions(txn: dict[str, Any]) -> list[tuple[str, float]]:
    """Every dollar of a transaction, paired with the determination it landed on.

    A split invoice contributes to more than one report line. Rolling the whole
    transaction into its top-level determination silently loses the remainder --
    for TXN-002 that is $828 of catering vanishing from the report while the
    dashboard promises every figure is traceable to its transaction.
    """
    if not txn.get("splits"):
        return [(txn["determination"], float(txn.get("amount", 0.0)))]
    return [(s["determination"], float(s["amount"])) for s in txn["splits"]]


def _report_bucket(determination: str) -> str:
    """Which SF-425 line a determination rolls up into."""
    return {
        "presumptively_allowable": "federal_share_of_expenditures",
        "requires_allocation": "pending_allocation",
        "missing_documentation": "pending_documentation",
        "requires_human_determination": "pending_determination",
        "requires_prior_approval": "pending_prior_approval",
        "conflicts_with_award_terms": "questioned_costs",
        "presumptively_unallowable": "questioned_costs",
    }[determination]


#: path -> (handler name, takes query params)
ROUTES: dict[str, str] = {
    "/api/health": "health",
    "/api/state/award": "award",
    "/api/state/ledger": "ledger",
    "/api/state/exceptions": "exceptions",
    "/api/state/report/current": "report_current",
}


def dispatch(orch: Orchestrator, path: str, query: dict[str, list[str]]) -> dict[str, Any] | None:
    handler_name = ROUTES.get(path)
    if handler_name is None:
        return None
    handler: Callable[..., dict[str, Any]] = getattr(orch, handler_name)
    if handler_name == "ledger":
        return handler(limit=int(query.get("limit", ["50"])[0]))
    return handler()
