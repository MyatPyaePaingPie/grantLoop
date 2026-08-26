"""Loader for the eCFR-verified allowability ruleset.

The ruleset is data, not code, on purpose: the citations were wrong once already
and the fix was a data edit rather than a deploy. `RuleSet.citations_verified`
gates rendering — the dashboard refuses to show a CFR number when it is false.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "schema" / "allowability_rules.v0.json"

# Titles for sections cited at paragraph level, where the section's own title is too
# coarse to be honest on screen. 200.403 is the clearest case: citing "Factors
# affecting allowability" when you mean "the receipt is missing" tells the viewer
# nothing.
PARAGRAPH_TITLES: dict[tuple[str, str], str] = {
    ("200.403", "(g)"): "Costs must be adequately documented",
    ("200.403", "(h)"): "Costs must be incurred during the approved budget period",
    ("200.414", "(f)"): "De minimis indirect cost rate",
    ("200.438", "(a)"): "Entertainment costs",
    ("200.438", "(b)"): "Prizes and challenges",
    ("200.439", "(b)"): "Rules of allowability for capital expenditures",
    ("200.453", "(c)"): "Computing devices as direct costs",
    ("200.454", "(c)"): "Civic and community organization memberships",
    ("200.454", "(d)"): "Country, social and dining club memberships",
    ("200.454", "(e)"): "Memberships in organizations whose primary purpose is lobbying",
    ("200.475", "(e)"): "Commercial air travel",
    ("200.308", "(f)"): "Revisions requiring prior approval",
}

# Sections cited by the engine that are not themselves allowability rules.
SUPPORTING_TITLES: dict[str, str] = {
    "200.208": "Specific conditions",
    "200.308": "Revision of budget and program plans",
    "200.334": "Record retention requirements",
    "200.403": "Factors affecting allowability of costs",
    "200.415": "Required certifications",
}


@dataclass(frozen=True)
class Citation:
    section: str
    title: str
    paragraph: str | None = None

    @property
    def label(self) -> str:
        para = self.paragraph or ""
        return f"2 CFR {self.section}{para}"

    def to_dict(self) -> dict[str, str | None]:
        return {
            "section": self.section,
            "paragraph": self.paragraph,
            "title": self.title,
            "label": self.label,
        }


class RuleSet:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.rules = raw["rules"]
        self.determination_values = raw["determination_values"]
        self._by_id = {r["id"]: r for r in self.rules}

    @property
    def citations_verified(self) -> bool:
        return str(self.raw.get("VERIFICATION_STATUS", "")).startswith("VERIFIED")

    @property
    def version(self) -> str:
        return self.raw["schema_version"]

    def by_id(self, rule_id: str) -> dict[str, Any]:
        return self._by_id[rule_id]

    def citation(self, rule_id: str, paragraph: str | None = None) -> Citation:
        rule = self._by_id[rule_id]
        return Citation(
            section=rule["section"],
            title=rule["title"],
            paragraph=paragraph if paragraph is not None else rule.get("paragraph"),
        )

    def cite(self, section: str, paragraph: str | None = None) -> Citation:
        """Build a citation from a bare section number, with the most precise title.

        Paragraph-level titles win over section-level ones. A rule's title is only
        borrowed when the rule actually owns that section at section level, so
        citing 200.403(g) never inherits a title from an unrelated rule that
        happens to hang off the same section.
        """
        if paragraph and (section, paragraph) in PARAGRAPH_TITLES:
            return Citation(section=section, title=PARAGRAPH_TITLES[(section, paragraph)],
                            paragraph=paragraph)
        if section in SUPPORTING_TITLES:
            return Citation(section=section, title=SUPPORTING_TITLES[section], paragraph=paragraph)
        for rule in self.rules:
            if rule["section"] == section and not rule.get("paragraph"):
                return Citation(section=section, title=rule["title"], paragraph=paragraph)
        return Citation(section=section, title="", paragraph=paragraph)

    def matching(self, text: str) -> list[dict[str, Any]]:
        """Rules whose trigger keywords appear in the transaction text.

        Longest keyword first so 'gift card to participant' beats 'gift card'.
        """
        haystack = text.lower()
        hits = []
        for rule in self.rules:
            words = sorted(rule.get("trigger_keywords") or [], key=len, reverse=True)
            matched = [w for w in words if w.lower() in haystack]
            if matched:
                hits.append((len(max(matched, key=len)), rule, matched))
        hits.sort(key=lambda h: h[0], reverse=True)
        return [{"rule": r, "matched": m} for _, r, m in hits]

    def with_date_rule(self, name: str) -> list[dict[str, Any]]:
        return [r for r in self.rules if r.get("date_rule") == name]


def load_ruleset(path: str | Path | None = None) -> RuleSet:
    p = Path(path) if path else DEFAULT_PATH
    return RuleSet(json.loads(p.read_text()))
