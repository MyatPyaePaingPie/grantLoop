"""Gemini drafts the question a human is asked when the fleet escalates.

The division of labour matters and is the reason a model appears here at all.

The *determination* is deterministic: which of the seven values a cost lands on,
and which paragraph of 2 CFR 200 says so. That has to be reproducible and citable,
so no model touches it.

The *question* is not. When the Sentinel escalates it has to explain, to a specific
person looking at a specific invoice from a specific counterparty, what fact it is
missing and why only they can supply it. Writing that well is language work a rule
engine genuinely cannot do, and a canned string does it badly.

Offline, or when Vertex is unreachable, this falls back to the rule's own static
question. The fallback is never worse than what we had before the model existed,
which is what makes the dependency safe to have.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Any

from ..config import Config, load

PROMPT = textwrap.dedent("""\
    You write the question a compliance system asks a human when it cannot decide alone.

    A federal grant recipient's automated ledger review has stopped on one transaction.
    The determination and the regulation are already settled and are NOT yours to revisit.
    Your only job is to write the question the reviewer must answer.

    Transaction:
      vendor: {vendor}
      memo: {memo}
      amount: ${amount:,.2f}
      date: {date}

    Rule that fired: {rule_title} ({citation})
    Why it escalated: {rationale}
    The missing fact: {fact}

    Write ONE question, at most two sentences, that:
      - names the specific counterparty and what must be established about it
      - makes clear this is a fact about the world, not a judgement about the invoice
      - a program director with no regulatory training could act on today
      - states no determination and no legal advice

    Return only the question. No preamble, no quotes, no citation.
    """)


@dataclass
class DraftedQuestion:
    text: str
    source: str          # "gemini" | "fallback"
    model_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "source": self.source, "model_id": self.model_id}


class QuestionDrafter:
    """Drafts escalation questions, with a static fallback that always works."""

    def __init__(self, config: Config | None = None, client: Any | None = None) -> None:
        self.config = config or load()
        self._client = client
        self._tried = False
        #: Why the model lane last fell back. A silent fallback is correct
        #: behaviour and a terrible diagnostic: the whole project insists that
        #: failures be visible rather than swallowed, and this one was swallowed.
        self.last_error: str | None = None

    def _get_client(self) -> Any | None:
        """Vertex client, built once and only when a project is configured."""
        if self._client is not None or self._tried:
            return self._client
        self._tried = True
        if self.config.offline:
            return None
        try:
            from google import genai

            self._client = genai.Client(
                vertexai=True,
                project=self.config.project,
                location=self.config.location,
            )
        except Exception as exc:  # never let model plumbing break a determination
            self.last_error = f"client: {type(exc).__name__}: {exc}"[:400]
            self._client = None
        return self._client

    def draft(self, *, txn: dict[str, Any], rule_title: str, citation: str,
              rationale: str, fact: str, fallback: str) -> DraftedQuestion:
        client = self._get_client()
        if client is None:
            if self.last_error is None and self.config.offline:
                self.last_error = "offline: no GOOGLE_CLOUD_PROJECT configured"
            return DraftedQuestion(fallback, "fallback")

        prompt = PROMPT.format(
            vendor=txn.get("vendor", "unknown"),
            memo=txn.get("memo", ""),
            amount=float(txn.get("amount", 0.0)),
            date=txn.get("date", ""),
            rule_title=rule_title,
            citation=citation,
            rationale=rationale,
            fact=fact,
        )
        try:
            response = client.models.generate_content(
                model=self.config.model_id,
                contents=prompt,
                config={"temperature": 0.2, "max_output_tokens": 200},
            )
            text = (getattr(response, "text", "") or "").strip()
        except Exception as exc:
            self.last_error = f"generate: {type(exc).__name__}: {exc}"[:400]
            return DraftedQuestion(fallback, "fallback")

        if not _usable(text):
            self.last_error = f"unusable draft ({len(text)} chars): {text[:120]!r}"
            return DraftedQuestion(fallback, "fallback")
        self.last_error = None
        return DraftedQuestion(text, "gemini", self.config.model_id)


def _usable(text: str) -> bool:
    """Reject a draft rather than put a bad question in front of a human.

    A model that returns an empty string, an essay, or something that is not a
    question has failed at the one job it was given, and the static fallback is
    better than any of those.
    """
    if not text or len(text) > 600:
        return False
    if "?" not in text:
        return False
    return True
