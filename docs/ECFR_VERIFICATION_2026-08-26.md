# eCFR verification pass — allowability ruleset

✅ **done** — every citation in `schema/allowability_rules.v0.json` is now checked against the regulation text. Four were wrong. They are fixed.

**Source of truth:** eCFR title 2, part 200, point-in-time snapshot **2026-08-01**, pulled from the versioner API on 2026-08-26.
Structure endpoint gave the section identifiers and official labels; the full part text was parsed and every claim read against it.

```
https://www.ecfr.gov/api/versioner/v1/structure/2026-08-01/title-2.json
https://www.ecfr.gov/api/versioner/v1/full/2026-08-01/title-2.xml?subtitle=A&chapter=II&part=200
```

## Headline

All 25 section numbers cited existed. That is the easy half. Four rules made claims the regulation does not support, and one of them would have put a wrong section number on screen during the demo.

| # | Rule | Was | Is | Why it matters |
|---|---|---|---|---|
| 1 | `R-474-TRAVEL` | § 200.474 "Travel costs" | **§ 200.475** Travel costs | 200.474 is *Transportation costs* — goods, not staff. Wrong number on screen. |
| 2 | `R-454-MEMB` | civic memberships "require prior approval" | **200.454(c): allowable** | Directly affects the chamber-dues demo beat. |
| 3 | `R-456-PSC` | participant support "allowable with prior approval" | **allowable, no prior approval** | Prior approval attaches to transferring funds *out*, 200.308(f)(5). |
| 4 | `R-334-RETENTION` | § 200.334 for a missing receipt | **§ 200.403(g)** | 200.334 is retention *duration*. Wrong hook entirely. |

## The travel one is the dangerous one

<details>
<summary>Evidence</summary>

From the eCFR Subpart E section list:

```
200.474 - Transportation costs.
200.475 - Travel costs.
```

The ruleset also cited `200.474(b)` for the lowest-available-airfare rule. In the actual regulation
that rule is **200.475(e)(1)**, and (e)(1)(i)–(v) enumerate the five exceptions. 200.475(b) is
*Lodging and subsistence*. So the paragraph was wrong too.

</details>

## Confirmed, not changed

- **De minimis indirect rate is 15% of MTDC**, at **200.414(f)**. Fizz was right to refuse to write this from memory — the 2024 OMB revision raised it from 10%. Now encoded as a structured field with the ceiling, base and citation.
- **200.423 in full:** "The cost of alcoholic beverages is unallowable." No exception, no threshold. The split beat is sound.
- **200.208(b)–(c)** supports the `never_say` framing exactly. An agency *may* impose specific conditions; nothing is automatic.
- **200.415(a)** carries the literal certification language the Reporting Agent needs. Quote it verbatim.

## Two things the ruleset was missing

**200.438 is "Entertainment and prizes."** Paragraph (b) makes prizes and challenges *allowable* on the
same two-part test entertainment fails — specific programmatic purpose, and included in the Federal
award. A ruleset that only knows (a) will wrongly reject a youth incentive prize.

**200.453 covers computing devices.** Paragraph (c) allows charging them as direct costs when they are
essential and allocable but not solely dedicated to the award. This changes the laptop beat, below.

## ✅ Two determination questions, both now settled

<details>
<summary>TXN-005 — the laptop block does not hold on CFR alone (resolved)</summary>

Four laptops at $6,400 is $1,600 a unit. That is below the **$10,000** special-purpose prior-approval
threshold at 200.439(b)(2), and 200.453(c) expressly permits charging computing devices as direct costs
when they are essential and allocable but not solely dedicated to the award.

So the Uniform Guidance does **not** block this purchase. Award term **SC-2** does.

Resolved by aligning the seed to `DEMO_SCRIPT.md`: the determination is now
`conflicts_with_award_terms`, because the conflict is with the award, not the regulation. The Sentinel
leads with SC-2 and cites the CFR as context.

This makes the beat sharper, not weaker. "The regulation permits this; your award does not" is a better
demonstration of the provenance chain than a generic CFR rejection — and it is the one moment where a
judge who knows this material would otherwise catch us.

</details>

<details>
<summary>TXN-006 — pre-award determination (resolved)</summary>

200.458 makes pre-award costs allowable only to the extent they would have been allowable after the
start date **and** only with the written approval of the Federal agency. On a plain reading that is
`requires_prior_approval`, which is what `DEMO_SCRIPT.md` already had.

Seed updated to match. All seven determination values still fire exactly once.

</details>

## Verified section inventory

<details>
<summary>All 25 sections, with official eCFR labels</summary>

| Cited | Official label | Subpart |
|---|---|---|
| 200.1 | Definitions | A |
| 200.208 | Specific conditions | C |
| 200.308 | Revision of budget and program plans | D |
| 200.334 | Record retention requirements | D |
| 200.403 | Factors affecting allowability of costs | E |
| 200.404 | Reasonable costs | E |
| 200.405 | Allocable costs | E |
| 200.414 | Indirect costs | E |
| 200.415 | Required certifications | E |
| 200.421 | Advertising and public relations | E |
| 200.423 | Alcoholic beverages | E |
| 200.430 | Compensation—personal services | E |
| 200.431 | Compensation—fringe benefits | E |
| 200.432 | Conferences | E |
| 200.434 | Contributions and donations | E |
| 200.438 | Entertainment and prizes | E |
| 200.439 | Equipment and other capital expenditures | E |
| 200.441 | Fines, penalties, damages and other settlements | E |
| 200.445 | Goods or services for personal use | E |
| 200.450 | Lobbying | E |
| 200.453 | Materials and supplies costs, including costs of computing devices | E |
| 200.454 | Memberships, subscriptions, and professional activity costs | E |
| 200.456 | Participant support costs | E |
| 200.458 | Pre-award costs | E |
| 200.475 | Travel costs | E |

Titles that were wrong in the draft and are now corrected: 200.414 (was "Indirect (F&A) costs"),
200.438 (was "Entertainment costs"), 200.453 (was "Materials and supplies"),
200.334 (was "Retention of records"), 200.475 (was cited as 200.474).

</details>

## No universal 10% rule

`R-BUDGET-OVER` now says this explicitly. Under 200.308 an agency **may, at its option** restrict
transfers among direct cost categories, and only when the Federal share exceeds the simplified
acquisition threshold **and** the cumulative transfer exceeds 10% of the total approved budget.
Read the award terms. Absent an award term, report the deviation under 200.308(b) rather than
asserting a violation.

## Re-verification

The snapshot date is pinned in `verified_against.snapshot_date` inside the ruleset. If that date moves,
re-run the two API calls above and re-read the four sections that carry hard numbers: 200.414(f) for
the de minimis ceiling, 200.439(b)(2) for the $10,000 threshold, 200.308 for the transfer restriction,
and 200.334 for the retention period.
