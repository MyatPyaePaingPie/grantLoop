# GrantLoop — revised plan (promise-to-proof)

Revised 2026-08-26 against Aria's corrections. Submission due Aug 31.

> **Most grant software remembers the documents. GrantLoop remembers the promises.**

## Thesis

The application and the award are the same living object. Lineage:

`NOFO -> application -> award -> transaction/evidence -> report -> renewal`

Differentiation is the **provenance chain**, not the agent count. Any team can
ship five agents this week. Nobody else can click a dollar on an SF-425 and walk
back to the sentence in the proposal that promised it.

## Corrections adopted (all of Aria's — all correct)

1. **No automatic high-risk claim.** Under 2 CFR 200.208 an agency *may* impose
   specific conditions: additional monitoring, additional/more frequent
   reporting, prior approval requirements, reimbursement-only payment,
   withholding authority to proceed. Encoded in
   `schema/allowability_rules.v0.json -> monitoring_consequences.never_say`.
2. **Allowability is a 7-value determination, not a boolean.** Encoded as
   `$defs.determination`. The seeded ledger has one transaction per value so all
   seven are visible in the demo.
3. **Alcohol beat is a split, not a rejection.** TXN-002: carve out the $412
   alcohol under 200.423, route the remaining $828 catering for program-purpose
   review. The split is more impressive than a rejection anyway.
4. **No implied auto-filing.** Reporting Agent assembles an evidence-backed
   package, requires named human certification (200.415), then exports with the
   submission explicitly labelled simulated.
5. **Five agents kept**, but each must earn it — see the earn-it table.

## Architecture decision — TWO Cloud Run services, not five

Aria asked me to validate five services rather than assume them. My call:

**One `orchestrator` service running Intake + Application + Covenant + Reporting
via ADK, plus one separate `ledger-sentinel` service.** Real Pub/Sub topics
between all five agents regardless.

Why not five: four of the agents are low-frequency, human-paced, and share the
same document-and-obligation working set. Five services buys four more cold
starts, four more deploy targets and four more failure surfaces to debug on a
six-day clock, and buys no isolation we actually need.

Why not one: the Ledger Sentinel has a genuinely different profile — it is the
only push-subscription, high-volume, retry-and-DLQ-heavy component, and it is
the one on screen during the showpiece. Splitting it is the honest demonstration
of decoupling and retry isolation, and it gives us a real DLQ panel to point at.

Decoupling is preserved where it counts: **no agent calls another agent.** Every
transition is a Pub/Sub event with `causation_id`, and every agent is idempotent
on `idempotency_key`. That is what the architecture score is actually measuring.
Say this reasoning out loud in the video — a defended two-service design scores
better than an undefended five.

Revisit if Day 3 shows the Reporting Agent's assembly step blocking the
orchestrator; splitting it later is one deploy.

## Each agent earns its slot

| Agent | Trigger | In -> Out | Persisted state | Auditable decision | Retry/idempotency | Handoff | Human authority |
|---|---|---|---|---|---|---|---|
| Intake | doc upload | file -> structured fields + confidence | `documents/{doc_id}` | extraction confidence per field | key = sha256(file) | `document.ingested`, `award.received` | low-confidence fields flagged |
| Application | `document.ingested` | org docs -> one narrative section + allowability-checked budget | `applications/{id}` | one consistency exception w/ 3 resolutions | key on (app_id, section) | `consistency.exception_raised` | **human resolves the exception** |
| Covenant | `award.received` | NOA + application -> obligation model | `obligations/{award_id}` | every award delta + downstream effect | key = (award_id, noa_doc_id) | `obligation_model.created`, `award.delta_detected` | human accepts the re-scope |
| Ledger Sentinel | `transaction.posted` | txn -> splits + determinations + citations | `determinations/{txn_id}` | 7-value determination w/ CFR + award-term cite | key = txn_id, DLQ after 5 | `determination.made` / `.escalated` | `requires_human_determination` |
| Reporting | `reporting.window_opened` | ledger state -> SF-425 draft + exceptions | `reports/{report_id}` | every line traceable to txns | key = report_id | `report.drafted` -> `.certified` -> `.exported` | **certification, 200.415** |

