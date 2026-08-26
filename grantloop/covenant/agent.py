"""Covenant Agent — turns a Notice of Award into an obligation model.

This is the award handoff, and it is the centrepiece of the demo. Everything it
produces is *derived* from the application and the award document. Nothing is read
from a hand-written delta list, because "the agency cut the money and kept the
promise" is only a finding if the agent found it.

Three things it does that a form-filler cannot:

1. Diffs awarded against proposed, per budget line and per performance target, and
   names the downstream effect of each change.
2. Catches the case the whole product exists for: a funding line reduced while the
   performance promise it paid for was accepted unchanged. Nobody's software flags
   that today, and the recipient discovers it at the first performance report.
3. Reconciles the award's stated federal share against its own budget lines, and
   raises an exception when they disagree rather than trusting the headline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: Budget lines that pay for a performance promise. Derived from the application's
#: own narrative in a fuller build; stated here because the demo's application is a
#: fixture rather than a parsed document.
FUNDS_PROMISE: dict[str, tuple[str, ...]] = {
    "BL-02": ("PP-1", "PP-2"),   # youth mentors -> enrolment and retention
    "BL-04": ("PP-1",),          # participant stipends -> youth enrolled
    "BL-07": ("PP-3",),          # convening budget -> convenings held
}


@dataclass
class Delta:
    obligation_ref: str
    status: str                  # reduced | increased | unchanged | condition_attached
    proposed_value: float
    awarded_value: float
    agency_note: str
    downstream_effect: str
    severity: str = "info"       # info | warning | critical

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_ref": self.obligation_ref,
            "status": self.status,
            "proposed_value": self.proposed_value,
            "awarded_value": self.awarded_value,
            "delta": round(self.awarded_value - self.proposed_value, 2),
            "agency_note": self.agency_note,
            "downstream_effect": self.downstream_effect,
            "severity": self.severity,
        }


@dataclass
class Obligation:
    obligation_id: str
    kind: str                    # budget_line | performance_promise
    description: str
    awarded_value: float
    conditions: list[str] = field(default_factory=list)
    funds_promises: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "kind": self.kind,
            "description": self.description,
            "awarded_value": self.awarded_value,
            "conditions": self.conditions,
            "funds_promises": self.funds_promises,
        }


@dataclass
class ObligationModel:
    award_id: str
    obligations: list[Obligation]
    deltas: list[Delta]
    exceptions: list[dict[str, Any]]
    period_of_performance: dict[str, str]

    @property
    def headline(self) -> dict[str, Any] | None:
        """The promise kept while its funding was cut. This is the demo's money shot."""
        for exception in self.exceptions:
            if exception["kind"] == "underfunded_promise":
                return exception
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "award_id": self.award_id,
            "period_of_performance": self.period_of_performance,
            "obligations": [o.to_dict() for o in self.obligations],
            "deltas": [d.to_dict() for d in self.deltas],
            "exceptions": self.exceptions,
            "headline": self.headline,
        }


