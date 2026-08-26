# GrantLoop — Demo Video Script (v1, aligned to PLANS/GRANTLOOP_PLAN.md @ b35d4c1)

**Target:** ~4:00 min. Judging: 40% innovation/operational utility, 30% architecture, 30% demo + production readiness. Video MUST show the backend running on Google Cloud.

**Owner:** Pooof (Paing's machine). **Status:** v1 — beats and scenario figures locked to the plan doc. Voiceover lines drafted; CFR citations render ONLY after Aria Agent's eCFR verification clears `allowability_rules.v0.json` (currently `VERIFICATION_STATUS: DRAFT`).

**Everything model-facing sits behind one `MODEL_ID` env var** (Gemini 3.x blocker: swap is a one-liner when cleared).

---

## Beat sheet (mirrors plan doc §Demo flow, timed for 4:00)

### 0:00–0:20 — Cold open: the pain
- On screen: "A 2-person nonprofit wins a $250K federal grant. Now the hard part starts."
- VO: 2 CFR 200, SF-425 deadlines, high-risk designation for late reports, no grants manager. One botched award ends the org.
- No product on screen yet.

### 0:20–0:45 — Beat 1: Application catches its own inconsistency
- Application agent flags: narrative promises **120 youth at a 1:10 ratio**, but the budget funds **2 mentors at 0.5 FTE**. Routes to a human with three concrete resolutions.
- VO point: the system reads what you *promised*, not just what you wrote.

### 0:45–1:25 — Beat 2: Award handoff — THE MONEY SHOT
- Upload the Notice of Award. Covenant diffs award vs proposal, on screen:
  - participant support **$30k → $18k**
  - outreach **$12k → $8k**
  - equipment condition attached
  - performance targets accepted **unchanged at 120 youth**
- VO: "They cut the money. They kept the promise." (exact framing from plan doc)
- Then, unprompted: obligation model, evidence plan, quarterly reporting calendar build themselves. Nobody clicks through steps.

### 1:25–2:25 — Beat 3: Ledger Sentinel — seven transactions, seven determinations
Live stream over Pub/Sub (replay CLI drives the deterministic seed; doubles as record-day fallback). Each determination value fires exactly once:

| Transaction | Determination |
|---|---|
| Alcohol in event catering → split | `presumptively_unallowable` |
| Rent → flagged for allocation | `requires_allocation` |
| Laptops → blocked by the award's own equipment condition (CFR + award term cited) | `conflicts_with_award_terms` |
| Pre-award registration → caught by date | `requires_prior_approval` |
| Chamber dues → escalated, human-only call | `requires_human_determination` |
| (from seed) receipt-less expense | `missing_documentation` |
| (from seed) ordinary program cost sails through | `presumptively_allowable` |

- Show the DLQ/exception panel once: failed handler retries then lands visibly. Failure handling as a feature.
- NO CFR number renders unless verified (Aria Agent's pass).

### 2:25–3:00 — Beat 4: Reporting on the deadline event
- SF-425 assembled from real ledger state; **every figure clickable to its transaction**; unresolved exceptions attached.
- Then it **stops and waits for the Executive Director to certify**. Export labelled *simulated*.
- VO: "The report isn't written from memory. It's computed from the same object that made the promises."

### 3:00–3:25 — Beat 5: Renewal — the loop closes
- Next application pulls verified performance + clean-compliance evidence forward.
- Thesis line: "The application and the award are the same living object."

### 3:25–4:00 — Architecture flyover + production evidence
- **Two Cloud Run services** (orchestrator + ledger-sentinel), Pub/Sub topics per EVENT_CONTRACT, Firestore, Gemini via ADK.
- Say the two-service reasoning OUT LOUD (defended call from plan §Architecture): Sentinel is the only push-subscription, high-volume, retry/DLQ-heavy component; splitting it demonstrates retry isolation honestly. No agent calls another agent; every transition is an event with causation_id; every handler idempotent.
- GCP console cutaways: Cloud Run services live, Pub/Sub topics, Firestore docs.

---

## Dependencies
- [ ] MODEL_ID blocker — Gemini 3.5+ on the GCP project (Paing, Model Garden). Fix path in docs/GCP_VALIDATION_2026-08-26.md.
- [ ] eCFR verification pass (Aria Agent) gates all on-screen citations.
- [ ] Dashboard/UI (Pooof) — screens implied by beats: obligation graph, award-diff view, sentinel feed w/ 7-value legend, DLQ panel, SF-425 draft w/ click-through, certify gate, renewal evidence view.
- [ ] Devpost submission text (Pooof) — draft after dashboard screenshots exist.

## Recording notes
- Deterministic replay ⇒ identical takes. Record backend visibly on Google Cloud (console cutaways, not localhost).
- Script every VO line; zero improv on CFR numbers or dollar figures — all figures come from seed/riverbend_scenario.json and the plan doc.
