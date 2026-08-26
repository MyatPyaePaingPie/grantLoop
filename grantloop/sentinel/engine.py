"""Ledger Sentinel — classifies a transaction into one of seven determinations.

Deliberately deterministic. The seven values are reached by rules over verified
citations and the award's own terms, not by asking a model what it thinks. A model
is useful for *drafting the human-facing question* on an escalation; it is not
useful for deciding whether a cost is allowable, because that decision has to be
defensible against a citation and reproducible on record day.

Precedence is the whole design. It runs most-specific to least:

1. Period of performance   — a date fact beats every category argument
2. Award specific conditions — the award can forbid what the CFR permits
3. Documentation           — an undocumented cost cannot be judged on its merits
4. Splittable line items   — carve out the unallowable part, judge the remainder
5. Category rules          — keyword match into the verified ruleset
6. Fallback                — unmatched costs go to a human, never to "allowable"

Rule 6 matters: silence must not read as approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .rules import Citation, RuleSet


def first_sentence(note: str) -> str:
    """First real sentence of a rule note.

    Naive splitting on "." breaks immediately here, because every note opens with a
    citation like "200.453(a)-(b):" whose period is not a sentence boundary.
    """
    text = note.strip()
    for i, char in enumerate(text):
        if char != "." or i + 1 >= len(text):
            continue
        if text[i + 1] != " ":
            continue
        if i and text[i - 1].isdigit() and _looks_like_citation(text, i):
            continue
        return text[: i + 1]
    return text


def _looks_like_citation(text: str, dot: int) -> bool:
    """True when the period sits inside a section number such as 200.423."""
    head = text[max(0, dot - 4):dot]
    return head[-3:].isdigit() and len(head) >= 3


@dataclass
class Split:
    """One portion of a transaction with its own determination."""

    amount: float
    determination: str
    citations: list[Citation]
    rationale: str
    obligation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": round(self.amount, 2),
            "determination": self.determination,
            "citations": [c.to_dict() for c in self.citations],
            "rationale": self.rationale,
            "obligation_id": self.obligation_id,
        }


@dataclass
class Determination:
    txn_id: str
    determination: str
    splits: list[Split]
    rationale: str
    citations: list[Citation] = field(default_factory=list)
    question_for_human: str | None = None
    options: list[dict[str, Any]] = field(default_factory=list)
    award_term: str | None = None

    @property
    def escalated(self) -> bool:
        return self.determination == "requires_human_determination"

    def to_dict(self) -> dict[str, Any]:
        return {
            "txn_id": self.txn_id,
            "determination": self.determination,
            "splits": [s.to_dict() for s in self.splits],
            "citations": [c.to_dict() for c in self.citations],
            "rationale": self.rationale,
            "question_for_human": self.question_for_human,
            "options": self.options,
            "award_term": self.award_term,
        }


def _d(value: str) -> date:
    return date.fromisoformat(value)


class Sentinel:
    """Classifies transactions against the ruleset and one award's terms."""

    def __init__(self, ruleset: RuleSet, award: dict[str, Any], org: dict[str, Any] | None = None):
        self.rules = ruleset
        self.award = award
        self.org = org or {}
        self.pop = award.get("period_of_performance", {})
        self.conditions = award.get("specific_conditions", [])

    # ---- precedence steps -------------------------------------------------

    def _date_check(self, txn: dict[str, Any]) -> Determination | None:
        txn_date = _d(txn["date"])
        start, end = self.pop.get("start"), self.pop.get("end")
        if start and txn_date < _d(start):
            rule = self.rules.by_id("R-458-PREAWARD")
            return Determination(
                txn_id=txn["txn_id"],
                determination=rule["default"],
                splits=[],
                citations=[self.rules.citation("R-458-PREAWARD"),
                           self.rules.cite("200.403", "(h)")],
                rationale=(
                    f"Dated {txn['date']}, before the period of performance opens on {start}. "
                    "Pre-award costs are allowable only to the extent they would have been "
                    "allowable after the start date, and only with written agency approval."
                ),
            )
        if end and txn_date > _d(end):
            return Determination(
                txn_id=txn["txn_id"],
                determination="conflicts_with_award_terms",
                splits=[],
                citations=[self.rules.cite("200.403", "(h)")],
                rationale=(
                    f"Dated {txn['date']}, after the period of performance closes on {end}. "
                    "All costs other than administrative closeout costs must be incurred "
                    "during the approved budget period."
                ),
            )
        return None

    def _award_condition_check(self, txn: dict[str, Any]) -> Determination | None:
        """The award can forbid what the regulation permits. That is the whole point."""
        text = f"{txn.get('memo','')} {txn.get('gl_account','')}".lower()
        for condition in self.conditions:
            if condition.get("imposed_measure") != "prior_approval_required":
                continue
            subject = _condition_subject(condition.get("text", ""))
            if not subject or subject not in text:
                continue
            if _has_approval_artifact(txn, condition):
                continue
            return Determination(
                txn_id=txn["txn_id"],
                determination="conflicts_with_award_terms",
                splits=[],
                award_term=condition["condition_id"],
                citations=[self.rules.cite("200.453", "(c)"),
                           self.rules.cite("200.208")],
                rationale=(
                    f"Blocked by award term {condition['condition_id']}: "
                    f"\"{condition['text']}\" No prior-approval artifact is attached. "
                    "Note the regulation does not forbid this purchase — at "
                    f"{_unit_hint(txn, self.org)} it sits below both the 2 CFR 200.439(b)(2) "
                    "$10,000 threshold and the organization's own capitalization threshold, "
                    "so 200.453(c) would permit it as a computing device. The award is stricter "
                    "than the regulation, and the award governs."
                ),
            )
        return None

    def _documentation_check(self, txn: dict[str, Any]) -> Determination | None:
        if txn.get("attachments"):
            return None
        return Determination(
            txn_id=txn["txn_id"],
            determination="missing_documentation",
            splits=[],
            citations=[self.rules.cite("200.403", "(g)")],
            rationale=(
                "No supporting documentation is attached. A cost must be adequately "
                "documented to be allowable, so this cannot be judged on its merits yet. "
                "This is not a finding of unallowability — attach the receipt and it "
                "will be reclassified."
            ),
        )

    def _split_check(self, txn: dict[str, Any]) -> Determination | None:
        lines = txn.get("line_detail")
        if not lines:
            return None
        carve, remainder = [], []
        for line in lines:
            hits = self.rules.matching(line.get("desc", ""))
            splittable = next((h for h in hits if h["rule"].get("splittable")), None)
            (carve if splittable else remainder).append((line, splittable))
        if not carve:
            return None

        splits: list[Split] = []
        for line, hit in carve:
            rule = hit["rule"]
            behavior = rule.get("split_behavior", {})
            splits.append(Split(
                amount=line["amount"],
                determination=behavior.get("carve_out", rule["default"]),
                citations=[self.rules.citation(rule["id"])],
                rationale=f"{line['desc']} — {rule['title']}. {first_sentence(rule['note'])}",
            ))
        behavior = carve[0][1]["rule"].get("split_behavior", {})
        for line, _ in remainder:
            splits.append(Split(
                amount=line["amount"],
                determination=behavior.get("remainder_determination", "requires_human_determination"),
                citations=[self.rules.cite(s.split("(")[0], _para(s))
                           for s in behavior.get("remainder_citations", [])],
                rationale=(
                    f"{line['desc']} — not auto-approved because it shared an invoice with an "
                    "unallowable item. Judged on its own merits."
                ),
            ))
        return Determination(
            txn_id=txn["txn_id"],
            determination="presumptively_unallowable",
            splits=splits,
            citations=[self.rules.citation(carve[0][1]["rule"]["id"])],
            question_for_human=behavior.get("remainder_question"),
            rationale=(
                f"Invoice split into {len(splits)} portions. "
                f"${sum(s.amount for s in splits if s.determination == 'presumptively_unallowable'):,.2f} "
                "carved out as unallowable; the remainder is routed for review rather than "
                "approved by association."
            ),
        )

    def _category_check(self, txn: dict[str, Any]) -> Determination | None:
        text = f"{txn.get('memo','')} {txn.get('vendor','')} {txn.get('gl_account','')}"
        for hit in self.rules.matching(text):
            rule = hit["rule"]
            question = rule.get("human_question")
            if question and not self._org_knows(question["fact_required"]):
                return Determination(
                    txn_id=txn["txn_id"],
                    determination="requires_human_determination",
                    splits=[],
                    citations=[self.rules.citation(rule["id"])],
                    question_for_human=question["question"],
                    options=question["options"],
                    rationale=(
                        f"Matched {rule['title']} on {hit['matched']}. The determination turns on a "
                        "fact about the counterparty that is not present in the transaction, so the "
                        "Sentinel asks rather than guesses."
                    ),
                )
            return Determination(
                txn_id=txn["txn_id"],
                determination=rule["default"],
                splits=[],
                citations=[self.rules.citation(rule["id"])],
                rationale=f"Matched {rule['title']} on {hit['matched']}. {first_sentence(rule['note'])}",
            )
        return None

    def _org_knows(self, fact: str) -> bool:
        return fact in (self.org.get("known_facts") or {})

    # ---- entry point ------------------------------------------------------

    def classify(self, txn: dict[str, Any]) -> Determination:
        for step in (self._date_check, self._award_condition_check,
                     self._documentation_check, self._split_check, self._category_check):
            result = step(txn)
            if result is not None:
                return result
        return Determination(
            txn_id=txn["txn_id"],
            determination="requires_human_determination",
            splits=[],
            citations=[self.rules.cite("200.403")],
            question_for_human=(
                "No allowability rule matched this transaction. Which cost category does it "
                "belong to, and does it meet the 200.403 factors?"
            ),
            rationale=(
                "Unmatched by every category rule. Routed to a human rather than defaulted to "
                "allowable — silence is not approval."
            ),
        )


def _condition_subject(text: str) -> str | None:
    """Pull the noun a prior-approval condition is about, e.g. 'equipment'."""
    for noun in ("equipment", "travel", "subaward", "consultant", "renovation", "vehicle"):
        if noun in text.lower():
            return noun
    return None


def _has_approval_artifact(txn: dict[str, Any], condition: dict[str, Any]) -> bool:
    marker = f"approval_{condition['condition_id'].lower()}"
    return any(marker in str(a).lower() or "approval" in str(a).lower()
               for a in txn.get("attachments", []))


def _unit_hint(txn: dict[str, Any], org: dict[str, Any]) -> str:
    qty = _leading_qty(txn.get("memo", ""))
    if qty and qty > 1:
        return f"${txn['amount'] / qty:,.0f} per unit"
    return f"${txn.get('amount', 0):,.0f}"


def _leading_qty(memo: str) -> int | None:
    token = memo.strip().split(" ")[0].lower().rstrip("x")
    return int(token) if token.isdigit() else None


def _para(section_with_para: str) -> str | None:
    if "(" not in section_with_para:
        return None
    return "(" + section_with_para.split("(", 1)[1]