class Covenant:
    def __init__(self, application: dict[str, Any], notice_of_award: dict[str, Any]):
        self.application = application
        self.noa = notice_of_award

    # ---- diffing ----------------------------------------------------------

    def _budget_deltas(self) -> list[Delta]:
        proposed = {l["line_id"]: l for l in self.application["budget_lines"]}
        awarded = {l["line_id"]: l for l in self.noa.get("awarded_budget_lines", [])}
        conditions = self.noa.get("conditions_by_line", {})
        deltas: list[Delta] = []

        for line_id, prop in proposed.items():
            award = awarded.get(line_id)
            if award is None:
                deltas.append(Delta(
                    obligation_ref=line_id, status="removed",
                    proposed_value=prop["amount"], awarded_value=0.0,
                    agency_note=f"{prop['cost_category']} not funded.",
                    downstream_effect="Every activity this line paid for is unfunded.",
                    severity="critical"))
                continue

            condition = conditions.get(line_id)
            if award["amount"] == prop["amount"]:
                if condition:
                    deltas.append(Delta(
                        obligation_ref=line_id, status="condition_attached",
                        proposed_value=prop["amount"], awarded_value=award["amount"],
                        agency_note=f"Funded in full with condition {condition} attached.",
                        downstream_effect=(
                            f"Ledger Sentinel must block spending against {line_id} until an "
                            f"approval artifact for {condition} exists."),
                        severity="warning"))
                continue

            reduced = award["amount"] < prop["amount"]
            deltas.append(Delta(
                obligation_ref=line_id,
                status="reduced" if reduced else "increased",
                proposed_value=prop["amount"], awarded_value=award["amount"],
                agency_note=f"{prop['cost_category']} "
                            f"{'reduced' if reduced else 'increased'}.",
                downstream_effect=self._budget_effect(line_id, prop, award, reduced),
                severity="warning" if reduced else "info"))
        return deltas

    def _budget_effect(self, line_id: str, prop: dict, award: dict, reduced: bool) -> str:
        promises = FUNDS_PROMISE.get(line_id, ())
        if not reduced:
            return "Additional funds available; no promise is at risk."
        base = (f"Cut of ${prop['amount'] - award['amount']:,.0f}. ")
        if "participant support" in prop["cost_category"].lower():
            base += ("Moving funds out of participant support requires prior written approval "
                     "under 2 CFR 200.308(f)(5). ")
        if promises:
            base += f"Directly funds {', '.join(promises)} — check those targets were reduced too."
        else:
            base += "Re-scope the activities this line paid for."
        return base

    def _performance_deltas(self) -> list[Delta]:
        proposed = {p["id"]: p for p in self.application["performance_promises"]}
        awarded = {p["id"]: p for p in self.noa.get("awarded_performance_targets", [])}
        deltas: list[Delta] = []
        for pid, prop in proposed.items():
            award = awarded.get(pid, prop)
            changed = award["target"] != prop["target"]
            deltas.append(Delta(
                obligation_ref=pid,
                status="reduced" if changed and award["target"] < prop["target"]
                       else "increased" if changed else "unchanged",
                proposed_value=prop["target"], awarded_value=award["target"],
                agency_note="Performance target accepted as proposed." if not changed
                            else "Performance target revised by the agency.",
                downstream_effect=(
                    f"{prop['metric']} remains a binding commitment at {award['target']}."
                    if not changed else
                    f"{prop['metric']} target moved to {award['target']}."),
                severity="info"))
        return deltas

    # ---- exceptions -------------------------------------------------------

    def _underfunded_promises(self, deltas: list[Delta]) -> list[dict[str, Any]]:
        """A promise kept whole while the line that pays for it was cut.

        This is the finding the product exists for. The recipient signs an award
        they cannot perform and finds out at the first performance report.
        """
        by_ref = {d.obligation_ref: d for d in deltas}
        findings: list[dict[str, Any]] = []
        for line_id, promises in FUNDS_PROMISE.items():
            budget = by_ref.get(line_id)
            if budget is None or budget.status != "reduced":
                continue
            for pid in promises:
                promise = by_ref.get(pid)
                if promise is None or promise.status != "unchanged":
                    continue
                cut = budget.proposed_value - budget.awarded_value
                pct = cut / budget.proposed_value * 100 if budget.proposed_value else 0
                findings.append({
                    "kind": "underfunded_promise",
                    "severity": "critical",
                    "budget_line": line_id,
                    "promise": pid,
                    "summary": (
                        f"{line_id} was cut {pct:.0f}% (${budget.proposed_value:,.0f} to "
                        f"${budget.awarded_value:,.0f}) while {pid} was accepted unchanged at "
                        f"{promise.awarded_value:,.0f}."),
                    "why_it_matters": (
                        "The agency reduced the money and kept the promise. Nothing in the award "
                        "says these are related, so the mismatch surfaces at the first "
                        "performance report unless it is caught on award day."),
                    "options": [
                        f"Request a revised target for {pid} in writing before drawing funds.",
                        f"Re-scope delivery so {pid} is achievable at the awarded amount.",
                        "Identify matching funds and document them as cost share.",
                    ],
                })
        return findings

    def _reconciliation(self) -> list[dict[str, Any]]:
        """Does the award's stated total match its own budget lines?"""
        lines = self.noa.get("awarded_budget_lines", [])
        if not lines:
            return []
        derived = sum(l["amount"] for l in lines)
        stated = self.noa.get("federal_share")
        if stated is None or derived == stated:
            return []
        return [{
            "kind": "award_total_mismatch",
            "severity": "critical",
            "summary": (
                f"The Notice of Award states a federal share of ${stated:,.0f}, but its own "
                f"budget lines sum to ${derived:,.0f} — a ${abs(derived - stated):,.0f} "
                "discrepancy."),
            "why_it_matters": (
                "Drawing funds against an award whose totals do not agree is how a recipient "
                "ends up with questioned costs it never chose. The discrepancy has to be "
                "resolved with the agency in writing before the first drawdown, not discovered "
                "at closeout."),
            "options": [
                "Request a corrected Notice of Award from the agency.",
                "Confirm in writing which figure governs before any drawdown.",
            ],
        }]

    # ---- entry point ------------------------------------------------------

    def build(self) -> ObligationModel:
        deltas = self._budget_deltas() + self._performance_deltas()
        conditions = self.noa.get("conditions_by_line", {})
        awarded_lines = {l["line_id"]: l for l in self.noa.get("awarded_budget_lines", [])}
        awarded_targets = {p["id"]: p for p in self.noa.get("awarded_performance_targets", [])}

        obligations = [
            Obligation(
                obligation_id=lid, kind="budget_line",
                description=line["cost_category"], awarded_value=line["amount"],
                conditions=[conditions[lid]] if lid in conditions else [],
                funds_promises=list(FUNDS_PROMISE.get(lid, ())),
            ) for lid, line in awarded_lines.items()
        ] + [
            Obligation(
                obligation_id=pid, kind="performance_promise",
                description=f"{target['metric']} ({target.get('cadence', 'annual')})",
                awarded_value=target["target"],
            ) for pid, target in awarded_targets.items()
        ]

        exceptions = self._underfunded_promises(deltas) + self._reconciliation()
        return ObligationModel(
            award_id=self.noa["award_id"],
            obligations=obligations,
            deltas=deltas,
            exceptions=exceptions,
            period_of_performance=self.noa.get("period_of_performance", {}),
        )