## Demo flow (the award handoff is the centerpiece)

1. **Application** finds the one inconsistency: narrative promises 120 youth at a
   1:10 ratio; the budget funds 2 mentors at 0.5 FTE. Routes to a human with
   three concrete resolutions.
2. **Award handoff — the money shot.** Upload the Notice of Award. Covenant
   diffs award against proposal and shows: participant support cut $30k -> $18k,
   outreach cut $12k -> $8k, equipment condition attached, **and performance
   targets accepted unchanged at 120 youth.** The agency cut the money and kept
   the promise. Then the fleet builds the obligation model, evidence plan and
   quarterly reporting calendar unprompted. Nobody is clicking through steps.
3. **Ledger Sentinel** on the live stream, seven transactions, seven different
   determinations. Alcohol split. Rent flagged for allocation. Laptops blocked
   against the award's own specific condition — CFR *and* award term cited.
   Pre-award registration caught by date. Chamber dues escalated as a question
   only a human can answer.
4. **Reporting** on the deadline event: SF-425 assembled from real ledger state,
   every figure clickable to its transaction, unresolved exceptions attached,
   then it stops and waits for the Executive Director to certify. Export labelled
   simulated.
5. **Renewal**: next application pulls verified performance and clean-compliance
   evidence forward. The loop closes.

## Scope — cut, confirmed

Cut: discovery, full proposal generation, real QuickBooks, real agency
submission. Intake is structured extraction only. Application Agent ships
exactly one consistency check. All simulated integrations disclosed on screen
and in the README.

## Schedule (Aug 26 -> 31)

| Day | Aria | Fizz |
|---|---|---|
| Aug 26 | **Unblock Gemini 3.x** (see below); enable Run/Firestore/Artifact Registry/Cloud Build; ADK hello-world deployed to Cloud Run | obligation schema, event contract, allowability ruleset, seeded scenario — **done, in `REPOS/grantloop/`**; next: verify every CFR cite against eCFR |
| Aug 27 | Pub/Sub topics + subscriptions from the contract; Firestore collections; Covenant Agent | Ledger Sentinel classification prompt + rule engine; deterministic replay CLI |
| Aug 28 | Wire full event flow end-to-end; idempotency + DLQ | Reporting Agent, SF-425 field mapping, line traceability |
| Aug 29 | Deploy hardening, architecture diagram, README repro steps, hosted test access | UI: award-delta view, determination queue, DLQ panel, lineage graph |
| Aug 30 | Bug triage, seed polish | Record the live unedited demo |
| Aug 31 | Final deploy check | Devpost text, screenshots, disclosure block, buffer |

## Submission checklist

- [ ] Live, unedited demo
- [ ] Hosted test access
- [ ] Clean architecture diagram
- [ ] Reproducible setup instructions
- [ ] Visible proof of Google Cloud deployment
- [ ] Failure/retry and human-approval behavior on screen (DLQ panel + certification gate)
- [ ] Clear disclosure of simulated integrations
- [ ] Gemini 3.5+, ADK, and >=1 Google Cloud infra service — **AT RISK, see below**

## Open risks

1. **BLOCKER — Gemini 3.x not reachable.** On `modelmind-491801`, only
   `gemini-2.5-flash` returns 200; every 3.x id 404s in us-central1 and global.
   The rules require Gemini 3.5+. Full evidence and the exact fix path in
   `REPOS/grantloop/docs/GCP_VALIDATION_2026-08-26.md`. Build behind a single
   `MODEL_ID` env var so the swap is one line.
2. **CFR citations are draft.** `allowability_rules.v0.json` is written from
   working knowledge and marked `VERIFICATION_STATUS: DRAFT`. Every section
   number must be checked against eCFR before it renders on screen. A confidently
   wrong citation in front of judges is worse than no citation. Do not hardcode
   the de minimis indirect rate from memory — it changed in the 2024 OMB revision.
3. **Deterministic replay path** — `seed/riverbend_scenario.json` is the fallback
   if the live bus stalls on record day. Wire the replay CLI by Day 2, not Day 5.
4. **Scope creep on the application side** — it is a cameo. One consistency check.
