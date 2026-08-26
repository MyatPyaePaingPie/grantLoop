"""The agent fleet as Google ADK agents.

The design point: ADK agents do not *decide* anything here. Each one wraps the
deterministic engine it owns as a tool, so the model plans and explains while the
regulation is applied by code that can be cited and reproduced.

That split is deliberate. An LLM agent asked directly whether a cost is allowable
gives a different answer on a different day, and a compliance product cannot ship
that. An LLM agent that must call `classify_transaction` to find out gives the same
answer every time and can tell you which paragraph produced it.

ADK is an optional dependency. Nothing in the offline path imports this module, so
the replay CLI and the test suite run with nothing installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import load
from ..covenant import Covenant
from ..sentinel import Sentinel, load_ruleset

from ..paths import SCENARIO as SEED


def _scenario() -> dict[str, Any]:
    return json.loads(SEED.read_text())


# ---- tools ---------------------------------------------------------------
# Plain functions with typed signatures and docstrings: ADK turns these into
# tool declarations, and the docstring is what the model reads to decide when to
# call them. They are written for that reader.


def classify_transaction(txn_id: str) -> dict[str, Any]:
    """Determine whether one transaction is an allowable charge to the award.

    Applies 2 CFR Part 200 and the award's own specific conditions, returning one
    of seven determinations with the citation that produced it. Use this for any
    question about whether a cost may be charged. Never answer that from memory:
    the determination must carry a citation.

    Args:
        txn_id: The transaction identifier, for example "TXN-002".

    Returns:
        The determination, its citations, any splits, and the rationale.
    """
    scenario = _scenario()
    txn = next((t for t in scenario["ledger_stream"]["transactions"]
                if t["txn_id"] == txn_id), None)
    if txn is None:
        return {"error": f"no transaction {txn_id}"}
    sentinel = Sentinel(load_ruleset(), scenario["notice_of_award"], scenario["org"])
    return sentinel.classify(txn).to_dict()


def build_obligation_model() -> dict[str, Any]:
    """Diff the Notice of Award against the application and derive the obligations.

    Returns every budget and performance delta, plus exceptions including any
    funding line that was cut while the performance promise it paid for was
    accepted unchanged. Use this to answer what the award changed and what the
    recipient is now committed to.

    Returns:
        Obligations, deltas, exceptions, and the headline finding if there is one.
    """
    scenario = _scenario()
    return Covenant(scenario["application"], scenario["notice_of_award"]).build().to_dict()


def lookup_allowability_rule(keyword: str) -> dict[str, Any]:
    """Find the 2 CFR 200 rules that govern a kind of cost.

    Use this before making any claim about a regulation. Every citation returned
    has been verified against the eCFR; citations from memory have not.

    Args:
        keyword: A cost description, for example "alcohol" or "membership dues".

    Returns:
        Matching rules with their section, title, default determination and note.
    """
    ruleset = load_ruleset()
    hits = ruleset.matching(keyword)
    return {
        "citations_verified": ruleset.citations_verified,
        "matches": [{
            "rule_id": h["rule"]["id"],
            "section": h["rule"]["section"],
            "title": h["rule"]["title"],
            "default_determination": h["rule"]["default"],
            "note": h["rule"]["note"],
            "matched_on": h["matched"],
        } for h in hits],
    }


TOOLS = [classify_transaction, build_obligation_model, lookup_allowability_rule]


# ---- agents --------------------------------------------------------------

COVENANT_INSTRUCTION = """\
You are the Covenant Agent for a federal grant recipient.

When an award arrives you call build_obligation_model and report what changed. Lead
with the most consequential finding rather than a list. If a funding line was cut
while the promise it paid for was accepted unchanged, that is the headline and you
say so plainly, because the recipient will otherwise discover it at the first
performance report.

You never state a dollar figure the tool did not return, and you never soften a
reconciliation exception. An award whose totals disagree with its own budget lines
is a problem to surface, not to average away.
"""

SENTINEL_INSTRUCTION = """\
You are the Ledger Sentinel for a federal grant recipient.

You do not decide allowability yourself. Call classify_transaction and report what
it determined, always naming the citation. If you are asked about a regulation, call
lookup_allowability_rule first; a citation you produced from memory is worse than no
citation at all.

When a determination is requires_human_determination, present the question and the
options exactly as returned. Do not resolve it. Some facts are facts about the world
that no amount of reasoning over an invoice can supply.

Silence is never approval. A cost you cannot classify is escalated, not allowed.
"""


def build_fleet() -> dict[str, Any]:
    """Construct the ADK agents. Requires google-adk and a configured project."""
    from google.adk.agents import Agent

    config = load()
    covenant = Agent(
        name="covenant",
        model=config.model_id,
        description="Derives the obligation model from a Notice of Award.",
        instruction=COVENANT_INSTRUCTION,
        tools=[build_obligation_model],
    )
    sentinel = Agent(
        name="ledger_sentinel",
        model=config.model_id,
        description="Classifies transactions against 2 CFR 200 and the award terms.",
        instruction=SENTINEL_INSTRUCTION,
        tools=[classify_transaction, lookup_allowability_rule],
    )
    orchestrator = Agent(
        name="grantloop",
        model=config.model_id,
        description="Carries a federal grant from application through award to reporting.",
        instruction=(
            "You coordinate the GrantLoop fleet. Route award questions to covenant and "
            "spending questions to ledger_sentinel. Never answer a compliance question "
            "yourself when a sub-agent owns it."
        ),
        sub_agents=[covenant, sentinel],
    )
    return {"orchestrator": orchestrator, "covenant": covenant, "ledger_sentinel": sentinel}
