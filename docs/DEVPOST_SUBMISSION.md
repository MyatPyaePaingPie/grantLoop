# Devpost submission — draft v0 (Pooof)

**Status: DRAFT.** Figures and claims must match what actually ships. TODO markers = filled at submission time. Nothing here is final copy until the demo video exists.

---

## Project name

GrantLoop

## Track

The Taskmaster

## Tagline (one line)

The grant application and the award are the same living object — agents enforce what you promised, from first draft to audit-ready.

## Inspiration

Small nonprofits win federal grants and then drown in them. A 2-person org that lands a $250K award inherits 2 CFR 200: allowability rules on every expense, SF-425 filings on a deadline, and a "high-risk recipient" designation waiting if they slip. Grant-writing AI tools abandon them at the moment of victory; compliance dashboards start from scratch after it, knowing nothing about what was promised. Nobody closes the loop. We built the loop.

## What it does

- **Application** — drafts against the org's own knowledge base and catches inconsistencies between narrative and budget before submission (our seed scenario: narrative promises 120 youth at a 1:10 ratio; the budget funds 2 mentors at 0.5 FTE — flagged, three concrete resolutions offered).
- **Covenant (award handoff)** — diffs the Notice of Award against the proposal and converts the result into machine-readable obligations. In our demo the agency cuts participant support $30k→$18k and outreach $12k→$8k while accepting the 120-youth performance target *unchanged*. Covenant says so out loud on award day, instead of the org discovering it at the first performance report.
- **Ledger Sentinel** — watches the transaction stream and classifies every expense into a 7-value determination taxonomy under 2 CFR 200 (allowable, unallowable, missing documentation, requires allocation, requires prior approval, conflicts with award terms, requires human determination). Not a yes/no filter: seven distinct behaviors on screen.
- **Reporting** — assembles the SF-425 from actual ledger state, every figure traceable to its transactions, then stops and waits for the Executive Director to certify. The system assembles; a human certifies.
- **Renewal** — the next application pulls verified performance and clean-compliance evidence forward. Compliance record becomes competitive advantage. The loop closes.

## How we built it

- **Gemini `gemini-3.5-flash`** via Vertex AI (location `global`) behind a single `MODEL_ID` env var.
- **Google ADK** for the agent fleet.
- **Two Cloud Run services**, deliberately not five: an orchestrator (Application, Covenant, Reporting, Intake) and a separate `ledger-sentinel`. The Sentinel is the only push-subscription, high-volume, retry-heavy component — isolating it demonstrates retry/DLQ isolation honestly; merging the four human-paced agents avoids four cold starts and four failure surfaces on a six-day clock. <!-- TODO: confirm final deploy matches -->
- **Pub/Sub** event bus between all five agents: no agent calls another agent; every transition is an event with a `causation_id`; every handler is idempotent (dedupe doc written in the same transaction as the output); DLQ after 5 attempts lands in a *visible* exception panel.
- **Firestore** as the obligation store — every obligation carries `source` (document + locator + quoted text) and `award_delta`, so lineage is a graph query, not a story we tell.
- **Dashboard**: zero-dependency static SPA served by the orchestrator; replay mode renders the deterministic seed, live mode renders Firestore state through a read API with identical shapes.

## Data sources

- 2 CFR Part 200 (Uniform Guidance) — allowability rules encoded as a versioned ruleset, every citation verified against eCFR before it renders on screen. <!-- TODO: confirm verification pass completed -->
- A fully synthetic demo scenario (Riverbend Youth Services): org profile, application, Notice of Award, and a 7-transaction ledger stream where each determination value fires exactly once. All simulated; the UI carries a permanent SIMULATED banner.

## Challenges we ran into

- **Model availability is a deployment fact, not a docs fact.** Gemini 3.x IDs 404'd region-by-region; only live probes against our own project settled what we could use (`gemini-3.5-flash` on `global`; nothing 3.x on `us-central1`). Everything model-facing went behind one env var the same day.
- **A confidently wrong CFR citation is worse than none.** Our allowability ruleset shipped marked `VERIFICATION_STATUS: DRAFT` and the UI refuses to render citations until the eCFR verification pass flips a flag.
- <!-- TODO: add 1-2 real build challenges from the final week -->

## Accomplishments we're proud of

- The award-handoff moment: the system catching "they cut the money and kept the promise" autonomously.
- An event-driven fleet that is demonstrably not a chatbot with steps — causation chains, idempotency, and a DLQ you can point at.
- Human-authority boundary held everywhere it matters: certification is a disabled button for everyone but the certifying official.

## What we learned

<!-- TODO: write honestly at the end — current candidates: model availability probing, verification-gated rendering, two-services-over-five reasoning -->

## What's next

Real bookkeeping integrations (QuickBooks class data), the single-audit prep trail, and multi-award support — the same obligation graph, more sources of truth.

## Built with

`gemini-3.5-flash` · Vertex AI · Google ADK · Cloud Run · Pub/Sub · Firestore · Cloud Build · vanilla JS

## Links

- Repo: https://github.com/MyatPyaePaingPie/grantLoop
- Live/hosted URL: <!-- TODO -->
- Demo video: <!-- TODO -->
- Architecture diagram: <!-- TODO: required artifact -->

## Checklist against submission requirements

- [ ] Category selected (Taskmaster)
- [ ] Hosted project URL or proof of GCP deployment
- [ ] Text description: features ✓ technologies ✓ data sources ✓ learnings (TODO)
- [ ] Public repo with reproducible setup README
- [ ] Architecture diagram
- [ ] ~4-min demo video showing backend on Google Cloud
- [ ] Bonus: published content with #AllThingsAgenticHackathon
